"""Build data/ward_postcodes.json (postcode -> town-council ward) from the
Oswestry Town Council ward street gazetteer PDFs in data/wards/.

A postcode that straddles two wards is assigned to the ward where most of its
addresses sit.
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader

DATA = Path(__file__).parent / "data"
PC_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b")

WARD_FILES = {
    "Cabin Lane": "Cabin-Lane-Ward-Streets-April-2025-1.pdf",
    "Cambrian": "Cambrian-Ward-Streets-April-2025.pdf",
    "Carreg Llwyd": "Carreg-Llwyd-Ward-Streets-April-2025-1.pdf",
    "Castle": "Castle-Ward-Streets-April-2025.pdf",
    "Gatacre": "Gatacre-Ward-Streets-April-2025.pdf",
    "Maserfield": "Maserfield-Ward-Streets-April-2025.pdf",
    "Victoria": "Victoria-Ward-Streets-April-2025.pdf",
}


def main():
    counts = defaultdict(Counter)  # postcode -> ward -> address count
    for ward, fname in WARD_FILES.items():
        reader = PdfReader(DATA / "wards" / fname)
        n = 0
        for page in reader.pages:
            for m in PC_RE.finditer(page.extract_text() or ""):
                counts[f"{m.group(1)} {m.group(2)}"][ward] += 1
                n += 1
        print(f"{ward}: {n} address rows")

    mapping = {pc: wards.most_common(1)[0][0] for pc, wards in counts.items()}
    (DATA / "ward_postcodes.json").write_text(
        json.dumps(mapping, indent=0, sort_keys=True), encoding="utf-8")

    per_ward = Counter(mapping.values())
    print(f"\n{len(mapping)} unique postcodes mapped:")
    for w, n in per_ward.most_common():
        print(f"  {w}: {n} postcodes")
    straddlers = sum(1 for c in counts.values() if len(c) > 1)
    print(f"({straddlers} postcodes straddle wards; assigned by majority)")


if __name__ == "__main__":
    main()
