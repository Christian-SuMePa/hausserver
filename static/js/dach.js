const datePicker = document.getElementById("datePicker");
const rawToggle = document.getElementById("rawToggle");

const tempCtx = document.getElementById("tempChart").getContext("2d");
const humidityCtx = document.getElementById("humidityChart").getContext("2d");

let tempChart;
let humidityChart;

function initCharts() {
  tempChart = new Chart(tempCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Temperatur (°C)",
          data: [],
          borderColor: "#1d4ed8",
          backgroundColor: "rgba(29, 78, 216, 0.1)",
          tension: 0.3,
        },
      ],
    },
  });

  humidityChart = new Chart(humidityCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Luftfeuchtigkeit (%)",
          data: [],
          borderColor: "#0f766e",
          backgroundColor: "rgba(15, 118, 110, 0.1)",
          tension: 0.3,
        },
      ],
    },
    options: {
      scales: {
        y: {
          min: 0,
          max: 100,
        },
      },
    },
  });
}

function formatTimeLabel(ts) {
  const date = new Date(ts);
  return date.toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function updateCharts(data) {
  const labels = data.times.map(formatTimeLabel);
  const source = rawToggle.checked ? data.raw : data.smoothed;

  tempChart.data.labels = labels;
  tempChart.data.datasets[0].data = source.temperature;
  tempChart.update();

  humidityChart.data.labels = labels;
  humidityChart.data.datasets[0].data = source.humidity;
  humidityChart.update();
}

async function loadData() {
  const dateValue = datePicker.value;
  if (!dateValue) return;
  const response = await fetch(`/api/dach?date=${dateValue}`);
  if (!response.ok) {
    console.error("Fehler beim Laden der Daten");
    return;
  }
  const data = await response.json();
  updateCharts(data);
}

function setToday() {
  const today = new Date();
  datePicker.value = today.toISOString().slice(0, 10);
}

initCharts();
setToday();
loadData();

rawToggle.addEventListener("change", loadData);
datePicker.addEventListener("change", loadData);
