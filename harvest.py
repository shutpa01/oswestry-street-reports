"""Harvest FixMyStreet reports for the Oswestry area via the public Open311 API.

Walks the Open311 GeoReport v2 endpoint (run by mySociety) week-by-week over
the last two years, filtered to Shropshire Council (agency 2238), and keeps
reports within RADIUS_KM of Oswestry town centre. Stdlib only.

Output: data/oswestry_reports.json and data/oswestry_reports.csv
"""

import csv
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://www.fixmystreet.com/open311/v2/requests.json"
AGENCY = "2238"  # Shropshire Council
CENTRE = (52.85737, -3.05359)  # Oswestry (user's map view)
RADIUS_KM = 5.0
WEEKS_BACK = 104
USER_AGENT = "OswestryCivicAudit/1.0 (resident accountability project; +https://github.com/shutpa01/oswestry-street-reports)"
OUT_DIR = Path(__file__).parent / "data"

FIELDS = [
    "service_request_id", "title", "detail", "service_name", "status",
    "requested_datetime", "updated_datetime", "agency_sent_datetime",
    "lat", "long", "comment_count", "interface_used", "media_url",
    "distance_km", "url",
]


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def fetch(status, start, end, retries=3):
    params = {
        "jurisdiction_id": "fixmystreet.com",
        "agency_responsible": AGENCY,
        "status": status,
        "start_date": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_date": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_requests": "1000",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp).get("service_requests", [])
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"  retry {attempt + 1} after error: {e} (waiting {wait}s)", flush=True)
            time.sleep(wait)
    print(f"  FAILED window {start:%Y-%m-%d} {status} - skipping", flush=True)
    return None


def main():
    OUT_DIR.mkdir(exist_ok=True)
    reports = {}
    failed_windows = []
    capped_windows = []
    now = datetime.now(timezone.utc)

    for week in range(WEEKS_BACK):
        end = now - timedelta(weeks=week)
        start = end - timedelta(weeks=1)
        for status in ("open", "closed"):
            rows = fetch(status, start, end)
            if rows is None:
                failed_windows.append((start.isoformat(), status))
                continue
            if len(rows) >= 1000:
                capped_windows.append((start.isoformat(), status))
            kept = 0
            for r in rows:
                try:
                    dist = haversine_km(CENTRE[0], CENTRE[1], float(r["lat"]), float(r["long"]))
                except (KeyError, ValueError):
                    continue
                if dist <= RADIUS_KM:
                    rid = r["service_request_id"]
                    r["distance_km"] = round(dist, 2)
                    r["url"] = f"https://www.fixmystreet.com/report/{rid}"
                    reports[rid] = r  # newer windows fetched first; keep first seen
                    kept += 1
            print(f"{start:%Y-%m-%d} {status:6s}: {len(rows):4d} county-wide, {kept:3d} in Oswestry "
                  f"(total {len(reports)})", flush=True)
            time.sleep(0.5)

    out = sorted(reports.values(), key=lambda r: r["requested_datetime"])
    (OUT_DIR / "oswestry_reports.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    with open(OUT_DIR / "oswestry_reports.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in out:
            if isinstance(r.get("agency_responsible"), dict):
                r = dict(r)
            w.writerow({k: r.get(k, "") for k in FIELDS})

    print(f"\nDone: {len(out)} unique Oswestry-area reports saved to {OUT_DIR}")
    if capped_windows:
        print(f"WARNING: {len(capped_windows)} windows hit the 1000-result cap (data may be incomplete): {capped_windows}")
    if failed_windows:
        print(f"WARNING: {len(failed_windows)} windows failed: {failed_windows}")


if __name__ == "__main__":
    sys.exit(main())
