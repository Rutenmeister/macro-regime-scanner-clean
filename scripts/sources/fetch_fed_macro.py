#!/usr/bin/env python3
"""Fetch Federal Reserve / liquidity data for Macro Regime Scanner.

This lane intentionally uses public FRED CSV endpoints for Federal Reserve and
New York Fed series, so it does not require a GitHub secret in v0.28.

Series used:
- EFFR: Effective Federal Funds Rate
- WALCL: Fed total assets, H.4.1, millions USD
- WRESBAL: Reserve balances with Federal Reserve Banks, H.4.1, millions USD
- RRPONTSYD: Overnight reverse repo facility, billions USD
- WTREGEN: Treasury General Account at the Fed, H.4.1, millions USD

FRED/Federal Reserve attribution is preserved in raw audit and normalized output.
"""
from __future__ import annotations

import csv
import io
import json
import math
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "fed"
NORM_PATH = ROOT / "data" / "normalized" / "fed_macro.json"
AUDIT_PATH = RAW_DIR / "fed_macro_compact_audit.json"
SOURCE_ID = "FED_FRED_SELECTED"
SOURCE_NAME = "Federal Reserve / FRED public data"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

SERIES = [
    {
        "key": "EFFR",
        "seriesId": "EFFR",
        "label": "Effective federal funds rate",
        "kind": "policy_rate",
        "unit": "percent",
        "frequency": "daily",
        "valueScale": 1.0,
        "sourceNote": "New York Fed effective federal funds rate via FRED.",
    },
    {
        "key": "FED_TOTAL_ASSETS",
        "seriesId": "WALCL",
        "label": "Federal Reserve total assets",
        "kind": "liquidity_supply",
        "unit": "billions USD",
        "frequency": "weekly",
        "valueScale": 0.001,  # FRED series is millions USD.
        "sourceNote": "Board of Governors H.4.1 total assets via FRED; converted from millions to billions USD.",
    },
    {
        "key": "RESERVE_BALANCES",
        "seriesId": "WRESBAL",
        "label": "Reserve balances with Federal Reserve Banks",
        "kind": "liquidity_supply",
        "unit": "billions USD",
        "frequency": "weekly",
        "valueScale": 0.001,  # FRED series is millions USD.
        "sourceNote": "Board of Governors H.4.1 reserve balances via FRED; converted from millions to billions USD.",
    },
    {
        "key": "REVERSE_REPO",
        "seriesId": "RRPONTSYD",
        "label": "Overnight reverse repo usage",
        "kind": "liquidity_drain",
        "unit": "billions USD",
        "frequency": "daily",
        "valueScale": 1.0,
        "sourceNote": "New York Fed overnight reverse repo operations via FRED.",
    },
    {
        "key": "TREASURY_GENERAL_ACCOUNT",
        "seriesId": "WTREGEN",
        "label": "Treasury General Account at the Fed",
        "kind": "liquidity_drain",
        "unit": "billions USD",
        "frequency": "weekly",
        "valueScale": 0.001,  # FRED series is millions USD.
        "sourceNote": "Board of Governors H.4.1 Treasury General Account via FRED; converted from millions to billions USD.",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == ".":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fetch_csv(series_id: str) -> list[dict[str, str]]:
    url = FRED_CSV.format(series_id=series_id)
    req = urllib.request.Request(url, headers={"User-Agent": "MacroRegimeScanner/0.28"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def latest_two(rows: list[dict[str, str]], series_id: str, scale: float) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    points: list[dict[str, Any]] = []
    for row in rows:
        date = row.get("observation_date") or row.get("DATE") or row.get("date")
        raw = row.get(series_id) or row.get("VALUE") or row.get("value")
        value = parse_float(raw)
        if date and value is not None and math.isfinite(value):
            points.append({"date": date, "value": value * scale, "rawValue": value})
    if not points:
        return None, None
    points.sort(key=lambda x: x["date"])
    latest = points[-1]
    previous = points[-2] if len(points) >= 2 else None
    return latest, previous


def score_policy_rate(latest: float | None, change: float | None) -> int | None:
    if latest is None:
        return None
    score = 0
    if latest >= 4.5:
        score = 2
    elif latest >= 3.0:
        score = 1
    elif latest <= 1.0:
        score = -1
    if change is not None:
        if change >= 0.10:
            score += 1
        elif change <= -0.10:
            score -= 1
    return max(-2, min(2, score))


def score_liquidity(kind: str, change: float | None) -> int | None:
    if change is None:
        return None
    # For supply series, rising = easier liquidity; falling = tightening.
    # For drain series (RRP/TGA), falling drain = easier liquidity; rising drain = tightening.
    if kind == "liquidity_supply":
        if change >= 50:
            return 2
        if change > 0:
            return 1
        if change <= -50:
            return -2
        if change < 0:
            return -1
        return 0
    if kind == "liquidity_drain":
        if change <= -50:
            return 2
        if change < 0:
            return 1
        if change >= 50:
            return -2
        if change > 0:
            return -1
        return 0
    return 0


def build_observation(spec: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    series_id = spec["seriesId"]
    audit: dict[str, Any] = {"seriesId": series_id, "label": spec["label"], "status": "started"}
    try:
        rows = fetch_csv(series_id)
        latest, previous = latest_two(rows, series_id, float(spec.get("valueScale", 1.0)))
        audit["rowsFetched"] = len(rows)
        if not latest:
            audit["status"] = "no_observations"
            return None, audit
        latest_value = latest["value"]
        previous_value = previous["value"] if previous else None
        change = latest_value - previous_value if previous_value is not None else None
        kind = spec["kind"]
        score = score_policy_rate(latest_value, change) if kind == "policy_rate" else score_liquidity(kind, change)
        obs = {
            "sourceId": SOURCE_ID,
            "sourceName": SOURCE_NAME,
            "seriesId": series_id,
            "key": spec["key"],
            "label": spec["label"],
            "kind": kind,
            "latestValue": round(latest_value, 4),
            "previousValue": round(previous_value, 4) if previous_value is not None else None,
            "change": round(change, 4) if change is not None else None,
            "unit": spec["unit"],
            "period": latest["date"],
            "previousPeriod": previous["date"] if previous else None,
            "releaseDate": latest["date"],
            "retrievedAt": now_iso(),
            "frequency": spec["frequency"],
            "score": score,
            "sourceNote": spec["sourceNote"],
        }
        audit.update({"status": "ok", "latestPeriod": latest["date"], "latestValue": obs["latestValue"], "score": score})
        return obs, audit
    except urllib.error.HTTPError as exc:
        audit.update({"status": "http_error", "error": str(exc)})
        return None, audit
    except Exception as exc:  # noqa: BLE001
        audit.update({"status": "error", "error": str(exc)})
        return None, audit


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_PATH.parent.mkdir(parents=True, exist_ok=True)
    observations: dict[str, Any] = {}
    audits: list[dict[str, Any]] = []
    for spec in SERIES:
        observation, audit = build_observation(spec)
        audits.append(audit)
        if observation:
            observations[spec["key"]] = observation
    if not observations:
        raise SystemExit("Fed/FRED fetch did not produce any normalized observations.")
    latest_dates = [o["period"] for o in observations.values() if o.get("period")]
    normalized = {
        "schemaVersion": "0.28",
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "retrievedAt": now_iso(),
        "latestDate": max(latest_dates) if latest_dates else None,
        "observations": observations,
        "notes": [
            "Public Federal Reserve/FRED liquidity lane. No API key required in v0.28.",
            "FRED graph CSV endpoint is used for selected Federal Reserve and New York Fed series.",
            "Balance sheet/TGA/reserve series from H.4.1 are converted from millions to billions USD where needed.",
        ],
    }
    audit_doc = {
        "schemaVersion": "0.28",
        "sourceId": SOURCE_ID,
        "retrievedAt": now_iso(),
        "seriesAudits": audits,
        "observationCount": len(observations),
    }
    NORM_PATH.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    AUDIT_PATH.write_text(json.dumps(audit_doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {NORM_PATH.relative_to(ROOT)} with {len(observations)} observations")
    print(f"Wrote {AUDIT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
