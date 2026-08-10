"""
Utility functions for meteorological spatial processing, spatial smoothing,
RGBA precipitation mask creation, and wind vector encoding.

Author: Osvaldo Gogliano Sobrinho
License: MIT
"""

import numpy as np
import xarray as xr
from scipy.ndimage import gaussian_filter


def apply_gaussian_smoothing(ds: xr.Dataset, sigma: float = 1.0) -> xr.Dataset:
    """Applies a 2D Gaussian spatial filter across atmospheric data variables.

    Args:
        ds (xr.Dataset): Input xarray Dataset containing spatial meteorological arrays.
        sigma (float, optional): Standard deviation for Gaussian kernel. Defaults to 1.0.

    Returns:
        xr.Dataset: A new xarray Dataset with spatially smoothed data fields.
    """
    ds_smoothed = ds.copy(deep=True)
    for var_name in ds_smoothed.data_vars:
        data = ds_smoothed[var_name].values
        if np.issubdtype(data.dtype, np.number):
            nan_mask = np.isnan(data)
            if np.any(nan_mask):
                filled_data = np.nan_to_num(data, nan=0.0)
                smoothed = gaussian_filter(filled_data, sigma=sigma)
                smoothed[nan_mask] = np.nan
                ds_smoothed[var_name].values = smoothed
            else:
                ds_smoothed[var_name].values = gaussian_filter(data, sigma=sigma)
    return ds_smoothed


def build_rain_rgba_mask(data_matrix: np.ndarray, height: int, width: int) -> np.ndarray:
    """Generates a custom RGBA image matrix for precipitation visualization.

    Args:
        data_matrix (np.ndarray): 2D spatial array of precipitation rates.
        height (int): Target pixel height of the output matrix.
        width (int): Target pixel width of the output matrix.

    Returns:
        np.ndarray: RGBA image array (shape: [height, width, 4]) with uint8 values.
    """
    rgba = np.zeros((height, width, 4), dtype=np.uint8)

    valid_mask = ~np.isnan(data_matrix) & (data_matrix >= 0.1)
    if not np.any(valid_mask):
        return rgba

    norm_rain = np.clip((data_matrix - 0.1) / (35.0 - 0.1), 0.0, 1.0)

    rgba[valid_mask, 0] = (30 + 100 * (1 - norm_rain[valid_mask])).astype(np.uint8)
    rgba[valid_mask, 1] = (100 + 100 * norm_rain[valid_mask]).astype(np.uint8)
    rgba[valid_mask, 2] = (200 + 55 * norm_rain[valid_mask]).astype(np.uint8)
    rgba[valid_mask, 3] = (150 + 105 * norm_rain[valid_mask]).astype(np.uint8)

    return rgba


def encode_wind_vectors(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Encodes zonal (u) and meridional (v) wind components into normalized RGBA channels.

    The u-component is mapped to the Red channel and the v-component to the Green channel,
    allowing client-side vector field reconstruction in HTML5 Canvas.

    Args:
        u (np.ndarray): 2D array of zonal wind speed components.
        v (np.ndarray): 2D array of meridional wind speed components.

    Returns:
        np.ndarray: 8-bit RGBA matrix encoding the wind vector field.
    """
    height, width = u.shape
    rgba = np.zeros((height, width, 4), dtype=np.uint8)

    u_min, u_max = -100.0, 100.0
    v_min, v_max = -100.0, 100.0

    u_norm = np.clip((u - u_min) / (u_max - u_min) * 255.0, 0, 255).astype(np.uint8)
    v_norm = np.clip((v - v_min) / (v_max - v_min) * 255.0, 0, 255).astype(np.uint8)

    rgba[:, :, 0] = u_norm
    rgba[:, :, 1] = v_norm
    rgba[:, :, 2] = 0
    rgba[:, :, 3] = 255

    return rgba
