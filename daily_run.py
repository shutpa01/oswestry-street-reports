"""Daily pipeline: harvest -> snapshot -> diff -> changelog -> analyse -> dashboard.

Run by the scheduler (or by hand: py daily_run.py). Each run:
1. Re-harvests the full 2-year window from the Open311 API (harvest.py)
2. Saves data/snapshots/YYYY-MM-DD.json
3. Diffs against the previous snapshot; appends transitions to data/changelog.jsonl
   (new reports, open->closed, closed->open, vanished reports)
4. Rebuilds data/analysis.json (analyze.py)
5. Rebuilds the dashboard (build_dashboard.py) if present
"""

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SNAPS = DATA / "snapshots"


def run_step(script):
    print(f"=== {script} ===", flush=True)
    r = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT)
    if r.returncode != 0:
        print(f"FATAL: {script} exited {r.returncode}", flush=True)
        sys.exit(r.returncode)


def index_by_id(path):
    reports = json.loads(path.read_text(encoding="utf-8"))
    return {r["service_request_id"]: r for r in reports}


def diff_and_log(today_str):
    SNAPS.mkdir(exist_ok=True)
    prev_snaps = sorted(SNAPS.glob("*.json"))
    new_snap = SNAPS / f"{today_str}.json"
    shutil.copy(DATA / "oswestry_reports.json", new_snap)

    prev = [p for p in prev_snaps if p.name != new_snap.name]
    if not prev:
        print("First snapshot saved - this is the baseline.", flush=True)
        return

    old = index_by_id(prev[-1])
    new = index_by_id(new_snap)
    observed = datetime.now(timezone.utc).isoformat()
    events = []

    for rid, r in new.items():
        if rid not in old:
            events.append({"event": "new_report", "id": rid, "title": r["title"],
                           "category": r.get("service_name"), "url": r["url"]})
        elif old[rid]["status"] != r["status"]:
            reported = datetime.fromisoformat(r["requested_datetime"])
            days_open = (datetime.now(timezone.utc) - reported).days
            events.append({"event": f"{old[rid]['status']}_to_{r['status']}", "id": rid,
                           "title": r["title"], "category": r.get("service_name"),
                           "days_since_reported": days_open, "url": r["url"]})
    for rid, r in old.items():
        if rid not in new:
            events.append({"event": "vanished", "id": rid, "title": r["title"],
                           "last_status": r["status"], "url": r["url"]})

    with open(DATA / "changelog.jsonl", "a", encoding="utf-8") as f:
        for e in events:
            e["observed"] = observed
            e["compared_to"] = prev[-1].name
            f.write(json.dumps(e) + "\n")

    closed = sum(1 for e in events if e["event"] == "open_to_closed")
    print(f"Diff vs {prev[-1].name}: {len(events)} events "
          f"({sum(1 for e in events if e['event'] == 'new_report')} new, "
          f"{closed} closed, "
          f"{sum(1 for e in events if e['event'] == 'vanished')} vanished)", flush=True)
    if closed >= 30:
        print(f"NOTE: {closed} reports closed in one day - possible bulk closure, "
              f"check changelog.jsonl", flush=True)


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n===== Daily run {today} =====", flush=True)
    run_step("harvest.py")
    diff_and_log(today)
    run_step("analyze.py")
    # non-fatal enrichment steps: dashboard still builds from caches if these fail
    for enrich in ("geocode_postcodes.py", "fetch_closures.py"):
        print(f"=== {enrich} ===", flush=True)
        r = subprocess.run([sys.executable, str(ROOT / enrich)], cwd=ROOT)
        if r.returncode != 0:
            print(f"WARNING: {enrich} failed; using cached data", flush=True)
    if (ROOT / "build_dashboard.py").exists():
        run_step("build_dashboard.py")
    print("Daily run complete.", flush=True)


if __name__ == "__main__":
    main()
