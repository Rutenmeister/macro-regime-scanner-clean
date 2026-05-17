#!/usr/bin/env python3
"""Generate a lightweight upcoming-report calendar for the sidebar.

This is deliberately separate from scoring. It creates data/release_calendar.json
from the source lanes being tracked by the Macro Regime Scanner. The first
version uses deterministic release-pattern rules and marks entries as expected
or official-pattern rather than pretending to be a full government calendar
parser. It is refreshed whenever the master refresh workflow runs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "release_calendar.json"
ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


@dataclass(frozen=True)
class CalendarEvent:
    source: str
    report: str
    lane: str
    event_time: datetime
    importance: str
    schedule_type: str
    tracked_inputs: list[str]
    note: str

    def to_json(self) -> dict:
        return {
            "source": self.source,
            "report": self.report,
            "lane": self.lane,
            "date": self.event_time.date().isoformat(),
            "timeET": self.event_time.strftime("%-I:%M %p ET"),
            "datetimeET": self.event_time.isoformat(),
            "datetimeUTC": self.event_time.astimezone(UTC).isoformat(),
            "importance": self.importance,
            "scheduleType": self.schedule_type,
            "trackedInputs": self.tracked_inputs,
            "note": self.note,
        }


def at_et(day, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), ET)


def next_weekday(start: datetime, weekday: int, hour: int, minute: int = 0, include_today: bool = True) -> datetime:
    # Monday=0 ... Sunday=6
    base = start.astimezone(ET)
    days = (weekday - base.weekday()) % 7
    candidate = at_et((base + timedelta(days=days)).date(), hour, minute)
    if days == 0 and (not include_today or candidate <= base):
        candidate += timedelta(days=7)
    return candidate


def business_days(start: datetime, count: int, hour: int, minute: int = 0) -> list[datetime]:
    base = start.astimezone(ET)
    day = base.date()
    out = []
    while len(out) < count:
        if day.weekday() < 5:
            candidate = at_et(day, hour, minute)
            if candidate > base:
                out.append(candidate)
        day = day + timedelta(days=1)
    return out


def nth_weekday(year: int, month: int, weekday: int, n: int, hour: int, minute: int = 0) -> datetime:
    d = datetime(year, month, 1, tzinfo=ET).date()
    offset = (weekday - d.weekday()) % 7
    target = d + timedelta(days=offset + (n - 1) * 7)
    return at_et(target, hour, minute)


def first_weekday(year: int, month: int, weekday: int, hour: int, minute: int = 0) -> datetime:
    return nth_weekday(year, month, weekday, 1, hour, minute)


def monthly_candidates(start: datetime, builder, months: int = 3) -> list[datetime]:
    base = start.astimezone(ET)
    out = []
    y, m = base.year, base.month
    for i in range(months):
        yy = y + (m - 1 + i) // 12
        mm = ((m - 1 + i) % 12) + 1
        candidate = builder(yy, mm)
        if candidate > base:
            out.append(candidate)
    return out


def add(events: list[CalendarEvent], source: str, report: str, lane: str, dt: datetime, importance: str, schedule_type: str, tracked: list[str], note: str):
    events.append(CalendarEvent(source, report, lane, dt, importance, schedule_type, tracked, note))


def build_calendar(now: datetime) -> dict:
    events: list[CalendarEvent] = []

    # Daily / weekly source updates that affect the scanner directly.
    for dt in business_days(now, 7, 18, 0):
        add(events, "U.S. Treasury", "Daily Treasury Par Yield Curve Rates", "Treasury", dt, "High", "daily expected", ["1M-30Y curve", "2Y", "10Y", "curve spreads"], "Treasury posts daily par yield curve data on business days; publication timing can vary.")

    add(events, "CFTC", "Commitments of Traders", "CFTC COT", next_weekday(now, 4, 15, 30), "High", "weekly expected", ["spec net", "commercial net", "open interest", "weekly change"], "COT is generally released Friday afternoon Eastern, subject to holidays.")
    add(events, "EIA", "Weekly Petroleum Status Report", "EIA", next_weekday(now, 2, 10, 30), "High", "weekly official-pattern", ["crude inventories", "Cushing", "gasoline", "distillate", "refinery utilization"], "WPSR summary/table files are normally released after 10:30 AM ET Wednesday; holidays can shift release.")
    add(events, "EIA", "Weekly Natural Gas Storage Report", "EIA", next_weekday(now, 3, 10, 30), "High", "weekly expected", ["natural gas storage"], "Natural gas storage is normally a Thursday 10:30 AM ET release; holidays can shift release.")
    add(events, "USDA/NASS", "Crop Progress", "USDA", next_weekday(now, 0, 16, 0), "Medium", "weekly seasonal expected", ["crop progress", "crop condition"], "Crop Progress is seasonal and generally Monday afternoon Eastern during the growing season.")
    add(events, "Federal Reserve", "H.4.1 Factors Affecting Reserve Balances", "Federal Reserve", next_weekday(now, 3, 16, 30), "High", "weekly official-pattern", ["Fed assets", "reserve balances", "reverse repo", "TGA"], "H.4.1 is generally a Thursday 4:30 PM ET weekly release.")

    # Monthly/quarterly macro reports. These are release-watch estimates based on common release patterns.
    # They remain useful as a dashboard reminder but are not a substitute for the official agency calendar.
    for dt in monthly_candidates(now, lambda y, m: first_weekday(y, m, 4, 8, 30), 3):
        add(events, "BLS", "Employment Situation", "BLS", dt, "Very High", "monthly expected", ["payrolls", "unemployment", "wages", "participation", "U-6"], "Usually released at 8:30 AM ET on the first Friday; official BLS calendar controls.")
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 2, 2, 8, 30), 3):
        add(events, "BLS", "Consumer Price Index", "BLS", dt, "Very High", "monthly estimated", ["headline CPI", "core CPI", "shelter", "energy", "food"], "Estimated second-Wednesday watch date; official BLS calendar controls.")
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 3, 2, 8, 30), 3):
        add(events, "BLS", "Producer Price Index", "BLS", dt, "High", "monthly estimated", ["headline PPI", "core PPI"], "Estimated second-Thursday watch date; official BLS calendar controls.")
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 5, 4, 8, 30), 3):
        add(events, "BEA", "Personal Income and Outlays / PCE", "BEA", dt, "Very High", "monthly estimated", ["PCE", "core PCE", "personal income", "consumption", "savings rate"], "Estimated late-month watch date; official BEA release schedule controls.")
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 3, 4, 8, 30), 3):
        add(events, "BEA", "GDP / Corporate Profits", "BEA", dt, "High", "quarterly/monthly estimated", ["real GDP", "GDP components", "corporate profits"], "Estimated late-month watch date; official BEA release schedule controls.")
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 2, 3, 8, 30), 3):
        add(events, "Census", "Retail Sales", "Census", dt, "High", "monthly estimated", ["retail sales", "control group"], "Estimated mid-month watch date; official Census calendar controls.")
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 4, 3, 8, 30), 3):
        add(events, "Census", "Housing Starts / Building Permits", "Census", dt, "Medium", "monthly estimated", ["housing starts", "building permits"], "Estimated mid-month watch date; official Census calendar controls.")
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 3, 4, 8, 30), 3):
        add(events, "Census", "Durable Goods", "Census", dt, "Medium", "monthly estimated", ["durable goods orders"], "Estimated late-month watch date; official Census calendar controls.")

    # Sort and keep an actionable near-term window.
    events = sorted(events, key=lambda e: e.event_time)
    horizon = now.astimezone(ET) + timedelta(days=14)
    upcoming = [e for e in events if e.event_time <= horizon]
    if len(upcoming) < 12:
        upcoming = events[:18]
    else:
        upcoming = upcoming[:24]

    return {
        "generatedAt": now.astimezone(UTC).isoformat(),
        "timezone": "America/New_York",
        "windowDays": 14,
        "method": "rule-based release watch generated during source refresh; entries marked estimated when official dates are not fetched directly",
        "events": [e.to_json() for e in upcoming],
    }


def main() -> int:
    now = datetime.now(tz=UTC)
    data = build_calendar(now)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {OUT.relative_to(ROOT)} with {len(data['events'])} upcoming report events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
