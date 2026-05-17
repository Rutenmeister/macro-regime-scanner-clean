#!/usr/bin/env python3
"""Fetch credit-spread and financial-stress indicators for Macro Regime Scanner.

Uses public FRED endpoints with two fallback formats:
1) graph/fredgraph.csv?id=SERIES
2) data/SERIES plain text table

No API key is required. This lane is intended to add official/public credit and
financial-condition context without using price-derived technical indicators.
"""
from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "financial_stress"
NORM_PATH = ROOT / "data" / "normalized" / "financial_stress.json"
AUDIT_PATH = RAW_DIR / "financial_stress_compact_audit.json"
SOURCE_ID = "FINANCIAL_STRESS_FRED"
SOURCE_NAME = "Federal Reserve / FRED credit and financial-stress public data"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
FRED_DATA = "https://fred.stlouisfed.org/data/{series_id}"

SERIES = [
    {
        "key": "HY_OAS",
        "seriesId": "BAMLH0A0HYM2",
        "label": "ICE BofA US High Yield Option-Adjusted Spread",
        "kind": "credit_spread",
        "unit": "percent",
        "frequency": "daily",
        "sourceNote": "ICE BofA US High Yield Index OAS via FRED.",
        "thresholds": {"tight": 3.0, "normal": 4.0, "stress": 5.5},
        "changeThreshold": 0.25,
    },
    {
        "key": "IG_OAS",
        "seriesId": "BAMLC0A0CM",
        "label": "ICE BofA US Corporate Option-Adjusted Spread",
        "kind": "credit_spread",
        "unit": "percent",
        "frequency": "daily",
        "sourceNote": "ICE BofA US Corporate Index OAS via FRED.",
        "thresholds": {"tight": 0.90, "normal": 1.25, "stress": 1.75},
        "changeThreshold": 0.12,
    },
    {
        "key": "BBB_OAS",
        "seriesId": "BAMLC0A4CBBB",
        "label": "ICE BofA BBB US Corporate Option-Adjusted Spread",
        "kind": "credit_spread",
        "unit": "percent",
        "frequency": "daily",
        "sourceNote": "ICE BofA BBB US Corporate Index OAS via FRED.",
        "thresholds": {"tight": 1.40, "normal": 2.00, "stress": 2.75},
        "changeThreshold": 0.15,
    },
    {
        "key": "NFCI",
        "seriesId": "NFCI",
        "label": "Chicago Fed National Financial Conditions Index",
        "kind": "financial_conditions",
        "unit": "index",
        "frequency": "weekly",
        "sourceNote": "Chicago Fed National Financial Conditions Index via FRED. Positive values indicate tighter-than-average financial conditions.",
        "thresholds": {"easy": -0.50, "tight": 0.00, "stress": 0.50},
        "changeThreshold": 0.10,
    },
    {
        "key": "ANFCI",
        "seriesId": "ANFCI",
        "label": "Chicago Fed Adjusted National Financial Conditions Index",
        "kind": "financial_conditions",
        "unit": "index",
        "frequency": "weekly",
        "sourceNote": "Chicago Fed adjusted NFCI via FRED. Positive values indicate tighter financial conditions after controlling for economic conditions.",
        "thresholds": {"easy": -0.40, "tight": 0.00, "stress": 0.40},
        "changeThreshold": 0.10,
    },
    {
        "key": "STLFSI4",
        "seriesId": "STLFSI4",
        "label": "St. Louis Fed Financial Stress Index",
        "kind": "financial_stress",
        "unit": "index",
        "frequency": "weekly",
        "sourceNote": "St. Louis Fed Financial Stress Index via FRED. Positive values indicate above-average financial stress.",
        "thresholds": {"easy": -0.50, "tight": 0.00, "stress": 0.75},
        "changeThreshold": 0.15,
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


def fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MacroRegimeScanner/0.30",
            "Accept": "text/csv,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read().decode("utf-8", errors="replace")


def rows_from_graph_csv(series_id: str) -> list[dict[str, str]]:
    text = fetch_url(FRED_CSV.format(series_id=series_id))
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def rows_from_data_txt(series_id: str) -> list[dict[str, str]]:
    text = fetch_url(FRED_DATA.format(series_id=series_id))
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) >= 2 and parts[0].count("-") == 2:
            rows.append({"DATE": parts[0], series_id: parts[1], "VALUE": parts[1]})
    return rows


def fetch_rows(series_id: str, audit_record: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[str] = []
    for method_name, fn in (("fredgraph_csv", rows_from_graph_csv), ("fred_data_txt", rows_from_data_txt)):
        try:
            rows = fn(series_id)
            audit_record.setdefault("fetchAttempts", []).append({"method": method_name, "rows": len(rows)})
            if rows:
                return rows
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{method_name}: {exc}")
            audit_record.setdefault("fetchAttempts", []).append({"method": method_name, "error": str(exc)})
    if errors:
        audit_record["fetchErrors"] = errors
    return []


def latest_two(rows: list[dict[str, str]], series_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    points: list[dict[str, Any]] = []
    for row in rows:
        date = row.get("observation_date") or row.get("DATE") or row.get("date")
        raw = row.get(series_id) or row.get(series_id.lower()) or row.get(series_id.upper()) or row.get("VALUE") or row.get("value")
        value = parse_float(raw)
        if date and value is not None and math.isfinite(value):
            points.append({"date": date, "value": value})
    if not points:
        return None, None
    points.sort(key=lambda x: x["date"])
    latest = points[-1]
    previous = points[-2] if len(points) >= 2 else None
    return latest, previous


def score_credit_spread(latest: float | None, change: float | None, thresholds: dict[str, float], change_threshold: float) -> int | None:
    if latest is None:
        return None
    # Positive score = easing/supportive credit conditions. Negative score = widening/tighter stress.
    if latest >= thresholds["stress"]:
        score = -2
    elif latest >= thresholds["normal"]:
        score = -1
    elif latest <= thresholds["tight"]:
        score = 1
    else:
        score = 0
    if change is not None:
        if change >= change_threshold:
            score -= 1
        elif change <= -change_threshold:
            score += 1
    return max(-2, min(2, score))


def score_stress_index(latest: float | None, change: float | None, thresholds: dict[str, float], change_threshold: float) -> int | None:
    if latest is None:
        return None
    # Positive score = easier/less stressed conditions. Negative score = tighter/stressed conditions.
    if latest >= thresholds["stress"]:
        score = -2
    elif latest >= thresholds["tight"]:
        score = -1
    elif latest <= thresholds["easy"]:
        score = 1
    else:
        score = 0
    if change is not None:
        if change >= change_threshold:
            score -= 1
        elif change <= -change_threshold:
            score += 1
    return max(-2, min(2, score))


def build_observation(meta: dict[str, Any], audit_record: dict[str, Any]) -> dict[str, Any] | None:
    rows = fetch_rows(meta["seriesId"], audit_record)
    latest, previous = latest_two(rows, meta["seriesId"])
    if not latest:
        audit_record["status"] = "missing_observations"
        return None
    prev_value = previous["value"] if previous else None
    change = latest["value"] - prev_value if prev_value is not None else None
    if meta["kind"] == "credit_spread":
        score = score_credit_spread(latest["value"], change, meta["thresholds"], meta["changeThreshold"])
    else:
        score = score_stress_index(latest["value"], change, meta["thresholds"], meta["changeThreshold"])
    audit_record["status"] = "ok"
    audit_record["latestDate"] = latest["date"]
    return {
        "key": meta["key"],
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "seriesId": meta["seriesId"],
        "label": meta["label"],
        "kind": meta["kind"],
        "unit": meta["unit"],
        "frequency": meta["frequency"],
        "latestValue": latest["value"],
        "previousValue": prev_value,
        "change": change,
        "period": latest["date"],
        "previousPeriod": previous["date"] if previous else None,
        "score": score,
        "retrievedAt": now_iso(),
        "sourceNote": meta["sourceNote"],
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_PATH.parent.mkdir(parents=True, exist_ok=True)
    audit: dict[str, Any] = {
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "retrievedAt": now_iso(),
        "series": {},
    }
    observations: dict[str, Any] = {}
    errors: list[str] = []
    for meta in SERIES:
        record: dict[str, Any] = {"seriesId": meta["seriesId"], "label": meta["label"]}
        try:
            observation = build_observation(meta, record)
            if observation:
                observations[meta["key"]] = observation
            else:
                errors.append(f"{meta['seriesId']}: no observations parsed")
        except Exception as exc:  # noqa: BLE001
            record["status"] = "error"
            record["error"] = str(exc)
            errors.append(f"{meta['seriesId']}: {exc}")
        audit["series"][meta["key"]] = record

    audit["observationCount"] = len(observations)
    audit["errors"] = errors
    AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    if not observations:
        raise SystemExit("Financial stress fetch did not produce any normalized observations.")

    latest_dates = [o.get("period") for o in observations.values() if o.get("period")]
    normalized = {
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "retrievedAt": now_iso(),
        "latestDate": max(latest_dates) if latest_dates else None,
        "observations": observations,
        "auditPath": str(AUDIT_PATH.relative_to(ROOT)),
    }
    NORM_PATH.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {NORM_PATH.relative_to(ROOT)} with {len(observations)} observations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
