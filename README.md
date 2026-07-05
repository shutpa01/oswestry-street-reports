# Oswestry Street Reports

A resident-run dashboard tracking how Shropshire Council responds to street
problems reported through [FixMyStreet](https://www.fixmystreet.com) across
Oswestry's seven town-council wards.

**Live dashboard:** see the GitHub Pages site for this repository.

## How it works

- `harvest.py` — pulls two years of reports from FixMyStreet's public Open311
  API (no scraping; the API is provided by mySociety for exactly this purpose)
- `daily_run.py` — the daily pipeline: harvest, snapshot, diff (changes logged
  to `data/changelog.jsonl`), enrich, rebuild the dashboard
- `geocode_postcodes.py` — reverse-geocodes report locations via postcodes.io
- `fetch_closures.py` — records each closed report's real outcome (Fixed /
  No further action / etc.) from its public FixMyStreet page
- `extract_wards.py` — maps postcodes to town wards using Oswestry Town
  Council's published ward gazetteers
- `scrape_councillors.py` — councillors' published contact details per ward
- `build_dashboard.py` — generates the self-contained `docs/index.html`

A GitHub Actions workflow re-runs the pipeline every morning and commits the
result, so the dashboard and the underlying data update automatically and every
day's figures are preserved in the git history as an independent audit trail.

Only information already public on FixMyStreet and council websites is shown.
Independent resident project — not affiliated with Shropshire Council,
Oswestry Town Council, or mySociety.
