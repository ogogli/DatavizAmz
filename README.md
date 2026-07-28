# DatavizAMZ 🌦️🌐

**Automated, High-Performance WebGIS Engine for Real-Time Meteorological Data**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Framework: MapLibre](https://img.shields.io/badge/Framework-MapLibre-brightgreen.svg)](https://maplibre.org/)

*DatavizAMZ is an open-source WebGIS platform designed to automate the retrieval, processing, and interactive rendering of atmospheric datasets. Optimized for the Amazon Basin with global grid scalability, it features a decoupled architecture for real-time environmental monitoring.*

---

## 🚀 Key Features

* **Automated Data Pipeline:** Programmatically ingests NOAA Global Forecast System (GFS) data via the `Herbie` framework. Applied Gaussian filtering (`σ = 1.0`, `5x5` kernel) and bicubic interpolation smooth out spatial noise without degrading meteorological gradients.
* **Lossless Vector Encoding:** Decomposes wind velocity into Zonal (`u`, East-West) and Meridional (`v`, North-South) vectors, encoding them into normalized **red and green** channels of 16 MB PNG containers.
* **Client-Side Particle Advection:** Animates up to 2,500 wind vectors with trailing fade effects directly in the browser at **60 FPS** using a hardware-accelerated **HTML5 Canvas API**.
* **Zero CORS Overhead:** Co-locates the Python ingestion backend and single-file frontend on the same server instance to eliminate cross-origin request latency.

---

## 🛠️ Architecture and Dataflow

The software executes a decoupled pipeline synchronized with NOAA's synoptic release windows:

* 📥 **1. Automated Ingestion:** Scheduled Python jobs fetch global grids from NOAA/AWS via the Herbie API.
* ⚙️ **2. Backend Processing:** The engine applies Gaussian filters and upscales the matrices.
* 📦 **3. Lossless Encoding:** Matrices are packed into static, lightweight 16 MB PNG graphic assets.
* 🌐 **4. Static Delivery:** A standard web server seamlessly hosts and delivers the processed PNGs.
* 💻 **5. Client Rendering:** The frontend reconstructs the vectors via HTML5 Canvas for fluid 60 FPS animation.

---

## 📋 System Requirements

* **Data Ingestion:** `herbie-data` (Programmatic GRIB2 index parsing & HTTP byte-range retrieval)
* **Processing:** `numpy`, `xarray`, `scipy` (Spatial array operations & Gaussian filtering)
* **Raster Export:** `matplotlib`, `imageio` (Normalized RGB channel encoding to PNG assets)
* **Mapping Engine:** `MapLibre GL JS` (Client-side spatial layers and base map control)
* **Vector Engine:** `HTML5 Canvas API` (Hardware-accelerated particle advection loop)

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

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the Repository
2. Create a Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License & Citation

Distributed under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** License.  
© 2026, **Osvaldo Gogliano Sobrinho**. Official repository: [github.com/ogogli/DatavizAmz](https://github.com/ogogli/DatavizAmz)

---

## 👥 Acknowledgments

* **Study and Research Group in Big Data (WDS)** — University of São Paulo (USP)
* **National Oceanic and Atmospheric Administration (NOAA)** for open meteorological data access.