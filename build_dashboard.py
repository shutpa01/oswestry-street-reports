"""Generate docs/index.html - self-contained public dashboard for Oswestry
FixMyStreet accountability. No external assets; works on GitHub Pages.

The page embeds a compact per-report dataset and renders client-side, so
viewers can filter everything by postcode (district dropdown or prefix box).

Sections: hero + stat tiles (open now, open >1 year, average days outstanding),
new vs solved grid (24h/7d/30d), aging bar chart, category table, roll of shame.
"""

import html as html_lib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
NOW = datetime.now(timezone.utc)

# ordinal blue ramps, validated with dataviz validator (light + dark)
RAMP_LIGHT = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
RAMP_DARK = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf"]


def build():
    reports = json.loads((ROOT / "data" / "oswestry_reports.json").read_text(encoding="utf-8"))
    cache_p = ROOT / "data" / "postcode_cache.json"
    postcodes = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}
    ward_p = ROOT / "data" / "ward_postcodes.json"
    ward_map = json.loads(ward_p.read_text(encoding="utf-8")) if ward_p.exists() else {}
    ward_names = sorted(set(ward_map.values()))
    ward_compact = {pc: ward_names.index(w) for pc, w in ward_map.items()}
    cllr_p = ROOT / "data" / "councillors.json"
    cllrs = json.loads(cllr_p.read_text(encoding="utf-8")) if cllr_p.exists() else []
    clo_p = ROOT / "data" / "closure_cache.json"
    closures = json.loads(clo_p.read_text(encoding="utf-8")) if clo_p.exists() else {}

    def closure_state(rid):
        e = closures.get(str(rid))
        if not e or "error" in e:
            return "Closed (outcome unrecorded)"
        s = html_lib.unescape((e.get("final_state") or "").split("\n")[0]).strip().rstrip(",")
        low = s.lower()
        if not s:
            return "Fixed" if e.get("banner") == "fixed" else "Closed (outcome unrecorded)"
        if low.startswith("fixed"):
            return "Fixed"
        if "no further action" in low:
            return "No further action"
        if "not the council" in low or "responsib" in low:
            return "Not the council's responsibility"
        if "internal referral" in low:
            return "Referred internally"
        if low == "closed":
            return "Closed (no reason given)"
        return s

    state_counts = Counter(closure_state(r["service_request_id"])
                           for r in reports if r["status"] == "closed")
    cstates = [s for s, _ in state_counts.most_common()]

    cats, cat_idx = [], {}
    rows = []
    skipped_outside = 0
    for r in reports:
        # town wards only: areas beyond the town boundary are other parishes'
        # responsibility and are excluded from this dashboard
        if postcodes.get(f"{r['lat']},{r['long']}", "") not in ward_map:
            skipped_outside += 1
            continue
        req = datetime.fromisoformat(r["requested_datetime"])
        upd = datetime.fromisoformat(r["updated_datetime"])
        cat = r.get("service_name", "Unknown")
        if cat not in cat_idx:
            cat_idx[cat] = len(cats)
            cats.append(cat)
        is_open = 1 if r["status"] == "open" else 0
        rows.append([
            is_open,
            (NOW - req).days,                       # age in days
            round((NOW - upd).total_seconds() / 86400, 2),  # updated days-ago
            cat_idx[cat],
            postcodes.get(f"{r['lat']},{r['long']}", ""),
            r["service_request_id"],
            r["title"][:90],
            -1 if is_open else cstates.index(closure_state(r["service_request_id"])),
        ])

    data_json = json.dumps(rows, separators=(",", ":")).replace("</", "<\\/")
    cats_json = json.dumps(cats, separators=(",", ":")).replace("</", "<\\/")
    wards_json = json.dumps(ward_names, separators=(",", ":")).replace("</", "<\\/")
    wardmap_json = json.dumps(ward_compact, separators=(",", ":")).replace("</", "<\\/")
    cllrs_json = json.dumps([{"n": c["name"], "w": c["ward"], "e": c["email"]}
                             for c in cllrs if c.get("ward")],
                            separators=(",", ":")).replace("</", "<\\/")
    cstates_json = json.dumps(cstates, separators=(",", ":")).replace("</", "<\\/")
    ramp_light_css = "".join(f"--ramp{i}:{c};" for i, c in enumerate(RAMP_LIGHT))
    ramp_dark_css = "".join(f"--ramp{i}:{c};" for i, c in enumerate(RAMP_DARK))

    page = f"""<title>Oswestry Street Reports — is the council listening?</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,.10);
  --good:#006300; --crit:#d03b3b; {ramp_light_css}
}}
@media (prefers-color-scheme: dark) {{ :root {{
  --page:#0d0d0d; --surface:#1a1a19; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,.10);
  --good:#0ca30c; --crit:#e66767; {ramp_dark_css}
}} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--page); color:var(--ink);
  font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif }}
.wrap {{ max-width:880px; margin:0 auto; padding:24px 16px 48px }}
h1 {{ font-size:26px; margin:8px 0 4px }}
h2 {{ font-size:18px; margin:36px 0 12px }}
.sub {{ color:var(--ink2); margin:0 0 24px }}
.note {{ color:var(--ink2); margin:0 0 12px; font-size:14px }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:10px;
  padding:20px; margin-bottom:16px }}
.hero {{ font-size:56px; font-weight:600; line-height:1.1 }}
.hero-label {{ color:var(--ink2) }}
.cllrcard {{ padding:14px 16px }}
.cllrcard .chead {{ font-size:14px; color:var(--ink2); margin-bottom:8px }}
.cllrcard ul {{ margin:0; padding:0; list-style:none; display:flex; flex-wrap:wrap; gap:6px 24px }}
.cllrcard li {{ font-size:15px }}
.cllrcard .cnote {{ font-size:12px; color:var(--muted); margin-top:8px }}
.searchcard {{ border:2px solid var(--ramp2); padding:18px 20px; margin-bottom:12px }}
.searchlabel {{ display:block; font-size:19px; font-weight:600; margin-bottom:10px }}
.searchrow {{ display:flex; gap:10px; flex-wrap:wrap }}
.searchrow input {{ flex:1 1 260px; max-width:440px; font:18px system-ui,sans-serif;
  color:var(--ink); background:var(--page); border:1px solid var(--baseline);
  border-radius:8px; padding:12px 14px }}
.searchrow button {{ font:15px system-ui,sans-serif; padding:10px 18px; border-radius:8px;
  border:1px solid var(--baseline); background:var(--surface); color:var(--ink2); cursor:pointer }}
.searchhint {{ font-size:13px; color:var(--muted); margin-top:8px }}
.filterbar {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center;
  background:var(--surface); border:1px solid var(--border); border-radius:10px;
  padding:12px 16px; margin:0 0 20px }}
.filterbar label {{ font-size:14px; color:var(--ink2) }}
.filterbar select {{ font:15px system-ui,sans-serif; color:var(--ink);
  background:var(--page); border:1px solid var(--baseline); border-radius:6px; padding:6px 10px }}
.pill {{ font-size:12px; font-weight:600; padding:2px 8px; border-radius:10px;
  white-space:nowrap }}
.pill.open {{ color:var(--crit); border:1px solid var(--crit) }}
.pill.done {{ color:var(--good); border:1px solid var(--good) }}
.pill.nofix {{ color:var(--ink2); border:1px solid var(--baseline) }}
.gnum.dim {{ color:var(--ink2) }}
#showing {{ font-size:14px; color:var(--muted) }}
.tiles, .gcols {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px }}
.tile, .gcol {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 16px }}
.tlabel, .glabel {{ font-size:13px; color:var(--ink2) }}
.tvalue {{ font-size:30px; font-weight:600 }}
.tvalue.crit {{ color:var(--crit) }}
.tsub {{ font-size:12px; color:var(--muted) }}
.glabel {{ margin-bottom:6px }}
.grow {{ font-size:15px; color:var(--ink2) }}
.gnum {{ font-size:24px; font-weight:600; color:var(--ink); margin-right:4px }}
.gnum.solved {{ color:var(--good) }}
.axis, .blabel, .bval {{ font:12px system-ui,sans-serif; fill:var(--muted) }}
.blabel {{ font-size:13px; fill:var(--ink2) }}
.bval {{ font-size:13px; font-weight:600; fill:var(--ink) }}
.bar:hover {{ opacity:.85 }}
table {{ width:100%; border-collapse:collapse; font-size:14px }}
th {{ text-align:left; color:var(--ink2); font-weight:500; padding:6px 8px;
  border-bottom:1px solid var(--baseline) }}
td {{ padding:6px 8px; border-bottom:1px solid var(--grid); vertical-align:top }}
td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums }}
td.strong {{ font-weight:600 }}
td.cat {{ color:var(--ink2) }}
a {{ color:var(--ramp2) }}
.tablewrap {{ overflow-x:auto }}
.foot {{ font-size:13px; color:var(--muted); margin-top:32px }}
#tip {{ position:fixed; pointer-events:none; background:var(--ink); color:var(--page);
  padding:6px 10px; border-radius:6px; font-size:13px; display:none; z-index:9 }}
.firsth2 {{ margin-top:20px }}
@media (max-width:640px) {{
  .wrap {{ padding:14px 10px 40px }}
  h1 {{ font-size:22px }}
  h2 {{ font-size:17px; margin:28px 0 10px }}
  .sub {{ font-size:14px; margin-bottom:16px }}
  .hero {{ font-size:40px }}
  .card {{ padding:14px }}
  .gcols {{ grid-template-columns:repeat(3,1fr); gap:8px }}
  .gcol {{ padding:10px 8px }}
  .glabel {{ font-size:11px }}
  .gnum {{ font-size:19px; margin-right:3px }}
  .grow {{ font-size:12px }}
  .tiles {{ gap:8px }}
  .tile {{ padding:10px 12px }}
  .tvalue {{ font-size:23px }}
  .tlabel {{ font-size:12px }}
  .searchcard {{ padding:14px }}
  .searchlabel {{ font-size:16px; margin-bottom:8px }}
  .searchrow input {{ font:16px system-ui,sans-serif; padding:10px 12px }}
  table {{ font-size:13px }}
  th, td {{ padding:5px 6px }}
}}
</style>
<div class="wrap">
<h1>Oswestry street reports: is the council listening?</h1>
<p class="sub">Every problem below was reported by a resident through
<a href="https://www.fixmystreet.com" target="_blank" rel="noopener">FixMyStreet</a>
and sent to Shropshire Council. Data covers the seven Oswestry town-council wards,
updated daily. Last update: {NOW:%d %B %Y}.</p>

<h2 class="firsth2">Reported vs solved</h2>
<div class="gcols" id="grid"></div>

<div class="card searchcard">
  <label class="searchlabel" for="pcbox">Look up your postcode or street</label>
  <div class="searchrow">
    <input id="pcbox" placeholder="e.g. SY11 2 or Salop Road" autocomplete="off">
    <button id="clearbtn" type="button">Clear</button>
  </div>
  <div class="searchhint">Type a postcode (with or without the space) or part of a
  street or report name — matching reports are listed below the headline figures.</div>
</div>

<div class="filterbar">
  <label for="ward">Ward:</label>
  <select id="ward"><option value="">All wards</option></select>
  <label for="district">Area:</label>
  <select id="district"><option value="">All areas</option></select>
  <span id="showing"></span>
</div>

<div class="card">
  <div class="hero" id="hero"></div>
  <div class="hero-label" id="herolabel"></div>
</div>

<div class="card cllrcard" id="cllrpanel" hidden></div>

<h2>Individual reports</h2>
<p class="note">Only what is already public on
<a href="https://www.fixmystreet.com" target="_blank" rel="noopener">FixMyStreet</a>
is shown here — no names or contact details. Click "view" to open the original
report, where you can add an update or photo.</p>
<div class="card tablewrap" id="reportcard"></div>

<div class="tiles" id="tiles"></div>

<h2>What does &ldquo;closed&rdquo; actually mean?</h2>
<p class="note">&ldquo;Closed&rdquo; on FixMyStreet does not always mean fixed. This is
the recorded outcome of every closed report in the current view.</p>
<div class="card tablewrap" id="closurecard"></div>

<h2>How long have today's unfixed problems been waiting?</h2>
<p class="note" id="chartnote"></p>
<div class="card" id="chartcard"></div>

<h2>Worst categories</h2>
<div class="card tablewrap" id="catcard"></div>

<h2>The longest-ignored reports</h2>
<div class="card tablewrap" id="shamecard"></div>

<p class="foot">Source: FixMyStreet public Open311 data (reports sent to Shropshire
Council, last 2 years, within Oswestry&rsquo;s seven town-council wards &mdash;
surrounding parishes are excluded). Postcodes derived
from report locations via postcodes.io. "Solved" means the report was marked closed
on FixMyStreet, recorded at its last update time; closure does not always mean
fixed. Independent resident project — not affiliated with Shropshire Council or
mySociety. Generated {NOW:%d %B %Y %H:%M} UTC.</p>
</div>
<div id="tip"></div>
<script>
/* rows: [open(1/0), ageDays, updatedDaysAgo, catIdx, postcode, reportId, title] */
var DATA = {data_json};
var CATS = {cats_json};
var WARDS = {wards_json};
var WARDMAP = {wardmap_json};  /* postcode -> index into WARDS (town-council wards) */
var CLLRS = {cllrs_json};      /* [{{n: name, w: ward name, e: email}}] */
var CSTATES = {cstates_json};  /* closure outcomes; row[7] indexes this (-1 = open) */
function isFixed(r) {{ return r[0] === 0 && CSTATES[r[7]] === 'Fixed'; }}
function wardOf(pc) {{ return WARDMAP.hasOwnProperty(pc) ? WARDMAP[pc] : -1; }}
var BUCKETS = [["Under 1 month",0,30],["1\\u20133 months",30,90],["3\\u20136 months",90,180],
               ["6\\u201312 months",180,365],["Over 1 year",365,1e9]];

function esc(s) {{ return String(s).replace(/[&<>"']/g, function(c) {{
  return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]; }}); }}
function fmt(n) {{ return n.toLocaleString('en-GB'); }}
function median(a) {{ if (!a.length) return 0; var s = a.slice().sort(function(x,y){{return x-y}});
  var m = Math.floor(s.length/2); return s.length % 2 ? s[m] : Math.round((s[m-1]+s[m])/2); }}

/* dropdown counts show OPEN reports only, so they reconcile with the headline */
var OPEN_ALL = DATA.filter(function(r){{return r[0]===1}});
var districts = {{}};
OPEN_ALL.forEach(function(r) {{ var d = (r[4]||'').split(' ')[0];
  if (d) districts[d] = (districts[d]||0) + 1; }});
var sel = document.getElementById('district');
sel.options[0].textContent = 'All areas (' + fmt(OPEN_ALL.length) + ' open)';
Object.keys(districts).sort().forEach(function(d) {{
  var o = document.createElement('option'); o.value = d;
  o.textContent = d + ' (' + fmt(districts[d]) + ' open)'; sel.appendChild(o); }});

var wsel = document.getElementById('ward');
var wardCounts = WARDS.map(function(){{return 0}});
var outsideCount = 0;
OPEN_ALL.forEach(function(r) {{ var w = wardOf(r[4]);
  if (w >= 0) wardCounts[w]++; else outsideCount++; }});
wsel.options[0].textContent = 'All wards (' + fmt(OPEN_ALL.length) + ' open)';
WARDS.forEach(function(w, i) {{
  var o = document.createElement('option'); o.value = String(i);
  o.textContent = w + ' (' + fmt(wardCounts[i]) + ' open)'; wsel.appendChild(o); }});

function isPostcodeish(s) {{ return /^[A-Z]{{1,2}}\\d/.test(s); }}

function currentFilter() {{
  var raw = document.getElementById('pcbox').value.trim();
  if (raw) {{
    var norm = raw.toUpperCase().replace(/\\s+/g,'');
    if (isPostcodeish(norm)) return function(r) {{
      return (r[4]||'').replace(/\\s+/g,'').indexOf(norm) === 0; }};
    var q = raw.toUpperCase();
    return function(r) {{
      return (r[6]||'').toUpperCase().indexOf(q) >= 0 ||
             CATS[r[3]].toUpperCase().indexOf(q) >= 0; }};
  }}
  var w = wsel.value;
  if (w !== '') return function(r) {{ return wardOf(r[4]) === +w; }};
  var d = sel.value;
  if (d) return function(r) {{ return (r[4]||'').split(' ')[0] === d; }};
  return function() {{ return true; }};
}}

function render() {{
  var rows = DATA.filter(currentFilter());
  var open = rows.filter(function(r){{return r[0]===1}});
  var closed = rows.filter(function(r){{return r[0]===0}});
  var raw = document.getElementById('pcbox').value.trim();
  var anyFilter = !!raw || wsel.value !== '' || sel.value !== '';
  var label;
  if (raw) {{
    label = isPostcodeish(raw.toUpperCase().replace(/\\s+/g,'')) ?
      'in ' + raw.toUpperCase() : 'matching \\u201C' + raw + '\\u201D';
  }} else if (wsel.value !== '') {{ label = 'in ' + WARDS[+wsel.value] + ' ward';
  }} else if (sel.value) {{ label = 'in ' + sel.value;
  }} else {{ label = 'across Oswestry\\u2019s seven town wards'; }}
  document.getElementById('showing').textContent =
    'Showing ' + fmt(rows.length) + (rows.length===1 ? ' report' : ' reports') +
    (anyFilter ? ' ' + label : '');

  document.getElementById('hero').textContent = fmt(open.length);
  document.getElementById('herolabel').textContent =
    (open.length===1 ? 'report' : 'reports') + ' still unresolved ' + label;

  renderReports(rows, anyFilter);

  var panel = document.getElementById('cllrpanel');
  if (wsel.value !== '') {{
    var wname = WARDS[+wsel.value];
    var mine = CLLRS.filter(function(c){{return c.w === wname}});
    var subj = encodeURIComponent('Unresolved street reports in ' + wname + ' ward');
    panel.innerHTML = '<div class="chead">Your town councillors for ' + esc(wname) +
      ' ward:</div><ul>' + mine.map(function(c) {{
        return '<li>' + esc(c.n) + (c.e ? ' \\u2014 <a href="mailto:' + esc(c.e) +
               '?subject=' + subj + '">' + esc(c.e) + '</a>' : '') + '</li>';
      }}).join('') + '</ul><div class="cnote">Street problems are Shropshire Council\\u2019s ' +
      'responsibility, but your town councillors can press them on your behalf. ' +
      'Contact details from oswestry-tc.gov.uk.</div>';
    panel.hidden = mine.length === 0;
  }} else {{
    panel.hidden = true;
  }}

  var overYear = open.filter(function(r){{return r[1]>=365}}).length;
  var avgOut = open.length ? Math.round(open.reduce(function(a,r){{return a+r[1]}},0)/open.length) : 0;
  document.getElementById('tiles').innerHTML =
    '<div class="tile"><div class="tlabel">Open for over a year</div>' +
    '<div class="tvalue crit">' + fmt(overYear) + '</div><div class="tsub">' +
    (open.length ? Math.round(overYear/open.length*100) : 0) + '% of open reports</div></div>' +
    '<div class="tile"><div class="tlabel">Average wait so far</div>' +
    '<div class="tvalue">' + fmt(avgOut) + ' days</div><div class="tsub">mean age of the ' +
    fmt(open.length) + ' unfixed ' + (open.length===1 ? 'report' : 'reports') +
    ' \\u2014 and counting</div></div>' +
    '<div class="tile"><div class="tlabel">Reports tracked</div>' +
    '<div class="tvalue">' + fmt(rows.length) + '</div><div class="tsub">over the last 2 years</div></div>' +
    (closed.length ? '<div class="tile"><div class="tlabel">\\u201CClosed\\u201D but not fixed</div>' +
    '<div class="tvalue crit">' + fmt(closed.length - closed.filter(isFixed).length) +
    '</div><div class="tsub">' +
    Math.round((closed.length - closed.filter(isFixed).length)/closed.length*100) +
    '% of all closed reports</div></div>' : '');

  var g = '';
  [['Last 24 hours',1],['Last 7 days',7],['Last 30 days',30]].forEach(function(w) {{
    var nnew = rows.filter(function(r){{return r[1] < w[1]}}).length;
    var recent = closed.filter(function(r){{return r[2] < w[1]}});
    var nfixed = recent.filter(isFixed).length;
    g += '<div class="gcol"><div class="glabel">' + w[0] + '</div>' +
         '<div class="grow"><span class="gnum">' + fmt(nnew) + '</span> new</div>' +
         '<div class="grow"><span class="gnum solved">' + fmt(nfixed) + '</span> fixed</div>' +
         '<div class="grow"><span class="gnum dim">' + fmt(recent.length - nfixed) +
         '</span> closed, not fixed</div></div>';
  }});
  document.getElementById('grid').innerHTML = g;

  var byState = {{}};
  closed.forEach(function(r) {{ byState[r[7]] = (byState[r[7]]||0) + 1; }});
  if (closed.length) {{
    var ch = '<table><tr><th>Recorded outcome</th><th class="num">Reports</th>' +
             '<th class="num">% of closures</th></tr>';
    Object.keys(byState).sort(function(a,b){{return byState[b]-byState[a]}})
      .forEach(function(k) {{
        ch += '<tr><td>' + esc(CSTATES[k]) + '</td><td class="num">' + fmt(byState[k]) +
              '</td><td class="num">' + Math.round(byState[k]/closed.length*100) + '%</td></tr>';
      }});
    document.getElementById('closurecard').innerHTML = ch + '</table>';
  }} else {{
    document.getElementById('closurecard').innerHTML =
      '<p class="note" style="margin:0">No closed reports in the current view.</p>';
  }}

  document.getElementById('chartnote').innerHTML =
    'Each bar counts reports that are <strong>still open right now</strong>, grouped by time ' +
    'since a resident reported them. This is waiting time so far \\u2014 not time to fix. ' +
    'Every one of these ' + fmt(open.length) + ' problems remains unresolved.';
  drawChart(open);

  var byCat = {{}};
  rows.forEach(function(r) {{
    var c = byCat[r[3]] || (byCat[r[3]] = {{open:0, total:0, ages:[]}});
    c.total++; if (r[0]===1) {{ c.open++; c.ages.push(r[1]); }}
  }});
  var catRows = Object.keys(byCat).map(function(k) {{
    return {{name: CATS[k], o: byCat[k].open, t: byCat[k].total, m: median(byCat[k].ages)}};
  }}).sort(function(a,b){{return b.o-a.o}}).slice(0,20);
  var ct = '<table><tr><th>Category</th><th class="num">Open</th>' +
           '<th class="num">Total reported</th><th class="num">Median days open</th></tr>';
  catRows.forEach(function(c) {{
    ct += '<tr><td>' + esc(c.name) + '</td><td class="num">' + fmt(c.o) +
          '</td><td class="num">' + fmt(c.t) + '</td><td class="num">' + fmt(c.m) + '</td></tr>';
  }});
  document.getElementById('catcard').innerHTML = ct + '</table>';

  var shame = open.slice().sort(function(a,b){{return b[1]-a[1]}}).slice(0,20);
  var st = '<table><tr><th class="num">Days open</th><th>Report</th><th>Category</th>' +
           '<th>Postcode</th><th></th></tr>';
  shame.forEach(function(r) {{
    st += '<tr><td class="num strong">' + fmt(r[1]) + '</td><td>' + esc(r[6]) +
          '</td><td class="cat">' + esc(CATS[r[3]]) + '</td><td>' + esc(r[4]) +
          '</td><td><a href="https://www.fixmystreet.com/report/' + r[5] +
          '" target="_blank" rel="noopener">view</a></td></tr>';
  }});
  document.getElementById('shamecard').innerHTML = st + '</table>';
}}

var NOW_MS = {int(NOW.timestamp() * 1000)};
function dateOf(daysAgo) {{
  return new Date(NOW_MS - daysAgo*864e5).toLocaleDateString('en-GB',
    {{day:'numeric', month:'short', year:'numeric'}});
}}

function renderReports(rows, anyFilter) {{
  var card = document.getElementById('reportcard');
  if (!anyFilter) {{
    card.innerHTML = '<p class="note" style="margin:0">Use the search box or the ward ' +
      'and area filters above and every matching report will be listed here.</p>';
    return;
  }}
  var list = rows.slice().sort(function(a,b){{return a[1]-b[1]}});  // newest first
  var shown = list.slice(0, 150);
  var h = '<table><tr><th>Status</th><th>Report</th><th>Category</th>' +
          '<th>Postcode</th><th class="num">Reported</th><th></th></tr>';
  shown.forEach(function(r) {{
    h += '<tr><td>' + (r[0] ?
           '<span class="pill open">Open ' + fmt(r[1]) + ' days</span>' :
           (isFixed(r) ? '<span class="pill done">Fixed</span>' :
            '<span class="pill nofix">' + esc(CSTATES[r[7]]) + '</span>')) +
         '</td><td>' + esc(r[6]) + '</td><td class="cat">' + esc(CATS[r[3]]) +
         '</td><td>' + esc(r[4]) + '</td><td class="num">' + dateOf(r[1]) +
         '</td><td><a href="https://www.fixmystreet.com/report/' + r[5] +
         '" target="_blank" rel="noopener">view</a></td></tr>';
  }});
  h += '</table>';
  if (list.length > shown.length) {{
    h += '<p class="note" style="margin:10px 0 0">Showing the ' + shown.length +
         ' most recent of ' + fmt(list.length) + ' matching reports \\u2014 narrow ' +
         'your search to see older ones.</p>';
  }}
  card.innerHTML = h;
}}

var SHORT = ['<1 mo','1\\u20133 mo','3\\u20136 mo','6\\u201312 mo','>1 yr'];
function drawChart(open) {{
  window._lastOpen = open;
  var counts = BUCKETS.map(function(b) {{
    return open.filter(function(r){{return r[1]>=b[1] && r[1]<b[2]}}).length; }});
  var maxC = Math.max.apply(null, counts) || 1;
  var compact = (document.getElementById('chartcard').clientWidth || 600) < 480;
  var LW = compact ? 64 : 120, BW = compact ? 240 : 560, BH = 24, GAP = 14,
      PR = compact ? 46 : 60;
  var W = LW + BW + PR, H = BUCKETS.length*(BH+GAP) + 30;
  var step = [1,2,5,10,25,50,100,200,500].filter(function(s){{return maxC/s <= 6}})[0] || 500;
  var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Open reports by age"' +
            ' style="width:100%;height:auto">';
  for (var t = 0; t <= maxC; t += step) {{
    var x = LW + t/maxC*BW;
    svg += '<line x1="'+x+'" y1="0" x2="'+x+'" y2="'+(H-24)+'" stroke="var(--grid)" stroke-width="1"/>' +
           '<text x="'+x+'" y="'+(H-8)+'" text-anchor="middle" class="axis">'+fmt(t)+'</text>';
  }}
  counts.forEach(function(n, i) {{
    var y = i*(BH+GAP) + 6;
    var w = Math.max(n/maxC*BW, 2), rx = Math.min(4, w/2);
    svg += '<text x="'+(LW-8)+'" y="'+(y+BH/2+4)+'" text-anchor="end" class="blabel">' +
           (compact ? SHORT[i] : BUCKETS[i][0]) + '</text>' +
           '<path class="bar" data-name="'+BUCKETS[i][0]+'" data-n="'+n+'" fill="var(--ramp'+i+')" d="' +
           'M'+LW+','+y+' h'+(w-rx)+' a'+rx+','+rx+' 0 0 1 '+rx+','+rx+' v'+(BH-2*rx) +
           ' a'+rx+','+rx+' 0 0 1 -'+rx+','+rx+' h-'+(w-rx)+' z"/>' +
           '<text x="'+(LW+w+8)+'" y="'+(y+BH/2+4)+'" class="bval">'+fmt(n)+'</text>';
  }});
  document.getElementById('chartcard').innerHTML = svg + '</svg>';

  var tip = document.getElementById('tip');
  var total = open.length || 1;
  document.querySelectorAll('.bar').forEach(function(b) {{
    b.addEventListener('mousemove', function(e) {{
      tip.textContent = b.dataset.name + ': ' + fmt(+b.dataset.n) + ' open reports (' +
        Math.round(b.dataset.n/total*100) + '%)';
      tip.style.display = 'block';
      tip.style.left = (e.clientX+14)+'px'; tip.style.top = (e.clientY-10)+'px';
    }});
    b.addEventListener('mouseleave', function() {{ tip.style.display = 'none'; }});
  }});
}}

var _rsz;
window.addEventListener('resize', function() {{
  clearTimeout(_rsz);
  _rsz = setTimeout(function() {{ if (window._lastOpen) drawChart(window._lastOpen); }}, 200);
}});

wsel.addEventListener('change', function() {{
  sel.value=''; document.getElementById('pcbox').value=''; render(); }});
sel.addEventListener('change', function() {{
  wsel.value=''; document.getElementById('pcbox').value=''; render(); }});
document.getElementById('pcbox').addEventListener('input', function() {{
  sel.value=''; wsel.value=''; render(); }});
document.getElementById('clearbtn').addEventListener('click', function() {{
  sel.value=''; wsel.value=''; document.getElementById('pcbox').value=''; render(); }});
render();
</script>
"""
    DOCS.mkdir(exist_ok=True)
    out = DOCS / "index.html"
    out.write_text("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
                   + page + "</html>", encoding="utf-8")
    print(f"Dashboard written to {out} ({out.stat().st_size / 1024:.0f} KB); "
          f"{len(rows)} town-ward reports kept, {skipped_outside} outside excluded")


if __name__ == "__main__":
    build()
