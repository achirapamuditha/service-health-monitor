"use strict";

// ---------- State ----------
var charts = {};              // Chart.js objects, so we update them instead of recreating
var statusFilter = "all";
var severityFilter = "all";
var latest = null;            // last data received from /api/summary
var REFRESH_MS = 5000;

// ---------- Helpers ----------
function esc(value) {
  // Escape text before putting it into HTML (prevents XSS)
  if (value === null || value === undefined) { return ""; }
  return String(value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function cssClass(value) {
  return String(value || "unknown").toLowerCase().replace(/[^a-z]/g, "");
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

// ---------- Loading data ----------
async function loadSummary() {
  try {
    var response = await fetch("/api/summary");
    if (!response.ok) { throw new Error("HTTP " + response.status); }
    latest = await response.json();
    render(latest);
    setConnection(true);
  } catch (error) {
    setConnection(false);
  }
}

function setConnection(ok) {
  var el = document.getElementById("connection");
  el.textContent = ok ? "live" : "offline";
  el.className = "conn " + (ok ? "ok" : "bad");
}

async function postAction(url) {
  try {
    var response = await fetch(url, { method: "POST" });
    if (!response.ok) { throw new Error("HTTP " + response.status); }
  } catch (error) {
    alert("Action failed: " + error.message);
  }
  await loadSummary();
}

// ---------- Rendering ----------
function render(data) {
  setText("updated", data.generated_at);
  setText("interval", data.check_interval);
  renderBanner(data.overall);
  renderKpis(data.kpi);
  renderServices(data.services);
  renderSeverityChart(data.severity_counts);
  renderLogChart(data.log);
  renderIncidents(data.incidents);
}

function renderBanner(overall) {
  var banner = document.getElementById("banner");
  var messages = {
    operational: "All systems operational",
    degraded: "Partial outage: a minor service is down",
    outage: "Major outage: a high-priority service is down"
  };
  banner.className = "banner " + overall;
  banner.textContent = messages[overall] || "Status unknown";
}

function renderKpis(kpi) {
  setText("kpiUp", kpi.up);
  setText("kpiDown", kpi.down);
  setText("kpiOpen", kpi.open_incidents);
  setText("kpiUptime", kpi.uptime === null ? "-" : kpi.uptime + "%");
  setText("kpiAvg", kpi.avg_ms === null ? "-" : kpi.avg_ms + " ms");
}

function renderServices(services) {
  var box = document.getElementById("services");

  // Create a card once; after that only update the numbers and the chart.
  services.forEach(function (s, index) {
    var id = "service-" + index;
    var card = document.getElementById(id);
    if (!card) {
      card = document.createElement("div");
      card.id = id;
      card.innerHTML =
        '<div class="service-head"><span class="service-name"></span>' +
        '<span><span class="badge"></span><span class="tag"></span></span></div>' +
        '<div class="service-detail"></div>' +
        '<div class="service-stats">' +
        '<div><b class="s-ms"></b>response</div>' +
        '<div><b class="s-uptime"></b>uptime</div>' +
        '<div><b class="s-avg"></b>average</div></div>' +
        '<div class="spark"><canvas></canvas></div>';
      box.appendChild(card);
    }

    var status = cssClass(s.status);
    card.className = "service " + status;
    card.querySelector(".service-name").textContent = s.name;
    var badge = card.querySelector(".badge");
    badge.textContent = s.status;
    badge.className = "badge " + status;
    card.querySelector(".tag").textContent = s.severity;
    card.querySelector(".service-detail").textContent =
      s.detail + (s.checked_at ? " (checked " + s.checked_at + ")" : "");
    card.querySelector(".s-ms").textContent = s.response_ms === null ? "-" : s.response_ms + " ms";
    card.querySelector(".s-uptime").textContent = s.uptime === null ? "-" : s.uptime + "%";
    card.querySelector(".s-avg").textContent = s.avg_ms === null ? "-" : s.avg_ms + " ms";

    updateSparkline(id, card.querySelector("canvas"), s);
  });
}

function updateSparkline(key, canvas, service) {
  var labels = service.history.map(function (h) { return h.time; });
  var values = service.history.map(function (h) { return h.ms; });
  var pointColours = service.history.map(function (h) {
    return h.status === "UP" ? cssVar("--green") : cssVar("--red");
  });
  var lineColour = service.status === "DOWN" ? cssVar("--red") : cssVar("--green");

  if (charts[key]) {
    var chart = charts[key];
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.data.datasets[0].pointBackgroundColor = pointColours;
    chart.data.datasets[0].borderColor = lineColour;
    chart.update("none");
    return;
  }

  charts[key] = new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        data: values, borderColor: lineColour, borderWidth: 2, tension: 0.3,
        pointRadius: 3, pointBackgroundColor: pointColours, fill: false
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false } },
      scales: { x: { display: false }, y: { display: false, beginAtZero: true } }
    }
  });
}

function renderSeverityChart(counts) {
  var labels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
  var values = labels.map(function (l) { return counts[l]; });
  var total = values.reduce(function (a, b) { return a + b; }, 0);
  var canvas = document.getElementById("severityChart");

  document.getElementById("severityEmpty").style.display = total === 0 ? "block" : "none";
  canvas.parentElement.style.display = total === 0 ? "none" : "block";
  if (total === 0) { return; }

  var colours = [cssVar("--darkred"), cssVar("--red"), cssVar("--amber"), cssVar("--blue")];
  if (charts.severity) {
    charts.severity.data.datasets[0].data = values;
    charts.severity.options.plugins.legend.labels.color = cssVar("--text");
    charts.severity.update("none");
    return;
  }
  charts.severity = new Chart(canvas, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colours, borderWidth: 0 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { position: "right", labels: { color: cssVar("--text") } } }
    }
  });
}

function renderLogChart(log) {
  var canvas = document.getElementById("logChart");
  document.getElementById("logEmpty").style.display = log ? "none" : "block";
  canvas.parentElement.style.display = log ? "block" : "none";
  if (!log) { return; }

  var labels = ["INFO", "WARNING", "ERROR"];
  var values = labels.map(function (l) { return log[l]; });
  var colours = [cssVar("--blue"), cssVar("--amber"), cssVar("--red")];

  if (charts.log) {
    charts.log.data.datasets[0].data = values;
    charts.log.options.scales.x.ticks.color = cssVar("--muted");
    charts.log.options.scales.y.ticks.color = cssVar("--muted");
    charts.log.update("none");
    return;
  }
  charts.log = new Chart(canvas, {
    type: "bar",
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colours, borderRadius: 6 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: cssVar("--muted") }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { color: cssVar("--muted"), precision: 0 } }
      }
    }
  });
}

function renderIncidents(incidents) {
  var rows = incidents.filter(function (i) {
    var statusOk = statusFilter === "all" || i.status.toLowerCase() === statusFilter;
    var severityOk = severityFilter === "all" || i.severity === severityFilter;
    return statusOk && severityOk;
  });

  var html = "";
  if (rows.length === 0) {
    html = '<tr><td colspan="8">No incidents match this filter.</td></tr>';
  }
  rows.forEach(function (i) {
    var buttons = "";
    if (i.status === "Open") {
      buttons += '<button class="act" data-action="acknowledge" data-id="' + i.id + '">Acknowledge</button>';
    }
    if (i.status !== "Resolved") {
      buttons += '<button class="act" data-action="resolve" data-id="' + i.id + '">Resolve</button>';
    }
    html += "<tr>" +
      "<td>" + esc(i.ticket) + "</td>" +
      "<td>" + esc(i.service) + "</td>" +
      '<td><span class="badge ' + cssClass(i.severity) + '">' + esc(i.severity) + "</span></td>" +
      '<td class="wrap">' + esc(i.description) + "</td>" +
      '<td><span class="badge ' + cssClass(i.status) + '">' + esc(i.status) + "</span></td>" +
      "<td>" + esc(i.created_at) + "</td>" +
      "<td>" + esc(i.resolved_at) + "</td>" +
      "<td>" + buttons + "</td></tr>";
  });
  document.getElementById("incidentRows").innerHTML = html;
}

// ---------- Events ----------
document.getElementById("statusFilters").addEventListener("click", function (event) {
  var button = event.target.closest("button");
  if (!button) { return; }
  statusFilter = button.getAttribute("data-status");
  var all = document.querySelectorAll("#statusFilters button");
  all.forEach(function (b) { b.className = ""; });
  button.className = "active";
  if (latest) { renderIncidents(latest.incidents); }
});

document.getElementById("severityFilter").addEventListener("change", function (event) {
  severityFilter = event.target.value;
  if (latest) { renderIncidents(latest.incidents); }
});

document.getElementById("incidentRows").addEventListener("click", function (event) {
  var button = event.target.closest("button[data-action]");
  if (!button) { return; }
  var url = "/api/incidents/" + button.getAttribute("data-id") + "/" + button.getAttribute("data-action");
  postAction(url);
});

document.getElementById("runBtn").addEventListener("click", async function () {
  var button = document.getElementById("runBtn");
  button.disabled = true;
  button.textContent = "Running...";
  await postAction("/api/run-checks");
  button.disabled = false;
  button.textContent = "Run checks now";
});

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  setText("themeBtn", theme === "dark" ? "Light mode" : "Dark mode");
  try { localStorage.setItem("theme", theme); } catch (e) { /* storage not available */ }
  if (latest) { render(latest); }
}

document.getElementById("themeBtn").addEventListener("click", function () {
  var current = document.documentElement.getAttribute("data-theme");
  applyTheme(current === "dark" ? "light" : "dark");
});

// ---------- Start ----------
var savedTheme = "light";
try { savedTheme = localStorage.getItem("theme") || "light"; } catch (e) { /* ignore */ }
applyTheme(savedTheme);
loadSummary();
setInterval(loadSummary, REFRESH_MS);
