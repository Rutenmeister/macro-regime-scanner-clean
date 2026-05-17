#!/usr/bin/env python3
"""Fetch NOAA/NWS public weather hazard context for Macro Regime Scanner.

This lane intentionally uses official NOAA/National Weather Service public API
endpoints that do not require an API key. It is not a model forecast lane and it
is not a paid-data feed. It captures live U.S. weather-hazard context that can
matter for energy demand, agriculture supply risk, transport disruption, and
broad macro/commodity context.

Primary endpoint:
    https://api.weather.gov/alerts/active?status=actual&message_type=alert

Output:
    data/raw/noaa/noaa_weather_compact_audit.json
    data/normalized/noaa_weather.json
"""
from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "noaa"
AUDIT_PATH = RAW_DIR / "noaa_weather_compact_audit.json"
NORM_PATH = ROOT / "data" / "normalized" / "noaa_weather.json"
SOURCE_ID = "NOAA_NWS"
SOURCE_NAME = "NOAA/National Weather Service public weather alerts"
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active?status=actual&message_type=alert"

CATEGORY_RULES = {
    "HEAT_STRESS": {
        "label": "NOAA heat stress alerts",
        "kind": "heat_stress",
        "keywords": ["excessive heat", "heat advisory", "extreme heat"],
        "description": "Heat-related alerts can affect cooling demand, power load, crop stress, labor productivity, and livestock/agriculture risk.",
    },
    "COLD_FREEZE_STRESS": {
        "label": "NOAA cold / freeze alerts",
        "kind": "cold_freeze_stress",
        "keywords": ["freeze", "frost", "wind chill", "extreme cold", "hard freeze"],
        "description": "Cold/freeze alerts can affect heating demand, natural gas use, crop/freeze risk, and transport conditions.",
    },
    "WINTER_STORM_STRESS": {
        "label": "NOAA winter storm alerts",
        "kind": "winter_storm_stress",
        "keywords": ["winter storm", "blizzard", "ice storm", "snow squall", "heavy snow", "lake effect snow"],
        "description": "Winter storm alerts can affect heating demand, logistics, refinery/transport operations, and broad activity disruptions.",
    },
    "FLOOD_STRESS": {
        "label": "NOAA flood alerts",
        "kind": "flood_stress",
        "keywords": ["flood", "flash flood", "coastal flood", "river flood"],
        "description": "Flood alerts can disrupt transport, agriculture, energy infrastructure, and local economic activity.",
    },
    "SEVERE_CONVECTIVE_STRESS": {
        "label": "NOAA severe storm / tornado alerts",
        "kind": "severe_convective_stress",
        "keywords": ["tornado", "severe thunderstorm", "derecho"],
        "description": "Severe storm/tornado alerts can disrupt logistics, local activity, agriculture, and infrastructure.",
    },
    "TROPICAL_STORM_STRESS": {
        "label": "NOAA tropical storm / hurricane alerts",
        "kind": "tropical_storm_stress",
        "keywords": ["hurricane", "tropical storm", "storm surge", "tropical depression"],
        "description": "Tropical alerts can affect Gulf energy infrastructure, ports, refined products, insurance losses, and logistics.",
    },
    "FIRE_WEATHER_STRESS": {
        "label": "NOAA fire weather alerts",
        "kind": "fire_weather_stress",
        "keywords": ["red flag", "fire weather", "extreme fire danger"],
        "description": "Fire-weather alerts can affect crops, power infrastructure, insurance risk, timber/soft commodities, and regional activity.",
    },
    "DROUGHT_STRESS": {
        "label": "NOAA drought alerts",
        "kind": "drought_stress",
        "keywords": ["drought"],
        "description": "Drought alerts are direct crop/water stress context when present, but active NWS alert feeds may underrepresent slower drought conditions.",
    },
}

SEVERITY_WEIGHT = {
    "Extreme": 4,
    "Severe": 3,
    "Moderate": 2,
    "Minor": 1,
    "Unknown": 1,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MacroRegimeScanner/0.31 (public NOAA/NWS API; contact: rutenmeister.github.io)",
            "Accept": "application/geo+json,application/json,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def event_matches(event: str, keywords: list[str]) -> bool:
    text = event.lower()
    return any(k in text for k in keywords)


def score_from_count(count: int, weighted_count: int, total_alerts: int) -> int:
    # Score convention: positive = calm/low weather stress, negative = weather hazard/disruption.
    if count == 0:
        return 1
    if weighted_count >= 80 or count >= 50:
        return -2
    if weighted_count >= 20 or count >= 12:
        return -1
    if total_alerts >= 150 and count >= 5:
        return -1
    return 0


def total_score(total_alerts: int, weighted_total: int) -> int:
    if total_alerts == 0:
        return 1
    if weighted_total >= 250 or total_alerts >= 175:
        return -2
    if weighted_total >= 90 or total_alerts >= 60:
        return -1
    return 0


def main() -> int:
    retrieved_at = now_iso()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_PATH.parent.mkdir(parents=True, exist_ok=True)

    audit: dict[str, Any] = {
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "retrievedAt": retrieved_at,
        "endpoint": NWS_ALERTS_URL,
        "fetchAttempts": [],
        "categoryCounts": {},
        "eventCountsTop": [],
    }

    data = fetch_json(NWS_ALERTS_URL)
    features = data.get("features", []) if isinstance(data, dict) else []
    audit["fetchAttempts"].append({"endpoint": NWS_ALERTS_URL, "features": len(features)})

    event_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    category_counts: dict[str, Counter[str]] = {key: Counter() for key in CATEGORY_RULES}
    sample_events: dict[str, list[str]] = {key: [] for key in CATEGORY_RULES}
    active_alerts: list[dict[str, Any]] = []
    latest_effective = None

    for feature in features:
        props = feature.get("properties", {}) if isinstance(feature, dict) else {}
        event = clean_text(props.get("event")) or "Unknown event"
        severity = clean_text(props.get("severity")) or "Unknown"
        effective = clean_text(props.get("effective") or props.get("sent"))
        area = clean_text(props.get("areaDesc"))
        headline = clean_text(props.get("headline"))

        event_counts[event] += 1
        severity_counts[severity] += 1
        weight = SEVERITY_WEIGHT.get(severity, 1)
        if effective and (latest_effective is None or effective > latest_effective):
            latest_effective = effective

        active_alerts.append({
            "event": event,
            "severity": severity,
            "effective": effective,
            "area": area[:240],
            "headline": headline[:240],
        })

        for key, rule in CATEGORY_RULES.items():
            if event_matches(event, rule["keywords"]):
                category_counts[key]["count"] += 1
                category_counts[key]["weighted"] += weight
                if len(sample_events[key]) < 5:
                    sample_events[key].append(event)

    total_alerts = len(features)
    weighted_total = sum(SEVERITY_WEIGHT.get(a.get("severity", "Unknown"), 1) for a in active_alerts)

    observations: dict[str, Any] = {}
    observations["ACTIVE_ALERTS"] = {
        "key": "ACTIVE_ALERTS",
        "seriesId": "NWS_ACTIVE_ALERTS",
        "label": "NOAA/NWS active weather alerts",
        "kind": "weather_hazard_total",
        "latestValue": total_alerts,
        "previousValue": None,
        "change": None,
        "unit": "alerts",
        "period": retrieved_at[:10],
        "previousPeriod": None,
        "releaseDate": latest_effective or retrieved_at,
        "retrievedAt": retrieved_at,
        "frequency": "intraday",
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "score": total_score(total_alerts, weighted_total),
        "sourceNote": "NOAA/NWS active alerts endpoint. Positive score means low national active weather-hazard load; negative score means elevated active weather disruption.",
        "sampleEvents": [k for k, _ in event_counts.most_common(8)],
    }

    for key, rule in CATEGORY_RULES.items():
        count = int(category_counts[key].get("count", 0))
        weighted = int(category_counts[key].get("weighted", 0))
        observations[key] = {
            "key": key,
            "seriesId": f"NWS_{key}",
            "label": rule["label"],
            "kind": rule["kind"],
            "latestValue": count,
            "previousValue": None,
            "change": None,
            "unit": "alerts",
            "period": retrieved_at[:10],
            "previousPeriod": None,
            "releaseDate": latest_effective or retrieved_at,
            "retrievedAt": retrieved_at,
            "frequency": "intraday",
            "sourceId": SOURCE_ID,
            "sourceName": SOURCE_NAME,
            "score": score_from_count(count, weighted, total_alerts),
            "sourceNote": rule["description"],
            "weightedCount": weighted,
            "sampleEvents": sample_events[key],
        }
        audit["categoryCounts"][key] = {"count": count, "weighted": weighted, "sampleEvents": sample_events[key]}

    audit["totalActiveAlerts"] = total_alerts
    audit["weightedActiveAlerts"] = weighted_total
    audit["severityCounts"] = dict(severity_counts)
    audit["eventCountsTop"] = event_counts.most_common(25)
    audit["sampleAlerts"] = active_alerts[:50]

    normalized = {
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "retrievedAt": retrieved_at,
        "latestDate": latest_effective or retrieved_at[:10],
        "endpoint": NWS_ALERTS_URL,
        "observations": observations,
        "notes": [
            "This lane uses NOAA/NWS active public alerts as live weather-hazard context.",
            "It is not a full drought monitor, seasonal forecast, or global weather model feed.",
            "Scores are disruption/context scores, not trade signals.",
        ],
    }

    AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    NORM_PATH.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {NORM_PATH.relative_to(ROOT)} with {len(observations)} NOAA/NWS weather observations")
    print(f"Wrote {AUDIT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
