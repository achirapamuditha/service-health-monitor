"""Module 2: stores health checks and incidents in a SQLite database (SQL)."""
import sqlite3
from datetime import datetime

DB_FILE = "incidents.db"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # lets us use row["column_name"]
    return conn


def format_id(number):
    """1 -> INC0001 (looks like a ServiceNow ticket number)."""
    return "INC" + str(number).zfill(4)


def init_db():
    conn = connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT, status TEXT, response_ms INTEGER,
            detail TEXT, checked_at TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT, severity TEXT, description TEXT,
            status TEXT, created_at TEXT, resolved_at TEXT
        )""")
    conn.commit()
    conn.close()


def save_check(service, status, response_ms, detail):
    conn = connect()
    conn.execute(
        "INSERT INTO checks (service, status, response_ms, detail, checked_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (service, status, response_ms, detail, now()),
    )
    conn.commit()
    conn.close()


def create_incident(service, severity, description):
    conn = connect()
    cur = conn.execute(
        "INSERT INTO incidents (service, severity, description, status, created_at) "
        "VALUES (?, ?, ?, 'Open', ?)",
        (service, severity, description, now()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return format_id(new_id)


def get_open_incident(service):
    """Return the unresolved (Open or Acknowledged) incident for a service, or None."""
    conn = connect()
    row = conn.execute(
        "SELECT * FROM incidents WHERE service = ? "
        "AND status IN ('Open', 'Acknowledged')", (service,)
    ).fetchone()
    conn.close()
    return row


def resolve_incident(incident_number):
    """Mark an incident Resolved. Returns True if a row was changed."""
    conn = connect()
    cur = conn.execute(
        "UPDATE incidents SET status = 'Resolved', resolved_at = ? "
        "WHERE id = ? AND status != 'Resolved'",
        (now(), incident_number),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def acknowledge_incident(incident_number):
    """Open -> Acknowledged (someone is working on it). Returns True if changed."""
    conn = connect()
    cur = conn.execute(
        "UPDATE incidents SET status = 'Acknowledged' WHERE id = ? AND status = 'Open'",
        (incident_number,),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def get_all_incidents():
    conn = connect()
    rows = conn.execute("SELECT * FROM incidents ORDER BY id").fetchall()
    conn.close()
    return rows


def get_open_incidents():
    """All unresolved incidents (Open or Acknowledged)."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM incidents WHERE status IN ('Open', 'Acknowledged') ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


# ---------- Functions used by the web dashboard (app.py) ----------

def get_latest_check(service):
    conn = connect()
    row = conn.execute(
        "SELECT * FROM checks WHERE service = ? ORDER BY id DESC LIMIT 1", (service,)
    ).fetchone()
    conn.close()
    return row


def get_recent_checks(service, limit=20):
    """Last N checks for a service, oldest first (good for a chart)."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM checks WHERE service = ? ORDER BY id DESC LIMIT ?",
        (service, limit),
    ).fetchall()
    conn.close()
    return list(reversed(rows))


def get_uptime(service):
    """Uptime % = UP checks / all checks * 100. None if there are no checks."""
    conn = connect()
    row = conn.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN status = 'UP' THEN 1 ELSE 0 END) AS ups "
        "FROM checks WHERE service = ?", (service,)
    ).fetchone()
    conn.close()
    if row["total"] == 0:
        return None
    return round(row["ups"] / row["total"] * 100, 1)


def get_avg_response(service):
    """Average response time (ms) of successful checks. None if there are none."""
    conn = connect()
    row = conn.execute(
        "SELECT AVG(response_ms) AS avg_ms FROM checks "
        "WHERE service = ? AND status = 'UP'", (service,)
    ).fetchone()
    conn.close()
    if row["avg_ms"] is None:
        return None
    return int(row["avg_ms"])
