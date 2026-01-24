const warningBox = document.getElementById("warningBox");

const maxTemp = document.getElementById("maxTemp");
const minTemp = document.getElementById("minTemp");
const sunDuration = document.getElementById("sunDuration");
const weatherSymbol = document.getElementById("weatherSymbol");

const tempCtx = document.getElementById("forecastTemp").getContext("2d");
const precipCtx = document.getElementById("forecastPrecip").getContext("2d");
const windCtx = document.getElementById("forecastWind").getContext("2d");

let tempChart;
let precipChart;
let windChart;

function formatDateLabel(ts) {
  const date = new Date(ts);
  return date.toLocaleString("de-DE", { hour: "2-digit", day: "2-digit", month: "2-digit" });
}

function warningLevel(severity) {
  const severityLower = severity.toLowerCase();
  if (severityLower.includes("extreme") || severityLower.includes("severe")) {
    return "warning-high";
  }
  if (severityLower.includes("moderate") || severityLower.includes("minor")) {
    return "warning-medium";
  }
  return "warning-medium";
}

function renderWarnings(warnings) {
  warningBox.innerHTML = "";
  if (!warnings.length) {
    const info = document.createElement("div");
    info.className = "warning-box warning-none";
    info.textContent = "Keine aktuellen Wetterwarnungen";
    warningBox.appendChild(info);
    return;
  }
  warnings.forEach((warn) => {
    const box = document.createElement("div");
    box.className = `warning-box ${warningLevel(warn.severity)}`;
    box.innerHTML = `<strong>⚠️ ${warn.headline}</strong><br>${warn.onset} – ${warn.expires}<br>${warn.description}`;
    warningBox.appendChild(box);
  });
}

function renderSummary(summary) {
  maxTemp.textContent = summary.max_temp !== null ? `${summary.max_temp} °C` : "—";
  minTemp.textContent = summary.min_temp !== null ? `${summary.min_temp} °C` : "—";
  sunDuration.textContent = summary.sunshine_hours !== null ? `${summary.sunshine_hours} h` : "—";
  weatherSymbol.textContent = summary.weather_symbol || "—";
}

function initCharts() {
  tempChart = new Chart(tempCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Temperatur (°C)",
          data: [],
          borderColor: "#ef4444",
          tension: 0.3,
        },
        {
          label: "Wetter",
          data: [],
          pointStyle: "circle",
          showLine: false,
        },
      ],
    },
  });

  precipChart = new Chart(precipCtx, {
    data: {
      labels: [],
      datasets: [
        {
          type: "bar",
          label: "Niederschlagswahrscheinlichkeit (%)",
          data: [],
          backgroundColor: "rgba(59, 130, 246, 0.5)",
          yAxisID: "y",
        },
        {
          type: "line",
          label: "Niederschlagsmenge (mm)",
          data: [],
          borderColor: "#1e3a8a",
          yAxisID: "y1",
        },
      ],
    },
    options: {
      scales: {
        y: {
          min: 0,
          max: 100,
          position: "left",
        },
        y1: {
          min: 0,
          position: "right",
          grid: {
            drawOnChartArea: false,
          },
        },
      },
    },
  });

  windChart = new Chart(windCtx, {
    data: {
      labels: [],
      datasets: [
        {
          type: "line",
          label: "Windstärke (m/s)",
          data: [],
          borderColor: "#0f766e",
        },
        {
          type: "scatter",
          label: "Windrichtung",
          data: [],
          pointStyle: "triangle",
          pointRadius: 6,
          showLine: false,
        },
      ],
    },
  });
}

function updateCharts(hourly) {
  const labels = hourly.map((entry) => formatDateLabel(entry.time));
  tempChart.data.labels = labels;
  tempChart.data.datasets[0].data = hourly.map((entry) => entry.temperature_c);
  tempChart.data.datasets[1].data = hourly.map((entry) => ({
    x: formatDateLabel(entry.time),
    y: entry.temperature_c,
  }));
  tempChart.update();

  precipChart.data.labels = labels;
  precipChart.data.datasets[0].data = hourly.map((entry) => entry.precip_probability);
  precipChart.data.datasets[1].data = hourly.map((entry) => entry.precip_amount);
  precipChart.update();

  windChart.data.labels = labels;
  windChart.data.datasets[0].data = hourly.map((entry) => entry.wind_speed);
  windChart.data.datasets[1].data = hourly.map((entry, idx) => ({
    x: labels[idx],
    y: entry.wind_speed,
    rotation: entry.wind_direction || 0,
  }));
  windChart.update();
}

async function loadWeather() {
  const response = await fetch("/api/wetter");
  if (!response.ok) {
    console.error("Wetterdaten konnten nicht geladen werden");
    return;
  }
  const data = await response.json();
  renderWarnings(data.warnings);
  renderSummary(data.today_summary || {});
  updateCharts(data.hourly || []);
}

initCharts();
loadWeather();
