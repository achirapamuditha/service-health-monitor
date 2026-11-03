"""
Live web dashboard (Flask).
Run:  python app.py      then open  http://127.0.0.1:5000
"""
import threading
import time

from flask import Flask, abort, jsonify, render_template

import database
import monitor
from log_analyzer import analyze_log

app = Flask(__name__)

CHECK_INTERVAL = 60          # seconds between automatic checks
run_lock = threading.Lock()  # stops two check runs happening at the same time
state = {"last_run": None}


# ---------- Running the checks ----------

def run_checks_once():
    """Run all checks (the same code as the command-line version)."""
    with run_lock:
        results, log_counts = monitor.collect_results()
        state["last_run"] = database.now()
        return results


def scheduler():
    """Background thread: run the checks every CHECK_INTERVAL seconds."""
    while True:
        try:
            run_checks_once()
        except Exception as error:
            print("Scheduler error:", error)
        time.sleep(CHECK_INTERVAL)


# ---------- Building the data for the page ----------

def overall_status(service_cards):
    """Decide the banner: operational, degraded or major outage."""
    down = [s for s in service_cards if s["status"] == "DOWN"]
    if not down:
        return "operational"
    if any(s["severity"] in ("HIGH", "CRITICAL") for s in down):
        return "outage"
    return "degraded"


def build_summary():
    cards = []
    for service in monitor.load_services():
        name = service["name"]
        latest = database.get_latest_check(name)
        history = database.get_recent_checks(name, 20)
        cards.append({
            "name": name,
            "severity": service.get("severity", "MEDIUM"),
            "status": latest["status"] if latest else "UNKNOWN",
            "response_ms": latest["response_ms"] if latest else None,
            "detail": latest["detail"] if latest else "No checks yet",
            "checked_at": latest["checked_at"] if latest else None,
            "uptime": database.get_uptime(name),
            "avg_ms": database.get_avg_response(name),
            "history": [{"time": h["checked_at"][11:], "ms": h["response_ms"],
                         "status": h["status"]} for h in history],
        })

    incidents = []
    for row in reversed(database.get_all_incidents()):   # newest first
        incident = dict(row)
        incident["ticket"] = database.format_id(row["id"])
        incidents.append(incident)

    open_incidents = [i for i in incidents if i["status"] in ("Open", "Acknowledged")]
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for i in open_incidents:
        if i["severity"] in severity_counts:
            severity_counts[i["severity"]] += 1

    uptimes = [c["uptime"] for c in cards if c["uptime"] is not None]
    averages = [c["avg_ms"] for c in cards if c["avg_ms"] is not None]
    log_counts, _ = analyze_log(monitor.LOG_FILE)

    return {
        "generated_at": database.now(),
        "last_run": state["last_run"],
        "check_interval": CHECK_INTERVAL,
        "overall": overall_status(cards),
        "kpi": {
            "up": len([c for c in cards if c["status"] == "UP"]),
            "down": len([c for c in cards if c["status"] == "DOWN"]),
            "open_incidents": len(open_incidents),
            "uptime": round(sum(uptimes) / len(uptimes), 1) if uptimes else None,
            "avg_ms": int(sum(averages) / len(averages)) if averages else None,
        },
        "services": cards,
        "severity_counts": severity_counts,
        "log": log_counts,
        "incidents": incidents[:100],
    }


# ---------- Routes (URLs) ----------

@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/api/summary")
def api_summary():
    return jsonify(build_summary())


@app.route("/api/run-checks", methods=["POST"])
def api_run_checks():
    results = run_checks_once()
    return jsonify({"checked": len(results), "last_run": state["last_run"]})


@app.route("/api/incidents/<int:incident_id>/acknowledge", methods=["POST"])
def api_acknowledge(incident_id):
    if not database.acknowledge_incident(incident_id):
        abort(404)
    return jsonify({"ok": True})


@app.route("/api/incidents/<int:incident_id>/resolve", methods=["POST"])
def api_resolve(incident_id):
    if not database.resolve_incident(incident_id):
        abort(404)
    return jsonify({"ok": True})


if __name__ == "__main__":
    database.init_db()
    threading.Thread(target=scheduler, daemon=True).start()
    print("Dashboard running at http://127.0.0.1:5000  (press Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=5000, debug=False)
