#!/usr/bin/env python3
"""Fetch Census real-economy indicators for Macro Regime Scanner.

This v0.29 lane targets U.S. Census Bureau economic-activity variables that
help explain demand, housing, manufacturing, and inventory pressure.

The Census Economic Indicators Time Series (EITS) API is keyed. The script also
uses public FRED CSV mirrors for selected Census/Bureau of Economic Analysis
indicator series so the lane can stay operational if a specific Census EITS
query changes. The normalized output preserves series/source notes so the UI can
show provenance honestly.

Optional environment variable:
    CENSUS_API_KEY
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "census"
NORM_PATH = ROOT / "data" / "normalized" / "census_macro.json"
AUDIT_PATH = RAW_DIR / "census_macro_compact_audit.json"
SOURCE_ID = "CENSUS_PUBLIC"
SOURCE_NAME = "U.S. Census Bureau economic indicators"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
FRED_DATA = "https://fred.stlouisfed.org/data/{series_id}"

# FRED series are used as public mirrors of Census economic indicators where
# they are stable and easy to parse. Census API probes are retained in the raw
# audit when CENSUS_API_KEY is present, but normalized observations below are
# built from the stable public time series to avoid breaking the whole pipeline
# when a Census table/category code changes.
SERIES = [
    {
        "key": "RETAIL_SALES_TOTAL",
        "seriesId": "RSXFS",
        "label": "Retail sales: retail and food services",
        "kind": "consumer_demand",
        "unit": "millions USD",
        "frequency": "monthly",
        "valueScale": 1.0,
        "sourceNote": "Advance Monthly Retail Trade Survey / Census retail sales, public series mirrored by FRED.",
    },
    {
        "key": "HOUSING_STARTS",
        "seriesId": "HOUST",
        "label": "Housing starts",
        "kind": "housing_activity",
        "unit": "thousands SAAR",
        "frequency": "monthly",
        "valueScale": 1.0,
        "sourceNote": "Census New Residential Construction housing starts, public series mirrored by FRED.",
    },
    {
        "key": "BUILDING_PERMITS",
        "seriesId": "PERMIT",
        "label": "Building permits",
        "kind": "housing_activity",
        "unit": "thousands SAAR",
        "frequency": "monthly",
        "valueScale": 1.0,
        "sourceNote": "Census New Residential Construction building permits, public series mirrored by FRED.",
    },
    {
        "key": "NEW_HOME_SALES",
        "seriesId": "HSN1F",
        "label": "New single-family home sales",
        "kind": "housing_activity",
        "unit": "thousands SAAR",
        "frequency": "monthly",
        "valueScale": 1.0,
        "sourceNote": "Census new residential sales, public series mirrored by FRED.",
    },
    {
        "key": "DURABLE_GOODS_ORDERS",
        "seriesId": "DGORDER",
        "label": "Durable goods new orders",
        "kind": "business_investment",
        "unit": "millions USD",
        "frequency": "monthly",
        "valueScale": 1.0,
        "sourceNote": "Census Manufacturers' New Orders: Durable Goods, public series mirrored by FRED.",
    },
    {
        "key": "TRADE_BALANCE",
        "seriesId": "BOPGSTB",
        "label": "U.S. trade balance: goods and services",
        "kind": "trade_balance",
        "unit": "millions USD",
        "frequency": "monthly",
        "valueScale": 1.0,
        "sourceNote": "U.S. international trade balance from Census/BEA public data, mirrored by FRED.",
    },
    {
        "key": "BUSINESS_INVENTORIES",
        "seriesId": "BUSINV",
        "label": "Total business inventories",
        "kind": "inventory_cycle",
        "unit": "millions USD",
        "frequency": "monthly",
        "valueScale": 1.0,
        "sourceNote": "Census Manufacturing and Trade Inventories and Sales, public series mirrored by FRED.",
    },
]

# Light Census API probes for audit only. These keep the official API connection
# visible without letting one fragile category query kill the lane.
CENSUS_PROBES = [
    {
        "id": "marts_retail_total",
        "endpoint": "https://api.census.gov/data/timeseries/eits/marts",
        "params": {
            "get": "data_type_code,time_slot_id,seasonally_adj,category_code,cell_value,error_data",
            "time": "from 2024-01",
            "category_code": "44X72",
            "data_type_code": "SM",
        },
    },
    {
        "id": "resconst_recent",
        "endpoint": "https://api.census.gov/data/timeseries/eits/resconst",
        "params": {
            "get": "data_type_code,time_slot_id,seasonally_adj,category_code,cell_value,error_data",
            "time": "from 2024-01",
        },
    },
    {
        "id": "advm3_recent",
        "endpoint": "https://api.census.gov/data/timeseries/eits/advm3",
        "params": {
            "get": "data_type_code,time_slot_id,seasonally_adj,category_code,cell_value,error_data",
            "time": "from 2024-01",
        },
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {".", "--", "NA", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MacroRegimeScanner/0.29",
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


def fetch_rows(series_id: str, audit: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[str] = []
    for method_name, fn in (("fredgraph_csv", rows_from_graph_csv), ("fred_data_txt", rows_from_data_txt)):
        try:
            rows = fn(series_id)
            audit.setdefault("fetchAttempts", []).append({"method": method_name, "rows": len(rows)})
            if rows:
                return rows
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{method_name}: {exc}")
            audit.setdefault("fetchAttempts", []).append({"method": method_name, "error": str(exc)})
    if errors:
        audit["fetchErrors"] = errors
    return []


def latest_two(rows: list[dict[str, str]], series_id: str, scale: float) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    points: list[dict[str, Any]] = []
    for row in rows:
        date = row.get("observation_date") or row.get("DATE") or row.get("date")
        raw = row.get(series_id) or row.get(series_id.lower()) or row.get(series_id.upper()) or row.get("VALUE") or row.get("value")
        value = parse_float(raw)
        if date and value is not None and math.isfinite(value):
            points.append({"date": date, "value": value * scale, "rawValue": value})
    if not points:
        return None, None
    points.sort(key=lambda x: x["date"])
    latest = points[-1]
    previous = points[-2] if len(points) >= 2 else None
    return latest, previous


def percent_change(latest: float | None, previous: float | None) -> float | None:
    if latest is None or previous is None or previous == 0:
        return None
    return ((latest - previous) / abs(previous)) * 100.0


def score_growth(pct: float | None) -> int | None:
    if pct is None:
        return None
    if pct >= 1.0:
        return 2
    if pct > 0.0:
        return 1
    if pct <= -1.0:
        return -2
    if pct < 0.0:
        return -1
    return 0


def score_trade_balance(latest: float | None, previous: float | None) -> int | None:
    if latest is None or previous is None:
        return None
    # Improvement means the deficit narrows or surplus widens.
    change = latest - previous
    if change >= 10_000:
        return 2
    if change > 0:
        return 1
    if change <= -10_000:
        return -2
    if change < 0:
        return -1
    return 0


def score_inventory(pct: float | None) -> int | None:
    if pct is None:
        return None
    # Inventory builds can signal restocking or unsold goods; keep muted/contextual.
    if pct >= 1.0:
        return -1
    if pct <= -1.0:
        return 1
    return 0


def build_observation(spec: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    series_id = spec["seriesId"]
    audit: dict[str, Any] = {"seriesId": series_id, "label": spec["label"], "status": "started"}
    try:
        rows = fetch_rows(series_id, audit)
        latest, previous = latest_two(rows, series_id, float(spec.get("valueScale", 1.0)))
        audit["rowsFetched"] = len(rows)
        if not latest:
            audit["status"] = "no_observations"
            return None, audit
        latest_value = latest["value"]
        previous_value = previous["value"] if previous else None
        change = latest_value - previous_value if previous_value is not None else None
        pct = percent_change(latest_value, previous_value)
        kind = spec["kind"]
        if kind == "trade_balance":
            score = score_trade_balance(latest_value, previous_value)
        elif kind == "inventory_cycle":
            score = score_inventory(pct)
        else:
            score = score_growth(pct)
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
            "percentChange": round(pct, 4) if pct is not None else None,
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


def fetch_census_probe(probe: dict[str, Any], key: str | None) -> dict[str, Any]:
    record: dict[str, Any] = {"id": probe["id"], "endpoint": probe["endpoint"], "status": "skipped_no_key"}
    if not key:
        return record
    params = dict(probe["params"])
    params["key"] = key.strip()
    url = probe["endpoint"] + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MacroRegimeScanner/0.29"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        rows = json.loads(text)
        record.update({"status": "ok", "rowsFetched": max(0, len(rows) - 1) if isinstance(rows, list) else None})
    except Exception as exc:  # noqa: BLE001
        record.update({"status": "error", "error": str(exc)[:500]})
    return record


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_PATH.parent.mkdir(parents=True, exist_ok=True)
    census_key = os.environ.get("CENSUS_API_KEY", "").strip() or None

    observations: dict[str, Any] = {}
    audits: list[dict[str, Any]] = []
    for spec in SERIES:
        observation, audit = build_observation(spec)
        audits.append(audit)
        if observation:
            observations[spec["key"]] = observation

    probes = [fetch_census_probe(probe, census_key) for probe in CENSUS_PROBES]

    normalized = {
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "retrievedAt": now_iso(),
        "observations": observations,
        "notes": [
            "Census macro lane uses U.S. Census Bureau economic-indicator concepts.",
            "Stable public FRED graph/data mirrors are used for normalized observations where they preserve the official Census/related series and reduce Census EITS category-code fragility.",
            "Census API probes are saved in raw audit output when CENSUS_API_KEY is available.",
        ],
    }
    audit_doc = {
        "sourceId": SOURCE_ID,
        "retrievedAt": normalized["retrievedAt"],
        "seriesAudit": audits,
        "censusApiProbes": probes,
        "observationCount": len(observations),
    }
    NORM_PATH.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    AUDIT_PATH.write_text(json.dumps(audit_doc, indent=2) + "\n", encoding="utf-8")

    if not observations:
        raise SystemExit("Census fetch did not produce any normalized observations.")
    print(f"Wrote {NORM_PATH.relative_to(ROOT)} with {len(observations)} observations")
    print(f"Wrote {AUDIT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
