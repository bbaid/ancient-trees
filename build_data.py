# /// script
# dependencies = ["xlrd"]
# ///
"""Convert venerable-trees.xls into data/trees.geojson for the map.

Run with:  uv run build_data.py
"""
import json
import re
from pathlib import Path

import xlrd

SRC = Path(__file__).parent / "venerable-trees.xls"
OUT = Path(__file__).parent / "data" / "trees.geojson"

# First matching group wins, so mixed entries ("бряст/дъб") land on the earlier one.
GROUPS = [
    ("oak", r"дъб|цер|благун|горун|пърнар"),
    ("plane", r"чинар|платан"),
    ("beech", r"бук"),
    ("conifer", r"\bбор\b|мура|смърч|\bела\b|кедър|секвоя|\bтис\b|кипарис|либоцедрус|мамонтово"),
    ("ash", r"ясен"),
    ("elm", r"бряст"),
    ("poplar", r"топол|върба|трепетлика"),
    ("fruit", r"орех|черница|круша|скоруша|кестен|леска|бадем|махалебка|брекина|фурма|лоза|джел"),
]


def group_of(species):
    s = species.lower()
    for key, pattern in GROUPS:
        if re.search(pattern, s):
            return key
    return "other"


def text(v):
    """Cell as display text; '' for blanks and the sheet's '-' placeholder."""
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else str(v)
    v = re.sub(r"\s+", " ", str(v)).strip()
    return "" if v == "-" else v


def number(v):
    """Cell as a float when it is a plain number ('4,30' -> 4.3), else None."""
    if isinstance(v, float):
        return v
    m = re.fullmatch(r"\d+(?:[.,]\d+)?", str(v).strip())
    return float(m.group().replace(",", ".")) if m else None


def age_of(v):
    """Numeric age for sizing/filtering. Free-text entries ('над 300',
    '280/300/200/120', '1=180, 2=120') use the largest plausible age."""
    if isinstance(v, float):
        return v
    ages = [int(n) for n in re.findall(r"\d+", str(v)) if int(n) >= 25]
    return max(ages) if ages else None


def date_of(v, datemode):
    if isinstance(v, float):
        return xlrd.xldate_as_datetime(v, datemode).strftime("%Y-%m-%d")
    return text(v)


def main():
    wb = xlrd.open_workbook(SRC)
    sheet = wb.sheet_by_index(0)
    features, skipped = [], 0
    for r in range(1, sheet.nrows):
        (no, species, count, doc_type, doc_no, date, gazette, place, municipality,
         province, riosv, age, height, girth, diameter, notes, lat, lon,
         *_) = sheet.row_values(r)
        if not (isinstance(lat, float) and isinstance(lon, float)):
            skipped += 1
            continue
        species = re.sub(r"\s+", " ", species).strip()
        props = {
            "id": int(no),
            "species": species,
            "group": group_of(species),
            "count": int(count),
            "place": text(place),
            "municipality": text(municipality),
            "province": text(province),
            "riosv": text(riosv),
            "age": age_of(age),
            "ageText": text(age),
            "height": number(height),
            "heightText": text(height),
            "girth": number(girth),
            "girthText": text(girth),
            "diameterText": text(diameter),
            "notes": text(notes),
            "docType": text(doc_type),
            "docNo": text(doc_no),
            "docDate": date_of(date, wb.datemode),
            "gazette": date_of(gazette, wb.datemode),
        }
        features.append({
            "type": "Feature",
            "id": int(no),
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": props,
        })

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(
        {"type": "FeatureCollection", "skipped": skipped, "features": features},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(features)} trees written to {OUT.relative_to(Path(__file__).parent)}; "
          f"{skipped} rows without coordinates skipped")


if __name__ == "__main__":
    main()
