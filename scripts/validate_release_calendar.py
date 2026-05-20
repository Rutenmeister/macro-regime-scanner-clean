#!/usr/bin/env python3
"""Validate release_calendar.json for v0.41 calendar hardening."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "data" / "release_calendar.json"

HOLIDAYS_2026 = {"2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-10-12", "2026-11-11", "2026-11-26", "2026-12-25"}
REQUIRED_FIELDS = ["source", "report", "lane", "date", "timeET", "datetimeET", "datetimeUTC", "importance", "scheduleType", "calendarConfidence", "sourceUrl", "trackedInputs", "note"]
VALID_CONFIDENCE = {"official", "official-pattern", "estimated"}


def fail(msg: str) -> int:
    print(f"VALIDATION FAILED: {msg}")
    return 1


def main() -> int:
    if not CAL.exists():
        return fail(f"missing {CAL.relative_to(ROOT)}")
    data = json.loads(CAL.read_text(encoding="utf-8"))
    events = data.get("events")
    if not isinstance(events, list) or not events:
        return fail("events must be a non-empty list")
    for i, ev in enumerate(events):
        for field in REQUIRED_FIELDS:
            if field not in ev:
                return fail(f"event {i} missing {field}")
        if ev["calendarConfidence"] not in VALID_CONFIDENCE:
            return fail(f"event {i} invalid calendarConfidence {ev['calendarConfidence']}")
        if not ev.get("sourceUrl", "").startswith("https://"):
            return fail(f"event {i} sourceUrl must be https URL")
        if ev["source"] == "U.S. Treasury" and ev["date"] in HOLIDAYS_2026:
            return fail(f"Treasury release scheduled on federal holiday {ev['date']}")
        if ev["report"] == "Advance Monthly Sales for Retail and Food Services / Retail Sales" and ev["date"] == "2026-05-20":
            return fail("Retail Sales May 20 false estimate still present")
        if "Personal Income and Outlays" in ev["report"] and ev["date"] == "2026-05-23":
            return fail("PCE May 23 false estimate still present")
    summary = data.get("confidenceSummary", {})
    if "official" not in summary or "estimated" not in summary:
        return fail("confidenceSummary missing official/estimated counts")
    print(f"VALIDATION PASSED: {len(events)} release-calendar events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
