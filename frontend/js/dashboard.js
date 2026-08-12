// Path configurations
const pngHome = '/pngs';
const metadataUrl = './metadata.json'; // Exported from backend/config.py

// 1. Take system date
const baseDate = new Date();

// 2. Cronjob runs every day at 04:15 UTC
const horaUTC = baseDate.getUTCHours();
const minutoUTC = baseDate.getUTCMinutes();

if (horaUTC < 4 || (horaUTC === 4 && minutoUTC < 15)) {
	// 1 day back at UTC calendar
	baseDate.setUTCDate(baseDate.getUTCDate() - 1);
}

// 3. System clock at 00:00:00 UTC
baseDate.setUTCHours(0, 0, 0, 0);

// Application State Variables
let currentType = 'rain';
let currentFrame = 0;
let isPlaying = true; 
let animationInterval = null;

// Dynamic Configuration Placeholders (Updated via metadata.json)
let totalFrames = 48;
let canvasWidth = 1000;
let canvasHeight = 574;
let zoomLevel;

// Particle System Canvas
const canvasParticles = document.createElement('canvas');
const ctxParticles = canvasParticles.getContext('2d');

let particles = [];
let numParticles;

let windGrid = null;
let windWidth = 0;
let windHeight = 0;

// Helper function to convert 0..360 longitudes to -180..180 for WebGIS
const normalizeLon = (lon) => (lon > 180 ? lon - 360 : lon);

// Parse and extract encoded UV vector fields from raster pixel channels

function processWindImage(imgElement) {
    windWidth = imgElement.naturalWidth;
    windHeight = imgElement.naturalHeight;

    if (windWidth === 0 || windHeight === 0) return;

    const cacheCanvas = document.createElement('canvas');
    cacheCanvas.width = windWidth;
    cacheCanvas.height = windHeight;
    const cacheCtx = cacheCanvas.getContext('2d');
    
    cacheCtx.drawImage(imgElement, 0, 0);
    
    try {
        const imgData = cacheCtx.getImageData(0, 0, windWidth, windHeight).data;
        const tempGrid = new Float32Array(windWidth * windHeight * 2);
        
        for (let i = 0; i < imgData.length; i += 4) {
            const idx = i / 4;
            // Decode packed bytes back into m/s matching backend range [-30, +30] m/s
            const u = ((imgData[i] / 255) * 60) - 30;
            const v = ((imgData[i+1] / 255) * 60) - 30;
            
            tempGrid[idx * 2] = u;
            tempGrid[idx * 2 + 1] = v;
        }
        windGrid = tempGrid;
    } catch (e) {
        console.error("Error decoding wind matrix from image:", e);
    }
}

// Fetch wind frame asset asynchronously
function loadWindFrame(frameIndex) {
    const tempImg = new Image();
    tempImg.crossOrigin = "anonymous";
    tempImg.onload = function() {
        processWindImage(tempImg);
    };
    tempImg.onerror = function() {
        console.error(`Failed to load wind frame: ${frameIndex}`);
    };
    tempImg.src = `.${pngHome}/amazon_wind_${frameIndex}.png?t=` + new Date().getTime();
}

// Main Dashboard Initialization Entry Point
async function initDashboard() {
    let metadata = null;

    try {
        const res = await fetch(metadataUrl);
        if (res.ok) {
            metadata = await res.json();
            console.log("✅ Loaded metadata.json successfully:", metadata);
        } else {
            console.warn("⚠️ Metadata not found. Using default fallback dimensions.");
        }
    } catch (err) {
        console.warn("⚠️ Error loading metadata.json, using defaults:", err);
    }

    // 1. Extract dynamic properties from metadata (or use fallbacks)
    if (metadata) {
        canvasWidth = metadata.canvas.width;
        canvasHeight = metadata.canvas.height;
        numParticles = metadata.canvas.number_particles;
        totalFrames = metadata.forecast.total_frames;
        zoomLevel = metadata.canvas.zoom;
    }

    // Update particle canvas dimensions dynamically
    canvasParticles.width = canvasWidth;
    canvasParticles.height = canvasHeight;

    // Build MapLibre BoundingBox from metadata coordinates [West, South, East, North]
    const lonMin = metadata ? normalizeLon(metadata.bbox.lon_min) : -74.125;
    const lonMax = metadata ? normalizeLon(metadata.bbox.lon_max) : -45.875;
    const latMin = metadata ? metadata.bbox.lat_min : -12.125;
    const latMax = metadata ? metadata.bbox.lat_max : 4.125;

    const boundingBox = [
        [lonMin, latMax], // Top Left
        [lonMax, latMax], // Top Right
        [lonMax, latMin], // Bottom Right
        [lonMin, latMin]  // Bottom Left
    ];

    // Compute center dynamically
    const centerLon = (lonMin + lonMax) / 2;
    const centerLat = (latMin + latMax) / 2;

    // Seed initial particle array states randomly using dynamic canvas dimensions
    particles = [];
    for (let i = 0; i < numParticles; i++) {
        particles.push({
            x: Math.random() * canvasWidth,
            y: Math.random() * canvasHeight,
            age: Math.floor(Math.random() * 80)
        });
    }

    // 2. Initialize MapLibre Engine instance
    const map = new maplibregl.Map({
        container: 'map',
        style: {
            "version": 8,
            "glyphs": "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
            "sources": {
                "satellite": {
                    "type": "raster",
                    "tiles": ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
                    "tileSize": 256
                },
                "openfreemap": {
                    "type": "vector",
                    "tiles": ["https://tile.openstreetmap.jp/data/planet/{z}/{x}/{y}.pbf"]
                }
            },
            "layers": [
                {
                    "id": "satellite-layer",
                    "type": "raster",
                    "source": "satellite",
                    "paint": { "raster-saturation": 0.4, "raster-contrast": 0.2 }
                },
                {
                    "id": "roads",
                    "type": "line",
                    "source": "openfreemap",
                    "source-layer": "transportation",
                    "paint": {
                        "line-color": "#ffffff",
                        "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.5, 12, 1.5],
                        "line-opacity": 0.3
                    }
                },
                {
                    "id": "labels",
                    "type": "symbol",
                    "source": "openfreemap",
                    "source-layer": "place",
                    "layout": {
                        "text-field": "{name:latin}",
                        "text-font": ["Noto Sans Bold"],
                        "text-transform": "uppercase",
                        "text-size": [
                            "case",
                            ["==", ["get", "class"], "state"], 18,
                            ["all", ["==", ["get", "class"], "city"], ["has", "capital"]], 14,
                            10
                        ],
                        "text-letter-spacing": ["match", ["get", "class"], "state", 0.2, 0]
                    },
                    "paint": {
                        "text-color": "#ffff00",
                        "text-halo-color": "rgba(0,0,0,0.8)",
                        "text-halo-width": 1.5
                    }
                }
            ]
        },
        center: [centerLon, centerLat],
        zoom: zoomLevel,
        minZoom: zoomLevel
    });

    // Streamline rendering loop using custom Canvas overlay
    function animateParticles() {
        if (!document.getElementById('wind-checkbox').checked) {
            ctxParticles.clearRect(0, 0, canvasWidth, canvasHeight);
            map.getSource('wind-canvas-source')?.play();
            requestAnimationFrame(animateParticles);
            return;
        }

        ctxParticles.save();
        ctxParticles.globalCompositeOperation = 'destination-out';
        ctxParticles.fillStyle = 'rgba(0, 0, 0, 0.08)'; 
        ctxParticles.fillRect(0, 0, canvasWidth, canvasHeight);

        ctxParticles.globalCompositeOperation = 'screen';
        ctxParticles.lineWidth = 1.5;

        const w = canvasWidth;
        const h = canvasHeight;

        for (let i = 0; i < numParticles; i++) {
            const p = particles[i];
            if (p.age > 80) {
                p.x = Math.random() * w;
                p.y = Math.random() * h;
                p.age = 0;
            }

            let u = 0.0; 
            let v = 0.0;

            if (windGrid && windWidth > 0 && windHeight > 0) {
                const gridX = Math.floor((p.x / w) * windWidth);
                const gridY = Math.floor((p.y / h) * windHeight);

                if (gridX >= 0 && gridX < windWidth && gridY >= 0 && gridY < windHeight) {
                    const gridIdx = (gridY * windWidth + gridX) * 2;
                    u = windGrid[gridIdx];
                    v = windGrid[gridIdx + 1];
                }
            }

            const speedKMH = Math.sqrt(u * u + v * v) * 3.6; // Unit conversion m/s => km/h

            // Assign streamline particle color based on velocity
            let particleColor = 'rgba(102, 255, 102, 0.7)'; 
            if (speedKMH >= 10 && speedKMH < 20) {
                particleColor = 'rgba(51, 153, 255, 0.8)';  
            } else if (speedKMH >= 20 && speedKMH < 30) {
                particleColor = 'rgba(255, 255, 51, 0.85)'; 
            } else if (speedKMH >= 30 && speedKMH < 40) {
                particleColor = 'rgba(255, 153, 51, 0.9)';  
            } else if (speedKMH >= 40 && speedKMH < 50) {
                particleColor = 'rgba(255, 51, 51, 0.95)';  
            } else if (speedKMH >= 50) {
                particleColor = 'rgba(153, 51, 255, 1.0)';  
            }

            const nextX = p.x + (u * 0.25);
            const nextY = p.y - (v * 0.25); 

            ctxParticles.beginPath();
            ctxParticles.strokeStyle = particleColor;
            ctxParticles.moveTo(p.x, p.y);
            ctxParticles.lineTo(nextX, nextY);
            ctxParticles.stroke();

            p.x = nextX;
            p.y = nextY;

            if (p.x < 0 || p.x > w || p.y < 0 || p.y > h) {
                p.x = Math.random() * w;
                p.y = Math.random() * h;
                p.age = 0;
            }
            p.age++;
        }
        ctxParticles.restore();

        map.getSource('wind-canvas-source')?.play();
        requestAnimationFrame(animateParticles);
    }

    // MapLibre Hooks and Event Listeners
    map.on('load', () => {
        map.addSource('weather-source', {
            'type': 'image',
            'url': `.${pngHome}/amazon_rain_0.png`,
            'coordinates': boundingBox
        });

        map.addLayer({
            'id': 'weather-layer', 
            'type': 'raster', 
            'source': 'weather-source',
            'paint': { 
                'raster-opacity': 0.72, 
                'raster-fade-duration': 0,
                'raster-resampling': 'linear'
            }
        });
        map.moveLayer('weather-layer', 'roads');

        map.addSource('wind-canvas-source', {
            'type': 'canvas',
            'canvas': canvasParticles,
            'animate': true,
            'coordinates': boundingBox
        });

        map.addLayer({
            'id': 'wind-canvas-layer', 'type': 'raster', 'source': 'wind-canvas-source',
            'paint': { 'raster-opacity': 0.95, 'raster-fade-duration': 0 }
        });

        animateParticles();

        const slider = document.getElementById('slider');
        if (slider) {
            slider.max = totalFrames - 1; // Sync dynamic max slider frames
        }

        // Core UI Synchronizer
        const updateUI = (index) => {
            currentFrame = parseInt(index);
            const fxx = currentFrame; 
            const validTime = new Date(baseDate.getTime() + fxx * 60 * 60 * 1000);
            
            const day = String(validTime.getUTCDate()).padStart(2, '0');
            const month = String(validTime.getUTCMonth() + 1).padStart(2, '0');
            const hours = String(validTime.getUTCHours()).padStart(2, '0');
            
            document.getElementById('fxx-text').innerText = `Forecast: +${fxx}h`;
            document.getElementById('zulu-text').innerText = `${day}/${month} ${hours}:00Z`;
            document.getElementById('slider').value = currentFrame;
        
            if (currentType !== 'none') {
                map.setLayoutProperty('weather-layer', 'visibility', 'visible');
                map.getSource('weather-source').updateImage({
                    url: `.${pngHome}/amazon_${currentType}_${currentFrame}.png`
                });
            } else {
                map.setLayoutProperty('weather-layer', 'visibility', 'none');
            }

            loadWindFrame(currentFrame);

            const source = map.getSource('wind-canvas-source');
            if (source && source.canvas) {
                source.play(); 
            }
        };            

        // Interface Control Events
        document.getElementById('wind-checkbox').addEventListener('change', (e) => {
            if (e.target.checked) {
                map.setLayoutProperty('wind-canvas-layer', 'visibility', 'visible');
                document.getElementById('legend-wind-particles').style.display = 'block';
            } else {
                map.setLayoutProperty('wind-canvas-layer', 'visibility', 'none');
                document.getElementById('legend-wind-particles').style.display = 'none';
            }
        });

        document.getElementById('layer-type').addEventListener('change', (e) => {
            currentType = e.target.value;
            document.getElementById('legend-rain').style.display = 'none';
            document.getElementById('legend-gust').style.display = 'none';
            document.getElementById('legend-humidity').style.display = 'none';
            document.getElementById('legend-temperature').style.display = 'none';
            
            if (currentType !== 'none') {
                const activeLegend = document.getElementById(`legend-${currentType}`);
                if (activeLegend) activeLegend.style.display = 'block';
            }
            updateUI(currentFrame);
        });

        slider.addEventListener('input', (e) => {
            pauseAnimation();
            updateUI(e.target.value);
        });

        const playPauseBtn = document.getElementById('play-pause-btn');
        
        const startAnimation = () => {
            isPlaying = true;
            playPauseBtn.innerText = "PAUSE";
            playPauseBtn.style.background = "#00e5ff";
            playPauseBtn.style.color = "#000";
            animationInterval = setInterval(() => {
                let nextFrame = (currentFrame + 1) % totalFrames; 
                updateUI(nextFrame);
            }, 2500);
        };

        const pauseAnimation = () => {
            isPlaying = false;
            playPauseBtn.innerText = "PLAY";
            playPauseBtn.style.background = "#222";
            playPauseBtn.style.color = "#fff";
            clearInterval(animationInterval);
        };

        playPauseBtn.addEventListener('click', () => {
            if (isPlaying) pauseAnimation();
            else startAnimation();
        });

        document.getElementById('prev-btn').addEventListener('click', () => {
            pauseAnimation();
            const maxFrames = parseInt(slider.max) + 1;
            let prevFrame = (Number(currentFrame) - 1 + maxFrames) % maxFrames; 
            updateUI(prevFrame);
        });
        
        document.getElementById('next-btn').addEventListener('click', () => {
            pauseAnimation();
            const maxFrames = parseInt(slider.max) + 1;
            let nextFrame = (Number(currentFrame) + 1) % maxFrames; 
            updateUI(nextFrame);
        }); 
        
        updateUI(0);
        startAnimation();
    });
}

// Execute when DOM is ready
document.addEventListener('DOMContentLoaded', initDashboard);
