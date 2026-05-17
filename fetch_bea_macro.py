#!/usr/bin/env python3
"""Fetch BEA macro data for Macro Regime Scanner.

This lane uses the official U.S. Bureau of Economic Analysis API. It is designed
as a robust starter-deep lane: it fetches available NIPA tables, extracts target
macroeconomic observations, writes a compact raw/audit file, and writes a stable
normalized file consumed by scripts/apply_bea_lane.py.

Required GitHub secret/environment variable:
    BEA_API_KEY
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "bea"
NORM_PATH = ROOT / "data" / "normalized" / "bea_macro.json"
AUDIT_PATH = RAW_DIR / "bea_macro_compact_audit.json"
BEA_API_URL = "https://apps.bea.gov/api/data"
SOURCE_ID = "BEA_PUBLIC"
SOURCE_NAME = "U.S. Bureau of Economic Analysis API"

# Tables are intentionally fetched by table name and searched by line description.
# If BEA changes availability for a table/frequency, the fetcher records the error
# in audit output and continues with the remaining tables rather than faking data.
TABLE_SPECS = [
    {
        "table": "T10101",
        "frequency": "Q",
        "label": "Real GDP growth",
        "targets": [
            {
                "key": "REAL_GDP_GROWTH",
                "label": "Real GDP growth",
                "kind": "growth",
                "unit": "percent annual rate",
                "include": ["gross domestic product"],
                "exclude": ["gross national product", "less", "residual"],
            }
        ],
    },
    {
        "table": "T20804",
        "frequency": "Q",
        "label": "PCE price index growth",
        "targets": [
            {
                "key": "PCE_PRICE_PRESSURE",
                "label": "PCE inflation pressure",
                "kind": "inflation",
                "unit": "percent annual rate",
                "include": ["personal consumption expenditures"],
                "exclude": ["excluding", "less", "goods", "services", "food", "energy"],
            },
            {
                "key": "CORE_PCE_PRICE_PRESSURE",
                "label": "Core PCE inflation pressure",
                "kind": "inflation",
                "unit": "percent annual rate",
                "include": ["excluding food and energy"],
                "exclude": [],
            },
        ],
    },
    {
        "table": "T20306",
        "frequency": "Q",
        "label": "Real PCE growth",
        "targets": [
            {
                "key": "REAL_PCE_GROWTH",
                "label": "Real personal consumption growth",
                "kind": "growth",
                "unit": "percent annual rate",
                "include": ["personal consumption expenditures"],
                "exclude": ["goods", "services", "durable", "nondurable"],
            }
        ],
    },
    # This table can vary by API release/frequency; it is optional and fail-soft.
    {
        "table": "T20600",
        "frequency": "M",
        "label": "Personal income and saving",
        "optional": True,
        "targets": [
            {
                "key": "PERSONAL_INCOME_GROWTH",
                "label": "Personal income growth",
                "kind": "growth",
                "unit": "percent annual rate",
                "include": ["personal income"],
                "exclude": ["less", "taxes", "receipts"],
            },
            {
                "key": "SAVING_RATE",
                "label": "Personal saving rate",
                "kind": "level",
                "unit": "percent",
                "include": ["personal saving as a percentage of disposable personal income"],
                "exclude": [],
            },
        ],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_api_key() -> str:
    key = os.environ.get("BEA_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "BEA_API_KEY GitHub secret is required for BEA API calls. "
            "Create a free BEA API key and add it as repository secret BEA_API_KEY."
        )
    return key


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "(NA)", "NA", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def period_key(period: str) -> tuple[int, int, int]:
    text = str(period)
    m = re.match(r"^(\d{4})Q([1-4])$", text)
    if m:
        return (int(m.group(1)), int(m.group(2)), 0)
    m = re.match(r"^(\d{4})M(\d{1,2})$", text)
    if m:
        return (int(m.group(1)), int(m.group(2)), 0)
    m = re.match(r"^(\d{4})$", text)
    if m:
        return (int(m.group(1)), 0, 0)
    return (0, 0, 0)


def bea_request(params: dict[str, str], retries: int = 2) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{BEA_API_URL}?{query}"
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"BEA request failed for {params.get('TableName')}: {last_error}") from exc
    raise RuntimeError(f"BEA request failed for {params.get('TableName')}: {last_error}")


def extract_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    beaapi = response.get("BEAAPI") or {}
    if "Error" in beaapi:
        err = beaapi.get("Error")
        raise RuntimeError(f"BEA API error: {err}")
    results = beaapi.get("Results") or {}
    if "Error" in results:
        raise RuntimeError(f"BEA API results error: {results.get('Error')}")
    data = results.get("Data")
    if not isinstance(data, list):
        raise RuntimeError("BEA response did not include Results.Data list")
    return [row for row in data if isinstance(row, dict)]


def fetch_table(api_key: str, table: str, frequency: str) -> list[dict[str, Any]]:
    params = {
        "UserID": api_key,
        "method": "GetData",
        "datasetname": "NIPA",
        "TableName": table,
        "Frequency": frequency,
        "Year": "X",
        "ResultFormat": "JSON",
    }
    response = bea_request(params)
    return extract_rows(response)


def row_description(row: dict[str, Any]) -> str:
    return str(row.get("LineDescription") or row.get("LineDesc") or row.get("LineNumber") or "").lower()


def matches(row: dict[str, Any], include: Iterable[str], exclude: Iterable[str]) -> bool:
    desc = row_description(row)
    if not desc:
        return False
    return all(term.lower() in desc for term in include) and not any(term.lower() in desc for term in exclude)


def latest_observation(rows: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [row for row in rows if matches(row, target.get("include", []), target.get("exclude", []))]
    points: list[dict[str, Any]] = []
    for row in candidates:
        value = parse_number(row.get("DataValue"))
        period = row.get("TimePeriod")
        if value is None or not period:
            continue
        points.append({
            "period": str(period),
            "value": value,
            "lineNumber": row.get("LineNumber"),
            "lineDescription": row.get("LineDescription") or row.get("LineDesc"),
            "unitMultiplier": row.get("UNIT_MULT"),
            "clUnit": row.get("CL_UNIT"),
        })
    points.sort(key=lambda item: period_key(item["period"]))
    if not points:
        return None
    latest = points[-1]
    previous = points[-2] if len(points) >= 2 else None
    latest_value = latest["value"]
    previous_value = previous["value"] if previous else None
    change = latest_value - previous_value if previous_value is not None else None
    return {
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "seriesId": target["key"],
        "label": target["label"],
        "kind": target["kind"],
        "unit": target["unit"],
        "latestValue": latest_value,
        "previousValue": previous_value,
        "change": change,
        "period": latest["period"],
        "previousPeriod": previous["period"] if previous else None,
        "lineNumber": latest.get("lineNumber"),
        "lineDescription": latest.get("lineDescription"),
        "score": score_observation(target["kind"], latest_value, change),
        "retrievedAt": now_iso(),
        "frequency": "quarterly/monthly",
    }


def score_observation(kind: str, latest: float | None, change: float | None) -> int | None:
    if latest is None:
        return None
    if kind == "inflation":
        if latest >= 4.0:
            return 2
        if latest >= 2.6:
            return 1
        if latest <= 0.5:
            return -1
        return 0
    if kind == "growth":
        if latest >= 3.5:
            return 2
        if latest >= 1.5:
            return 1
        if latest <= -1.0:
            return -2
        if latest < 0.5:
            return -1
        return 0
    if kind == "level":
        # Savings rate is useful context but not directly directional here.
        return 0
    return 0


def main() -> int:
    api_key = require_api_key()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_PATH.parent.mkdir(parents=True, exist_ok=True)

    observations: dict[str, Any] = {}
    table_audit: list[dict[str, Any]] = []
    errors: list[str] = []
    retrieved_at = now_iso()

    for spec in TABLE_SPECS:
        table = spec["table"]
        frequency = spec["frequency"]
        try:
            rows = fetch_table(api_key, table, frequency)
            table_audit.append({
                "table": table,
                "frequency": frequency,
                "label": spec.get("label"),
                "rowCount": len(rows),
                "status": "ok",
            })
            for target in spec.get("targets", []):
                obs = latest_observation(rows, target)
                if obs:
                    observations[target["key"]] = obs
                else:
                    errors.append(f"No matching BEA row found for {target['key']} in {table}/{frequency}")
        except Exception as exc:
            msg = f"{table}/{frequency}: {exc}"
            if spec.get("optional"):
                errors.append(msg)
                table_audit.append({"table": table, "frequency": frequency, "label": spec.get("label"), "status": "optional_failed", "error": str(exc)})
                continue
            errors.append(msg)
            table_audit.append({"table": table, "frequency": frequency, "label": spec.get("label"), "status": "failed", "error": str(exc)})

    if not observations:
        raise SystemExit("BEA fetch did not produce any normalized observations. Errors: " + "; ".join(errors[:8]))

    latest_periods = [obs.get("period") for obs in observations.values() if obs.get("period")]
    normalized = {
        "sourceId": SOURCE_ID,
        "sourceName": SOURCE_NAME,
        "retrievedAt": retrieved_at,
        "latestDate": max(latest_periods) if latest_periods else "unknown",
        "observations": observations,
        "errors": errors[:25],
        "note": "BEA NIPA macro lane. Missing optional observations are recorded in errors and not faked.",
    }
    audit = {
        "sourceId": SOURCE_ID,
        "retrievedAt": retrieved_at,
        "tables": table_audit,
        "observationKeys": sorted(observations.keys()),
        "errors": errors[:50],
    }
    NORM_PATH.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"Fetched BEA macro lane with {len(observations)} observations")
    if errors:
        print(f"BEA warnings: {len(errors)} issue(s); see {AUDIT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
