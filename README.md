# DatavizAMZ 🌦️🌐

**Automated, High-Performance WebGIS Engine for Real-Time Meteorological Data**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)[![Framework: MapLibre](https://img.shields.io/badge/Framework-MapLibre-brightgreen.svg)](https://maplibre.org/)

*DatavizAMZ is an open-source WebGIS platform designed to automate the retrieval, processing, and interactive rendering of atmospheric datasets. Optimized for the Amazon Basin with global grid scalability, it features a decoupled architecture for real-time environmental monitoring.*

---

## 🚀 Key Features

* **Automated Data Pipeline:** Programmatically ingests NOAA Global Forecast System (GFS) data via the `Herbie` framework. Applied Gaussian filtering ($\sigma = 1.0$, $5 \times 5$ kernel) and bicubic interpolation smooth out spatial noise without degrading meteorological gradients.
* **Lossless Vector Encoding:** Decomposes wind velocity into Zonal ($u$, East-West) and Meridional ($v$, North-South) vectors, encoding them into normalized **red and green** channels of ~16 MB PNG containers.
* **Client-Side Particle Advection:** Animates up to 2,500 wind vectors with trailing fade effects directly in the browser at **60 FPS** using a hardware-accelerated **HTML5 Canvas API**.
* **Zero CORS Overhead:** Co-locates the Python ingestion backend and single-file frontend on the same server instance to eliminate cross-origin request latency.

---

## 📁 Directory Structure

```text
DatavizAmz/
├── backend/
│   ├── get_grib2.py          # Primary data ingestion, processing, and raster export script
│   ├── utils.py              # Mathematical transformation and spatial filtering utilities
│   ├── requirements.txt      # Python dependencies for data pipeline
|   ├── config.py             # Config variables 
│   └── cron_output.log       # Output log generated after each cron run
├── frontend/
│   ├── index.html            # Main WebGIS dashboard container
│   ├── css/
│   │   └── style.css         # UI layout and MapLibre overlay styling
│   └── js/
│   |   └── dashboard.js      # MapLibre map initialization, layer management and wind Canvas
│   ├── metadata.json         # Config variables for js (generated after running get_grib2.py)
|   └── pngs/                 # Target directory for generated PNG rasters and metadata
├── tests/
│   ├── test_pipeine.py       # Unitary test or get_grib2.py
├── L(CENSE                   # MIT License file
└── README.md                 # System documentation
```

---

## 🔄 Backend-Frontend Relationship & Architecture

DatavizAMZ employs a **producer-consumer architecture** synchronized with NOAA's synoptic release windows:

1. **Backend (Data Producer):** Executes as a headless, scheduled pipeline. It ingests raw meteorological GRIB2 files from NOAA, computes array operations, maps vector components into normalized RGB channels, and writes static web-ready assets (`.png') to disk.
2. **Frontend (Visual Consumer):** Runs entirely client-side in the user's browser. It asynchronously fetches the static PNG rasters and metadata from the web server. The HTML5 Canvas engine decodes RGBA pixel channels back into physical velocity vectors $(u, v)$ to drive real-time particle animation over MapLibre GL JS layers.

```text
+------------------------+      Generates      +-------------------------+
|  Backend (Python Engine) | -----------------> | Static PNG & JSON Assets|
+------------------------+                     +-------------------------+
                                                            |
                                    Fetched via HTTP        v
                                               +--------------------------+
                                               | Frontend (Browser/Canvas)|
                                               +--------------------------+
```

---

## ⚙️ Core Functions & Processing Pipeline

### Backend Pipeline (`backend/get_grib2.py` & `backend/utils.py`)
* **NOAA Ingestion (`backend/get_grib2.py`):** Connects to NOAA AWS S3 / NOMADS endpoints using the `Herbie` framework to fetch GFS 0.25° GRIB2 sub-regions for 10m zonal ($u$) and meridional ($v$) wind vectors, 2m temperature, and precipitation rates.
* `apply_gaussian_smoothing(ds, sigma=1.0)` (`backend/utils.py`): Applies a 2D Gaussian filter via `scipy.ndimage.gaussian_filter` across spatial arrays to attenuate grid noise while preserving synoptic gradients.
* `encode_wind_vectors(u, v)` (`backend/utils.py`): Normalizes continuous floating-point velocity vectors into an 8-bit RGBA integer array $[0, 255]$ for $u \rightarrow \text{Red}$ and $v \rightarrow \text{Green}$ channels, exported as PNG assets.

### Frontend Engine (`frontend/js/dashboard.js`)
* **Data Ingestion:** Loads pre-processed PNG vector rasters and metadata JSON into HTML5 Canvas / WebGL contexts.
* **Vector Decoding:** Reconstructs continuous velocity fields $(u, v)$ in $\text{m/s}$ from RGBA pixel channels using metadata boundary scaling factors.
* **Particle Advection:** Computes particle displacement across frame updates via Euler integration ($x_{t+1} = x_t + u \cdot \Delta t$) with dynamic lifecycle re-seeding.
---

## ⚙️ Configuration Parameters

The backend pipeline uses `config.py` as the **single source of truth** for geographic spatial boundaries, grid interpolation, display canvas sizing, and forecast output settings. Modifying primary inputs automatically updates all derived matrix calculations and client-side metadata manifests.

---

### 📍 Primary Geographic Inputs

Primary bounds define the Amazon Basin region. Longitudes are defined using NOAA GFS 0° to 360° coordinate system ($360^\circ - \text{Longitude W}$).

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `LAT_MIN` | `-12.125°` | Southern latitude boundary |
| `LAT_MAX` | `4.125°` | Northern latitude boundary |
| `LON_MIN` | `285.875°` | Western longitude boundary ($74.125^\circ\text{W}$) |
| `LON_MAX` | `314.125°` | Eastern longitude boundary ($45.875^\circ\text{W}$) |
| `RAW_GRID_STEP` | `0.25°` | Native GFS dataset resolution (~28 km spacing) |
| `INTERPOLATED_STEP` | `0.0625°` | Upscaled spatial grid resolution (~7 km spacing) |

---

### 🖼️ Derived Spatial & Canvas Variables

To eliminate spatial skewing or distortion when rendering WebGIS map overlays, canvas height is dynamically computed using the spatial aspect ratio:

$$\text{Aspect Ratio} = \frac{\Delta \text{LAT}}{\Delta \text{LON}} = \frac{|4.125 - (-12.125)|}{|314.125 - 285.875|} = \frac{16.25^\circ}{28.25^\circ} \approx 0.5752$$

* **Target Canvas Width (`TARGET_CANVAS_WIDTH`):** `1000 px`
* **Calculated Canvas Height (`CANVAS_HEIGHT`):** `575 px`
* **Raw Matrix Shape (`RAW_LAT_COUNT` x `RAW_LON_COUNT`):** $66 \times 114$ grid points
* **Interpolated Matrix Shape (`INTERPOLATED_LAT_COUNT` x `INTERPOLATED_LON_COUNT`):** $261 \times 453$ grid points

---

### ⏱️ Forecast & Export Settings

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `TOTAL_FRAMES` | `48` | Total forecast lead-time hours (`+0h` to `+47h`) |
| `FORECAST_INTERVAL` | `1` | Hourly step between forecast frames |
| `OUTPUT_PNG_DIR` | `frontend/pngs` | Output directory for web raster layers |
| `METADATA_JSON_PATH` | `frontend/metadata.json` | Manifest path for WebGL/HTML5 canvas sync |

---

### 🔄 Metadata Manifest Export

Calling `export_frontend_metadata()` generates `frontend/metadata.json`, synchronizing client-side WebGL maps with backend bounding boxes:

```json
{
  "bbox": {
    "lat_min": -12.125,
    "lat_max": 4.125,
    "lon_min": 285.875,
    "lon_max": 314.125,
    "webgis_bounds": [285.875, -12.125, 314.125, 4.125]
  },
  "canvas": {
    "width": 1000,
    "height": 575,
    "aspect_ratio": 0.5752
  },
  "grid": {
    "raw_dimensions": [66, 114],
    "interpolated_dimensions": [261, 453]
  },
  "forecast": {
    "total_frames": 48,
    "interval_hours": 1
  }
}
---

### 📊 Output Artifacts & File Specifications

Each pipeline execution outputs two synchronized static files into the web root directory:

1. **Several Vector PNG Containers (`amazon_[climate_parameter]_[hour].png`):**
   * **Dimensions:** Scalable grid resolution (e.g., $1440 \times 720$ pixels).
   * **Color Encoding:** 
     * **Red Channel ($R$):** Zonal velocity component ($u$, East-West).
     * **Green Channel ($G$):** Meridional velocity component ($v$, North-South).
     * **Blue/Alpha Channels ($B, A$):** Reserved for future scalar overlays (e.g., atmospheric pressure or humidity).
2. **Output log generated after each cron run (`backend/cron_output.log`):** Content generated by running get_grib2.py
---

## 📋 System Requirements

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Data Ingestion** | `herbie-data` | Programmatic GRIB2 index parsing & HTTP byte-range retrieval |
| **Processing** | `numpy`, `xarray`, `scipy` | Spatial array operations & Gaussian filtering |
| **Raster Export** | `matplotlib`, `imageio` | Normalized RGB channel encoding to PNG assets |
| **Mapping Engine** | `MapLibre GL JS` | Client-side spatial layers and base map control |
| **Vector Engine** | `HTML5 Canvas API` | Hardware-accelerated particle advection loop |

---

## 🔧 Installation & Setup

### 1. Repository Setup
```bash
git clone https://github.com/ogogli/DatavizAmz.git
cd DatavizAmz
```

### 2. Environment Configuration
Create and activate an isolated Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
> **Note:** Ensure `requirements.txt` contains `herbie-data`, `numpy`, `xarray`, `scipy`, `matplotlib`, and `imageio`.

### 3. Frontend Deployment
Copy the contents of the `frontend/` directory to your web server's public root:

###
```bash
cp -r frontend/* /var/www/html/datavizamz/
# Alternatively, configure the /frontend folder to be the web server public root.
```
 3. Running the pipeline manually on the terminal for tests
```
cd path_to_DatavizAmz/backend
python get_grib2.py
# or python3 get_grib2.py depending on how Python 3 was installed
## The intermediate results generated by get_grib2.py appear on terminal
```
 4. Automation (Cron Job)
Configure a Linux cron task to trigger automated pipeline executions following NOAA publication windows:
```bash
crontab -e
```
Add the daily job definition (configured for **05:30 UTC** to ingest the 00z forecast horizon):
```cron
30 5 * * * /path/to/DatavizAmz/venv/bin/python /path/to/DatavizAmz/backend/get_grib2.py
# after inserting the line, exit crontab typing ctrl-O crtl-X.
# after each cron task execution a log file (cron_output.log) is generated inside the backend folder.
```
---
## 🛠️ Troubleshooting & Common Issues

This section covers common runtime errors, dependency pitfalls, and troubleshooting steps for the backend ingestion pipeline and frontend WebGIS interface.

---

### 1. Backend Ingestion & Grib2 Ingestion Issues

#### ❌ `Herbie / NOAA GFS Data Download Timeout`
* **Symptom:** `Failed to download data for Frame X` or HTTP 404/503 errors during execution.
* **Cause:** The NOAA NOMADS or AWS S3 data servers may experience temporary downtime, or the selected `MODEL_RUN_DATE` (e.g., today's `00:00 UTC` run) has not yet been fully published by NOAA (GFS runs usually take 3.5 to 4 hours to become available).
* **Fix:** 
  1. Check NOAA GFS status or test with yesterday's model run date by modifying `MODEL_RUN_DATE` in `get_grib2.py`.
  2. Ensure your internet connection is active and not blocked by a strict firewall/VPN blocking HTTPS requests to AWS S3 buckets.

#### ❌ `Missing C Libraries for GRIB2 Processing (eccodes / cfgrib)`
* **Symptom:** `ValueError: unrecognized engine cfgrib` or `eccodes library not found`.
* **Cause:** `xarray` relies on `cfgrib` and the underlying C library `eccodes` to parse raw GRIB2 files.
* **Fix:**
  * **Linux (Debian / Ubuntu - without Conda):**
    ```bash
    sudo apt-get update
    sudo apt-get install -y libeccodes-dev libeccodes-tools
    pip install cfgrib
    ```
  * **Linux (Fedora / RHEL):**
    ```bash
    sudo dnf install eccodes eccodes-devel
    pip install cfgrib
    ```
  * **Linux (Arch Linux):**
    ```bash
    sudo pacman -S eccodes
    pip install cfgrib
    ```
  * **Mac (Homebrew):** 
    ```bash
    brew install eccodes
    pip install cfgrib
    ```
  * **Conda Environment (Recommended multi-platform alternative):**
    ```bash
    conda install -c conda-forge eccodes cfgrib
    ```
  * **NOTE: The authors have tested DatavizAmz only on Python 3.12.3 and 3.10.12, Ubuntu 22.04.5 and macOS 26.5.2, but strongly believe it can run on other Linux and Python 3 versions.**
     
#### ❌ `FileNotFoundError: [Errno 2] No such file or directory: '../frontend/pngs'`
* **Symptom:** Script fails when attempting to save exported raster PNGs.
* **Cause:** The output directory relative path does not exist or lacks write permissions.
* **Fix:**
  The pipeline automatically attempts to create this directory using `os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)`. Ensure you are running the script from inside the `backend/` folder:
  ```bash
  cd backend
  python get_grib2.py
## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the Repository
2. Create a Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License & Citation

This software is distributed under the **MIT License**. See the [LICENSE](LICENSE) file for details.  
© 2026, **Osvaldo Gogliano Sobrinho**. Official repository: [github.com/ogogli/DatavizAmz](https://github.com/ogogli/DatavizAmz)

---

## 👥 Acknowledgments

* **Study and Research Group in Big Data (WDS)** — University of São Paulo (USP)
* **National Oceanic and Atmospheric Administration (NOAA)** for open meteorological data access.
