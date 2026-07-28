Markdown
<div align="center">

# DatavizAMZ 🌦️🌐

**Automated, High-Performance WebGIS Engine for Real-Time Meteorological Data**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Framework: MapLibre](https://img.shields.io/badge/Framework-MapLibre-brightgreen.svg)](https://maplibre.org/)

*DatavizAMZ is an open-source WebGIS platform designed to automate the retrieval, processing, and interactive rendering of atmospheric datasets. Optimized for the Amazon Basin with global grid scalability, it features a decoupled architecture for real-time environmental monitoring.*

</div>

---

## 🚀 Key Features

* **Automated Data Pipeline:** Programmatically ingests NOAA Global Forecast System (GFS) data via the `Herbie` framework. Applied Gaussian filtering (`σ = 1.0`, `5x5` kernel) and bicubic interpolation smooth out spatial noise without degrading meteorological gradients.
* **Lossless Vector Encoding:** Decomposes wind velocity into Zonal (`u`, East-West) and Meridional (`v`, North-South) vectors, encoding them into normalized **red and green** channels of 16 MB PNG containers.
* **Client-Side Particle Advection:** Animates up to 2,500 wind vectors with trailing fade effects directly in the browser at **60 FPS** using a hardware-accelerated **HTML5 Canvas API**.
* **Zero CORS Overhead:** Co-locates the Python ingestion backend and single-file frontend on the same server instance to eliminate cross-origin request latency.

---

## 🛠️ Architecture and Dataflow

The software executes a decoupled pipeline synchronized with NOAA's synoptic release windows:


```mermaid
flowchart TD
    A[NOAA Servers and Cloud Mirrors] -->|Automated Ingestion| B[Backend Python Engine]
    B -->|Gaussian Filter and Upscaling| C[PNG Encoding Module]
    C -->|Lossless PNG Assets| D[Web Server Repository]
    D -->|Static HTTP Delivery| E[Frontend MapLibre Engine]
    E -->|HTML5 Canvas Rendering| F[Interactive Dashboard]
📋 System Requirements
Component	Technology	Purpose
Data Ingestion	herbie-data	Programmatic GRIB2 index parsing & HTTP byte-range retrieval
Processing	numpy, xarray, scipy	Spatial array operations & Gaussian filtering
Raster Export	matplotlib, imageio	Normalized RGB channel encoding to PNG assets
Mapping Engine	MapLibre GL JS	Client-side spatial layers and base map control
Vector Engine	HTML5 Canvas API	Hardware-accelerated particle advection loop
🔧 Installation & Setup
1. Repository Setup
Bash
git clone [https://github.com/ogogli/DatavizAmz.git](https://github.com/ogogli/DatavizAmz.git)
cd DatavizAmz
2. Environment Configuration
Create and activate an isolated Python virtual environment:
Bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Note: Ensure requirements.txt contains herbie-data, numpy, xarray, scipy, matplotlib, and imageio.
3. Frontend Deployment
Copy the contents of the frontend/ directory to your web server's public root:
Bash
cp -r frontend/* /var/www/html/datavizamz/
4. Automation (Cron Job)
Configure a Linux cron task to trigger automated pipeline executions following NOAA publication windows:
Bash
crontab -e
Add the daily job definition (configured for 05:30 UTC to ingest the 00z forecast horizon):
Snippet de código
30 5 * * * /path/to/DatavizAmz/venv/bin/python /path/to/DatavizAmz/backend/get_grib2.py
🤝 Contributing
Contributions are welcome! Please follow these steps:
Fork the Repository
Create a Feature Branch (git checkout -b feature/AmazingFeature)
Commit your Changes (git commit -m 'Add AmazingFeature')
Push to the Branch (git push origin feature/AmazingFeature)
Open a Pull Request
📄 License & Citation
Distributed under the Creative Commons Attribution 4.0 International (CC BY 4.0) License.
© 2026, Osvaldo Gogliano Sobrinho. Official repository: github.com/ogogli/DatavizAmz
👥 Acknowledgments
Study and Research Group in Big Data (WDS) — University of São Paulo (USP)
National Oceanic and Atmospheric Administration (NOAA) for open meteorological data access.Vector Engine	HTML5 Canvas API	Hardware-accelerated particle advection loop
🔧 Installation & Setup
1. Repository Setup
Bash
git clone [https://github.com/ogogli/DatavizAmz.git](https://github.com/ogogli/DatavizAmz.git)
cd DatavizAmz
2. Environment Configuration
Create and activate an isolated Python virtual environment:
Bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Note: Ensure requirements.txt contains herbie-data, numpy, xarray, scipy, matplotlib, and imageio.
3. Frontend Deployment
Copy the contents of the frontend/ directory to your web server's public root:
Bash
cp -r frontend/* /var/www/html/datavizamz/
4. Automation (Cron Job)
Configure a Linux cron task to trigger automated pipeline executions following NOAA publication windows:
Bash
crontab -e
Add the daily job definition (configured for 05:30 UTC to ingest the 00z forecast horizon):
Snippet de código
30 5 * * * /path/to/DatavizAmz/venv/bin/python /path/to/DatavizAmz/backend/get_grib2.py
🤝 Contributing
Contributions are welcome! Please follow these steps:
Fork the Repository
Create a Feature Branch (git checkout -b feature/AmazingFeature)
Commit your Changes (git commit -m 'Add AmazingFeature')
Push to the Branch (git push origin feature/AmazingFeature)
Open a Pull Request
📄 License & Citation
Distributed under the Creative Commons Attribution 4.0 International (CC BY 4.0) License.
© 2026, Osvaldo Gogliano Sobrinho. Official repository: github.com/ogogli/DatavizAmz
👥 Acknowledgments
Study and Research Group in Big Data (WDS) — University of São Paulo (USP)
National Oceanic and Atmospheric Administration (NOAA) for open meteorological data access.
