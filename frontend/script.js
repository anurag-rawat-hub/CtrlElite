/* ============================================================
   AquaYield Dashboard — Frontend Logic
   Connects to Django backend at http://127.0.0.1:8000
   Endpoints used:
     GET  /api/latest/   — most recent sensor reading
     GET  /api/history/  — last 20 readings
     POST /api/sensor/   — submit new reading (used by ESP32)
   ============================================================ */

const API_BASE = "http://127.0.0.1:8000/api";

// ── DOM refs ─────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const connDot          = $("conn-dot");
const moistureDisplay  = $("moisture-display");
const moistureBadge    = $("moisture-badge");
const badgeText        = $("badge-text");
const detailDevice     = $("detail-device");
const detailTimestamp  = $("detail-timestamp");
const detailTemp       = $("detail-temp");
const detailHum        = $("detail-hum");
const detailGas        = $("detail-gas");
const statusBadge      = $("status-badge");
const irrMm            = $("irr-mm");
const irrPump          = $("irr-pump");
const irrStatusText    = $("irr-status-text");
const irrDevice        = $("irr-device");
const irrPredictedAgo  = $("irr-predicted-ago");
const lastUpdatedText  = $("last-updated-text");
const historyTbody     = $("history-tbody");
const refreshHistoryBtn= $("refresh-history-btn");
const toastEl          = $("toast");

// ── Utility: toast notifications ─────────────────────────────
let toastTimer;
function showToast(msg, isError = false) {
  toastEl.textContent = msg;
  toastEl.className   = "show" + (isError ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastEl.className = ""; }, 3200);
}

// ── Utility: relative time ────────────────────────────────────
function relativeTime(isoString) {
  const diff = Math.floor((Date.now() - new Date(isoString)) / 1000);
  if (diff < 5)  return "just now";
  if (diff < 60) return `${diff} seconds ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
  return `${Math.floor(diff / 3600)} hours ago`;
}

// ── Utility: format datetime ──────────────────────────────────
function formatDateTime(isoString) {
  const d = new Date(isoString);
  const pad = n => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())} / ${pad(d.getDate())}-${pad(d.getMonth()+1)}-${d.getFullYear()}`;
}

// ── Animate number change ─────────────────────────────────────
function animateTo(el, newText) {
  if (el.textContent === newText) return;
  el.classList.remove("tick");
  void el.offsetWidth;            // reflow to restart animation
  el.textContent = newText;
  el.classList.add("tick");
}

// ── Update moisture card ──────────────────────────────────────
let lastTimestamp = null;

function updateMoistureCard(data) {
  const soil = data.soil_moisture;

  // Moisture value
  animateTo(moistureDisplay, `${soil.toFixed(1)}%`);

  // Badge — Optimal moisture if soil > 70%
  const isOptimal = soil > 70;
  moistureBadge.className = "moisture-badge" + (isOptimal ? " good" : "");
  badgeText.textContent   = isOptimal ? "Optimal moisture" : "Needs water";

  // Details
  detailDevice.textContent    = data.device_id || "device_01";
  detailTimestamp.textContent = formatDateTime(data.timestamp);
  detailTemp.textContent      = `${parseFloat(data.temperature).toFixed(1)} °C`;
  detailHum.textContent       = `${parseFloat(data.humidity).toFixed(1)} %`;
  detailGas.textContent       = `${parseFloat(data.gas).toFixed(0)} ppm`;

  lastTimestamp = data.timestamp;
}

// ── Update irrigation card ────────────────────────────────────
let isPumpRunningInUI = false;



function updateIrrigationCard(data) {
  const req     = data.water_flow_req || "–";
  const pump    = parseFloat(data.pump_time_min  ?? 0);
  const hasData = pump > 0;

  // ── EMERGENCY START/STOP FRONTEND TRIGGERS ──
  if (req !== window.lastKnownReq) {
    window.lastKnownReq = req;
    if (req === "Emergency Drought Control") {
      showToast("Emergency Pump Started", true);
    } else if (req === "Emergency Flood Control") {
      showToast("Emergency Pump Stopped", true);
    }
  }

  // ── FIRE ALERT WHEN IRRIGATION FINISHES ──
  if (hasData && !isPumpRunningInUI) {
    isPumpRunningInUI = true;
    
    // In our hardware "demo mode", the ESP32 interprets pump_time_min completely as seconds.
    // We recreate that exact timer in the UI to notify the user right when the physical pump terminates.
    const pumpSecondsDemo = pump; 
    setTimeout(() => {
      showToast(`Pump finished (${pumpSecondsDemo}s)`, false);
      
      // Update UI manually to show Idle
      statusBadge.className = "status-badge pending";
      statusBadge.textContent = "● IDLE";
      irrStatusText.style.color = "var(--warn)";
      irrStatusText.textContent = "Idle ✦";
      
      // Unblock so we can track the next major irrigation cycle
      isPumpRunningInUI = false;
    }, pumpSecondsDemo * 1000);
  }

  animateTo(irrMm,   req);
  animateTo(irrPump, hasData ? `${pump.toFixed(1)} min` : "–");

  // Status
  if (hasData) {
    statusBadge.className     = "status-badge";
    statusBadge.textContent   = "● ON";
    irrStatusText.style.color = "var(--accent)";
    irrStatusText.textContent = "Active ✦";
  } else {
    statusBadge.className     = "status-badge pending";
    statusBadge.textContent   = "● PENDING";
    irrStatusText.style.color = "var(--warn)";
    irrStatusText.textContent = "Pending ✦";
  }

  irrDevice.textContent       = data.device_id || "device_01";
  irrPredictedAgo.textContent = relativeTime(data.timestamp);
  animateTo(lastUpdatedText, "0 seconds ago");

  // Start ticking the "last updated" counter
  startLastUpdatedTicker(data.timestamp);
}

// ── Live "last updated" ticker ────────────────────────────────
let tickerInterval;
function startLastUpdatedTicker(timestamp) {
  clearInterval(tickerInterval);
  tickerInterval = setInterval(() => {
    lastUpdatedText.textContent = relativeTime(timestamp);
    irrPredictedAgo.textContent = relativeTime(timestamp);
  }, 1000);
}

// ── Fetch latest reading ──────────────────────────────────────
async function fetchLatest() {
  try {
    const res = await fetch(`${API_BASE}/latest/`, { cache: "no-store" });

    if (res.status === 404) {
      // No readings in DB yet — show placeholder
      moistureDisplay.textContent = "–";
      badgeText.textContent       = "No data yet";
      setOffline(false);           // backend is up
      return;
    }

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    setOnline();
    updateMoistureCard(data);
    updateIrrigationCard(data);

  } catch (err) {
    setOffline(true);
    showToast("⚡ Cannot reach backend — is Django running?", true);
    console.error("fetchLatest error:", err);
  }
}

// ── Fetch history ─────────────────────────────────────────────
async function fetchHistory() {
  const btn = refreshHistoryBtn;
  btn.classList.add("spinning");

  try {
    const res = await fetch(`${API_BASE}/history/`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const rows = await res.json();

    if (rows.length === 0) {
      historyTbody.innerHTML = `<tr><td colspan="7" class="no-data">No sensor history yet.</td></tr>`;
      return;
    }

    historyTbody.innerHTML = rows.map(r => `
      <tr>
        <td>${formatDateTime(r.timestamp)}</td>
        <td>${r.device_id}</td>
        <td>${parseFloat(r.soil_moisture).toFixed(1)}</td>
        <td>${parseFloat(r.temperature).toFixed(1)}</td>
        <td>${parseFloat(r.humidity).toFixed(1)}</td>
        <td>${r.water_flow_req || "–"}</td>
        <td>${r.pump_time_min != null ? parseFloat(r.pump_time_min).toFixed(1) : "–"}</td>
      </tr>
    `).join("");

    showToast("✓ History refreshed");
  } catch (err) {
    historyTbody.innerHTML = `<tr><td colspan="7" class="no-data">Failed to load history.</td></tr>`;
    showToast("⚡ History load failed", true);
  } finally {
    setTimeout(() => btn.classList.remove("spinning"), 500);
  }
}

// ── Connection indicators ─────────────────────────────────────
function setOnline() {
  connDot.className = "connection-dot";
  connDot.title     = "Backend connected";
}
function setOffline(err = true) {
  connDot.className = err ? "connection-dot offline" : "connection-dot";
  connDot.title     = err ? "Backend unreachable" : "Awaiting data";
}

// ── Refresh history button ────────────────────────────────────
refreshHistoryBtn.addEventListener("click", fetchHistory);

// ── Theme Toggle ──
const themeToggle = $("theme-toggle");
if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    if (currentTheme === 'light') {
      document.documentElement.removeAttribute('data-theme');
      themeToggle.innerText = '☀';
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      themeToggle.innerText = '🌙';
      localStorage.setItem('theme', 'light');
    }
  });

  // Load saved theme
  if (localStorage.getItem('theme') === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    themeToggle.innerText = '🌙';
  }
}

// ── Auto-refresh every 8 seconds ─────────────────────────────
async function refresh() {
  await fetchLatest();
}

// Initial load
refresh();
fetchHistory();

setInterval(refresh, 3000);