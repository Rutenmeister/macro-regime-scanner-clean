#!/usr/bin/env python3
"""Fetch official U.S. Treasury Daily Treasury Par Yield Curve Rates.

This first live lane intentionally uses only official/public Treasury data and
avoids market-price, momentum, moving-average, or other price-derived inputs.

Outputs:
  data/raw/treasury/treasury_yield_curve_raw.xml
  data/normalized/treasury_yields.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "treasury"
NORM_DIR = ROOT / "data" / "normalized"
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
DATASET = "daily_treasury_yield_curve"

TREASURY_FIELD_MAP = {
    "1 Mo": "BC_1MONTH",
    "2 Mo": "BC_2MONTH",
    "3 Mo": "BC_3MONTH",
    "4 Mo": "BC_4MONTH",
    "6 Mo": "BC_6MONTH",
    "1 Yr": "BC_1YEAR",
    "2 Yr": "BC_2YEAR",
    "3 Yr": "BC_3YEAR",
    "5 Yr": "BC_5YEAR",
    "7 Yr": "BC_7YEAR",
    "10 Yr": "BC_10YEAR",
    "20 Yr": "BC_20YEAR",
    "30 Yr": "BC_30YEAR",
}


def fetch_year(year: int) -> bytes:
    url = f"{BASE_URL}?data={DATASET}&field_tdr_date_value={year}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def text_for_child(element: ET.Element, wanted_name: str) -> str | None:
    for child in element.iter():
        if local_name(child.tag) == wanted_name:
            text = (child.text or "").strip()
            return text or None
    return None


def parse_xml(xml_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    records: list[dict[str, Any]] = []

    for entry in root.iter():
        if local_name(entry.tag) != "entry":
            continue
        date_text = text_for_child(entry, "NEW_DATE")
        if not date_text:
            continue
        try:
            date = dt.datetime.fromisoformat(date_text.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            # Treasury XML sometimes emits a simple date. Keep parse strict but forgiving.
            date = date_text[:10]

        rates: dict[str, float | None] = {}
        for label, field in TREASURY_FIELD_MAP.items():
            raw = text_for_child(entry, field)
            if raw is None:
                rates[label] = None
            else:
                try:
                    rates[label] = float(raw)
                except ValueError:
                    rates[label] = None
        records.append({"date": date, "rates": rates})

    records.sort(key=lambda row: row["date"])
    return records


def compute_curves(latest_rates: dict[str, float | None]) -> dict[str, float | None]:
    def spread(a: str, b: str) -> float | None:
        av = latest_rates.get(a)
        bv = latest_rates.get(b)
        if av is None or bv is None:
            return None
        return round(av - bv, 3)

    # Convention used here: long minus short, in percentage points.
    return {
        "10Y minus 2Y": spread("10 Yr", "2 Yr"),
        "30Y minus 5Y": spread("30 Yr", "5 Yr"),
    }


def main() -> int:
    today = dt.date.today()
    years = [today.year]
    if today.month == 1:
        years.append(today.year - 1)

    all_records: list[dict[str, Any]] = []
    last_xml: bytes | None = None
    for year in years:
        xml = fetch_year(year)
        last_xml = xml
        all_records.extend(parse_xml(xml))

    # Remove duplicate dates if both current and prior year were fetched.
    by_date = {row["date"]: row for row in all_records}
    records = [by_date[d] for d in sorted(by_date)]
    if len(records) < 2:
        raise RuntimeError("Treasury yield feed returned fewer than 2 dated records")

    latest = records[-1]
    previous = records[-2]

    normalized = {
        "source_id": "TREASURY_OFFICIAL",
        "source_name": "U.S. Treasury Daily Treasury Par Yield Curve Rates",
        "retrieved_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "latest_date": latest["date"],
        "previous_date": previous["date"],
        "latest_rates": latest["rates"],
        "previous_rates": previous["rates"],
        "curve_spreads": compute_curves(latest["rates"]),
        "records_tail": records[-10:],
        "notes": [
            "Official U.S. Treasury public yield curve feed.",
            "Rates are percentages, not prices.",
            "This lane intentionally avoids price-derived trend, momentum, and moving-average inputs.",
        ],
    }

    if last_xml:
        (RAW_DIR / "treasury_yield_curve_raw.xml").write_bytes(last_xml)
    (NORM_DIR / "treasury_yields.json").write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    print(f"Fetched Treasury yields through {normalized['latest_date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
