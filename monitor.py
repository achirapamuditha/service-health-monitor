"""
Service Health Monitor and Incident Tracker
Run:            python monitor.py   (also creates reports/dashboard.html)
List incidents: python monitor.py incidents
"""
import csv
import json
import os
import sys
import time
from datetime import datetime

import requests

import database
from dashboard import generate_dashboard
from log_analyzer import analyze_log

SERVICES_FILE = "services.json"
LOG_FILE = "app.log"
REPORT_DIR = "reports"
ERROR_THRESHOLD = 3   # this many log errors creates an incident
TIMEOUT = 5           # seconds to wait for a service


def load_services():
    try:
        with open(SERVICES_FILE, "r") as f:
            return json.load(f)["services"]
    except FileNotFoundError:
        print("Cannot find", SERVICES_FILE)
        return []
    except (json.JSONDecodeError, KeyError):
        print(SERVICES_FILE, "is not valid. Check the JSON format.")
        return []


def check_service(url):
    """Visit the URL. Return (status, response_ms, detail)."""
    start = time.time()
    try:
        response = requests.get(url, timeout=TIMEOUT)
        ms = int((time.time() - start) * 1000)
        if response.status_code >= 400:
            return "DOWN", ms, "HTTP " + str(response.status_code)
        return "UP", ms, "OK"
    except requests.exceptions.Timeout:
        return "DOWN", TIMEOUT * 1000, "Timeout"
    except requests.exceptions.ConnectionError:
        return "DOWN", 0, "Connection failed"
    except requests.exceptions.RequestException:
        return "DOWN", 0, "Request error"


def handle_incident(name, severity, status, detail):
    """Create an incident when DOWN, resolve it when the service is back UP."""
    open_incident = database.get_open_incident(name)

    if status == "DOWN":
        if open_incident is None:
            ticket = database.create_incident(name, severity, detail)
            print("   -> Incident", ticket, "created (" + severity + ")")
            if severity in ("HIGH", "CRITICAL"):
                print("   -> ESCALATE: notify the on-call support team!")
        else:
            ticket = database.format_id(open_incident["id"])
            print("   -> Incident", ticket, "is already open")
    elif open_incident is not None:
        database.resolve_incident(open_incident["id"])
        ticket = database.format_id(open_incident["id"])
        print("   -> Service recovered. Incident", ticket, "resolved")


def check_logs():
    """Phase 1 project, now a module: scan the log and raise an incident."""
    print("\n--- Log Analysis ---")
    counts, errors = analyze_log(LOG_FILE)
    if counts is None:
        print("Log file not found:", LOG_FILE)
        return None

    print("INFO:", counts["INFO"], "| WARNING:", counts["WARNING"],
          "| ERROR:", counts["ERROR"])
    status = "DOWN" if len(errors) >= ERROR_THRESHOLD else "UP"
    detail = str(len(errors)) + " errors found in " + LOG_FILE
    handle_incident("Log Analysis", "MEDIUM", status, detail)
    return counts


def export_reports(results, log_counts):
    """Save a JSON daily report and a CSV of all incidents (open it in Power BI)."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    incidents = database.get_all_incidents()
    open_count = len(database.get_open_incidents())

    report = {
        "generated_at": database.now(),
        "services_checked": len(results),
        "services_up": len([r for r in results if r["status"] == "UP"]),
        "services_down": len([r for r in results if r["status"] == "DOWN"]),
        "open_incidents": open_count,
        "log_summary": log_counts,
        "results": results,
    }
    json_path = os.path.join(REPORT_DIR, "daily_report_" + today + ".json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=4)

    csv_path = os.path.join(REPORT_DIR, "incidents.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Incident", "Service", "Severity", "Description",
                         "Status", "Created", "Resolved"])
        for i in incidents:
            writer.writerow([database.format_id(i["id"]), i["service"],
                             i["severity"], i["description"], i["status"],
                             i["created_at"], i["resolved_at"]])

    dashboard_path = generate_dashboard(results, log_counts, incidents, REPORT_DIR)

    print("\nReports saved:", json_path, "and", csv_path)
    print("Dashboard saved:", dashboard_path, "(open it in your browser)")


def show_open_incidents():
    rows = database.get_open_incidents()
    print("===== OPEN INCIDENTS =====")
    if not rows:
        print("No open incidents.")
    for i in rows:
        print(database.format_id(i["id"]), "|", i["severity"], "|",
              i["service"], "|", i["description"], "|", i["created_at"])


def collect_results():
    """Check every service and the log file. Returns (results, log_counts)."""
    services = load_services()
    results = []
    for service in services:
        name, url = service["name"], service["url"]
        severity = service.get("severity", "MEDIUM")

        status, ms, detail = check_service(url)
        database.save_check(name, status, ms, detail)
        print("[" + status + "]", name, "-", ms, "ms -", detail)
        handle_incident(name, severity, status, detail)

        results.append({"service": name, "url": url, "status": status,
                        "response_ms": ms, "detail": detail})

    log_counts = check_logs()
    return results, log_counts


def run_checks():
    print("===== SERVICE HEALTH CHECK =====")
    print("Time:", database.now(), "\n")

    results, log_counts = collect_results()
    if not results:
        return

    print("\n===== SUMMARY =====")
    ups = len([r for r in results if r["status"] == "UP"])
    print("Services UP:", ups, "/", len(results))
    print("Open incidents:", len(database.get_open_incidents()))

    export_reports(results, log_counts)


def main():
    database.init_db()
    if len(sys.argv) > 1 and sys.argv[1] == "incidents":
        show_open_incidents()
    else:
        run_checks()


if __name__ == "__main__":
    main()
