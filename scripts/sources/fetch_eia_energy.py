#!/usr/bin/env python3
"""Fetch EIA public/open energy fundamentals for Macro Regime Scanner.

This lane intentionally avoids prices, momentum, moving averages, spreads, and
other price-derived inputs. It uses EIA public/open data for physical energy
fundamentals only.

Required for petroleum APIv2 calls:
  GitHub secret EIA_API_KEY

Outputs:
  data/raw/eia/eia_energy_compact_audit.json
  data/normalized/eia_energy.json
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "eia"
NORM_DIR = ROOT / "data" / "normalized"
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)

EIA_V2_BASE = "https://api.eia.gov/v2"
NATGAS_STORAGE_RELEASE = "https://ir.eia.gov/ngs/wngsr.json"

# Petroleum weekly supply estimates. These are public EIA series identifiers
# exposed in the EIA API browser for the weekly petroleum supply/disposition route.
PETROLEUM_SERIES = {
    "CRUDE_STOCKS": {
        "route": "petroleum/sum/sndw",
        "series": "W_EPC0_SAX_NUS_MBBL",
        "label": "U.S. commercial crude oil stocks excluding SPR",
        "unit": "thousand barrels",
        "kind": "inventory",
        "threshold": 1500,
        "strong_threshold": 5000,
    },
    "CUSHING_STOCKS": {
        "route": "petroleum/sum/sndw",
        "series": "W_EPC0_SAX_YCUOK_MBBL",
        "label": "Cushing, Oklahoma crude oil stocks",
        "unit": "thousand barrels",
        "kind": "inventory",
        "threshold": 500,
        "strong_threshold": 1500,
    },
    "GASOLINE_STOCKS": {
        "route": "petroleum/sum/sndw",
        "series": "W_EPM0_SAX_NUS_MBBL",
        "label": "U.S. motor gasoline stocks",
        "unit": "thousand barrels",
        "kind": "inventory",
        "threshold": 1000,
        "strong_threshold": 3000,
    },
    "DISTILLATE_STOCKS": {
        "route": "petroleum/sum/sndw",
        "series": "W_EPD0_SAX_NUS_MBBL",
        "label": "U.S. distillate fuel oil stocks",
        "unit": "thousand barrels",
        "kind": "inventory",
        "threshold": 750,
        "strong_threshold": 2500,
    },

    "REFINERY_UTILIZATION": {
        "route": "petroleum/sum/sndw",
        "series": "WPULEUS3",
        "label": "U.S. refinery utilization rate",
        "unit": "percent",
        "kind": "utilization",
        "threshold": 1.0,
        "strong_threshold": 3.0,
        "optional": True,
    },
    "CRUDE_PRODUCTION": {
        "route": "petroleum/sum/sndw",
        "series": "WCRFPUS2",
        "label": "U.S. field production of crude oil",
        "unit": "thousand barrels per day",
        "kind": "production",
        "threshold": 100,
        "strong_threshold": 300,
        "optional": True,
    },
    "CRUDE_IMPORTS": {
        "route": "petroleum/sum/sndw",
        "series": "WCRIMUS2",
        "label": "U.S. crude oil imports",
        "unit": "thousand barrels per day",
        "kind": "flow",
        "threshold": 250,
        "strong_threshold": 750,
        "optional": True,
    },
    "CRUDE_EXPORTS": {
        "route": "petroleum/sum/sndw",
        "series": "WCREXUS2",
        "label": "U.S. crude oil exports",
        "unit": "thousand barrels per day",
        "kind": "flow",
        "threshold": 250,
        "strong_threshold": 750,
        "optional": True,
    },
    "GASOLINE_PRODUCT_SUPPLIED": {
        "route": "petroleum/sum/sndw",
        "series": "WGFUPUS2",
        "label": "U.S. finished motor gasoline product supplied",
        "unit": "thousand barrels per day",
        "kind": "demand_proxy",
        "threshold": 250,
        "strong_threshold": 750,
        "optional": True,
    },
    "DISTILLATE_PRODUCT_SUPPLIED": {
        "route": "petroleum/sum/sndw",
        "series": "WDIUPUS2",
        "label": "U.S. distillate fuel oil product supplied",
        "unit": "thousand barrels per day",
        "kind": "demand_proxy",
        "threshold": 150,
        "strong_threshold": 500,
        "optional": True,
    },
}


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def fetch_url_json(url: str, label: str) -> Any:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Edgefield-Macro-Regime-Scanner/0.22"})
            with urllib.request.urlopen(req, timeout=90) as response:
                raw = response.read().decode("utf-8-sig")
            return json.loads(raw)
        except Exception as exc:  # pragma: no cover - network guard
            last_exc = exc
            if attempt < 2:
                time.sleep(3)
    raise RuntimeError(f"could not fetch {label}: {last_exc}")


def fetch_eia_v2_series(api_key: str, route: str, series_id: str) -> list[dict[str, Any]]:
    url = f"{EIA_V2_BASE}/{route}/data/"
    params: list[tuple[str, str]] = [
        ("api_key", api_key),
        ("frequency", "weekly"),
        ("data[0]", "value"),
        ("facets[series][]", series_id),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("offset", "0"),
        ("length", "8"),
    ]
    payload = fetch_url_json(url + "?" + urllib.parse.urlencode(params), f"EIA series {series_id}")
    response = payload.get("response", {}) if isinstance(payload, dict) else {}
    data = response.get("data", [])
    if not isinstance(data, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        try:
            value = float(str(row.get("value", "")).replace(",", ""))
        except ValueError:
            continue
        rows.append({
            "period": str(row.get("period", "")),
            "value": value,
            "series": row.get("series") or series_id,
            "series-description": row.get("series-description") or row.get("seriesDescription") or "",
            "units": row.get("units") or row.get("unit") or "",
        })
    rows.sort(key=lambda r: r["period"], reverse=True)
    return rows


def score_inventory_change(change: float | None, threshold: float, strong_threshold: float) -> tuple[int, str, str]:
    if change is None:
        return 0, "Neutral", "EIA series returned only one usable observation, so weekly inventory change could not be scored."
    # Inventory draw is supportive for petroleum products; inventory build is pressure.
    if change <= -strong_threshold:
        return 2, "Strong support", "Large EIA inventory draw: tighter visible supply is supportive for the related energy market."
    if change <= -threshold:
        return 1, "Support", "EIA inventory draw: lower visible supply is supportive for the related energy market."
    if change >= strong_threshold:
        return -2, "Strong pressure", "Large EIA inventory build: higher visible supply pressures the related energy market."
    if change >= threshold:
        return -1, "Pressure", "EIA inventory build: higher visible supply pressures the related energy market."
    return 0, "Neutral", "EIA inventory change was small, so the physical-balance signal is neutral."


def score_non_inventory_change(change: float | None, threshold: float, strong_threshold: float, kind: str) -> tuple[int, str, str]:
    if change is None:
        return 0, "Neutral", "EIA series returned only one usable observation, so weekly change could not be scored."
    # Demand/refinery-utilization/export increases are generally supportive for product/crude balance;
    # production/import increases add supply and are usually pressure for crude balance.
    supply_kinds = {"production", "flow_import_supply"}
    if kind in supply_kinds:
        if change >= strong_threshold:
            return -2, "Strong pressure", "Large EIA supply increase: higher visible supply pressures the related energy market."
        if change >= threshold:
            return -1, "Pressure", "EIA supply increase: higher visible supply pressures the related energy market."
        if change <= -strong_threshold:
            return 2, "Strong support", "Large EIA supply decline: lower visible supply supports the related energy market."
        if change <= -threshold:
            return 1, "Support", "EIA supply decline: lower visible supply supports the related energy market."
        return 0, "Neutral", "EIA supply change was small, so the physical-balance signal is neutral."
    # For demand proxy, exports and utilization, higher values normally tighten balance.
    if change >= strong_threshold:
        return 2, "Strong support", "Large EIA demand/utilization increase: stronger throughput or product demand supports the related energy market."
    if change >= threshold:
        return 1, "Support", "EIA demand/utilization increase: stronger throughput or product demand supports the related energy market."
    if change <= -strong_threshold:
        return -2, "Strong pressure", "Large EIA demand/utilization decline: weaker throughput or product demand pressures the related energy market."
    if change <= -threshold:
        return -1, "Pressure", "EIA demand/utilization decline: weaker throughput or product demand pressures the related energy market."
    return 0, "Neutral", "EIA demand/utilization change was small, so the signal is neutral."


def build_petroleum_observation(key: str, meta: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest = rows[0] if rows else None
    previous = rows[1] if len(rows) > 1 else None
    latest_value = latest.get("value") if latest else None
    prev_value = previous.get("value") if previous else None
    change = None if latest_value is None or prev_value is None else latest_value - prev_value
    kind = str(meta.get("kind", "inventory"))
    if kind == "inventory":
        score, status, interpretation = score_inventory_change(change, float(meta["threshold"]), float(meta["strong_threshold"]))
    elif key == "CRUDE_IMPORTS":
        score, status, interpretation = score_non_inventory_change(change, float(meta["threshold"]), float(meta["strong_threshold"]), "flow_import_supply")
    else:
        score, status, interpretation = score_non_inventory_change(change, float(meta["threshold"]), float(meta["strong_threshold"]), kind)
    return {
        "id": key,
        "label": meta["label"],
        "series": meta["series"],
        "latest_period": latest.get("period") if latest else None,
        "previous_period": previous.get("period") if previous else None,
        "latest_value": latest_value,
        "previous_value": prev_value,
        "weekly_change": change,
        "unit": meta["unit"],
        "kind": meta.get("kind", "inventory"),
        "score": score,
        "status": status,
        "interpretation": interpretation,
        "observations_returned": len(rows),
    }


def fetch_natural_gas_storage() -> dict[str, Any]:
    payload = fetch_url_json(NATGAS_STORAGE_RELEASE, "EIA Weekly Natural Gas Storage Report")
    series = payload.get("series", []) if isinstance(payload, dict) else []
    total = None
    for item in series:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("series_id", "")).lower()
        name = str(item.get("name", "")).lower()
        if "r48" in sid or "total lower 48" in name:
            total = item
            break
    if not total:
        raise RuntimeError("could not locate total lower 48 natural gas storage series in EIA WNGSR JSON")

    data = total.get("data", [])
    latest_pair = data[0] if data else [None, None]
    prev_pair = data[1] if len(data) > 1 else [None, None]
    latest_value = float(latest_pair[1]) if latest_pair[1] is not None else None
    prev_value = float(prev_pair[1]) if prev_pair[1] is not None else None
    weekly_change = total.get("calculated", {}).get("net_change")
    try:
        weekly_change = float(weekly_change)
    except (TypeError, ValueError):
        weekly_change = None if latest_value is None or prev_value is None else latest_value - prev_value
    pct_5yr = total.get("calculated", {}).get("pct-chg_5yr-avg")
    try:
        pct_5yr = float(pct_5yr)
    except (TypeError, ValueError):
        pct_5yr = None

    # For natural gas, storage versus five-year average is usually more useful than the raw weekly injection/withdrawal.
    if pct_5yr is None:
        score, status, interpretation = 0, "Neutral", "EIA storage comparison to the five-year average was unavailable, so the natural gas storage signal is neutral."
    elif pct_5yr <= -10:
        score, status, interpretation = 2, "Strong support", "Natural gas storage is well below the five-year average; tighter supply cushion supports natural gas."
    elif pct_5yr <= -3:
        score, status, interpretation = 1, "Support", "Natural gas storage is below the five-year average; smaller supply cushion supports natural gas."
    elif pct_5yr >= 10:
        score, status, interpretation = -2, "Strong pressure", "Natural gas storage is far above the five-year average; larger supply cushion pressures natural gas."
    elif pct_5yr >= 3:
        score, status, interpretation = -1, "Pressure", "Natural gas storage is above the five-year average; larger supply cushion pressures natural gas."
    else:
        score, status, interpretation = 0, "Neutral", "Natural gas storage is near the five-year average, so the storage signal is neutral."

    return {
        "id": "NATGAS_STORAGE",
        "label": "Lower 48 working natural gas in underground storage",
        "series": total.get("series_id"),
        "release_date": payload.get("release_date"),
        "latest_period": latest_pair[0],
        "previous_period": prev_pair[0],
        "latest_value": latest_value,
        "previous_value": prev_value,
        "weekly_change": weekly_change,
        "pct_vs_5yr_avg": pct_5yr,
        "five_year_avg": total.get("calculated", {}).get("5yr-avg"),
        "unit": total.get("unitsshort") or total.get("units") or "bcf",
        "kind": meta.get("kind", "inventory"),
        "score": score,
        "status": status,
        "interpretation": interpretation,
        "observations_returned": len(data),
    }


def main() -> int:
    api_key = os.environ.get("EIA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "EIA_API_KEY GitHub secret is required for EIA petroleum APIv2 calls. "
            "Create a free EIA API key and add it as repository secret EIA_API_KEY."
        )

    petroleum: dict[str, Any] = {}
    audit: dict[str, Any] = {
        "fetched_at": iso_now(),
        "source": "U.S. Energy Information Administration open data/API",
        "petroleum_series_requested": PETROLEUM_SERIES,
        "notes": "Compact audit only; raw API payloads are not committed to avoid large files.",
    }

    for key, meta in PETROLEUM_SERIES.items():
        rows = fetch_eia_v2_series(api_key, meta["route"], meta["series"])
        petroleum[key] = build_petroleum_observation(key, meta, rows)
        time.sleep(0.25)

    natgas = fetch_natural_gas_storage()
    observations = {**petroleum, "NATGAS_STORAGE": natgas}
    latest_dates = [str(v.get("latest_period")) for v in observations.values() if v.get("latest_period")]
    latest_date = max(latest_dates) if latest_dates else None

    normalized = {
        "schema_version": "0.22",
        "source_id": "EIA_OPEN_DATA",
        "source": "U.S. Energy Information Administration open data/API",
        "fetched_at": audit["fetched_at"],
        "latest_date": latest_date,
        "observations": observations,
    }

    audit["observations_summary"] = {
        k: {
            "label": v.get("label"),
            "series": v.get("series"),
            "latest_period": v.get("latest_period"),
            "previous_period": v.get("previous_period"),
            "latest_value": v.get("latest_value"),
            "weekly_change": v.get("weekly_change"),
            "status": v.get("status"),
        }
        for k, v in observations.items()
    }

    (RAW_DIR / "eia_energy_compact_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (NORM_DIR / "eia_energy.json").write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    print(f"Fetched EIA energy fundamentals for {len(observations)} series; latest date {latest_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
