import os
import sys
import numpy as np
import xarray as xr
from datetime import datetime
import matplotlib.pyplot as plt
import imageio  
import warnings

# Importing our custom utility functions
from utils import apply_gaussian_smoothing, build_rain_rgba_mask, encode_wind_vectors

# Ignore warning messages
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')

from herbie import Herbie

# ==================================
# Script configurations and metadata
# ==================================

current_time = datetime.utcnow()
MODEL_RUN_DATE = datetime(current_time.year, current_time.month, current_time.day, 0, 0) 
TOTAL_FRAMES = 48
OUTPUT_DIRECTORY = "../frontend/pngs"

BBOX = {
    "longitude": slice(285.875, 314.125),  
    "latitude": slice(4.125, -12.125)      
}

print(f"Initializing GFS data processing for model run: {MODEL_RUN_DATE.strftime('%Y-%m-%d %H:%M UTC')}")

# ==================================
# Core function for frame processing
# ==================================
def process_frame(frame_idx):
    print(f"\nProcessing frame {frame_idx} (Forecast Lead Time: +{frame_idx}h)...")
    
    try:
        H = Herbie(date=MODEL_RUN_DATE, fxx=frame_idx, model="gfs", product="pgrb2.0p25")
    except Exception as e:
        print(f"Error initializing Herbie for Frame {frame_idx}: {e}")
        return False

	# Search for temperature or humidity at 2 m, or wind components at 10 m or
	# Gust or precipitation at the surface
    search_regex = "(TMP|RH):2 m|(UGRD|VGRD):10 m|(GUST|PRATE):surface"
    
    try:
        dataset_list = H.xarray(search_regex)
    except Exception as e:
        print(f"Failed to download data for Frame {frame_idx}: {e}")
        return False

    if not isinstance(dataset_list, list):
        dataset_list = [dataset_list]
        
    ds_gfs = xr.Dataset()

    for chunk_ds in dataset_list:
        ds_cropped = chunk_ds.sel(**BBOX)
        if 'u10' in ds_cropped.data_vars:
            ds_gfs['u10'] = ds_cropped['u10'] * 3.6  # m/s to km/h
        if 'v10' in ds_cropped.data_vars:
            ds_gfs['v10'] = ds_cropped['v10'] * 3.6  # m/s to km/h
            
        for target_var in ds_cropped.data_vars:
            var_lower = target_var.lower()
            if 'gust' in var_lower:
                ds_gfs['gust'] = ds_cropped[target_var] * 3.6
            elif 'prate' in var_lower:
                ds_gfs['prate'] = ds_cropped[target_var] * 3600
            elif 'tmp' in var_lower or 't2m' in var_lower:
                kelvin_vals = ds_cropped[target_var]
                ds_gfs['tmp'] = kelvin_vals - 273.15 if kelvin_vals.max() > 150 else kelvin_vals
            elif 'rh' in var_lower or 'r2' in var_lower:
                ds_gfs['rh'] = ds_cropped[target_var]

    if frame_idx == 0 and 'prate' not in ds_gfs.data_vars:
        reference_var = 'tmp' if 'tmp' in ds_gfs.data_vars else 'u10'
        ds_gfs['prate'] = xr.zeros_like(ds_gfs[reference_var])

    # Grid Interpolation (Upscaling mesh resolution)
    lat_start, lat_end = float(ds_gfs.latitude.values[0]), float(ds_gfs.latitude.values[-1])
    lon_start, lon_end = float(ds_gfs.longitude.values[0]), float(ds_gfs.longitude.values[-1])
    num_lats, num_lons = int(ds_gfs.latitude.size * 4), int(ds_gfs.longitude.size * 4)
    target_lats = np.linspace(lat_start, lat_end, num_lats)
    target_lons = np.linspace(lon_start, lon_end, num_lons)
    
    vars_cubic = [v for v in ['tmp', 'rh'] if v in ds_gfs.data_vars]
    ds_smoothed_cubic = ds_gfs[vars_cubic].interp(latitude=target_lats, longitude=target_lons, method="cubic")
    
    vars_linear = [v for v in ['u10', 'v10', 'gust', 'prate'] if v in ds_gfs.data_vars]
    ds_smoothed_linear = ds_gfs[vars_linear].interp(latitude=target_lats, longitude=target_lons, method="linear")
    
    ds_smoothed = xr.merge([ds_smoothed_cubic, ds_smoothed_linear])

    # MODIFICATION 1: Call Gaussian Filter from utilities
    ds_smoothed = apply_gaussian_smoothing(ds_smoothed)

    final_arrays = {
        "u10": ds_smoothed['u10'].values if 'u10' in ds_smoothed else None,
        "v10": ds_smoothed['v10'].values if 'v10' in ds_smoothed else None,
        "gust": ds_smoothed['gust'].values if 'gust' in ds_smoothed else None,
        "prate": ds_smoothed['prate'].values if 'prate' in ds_smoothed else None,
        "tmp": ds_smoothed['tmp'].values if 'tmp' in ds_smoothed else None,
        "rh": ds_smoothed['rh'].values if 'rh' in ds_smoothed else None
    }

    try:
        os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
        raster_layers = {
            "temperature": {"data": final_arrays["tmp"], "cmap": "inferno", "vmax": 40.0},
            "humidity":    {"data": final_arrays["rh"],  "cmap": "YlGnBu",   "vmax": 100.0},
            "gust":        {"data": final_arrays["gust"],"cmap": "magma",    "vmax": 90.0},
            "rain":        {"data": final_arrays["prate"],"cmap": "Blues",   "vmax": 35.0}
        }        
        
        for layer_name, config in raster_layers.items():
            data_matrix = config["data"].copy()
            chosen_cmap = config["cmap"]
            layer_vmax = config["vmax"]
            
            threshold = 0.1 if layer_name == "rain" else (15.0 if layer_name == "gust" else (40.0 if layer_name == "humidity" else None))
            
            height, width = data_matrix.shape
            fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')
            
            if layer_name == "rain":
                # MODIFICATION 2: Call RGBA Rain mask generation from utilities
                rgba_image = build_rain_rgba_mask(data_matrix, height, width)
                ax.imshow(rgba_image, origin='upper', interpolation='bicubic')
            else:
                if threshold is not None:
                    data_matrix = np.where(data_matrix < threshold, np.nan, data_matrix)
                current_cmap = plt.get_cmap(chosen_cmap).copy()
                current_cmap.set_bad(color='none', alpha=0.0)
                ax.imshow(data_matrix, cmap=current_cmap, origin='upper', interpolation='bicubic', vmin=threshold, vmax=layer_vmax)
            
            output_filepath = os.path.join(OUTPUT_DIRECTORY, f"amazon_{layer_name}_{frame_idx}.png")
            plt.savefig(output_filepath, transparent=True, dpi=100, pad_inches=0)
            plt.close(fig)
            
        # MODIFICATION 3: Call Wind Vector Encoding from utilities
        if final_arrays["u10"] is not None and final_arrays["v10"] is not None:
            wind_rgba_image = encode_wind_vectors(final_arrays["u10"], final_arrays["v10"])
            wind_output_filepath = os.path.join(OUTPUT_DIRECTORY, f"amazon_wind_{frame_idx}.png")
            imageio.imwrite(wind_output_filepath, wind_rgba_image)
            
        return True 
        
    except Exception as e:
        print(f"Critical internal error encountered during array processing: {e}")
        return False

if __name__ == "__main__":
    successful_frames = 0
    for frame in range(TOTAL_FRAMES):
        if process_frame(frame):
            successful_frames += 1
            
    print(f"\nPipeline execution finished! Successfully processed frames: {successful_frames}/{TOTAL_FRAMES}")
    sys.exit(0 if successful_frames == TOTAL_FRAMES else 1)# ==================================
# Core function for frame processing
# ==================================
def process_frame(frame_idx):
    print(f"\nProcessing frame {frame_idx} (Forecast Lead Time: +{frame_idx}h)...")
    
    try:
        H = Herbie(date=MODEL_RUN_DATE, fxx=frame_idx, model="gfs", product="pgrb2.0p25")
    except Exception as e:
        print(f"Error initializing Herbie for Frame {frame_idx}: {e}")
        return False

	# Search for temperature or humidity at 2 m, or wind components at 10 m or
	# Gust or precipitation at the surface
    search_regex = "(TMP|RH):2 m|(UGRD|VGRD):10 m|(GUST|PRATE):surface"
    
    try:
        dataset_list = H.xarray(search_regex)
    except Exception as e:
        print(f"Failed to download data for Frame {frame_idx}: {e}")
        return False

    if not isinstance(dataset_list, list):
        dataset_list = [dataset_list]
        
    ds_gfs = xr.Dataset()

    for chunk_ds in dataset_list:
        ds_cropped = chunk_ds.sel(**BBOX)
        if 'u10' in ds_cropped.data_vars:
            ds_gfs['u10'] = ds_cropped['u10'] * 3.6  # m/s to km/h
        if 'v10' in ds_cropped.data_vars:
            ds_gfs['v10'] = ds_cropped['v10'] * 3.6  # m/s to km/h
            
        for target_var in ds_cropped.data_vars:
            var_lower = target_var.lower()
            if 'gust' in var_lower:
                ds_gfs['gust'] = ds_cropped[target_var] * 3.6
            elif 'prate' in var_lower:
                ds_gfs['prate'] = ds_cropped[target_var] * 3600
            elif 'tmp' in var_lower or 't2m' in var_lower:
                kelvin_vals = ds_cropped[target_var]
                ds_gfs['tmp'] = kelvin_vals - 273.15 if kelvin_vals.max() > 150 else kelvin_vals
            elif 'rh' in var_lower or 'r2' in var_lower:
                ds_gfs['rh'] = ds_cropped[target_var]

    if frame_idx == 0 and 'prate' not in ds_gfs.data_vars:
        reference_var = 'tmp' if 'tmp' in ds_gfs.data_vars else 'u10'
        ds_gfs['prate'] = xr.zeros_like(ds_gfs[reference_var])

    # Grid Interpolation (Upscaling mesh resolution)
    lat_start, lat_end = float(ds_gfs.latitude.values[0]), float(ds_gfs.latitude.values[-1])
    lon_start, lon_end = float(ds_gfs.longitude.values[0]), float(ds_gfs.longitude.values[-1])
    num_lats, num_lons = int(ds_gfs.latitude.size * 4), int(ds_gfs.longitude.size * 4)
    target_lats = np.linspace(lat_start, lat_end, num_lats)
    target_lons = np.linspace(lon_start, lon_end, num_lons)
    
    vars_cubic = [v for v in ['tmp', 'rh'] if v in ds_gfs.data_vars]
    ds_smoothed_cubic = ds_gfs[vars_cubic].interp(latitude=target_lats, longitude=target_lons, method="cubic")
    
    vars_linear = [v for v in ['u10', 'v10', 'gust', 'prate'] if v in ds_gfs.data_vars]
    ds_smoothed_linear = ds_gfs[vars_linear].interp(latitude=target_lats, longitude=target_lons, method="linear")
    
    ds_smoothed = xr.merge([ds_smoothed_cubic, ds_smoothed_linear])

    # MODIFICATION 1: Call Gaussian Filter from utilities
    ds_smoothed = apply_gaussian_smoothing(ds_smoothed)

    final_arrays = {
        "u10": ds_smoothed['u10'].values if 'u10' in ds_smoothed else None,
        "v10": ds_smoothed['v10'].values if 'v10' in ds_smoothed else None,
        "gust": ds_smoothed['gust'].values if 'gust' in ds_smoothed else None,
        "prate": ds_smoothed['prate'].values if 'prate' in ds_smoothed else None,
        "tmp": ds_smoothed['tmp'].values if 'tmp' in ds_smoothed else None,
        "rh": ds_smoothed['rh'].values if 'rh' in ds_smoothed else None
    }

    try:
        os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
        raster_layers = {
            "temperature": {"data": final_arrays["tmp"], "cmap": "inferno", "vmax": 40.0},
            "humidity":    {"data": final_arrays["rh"],  "cmap": "YlGnBu",   "vmax": 100.0},
            "gust":        {"data": final_arrays["gust"],"cmap": "magma",    "vmax": 90.0},
            "rain":        {"data": final_arrays["prate"],"cmap": "Blues",   "vmax": 35.0}
        }        
        
        for layer_name, config in raster_layers.items():
            data_matrix = config["data"].copy()
            chosen_cmap = config["cmap"]
            layer_vmax = config["vmax"]
            
            threshold = 0.1 if layer_name == "rain" else (15.0 if layer_name == "gust" else (40.0 if layer_name == "humidity" else None))
            
            height, width = data_matrix.shape
            fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')
            
            if layer_name == "rain":
                # MODIFICATION 2: Call RGBA Rain mask generation from utilities
                rgba_image = build_rain_rgba_mask(data_matrix, height, width)
                ax.imshow(rgba_image, origin='upper', interpolation='bicubic')
            else:
                if threshold is not None:
                    data_matrix = np.where(data_matrix < threshold, np.nan, data_matrix)
                current_cmap = plt.get_cmap(chosen_cmap).copy()
                current_cmap.set_bad(color='none', alpha=0.0)
                ax.imshow(data_matrix, cmap=current_cmap, origin='upper', interpolation='bicubic', vmin=threshold, vmax=layer_vmax)
            
            output_filepath = os.path.join(OUTPUT_DIRECTORY, f"amazon_{layer_name}_{frame_idx}.png")
            plt.savefig(output_filepath, transparent=True, dpi=100, pad_inches=0)
            plt.close(fig)
            
        # MODIFICATION 3: Call Wind Vector Encoding from utilities
        if final_arrays["u10"] is not None and final_arrays["v10"] is not None:
            wind_rgba_image = encode_wind_vectors(final_arrays["u10"], final_arrays["v10"])
            wind_output_filepath = os.path.join(OUTPUT_DIRECTORY, f"amazon_wind_{frame_idx}.png")
            imageio.imwrite(wind_output_filepath, wind_rgba_image)
            
        return True 
        
    except Exception as e:
        print(f"Critical internal error encountered during array processing: {e}")
        return False

if __name__ == "__main__":
    successful_frames = 0
    for frame in range(TOTAL_FRAMES):
        if process_frame(frame):
            successful_frames += 1
            
    print(f"\nPipeline execution finished! Successfully processed frames: {successful_frames}/{TOTAL_FRAMES}")
    sys.exit(0 if successful_frames == TOTAL_FRAMES else 1)
