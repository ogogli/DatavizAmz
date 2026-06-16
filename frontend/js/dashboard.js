// Set the PNG files directory 
const pngHome = 'YOUR PNG DIRECTORY HERE'

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

let currentType = 'rain';
let currentFrame = 0;
let isPlaying = true; 
let animationInterval = null;

// Particle System Canvas Definition
const canvasParticles = document.createElement('canvas');
canvasParticles.width = 1000;
canvasParticles.height = 574;
const ctxParticles = canvasParticles.getContext('2d');

let particles = [];
const numParticles = 2500;

let windGrid = null;
let windWidth = 0;
let windHeight = 0;

// Bounding Box Definition: Array containing the 4 geographic corners for MapLibre projection
const boundingBox = [
	[-74.125, 4.125],   // Top Left
	[-45.875, 4.125],   // Top Right
	[-45.875, -12.125], // Bottom Right
	[-74.125, -12.125]  // Bottom Left
];

// Seed initial particle array states randomly
for (let i = 0; i < numParticles; i++) {
	particles.push({
		x: Math.random() * 1000,
		y: Math.random() * 574,
		age: Math.floor(Math.random() * 80)
	});
}

// Initialize MapLibre Engine instance
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
	// THE FOLLOWING 3 PARAMETERS ARE SPECIFIC FOR THE REGION ANALYZED, CHANGE IT IF NECESSARY
	center: [-59.995, -4.0],
	zoom: 5.5,
	minZoom: 5.5
});

// Parse and extract encoded UV vector fields from raster pixel channels
function processWindImage(imgElement) {
	windWidth = imgElement.naturalWidth;
	windHeight = imgElement.naturalHeight;

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
			// Decode packed bytes back into m/s or scaled velocity values
			const u = ((imgData[i] / 255) * 80) - 40;
			const v = ((imgData[i+1] / 255) * 80) - 40;
			
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
	tempImg.src = `.${pngHome}/amazon_wind_${frameIndex}.png?t=` + new Date().getTime();
}

// Streamline rendering loop using custom Canvas overlay
function animateParticles() {
	if (!document.getElementById('wind-checkbox').checked) {
		ctxParticles.clearRect(0, 0, 1000, 574);
		map.getSource('wind-canvas-source')?.play();
		requestAnimationFrame(animateParticles);
		return;
	}

	ctxParticles.save();
	ctxParticles.globalCompositeOperation = 'destination-out';
	ctxParticles.fillStyle = 'rgba(0, 0, 0, 0.08)'; 
	ctxParticles.fillRect(0, 0, 1000, 574);

	ctxParticles.globalCompositeOperation = 'screen';
	ctxParticles.lineWidth = 1.5;

	const w = 1000;
	const h = 574;

	for (let i = 0; i < numParticles; i++) {
		const p = particles[i];
		if (p.age > 80) {
			p.x = Math.random() * w;
			p.y = Math.random() * h;
			p.age = 0;
		}

		let u = 2.0; 
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

		// Assign streamline particle hue based on absolute scalar velocity
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

		const nextX = p.x + (u * 0.12);
		const nextY = p.y - (v * 0.12); 

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
		'url': '.${pngHome}/amazon_rain_0.png',
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

	const slider = document.getElementById('slider');
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
			let nextFrame = (currentFrame + 1) % 48; 
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

