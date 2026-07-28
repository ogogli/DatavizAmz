Markdown
# DatavizAMZ 🌦️🌐

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/) [![License: CC BY 4.0](https://img.shields.io/badge/License-CCBY-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/deed.en) [![Framework: MapLibre](https://img.shields.io/badge/Framework-MapLibre-brightgreen.svg)](https://maplibre.org/)

DatavizAMZ is an open-source, high-performance WebGIS application designed to automate the retrieval, processing, and interactive visualization of meteorological data. Optimized for the Amazon Basin with global grid scalability, the platform provides a lightweight, decoupled architecture for real-time environmental monitoring.

---

## 🚀 Key Features

* **Automated Weather Data Pipeline:** Retrieves numerical weather predictions from NOAA's Global Forecast System (GFS) via the `Herbie` framework. A Gaussian filter (`σ = 1.0`, `5x5` kernel window) and bicubic interpolation are applied to eliminate high-frequency noise and upscale matrix resolution without blocky artifacts.
* **Vector Field Encoding:** Decomposes wind velocity into its Zonal (`u`, East-West) and Meridional (`v`, North-South) components, normalizing them into the **red and green** channels of compact PNG graphic containers.
* **Client-Side Particle Advection:** Renders smooth, fluid wind flow animations with trailing fade effects directly in the client's browser using a hardware-accelerated **HTML5 Canvas API** loop operating at 60 FPS.
* **Unified & Lightweight Architecture:** Co-locates frontend web components (HTML/JS/MapLibre) and backend data ingestion scripts (Python 3) on a single web server (Apache/Nginx) to eliminate Cross-Origin Resource Sharing (CORS) overhead.

---

## 🛠️ System Architecture

The software operates as a decoupled, automated data pipeline synchronized with NOAA's synoptic update cycles (accounting for the standard 3.5 to 4-hour publication latency):

[ NOAA Servers / AWS S3 / GCP ]
│
│ (Automated Cron Job / Herbie API Byte-Range Retrieval)
▼
[ Backend: Python Processing ] ──► Gaussian Filter (σ = 1.0) & Bicubic Interpolation
│
▼
[ Lossless PNG Encoding ]    ──► Generates 16 MB PNG Assets (Scalar & RGB-encoded Vectors)
│
▼
[ Frontend: MapLibre Dashboard ]──► HTML5 Canvas Render & 60 FPS Particle Flow

---

## 📋 Software Requirements

### Backend (Python 3.8+)
The pipeline relies on the following standard utility modules and scientific computing libraries:
* `herbie-data` (Programmatic GRIB2 data discovery and HTTP byte-range retrieval)
* `numpy` & `xarray` (Multidimensional array processing)
* `scipy` (Gaussian spatial filtering)
* `matplotlib` & `imageio` (Raster image processing and PNG export)
* `os`, `sys`, `datetime`, `warnings` (System scheduling and operational utilities)

### Web Hosting & Frontend
* HTTP Web Server (**Apache**, **Nginx**, or equivalent).
* **MapLibre GL JS** (client-side interactive map rendering).
* **HTML5 Canvas API** (hardware-accelerated particle flow vector engine).

---

## 🔧 Installation & Setup

#### Step 1: Clone the Repository
```bash
git clone [https://github.com/ogogli/DatavizAmz.git](https://github.com/ogogli/DatavizAmz.git)
cd DatavizAmz
Step 2: Configure the Backend Environment
We recommend using a virtual environment to manage dependencies cleanly:
Bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
(Ensure your requirements.txt includes: herbie-data, numpy, xarray, scipy, matplotlib, and imageio).
Step 3: Deploy the Dashboard
Move the contents of the frontend/ directory to your web server's public root directory (e.g., /var/www/html/datavizamz).
Step 4: Automate Data Retrieval
To handle NOAA's data processing latency automatically, configure a daily cron job on your Linux environment to trigger the script following publication windows. Open your crontab editor:
Bash
crontab -e
Add the following line to run the automated script daily (configured for 05:30 UTC to fetch the complete 00z forecast horizon):
Bash
30 5 * * * /path/to/DatavizAmz/venv/bin/python /path/to/DatavizAmz/backend/get_grib2.py
(Note: Replace /path/to/DatavizAmz/ with the absolute path on your server).
🤝 Contributing
Contributions to enhance DatavizAMZ are welcome! To contribute:
Fork the Project
Create your Feature Branch (git checkout -b feature/AmazingFeature)
Commit your Changes (git commit -m 'Add some AmazingFeature')
Push to the Branch (git push origin feature/AmazingFeature)
Open a Pull Request
📄 License
This work is licensed under a Creative Commons Attribution 4.0 International License.
© 2026, Osvaldo Gogliano Sobrinho. Available at: https://github.com/ogogli/DatavizAmz
👥 Acknowledgments
Study and Research Group in Big Data (WDS) — University of São Paulo (USP)
National Oceanic and Atmospheric Administration (NOAA) for providing open-access GFS meteorological data.MapLibre GL JS (client-side interactive map rendering).
HTML5 Canvas API (hardware-accelerated particle flow vector engine).
🔧 Installation & Setup
1. Clone the Repository
Bash
git clone [https://github.com/ogogli/DatavizAmz.git](https://github.com/ogogli/DatavizAmz.git)
cd DatavizAmz
2. Configure the Backend Environment
We recommend using a virtual environment to manage dependencies cleanly:
Bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
(Ensure your requirements.txt includes: herbie-data, numpy, xarray, scipy, matplotlib, and imageio).
3. Deploy the Dashboard
Move the contents of the frontend/ directory to your web server's public root directory (e.g., /var/www/html/datavizamz).
4. Automate Data Retrieval
To handle NOAA's data processing latency automatically, configure a daily cron job on your Linux environment to trigger the script following publication windows. Open your crontab editor:
Bash
crontab -e
Add the following line to run the automated script daily (configured for 05:30 UTC to fetch the complete 00z forecast horizon):
Bash
30 5 * * * /path/to/DatavizAmz/venv/bin/python /path/to/DatavizAmz/backend/get_grib2.py
(Note: Replace /path/to/DatavizAmz/ with the absolute path on your server).
🤝 Contributing
Contributions to enhance DatavizAMZ are welcome! To contribute:
Fork the Project
Create your Feature Branch (git checkout -b feature/AmazingFeature)
Commit your Changes (git commit -m 'Add some AmazingFeature')
Push to the Branch (git push origin feature/AmazingFeature)
Open a Pull Request
📄 License
This work is licensed under a Creative Commons Attribution 4.0 International License.
© 2026, Osvaldo Gogliano Sobrinho. Available at: https://github.com/ogogli/DatavizAmz
👥 Acknowledgments
Study and Research Group in Big Data (WDS) — University of São Paulo (USP)
National Oceanic and Atmospheric Administration (NOAA) for providing open-access GFS meteorological data.
