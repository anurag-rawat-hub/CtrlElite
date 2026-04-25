/* ============================================================
   AquaYield Dashboard JS
   ============================================================ */

const API_BASE = "http://127.0.0.1:8000/api";

// Chart instances
let tempChart;
let humChart;
let gasChart;



// ── Utility: format time for charts ──
function getFormatTime(isoString) {
  const d = new Date(isoString);
  const pad = n => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ── Initialize Charts ──
function initCharts() {
  Chart.defaults.color = "#7a8fa6";
  Chart.defaults.font.family = "'Inter', sans-serif";

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { 
        grid: { color: "rgba(30,58,74,.6)" },
        ticks: { color: "#7a8fa6" }
      },
      y: { 
        grid: { color: "rgba(30,58,74,.6)" },
        ticks: { color: "#7a8fa6" }
      }
    },
    elements: {
      line: { tension: 0.3 }
    }
  };

  const ctxTemp = document.getElementById('tempChart').getContext('2d');
  tempChart = new Chart(ctxTemp, {
    type: 'line',
    data: { labels: [], datasets: [{ 
      label: 'Temperature °C', 
      data: [], 
      borderColor: '#39d98a', 
      backgroundColor: 'rgba(57,217,138,0.1)',
      borderWidth: 2,
      fill: true 
    }]},
    options: commonOptions
  });

  const ctxHum = document.getElementById('humChart').getContext('2d');
  humChart = new Chart(ctxHum, {
    type: 'line',
    data: { labels: [], datasets: [{ 
      label: 'Humidity %', 
      data: [], 
      borderColor: '#06b6d4', 
      backgroundColor: 'rgba(6,182,212,0.1)',
      borderWidth: 2,
      fill: true 
    }]},
    options: commonOptions
  });

  const ctxGas = document.getElementById('gasChart').getContext('2d');
  gasChart = new Chart(ctxGas, {
    type: 'line',
    data: { labels: [], datasets: [{ 
      label: 'Gas Level (ppm)', 
      data: [], 
      borderColor: '#eab308', 
      backgroundColor: 'rgba(234,179,8,0.1)',
      borderWidth: 2,
      fill: true 
    }]},
    options: commonOptions
  });
}

// ── Fetch Data & Update UI ──
async function fetchUpdate() {
  try {
    const res = await fetch(`${API_BASE}/history/`);
    if (!res.ok) return;
    
    let history = await res.json();
    history = history.reverse();

    if (history.length === 0) return;

    // Prepare chart data
    const labels = history.map(r => getFormatTime(r.timestamp));
    const tempData = history.map(r => parseFloat(r.temperature));
    const humData = history.map(r => parseFloat(r.humidity));
    const gasData = history.map(r => parseFloat(r.gas));

    // Update Charts
    tempChart.data.labels = labels;
    tempChart.data.datasets[0].data = tempData;
    tempChart.update();

    humChart.data.labels = labels;
    humChart.data.datasets[0].data = humData;
    humChart.update();

    gasChart.data.labels = labels;
    gasChart.data.datasets[0].data = gasData;
    gasChart.update();

  } catch (err) {
    console.error("Failed to fetch chart data:", err);
  }
}

// ── Initialization ──
initCharts();
fetchUpdate();
setInterval(fetchUpdate, 5000);

// ── Theme Toggle ──
const themeToggle = document.getElementById('theme-toggle');
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

