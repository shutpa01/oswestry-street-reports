"""Reverse-geocode report coordinates to UK postcodes via postcodes.io (bulk API).

Reads data/oswestry_reports.json, maintains a cache in data/postcode_cache.json
keyed by "lat,long" so daily runs only geocode new locations. Stdlib only.
"""

import json
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"
CACHE = DATA / "postcode_cache.json"
API = "https://api.postcodes.io/postcodes"
BATCH = 100


def main():
    reports = json.loads((DATA / "oswestry_reports.json").read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    todo = []
    seen = set()
    for r in reports:
        key = f"{r['lat']},{r['long']}"
        if key not in cache and key not in seen:
            seen.add(key)
            todo.append({"latitude": float(r["lat"]), "longitude": float(r["long"]),
                         "limit": 1, "radius": 1000, "_key": key})

    print(f"{len(reports)} reports, {len(cache)} cached locations, {len(todo)} to geocode")
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        body = json.dumps({"geolocations": [
            {k: v for k, v in c.items() if k != "_key"} for c in chunk]}).encode()
        req = urllib.request.Request(API, data=body,
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "OswestryCivicAudit/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                results = json.load(resp)["result"]
        except Exception as e:
            print(f"  batch {i // BATCH + 1} failed: {e} - continuing with partial data")
            break
        for c, res in zip(chunk, results):
            hits = res.get("result") or []
            cache[c["_key"]] = hits[0]["postcode"] if hits else ""
        print(f"  geocoded {min(i + BATCH, len(todo))}/{len(todo)}", flush=True)
        time.sleep(0.3)

    CACHE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
    with_pc = sum(1 for v in cache.values() if v)
    print(f"Cache now {len(cache)} locations ({with_pc} with postcode)")


if __name__ == "__main__":
    main()
