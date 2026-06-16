# DatavizAmz

Markdown
# DatavizAMZ 🌦️🌐

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: MapLibre](https://img.shields.io/badge/Framework-MapLibre-brightgreen.svg)](https://maplibre.org/)

DatavizAMZ is an open-source, high-performance WebGIS application designed to automate the retrieval, processing, and interactive visualization of meteorological data. The platform serves as a flexible architecture for environmental monitoring.

---

## 🚀 Key Features

* **Weather Data:** Retrieve weather data from NOAA's Global Forecast System (GFS) via the Herbie package. A Gaussian filter  and Cubic interpolation are used to mitigate high-frequency noise and upscale the data matrices.
* **Vector Field Visualizations:** Encodes North-South ($u$) and East-West ($v$) wind velocity components directly into the red and blue color channels of PNG files, enabling real-time particle advection via GPU on the client side.
* **Unified & Lightweight Architecture:** Both frontend components (HTML/JS/MapLibre) and backend scripts (Python 3) can be co-located on a single standard web server (Apache/Nginx).

---

## 🛠️ System Architecture

The software operates under a decoupled, automated data pipeline synchronized with NOAA's synoptic update cycles (accounting for the standard 3.5 to 4-hour publication latency):

[ NOAA Servers / AWS S3 ]
│ (Automated Cron Job / Herbie API Retrieval)
▼
[ Backend: Python 3 Processing ] ──► Gaussian Filter & Bicubic Interpolation
│
▼
[ Matrix Exportation ] ──► Generates PNG files (Scalar Layers & RGB-encoded Wind Vectors)
│
▼
[ Frontend: MapLibre Dashboard ] ──► Real-time rendering & Fluid particle advection

---

## 📋 Software Requirements

### Backend (Python 3.8+)
The pipeline relies on the following standard utility modules and scientific libraries:
* `herbie` (Data discovery and retrieval)
* `numpy` & `xarray` (Multidimensional matrix manipulation)
* `matplotlib` & `imageio` (Image processing and PNG exportation)
* `os`, `sys`, `datetime`, `warnings` (System and scheduling utilities)

### Web Hosting & Frontend
* An HTTP Web Server (**Apache**, **Nginx**, or equivalent).
* **MapLibre GL JS** framework (loaded client-side for interactive map rendering).

---

## 🔧 Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/DatavizAMZ.git](https://github.com/your-username/DatavizAMZ.git)
cd DatavizAMZ

2. Configure the Backend Environment
We recommend using a virtual environment to manage dependencies:
Bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
(Make sure your requirements.txt includes: herbie, numpy, xarray, matplotlib, imageio)

3. Deploy the Dashboard
Move the contents of the frontend/ directory to your web server's root directory (e.g., /var/www/html/datavizamz).

4. Automate Data Retrieval
To bypass NOAA's data processing latency, configure a daily cron job on your Linux environment to trigger the script strictly after the submission completion windows. Open your crontab configuration:
Bash
crontab -e
Add the following line to run the automated script daily (example configured for 05:30 UTC to download the complete 00z forecast horizon):
Bash
30 5 * * * /path/to/DatavizAMZ/venv/bin/python /path/to/DatavizAMZ/backend/download_pipeline.py

🤝 Contributing
Any contributions you make to enhance DatavizAMZ are greatly appreciated.
Fork the Project
Create your Feature Branch (git checkout -b feature/AmazingFeature)
Commit your Changes (git commit -m 'Add some AmazingFeature')
Push to the Branch (git push origin feature/AmazingFeature)
Open a Pull Request

📄 License
Distributed under the MIT License. See LICENSE for more information.

👥 Acknowledgments
Study and Research Group in Big Data (WDS) — University of São Paulo (USP)
National Oceanic and Atmospheric Administration (NOAA) for open-access data.
