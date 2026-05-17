#!/usr/bin/env python3
"""Apply normalized U.S. Treasury yield data to Macro Regime Scanner JSON.

This script updates the first live public-source lane: official Treasury yield
curve data. It is intentionally conservative. It updates rate/yield assets and
public-source evidence fields, then leaves non-Treasury lanes untouched.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
TREASURY_PATH = ROOT / "data" / "normalized" / "treasury_yields.json"

RATE_ASSET_MAP = {
    "US02Y": "2 Yr",
    "US05Y": "5 Yr",
    "US10Y": "10 Yr",
    "US30Y": "30 Yr",
}
CURVE_ASSET_MAP = {
    "CURVE2S10": "10Y minus 2Y",
    "CURVE5S30": "30Y minus 5Y",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def rate_score(latest: float | None, previous: float | None) -> tuple[int | None, str, str]:
    if latest is None or previous is None:
        return None, "Missing", "Treasury feed did not provide enough values for this point."
    change_bp = (latest - previous) * 100.0
    if change_bp >= 10:
        return 2, "Strong support", "Yield rose sharply versus the prior Treasury observation."
    if change_bp >= 3:
        return 1, "Support", "Yield rose versus the prior Treasury observation."
    if change_bp <= -10:
        return -2, "Strong pressure", "Yield fell sharply versus the prior Treasury observation."
    if change_bp <= -3:
        return -1, "Pressure", "Yield fell versus the prior Treasury observation."
    return 0, "Neutral", "Yield was little changed versus the prior Treasury observation."


def curve_score(latest: float | None, previous: float | None) -> tuple[int | None, str, str]:
    if latest is None or previous is None:
        return None, "Missing", "Treasury feed did not provide enough curve data."
    change_bp = (latest - previous) * 100.0
    if change_bp >= 10:
        return 2, "Strong support", "Curve steepened sharply versus the prior Treasury observation."
    if change_bp >= 3:
        return 1, "Support", "Curve steepened versus the prior Treasury observation."
    if change_bp <= -10:
        return -2, "Strong pressure", "Curve flattened/inverted sharply versus the prior Treasury observation."
    if change_bp <= -3:
        return -1, "Pressure", "Curve flattened versus the prior Treasury observation."
    return 0, "Neutral", "Curve slope was little changed versus the prior Treasury observation."


def bias_from_score(score: int | None, kind: str) -> str:
    if score is None:
        return "Missing Treasury Data"
    if kind == "curve":
        if score >= 2:
            return "Curve Steepening Pressure"
        if score == 1:
            return "Curve Mildly Steepening"
        if score == 0:
            return "Curve Neutral"
        if score == -1:
            return "Curve Mildly Flattening"
        return "Curve Flattening Pressure"
    if score >= 2:
        return "Yield Pressure Rising"
    if score == 1:
        return "Yield Pressure Mildly Rising"
    if score == 0:
        return "Yield Pressure Neutral"
    if score == -1:
        return "Yield Pressure Mildly Falling"
    return "Yield Pressure Falling"


def pct(value: float | None) -> str:
    return "missing" if value is None else f"{value:.2f}%"


def spread_text(value: float | None) -> str:
    return "missing" if value is None else f"{value:.3f} percentage points"


def update_factor(asset: dict[str, Any], factor_name: str, score: int | None, status: str, derived: str, effect: str, freshness: str) -> bool:
    factors = asset.setdefault("factors", [])
    found = False
    for factor in factors:
        if factor.get("name") == factor_name:
            factor["score"] = score
            factor["status"] = status
            factor["derived"] = derived
            factor["effect"] = effect
            factor["source"] = "U.S. Treasury official Daily Treasury Par Yield Curve Rates"
            factor["freshness"] = freshness
            found = True
    if not found:
        factors.insert(0, {
            "group": "Rates / Policy",
            "name": factor_name,
            "relevance": "Primary",
            "score": score,
            "status": status,
            "derived": derived,
            "effect": effect,
            "source": "U.S. Treasury official Daily Treasury Par Yield Curve Rates",
            "freshness": freshness,
        })
    return True


def previous_rate(treasury: dict[str, Any], label: str) -> float | None:
    return treasury.get("previous_rates", {}).get(label)


def latest_rate(treasury: dict[str, Any], label: str) -> float | None:
    return treasury.get("latest_rates", {}).get(label)


def previous_curve(treasury: dict[str, Any], key: str) -> float | None:
    previous_rates = treasury.get("previous_rates", {})
    if key == "10Y minus 2Y":
        a = previous_rates.get("10 Yr")
        b = previous_rates.get("2 Yr")
    else:
        a = previous_rates.get("30 Yr")
        b = previous_rates.get("5 Yr")
    if a is None or b is None:
        return None
    return round(a - b, 3)


def apply_rate_asset(asset: dict[str, Any], treasury: dict[str, Any]) -> None:
    label = RATE_ASSET_MAP[asset["id"]]
    latest = latest_rate(treasury, label)
    prev = previous_rate(treasury, label)
    score, status, reason = rate_score(latest, prev)
    latest_date = treasury["latest_date"]
    prev_date = treasury["previous_date"]
    freshness = "Fresh"
    asset["previousScore"] = asset.get("score", 0)
    asset["score"] = score if score is not None else 0
    asset["bias"] = bias_from_score(score, "rate")
    asset["confidence"] = 92 if score is not None else 45
    asset["conflict"] = "Low" if score is not None else "Sample"
    asset["freshness"] = "Fresh"
    asset["coverage"] = f"Treasury yield: {label}"
    asset["topDriver"] = f"{label} official Treasury yield"
    asset["mainConflict"] = "Other public macro lanes not connected yet"
    asset["watchNext"] = ["Next Treasury yield update", "Inflation releases", "Labor releases", "COT Treasury positioning"]
    asset["quick"] = (
        f"Official Treasury lane: {label} is {pct(latest)} as of {latest_date}. "
        f"Prior observation was {pct(prev)} on {prev_date}. {reason}"
    )
    effect = (
        f"For the {asset['name']}, this official yield is the direct input. Higher yields mean stronger rate pressure; lower yields mean weaker rate pressure. This is a public-source rates input, not a trade-timing signal."
    )
    update_factor(asset, f"{label.split()[0]}Y yield" if label != "30 Yr" else "30Y yield", score, status, f"Official Treasury {label} par yield: {pct(latest)} on {latest_date}; previous {pct(prev)} on {prev_date}", effect, freshness)


def apply_curve_asset(asset: dict[str, Any], treasury: dict[str, Any]) -> None:
    key = CURVE_ASSET_MAP[asset["id"]]
    latest = treasury.get("curve_spreads", {}).get(key)
    prev = previous_curve(treasury, key)
    score, status, reason = curve_score(latest, prev)
    latest_date = treasury["latest_date"]
    prev_date = treasury["previous_date"]
    freshness = "Fresh"
    asset["previousScore"] = asset.get("score", 0)
    asset["score"] = score if score is not None else 0
    asset["bias"] = bias_from_score(score, "curve")
    asset["confidence"] = 90 if score is not None else 45
    asset["conflict"] = "Low" if score is not None else "Sample"
    asset["freshness"] = "Fresh"
    asset["coverage"] = f"Treasury curve: {key}"
    asset["topDriver"] = key
    asset["mainConflict"] = "Other public macro lanes not connected yet"
    asset["watchNext"] = ["Next Treasury yield update", "Inflation releases", "Labor releases", "Fed policy path"]
    asset["quick"] = (
        f"Official Treasury lane: {key} is {spread_text(latest)} as of {latest_date}. "
        f"Prior observation was {spread_text(prev)} on {prev_date}. {reason}"
    )
    effect = (
        f"For the {asset['name']}, this curve spread is the direct input. Steepening usually points to changing growth or inflation pressure; flattening/inversion can warn of restrictive policy or growth stress."
    )
    update_factor(asset, "Yield curve", score, status, f"Official Treasury curve spread {key}: {spread_text(latest)} on {latest_date}; previous {spread_text(prev)} on {prev_date}", effect, freshness)


def apply_contextual_treasury_factors(asset: dict[str, Any], treasury: dict[str, Any]) -> None:
    latest_date = treasury["latest_date"]
    freshness = "Fresh"
    latest_2y = latest_rate(treasury, "2 Yr")
    prev_2y = previous_rate(treasury, "2 Yr")
    latest_10y = latest_rate(treasury, "10 Yr")
    prev_10y = previous_rate(treasury, "10 Yr")
    score_2y, status_2y, _ = rate_score(latest_2y, prev_2y)
    score_10y, status_10y, _ = rate_score(latest_10y, prev_10y)

    # Do not force scores for every asset. This is a provenance/freshness upgrade unless the factor already exists.
    for factor in asset.get("factors", []):
        name = factor.get("name")
        if name == "2Y yield":
            factor["derived"] = f"Official Treasury 2 Yr par yield: {pct(latest_2y)} on {latest_date}"
            factor["source"] = "U.S. Treasury official Daily Treasury Par Yield Curve Rates"
            factor["freshness"] = freshness
            factor["effect"] = "Higher 2Y yields usually mean stronger front-end policy pressure; lower 2Y yields reduce that pressure. The effect is direct for rate assets and indirect for other assets through policy, dollar, and risk channels."
            if factor.get("relevance") in {"Primary", "Secondary", "Contextual"}:
                factor["score"] = score_2y
                factor["status"] = status_2y
        elif name == "10Y yield":
            factor["derived"] = f"Official Treasury 10 Yr par yield: {pct(latest_10y)} on {latest_date}"
            factor["source"] = "U.S. Treasury official Daily Treasury Par Yield Curve Rates"
            factor["freshness"] = freshness
            factor["effect"] = "Higher 10Y yields usually increase long-rate pressure and can pressure risk assets and gold; lower 10Y yields usually ease that pressure."
            if factor.get("relevance") in {"Primary", "Secondary", "Contextual"}:
                factor["score"] = score_10y
                factor["status"] = status_10y
        elif name == "Yield curve":
            curve = treasury.get("curve_spreads", {}).get("10Y minus 2Y")
            factor["derived"] = f"Official Treasury 10Y minus 2Y curve spread: {spread_text(curve)} on {latest_date}"
            factor["source"] = "U.S. Treasury official Daily Treasury Par Yield Curve Rates"
            factor["freshness"] = freshness


def main() -> int:
    treasury = load_json(TREASURY_PATH)
    dashboard = load_json(DATA_PATH)

    for asset in dashboard.get("assets", []):
        asset_id = asset.get("id")
        if asset_id in RATE_ASSET_MAP:
            apply_rate_asset(asset, treasury)
        elif asset_id in CURVE_ASSET_MAP:
            apply_curve_asset(asset, treasury)
        else:
            apply_contextual_treasury_factors(asset, treasury)

    dashboard["schema_version"] = "0.19"
    dashboard["notice"] = "Macro Regime Scanner v0.19. Public-source fundamental pressure structure with official Treasury yield lane, CFTC COT scaffold, and source-health status. Other lanes remain prototype/public-source candidates until connected."
    dashboard["data_mode"] = "public-source-treasury-lane"
    dashboard["updated_at"] = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    source_status = dashboard.get("source_status") or {}
    source_status["TREASURY_OFFICIAL"] = {
        "status": "live_lane_ready",
        "latest_date": treasury.get("latest_date"),
        "retrieved_at": treasury.get("retrieved_at"),
        "note": "Official U.S. Treasury yield curve data. Rates are percentages and this lane is used as public-source rate pressure, not trade timing data."
    }
    dashboard["source_status"] = source_status
    write_json(DATA_PATH, dashboard)
    print(f"Applied Treasury lane through {treasury.get('latest_date')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
