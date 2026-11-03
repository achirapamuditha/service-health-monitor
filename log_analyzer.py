"""Module 1: reads a log file and counts INFO / WARNING / ERROR lines."""


def analyze_log(path):
    """Return (counts, errors). Returns (None, None) if the file is missing."""
    counts = {"INFO": 0, "WARNING": 0, "ERROR": 0}
    errors = []

    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None, None

    for line in lines:
        parts = line.strip().split(" ", 3)
        if len(parts) < 4:
            continue  # skip badly formatted lines
        date, time, level, message = parts
        if level in counts:
            counts[level] += 1
        if level == "ERROR":
            errors.append({"time": date + " " + time, "message": message})

    return counts, errors
