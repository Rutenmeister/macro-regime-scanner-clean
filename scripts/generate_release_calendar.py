#!/usr/bin/env python3
"""Generate the Macro Regime Scanner upcoming-report calendar.

v0.41 hardens the old rule-based release watch by:
- preferring official agency dates when known/available,
- attaching calendarConfidence to every event,
- skipping U.S. federal holidays for daily Treasury releases,
- moving holiday-sensitive weekly reports when a federal holiday disrupts the week,
- visibly downgrading estimated entries instead of letting them look confirmed.

This calendar is informational only. It is separate from scoring.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "release_calendar.json"
ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# Minimal federal-holiday table used to prevent obvious false daily release rows.
# Add future years as needed. This is intentionally explicit rather than vague.
US_FEDERAL_HOLIDAYS = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # Martin Luther King Jr. Day
    date(2026, 2, 16),  # Washington's Birthday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day observed
    date(2026, 9, 7),   # Labor Day
    date(2026, 10, 12), # Columbus Day
    date(2026, 11, 11), # Veterans Day
    date(2026, 11, 26), # Thanksgiving Day
    date(2026, 12, 25), # Christmas Day
}

SOURCE_URLS = {
    "Treasury": "https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics",
    "CFTC": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm",
    "EIA_WPSR": "https://www.eia.gov/petroleum/supply/weekly/schedule.php",
    "EIA_NG": "https://ir.eia.gov/ngs/schedule.html",
    "Fed_H41": "https://www.federalreserve.gov/releases/h41/",
    "BEA": "https://www.bea.gov/news/schedule",
    "Census": "https://www.census.gov/economic-indicators/calendar-listview-2026.html",
    "USDA_NASS": "https://www.nass.usda.gov/Publications/Calendar/",
    "BLS": "https://www.bls.gov/schedule/news_release/",
}

# Official/confirmed upcoming dates that replace weak pattern guesses.
# These prevent errors like Retail Sales May 20 and PCE May 23.
OFFICIAL_RELEASES_2026 = [
    {
        "source": "Census",
        "report": "New Residential Construction / Housing Starts and Building Permits",
        "lane": "Census",
        "date": "2026-05-21",
        "hour": 8,
        "minute": 30,
        "importance": "Medium",
        "tracked": ["housing starts", "building permits"],
        "confidence": "official",
        "schedule_type": "official calendar",
        "source_url": SOURCE_URLS["Census"],
        "note": "Official Census economic-indicator calendar date for the April residential construction release.",
    },
    {
        "source": "BEA",
        "report": "GDP (Second Estimate) and Corporate Profits, Q1 2026",
        "lane": "BEA",
        "date": "2026-05-28",
        "hour": 8,
        "minute": 30,
        "importance": "High",
        "tracked": ["real GDP", "GDP components", "corporate profits"],
        "confidence": "official",
        "schedule_type": "official calendar",
        "source_url": SOURCE_URLS["BEA"],
        "note": "Official BEA release schedule date.",
    },
    {
        "source": "BEA",
        "report": "Personal Income and Outlays / PCE, April 2026",
        "lane": "BEA",
        "date": "2026-05-28",
        "hour": 8,
        "minute": 30,
        "importance": "Very High",
        "tracked": ["PCE", "core PCE", "personal income", "consumption", "savings rate"],
        "confidence": "official",
        "schedule_type": "official calendar",
        "source_url": SOURCE_URLS["BEA"],
        "note": "Official BEA release schedule date. Replaces the old estimated May 23 watch date.",
    },
    {
        "source": "Census",
        "report": "Advance Report on Durable Goods Manufacturers' Shipments, Inventories, and Orders",
        "lane": "Census",
        "date": "2026-05-28",
        "hour": 8,
        "minute": 30,
        "importance": "Medium",
        "tracked": ["durable goods orders", "core capital goods"],
        "confidence": "official",
        "schedule_type": "official calendar",
        "source_url": SOURCE_URLS["Census"],
        "note": "Official Census economic-indicator calendar date for the advance durable goods report.",
    },
    {
        "source": "Census",
        "report": "Advance Monthly Sales for Retail and Food Services / Retail Sales",
        "lane": "Census",
        "date": "2026-06-17",
        "hour": 8,
        "minute": 30,
        "importance": "High",
        "tracked": ["retail sales", "control group"],
        "confidence": "official",
        "schedule_type": "official calendar",
        "source_url": SOURCE_URLS["Census"],
        "note": "Official Census date for the next retail sales release. Removes the incorrect May 20 estimated event.",
    },
    {
        "source": "BEA",
        "report": "Personal Income and Outlays / PCE, May 2026",
        "lane": "BEA",
        "date": "2026-06-25",
        "hour": 8,
        "minute": 30,
        "importance": "Very High",
        "tracked": ["PCE", "core PCE", "personal income", "consumption", "savings rate"],
        "confidence": "official",
        "schedule_type": "official calendar",
        "source_url": SOURCE_URLS["BEA"],
        "note": "Official BEA release schedule date for the following PCE release.",
    },
]


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
    calendar_confidence: str
    source_url: str

    def key(self) -> tuple[str, str, str]:
        return (self.report.lower(), self.source.lower(), self.event_time.date().isoformat())

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
            "calendarConfidence": self.calendar_confidence,
            "sourceUrl": self.source_url,
            "trackedInputs": self.tracked_inputs,
            "note": self.note,
        }


def at_et(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), ET)


def is_business_day(day: date) -> bool:
    return day.weekday() < 5 and day not in US_FEDERAL_HOLIDAYS


def week_has_federal_holiday(day: date) -> bool:
    monday = day - timedelta(days=day.weekday())
    return any((monday + timedelta(days=i)) in US_FEDERAL_HOLIDAYS for i in range(5))


def next_weekday(start: datetime, weekday: int, hour: int, minute: int = 0, include_today: bool = True) -> datetime:
    base = start.astimezone(ET)
    days = (weekday - base.weekday()) % 7
    candidate = at_et((base + timedelta(days=days)).date(), hour, minute)
    if days == 0 and (not include_today or candidate <= base):
        candidate += timedelta(days=7)
    return candidate


def business_days(start: datetime, count: int, hour: int, minute: int = 0) -> list[datetime]:
    base = start.astimezone(ET)
    day = base.date()
    out: list[datetime] = []
    while len(out) < count:
        if is_business_day(day):
            candidate = at_et(day, hour, minute)
            if candidate > base:
                out.append(candidate)
        day = day + timedelta(days=1)
    return out


def nth_weekday(year: int, month: int, weekday: int, n: int, hour: int, minute: int = 0) -> datetime:
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    target = d + timedelta(days=offset + (n - 1) * 7)
    return at_et(target, hour, minute)


def first_weekday(year: int, month: int, weekday: int, hour: int, minute: int = 0) -> datetime:
    return nth_weekday(year, month, weekday, 1, hour, minute)


def monthly_candidates(start: datetime, builder, months: int = 3) -> list[datetime]:
    base = start.astimezone(ET)
    out: list[datetime] = []
    y, m = base.year, base.month
    for i in range(months):
        yy = y + (m - 1 + i) // 12
        mm = ((m - 1 + i) % 12) + 1
        candidate = builder(yy, mm)
        if candidate > base:
            out.append(candidate)
    return out


def add(events: list[CalendarEvent], source: str, report: str, lane: str, dt: datetime, importance: str, schedule_type: str, tracked: list[str], note: str, confidence: str, source_url: str):
    events.append(CalendarEvent(source, report, lane, dt, importance, schedule_type, tracked, note, confidence, source_url))


def add_official_events(events: list[CalendarEvent], now: datetime) -> None:
    base = now.astimezone(ET)
    for item in OFFICIAL_RELEASES_2026:
        dt = at_et(date.fromisoformat(item["date"]), item["hour"], item["minute"])
        if dt <= base:
            continue
        add(
            events,
            item["source"],
            item["report"],
            item["lane"],
            dt,
            item["importance"],
            item["schedule_type"],
            item["tracked"],
            item["note"],
            item["confidence"],
            item["source_url"],
        )


def add_weekly_pattern_events(events: list[CalendarEvent], now: datetime) -> None:
    # Treasury daily curve: business days only, with U.S. federal holidays excluded.
    for dt in business_days(now, 9, 18, 0):
        add(events, "U.S. Treasury", "Daily Treasury Par Yield Curve Rates", "Treasury", dt, "High", "official-pattern", ["1M-30Y curve", "2Y", "10Y", "curve spreads"], "Treasury posts daily par yield curve data on business days; U.S. federal holidays are skipped by v0.41.", "official-pattern", SOURCE_URLS["Treasury"])

    # CFTC COT: official release pattern, holiday caveat.
    cot_dt = next_weekday(now, 4, 15, 30)
    add(events, "CFTC", "Commitments of Traders", "CFTC COT", cot_dt, "High", "official-pattern", ["spec net", "commercial net", "open interest", "weekly change"], "CFTC states COT reports are usually released Friday at 3:30 PM ET; federal holidays may delay release.", "official-pattern", SOURCE_URLS["CFTC"])

    # EIA WPSR: official current next release if May 20; otherwise official-pattern with holiday shift.
    wpsr = next_weekday(now, 2, 10, 30)
    if week_has_federal_holiday(wpsr.date()):
        wpsr = wpsr + timedelta(days=1)
        note = "Holiday-adjusted official-pattern estimate: EIA says WPSR releases are normally Wednesday 10:30 AM ET but some holiday weeks are delayed by one day."
    else:
        note = "EIA WPSR files are normally released after 10:30 AM ET Wednesday. Current public WPSR page should be treated as source of truth for exact next release."
    add(events, "EIA", "Weekly Petroleum Status Report", "EIA", wpsr, "High", "official-pattern", ["crude inventories", "Cushing", "gasoline", "distillate", "refinery utilization"], note, "official-pattern", SOURCE_URLS["EIA_WPSR"])

    # EIA natural gas storage: official pattern with source link. Keep Thursday unless official page specifies holiday shift.
    ng = next_weekday(now, 3, 10, 30)
    add(events, "EIA", "Weekly Natural Gas Storage Report", "EIA", ng, "High", "official-pattern", ["natural gas storage"], "EIA natural gas storage schedule is normally Thursday 10:30 AM ET; official schedule page controls holiday exceptions.", "official-pattern", SOURCE_URLS["EIA_NG"])

    # Fed H.4.1: official pattern.
    h41 = next_weekday(now, 3, 16, 30)
    add(events, "Federal Reserve", "H.4.1 Factors Affecting Reserve Balances", "Federal Reserve", h41, "High", "official-pattern", ["Fed assets", "reserve balances", "reverse repo", "TGA"], "Federal Reserve says H.4.1 data are released each Thursday, generally at 4:30 PM ET; holidays can shift release.", "official-pattern", SOURCE_URLS["Fed_H41"])

    # USDA/NASS Crop Progress: seasonal official-pattern. Skip federal holiday Mondays and use next business day as tentative.
    crop = next_weekday(now, 0, 16, 0)
    if not is_business_day(crop.date()):
        day = crop.date() + timedelta(days=1)
        while not is_business_day(day):
            day += timedelta(days=1)
        crop = at_et(day, 16, 0)
        note = "Holiday-adjusted seasonal estimate. NASS official report calendar should control exact release date."
        confidence = "estimated"
    else:
        note = "Crop Progress is seasonal and generally Monday afternoon Eastern during the growing season; NASS calendar controls exact release."
        confidence = "official-pattern"
    add(events, "USDA/NASS", "Crop Progress", "USDA", crop, "Medium", "seasonal official-pattern", ["crop progress", "crop condition"], note, confidence, SOURCE_URLS["USDA_NASS"])


def add_low_confidence_watch_items(events: list[CalendarEvent], now: datetime) -> None:
    # These stay available as reminders only, but they are clearly tagged as estimated.
    # Official overrides above should cover the highest-risk near-term BEA/Census dates.
    for dt in monthly_candidates(now, lambda y, m: first_weekday(y, m, 4, 8, 30), 3):
        add(events, "BLS", "Employment Situation", "BLS", dt, "Very High", "monthly estimated", ["payrolls", "unemployment", "wages", "participation", "U-6"], "Estimated first-Friday watch date; official BLS calendar controls.", "estimated", SOURCE_URLS["BLS"])
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 2, 2, 8, 30), 3):
        add(events, "BLS", "Consumer Price Index", "BLS", dt, "Very High", "monthly estimated", ["headline CPI", "core CPI", "shelter", "energy", "food"], "Estimated second-Wednesday watch date; official BLS calendar controls.", "estimated", SOURCE_URLS["BLS"])
    for dt in monthly_candidates(now, lambda y, m: nth_weekday(y, m, 3, 2, 8, 30), 3):
        add(events, "BLS", "Producer Price Index", "BLS", dt, "High", "monthly estimated", ["headline PPI", "core PPI"], "Estimated second-Thursday watch date; official BLS calendar controls.", "estimated", SOURCE_URLS["BLS"])


def dedupe_events(events: list[CalendarEvent]) -> list[CalendarEvent]:
    # Official beats official-pattern; official-pattern beats estimated.
    rank = {"official": 3, "official-pattern": 2, "estimated": 1}
    best: dict[tuple[str, str], CalendarEvent] = {}
    for ev in events:
        # Deduplicate by report + lane, but allow repeated daily Treasury events.
        if ev.report == "Daily Treasury Par Yield Curve Rates":
            best[(ev.report.lower(), ev.event_time.isoformat())] = ev
            continue
        key = (ev.report.lower(), ev.lane.lower())
        current = best.get(key)
        if current is None:
            best[key] = ev
            continue
        if rank.get(ev.calendar_confidence, 0) > rank.get(current.calendar_confidence, 0):
            best[key] = ev
        elif rank.get(ev.calendar_confidence, 0) == rank.get(current.calendar_confidence, 0) and ev.event_time < current.event_time:
            best[key] = ev
    return sorted(best.values(), key=lambda e: e.event_time)


def build_calendar(now: datetime) -> dict:
    events: list[CalendarEvent] = []
    add_official_events(events, now)
    add_weekly_pattern_events(events, now)
    add_low_confidence_watch_items(events, now)

    events = dedupe_events(events)
    horizon = now.astimezone(ET) + timedelta(days=21)
    upcoming = [e for e in events if e.event_time <= horizon]
    if len(upcoming) < 12:
        upcoming = events[:20]
    else:
        upcoming = upcoming[:28]

    official_count = sum(1 for e in upcoming if e.calendar_confidence == "official")
    pattern_count = sum(1 for e in upcoming if e.calendar_confidence == "official-pattern")
    estimated_count = sum(1 for e in upcoming if e.calendar_confidence == "estimated")

    return {
        "generatedAt": now.astimezone(UTC).isoformat(),
        "timezone": "America/New_York",
        "windowDays": 21,
        "version": "v0.41-official-calendar-hardening",
        "method": "official-date overrides + official-pattern recurring releases + visibly tagged estimates; scoring is unaffected",
        "confidenceSummary": {
            "official": official_count,
            "officialPattern": pattern_count,
            "estimated": estimated_count,
        },
        "events": [e.to_json() for e in upcoming],
    }


def main() -> int:
    now = datetime.now(tz=UTC)
    data = build_calendar(now)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {OUT.relative_to(ROOT)} with {len(data['events'])} upcoming report events.")
    print(f"Confidence summary: {data['confidenceSummary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
