/**
 * Vietnam Motorbike Smart Traffic Assistant - Main Frontend Engine
 * Handles Bilingual i18n, Web Speech STT/TTS, Leaflet Map, Motorbike HUD, and Route Simulation.
 */

// --- GLOBAL STATE ---
let currentLang = localStorage.getItem('traffic_assistant_lang') || 'vi';
let i18nData = {};
let map = null;
let userMarker = null;
let routePolyline = null;
let hazardMarkersLayer = null;
let currentCoords = { lat: 10.8018, lon: 106.7115 }; // Default Hàng Xanh
let isListening = false;
let recognition = null;
let simulationInterval = null;
let currentSimulationStep = 0;
let simulationWaypoints = [];
let lastSpokenHazardId = null;

// --- 1. MULTILINGUAL SUPPORT (i18n) ---
async function loadI18n(lang) {
  try {
    const res = await fetch(`/locales/${lang}.json`);
    i18nData = await res.json();
    currentLang = lang;
    localStorage.setItem('traffic_assistant_lang', lang);
    applyI18n();
  } catch (e) {
    console.error('Failed to load i18n:', e);
  }
}

function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (i18nData[key]) el.textContent = i18nData[key];
  });
  document.getElementById('btn-lang-vi').className =
    currentLang === 'vi'
      ? 'px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white'
      : 'px-2.5 py-1 text-xs font-semibold rounded-md text-gray-400 hover:text-white';
  document.getElementById('btn-lang-en').className =
    currentLang === 'en'
      ? 'px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white'
      : 'px-2.5 py-1 text-xs font-semibold rounded-md text-gray-400 hover:text-white';
}

// --- 2. TEXT-TO-SPEECH (TTS) ---
function speakText(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel(); // Cancel any ongoing speech
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = currentLang === 'vi' ? 'vi-VN' : 'en-US';
  utterance.rate = 1.05;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

// --- 3. SPEECH-TO-TEXT (STT) VIA WEB SPEECH API ---
function setupSpeechRecognition() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    console.warn('Web Speech API is not supported in this browser.');
    document.getElementById('voice-status').textContent = 'Voice recognition unavailable';
    return;
  }

  recognition = new SpeechRec();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = currentLang === 'vi' ? 'vi-VN' : 'en-US';

  recognition.onstart = () => {
    isListening = true;
    document.getElementById('btn-mic').classList.add('mic-listening');
    document.getElementById('voice-indicator').className = 'w-2.5 h-2.5 rounded-full bg-red-500 animate-ping';
    document.getElementById('voice-status').textContent = i18nData['voice_listening'] || 'Đang lắng nghe...';
  };

  recognition.onresult = async (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById('voice-transcript').textContent = `"${transcript}"`;
    await handleVoiceInput(transcript);
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    stopListening();
  };

  recognition.onend = () => {
    stopListening();
  };
}

function toggleListening() {
  if (!recognition) setupSpeechRecognition();
  if (!recognition) {
    alert('Trình duyệt của bạn chưa hỗ trợ Web Speech API. Bạn có thể bấm các nút mẫu phía trên.');
    return;
  }

  if (isListening) {
    recognition.stop();
  } else {
    recognition.lang = currentLang === 'vi' ? 'vi-VN' : 'en-US';
    recognition.start();
  }
}

function stopListening() {
  isListening = false;
  document.getElementById('btn-mic').classList.remove('mic-listening');
  document.getElementById('voice-indicator').className = 'w-2.5 h-2.5 rounded-full bg-gray-500';
  document.getElementById('voice-status').textContent = i18nData['voice_mic_btn'] || 'Nhấn để Nói';
}

// --- 4. HANDLE VOICE COMMAND (NLP PARSING) ---
async function handleVoiceInput(text) {
  document.getElementById('voice-status').textContent = i18nData['voice_processing'] || 'Đang phân tích...';
  try {
    const res = await fetch('/api/v1/voice/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        current_lat: currentCoords.lat,
        current_lon: currentCoords.lon,
        language: currentLang,
      }),
    });
    const data = await res.json();

    // Speak natural response
    speakText(data.voice_response);

    // Act upon Intent
    if (data.intent === 'NAVIGATE' && data.entities.destination) {
      document.getElementById('input-end').value = data.entities.destination;
      if (data.entities.avoid_floods) {
        document.getElementById('cb-avoid-floods').checked = true;
      }
      setTimeout(calculateRoute, 600);
    } else if (data.intent === 'CHECK_HAZARDS' || data.intent === 'CHECK_FLOOD_WEATHER') {
      checkProximity();
    }
  } catch (e) {
    console.error('Error handling voice command:', e);
  } finally {
    stopListening();
  }
}

// --- 5. LEAFLET MAP INITIALIZATION ---
function initMap() {
  map = L.map('map').setView([currentCoords.lat, currentCoords.lon], 14);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);

  hazardMarkersLayer = L.layerGroup().addTo(map);

  // User Marker
  const userIcon = L.divIcon({
    html: '<div style="background-color:#10b981; width:22px; height:22px; border-radius:50%; border:3px solid #ffffff; box-shadow:0 0 10px rgba(16,185,129,0.8);"></div>',
    className: 'custom-user-marker',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });

  userMarker = L.marker([currentCoords.lat, currentCoords.lon], { icon: userIcon })
    .addTo(map)
    .bindPopup('<b>Vị trí của bạn (Xe máy)</b>');

  loadHazardsOnMap();
}

// --- 6. LOAD HAZARDS ON MAP ---
async function loadHazardsOnMap() {
  try {
    const res = await fetch('/api/v1/hazards');
    const data = await res.json();
    hazardMarkersLayer.clearLayers();

    const tbody = document.getElementById('hazards-table-body');
    if (tbody) tbody.innerHTML = '';

    data.hazards.forEach((h) => {
      let color = '#3b82f6';
      let iconText = '🌊';
      if (h.type === 'speed_camera') {
        color = '#ef4444';
        iconText = '📷';
      } else if (h.type === 'speed_limit') {
        color = '#f59e0b';
        iconText = '⚡';
      } else if (h.type === 'traffic_jam') {
        color = '#f97316';
        iconText = '🚗';
      }

      // Add Circle Geofence
      L.circle([h.latitude, h.longitude], {
        radius: h.radius_meters,
        color: color,
        fillColor: color,
        fillOpacity: 0.15,
        weight: 1.5,
      }).addTo(hazardMarkersLayer);

      // Add Marker
      const icon = L.divIcon({
        html: `<div style="background-color:${color}; width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#fff; font-size:13px; border:2px solid #fff; box-shadow:0 2px 6px rgba(0,0,0,0.5);">${iconText}</div>`,
        className: 'custom-hazard-marker',
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      L.marker([h.latitude, h.longitude], { icon: icon })
        .addTo(hazardMarkersLayer)
        .bindPopup(`<b>${h.title}</b><br><span style="font-size:11px;color:#9ca3af;">${h.description}</span>`);

      // Populate Table
      if (tbody) {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-800/50';
        row.innerHTML = `
          <td class="px-4 py-3"><span class="px-2 py-0.5 rounded text-[10px] font-mono" style="background:${color}22; color:${color};">${h.type}</span></td>
          <td class="px-4 py-3 font-medium text-white">${h.title}</td>
          <td class="px-4 py-3 font-mono text-[11px] text-gray-400">${h.latitude.toFixed(4)}, ${h.longitude.toFixed(4)}</td>
          <td class="px-4 py-3">${h.radius_meters}m</td>
          <td class="px-4 py-3 font-bold">${h.speed_limit ? h.speed_limit + ' km/h' : '—'}</td>
          <td class="px-4 py-3">
            <button onclick="focusHazard(${h.latitude}, ${h.longitude})" class="text-blue-400 hover:underline">Xem</button>
          </td>
        `;
        tbody.appendChild(row);
      }
    });
  } catch (e) {
    console.error('Error loading hazards:', e);
  }
}

window.focusHazard = function (lat, lon) {
  switchToTab('map');
  map.setView([lat, lon], 16);
};

// --- 7. ROUTE CALCULATION ---
async function calculateRoute() {
  const avoidFloods = document.getElementById('cb-avoid-floods').checked;
  // Geocode destination simple coordinates if needed
  let endLat = 10.7725;
  let endLon = 106.6980;

  const destText = document.getElementById('input-end').value.toLowerCase();
  if (destText.includes('hàng xanh')) {
    endLat = 10.8018; endLon = 106.7115;
  } else if (destText.includes('sài gòn') || destText.includes('cầu sài gòn')) {
    endLat = 10.7997; endLon = 106.7214;
  } else if (destText.includes('thảo điền')) {
    endLat = 10.8045; endLon = 106.7335;
  }

  try {
    const res = await fetch('/api/v1/routes/directions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_lat: currentCoords.lat,
        start_lon: currentCoords.lon,
        end_lat: endLat,
        end_lon: endLon,
        avoid_floods: avoidFloods,
      }),
    });
    const data = await res.json();

    // Render Stats
    document.getElementById('route-stats').classList.remove('hidden');
    document.getElementById('stat-dist').textContent = `${data.distance_km} km`;
    document.getElementById('stat-time').textContent = `${data.duration_minutes} phút`;
    document.getElementById('route-summary-desc').textContent = data.summary;

    // Draw Polyline
    if (routePolyline) map.removeLayer(routePolyline);
    routePolyline = L.polyline(data.waypoints, {
      color: '#3b82f6',
      weight: 5,
      opacity: 0.85,
    }).addTo(map);

    map.fitBounds(routePolyline.getBounds(), { padding: [50, 50] });

    // Store for simulation
    simulationWaypoints = data.waypoints;

    // Render alerts on route
    renderAlertsList(data.hazards_on_route);
  } catch (e) {
    console.error('Error calculating route:', e);
  }
}

// --- 8. PROXIMITY CHECK & NOTIFICATION BANNER ---
async function checkProximity() {
  try {
    const res = await fetch('/api/v1/hazards/check-proximity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        latitude: currentCoords.lat,
        longitude: currentCoords.lon,
        radius_meters: 300,
      }),
    });
    const data = await res.json();

    const banner = document.getElementById('live-alert-banner');
    const badgeCount = document.getElementById('badge-alert-count');
    badgeCount.textContent = `${data.active_alerts.length} điểm`;

    if (data.has_alert && data.active_alerts.length > 0) {
      const topAlert = data.active_alerts[0];
      banner.classList.remove('hidden', 'bg-blue-950', 'bg-red-950', 'bg-amber-950');

      let bannerBg = 'bg-amber-950 border border-amber-800';
      let icon = '⚠️';
      if (topAlert.severity === 'danger') {
        bannerBg = 'bg-red-950 border border-red-800';
        icon = '🚨';
      }

      banner.className = `rounded-xl p-3.5 flex items-center justify-between text-sm shadow-md transition-all ${bannerBg}`;
      document.getElementById('alert-banner-icon').textContent = icon;
      document.getElementById('alert-banner-title').textContent = topAlert.title;
      document.getElementById('alert-banner-desc').textContent = `${topAlert.speech_announcement} (${topAlert.distance_meters}m)`;

      // Update HUD
      updateHud(topAlert);

      // Speak alert once if new hazard
      if (lastSpokenHazardId !== topAlert.hazard_id) {
        lastSpokenHazardId = topAlert.hazard_id;
        speakText(topAlert.speech_announcement);
      }
    } else {
      banner.classList.add('hidden');
      updateHud(null);
    }
  } catch (e) {
    console.error('Error checking proximity:', e);
  }
}

function updateHud(alert) {
  const pill = document.getElementById('hud-safety-pill');
  const text = document.getElementById('hud-safety-text');
  const icon = document.getElementById('hud-notice-icon');
  const title = document.getElementById('hud-notice-title');
  const desc = document.getElementById('hud-notice-desc');

  if (alert) {
    if (alert.severity === 'danger') {
      pill.className = 'inline-block px-4 py-1.5 rounded-full text-xs font-black tracking-widest uppercase mb-4 bg-red-600 text-white animate-pulse';
      text.textContent = i18nData['hud_status_danger'] || 'NGUY HIỂM';
      icon.textContent = '🚨';
      title.textContent = alert.title;
      title.className = 'text-base font-bold text-red-400';
      desc.textContent = alert.speech_announcement;
    } else {
      pill.className = 'inline-block px-4 py-1.5 rounded-full text-xs font-black tracking-widest uppercase mb-4 bg-amber-600 text-white';
      text.textContent = i18nData['hud_status_warning'] || 'CHÚ Ý';
      icon.textContent = '⚠️';
      title.textContent = alert.title;
      title.className = 'text-base font-bold text-amber-400';
      desc.textContent = alert.speech_announcement;
    }
  } else {
    pill.className = 'inline-block px-4 py-1.5 rounded-full text-xs font-black tracking-widest uppercase mb-4 bg-emerald-600 text-white';
    text.textContent = i18nData['hud_status_safe'] || 'AN TOÀN';
    icon.textContent = '🛡️';
    title.textContent = 'LÀN ĐƯỜNG AN TOÀN';
    title.className = 'text-base font-bold text-emerald-400';
    desc.textContent = 'Không phát hiện camera phạt nguội hay điểm ngập trong phạm vi 300m.';
  }
}

function renderAlertsList(hazards) {
  const container = document.getElementById('alerts-list');
  container.innerHTML = '';
  if (!hazards || hazards.length === 0) {
    container.innerHTML = `<p class="text-xs text-gray-500 italic text-center py-4">${i18nData['no_alerts_nearby'] || 'Vùng an toàn.'}</p>`;
    return;
  }

  hazards.forEach((h) => {
    const card = document.createElement('div');
    const colorClass = h.severity === 'danger' ? 'alert-card-danger' : h.severity === 'warning' ? 'alert-card-warning' : 'alert-card-info';
    card.className = `p-3 rounded-lg text-xs ${colorClass}`;
    card.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-bold text-white">${h.title}</span>
        <span class="font-mono text-[10px] text-gray-400">${h.radius_meters}m</span>
      </div>
      <p class="text-gray-300 mt-1">${h.description}</p>
    `;
    container.appendChild(card);
  });
}

// --- 9. RIDE SIMULATION ENGINE ---
function toggleSimulation() {
  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
    document.getElementById('sim-btn-text').textContent = i18nData['btn_simulate_movement'] || 'Mô Phỏng Chạy Xe';
    document.getElementById('btn-toggle-sim').className = 'w-full bg-emerald-700 hover:bg-emerald-600 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors flex items-center justify-center gap-2';
  } else {
    if (!simulationWaypoints || simulationWaypoints.length === 0) {
      alert('Vui lòng nhấn "Tìm Lộ Trình Xe Máy" trước khi bật mô phỏng.');
      return;
    }
    currentSimulationStep = 0;
    document.getElementById('sim-btn-text').textContent = i18nData['btn_stop_simulation'] || 'Dừng Mô Phỏng';
    document.getElementById('btn-toggle-sim').className = 'w-full bg-red-700 hover:bg-red-600 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors flex items-center justify-center gap-2 animate-pulse';

    simulationInterval = setInterval(() => {
      if (currentSimulationStep >= simulationWaypoints.length) {
        toggleSimulation();
        speakText('Bạn đã đến nơi an toàn!');
        return;
      }
      const pt = simulationWaypoints[currentSimulationStep];
      currentCoords = { lat: pt[0], lon: pt[1] };
      userMarker.setLatLng([pt[0], pt[1]]);
      map.panTo([pt[0], pt[1]], { animate: true });

      // Fluctuate speed around 38-46 km/h
      const simSpeed = Math.floor(38 + Math.random() * 8);
      document.getElementById('hud-speed-val').textContent = simSpeed;

      checkProximity();
      currentSimulationStep++;
    }, 1200);
  }
}

// --- 10. TAB NAVIGATION ---
function switchToTab(tabName) {
  const mapContent = document.getElementById('tab-content-map');
  const hudContent = document.getElementById('tab-content-hud');
  const hazardsContent = document.getElementById('tab-content-hazards');

  const btnMap = document.getElementById('tab-btn-map');
  const btnHud = document.getElementById('tab-btn-hud');
  const btnHazards = document.getElementById('tab-btn-hazards');

  mapContent.classList.add('hidden');
  hudContent.classList.add('hidden');
  hazardsContent.classList.add('hidden');

  btnMap.className = 'py-2.5 border-b-2 border-transparent text-gray-400 hover:text-gray-200 font-medium flex items-center gap-1.5';
  btnHud.className = 'py-2.5 border-b-2 border-transparent text-gray-400 hover:text-gray-200 font-medium flex items-center gap-1.5';
  btnHazards.className = 'py-2.5 border-b-2 border-transparent text-gray-400 hover:text-gray-200 font-medium flex items-center gap-1.5';

  if (tabName === 'map') {
    mapContent.classList.remove('hidden');
    btnMap.className = 'py-2.5 border-b-2 border-blue-500 text-blue-400 font-medium flex items-center gap-1.5';
    setTimeout(() => map && map.invalidateSize(), 100);
  } else if (tabName === 'hud') {
    hudContent.classList.remove('hidden');
    btnHud.className = 'py-2.5 border-b-2 border-blue-500 text-blue-400 font-medium flex items-center gap-1.5';
  } else if (tabName === 'hazards') {
    hazardsContent.classList.remove('hidden');
    btnHazards.className = 'py-2.5 border-b-2 border-blue-500 text-blue-400 font-medium flex items-center gap-1.5';
  }
}

// --- 11. INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
  loadI18n(currentLang);
  initMap();

  document.getElementById('btn-lang-vi').addEventListener('click', () => loadI18n('vi'));
  document.getElementById('btn-lang-en').addEventListener('click', () => loadI18n('en'));

  document.getElementById('tab-btn-map').addEventListener('click', () => switchToTab('map'));
  document.getElementById('tab-btn-hud').addEventListener('click', () => switchToTab('hud'));
  document.getElementById('tab-btn-hazards').addEventListener('click', () => switchToTab('hazards'));

  document.getElementById('btn-mic').addEventListener('click', toggleListening);
  document.getElementById('btn-calc-route').addEventListener('click', calculateRoute);
  document.getElementById('btn-toggle-sim').addEventListener('click', toggleSimulation);

  document.getElementById('btn-replay-speech').addEventListener('click', () => {
    const text = document.getElementById('alert-banner-desc').textContent;
    speakText(text);
  });

  // Voice Chips
  document.querySelectorAll('.voice-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const text = chip.getAttribute('data-text');
      document.getElementById('voice-transcript').textContent = `"${text}"`;
      handleVoiceInput(text);
    });
  });

  // HUD Quick Thumb Buttons
  document.getElementById('hud-btn-camera').addEventListener('click', () => {
    handleVoiceInput('Phía trước có camera phạt nguội không?');
  });
  document.getElementById('hud-btn-flood').addEventListener('click', () => {
    handleVoiceInput('Đoạn này có điểm ngập nước không?');
  });
  document.getElementById('hud-btn-report').addEventListener('click', () => {
    handleVoiceInput('Báo cáo tắc đường tại vị trí hiện tại');
  });

  // Filter Hazards
  document.getElementById('filter-hazard-type').addEventListener('change', (e) => {
    // Reload with query
    loadHazardsOnMap();
  });
});
