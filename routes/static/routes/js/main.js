/* ═════════════════════════════════════════════════════════════
   RouteOptimizer — Main page logic
   Handles: Leaflet map, point CRUD, optimization trigger
═════════════════════════════════════════════════════════════ */

'use strict';

// ── State ────────────────────────────────────────────────────────
const state = {
  points: [],            // [{id, name, address, latitude, longitude}, ...]
  markers: {},           // pointId → L.Marker
  selectedIds: new Set(),
  tempMarker: null,
  clickedCoords: null,
};

// ── Leaflet map ──────────────────────────────────────────────────
const map = L.map('map', { zoomControl: true }).setView([48.5, 31.5], 6);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap &copy; CARTO',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);

// ── DOM refs ────────────────────────────────────────────────────
const pointNameEl   = document.getElementById('pointName');
const pointAddrEl   = document.getElementById('pointAddress');
const pointLatEl    = document.getElementById('pointLat');
const pointLonEl    = document.getElementById('pointLon');
const addPointForm  = document.getElementById('addPointForm');
const pointListEl   = document.getElementById('pointList');
const emptyStateEl  = document.getElementById('emptyState');
const pointCountEl  = document.getElementById('pointCount');
const selCountText  = document.getElementById('selCountText');
const selectAllBtn  = document.getElementById('selectAllBtn');
const optimizeForm  = document.getElementById('optimizeForm');
const optimizeBtn   = document.getElementById('optimizeBtn');
const algoSelect    = document.getElementById('algorithmSelect');
const routeNameEl   = document.getElementById('routeName');
const optimizeErr   = document.getElementById('optimizeError');
const mapHint       = document.getElementById('mapHint');
const optimizeSpin  = document.getElementById('optimizeSpinner');

// ── Toast helper ─────────────────────────────────────────────────
function showToast(msg, isError = false) {
  const toastEl = document.getElementById('liveToast');
  const msgEl   = document.getElementById('toastMsg');
  msgEl.textContent = msg;
  toastEl.className = `toast align-items-center border-0 text-bg-${isError ? 'danger' : 'dark'}`;
  bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 3000 }).show();
}

// ── Custom Leaflet marker ─────────────────────────────────────────
function makeIcon(label = '') {
  return L.divIcon({
    html: `<div class="point-marker-icon"><div class="point-marker-icon-inner">${label}</div></div>`,
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -30],
  });
}

// ── Map click → pre-fill coordinates ─────────────────────────────
map.on('click', (e) => {
  const { lat, lng } = e.latlng;
  state.clickedCoords = { lat, lon: lng };
  pointLatEl.value = lat.toFixed(5);
  pointLonEl.value = lng.toFixed(5);

  // Show temporary marker so user knows where they clicked
  if (state.tempMarker) map.removeLayer(state.tempMarker);
  state.tempMarker = L.marker([lat, lng], {
    icon: L.divIcon({
      html: '<div class="point-marker-icon temp-marker"><div class="point-marker-icon-inner">+</div></div>',
      className: '',
      iconSize: [28, 28],
      iconAnchor: [14, 28],
    }),
    zIndexOffset: -10,
  }).addTo(map);

  mapHint.textContent = `📍 ${lat.toFixed(4)}, ${lng.toFixed(4)} — fill in a name and click Add Point`;
});

// ── Render point list ─────────────────────────────────────────────
function renderPointList() {
  // Clear all items except empty state
  Array.from(pointListEl.children)
    .filter(el => el !== emptyStateEl)
    .forEach(el => el.remove());

  emptyStateEl.style.display = state.points.length === 0 ? '' : 'none';
  pointCountEl.textContent = state.points.length;

  state.points.forEach((pt, idx) => {
    const li = document.createElement('li');
    li.className = `point-item ${state.selectedIds.has(pt.id) ? 'selected' : ''}`;
    li.dataset.id = pt.id;

    li.innerHTML = `
      <input type="checkbox" class="point-check" ${state.selectedIds.has(pt.id) ? 'checked' : ''} />
      <div class="point-info">
        <div class="point-name">${escHtml(pt.name)}</div>
        <div class="point-coords">${pt.latitude.toFixed(4)}, ${pt.longitude.toFixed(4)}</div>
      </div>
      <button class="point-del-btn" title="Remove point">
        <i class="bi bi-x-lg"></i>
      </button>
    `;

    // Toggle selection on click
    li.querySelector('.point-check').addEventListener('change', (e) => {
      if (e.target.checked) state.selectedIds.add(pt.id);
      else state.selectedIds.delete(pt.id);
      updateOptimizeButton();
      li.classList.toggle('selected', e.target.checked);
    });

    li.querySelector('.point-del-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      deletePoint(pt.id);
    });

    // Click anywhere on item to pan map
    li.addEventListener('click', (e) => {
      if (e.target.closest('.point-del-btn') || e.target.closest('.point-check')) return;
      map.setView([pt.latitude, pt.longitude], 10, { animate: true });
    });

    pointListEl.appendChild(li);
  });

  updateOptimizeButton();
}

// ── Render map markers ────────────────────────────────────────────
function renderMarkers() {
  // Remove stale markers
  Object.keys(state.markers).forEach(id => {
    if (!state.points.find(p => p.id == id)) {
      map.removeLayer(state.markers[id]);
      delete state.markers[id];
    }
  });
  // Add missing markers
  state.points.forEach((pt, idx) => {
    if (!state.markers[pt.id]) {
      const marker = L.marker([pt.latitude, pt.longitude], { icon: makeIcon(idx + 1) })
        .addTo(map)
        .bindPopup(`<strong>${escHtml(pt.name)}</strong><br/><small>${pt.latitude.toFixed(4)}, ${pt.longitude.toFixed(4)}</small>`);
      state.markers[pt.id] = marker;
    }
  });
}

// ── Optimize button state ─────────────────────────────────────────
function updateOptimizeButton() {
  const count = state.selectedIds.size;
  selCountText.textContent = `${count} point${count !== 1 ? 's' : ''} selected`;
  optimizeBtn.disabled = count < 2;
  optimizeErr.classList.add('d-none');
}

// ── Fetch all points from API ────────────────────────────────────
async function loadPoints() {
  try {
    const res = await fetch('/api/points/');
    if (!res.ok) throw new Error('Failed to load points');
    const data = await res.json();
    state.points = data;
    // Select all by default
    state.selectedIds = new Set(data.map(p => p.id));
    renderPointList();
    renderMarkers();
  } catch (err) {
    showToast('Could not load saved points.', true);
  }
}

// ── Add point (form submit) ───────────────────────────────────────
addPointForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const body = {
    name: pointNameEl.value.trim(),
    address: pointAddrEl.value.trim(),
    latitude: parseFloat(pointLatEl.value),
    longitude: parseFloat(pointLonEl.value),
  };

  if (!body.name || isNaN(body.latitude) || isNaN(body.longitude)) {
    showToast('Please fill in name and coordinates.', true);
    return;
  }
  if (body.latitude < -90 || body.latitude > 90 || body.longitude < -180 || body.longitude > 180) {
    showToast('Coordinates out of valid range.', true);
    return;
  }

  try {
    const res = await fetch('/api/points/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Server error');
    const pt = await res.json();

    state.points.push(pt);
    state.selectedIds.add(pt.id);
    renderPointList();
    renderMarkers();

    // Remove temp marker
    if (state.tempMarker) { map.removeLayer(state.tempMarker); state.tempMarker = null; }
    mapHint.textContent = '📍 Click map to set coordinates';

    // Reset form
    addPointForm.reset();
    state.clickedCoords = null;

    map.setView([pt.latitude, pt.longitude], 9, { animate: true });
    showToast(`"${pt.name}" added successfully.`);
  } catch (err) {
    showToast('Failed to add point.', true);
  }
});

// ── Delete point ──────────────────────────────────────────────────
async function deletePoint(id) {
  try {
    const res = await fetch(`/api/points/${id}/`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    if (!res.ok && res.status !== 204) throw new Error();

    // Remove marker
    if (state.markers[id]) { map.removeLayer(state.markers[id]); delete state.markers[id]; }
    state.points = state.points.filter(p => p.id !== id);
    state.selectedIds.delete(id);
    renderPointList();
    showToast('Point removed.');
  } catch {
    showToast('Could not delete point.', true);
  }
}

// ── Select / deselect all ─────────────────────────────────────────
let allSelected = true;
selectAllBtn.addEventListener('click', () => {
  allSelected = !allSelected;
  if (allSelected) {
    state.selectedIds = new Set(state.points.map(p => p.id));
    selectAllBtn.textContent = 'All';
  } else {
    state.selectedIds.clear();
    selectAllBtn.textContent = 'None';
  }
  renderPointList();
});

// ── Optimize ──────────────────────────────────────────────────────
optimizeForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  optimizeErr.classList.add('d-none');

  const pointIds = [...state.selectedIds];
  if (pointIds.length < 2) {
    optimizeErr.textContent = 'Select at least 2 delivery points.';
    optimizeErr.classList.remove('d-none');
    return;
  }

  const body = {
    point_ids: pointIds,
    algorithm: algoSelect.value,
    name: routeNameEl.value.trim() || `Route #${Date.now().toString(36).slice(-4).toUpperCase()}`,
  };

  optimizeBtn.disabled = true;
  optimizeSpin.classList.remove('d-none');

  try {
    const res = await fetch('/api/optimize/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Optimization failed');

    window.location.href = `/results/${data.task_id}/`;
  } catch (err) {
    optimizeSpin.classList.add('d-none');
    optimizeBtn.disabled = false;
    optimizeErr.textContent = err.message;
    optimizeErr.classList.remove('d-none');
  }
});

// ── Helpers ───────────────────────────────────────────────────────
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
}

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────────────────────────────────
loadPoints();
