"""Analyse harvested Oswestry FixMyStreet reports for council accountability.

Reads data/oswestry_reports.json (from harvest.py) and prints:
- headline open/closed counts and fix rate
- age distribution of still-open reports
- worst categories by open count and median age
- roll of shame: oldest open reports
- likely duplicate clusters (residents re-reporting the same ignored issue)

Also writes data/analysis.json for the dashboard.
"""

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

DATA = Path(__file__).parent / "data"
NOW = datetime.now(timezone.utc)


def parse_dt(s):
    return datetime.fromisoformat(s)


def age_days(r):
    return (NOW - parse_dt(r["requested_datetime"])).days


def main():
    reports = json.loads((DATA / "oswestry_reports.json").read_text(encoding="utf-8"))
    open_r = [r for r in reports if r["status"] == "open"]
    closed_r = [r for r in reports if r["status"] == "closed"]

    print(f"Total Oswestry-area reports harvested: {len(reports)}")
    print(f"  Open (unresolved): {len(open_r)}")
    print(f"  Closed:            {len(closed_r)}")
    if reports:
        span = f"{reports[0]['requested_datetime'][:10]} to {reports[-1]['requested_datetime'][:10]}"
        print(f"  Date span: {span}")

    # Age buckets for open reports
    buckets = [("< 1 month", 0, 30), ("1-3 months", 30, 90), ("3-6 months", 90, 180),
               ("6-12 months", 180, 365), ("over 1 year", 365, 10000)]
    print("\nAge of still-open reports:")
    bucket_counts = {}
    for name, lo, hi in buckets:
        n = sum(1 for r in open_r if lo <= age_days(r) < hi)
        bucket_counts[name] = n
        print(f"  {name:12s}: {n}")

    # Time-to-close for closed reports
    close_days = []
    for r in closed_r:
        d = (parse_dt(r["updated_datetime"]) - parse_dt(r["requested_datetime"])).days
        if d >= 0:
            close_days.append(d)
    if close_days:
        print(f"\nClosed reports: median {median(close_days):.0f} days to close, "
              f"max {max(close_days)} days")

    # Categories
    cats = defaultdict(lambda: {"open": 0, "closed": 0, "open_ages": []})
    for r in reports:
        c = cats[r.get("service_name", "Unknown")]
        c[r["status"]] += 1
        if r["status"] == "open":
            c["open_ages"].append(age_days(r))
    print("\nWorst categories (by open count):")
    cat_rows = []
    for name, c in sorted(cats.items(), key=lambda kv: -kv[1]["open"]):
        total = c["open"] + c["closed"]
        med_age = median(c["open_ages"]) if c["open_ages"] else 0
        cat_rows.append({"category": name, "open": c["open"], "closed": c["closed"],
                         "total": total, "median_open_age_days": med_age})
        if c["open"] > 0:
            print(f"  {name[:45]:45s} open {c['open']:3d} / total {total:3d}  "
                  f"median open age {med_age:.0f}d")

    # Roll of shame
    shame = sorted(open_r, key=age_days, reverse=True)[:25]
    print("\nRoll of shame - oldest open reports:")
    for r in shame:
        print(f"  {age_days(r):4d} days  [{r.get('service_name','?')[:30]}] "
              f"{r['title'][:60]}  {r['url']}")

    # Duplicate clusters: same rounded location, similar-ish, >1 report
    clusters = defaultdict(list)
    for r in reports:
        key = (round(float(r["lat"]), 4), round(float(r["long"]), 4))
        clusters[key].append(r)
    dupes = [v for v in clusters.values() if len(v) >= 3]
    dupes.sort(key=len, reverse=True)
    print(f"\nLocations reported 3+ times ({len(dupes)} clusters):")
    for v in dupes[:15]:
        titles = {re.sub(r"\s+", " ", x["title"]).strip()[:50] for x in v}
        still_open = sum(1 for x in v if x["status"] == "open")
        print(f"  {len(v)}x ({still_open} still open) @ {v[0]['lat']},{v[0]['long']}: "
              f"{' | '.join(sorted(titles))[:120]}")

    out = {
        "generated": NOW.isoformat(),
        "total": len(reports), "open": len(open_r), "closed": len(closed_r),
        "age_buckets": bucket_counts,
        "median_days_to_close": median(close_days) if close_days else None,
        "categories": cat_rows,
        "roll_of_shame": [{"days_open": age_days(r), "title": r["title"],
                           "category": r.get("service_name"), "url": r["url"],
                           "reported": r["requested_datetime"][:10],
                           "lat": r["lat"], "long": r["long"]} for r in shame],
        "duplicate_clusters": [{"count": len(v),
                                "open": sum(1 for x in v if x["status"] == "open"),
                                "lat": v[0]["lat"], "long": v[0]["long"],
                                "titles": sorted({x["title"][:80] for x in v}),
                                "urls": [x["url"] for x in v]} for v in dupes],
    }
    (DATA / "analysis.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nWrote {DATA / 'analysis.json'}")


if __name__ == "__main__":
    main()
