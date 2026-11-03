"""Module 4: builds a simple HTML dashboard (dashboard.html) from the results."""
import html
import os

import database

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Service Health Dashboard</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: Arial, sans-serif; background: #f3f5f9; color: #1f2937; margin: 0; padding: 24px; }
  h1 { margin: 0 0 4px 0; }
  .sub { color: #6b7280; margin-bottom: 24px; font-size: 14px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .card { background: white; border-radius: 10px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-top: 4px solid #9ca3af; }
  .card .num { font-size: 32px; font-weight: bold; }
  .card .label { color: #6b7280; font-size: 14px; }
  .card.good { border-top-color: #16a34a; }
  .card.bad { border-top-color: #dc2626; }
  .card.warn { border-top-color: #f59e0b; }
  .panel { background: white; border-radius: 10px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; overflow-x: auto; }
  h2 { margin-top: 0; font-size: 18px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e7eb; }
  th { color: #6b7280; font-weight: 600; }
  .badge { padding: 3px 10px; border-radius: 12px; color: white; font-size: 12px; font-weight: bold; }
  .up { background: #16a34a; }
  .down { background: #dc2626; }
  .critical { background: #7f1d1d; }
  .high { background: #dc2626; }
  .medium { background: #f59e0b; }
  .low { background: #3b82f6; }
  .open { background: #dc2626; }
  .acknowledged { background: #f59e0b; }
  .resolved { background: #16a34a; }
  .bar-row { display: flex; align-items: center; margin: 8px 0; font-size: 14px; }
  .bar-label { width: 90px; }
  .bar { height: 14px; border-radius: 7px; }
  .bar-num { margin-left: 8px; }
  .filters button { border: 1px solid #d1d5db; background: white; padding: 6px 14px; border-radius: 6px; cursor: pointer; margin-right: 6px; }
  .filters button.active { background: #1f2937; color: white; border-color: #1f2937; }
  .filters { margin-bottom: 12px; }
</style>
</head>
<body>
  <h1>Service Health Dashboard</h1>
  <div class="sub">Generated: %%TIME%%</div>

  <div class="cards">
    <div class="card good"><div class="num">%%UP%%</div><div class="label">Services UP</div></div>
    <div class="card bad"><div class="num">%%DOWN%%</div><div class="label">Services DOWN</div></div>
    <div class="card warn"><div class="num">%%OPEN%%</div><div class="label">Open incidents</div></div>
    <div class="card"><div class="num">%%LOGERRORS%%</div><div class="label">Log errors</div></div>
  </div>

  <div class="panel">
    <h2>Services</h2>
    <table>
      <tr><th>Service</th><th>Status</th><th>Response (ms)</th><th>Detail</th></tr>
      %%SERVICE_ROWS%%
    </table>
  </div>

  <div class="panel">
    <h2>Log Summary</h2>
    %%LOG_BARS%%
  </div>

  <div class="panel">
    <h2>Incidents</h2>
    <div class="filters">
      <button class="active" onclick="filterIncidents('all', this)">All</button>
      <button onclick="filterIncidents('open', this)">Open</button>
      <button onclick="filterIncidents('resolved', this)">Resolved</button>
    </div>
    <table>
      <tr><th>ID</th><th>Service</th><th>Severity</th><th>Description</th><th>Status</th><th>Created</th><th>Resolved</th></tr>
      %%INCIDENT_ROWS%%
    </table>
  </div>

<script>
  function filterIncidents(status, button) {
    var rows = document.querySelectorAll("tr[data-status]");
    for (var i = 0; i < rows.length; i++) {
      var rowStatus = rows[i].getAttribute("data-status");
      if (status === "all" || rowStatus === status ||
          (status === "open" && rowStatus === "acknowledged")) {
        rows[i].style.display = "";
      } else {
        rows[i].style.display = "none";
      }
    }
    var buttons = document.querySelectorAll(".filters button");
    for (var j = 0; j < buttons.length; j++) {
      buttons[j].className = "";
    }
    button.className = "active";
  }
</script>
</body>
</html>
"""


def safe(value):
    """Escape text so it is safe to place inside HTML."""
    if value is None:
        return ""
    return html.escape(str(value))


def build_service_rows(results):
    rows = ""
    for r in results:
        status = r["status"]
        rows += ("<tr><td>" + safe(r["service"]) + "</td>"
                 "<td><span class='badge " + status.lower() + "'>" + status + "</span></td>"
                 "<td>" + safe(r["response_ms"]) + "</td>"
                 "<td>" + safe(r["detail"]) + "</td></tr>\n")
    return rows


def build_incident_rows(incidents):
    if not incidents:
        return "<tr><td colspan='7'>No incidents yet.</td></tr>"
    rows = ""
    for i in incidents:
        status = i["status"]
        rows += ("<tr data-status='" + status.lower() + "'>"
                 "<td>" + database.format_id(i["id"]) + "</td>"
                 "<td>" + safe(i["service"]) + "</td>"
                 "<td><span class='badge " + i["severity"].lower() + "'>" + safe(i["severity"]) + "</span></td>"
                 "<td>" + safe(i["description"]) + "</td>"
                 "<td><span class='badge " + status.lower() + "'>" + safe(status) + "</span></td>"
                 "<td>" + safe(i["created_at"]) + "</td>"
                 "<td>" + safe(i["resolved_at"]) + "</td></tr>\n")
    return rows


def build_log_bars(log_counts):
    if not log_counts:
        return "<p>No log data available.</p>"
    colours = {"INFO": "#3b82f6", "WARNING": "#f59e0b", "ERROR": "#dc2626"}
    biggest = max(log_counts.values()) or 1
    bars = ""
    for level, number in log_counts.items():
        width = int(number / biggest * 300)
        bars += ("<div class='bar-row'><div class='bar-label'>" + level + "</div>"
                 "<div class='bar' style='width:" + str(width) + "px; background:" + colours[level] + "'></div>"
                 "<div class='bar-num'>" + str(number) + "</div></div>\n")
    return bars


def generate_dashboard(results, log_counts, incidents, report_dir):
    """Fill the template with real data and save it as dashboard.html."""
    ups = len([r for r in results if r["status"] == "UP"])
    downs = len([r for r in results if r["status"] == "DOWN"])
    open_count = len([i for i in incidents if i["status"] in ("Open", "Acknowledged")])
    log_errors = log_counts["ERROR"] if log_counts else 0

    page = TEMPLATE
    page = page.replace("%%TIME%%", database.now())
    page = page.replace("%%UP%%", str(ups))
    page = page.replace("%%DOWN%%", str(downs))
    page = page.replace("%%OPEN%%", str(open_count))
    page = page.replace("%%LOGERRORS%%", str(log_errors))
    page = page.replace("%%SERVICE_ROWS%%", build_service_rows(results))
    page = page.replace("%%LOG_BARS%%", build_log_bars(log_counts))
    page = page.replace("%%INCIDENT_ROWS%%", build_incident_rows(incidents))

    path = os.path.join(report_dir, "dashboard.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path
