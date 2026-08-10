"""
Central Spatial & Pipeline Configuration for DatavizAMZ
Modifying primary geographic coordinates will automatically update all derived parameters.
"""

import os
import json

# ==============================================================================
# 1. PRIMARY INPUTS (Change these to modify the region or resolution)
# ==============================================================================

# Geographic Bounding Box (Amazon Basin default)
LAT_MIN = -12.125
LAT_MAX = 4.125
LON_MIN = 285.875
LON_MAX = 314.125

# Spatial Resolutions (in degrees)
RAW_GRID_STEP = 0.25          # Native GFS 0.25° resolution
INTERPOLATED_STEP = 0.0625    # High-resolution web grid (0.0625° / ~7 km)

# Desired Frontend Canvas Display Width (in pixels)
TARGET_CANVAS_WIDTH = 1000

# Forecast Configuration
TOTAL_FRAMES = 48             # Number of forecast lead-time hours (f000 to f047)
FORECAST_INTERVAL = 1         # Hour step between frames

# Number of wind particles for animation
NUMBER_PARTICLES = 2500

# Maplibre zoom
ZOOM = 5.5					# Start zoom for Maplibre

# ==============================================================================
# 2. AUTOMATICALLY DERIVED SPATIAL VARIABLES
# ==============================================================================

# Degree Spans & Geographic Aspect Ratio
DELTA_LON = abs(LON_MAX - LON_MIN)                  # 28.25°
DELTA_LAT = abs(LAT_MAX - LAT_MIN)                  # 16.25°
ASPECT_RATIO = DELTA_LAT / DELTA_LON                  # ~0.5752

# Canvas Dimensions (Guarantees zero spatial distortion on WebGIS)
CANVAS_WIDTH = TARGET_CANVAS_WIDTH
CANVAS_HEIGHT = round(TARGET_CANVAS_WIDTH * ASPECT_RATIO)  # 575 px

# Matrix Dimensions (Rows x Columns)
RAW_LAT_COUNT = int(round(DELTA_LAT / RAW_GRID_STEP)) + 1         # 66
RAW_LON_COUNT = int(round(DELTA_LON / RAW_GRID_STEP)) + 1         # 114

INTERPOLATED_LAT_COUNT = int(round(DELTA_LAT / INTERPOLATED_STEP)) + 1  # 261
INTERPOLATED_LON_COUNT = int(round(DELTA_LON / INTERPOLATED_STEP)) + 1  # 453

# Ready-to-use Slices for xarray / Herbie Dataset indexing
# (Note: GFS arrays sort latitudes from North to South, so start=LAT_MAX)
BBOX_SLICES = {
    "latitude": slice(LAT_MAX, LAT_MIN),
    "longitude": slice(LON_MIN, LON_MAX),
}

# WebGIS Bounding Box Format [West, South, East, North] for MapLibre/Leaflet
WEBGIS_BBOX = [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX]

# Default File Paths
OUTPUT_PNG_DIR = "frontend/pngs"
METADATA_JSON_PATH = "frontend/metadata.json"

# ==============================================================================
# 3. METADATA EXPORT FUNCTION
# ==============================================================================

def export_frontend_metadata(output_path: str = METADATA_JSON_PATH) -> dict:
    """
    Exports a JSON manifest to the frontend directory so HTML5/WebGL layers
    stay perfectly synchronized with backend bounding boxes and canvas sizes.
    """
    metadata = {
        "bbox": {
            "lat_min": LAT_MIN,
            "lat_max": LAT_MAX,
            "lon_min": LON_MIN,
            "lon_max": LON_MAX,
            "webgis_bounds": WEBGIS_BBOX,
        },
        "canvas": {
            "width": CANVAS_WIDTH,
            "height": CANVAS_HEIGHT,
            "aspect_ratio": round(ASPECT_RATIO, 4),
            "number_particles": NUMBER_PARTICLES,
            "zoom": ZOOM
        },
        "grid": {
            "raw_dimensions": [RAW_LAT_COUNT, RAW_LON_COUNT],
            "interpolated_dimensions": [INTERPOLATED_LAT_COUNT, INTERPOLATED_LON_COUNT],
        },
        "forecast": {
            "total_frames": TOTAL_FRAMES,
            "interval_hours": FORECAST_INTERVAL,
        },
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata

if __name__ == "__main__":
    # Test script execution and generate metadata.json directly
    meta = export_frontend_metadata()
    print(f"✅ Spatial configuration exported successfully!")
    print(f"   Canvas Size: {CANVAS_WIDTH} x {CANVAS_HEIGHT} px")
    print(f"   Raw Grid Shape: {RAW_LAT_COUNT} x {RAW_LON_COUNT}")