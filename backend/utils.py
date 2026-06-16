# backend/utils.py
import numpy as np
import matplotlib.colors as mcolors
from scipy.ndimage import gaussian_filter

def apply_gaussian_smoothing(ds_smoothed):

    # ========================================================================= 
    # Applies Gaussian filter kernels to specific meteorological data variables
    # to mitigate high-frequency noise and prevent color-band artifacts.
    # ========================================================================= 

    if 'prate' in ds_smoothed.data_vars:
        ds_smoothed['prate'].values = gaussian_filter(ds_smoothed['prate'].values, sigma=2.2)
    if 'gust' in ds_smoothed.data_vars:
        ds_smoothed['gust'].values = gaussian_filter(ds_smoothed['gust'].values, sigma=1.2)
    return ds_smoothed

def build_rain_rgba_mask(data_matrix, height, width):

    # ================================================== 
    # Generates a RGBA mask for precipitation intervals,
    # synchronized with frontend dashboard legends.
    # ==================================================

    rgba_image = np.zeros((height, width, 4), dtype=np.float32)
    
    hex_colors = ["#ebf4f6", "#b2d4ec", "#4b97c9", "#1f67b1", "#08306b"]
    rgb_colors = [mcolors.to_rgb(c) for c in hex_colors]
    
    # Render discrete intervals without partial pixel transparency (Alpha = 1.0)
    m1 = (data_matrix >= 0.1) & (data_matrix < 1.0)
    rgba_image[m1, 0:3] = rgb_colors[0]
    rgba_image[m1, 3] = 1.0
    
    m2 = (data_matrix >= 1.0) & (data_matrix < 5.0)
    rgba_image[m2, 0:3] = rgb_colors[1]
    rgba_image[m2, 3] = 1.0
    
    m3 = (data_matrix >= 5.0) & (data_matrix < 15.0)
    rgba_image[m3, 0:3] = rgb_colors[2]
    rgba_image[m3, 3] = 1.0
    
    m4 = (data_matrix >= 15.0) & (data_matrix < 30.0)
    rgba_image[m4, 0:3] = rgb_colors[3]
    rgba_image[m4, 3] = 1.0
    
    m5 = (data_matrix >= 30.0)
    rgba_image[m5, 0:3] = rgb_colors[4]
    rgba_image[m5, 3] = 1.0
    
    return rgba_image

def encode_wind_vectors(u_array, v_array):

    # ===================================================================
    # Performs UV-to-RGBA bit-packing conversion. Normalizes components 
    # into 0-255 bounds for frontend vector engine parsing.
    # ===============================================================

    matrix_u = u_array[::-1, :].copy()
    matrix_v = v_array[::-1, :].copy()
    
    u_normalized = ((matrix_u + 40) / 80 * 255).clip(0, 255).astype(np.uint8)
    v_normalized = ((matrix_v + 40) / 80 * 255).clip(0, 255).astype(np.uint8)
    
    height, width = u_normalized.shape
    wind_rgba_image = np.zeros((height, width, 4), dtype=np.uint8)
    wind_rgba_image[..., 0] = u_normalized  # R channel -> U-component
    wind_rgba_image[..., 1] = v_normalized  # G channel -> V-component
    wind_rgba_image[..., 3] = 255           # Absolute opacity
    
    return wind_rgba_image
