"""SessionStart health check for CognitiveMemory.

Runs on SessionStart. Reads memory/.last-consolidation.json and emits a
system reminder if the curator hasn't run successfully in >7 days.

Silent success: if recent, exits 0 with no output.
Visible warning: if stale or missing, prints a short system reminder that
Claude sees at session start.

Never crashes. Prints only to stdout (which becomes a system reminder).
"""
import json
import os
import sys
from datetime import datetime, timedelta


STALE_DAYS = 7
LAST_RUN_FILE = os.path.join(os.getcwd(), "memory", ".last-consolidation.json")


def main():
    if not os.path.isdir(os.path.join(os.getcwd(), "memory")):
        sys.exit(0)  # not a CognitiveMemory project

    try:
        with open(LAST_RUN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        last_ts = datetime.fromisoformat(data.get("timestamp", ""))
    except Exception:
        last_ts = None

    now = datetime.now()
    if last_ts is None:
        print("[minds] Memory consolidation has not run yet. Run /document or wait for the auto-curator.")
        sys.exit(0)

    age = now - last_ts
    if age > timedelta(days=STALE_DAYS):
        days = age.days
        print(f"[minds] Memory consolidation is {days} days stale. Auto-curator hasn't fired. Check ~/.claude/metrics/curator-log.txt.")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
