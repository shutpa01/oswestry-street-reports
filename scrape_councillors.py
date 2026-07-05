"""Build data/councillors.json: name, ward, email, profile URL for each
Oswestry Town Council councillor, from the public council website."""

import json
import re
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"
UA = "OswestryCivicAudit/1.0 (resident accountability project)"
MAIN = "https://www.oswestry-tc.gov.uk/the-council/councillors/"
WARDS = ["Cabin Lane", "Cambrian", "Carreg Llwyd", "Castle", "Gatacre",
         "Maserfield", "Victoria"]
EMAIL_RE = re.compile(r"(?:mailto:)?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
CF_RE = re.compile(r'(?:data-cfemail="|email-protection#)([a-f0-9]{8,})')
PERSON_RE = re.compile(r'href="(https://www\.oswestry-tc\.gov\.uk/people/[^"]+)"')


def cf_decode(hexstr):
    b = bytes.fromhex(hexstr)
    return "".join(chr(c ^ b[0]) for c in b[1:])


def get(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def main():
    html = get(MAIN)

    # ward section positions: match "<ward name> Ward" headings, ignoring the
    # PDF street-list links (those contain "Ward-Streets" or "Ward Streets")
    marks = []
    for w in WARDS:
        for m in re.finditer(re.escape(w) + r"\s+Ward(?!\s*Streets|-Streets)", html):
            marks.append((m.start(), w))
    marks.sort()

    people = {}
    for m in PERSON_RE.finditer(html):
        url = m.group(1)
        if "example-councillor" in url or url in people:
            continue
        ward = None
        for pos, w in marks:
            if pos < m.start():
                ward = w
        people[url] = ward

    out = []
    for url, ward in people.items():
        page = get(url)
        if re.search(r"<title>\s*Vacancy", page):
            continue
        title = re.search(r"<title>\s*([^<|]+?)\s*(?:[-|].*)?</title>", page)
        name = title.group(1).strip() if title else url.rsplit("/", 2)[-2]
        emails = [cf_decode(h) for h in CF_RE.findall(page)]
        emails += EMAIL_RE.findall(page)
        emails = [e for e in emails if "@" in e and "example" not in e
                  and "wordpress" not in e]
        generic = ("enquiries@", "info@", "admin@", "townclerk@")
        personal = [e for e in emails if not e.lower().startswith(generic)]
        email = personal[0] if personal else (emails[0] if emails else "")
        out.append({"name": name, "ward": ward, "email": email, "url": url})
        print(f"{ward or '??':13s} {name:35s} {email}")
        time.sleep(0.5)

    (DATA / "councillors.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    missing = [c["name"] for c in out if not c["email"] or not c["ward"]]
    print(f"\n{len(out)} councillors saved; missing data for: {missing or 'none'}")


if __name__ == "__main__":
    main()
