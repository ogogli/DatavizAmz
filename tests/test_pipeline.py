"""
Automated Verification and Validation (V&V) Test Suite for DatavizAMZ Pipeline.

License: MIT
"""

import os
import sys
import pytest
import numpy as np
import xarray as xr

# Adiciona a raiz do projeto ao path do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.utils import apply_gaussian_smoothing, encode_wind_vectors


def create_mock_gfs_dataset() -> xr.Dataset:
    """Creates a synthetic xarray Dataset mimicking the raw GFS grid over the Amazon bbox."""
    lats = np.linspace(4.125, -12.125, 66)
    lons = np.linspace(285.875, 314.125, 114)

    # Força matrizes 2D estritas no formato (66, 114)
    temp = np.full((66, 114), 295.0)
    u10 = np.full((66, 114), 5.0)
    v10 = np.full((66, 114), -3.0)
    precip = np.full((66, 114), 2.5)

    ds = xr.Dataset(
        data_vars={
            "tmp": (("latitude", "longitude"), temp),
            "u10": (("latitude", "longitude"), u10),
            "v10": (("latitude", "longitude"), v10),
            "prate": (("latitude", "longitude"), precip),
        },
        coords={"latitude": lats, "longitude": lons},
        attrs={"model_run": "2026-07-30T00:00:00"},
    )
    return ds


def test_spatial_grid_dimensions():
    """Verify raw bounding box dimensions match the expected 66 x 114 grid."""
    ds = create_mock_gfs_dataset()
    assert ds.dims["latitude"] == 66
    assert ds.dims["longitude"] == 114


def test_temperature_interpolation_residuals():
    """Verify Gaussian smoothing does not introduce unphysical temperature shifts."""
    ds = create_mock_gfs_dataset()
    ds_smoothed = apply_gaussian_smoothing(ds, sigma=1.0)

    raw_temp = ds["tmp"].values
    smoothed_temp = ds_smoothed["tmp"].values

    mae = np.mean(np.abs(raw_temp - smoothed_temp))
    assert mae < 0.5, f"Temperature MAE too high: {mae:.3f} K"


def test_precipitation_non_negativity():
    """Verify post-processed precipitation rates contain no negative values."""
    ds = create_mock_gfs_dataset()
    ds_smoothed = apply_gaussian_smoothing(ds, sigma=1.0)

    precip_values = ds_smoothed["prate"].values
    assert np.all(precip_values >= 0.0), "Interpolation produced negative precipitation values!"


def test_wind_vector_encoding_range():
    """Verify wind vector RGBA encoding maps values correctly to uint8 [0, 255]."""
    u = np.array([[-10.0, 0.0, 10.0]])
    v = np.array([[5.0, 0.0, -5.0]])

    encoded = encode_wind_vectors(u, v)

    assert encoded.dtype == np.uint8
    assert encoded.shape == (1, 3, 4)
    assert np.all(encoded[:, :, 3] == 255)  # Alpha channel fully opaque
