/* ═════════════════════════════════════════════════════════════
   RouteOptimizer — Results page logic
   Handles: route map rendering, algorithm switcher, Chart.js comparison
═════════════════════════════════════════════════════════════ */

'use strict';

// ── Parse task data from embedded JSON ───────────────────────────
const taskData = JSON.parse(document.getElementById('taskDataEl').textContent);

// ── Leaflet map ───────────────────────────────────────────────────
const map = L.map('map', { zoomControl: true });

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap &copy; CARTO',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);

// ── State ─────────────────────────────────────────────────────────
let currentPolyline = null;
let currentMarkers  = [];

// ── Draw a route path on the map ──────────────────────────────────
function drawRoute(path, color = '#00d4ff') {
  // Clean up previous layers
  if (currentPolyline) { map.removeLayer(currentPolyline); currentPolyline = null; }
  currentMarkers.forEach(m => map.removeLayer(m));
  currentMarkers = [];

  if (!path || path.length < 2) return;

  const coords = path.map(p => [p.lat, p.lon]);

  // Animated polyline
  currentPolyline = L.polyline(coords, {
    color,
    weight: 3.5,
    opacity: 0.9,
    smoothFactor: 1,
    dashArray: null,
  }).addTo(map);

  // Direction arrows (decorative dashes)
  L.polyline(coords, {
    color,
    weight: 1.5,
    opacity: 0.35,
    dashArray: '6 14',
  }).addTo(map);

  // Numbered markers (skip last point — it's the duplicate start)
  const stops = path.slice(0, -1);
  stops.forEach((pt, i) => {
    const isStart = i === 0;
    const markerHtml = `<div class="route-num-marker ${isStart ? 'route-num-start' : 'route-num-mid'}">${i + 1}</div>`;
    const icon = L.divIcon({
      html: markerHtml,
      className: '',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -16],
    });

    const m = L.marker([pt.lat, pt.lon], { icon })
      .addTo(map)
      .bindPopup(`
        <strong style="color:#00d4ff">${i + 1}. ${pt.name}</strong>
        <br/><small style="color:#6b7a99">${pt.lat.toFixed(4)}, ${pt.lon.toFixed(4)}</small>
        ${isStart ? '<br/><small style="color:#ff6b35">⚑ Start / End</small>' : ''}
      `);
    currentMarkers.push(m);
  });

  // Fit map bounds
  map.fitBounds(currentPolyline.getBounds(), { padding: [30, 30] });
}

// ── Initial draw ──────────────────────────────────────────────────
drawRoute(taskData.path);

// ── Algorithm switcher (only present for "all" tasks) ─────────────
const algoSwitcher = document.getElementById('algoSwitcher');
if (algoSwitcher) {
  const algoColors = { nn: '#00d4ff', '2opt': '#ff6b35', aco: '#64dc8c', best: '#00d4ff' };

  algoSwitcher.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-algo]');
    if (!btn) return;

    const algo = btn.dataset.algo;
    algoSwitcher.querySelectorAll('[data-algo]').forEach(b => {
      b.className = 'btn btn-xs btn-outline-secondary';
    });
    btn.className = 'btn btn-xs btn-accent';

    const color = algoColors[algo] || '#00d4ff';

    if (algo === 'best') {
      drawRoute(taskData.path, color);
    } else if (taskData.benchmarks && taskData.benchmarks[algo]) {
      drawRoute(taskData.benchmarks[algo].path, color);
    }
  });
}

// ── Comparison chart + cards (only for "all") ─────────────────────
if (taskData.algorithm === 'all' && taskData.benchmarks) {
  const bm = taskData.benchmarks;
  const algos = ['nn', '2opt', 'aco'];
  const labels = algos.map(k => bm[k]?.label || k);
  const distances = algos.map(k => bm[k]?.distance ?? 0);
  const times = algos.map(k => bm[k]?.execution_time ?? 0);

  // Find best (lowest distance)
  const minDist = Math.min(...distances);

  // ── Metric cards ──────────────────────────────────────────────
  const cardsEl = document.getElementById('comparisonCards');
  if (cardsEl) {
    algos.forEach((k, i) => {
      const isBest = distances[i] === minDist;
      cardsEl.innerHTML += `
        <div class="comp-card ${isBest ? 'best' : ''}">
          <div class="comp-card-title">
            ${labels[i]}
            ${isBest ? '<span class="best-tag">BEST</span>' : ''}
          </div>
          <div class="comp-card-dist">${distances[i].toFixed(1)} km</div>
          <div class="comp-card-time">Computed in ${times[i].toFixed(4)} s</div>
        </div>
      `;
    });
  }

  // ── Chart.js bar chart ────────────────────────────────────────
  const chartCanvas = document.getElementById('comparisonChart');
  if (chartCanvas && window.Chart) {
    const chartColors = ['#00d4ff', '#ff6b35', '#64dc8c'];

    new Chart(chartCanvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Distance (km)',
            data: distances,
            backgroundColor: algos.map((_, i) => chartColors[i] + '99'),
            borderColor: algos.map((_, i) => chartColors[i]),
            borderWidth: 2,
            borderRadius: 5,
            yAxisID: 'yDist',
          },
          {
            label: 'Time (s)',
            data: times,
            backgroundColor: algos.map(() => 'rgba(180,100,255,0.4)'),
            borderColor: algos.map(() => '#b464ff'),
            borderWidth: 2,
            borderRadius: 5,
            yAxisID: 'yTime',
            type: 'bar',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: '#e0e6f0', font: { size: 12 } },
          },
          tooltip: {
            backgroundColor: '#1e2540',
            titleColor: '#e0e6f0',
            bodyColor: '#6b7a99',
            borderColor: '#2a3155',
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: { color: '#e0e6f0', font: { size: 12 } },
            grid: { color: 'rgba(42,49,85,0.5)' },
          },
          yDist: {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'Distance (km)', color: '#00d4ff' },
            ticks: { color: '#00d4ff' },
            grid: { color: 'rgba(42,49,85,0.5)' },
          },
          yTime: {
            type: 'linear',
            position: 'right',
            title: { display: true, text: 'Time (s)', color: '#b464ff' },
            ticks: { color: '#b464ff' },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  }
}
