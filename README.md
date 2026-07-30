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
│   └── cron_output.log       # Output log generated after each get_grib2.py run
├── frontend/
│   ├── index.html            # Main WebGIS dashboard container
│   ├── css/
│   │   └── style.css         # UI layout and MapLibre overlay styling
│   └── js/
│   |   └── dashboard.js      # MapLibre map initialization, layer management and wind Canvas
│   └── pngs/                 # Target directory for generated PNG rasters and metadata
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

## ⚙️ Principal Functions & Processing Pipeline

### Backend Modules (`backend/get_grib2.py`)
* `fetch_gfs_data()`: Connects to NOAA AWS S3 mirrors using the `Herbie` framework to execute byte-range HTTP requests for 10 m Zonal ($u$) and Meridional ($v$) wind velocity components.
* `apply_spatial_smoothing(data_array, sigma=1.0)`: Applies a 2D Gaussian filter kernel to spatial arrays via `scipy.ndimage.gaussian_filter` to attenuate grid noise while preserving synoptic gradients.
* `encode_vectors_to_png(u_array, v_array, output_path)`: Normalizes continuous floating-point velocity vectors to an 8-bit integer range $[0, 255]$ and writes $u \rightarrow \text{Red}$ and $v \rightarrow \text{Green}$ channels into a lossless 16 MB PNG raster container.
* `export_metadata(bounds, min_max_vals, output_path)`: Generates a JSON manifest containing spatial coordinate boundaries ($Lat_{min}, Lat_{max}, Lon_{min}, Lon_{max}$) and vector normalization extrema ($u_{min}, u_{max}, v_{min}, v_{max}$).

### Frontend Engine (`frontend/js/wind_canvas.js`)
* `fetchMetadataAndRaster()`: Loads the JSON manifest and PNG raster container into an offscreen HTML5 Canvas memory context.
* `decodeRGBToVector(r, g)`: Converts 8-bit pixel channel values back into real physical velocities $(u, v)$ in m/s using linear interpolation against bounds defined in the metadata.
* `updateParticles()`: Computes particle displacement using Euler integration ($x_{t+1} = x_t + u \cdot \Delta t$) and manages particle lifecycles (random re-seeding upon expiration).

---

## 🎛️ Configuration Parameters

Key system parameters are defined in `backend/config.py` (or within `get_grib2.py`) and `frontend/js/wind_canvas.js`:

| Parameter | Location | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `GAUSSIAN_SIGMA` | Backend | `1.0` | Standard deviation ($\sigma$) for spatial smoothing filter kernel |
| `KERNEL_SIZE` | Backend | `5x5` | Dimension matrix for Gaussian smoothing convolution |
| `BOUNDS_AMAZON` | Backend | `[-20.0, 10.0, -80.0, -45.0]` | Geographic bounding box $[Lat_{min}, Lat_{max}, Lon_{min}, Lon_{max}]$ |
| `PARTICLE_COUNT` | Frontend | `2500` | Maximum number of simultaneously animated wind particles |
| `FADE_OPACITY` | Frontend | `0.96` | Canvas trail persistence factor for motion-blur particle paths |
| `TARGET_FPS` | Frontend | `60` | Hardware-accelerated frame rate render target |

---

## 📊 Output Artifacts & File Specifications

Each pipeline execution outputs two synchronized static files into the web root directory:

1. **Several Vector PNG Containers (`amazon_[climate_parameter]_[hour].png`):**
   * **Dimensions:** Scalable grid resolution (e.g., $1440 \times 720$ pixels).
   * **Color Encoding:** 
     * **Red Channel ($R$):** Zonal velocity component ($u$, East-West).
     * **Green Channel ($G$):** Meridional velocity component ($v$, North-South).
     * **Blue/Alpha Channels ($B, A$):** Reserved for future scalar overlays (e.g., atmospheric pressure or humidity).

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
git clone [https://github.com/ogogli/DatavizAmz.git](https://github.com/ogogli/DatavizAmz.git)
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
```bash
cp -r frontend/* /var/www/html/datavizamz/
```

### 4. Automation (Cron Job)
Configure a Linux cron task to trigger automated pipeline executions following NOAA publication windows:
```bash
crontab -e
```
Add the daily job definition (configured for **05:30 UTC** to ingest the 00z forecast horizon):
```cron
30 5 * * * /path/to/DatavizAmz/venv/bin/python /path/to/DatavizAmz/backend/get_grib2.py
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
  * **Mac (Homebrew):** 
    ```bash
    brew install eccodes
    pip install cfgrib
    ```
  * **Conda Environment (Recommended for GRIB2 dependencies):**
    ```bash
    conda install -c conda-forge eccodes cfgrib
    ```

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
