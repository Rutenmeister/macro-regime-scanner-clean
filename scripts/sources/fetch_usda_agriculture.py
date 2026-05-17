#!/usr/bin/env python3
"""Fetch USDA NASS Quick Stats public agriculture fundamentals.

v0.23 adds an agriculture public-source lane using USDA/NASS Quick Stats.
This lane intentionally avoids prices, momentum, moving averages, and other
price-derived inputs. It fetches official NASS production, crop-condition, and
crop-progress records for core U.S. crop markets.

Required GitHub secret:
  USDA_API_KEY

Outputs:
  data/raw/usda/usda_nass_compact_audit.json
  data/normalized/usda_agriculture.json
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
RAW_DIR = ROOT / "data" / "raw" / "usda"
NORM_DIR = ROOT / "data" / "normalized"
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)

QS_BASE = "https://quickstats.nass.usda.gov/api/api_GET/"
USER_AGENT = "Edgefield-Macro-Regime-Scanner/0.23"

CROPS = {
    "WHEAT": {"commodity_desc": "WHEAT", "asset_id": "WHEAT", "label": "Wheat"},
    "CORN": {"commodity_desc": "CORN", "asset_id": "CORN", "label": "Corn"},
    "SOY": {"commodity_desc": "SOYBEANS", "asset_id": "SOY", "label": "Soybeans"},
    "COTTON": {"commodity_desc": "COTTON", "asset_id": "COTTON", "label": "Cotton"},
}


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def current_year() -> int:
    return dt.date.today().year


def parse_value(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"(D)", "(Z)", "NA", "--"}:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def fetch_json(url: str, label: str) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=90) as response:
                raw = response.read().decode("utf-8-sig")
            return json.loads(raw)
        except Exception as exc:  # pragma: no cover - network guard
            last_exc = exc
            if attempt < 2:
                time.sleep(3)
    raise RuntimeError(f"could not fetch {label}: {last_exc}")


def qs_url(api_key: str, **params: str) -> str:
    payload: dict[str, str] = {
        "key": api_key,
        "format": "JSON",
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "group_desc": "FIELD CROPS",
        "agg_level_desc": "NATIONAL",
    }
    payload.update(params)
    return QS_BASE + "?" + urllib.parse.urlencode(payload)


def qs_query(api_key: str, label: str, **params: str) -> list[dict[str, Any]]:
    payload = fetch_json(qs_url(api_key, **params), label)
    data = payload.get("data", []) if isinstance(payload, dict) else []
    return [r for r in data if isinstance(r, dict)]


def latest_week(records: list[dict[str, Any]]) -> str | None:
    weeks = [str(r.get("week_ending", "")) for r in records if r.get("week_ending")]
    return max(weeks) if weeks else None


def score_crop_condition(good_excellent: float | None) -> tuple[int | None, str, str]:
    if good_excellent is None:
        return None, "Missing", "USDA/NASS crop condition records did not include a usable good/excellent percentage."
    # For crop futures, strong crop condition usually means stronger supply outlook, which pressures price.
    # Weak crop condition usually means supply stress, which supports price.
    if good_excellent <= 40:
        return 2, "Strong support", "Poor crop condition: low good/excellent ratings imply supply risk, which usually supports crop prices."
    if good_excellent <= 55:
        return 1, "Support", "Below-normal crop condition: weaker good/excellent ratings add supply-risk support to the crop."
    if good_excellent >= 75:
        return -2, "Strong pressure", "Very strong crop condition: better supply outlook usually pressures crop prices unless demand is also very strong."
    if good_excellent >= 65:
        return -1, "Pressure", "Strong crop condition: healthier crops usually improve supply expectations and pressure crop prices."
    return 0, "Neutral", "Crop condition is not extreme enough to give a strong supply-risk signal."


def build_condition(api_key: str, crop_key: str, meta: dict[str, str]) -> dict[str, Any]:
    start_year = str(current_year() - 2)
    rows = qs_query(
        api_key,
        f"NASS {meta['label']} crop condition",
        commodity_desc=meta["commodity_desc"],
        statisticcat_desc="CONDITION",
        year__GE=start_year,
    )
    # Use national weekly rows, latest week_ending. NASS condition records are usually separate rows for GOOD/EXCELLENT/etc.
    rows = [r for r in rows if str(r.get("unit_desc", "")).upper() == "PCT" and r.get("week_ending")]
    week = latest_week(rows)
    latest = [r for r in rows if str(r.get("week_ending")) == str(week)] if week else []
    parts: dict[str, float] = {}
    for r in latest:
        desc = (str(r.get("short_desc", "")) + " " + str(r.get("prodn_practice_desc", ""))).upper()
        val = parse_value(r.get("Value"))
        if val is None:
            continue
        if "EXCELLENT" in desc:
            parts["excellent"] = max(parts.get("excellent", 0.0), val)
        elif "GOOD" in desc:
            parts["good"] = max(parts.get("good", 0.0), val)
        elif "POOR" in desc and "VERY" not in desc:
            parts["poor"] = max(parts.get("poor", 0.0), val)
        elif "VERY POOR" in desc:
            parts["very_poor"] = max(parts.get("very_poor", 0.0), val)
    good_excellent = None
    if "good" in parts or "excellent" in parts:
        good_excellent = parts.get("good", 0.0) + parts.get("excellent", 0.0)
    score, status, interpretation = score_crop_condition(good_excellent)
    return {
        "id": f"{crop_key}_CONDITION",
        "asset_id": meta["asset_id"],
        "crop": meta["label"],
        "input": "USDA crop condition",
        "latest_period": week,
        "good_pct": parts.get("good"),
        "excellent_pct": parts.get("excellent"),
        "good_excellent_pct": good_excellent,
        "poor_pct": parts.get("poor"),
        "very_poor_pct": parts.get("very_poor"),
        "score": score,
        "status": status,
        "interpretation": interpretation,
        "records_returned": len(rows),
    }


def score_production_yoy(change_pct: float | None) -> tuple[int | None, str, str]:
    if change_pct is None:
        return None, "Missing", "USDA/NASS production records did not include two usable national observations for a year-over-year comparison."
    # More production is usually supply pressure for crop prices; less production is supportive.
    if change_pct <= -10:
        return 2, "Strong support", "Production fell sharply year over year; smaller supply usually supports crop prices."
    if change_pct <= -5:
        return 1, "Support", "Production fell year over year; smaller supply usually supports the crop."
    if change_pct >= 10:
        return -2, "Strong pressure", "Production rose sharply year over year; larger supply usually pressures crop prices."
    if change_pct >= 5:
        return -1, "Pressure", "Production rose year over year; larger supply usually pressures the crop."
    return 0, "Neutral", "Production changed modestly year over year, so the production signal is neutral."


def build_production(api_key: str, crop_key: str, meta: dict[str, str]) -> dict[str, Any]:
    start_year = str(current_year() - 6)
    rows = qs_query(
        api_key,
        f"NASS {meta['label']} production",
        commodity_desc=meta["commodity_desc"],
        statisticcat_desc="PRODUCTION",
        year__GE=start_year,
    )
    usable: list[dict[str, Any]] = []
    for r in rows:
        val = parse_value(r.get("Value"))
        if val is None:
            continue
        year = r.get("year")
        try:
            y = int(year)
        except (TypeError, ValueError):
            continue
        # Prefer broad national totals, not seed/processing subcategories when possible.
        desc = str(r.get("short_desc", "")).upper()
        if "PRODUCTION" not in desc:
            continue
        if r.get("agg_level_desc") != "NATIONAL":
            continue
        usable.append({"year": y, "value": val, "unit": r.get("unit_desc"), "short_desc": r.get("short_desc")})
    # Pick one observation per year, preferring ALL CLASSES-like broad short_desc by largest value.
    by_year: dict[int, dict[str, Any]] = {}
    for r in usable:
        prev = by_year.get(r["year"])
        if prev is None or float(r["value"]) > float(prev["value"]):
            by_year[r["year"]] = r
    years = sorted(by_year, reverse=True)
    latest = by_year[years[0]] if years else None
    previous = by_year[years[1]] if len(years) > 1 else None
    change_pct = None
    if latest and previous and previous["value"]:
        change_pct = (float(latest["value"]) - float(previous["value"])) / abs(float(previous["value"])) * 100
    score, status, interpretation = score_production_yoy(change_pct)
    return {
        "id": f"{crop_key}_PRODUCTION",
        "asset_id": meta["asset_id"],
        "crop": meta["label"],
        "input": "USDA production estimate",
        "latest_year": latest.get("year") if latest else None,
        "latest_value": latest.get("value") if latest else None,
        "previous_year": previous.get("year") if previous else None,
        "previous_value": previous.get("value") if previous else None,
        "unit": latest.get("unit") if latest else None,
        "change_pct": change_pct,
        "score": score,
        "status": status,
        "interpretation": interpretation,
        "records_returned": len(rows),
    }


def build_progress(api_key: str, crop_key: str, meta: dict[str, str]) -> dict[str, Any]:
    start_year = str(current_year() - 2)
    rows = qs_query(
        api_key,
        f"NASS {meta['label']} crop progress",
        commodity_desc=meta["commodity_desc"],
        statisticcat_desc="PROGRESS",
        year__GE=start_year,
    )
    rows = [r for r in rows if str(r.get("unit_desc", "")).upper() == "PCT" and r.get("week_ending")]
    week = latest_week(rows)
    latest = [r for r in rows if str(r.get("week_ending")) == str(week)] if week else []
    stages: list[dict[str, Any]] = []
    for r in latest[:12]:
        val = parse_value(r.get("Value"))
        if val is None:
            continue
        desc = str(r.get("short_desc", ""))
        stages.append({"short_desc": desc, "value": val, "unit": r.get("unit_desc")})
    return {
        "id": f"{crop_key}_PROGRESS",
        "asset_id": meta["asset_id"],
        "crop": meta["label"],
        "input": "USDA crop progress context",
        "latest_period": week,
        "stages": stages[:5],
        "score": 0 if stages else None,
        "status": "Neutral" if stages else "Missing",
        "interpretation": "Crop progress is context until compared with normal pace. Delays can support prices through supply risk; smooth progress can pressure prices through better supply confidence.",
        "records_returned": len(rows),
    }


def build_normalized(api_key: str) -> dict[str, Any]:
    observations: dict[str, Any] = {}
    errors: list[str] = []
    for crop_key, meta in CROPS.items():
        for builder in (build_condition, build_production, build_progress):
            try:
                item = builder(api_key, crop_key, meta)
                observations[item["id"]] = item
            except Exception as exc:  # pragma: no cover - network/source guard
                errors.append(f"{crop_key} {builder.__name__}: {exc}")
    latest_dates = []
    for o in observations.values():
        if o.get("latest_period"):
            latest_dates.append(str(o["latest_period"]))
        if o.get("latest_year"):
            latest_dates.append(str(o["latest_year"]))
    latest_date = max(latest_dates) if latest_dates else None
    return {
        "source_id": "USDA_PUBLIC",
        "source_name": "USDA National Agricultural Statistics Service Quick Stats API",
        "retrieved_at": iso_now(),
        "latest_date": latest_date,
        "observations": observations,
        "errors": errors,
        "note": "USDA/NASS Quick Stats lane covers crop condition, crop progress, and production estimates. WASDE ending stocks, stock/use, and export sales remain future USDA sub-lanes.",
    }


def main() -> int:
    api_key = os.environ.get("USDA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "USDA_API_KEY GitHub secret is required for USDA/NASS Quick Stats API calls. "
            "Create a free USDA/NASS Quick Stats API key and add it as repository secret USDA_API_KEY."
        )
    normalized = build_normalized(api_key)
    audit = {
        "source_id": normalized["source_id"],
        "source_name": normalized["source_name"],
        "retrieved_at": normalized["retrieved_at"],
        "latest_date": normalized.get("latest_date"),
        "observation_count": len(normalized.get("observations", {})),
        "observation_keys": sorted(normalized.get("observations", {}).keys()),
        "errors": normalized.get("errors", []),
        "note": normalized.get("note"),
    }
    (RAW_DIR / "usda_nass_compact_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (NORM_DIR / "usda_agriculture.json").write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote USDA/NASS agriculture lane with {audit['observation_count']} observations; latest={audit['latest_date']}")
    if audit["errors"]:
        print("USDA/NASS warnings:")
        for err in audit["errors"]:
            print("-", err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
