#!/usr/bin/env python3
"""Build the Edgefield Growth / Inflation Pressure Map.

This is a no-price macro quadrant overlay. It reads the existing
macro_regime_scanner.json row evidence and summarizes two axes:
- Growth pressure
- Inflation / policy pressure

It does not replace asset scores and it does not make buy/sell claims.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
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
    "cpi": 1.10,
    "pce": 1.10,
    "ppi": 0.90,
    "yield": 1.00,
    "policy": 0.95,
    "energy": 0.85,
    "crude": 0.85,
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
    return " ".join(clean(f.get(k)).lower() for k in ("group", "name", "source", "derived", "effect", "scoreReason"))


def is_usable(f: dict[str, Any]) -> bool:
    if f.get("scoreRole") not in LIVE_ROLES:
        return False
    if not isinstance(f.get("score"), (int, float)):
        return False
    freshness = clean(f.get("freshness")).lower()
    if not ("fresh" in freshness or "live" in freshness):
        return False
    text = " ".join([clean(f.get("source")), clean(f.get("derived")), clean(f.get("status")), freshness]).lower()
    if any(m in text[:240] for m in BAD_MARKERS):
        return False
    return True


def axis_matches(f: dict[str, Any], axis: str) -> bool:
    text = lower_blob(f)
    keys = GROWTH_KEYWORDS if axis == "growth" else INFLATION_KEYWORDS
    return any(k in text for k in keys)


def base_weight(f: dict[str, Any], axis: str) -> float:
    text = lower_blob(f)
    weight = 0.45 if axis == "growth" else 0.45
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
        weight *= 0.38
    return round(max(0.05, weight), 3)


def group_key(f: dict[str, Any]) -> str:
    return "__".join([clean(f.get("group")), clean(f.get("name")), clean(f.get("source")), clean(f.get("derived"))[:140]])


def signed_value(group: list[dict[str, Any]], axis: str) -> float:
    vals = [float(f.get("score", 0) or 0) for f in group if isinstance(f.get("score"), (int, float))]
    if not vals:
        return 0.0
    # Rates/yields often flip sign by asset; for the inflation/policy axis, positive pressure means the rate/inflation lane is hot.
    text = lower_blob(group[0])
    if axis == "inflation" and any(k in text for k in ("yield", "policy rate", "breakeven", "real yields")):
        pos = [v for v in vals if v > 0]
        neg = [v for v in vals if v < 0]
        if pos and neg:
            return max(pos, key=abs)
    return float(median(vals))


def collect_axis(assets: list[dict[str, Any]], axis: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        for f in asset.get("factors", []) or []:
            if not is_usable(f) or not axis_matches(f, axis):
                continue
            groups.setdefault(group_key(f), []).append(f)

    rows = []
    for key, group in groups.items():
        sample = group[0]
        val = signed_value(group, axis)
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
        # Most source row scores are about -2 to +2. Scaling by 5 makes the axis easy to read as roughly -10 to +10.
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
    if inputs >= 5 and distance >= 5:
        return "High"
    if inputs >= 3 and distance >= 2:
        return "Medium"
    return "Low"


def main_conflict(state: str, g_axis: dict[str, Any], i_axis: dict[str, Any]) -> str:
    if state == "Neutral / Low-Conviction Macro Pressure":
        return "Both growth and inflation axes are near neutral, source coverage is limited, or live evidence is mixed."
    if "Blend" in state:
        if g_axis["label"] == "mixed":
            return "Growth evidence is mixed, so the regime sits between two adjacent states rather than a clean quadrant."
        if i_axis["label"] == "mixed":
            return "Inflation evidence is mixed, so the regime sits between two adjacent states rather than a clean quadrant."
    if state == "Stagflation":
        return "Traditional stagflation can favor inflation hedges, but the asset score table should still check rate, USD, and source-specific conflicts."
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
        "schemaVersion": "macro_quad_snapshot_v1",
        "version": "v0.50-growth-inflation-pressure-map",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "No-price public-source overlay built from existing live scanner row evidence. It summarizes growth pressure and inflation/policy pressure; it does not replace asset scores and does not produce buy/sell signals.",
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
        "limits": [
            "Uses current public-source pressure only; no price data is used.",
        ],
    }
    OUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}: {state} ({copy['subtitle']})")


if __name__ == "__main__":
    main()
