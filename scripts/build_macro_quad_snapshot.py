#!/usr/bin/env python3
"""Build the Edgefield Growth / Inflation Pressure Map.

v0.50.1 calibration notes:
- No price is used.
- Uses existing live scanner row evidence.
- Does not force neutral just because one axis is uncertain.
- Uses blend states when one axis is mixed and the other is clear.
- Separates confidence from score: low confidence can still have directional pressure.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
OUT_PATH = ROOT / "data" / "macro_quad_snapshot.json"

LIVE_ROLES = {"live_scored", "live_context"}
BAD_MARKERS = ("prototype", "sample", "candidate", "missing", "n/a")

GROWTH_KEYWORDS = (
    "gdp", "growth", "retail", "consumer", "labor", "payroll", "unemployment",
    "claims", "jolts", "income", "spending", "durable", "census", "housing",
    "industrial", "demand", "product supplied", "credit spreads", "financial stress",
    "financial conditions", "reserve balances", "liquidity", "fed total assets",
)
INFLATION_KEYWORDS = (
    "cpi", "pce", "ppi", "inflation", "core", "wage", "earnings", "yield",
    "breakeven", "real yields", "policy rate", "fed policy", "energy", "crude",
    "gasoline", "distillate", "natural gas", "inventories", "cushing", "refinery",
    "wasde", "stock/use", "crop", "weather", "drought", "food", "agriculture",
)

# Anchor assets are used only to avoid asset-direction cancellation. For example,
# hot CPI can be positive for USD/rates but negative for equities. For the inflation
# axis, the macro fact is still "inflation hot," so USD/rates/commodity anchors are
# better than a median across every asset.
GROWTH_ANCHORS = {
    "SPX", "NDX", "RUT", "DOW", "DXY", "USD", "COPPER", "WTI", "BRENT", "BCOM",
    "FCI", "HY", "IG",
}
INFLATION_ANCHORS = {
    "DXY", "USD", "US02Y", "US05Y", "US10Y", "US30Y", "REALY", "BE5Y", "BE10Y",
    "WTI", "BRENT", "NG", "GASOLINE", "HEATING", "BCOM", "WHEAT", "CORN", "SOY",
    "GOLD", "SILVER",
}

WEIGHT_PRIMARY = {
    "gdp": 1.05,
    "retail": 0.95,
    "labor": 1.05,
    "payroll": 1.05,
    "unemployment": 1.05,
    "credit": 1.05,
    "financial stress": 1.05,
    "financial conditions": 0.95,
    "liquidity": 0.85,
    "reserve balances": 0.85,
    "cpi": 1.10,
    "pce": 1.10,
    "ppi": 0.95,
    "yield": 1.00,
    "policy": 0.95,
    "energy": 0.85,
    "crude": 0.85,
    "gasoline": 0.85,
    "crop": 0.65,
    "drought": 0.65,
    "weather": 0.55,
}

STATE_COPY = {
    "Goldilocks": {
        "subtitle": "Growth supportive / inflation easing",
        "simpleRead": "Growth pressure is supportive while inflation pressure is calm or easing. This is usually the cleanest broad risk-supportive backdrop.",
    },
    "Goldilocks / Reflation Blend": {
        "subtitle": "Growth supportive / inflation mixed",
        "simpleRead": "Growth still looks supportive, but inflation pressure is unclear or shifting. The backdrop sits between clean Goldilocks and hotter Reflation.",
    },
    "Reflation": {
        "subtitle": "Growth supportive / inflation hot",
        "simpleRead": "Growth remains supportive, but inflation and policy pressure are elevated. Risk can still work, but rate and dollar pressure matter.",
    },
    "Reflation / Stagflation Blend": {
        "subtitle": "Growth mixed / inflation hot",
        "simpleRead": "Inflation and policy pressure are elevated, but growth evidence is mixed. The backdrop sits between hot-growth Reflation and stagflation risk.",
    },
    "Stagflation": {
        "subtitle": "Growth weak / inflation hot",
        "simpleRead": "Growth pressure is weakening while inflation pressure remains elevated. This is a difficult backdrop where conflict matters.",
    },
    "Stagflation / Deflation Blend": {
        "subtitle": "Growth weak / inflation mixed",
        "simpleRead": "Growth is weak, but inflation pressure is unclear or shifting. The backdrop sits between sticky-inflation slowdown and deflationary slowdown.",
    },
    "Deflation": {
        "subtitle": "Growth weak / inflation easing",
        "simpleRead": "Growth is weakening and inflation pressure is easing. This is usually a defensive slowdown-style backdrop.",
    },
    "Deflation / Goldilocks Blend": {
        "subtitle": "Growth mixed / inflation easing",
        "simpleRead": "Inflation pressure is cooling, but growth evidence is mixed. The backdrop sits between defensive Deflation and cleaner Goldilocks recovery.",
    },
    "Neutral / Low-Conviction Macro Pressure": {
        "subtitle": "Growth mixed / inflation mixed",
        "simpleRead": "The scanner does not have enough directional evidence to classify a clean macro quadrant. Source pressure is mixed, near neutral, or low conviction.",
    },
}


def clean(v: Any) -> str:
    return str(v or "").strip()


def lower_blob(f: dict[str, Any]) -> str:
    return " ".join(clean(f.get(k)).lower() for k in ("group", "name", "source", "derived", "effect", "scoreReason", "status"))


def asset_symbol(asset: dict[str, Any]) -> str:
    return clean(asset.get("id") or asset.get("symbol")).upper()


def is_usable(f: dict[str, Any]) -> bool:
    if f.get("scoreRole") not in LIVE_ROLES:
        return False
    if not isinstance(f.get("score"), (int, float)):
        return False
    freshness = clean(f.get("freshness")).lower()
    if not ("fresh" in freshness or "live" in freshness):
        return False
    text = " ".join([clean(f.get("source")), clean(f.get("derived")), clean(f.get("status")), freshness]).lower()
    if any(m in text[:260] for m in BAD_MARKERS):
        return False
    return True


def axis_matches(f: dict[str, Any], axis: str) -> bool:
    text = lower_blob(f)
    keys = GROWTH_KEYWORDS if axis == "growth" else INFLATION_KEYWORDS
    return any(k in text for k in keys)


def base_weight(f: dict[str, Any], axis: str) -> float:
    text = lower_blob(f)
    weight = 0.45
    for key, w in WEIGHT_PRIMARY.items():
        if key in text:
            weight = max(weight, w)
    relevance = clean(f.get("relevance")).lower()
    if "primary" in relevance:
        weight *= 1.0
    elif "secondary" in relevance:
        weight *= 0.72
    elif "context" in relevance:
        weight *= 0.42
    else:
        weight *= 0.55
    if f.get("scoreRole") == "live_context":
        weight *= 0.55
    return round(max(0.05, weight), 3)


def group_key(f: dict[str, Any]) -> str:
    return "__".join([clean(f.get("group")), clean(f.get("name")), clean(f.get("source")), clean(f.get("derived"))[:140]])


def strongest(vals: list[float]) -> float:
    if not vals:
        return 0.0
    return max(vals, key=lambda v: abs(v))


def calibrated_value(group: list[dict[str, Any]], axis: str) -> float:
    vals = [float(f.get("score", 0) or 0) for f in group if isinstance(f.get("score"), (int, float))]
    if not vals:
        return 0.0

    text = lower_blob(group[0])
    symbols = [clean(f.get("assetSymbol")).upper() for f in group]
    anchors = GROWTH_ANCHORS if axis == "growth" else INFLATION_ANCHORS
    anchor_vals = [float(f.get("score", 0) or 0) for f in group if clean(f.get("assetSymbol")).upper() in anchors]
    usable_vals = anchor_vals or vals

    # Direct inflation and rate rows should not cancel just because they hurt some assets and help others.
    # If live evidence has a positive inflation/rate-pressure read anywhere in the anchor set, use it.
    if axis == "inflation":
        direct_hot_terms = ("cpi", "pce", "ppi", "inflation", "wage", "earnings", "yield", "policy", "breakeven", "energy", "crude", "gasoline")
        if any(t in text for t in direct_hot_terms):
            pos = [v for v in usable_vals if v > 0]
            neg = [v for v in usable_vals if v < 0]
            if pos and (not neg or max(pos) >= abs(min(neg)) * 0.60):
                return max(pos)
            if neg:
                return min(neg)

    # Growth rows should lean on risk/growth anchors so bond/rate inversions do not dominate.
    if axis == "growth" and anchor_vals:
        nonzero = [v for v in anchor_vals if abs(v) > 0.01]
        if nonzero:
            return float(mean(nonzero))

    nonzero = [v for v in usable_vals if abs(v) > 0.01]
    if not nonzero:
        return 0.0
    # Median is still useful when rows are already source-directional.
    med = float(median(nonzero))
    if abs(med) >= 0.25:
        return med
    return strongest(nonzero)


def collect_axis(assets: list[dict[str, Any]], axis: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        sym = asset_symbol(asset)
        for f0 in asset.get("factors", []) or []:
            if not is_usable(f0) or not axis_matches(f0, axis):
                continue
            f = dict(f0)
            f["assetSymbol"] = sym
            groups.setdefault(group_key(f), []).append(f)

    rows = []
    for _key, group in groups.items():
        sample = group[0]
        val = calibrated_value(group, axis)
        wt = base_weight(sample, axis)
        rows.append({
            "name": clean(sample.get("name")) or "Unnamed input",
            "group": clean(sample.get("group")) or "Input",
            "source": clean(sample.get("source")) or "Public source",
            "status": clean(sample.get("status")),
            "value": round(val, 3),
            "weight": wt,
            "contribution": round(val * wt, 3),
            "reason": clean(sample.get("derived"))[:220],
        })

    total_weight = sum(r["weight"] for r in rows)
    if total_weight <= 0:
        score = 0.0
    else:
        score = (sum(r["contribution"] for r in rows) / total_weight) * 5.0
    score = max(-15.0, min(15.0, score))
    top_positive = sorted([r for r in rows if r["contribution"] > 0], key=lambda r: r["contribution"], reverse=True)[:5]
    top_negative = sorted([r for r in rows if r["contribution"] < 0], key=lambda r: r["contribution"])[:5]
    label = "positive" if score > 2 else "negative" if score < -2 else "mixed"
    return {
        "score": round(score, 1),
        "label": label,
        "inputCount": len(rows),
        "totalWeight": round(total_weight, 2),
        "topPositiveDrivers": top_positive,
        "topNegativeDrivers": top_negative,
    }


def classify_state(growth: str, inflation: str) -> str:
    if growth == "positive" and inflation == "negative":
        return "Goldilocks"
    if growth == "positive" and inflation == "mixed":
        return "Goldilocks / Reflation Blend"
    if growth == "positive" and inflation == "positive":
        return "Reflation"
    if growth == "mixed" and inflation == "positive":
        return "Reflation / Stagflation Blend"
    if growth == "negative" and inflation == "positive":
        return "Stagflation"
    if growth == "negative" and inflation == "mixed":
        return "Stagflation / Deflation Blend"
    if growth == "negative" and inflation == "negative":
        return "Deflation"
    if growth == "mixed" and inflation == "negative":
        return "Deflation / Goldilocks Blend"
    return "Neutral / Low-Conviction Macro Pressure"


def confidence(g_axis: dict[str, Any], i_axis: dict[str, Any]) -> str:
    inputs = min(g_axis["inputCount"], i_axis["inputCount"])
    distance = min(abs(g_axis["score"]), abs(i_axis["score"]))
    max_distance = max(abs(g_axis["score"]), abs(i_axis["score"]))
    if inputs >= 6 and distance >= 5:
        return "High"
    if inputs >= 3 and (distance >= 2 or max_distance >= 5):
        return "Medium"
    if inputs >= 2 and max_distance >= 2:
        return "Low-Medium"
    return "Low"


def main_conflict(state: str, g_axis: dict[str, Any], i_axis: dict[str, Any]) -> str:
    if state == "Neutral / Low-Conviction Macro Pressure":
        return "Both growth and inflation axes are near neutral, source coverage is limited, or live evidence is mixed."
    if "Blend" in state:
        if g_axis["label"] == "mixed":
            return "Growth evidence is mixed, so the map shows the adjacent inflation-led blend rather than forcing a clean quadrant."
        if i_axis["label"] == "mixed":
            return "Inflation evidence is mixed, so the map shows the adjacent growth-led blend rather than forcing a clean quadrant."
    if state == "Stagflation":
        return "Traditional stagflation can favor inflation hedges, but individual asset audits should still check rate, USD, and source-specific conflicts."
    if state == "Reflation":
        return "Reflation can support cyclicals and commodities, but elevated rates and USD pressure can still hurt duration-sensitive assets."
    return "Use individual asset audits to confirm whether the broad quadrant is supported or contradicted by live source evidence."


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assets = payload.get("assets", []) or []
    g_axis = collect_axis(assets, "growth")
    i_axis = collect_axis(assets, "inflation")
    state = classify_state(g_axis["label"], i_axis["label"])
    copy = STATE_COPY[state]
    output = {
        "schemaVersion": "macro_quad_snapshot_v1_1",
        "version": "v0.50.1-growth-inflation-pressure-map-calibrated",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "No-price public-source overlay built from existing live scanner row evidence. v0.50.1 uses calibrated axis extraction so asset-direction conflicts do not cancel obvious macro pressure.",
        "currentState": state,
        "subtitle": copy["subtitle"],
        "simpleRead": copy["simpleRead"],
        "confidence": confidence(g_axis, i_axis),
        "growth": g_axis,
        "inflation": i_axis,
        "mainConflict": main_conflict(state, g_axis, i_axis),
        "states": [
            {"name": name, **STATE_COPY[name]} for name in [
                "Goldilocks", "Goldilocks / Reflation Blend", "Reflation",
                "Reflation / Stagflation Blend", "Stagflation", "Stagflation / Deflation Blend",
                "Deflation", "Deflation / Goldilocks Blend", "Neutral / Low-Conviction Macro Pressure",
            ]
        ],
        "limits": ["Uses current public-source pressure only; no price data is used."],
    }
    OUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}: {state} ({copy['subtitle']})")


if __name__ == "__main__":
    main()
