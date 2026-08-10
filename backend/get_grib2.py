"""
GFS Data Ingestion and Processing Pipeline for DatavizAMZ.

This script programmatically retrieves NOAA Global Forecast System (GFS) 
meteorological datasets via the Herbie framework, processes spatial parameters 
(wind components, temperature, relative humidity, wind gusts, and precipitation), 
applies spatial interpolation and Gaussian smoothing, and exports encoded PNG 
raster assets for client-side WebGIS rendering.

Author: Osvaldo Gogliano Sobrinho
License: MIT
"""

import os
import sys
import warnings
from datetime import datetime
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import imageio
from herbie import Herbie

# Custom imports
from config import LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, TOTAL_FRAMES, export_frontend_metadata
from utils import apply_gaussian_smoothing, build_rain_rgba_mask, encode_wind_vectors

# Suppress unnecessary non-critical warnings
warnings.filterwarnings('ignore')
matplotlib.use('Agg')


def crop_bbox(ds, lat_min=LAT_MIN, lat_max=LAT_MAX, lon_min=LON_MIN, lon_max=LON_MAX):
    """
    Crops dataset dynamically handling ascending or descending coordinate orientations.
    """
    lat_name = "latitude" if "latitude" in ds.coords else "lat"
    lon_name = "longitude" if "longitude" in ds.coords else "lon"

    # Determine latitude slice direction
    if ds[lat_name].values[0] > ds[lat_name].values[-1]:
        lat_slice = slice(lat_max, lat_min)  # Descending
    else:
        lat_slice = slice(lat_min, lat_max)  # Ascending

    # Determine longitude slice direction
    if ds[lon_name].values[0] > ds[lon_name].values[-1]:
        lon_slice = slice(lon_max, lon_min)
    else:
        lon_slice = slice(lon_min, lon_max)

    return ds.sel({lat_name: lat_slice, lon_name: lon_slice})


# Pipeline timing configuration
current_time = datetime.utcnow()
MODEL_RUN_DATE = datetime(current_time.year, current_time.month, current_time.day, 0, 0)
OUTPUT_DIRECTORY = "../frontend/pngs"


def process_frame(frame_idx: int) -> bool:
    """Fetches, processes, and exports raster assets for a single forecast frame."""
    print(f"\nProcessing frame {frame_idx} (Forecast Lead Time: +{frame_idx}h)...")

    # Garante o caminho absoluto para a pasta de saída
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_directory = os.path.abspath(os.path.join(script_dir, "../frontend/pngs"))

    try:
        herbie = Herbie(
            date=MODEL_RUN_DATE, 
            fxx=frame_idx, 
            model="gfs", 
            product="pgrb2.0p25",
            overwrite=True
        )
    except Exception as e:
        print(f"Error initializing Herbie for Frame {frame_idx}: {e}")
        return False

    ds_gfs = xr.Dataset()

    search_patterns = [
        r":UGRD:10 m|:VGRD:10 m",
        r":TMP:2 m|:RH:2 m",
        r":GUST:surface",
        r":PRATE:surface"
    ]

    for pattern in search_patterns:
        try:
            dataset_list = herbie.xarray(pattern, overwrite=True, backend_kwargs={"indexpath": ""})
            if not isinstance(dataset_list, list):
                dataset_list = [dataset_list]

            for chunk_ds in dataset_list:
                # Ajusta coordenadas de longitude para o formato 0..360 caso venham como -180..180
                lon_name = "longitude" if "longitude" in chunk_ds.coords else "lon"
                if float(chunk_ds[lon_name].min()) < 0 and LON_MIN > 180:
                    chunk_ds[lon_name] = chunk_ds[lon_name] % 360

                ds_cropped = crop_bbox(chunk_ds)

                for target_var in ds_cropped.data_vars:
                    var_lower = str(target_var).lower()

                    if var_lower in ['u10', 'u10m', 'u']:
                        ds_gfs['u10'] = ds_cropped[target_var].squeeze()
                    elif var_lower in ['v10', 'v10m', 'v']:
                        ds_gfs['v10'] = ds_cropped[target_var].squeeze()
                    elif 'gust' in var_lower:
                        ds_gfs['gust'] = ds_cropped[target_var].squeeze() * 3.6
                    elif 'prate' in var_lower:
                        ds_gfs['prate'] = ds_cropped[target_var].squeeze() * 3600
                    elif var_lower in ['tmp', 't2m', 't', '2t'] or 'temp' in var_lower:
                        kelvin_vals = ds_cropped[target_var].squeeze()
                        ds_gfs['tmp'] = kelvin_vals - 273.15 if float(kelvin_vals.max()) > 150 else kelvin_vals
                    elif var_lower in ['rh', 'r2', 'r', '2r'] or 'humidity' in var_lower:
                        ds_gfs['rh'] = ds_cropped[target_var].squeeze()

        except Exception as e:
            print(f"Warning: Exception encountered fetching '{pattern}' for Frame {frame_idx}: {e}")

    # Fallback para precipitação (Frame 0)
    if 'prate' not in ds_gfs.data_vars:
        existing_vars = list(ds_gfs.data_vars)
        if existing_vars:
            ds_gfs['prate'] = xr.zeros_like(ds_gfs[existing_vars[0]])
        else:
            print(f"Error: No valid data variables decoded for Frame {frame_idx}")
            return False

    # Ajuste de coordenadas
    lat_name = "latitude" if "latitude" in ds_gfs.coords else "lat"
    lon_name = "longitude" if "longitude" in ds_gfs.coords else "lon"
    
    ds_gfs = ds_gfs.sortby(lat_name).sortby(lon_name)

    lat_start, lat_end = float(ds_gfs[lat_name].values[0]), float(ds_gfs[lat_name].values[-1])
    lon_start, lon_end = float(ds_gfs[lon_name].values[0]), float(ds_gfs[lon_name].values[-1])
    
    num_lats, num_lons = int(ds_gfs[lat_name].size * 4), int(ds_gfs[lon_name].size * 4)
    target_lats = np.linspace(lat_start, lat_end, num_lats)
    target_lons = np.linspace(lon_start, lon_end, num_lons)

    interp_coords = {lat_name: target_lats, lon_name: target_lons}

    # Interpolação
    vars_cubic = [v for v in ['tmp', 'rh'] if v in ds_gfs.data_vars]
    ds_smoothed_cubic = ds_gfs[vars_cubic].interp(interp_coords, method="cubic") if vars_cubic else xr.Dataset()

    vars_linear = [v for v in ['u10', 'v10', 'gust', 'prate'] if v in ds_gfs.data_vars]
    ds_smoothed_linear = ds_gfs[vars_linear].interp(interp_coords, method="linear") if vars_linear else xr.Dataset()

    to_merge = [d for d in [ds_smoothed_cubic, ds_smoothed_linear] if len(d.data_vars) > 0]
    ds_smoothed = xr.merge(to_merge) if to_merge else xr.Dataset()

    ds_smoothed = apply_gaussian_smoothing(ds_smoothed)
    ds_smoothed = ds_smoothed.reindex({lat_name: list(reversed(ds_smoothed[lat_name].values))})

    final_arrays = {
        "u10": ds_smoothed['u10'].values if 'u10' in ds_smoothed else None,
        "v10": ds_smoothed['v10'].values if 'v10' in ds_smoothed else None,
        "gust": ds_smoothed['gust'].values if 'gust' in ds_smoothed else None,
        "prate": ds_smoothed['prate'].values if 'prate' in ds_smoothed else None,
        "tmp": ds_smoothed['tmp'].values if 'tmp' in ds_smoothed else None,
        "rh": ds_smoothed['rh'].values if 'rh' in ds_smoothed else None
    }

    try:
        os.makedirs(output_directory, exist_ok=True)
        print(f"📍 Salvando PNGs em: {output_directory}")

        raster_layers = {
            "temperature": {"data": final_arrays["tmp"], "cmap": "inferno", "vmax": 40.0},
            "humidity":    {"data": final_arrays["rh"],  "cmap": "YlGnBu",   "vmax": 100.0},
            "gust":        {"data": final_arrays["gust"],"cmap": "magma",    "vmax": 90.0},
            "rain":        {"data": final_arrays["prate"],"cmap": "Blues",   "vmax": 35.0}
        }

        saved_count = 0
        for layer_name, config in raster_layers.items():
            if config["data"] is None:
                print(f"⚠️ AVISO: Dados de '{layer_name}' estão None. Imagem ignorada.")
                continue

            data_matrix = config["data"].copy()
            chosen_cmap = config["cmap"]
            layer_vmax = config["vmax"]

            threshold = 0.1 if layer_name == "rain" else (15.0 if layer_name == "gust" else (40.0 if layer_name == "humidity" else None))

            height, width = data_matrix.shape
            fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')

            if layer_name == "rain":
                rgba_image = build_rain_rgba_mask(data_matrix, height, width)
                ax.imshow(rgba_image, origin='upper', interpolation='bicubic')
            else:
                if threshold is not None:
                    data_matrix = np.where(data_matrix < threshold, np.nan, data_matrix)
                current_cmap = plt.get_cmap(chosen_cmap).copy()
                current_cmap.set_bad(color='none', alpha=0.0)
                ax.imshow(data_matrix, cmap=current_cmap, origin='upper', interpolation='bicubic', vmin=threshold, vmax=layer_vmax)

            output_filepath = os.path.join(output_directory, f"amazon_{layer_name}_{frame_idx}.png")
            plt.savefig(output_filepath, transparent=True, dpi=100, pad_inches=0)
            plt.close(fig)
            saved_count += 1

        if final_arrays["u10"] is not None and final_arrays["v10"] is not None:
            wind_rgba_image = encode_wind_vectors(final_arrays["u10"], final_arrays["v10"])
            wind_output_filepath = os.path.join(output_directory, f"amazon_wind_{frame_idx}.png")
            imageio.imwrite(wind_output_filepath, wind_rgba_image)
            saved_count += 1

        print(f"✅ {saved_count} arquivos salvos com sucesso para o Frame {frame_idx}.")
        return True

    except Exception as e:
        print(f"Critical internal error encountered during array processing: {e}")
        return False
        
    
if __name__ == "__main__":
    print(f"Initializing GFS processing for model run: {MODEL_RUN_DATE.strftime('%Y-%m-%d %H:%M UTC')}")
    
    # Export web metadata once before execution
    export_frontend_metadata()

    successful_frames = 0
    for frame in range(TOTAL_FRAMES):
        if process_frame(frame):
            successful_frames += 1

    print(f"\nPipeline execution finished! Successfully processed frames: {successful_frames}/{TOTAL_FRAMES}")
    sys.exit(0 if successful_frames == TOTAL_FRAMES else 1)
