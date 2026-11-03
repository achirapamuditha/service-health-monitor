# Service Health Monitor and Incident Tracker

A Python tool that checks whether services are UP or DOWN, scans application
logs for errors, creates incident tickets (like a mini ServiceNow), stores them
in a SQL database and exports reports for Power BI.

## Features
- Health checks for websites and APIs (response time and HTTP status)
- Automatic incident creation with ID, severity and status (Open / Resolved)
- No duplicate tickets: an open incident is reused, and resolved when the service recovers
- Escalation message for HIGH and CRITICAL incidents
- Log analysis (INFO / WARNING / ERROR counts) that raises an incident on too many errors
- SQLite database (SQL: INSERT, SELECT, UPDATE)
- Daily JSON report and incidents.csv (open in Power BI or Excel)
- **Live web dashboard (Flask)** at http://127.0.0.1:5000 with:
  - Overall status banner (operational / partial outage / major outage)
  - KPI cards: services UP/DOWN, open incidents, average uptime, average response time
  - Per-service cards with uptime % and a response-time chart (Chart.js)
  - Incident workflow: Open -> Acknowledged -> Resolved (buttons in the browser)
  - Incident filters by status and severity, severity doughnut chart, log bar chart
  - Automatic checks every 60 seconds, page refreshes every 5 seconds
  - Light and dark mode
- Static HTML dashboard (`reports/dashboard.html`) from the command-line version

## Tech
Python 3, Flask, requests, sqlite3, json, csv, HTML, CSS, JavaScript, Chart.js

## Project structure
| File | Purpose |
|---|---|
| app.py | Flask web app: pages, JSON API and the automatic check scheduler |
| monitor.py | Check logic and the command-line version |
| database.py | SQLite functions (checks and incidents tables) |
| log_analyzer.py | Reads the log file and counts levels |
| dashboard.py | Generates the static HTML dashboard (command-line version) |
| templates/dashboard.html | Page structure of the live dashboard |
| static/style.css | Styling, light and dark themes |
| static/dashboard.js | Fetches data, draws charts, handles buttons |
| static/chart.umd.js | Chart.js library (works offline) |
| services.json | List of services to monitor (edit this) |
| app.log | Sample log file |
| requirements.txt | Libraries needed |

## How to run
1. Install Python 3
2. Install the library: `pip install -r requirements.txt`
3. **Live dashboard:** `python app.py`, then open http://127.0.0.1:5000 (press Ctrl+C to stop)
4. **Command-line version:** `python monitor.py` (also creates the static dashboard)
5. List open incidents: `python monitor.py incidents`

Run `monitor.py` repeatedly (or schedule it with Task Scheduler / cron) to
simulate continuous monitoring.

## Add your own service
Edit `services.json`:
```json
{"name": "My API", "url": "https://example.com/health", "severity": "HIGH"}
```
Severity options: LOW, MEDIUM, HIGH, CRITICAL.

## API endpoints (used by the dashboard)
| Method | URL | Purpose |
|---|---|---|
| GET | /api/summary | All dashboard data as JSON |
| POST | /api/run-checks | Run all checks now |
| POST | /api/incidents/<id>/acknowledge | Open -> Acknowledged |
| POST | /api/incidents/<id>/resolve | Mark Resolved |

## Output
- `incidents.db` : SQLite database (created on first run)
- `reports/daily_report_YYYY-MM-DD.json` : daily summary
- `reports/incidents.csv` : all incidents, ready for Power BI
- `reports/dashboard.html` : open in any browser (double-click it)

## Runbook: what to do when a service is DOWN
1. **Confirm:** run `python monitor.py` again to rule out a temporary glitch
2. **Check the incident:** `python monitor.py incidents` and note ID and severity
3. **Investigate:** check the error detail (Timeout, Connection failed, HTTP 500) and the service logs
4. **Escalate:** for HIGH or CRITICAL, notify the on-call team immediately
5. **Fix or restart** the service following the procedure for that service
6. **Verify:** run the monitor again; the incident resolves automatically when the service is UP
7. **Document:** record the cause and fix for the knowledge base

## Severity guide
| Severity | Meaning | Action |
|---|---|---|
| CRITICAL | Core service down | Escalate immediately |
| HIGH | Major feature affected | Escalate quickly |
| MEDIUM | Partial or minor issue | Fix during working hours |
| LOW | Cosmetic or minor | Plan a fix |

## Possible improvements
- Email alerts using smtplib
- Power BI dashboard on incidents.csv
- Flask web app version with a Run Checks button
- Deploy as an AWS Lambda function on a schedule
