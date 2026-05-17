#!/usr/bin/env python3
"""Fetch BLS public inflation and labor macro series.

v0.24 adds a Bureau of Labor Statistics public-source macro lane. It avoids
prices, technicals, and market-derived inputs. The lane uses published BLS
series for inflation and labor pressure, then normalizes them for the dashboard.

No API key is required for the public BLS API at this request size.

Outputs:
  data/raw/bls/bls_macro_compact_audit.json
  data/normalized/bls_macro.json
"""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "bls"
NORM_DIR = ROOT / "data" / "normalized"
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
USER_AGENT = "Edgefield-Macro-Regime-Scanner/0.24"

SERIES = {
    "CPI_HEADLINE": {
        "series_id": "CUSR0000SA0",
        "label": "CPI all items",
        "input": "BLS CPI pressure",
        "unit": "index",
        "kind": "inflation_index",
    },
    "CPI_CORE": {
        "series_id": "CUSR0000SA0L1E",
        "label": "Core CPI less food and energy",
        "input": "BLS core CPI pressure",
        "unit": "index",
        "kind": "inflation_index",
    },
    "PPI_FINAL_DEMAND": {
        "series_id": "WPUFD4",
        "label": "PPI final demand",
        "input": "BLS PPI pressure",
        "unit": "index",
        "kind": "inflation_index",
    },
    "UNEMPLOYMENT_RATE": {
        "series_id": "LNS14000000",
        "label": "Unemployment rate",
        "input": "BLS unemployment rate",
        "unit": "percent",
        "kind": "level",
    },
    "NONFARM_PAYROLLS": {
        "series_id": "CES0000000001",
        "label": "Total nonfarm payroll employment",
        "input": "BLS payroll growth",
        "unit": "thousands of jobs",
        "kind": "level_change",
    },
    "AVG_HOURLY_EARNINGS": {
        "series_id": "CES0500000003",
        "label": "Average hourly earnings private employees",
        "input": "BLS wage pressure",
        "unit": "dollars/hour",
        "kind": "wage_index",
    },
}


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"NA", "--", "."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def period_date(year: int, period: str) -> str | None:
    if not period or not period.startswith("M") or period == "M13":
        return None
    try:
        month = int(period[1:])
        return dt.date(year, month, 1).isoformat()
    except Exception:
        return None


def fetch_bls(series_ids: list[str]) -> dict[str, Any]:
    now = dt.date.today()
    payload = {
        "seriesid": series_ids,
        "startyear": str(now.year - 4),
        "endyear": str(now.year),
    }
    body = json.dumps(payload).encode("utf-8")
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                BLS_URL,
                data=body,
                headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                raw = response.read().decode("utf-8-sig")
            return json.loads(raw)
        except Exception as exc:  # pragma: no cover - network guard
            last_exc = exc
            if attempt < 2:
                time.sleep(3)
    raise RuntimeError(f"could not fetch BLS macro data: {last_exc}")


def normalize_series(raw_series: dict[str, Any]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for row in raw_series.get("data", []) or []:
        year = row.get("year")
        period = row.get("period")
        value = parse_float(row.get("value"))
        if value is None:
            continue
        try:
            y = int(year)
        except (TypeError, ValueError):
            continue
        date = period_date(y, str(period))
        if not date:
            continue
        points.append({
            "date": date,
            "year": y,
            "period": period,
            "value": value,
        })
    points.sort(key=lambda x: x["date"])
    return points


def pct_change(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return (a - b) / abs(b) * 100.0


def latest_metrics(points: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    if not points:
        return {}
    latest = points[-1]
    prev = points[-2] if len(points) > 1 else None
    last12 = points[-13] if len(points) > 12 else None
    last3 = points[-4] if len(points) > 3 else None
    latest_val = latest.get("value")
    prev_val = prev.get("value") if prev else None
    yoy = pct_change(latest_val, last12.get("value") if last12 else None)
    mom = None
    if kind in {"inflation_index", "wage_index"}:
        mom = pct_change(latest_val, prev_val)
    three_month = None
    if kind in {"inflation_index", "wage_index"} and last3:
        raw = pct_change(latest_val, last3.get("value"))
        if raw is not None:
            three_month = ((1 + raw / 100.0) ** 4 - 1) * 100.0
    one_month_change = None
    if prev_val is not None:
        one_month_change = latest_val - prev_val
    return {
        "latest_date": latest.get("date"),
        "latest_value": latest_val,
        "previous_date": prev.get("date") if prev else None,
        "previous_value": prev_val,
        "month_change": one_month_change,
        "month_pct_change": mom,
        "yoy_pct_change": yoy,
        "three_month_annualized_pct": three_month,
        "observations": len(points),
    }


def score_inflation(yoy: float | None, three_month: float | None) -> tuple[int | None, str, str]:
    if yoy is None:
        return None, "Missing", "BLS inflation series did not have enough observations for a year-over-year read."
    pressure = yoy
    if three_month is not None:
        pressure = max(yoy, three_month)
    if pressure >= 5.0:
        return 2, "Strong support", "Inflation pressure is high. It supports inflation/rate-pressure reads but can pressure risk assets through tighter-policy concerns."
    if pressure >= 3.0:
        return 1, "Support", "Inflation pressure is elevated. It supports inflation/rate-pressure reads and can weigh on risk assets if policy expectations tighten."
    if pressure <= 1.0:
        return -1, "Pressure", "Inflation pressure is soft. It reduces rate-pressure support and can ease policy pressure on risk assets."
    return 0, "Neutral", "Inflation pressure is not extreme enough to create a strong directional macro signal."


def score_ppi(yoy: float | None) -> tuple[int | None, str, str]:
    if yoy is None:
        return None, "Missing", "BLS PPI series did not have enough observations for a year-over-year read."
    if yoy >= 4.0:
        return 2, "Strong support", "Producer-price pressure is high. It supports cost/inflation pressure and can squeeze risk-asset margins if it persists."
    if yoy >= 2.5:
        return 1, "Support", "Producer-price pressure is elevated. It supports inflation-pressure context and can feed consumer-price pressure later."
    if yoy <= 0.0:
        return -1, "Pressure", "Producer-price pressure is soft or negative. It reduces upstream inflation pressure."
    return 0, "Neutral", "Producer-price pressure is not extreme enough to create a strong directional macro signal."


def score_unemployment(level: float | None, month_change: float | None) -> tuple[int | None, str, str]:
    if level is None:
        return None, "Missing", "BLS unemployment series did not return a usable latest value."
    if month_change is not None and month_change >= 0.3:
        return -2, "Strong pressure", "Unemployment rose sharply. That weakens labor strength and can raise recession-risk pressure."
    if month_change is not None and month_change >= 0.1:
        return -1, "Pressure", "Unemployment rose. That weakens labor strength and can reduce growth confidence."
    if level <= 4.0 and (month_change is None or month_change <= 0.0):
        return 1, "Support", "Unemployment is low/stable. That supports labor strength but can also keep policy pressure firmer."
    return 0, "Neutral", "Unemployment is not moving enough to give a strong labor signal."


def score_payrolls(change_thousands: float | None) -> tuple[int | None, str, str]:
    if change_thousands is None:
        return None, "Missing", "BLS payroll series did not have a usable one-month change."
    if change_thousands >= 250:
        return 2, "Strong support", "Payroll growth is strong. It supports labor/growth strength but may keep rate pressure firmer."
    if change_thousands >= 125:
        return 1, "Support", "Payroll growth is solid. It supports labor/growth strength."
    if change_thousands <= 0:
        return -2, "Strong pressure", "Payrolls contracted. That is strong labor/growth pressure and can raise recession-risk concerns."
    if change_thousands <= 75:
        return -1, "Pressure", "Payroll growth is weak. That reduces labor-strength support."
    return 0, "Neutral", "Payroll growth is modest and not extreme enough for a strong signal."


def score_wages(yoy: float | None) -> tuple[int | None, str, str]:
    if yoy is None:
        return None, "Missing", "BLS wage series did not have enough observations for a year-over-year read."
    if yoy >= 5.0:
        return 2, "Strong support", "Wage growth is strong. It supports income but can keep service inflation and policy pressure firmer."
    if yoy >= 3.5:
        return 1, "Support", "Wage growth is firm. It supports income and can keep inflation pressure sticky."
    if yoy <= 2.0:
        return -1, "Pressure", "Wage growth is soft. It reduces wage-inflation pressure and may signal weaker labor demand."
    return 0, "Neutral", "Wage growth is not extreme enough to create a strong macro signal."


def main() -> int:
    raw = fetch_bls([meta["series_id"] for meta in SERIES.values()])
    series_by_id = {s.get("seriesID"): s for s in raw.get("Results", {}).get("series", []) if isinstance(s, dict)}
    observations: dict[str, Any] = {}
    latest_dates: list[str] = []
    audit: dict[str, Any] = {
        "fetched_at": iso_now(),
        "source": "BLS public API v2",
        "series_requested": SERIES,
        "status": raw.get("status"),
        "message": raw.get("message"),
        "series": {},
    }
    for key, meta in SERIES.items():
        raw_series = series_by_id.get(meta["series_id"], {})
        points = normalize_series(raw_series)
        metrics = latest_metrics(points, meta["kind"])
        if metrics.get("latest_date"):
            latest_dates.append(metrics["latest_date"])
        score = status = interpretation = None
        if meta["kind"] == "inflation_index":
            if key == "PPI_FINAL_DEMAND":
                score, status, interpretation = score_ppi(metrics.get("yoy_pct_change"))
            else:
                score, status, interpretation = score_inflation(metrics.get("yoy_pct_change"), metrics.get("three_month_annualized_pct"))
        elif key == "UNEMPLOYMENT_RATE":
            score, status, interpretation = score_unemployment(metrics.get("latest_value"), metrics.get("month_change"))
        elif key == "NONFARM_PAYROLLS":
            score, status, interpretation = score_payrolls(metrics.get("month_change"))
        elif key == "AVG_HOURLY_EARNINGS":
            score, status, interpretation = score_wages(metrics.get("yoy_pct_change"))
        observations[key] = {
            "id": key,
            "series_id": meta["series_id"],
            "label": meta["label"],
            "input": meta["input"],
            "unit": meta["unit"],
            "kind": meta["kind"],
            **metrics,
            "score": score,
            "status": status,
            "interpretation": interpretation,
        }
        audit["series"][key] = {
            "series_id": meta["series_id"],
            "label": meta["label"],
            "latest_date": metrics.get("latest_date"),
            "latest_value": metrics.get("latest_value"),
            "observations": metrics.get("observations"),
            "score": score,
            "status": status,
        }
    normalized = {
        "schema_version": "0.24",
        "source": "U.S. Bureau of Labor Statistics public API v2",
        "fetched_at": iso_now(),
        "latest_date": max(latest_dates) if latest_dates else None,
        "observations": observations,
    }
    (RAW_DIR / "bls_macro_compact_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (NORM_DIR / "bls_macro.json").write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    print(f"Fetched BLS macro data for {len(observations)} series; latest_date={normalized['latest_date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
