(() => {
  const state = { devices: [], locations: [], selectedDevice: null, hours: 24, start: null, end: null, markers: [], lines: [], bounds: [] };
  const $ = (id) => document.getElementById(id);
  const map = L.map('map', { zoomControl: false }).setView([51.1657, 10.4515], 6);
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 19,referrerPolicy:'origin' }).addTo(map);

  const icons = { iphone: '📱', ipad: '▣', mac: '▰', watch: '⌚', airpods: '◉', default: '⌖' };
  const iconFor = (name = '') => Object.entries(icons).find(([key]) => name.toLowerCase().includes(key))?.[1] || icons.default;
  const fmtNumber = (n) => Number(n || 0).toLocaleString();
  const fmtDate = (value) => value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—';
  const fmtRelative = (value) => {
    if (!value) return 'Never';
    const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
    if (seconds < 90) return 'Just now';
    if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)} h ago`;
    return `${Math.round(seconds / 86400)} d ago`;
  };
  const batteryPercent = (level) => level == null ? null : Math.max(0, Math.min(100, Math.round(Number(level) * 100)));

  function toast(message) {
    const el = $('toast');
    el.textContent = message;
    el.classList.add('visible');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => el.classList.remove('visible'), 2600);
  }

  function setBusy(busy) {
    $('refresh-btn').disabled = busy;
    $('live-status').lastChild.textContent = busy ? ' Loading' : ' Ready';
  }

  function switchView(view) {
    document.querySelectorAll('.workspace').forEach((el) => el.classList.toggle('active', el.id === `${view}-view`));
    document.querySelectorAll('[data-view]').forEach((el) => el.classList.toggle('active', el.dataset.view === view));
    $('page-title').textContent = view === 'map' ? 'Overview' : 'Timeline';
    if (view === 'map') setTimeout(() => map.invalidateSize(), 80);
  }

  function closeSidebar() {
    $('sidebar').classList.remove('open');
    $('sidebar-backdrop').classList.remove('visible');
  }

  function renderDevices() {
    $('device-count').textContent = state.devices.length;
    const container = $('devices-list');
    if (!state.devices.length) {
      container.innerHTML = '<div class="empty-inline">No devices recorded yet.</div>';
      return;
    }
    container.innerHTML = state.devices.map((device) => {
      const latest = device.latest_location || {};
      const battery = batteryPercent(latest.battery_level);
      return `<button class="device-card ${state.selectedDevice === device.id ? 'active' : ''}" data-device="${escapeHtml(device.id)}">
        <span class="device-avatar">${iconFor(`${device.name} ${device.device_display_name || ''}`)}</span>
        <span><span class="device-name">${escapeHtml(device.name || 'Unknown device')}</span><span class="device-meta">${escapeHtml(device.device_display_name || 'Apple device')} · ${fmtRelative(device.last_seen)}</span></span>
        <span class="device-side"><i class="device-status"></i>${battery == null ? '' : `<span class="device-meta">${battery}%</span><span class="battery-bar"><i style="width:${battery}%"></i></span>`}</span>
      </button>`;
    }).join('');
    container.querySelectorAll('[data-device]').forEach((button) => button.addEventListener('click', () => {
      state.selectedDevice = state.selectedDevice === button.dataset.device ? null : button.dataset.device;
      renderDevices();
      loadLocations();
      closeSidebar();
    }));
  }

  function clearMap() {
    state.markers.forEach((marker) => map.removeLayer(marker));
    state.lines.forEach((line) => map.removeLayer(line));
    state.markers = [];
    state.lines = [];
    state.bounds = [];
  }

  function renderMap() {
    clearMap();
    const grouped = {};
    state.locations.forEach((loc) => (grouped[loc.device_id] ||= []).push(loc));
    const palette = ['#38bdf8', '#5eead4', '#a78bfa', '#fbbf24', '#fb7185'];
    Object.values(grouped).forEach((items, groupIndex) => {
      items.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
      const color = palette[groupIndex % palette.length];
      const path = items.map((loc) => [loc.latitude, loc.longitude]);
      if (path.length > 1) state.lines.push(L.polyline(path, { color, weight: 4, opacity: .72, lineJoin: 'round' }).addTo(map));
      items.forEach((loc, index) => {
        const latest = index === items.length - 1;
        const marker = L.circleMarker([loc.latitude, loc.longitude], {
          radius: latest ? 9 : 5,
          fillColor: latest ? '#5eead4' : color,
          color: latest ? '#ffffff' : '#dbeafe',
          weight: latest ? 3 : 1.5,
          fillOpacity: .9
        }).addTo(map);
        marker.bindPopup(`<strong>${escapeHtml(deviceName(loc.device_id))}</strong><br>${fmtDate(loc.timestamp)}<br><span style="color:#8f9bb3">Accuracy ${loc.horizontal_accuracy ? `${Math.round(loc.horizontal_accuracy)} m` : 'unknown'}</span>`);
        marker.on('click', () => switchView('map'));
        state.markers.push(marker);
        state.bounds.push([loc.latitude, loc.longitude]);
      });
    });
    $('map-empty').classList.toggle('hidden', state.locations.length > 0);
    $('visible-points').textContent = fmtNumber(state.locations.length);
    if (state.bounds.length) map.fitBounds(state.bounds, { padding: [40, 40], maxZoom: 15 });
  }

  function renderTimeline() {
    const list = $('timeline-list');
    const rows = [...state.locations].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    $('timeline-count').textContent = `${fmtNumber(rows.length)} points`;
    $('timeline-title').textContent = state.selectedDevice ? deviceName(state.selectedDevice) : 'All devices';
    if (!rows.length) {
      list.innerHTML = '<div class="empty-inline">No recorded positions in this time range.</div>';
      return;
    }
    list.innerHTML = rows.map((loc, index) => {
      const date = new Date(loc.timestamp);
      const battery = batteryPercent(loc.battery_level);
      return `<button class="timeline-entry ${index === 0 ? 'latest' : ''}" data-lat="${loc.latitude}" data-lng="${loc.longitude}">
        <span><span class="timeline-time">${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span><span class="timeline-date">${date.toLocaleDateString([], { month: 'short', day: 'numeric' })}</span></span>
        <span class="timeline-rail"><i></i></span>
        <span><span class="timeline-position">${iconFor(deviceName(loc.device_id))} ${escapeHtml(deviceName(loc.device_id))}</span><span class="timeline-detail">${loc.position_type || 'Location'} · ${loc.horizontal_accuracy ? `${Math.round(loc.horizontal_accuracy)} m accuracy` : 'accuracy unknown'}</span></span>
        <span class="timeline-battery">${battery == null ? '' : `${battery}%`}</span>
      </button>`;
    }).join('');
    list.querySelectorAll('.timeline-entry').forEach((entry) => entry.addEventListener('click', () => {
      switchView('map');
      map.setView([Number(entry.dataset.lat), Number(entry.dataset.lng)], 16);
    }));
  }

  function deviceName(id) {
    return state.devices.find((device) => device.id === id)?.name || id || 'Unknown device';
  }

  function updateMetrics(stats) {
    $('metric-devices').textContent = fmtNumber(stats.total_devices);
    $('metric-locations').textContent = fmtNumber(stats.total_locations);
    const latest = stats.devices.map((d) => d.last_seen).filter(Boolean).sort().at(-1);
    $('metric-latest').textContent = latest ? fmtRelative(latest) : '—';
    $('last-refresh').textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  async function loadStatsAndDevices() {
    const [statsResponse, devicesResponse] = await Promise.all([fetch('/api/stats', { cache: 'no-store' }), fetch('/api/devices', { cache: 'no-store' })]);
    if (!statsResponse.ok || !devicesResponse.ok) throw new Error('Could not load dashboard data');
    const stats = await statsResponse.json();
    const devices = await devicesResponse.json();
    const byId = Object.fromEntries(stats.devices.map((item) => [item.id, item]));
    state.devices = devices.map((device) => ({ ...device, ...byId[device.id] }));
    renderDevices();
    updateMetrics(stats);
  }

  function buildLocationUrl() {
    const params = new URLSearchParams({ limit: '5000' });
    if (state.selectedDevice) params.set('device_id', state.selectedDevice);
    if (state.start) params.set('start', state.start);
    else if (state.hours) params.set('hours', String(state.hours));
    if (state.end) params.set('end', state.end);
    return `/api/locations?${params}`;
  }

  async function loadLocations() {
    setBusy(true);
    try {
      const response = await fetch(buildLocationUrl(), { cache: 'no-store' });
      if (!response.ok) throw new Error('Could not load locations');
      state.locations = await response.json();
      renderMap();
      renderTimeline();
    } catch (error) {
      toast(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function refreshAll(showToast = false) {
    setBusy(true);
    try {
      await loadStatsAndDevices();
      await loadLocations();
      if (showToast) toast('Dashboard updated');
    } catch (error) {
      toast(error.message);
    } finally {
      setBusy(false);
    }
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
  }

  document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => switchView(button.dataset.view)));
  document.querySelectorAll('[data-hours]').forEach((button) => button.addEventListener('click', () => {
    document.querySelectorAll('[data-hours]').forEach((el) => el.classList.remove('active'));
    button.classList.add('active');
    state.hours = Number(button.dataset.hours);
    state.start = null;
    state.end = null;
    $('metric-range').textContent = state.hours === 0 ? 'All time' : state.hours === 24 ? '24 hours' : `${state.hours / 24} days`;
    loadLocations();
  }));
  $('apply-range').addEventListener('click', () => {
    state.start = $('start-time').value || null;
    state.end = $('end-time').value || null;
    if (!state.start && !state.end) return toast('Choose a start or end date');
    state.hours = 0;
    document.querySelectorAll('[data-hours]').forEach((el) => el.classList.remove('active'));
    $('metric-range').textContent = 'Custom range';
    loadLocations();
  });
  $('refresh-btn').addEventListener('click', () => refreshAll(true));
  $('mobile-refresh').addEventListener('click', () => refreshAll(true));
  $('fit-map').addEventListener('click', () => state.bounds.length && map.fitBounds(state.bounds, { padding: [40, 40], maxZoom: 15 }));
  $('menu-button').addEventListener('click', () => { $('sidebar').classList.add('open'); $('sidebar-backdrop').classList.add('visible'); });
  $('mobile-devices').addEventListener('click', () => { $('sidebar').classList.add('open'); $('sidebar-backdrop').classList.add('visible'); });
  $('sidebar-close').addEventListener('click', closeSidebar);
  $('sidebar-backdrop').addEventListener('click', closeSidebar);

  refreshAll();
  setInterval(() => refreshAll(false), 5 * 60 * 1000);
})();
