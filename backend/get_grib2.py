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
import imageio.v3 as imageio
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from herbie import Herbie

# Custom imports - Importa dimensões diretas do config.py
from config import (
    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, 
    INTERPOLATED_LAT_COUNT, INTERPOLATED_LON_COUNT,
    TOTAL_FRAMES, export_frontend_metadata
)
from utils import apply_gaussian_smoothing, build_rain_rgba_mask

# Suppress unnecessary non-critical warnings
warnings.filterwarnings('ignore')
matplotlib.use('Agg')


# Pipeline timing configuration
current_time = datetime.utcnow()
MODEL_RUN_DATE = datetime(current_time.year, current_time.month, current_time.day, 0, 0)


def sanitize_and_crop(da: xr.DataArray) -> xr.DataArray:
    """
    Standardizes coordinate names, normalizes longitude system (-180..180 vs 0..360)
    to match config.py, sorts axes monotonically, and crops to the target bounding box.
    """
    if da is None:
        return None

    da = da.squeeze()

    # 1. Identifica e padroniza os nomes das coordenadas para 'lat' e 'lon'
    lat_col = "latitude" if "latitude" in da.coords else ("lat" if "lat" in da.coords else None)
    lon_col = "longitude" if "longitude" in da.coords else ("lon" if "lon" in da.coords else None)

    if not lat_col or not lon_col:
        return None

    rename_dict = {}
    if lat_col != "lat":
        rename_dict[lat_col] = "lat"
    if lon_col != "lon":
        rename_dict[lon_col] = "lon"

    if rename_dict:
        da = da.rename(rename_dict)

    # Remove coordenadas extras não espaciais (heightAboveGround, surface, etc.)
    coords_to_drop = [c for c in da.coords if c not in ["lat", "lon"]]
    da = da.drop_vars(coords_to_drop, errors="ignore")

    # 2. Normaliza o sistema de longitude com base no LON_MIN do config.py
    if LON_MIN < 0:
        if float(da["lon"].max()) > 180:
            lon_180 = ((da["lon"] + 180) % 360) - 180
            da = da.assign_coords(lon=lon_180)
    else:
        if float(da["lon"].min()) < 0:
            lon_360 = da["lon"] % 360
            da = da.assign_coords(lon=lon_360)

    # 3. Reordena as coordenadas para garantir eixos estritamente crescentes
    da = da.sortby("lat").sortby("lon")

    # 4. Ajusta os limites de recorte garantindo compatibilidade com a grade
    lats = da["lat"].values
    lons = da["lon"].values

    lat_sub_min = max(float(lats.min()), min(LAT_MIN, LAT_MAX))
    lat_sub_max = min(float(lats.max()), max(LAT_MIN, LAT_MAX))
    lon_sub_min = max(float(lons.min()), min(LON_MIN, LON_MAX))
    lon_sub_max = min(float(lons.max()), max(LON_MIN, LON_MAX))

    return da.sel(lat=slice(lat_sub_min, lat_sub_max), lon=slice(lon_sub_min, lon_sub_max))


def process_frame(frame_idx: int) -> bool:
    """Fetches, processes, and exports raster assets for a single forecast frame."""
    print(f"\nProcessing frame {frame_idx} (Forecast Lead Time: +{frame_idx}h)...")

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

    raw_extracted = {}

    # REGEX RIGOROSO: "above ground" previne a captura indesejada do nível de pressão "2 mb" (estratosfera)
    search_patterns = [
        r":UGRD:10 m above ground|:VGRD:10 m above ground",
        r":TMP:2 m above ground|:RH:2 m above ground",
        r":GUST:surface",
        r":PRATE:surface"
    ]

    for pattern in search_patterns:
        try:
            dataset_list = herbie.xarray(pattern, overwrite=True, backend_kwargs={"indexpath": ""})
            if not isinstance(dataset_list, list):
                dataset_list = [dataset_list]

            for chunk_ds in dataset_list:
                for target_var in chunk_ds.data_vars:
                    var_lower = str(target_var).lower()
                    da_clean = sanitize_and_crop(chunk_ds[target_var])

                    if da_clean is None or da_clean.size == 0:
                        continue

                    if var_lower in ['u10', 'u10m', 'u', 'ugrd']:
                        raw_extracted['u10'] = da_clean
                    elif var_lower in ['v10', 'v10m', 'v', 'vgrd']:
                        raw_extracted['v10'] = da_clean
                    elif 'gust' in var_lower:
                        raw_extracted['gust'] = da_clean * 3.6
                    elif 'prate' in var_lower:
                        raw_extracted['prate'] = da_clean * 3600
                    elif var_lower in ['tmp', 't2m', 't', '2t'] or 'temp' in var_lower:
                        mean_k = float(da_clean.mean(skipna=True).values)
                        if mean_k > 150:
                            da_clean = da_clean - 273.15
                        raw_extracted['tmp'] = da_clean
                    elif var_lower in ['rh', 'r2', 'r', '2r', 'relative_humidity'] or 'humidity' in var_lower:
                        raw_extracted['rh'] = da_clean

        except Exception as e:
            print(f"Warning: Exception encountered fetching '{pattern}' for Frame {frame_idx}: {e}")

    if not raw_extracted:
        print(f"Error: No valid data variables extracted for Frame {frame_idx}")
        return False

    # Fallback para Precipitação no Frame 0
    if 'prate' not in raw_extracted:
        first_ref = list(raw_extracted.values())[0]
        raw_extracted['prate'] = xr.zeros_like(first_ref)

    # --- DEFINIÇÃO DA GRADE ALVO BASEADA NO CONFIG.PY ---
    target_lats = np.linspace(min(LAT_MIN, LAT_MAX), max(LAT_MIN, LAT_MAX), INTERPOLATED_LAT_COUNT)
    target_lons = np.linspace(min(LON_MIN, LON_MAX), max(LON_MIN, LON_MAX), INTERPOLATED_LON_COUNT)
    interp_coords = {"lat": target_lats, "lon": target_lons}

    # Interpolação individual por variável
    ds_interpolated = xr.Dataset()
    print("📊 Surface data status:")
    for var_name, da in raw_extracted.items():
        da_interp = da.interp(interp_coords, method="linear")
        ds_interpolated[var_name] = da_interp
        
        v_min = float(da_interp.min(skipna=True).values)
        v_max = float(da_interp.max(skipna=True).values)
        print(f"  • {var_name.upper()}: min={v_min:.2f}, max={v_max:.2f}")

    # Aplica suavização gaussiana
    ds_smoothed = apply_gaussian_smoothing(ds_interpolated)

    # Reordena latitude de cima para baixo (Norte no topo para renderização origin='upper')
    ds_smoothed = ds_smoothed.reindex({"lat": list(reversed(ds_smoothed["lat"].values))})

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
        saved_count = 0

        # 1. RENDERIZAÇÃO MATPLOTLIB (Camadas Escalares: Temp, Umidade, Rajada, Chuva)
        raster_layers = {
            "temperature": {"data": final_arrays["tmp"],  "cmap": "inferno", "vmin": 15.0, "vmax": 40.0, "mask_below": None},
            "humidity":    {"data": final_arrays["rh"],   "cmap": "YlGnBu",  "vmin": 20.0, "vmax": 100.0, "mask_below": None},
            "gust":        {"data": final_arrays["gust"], "cmap": "magma",   "vmin": 15.0, "vmax": 90.0,  "mask_below": 15.0},
            "rain":        {"data": final_arrays["prate"],"cmap": "Blues",  "vmin": 0.1,  "vmax": 35.0,  "mask_below": 0.1}
        }

        for layer_name, config in raster_layers.items():
            if config["data"] is None:
                print(f"⚠️ AVISO: Dados de '{layer_name}' estão None. Imagem ignorada.")
                continue

            data_matrix = config["data"].copy()
            height, width = data_matrix.shape

            fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')

            if layer_name == "rain":
                rgba_image = build_rain_rgba_mask(data_matrix, height, width)
                ax.imshow(rgba_image, origin='upper', interpolation='bicubic')
            else:
                if config["mask_below"] is not None:
                    data_matrix = np.where(data_matrix < config["mask_below"], np.nan, data_matrix)

                current_cmap = plt.get_cmap(config["cmap"]).copy()
                current_cmap.set_bad(color='none', alpha=0.0)

                ax.imshow(
                    data_matrix, 
                    cmap=current_cmap, 
                    origin='upper', 
                    interpolation='bicubic', 
                    vmin=config["vmin"], 
                    vmax=config["vmax"]
                )

            output_filepath = os.path.join(output_directory, f"amazon_{layer_name}_{frame_idx}.png")
            plt.savefig(output_filepath, transparent=True, dpi=100, pad_inches=0)
            plt.close(fig)
            saved_count += 1

        # 2. EXPORTAÇÃO CODIFICADA EM TEXTURA UV (Para Partículas WebGL no MapLibre)
        if final_arrays["u10"] is not None and final_arrays["v10"] is not None:
            u_m_s = final_arrays["u10"]
            v_m_s = final_arrays["v10"]

            # Mapeia [-30, +30] m/s para [0, 255] uint8 (128 = 0 m/s)
            u_norm = np.clip((u_m_s + 30.0) / 60.0 * 255.0, 0, 255).astype(np.uint8)
            v_norm = np.clip((v_m_s + 30.0) / 60.0 * 255.0, 0, 255).astype(np.uint8)

            height, width = u_m_s.shape
            rgba_uv = np.zeros((height, width, 4), dtype=np.uint8)
            rgba_uv[:, :, 0] = u_norm  # Canal Red = Componente U
            rgba_uv[:, :, 1] = v_norm  # Canal Green = Componente V
            rgba_uv[:, :, 2] = 0       # Canal Blue
            rgba_uv[:, :, 3] = 255     # Alpha Totalmente Opaco

            wind_filepath = os.path.join(output_directory, f"amazon_wind_{frame_idx}.png")
            imageio.imwrite(wind_filepath, rgba_uv)
            saved_count += 1

        print(f"✅ {saved_count} arquivos raster/texturas gerados com sucesso para o Frame {frame_idx}.")
        return True

    except Exception as e:
        print(f"Critical internal error encountered during array processing: {e}")
        return False


if __name__ == "__main__":
    print(f"Initializing GFS processing for model run: {MODEL_RUN_DATE.strftime('%Y-%m-%d %H:%M UTC')}")

    export_frontend_metadata()

    successful_frames = 0
    for frame in range(TOTAL_FRAMES):
        if process_frame(frame):
            successful_frames += 1

    print(f"\nPipeline execution finished! Successfully processed frames: {successful_frames}/{TOTAL_FRAMES}")
    sys.exit(0 if successful_frames == TOTAL_FRAMES else 1)
