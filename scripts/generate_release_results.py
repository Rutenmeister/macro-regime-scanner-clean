#!/usr/bin/env python3
"""Build v0.42 release-result records from the release calendar.

This intentionally does not invent consensus/actual figures. Official sources in this
static public-source prototype do not all expose forecasts, so unavailable values are
kept null with explicit dataStatus labels. If a future licensed/official feed is added,
fill the same schema and the UI will render it automatically.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAL_PATH = ROOT / "data" / "release_calendar.json"
OUT_PATH = ROOT / "data" / "release_results.json"


def event_id(ev: dict) -> str:
    lane = str(ev.get("lane") or ev.get("source") or "event").lower().replace(" ", "-")
    report = str(ev.get("report") or "report").lower().replace(" ", "-").replace("/", "-")
    date = str(ev.get("date") or "undated")
    return f"{date}__{lane}__{report}"[:180]


def classify_status(ev: dict, now: datetime) -> str:
    raw = ev.get("datetimeUTC") or ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return "released_pending_result" if dt <= now else "upcoming"
    except Exception:
        return "unknown"


def result_source_mode(ev: dict) -> str:
    # Schedules can be official while actual/forecast/previous values are not yet attached.
    confidence = ev.get("calendarConfidence") or ev.get("scheduleType") or "estimated"
    if confidence == "official":
        return "official-calendar-no-result-feed"
    if confidence == "official-pattern":
        return "official-pattern-no-result-feed"
    return "estimated-calendar-no-result-feed"


def main() -> int:
    if not CAL_PATH.exists():
        raise SystemExit(f"Missing {CAL_PATH}")
    calendar = json.loads(CAL_PATH.read_text())
    now = datetime.now(timezone.utc)
    results = []
    for ev in calendar.get("events", []):
        status = classify_status(ev, now)
        results.append({
            "id": event_id(ev),
            "report": ev.get("report"),
            "lane": ev.get("lane"),
            "source": ev.get("source"),
            "date": ev.get("date"),
            "timeET": ev.get("timeET"),
            "datetimeUTC": ev.get("datetimeUTC"),
            "releaseStatus": status,
            "calendarConfidence": ev.get("calendarConfidence") or ev.get("scheduleType") or "estimated",
            "resultSourceMode": result_source_mode(ev),
            "actual": None,
            "forecast": None,
            "previous": None,
            "revision": None,
            "surprise": None,
            "unit": None,
            "resultConfidence": "not_available",
            "resultNote": "v0.42 schema is ready for actual/forecast/previous values, but no official or licensed result feed is attached for this event yet.",
            "sourceUrl": ev.get("sourceUrl"),
            "trackedInputs": ev.get("trackedInputs", []),
        })
    payload = {
        "version": "v0.42-release-result-schema",
        "generatedAt": now.isoformat(),
        "method": "calendar-derived-result-stub-no-invented-figures",
        "warning": "Null actual/forecast/previous values mean no trusted result feed was available. Do not treat null as zero or neutral.",
        "events": results,
        "summary": {
            "total": len(results),
            "withActual": sum(1 for r in results if r.get("actual") is not None),
            "upcoming": sum(1 for r in results if r.get("releaseStatus") == "upcoming"),
            "releasedPendingResult": sum(1 for r in results if r.get("releaseStatus") == "released_pending_result"),
        },
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} with {len(results)} events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
