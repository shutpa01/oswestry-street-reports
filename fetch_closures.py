"""Fetch the closure detail for closed reports from their FixMyStreet pages.

The Open311 API only says "closed"; the public report page shows the update
timeline ("State changed to: Fixed" / "No further action" / etc.). This crawls
closed reports politely (1 req/sec), caching results in data/closure_cache.json
so daily runs only fetch newly-closed reports. Stdlib only.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"
CACHE = DATA / "closure_cache.json"
UA = "OswestryCivicAudit/1.0 (resident accountability project; +https://github.com/shutpa01/oswestry-street-reports)"
STATE_RE = re.compile(r"State changed to: ([^<]+)")
BANNER_RE = re.compile(r'class="banner banner--([a-z-]+)"')


def main():
    reports = json.loads((DATA / "oswestry_reports.json").read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    closed = [r for r in reports if r["status"] == "closed"
              and str(r["service_request_id"]) not in cache]
    print(f"{len(closed)} closed reports to fetch (cache has {len(cache)})", flush=True)

    for i, r in enumerate(closed, 1):
        rid = str(r["service_request_id"])
        url = f"https://www.fixmystreet.com/report/{rid}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")
            states = STATE_RE.findall(html)
            banner = BANNER_RE.search(html)
            cache[rid] = {"final_state": states[-1].strip() if states else "",
                          "states": [s.strip() for s in states],
                          "banner": banner.group(1) if banner else ""}
        except Exception as e:
            cache[rid] = {"error": str(e)[:100]}
        if i % 50 == 0 or i == len(closed):
            CACHE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
            print(f"  {i}/{len(closed)} fetched", flush=True)
        time.sleep(1.0)

    CACHE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
    from collections import Counter
    counts = Counter(v.get("final_state", "?") or "(no state recorded)"
                     for v in cache.values() if "error" not in v)
    print("\nFinal states across closed reports:")
    for state, n in counts.most_common():
        print(f"  {n:5d}  {state}")


if __name__ == "__main__":
    main()
