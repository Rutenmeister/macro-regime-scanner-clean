#!/usr/bin/env python3
"""Build the Edgefield Growth / Inflation Regime.

v0.50.2 rules:
- No price is used.
- Four regimes only: Goldilocks, Reflation, Stagflation, Deflation.
- No confidence score, no blend states, no transition language.
- Growth and inflation are scored as macro axes, not as asset trade signals.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
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

GROWTH_ANCHORS = {"SPX", "NDX", "RUT", "DOW", "COPPER", "WTI", "BRENT", "BCOM"}
INFLATION_ANCHORS = {
    "DXY", "USD", "US02Y", "US05Y", "US10Y", "US30Y", "REALY", "BE5Y", "BE10Y",
    "WTI", "BRENT", "NG", "GASOLINE", "HEATING", "BCOM", "WHEAT", "CORN", "SOY",
}

ASSET_CLUSTER_WEIGHTS = {
    "growth": {"SPX": 1.0, "NDX": 1.0, "RUT": 0.9, "DOW": 0.8, "COPPER": 0.7, "WTI": 0.45, "BRENT": 0.45},
    "inflation": {"DXY": 0.8, "US02Y": 1.0, "US05Y": 1.0, "US10Y": 1.0, "US30Y": 0.8, "REALY": 0.8, "WTI": 0.6, "BRENT": 0.6, "GASOLINE": 0.6, "WHEAT": 0.5, "CORN": 0.5, "SOY": 0.5},
}

STATE_COPY = {
    "Goldilocks": {
        "subtitle": "Growth positive / Inflation negative",
        "simpleRead": "Growth evidence is supportive while inflation pressure is easing.",
    },
    "Reflation": {
        "subtitle": "Growth positive / Inflation positive",
        "simpleRead": "Growth evidence is supportive while inflation pressure is elevated.",
    },
    "Stagflation": {
        "subtitle": "Growth negative / Inflation positive",
        "simpleRead": "Growth evidence is weakening while inflation pressure remains elevated.",
    },
    "Deflation": {
        "subtitle": "Growth negative / Inflation negative",
        "simpleRead": "Growth evidence is weakening while inflation pressure is easing.",
    },
}


def clean(v: Any) -> str:
    return str(v or "").strip()


def lower_blob(f: dict[str, Any]) -> str:
    keys = ("group", "name", "source", "derived", "effect", "scoreReason", "status", "relevance")
    return " ".join(clean(f.get(k)).lower() for k in keys)


def asset_symbol(asset: dict[str, Any]) -> str:
    return clean(asset.get("id") or asset.get("symbol")).upper()


def numeric(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def is_live_row(f: dict[str, Any]) -> bool:
    if f.get("scoreRole") not in LIVE_ROLES:
        return False
    if numeric(f.get("score")) is None and numeric(f.get("scoreContribution")) is None:
        return False
    freshness = clean(f.get("freshness")).lower()
    status = clean(f.get("status")).lower()
    source = clean(f.get("source")).lower()
    reason = clean(f.get("scoreReason")).lower()
    text = " ".join([freshness, status, source, reason])
    if any(marker in text for marker in BAD_MARKERS):
        return False
    return True


def axis_matches(f: dict[str, Any], axis: str) -> bool:
    text = lower_blob(f)
    keys = GROWTH_KEYWORDS if axis == "growth" else INFLATION_KEYWORDS
    return any(k in text for k in keys)


def group_key(f: dict[str, Any]) -> str:
    return "__".join([clean(f.get("group")), clean(f.get("name")), clean(f.get("source")), clean(f.get("derived"))[:140]])


def row_weight(f: dict[str, Any], axis: str) -> float:
    text = lower_blob(f)
    weight = 0.45
    primary_terms = {
        "growth": ("gdp", "retail", "labor", "payroll", "unemployment", "claims", "credit", "financial stress", "liquidity", "reserve balances", "durable"),
        "inflation": ("cpi", "pce", "ppi", "inflation", "yield", "policy", "energy", "crude", "gasoline", "wage", "crop", "drought"),
    }[axis]
    if any(t in text for t in primary_terms):
        weight = 1.0
    relevance = clean(f.get("relevance")).lower()
    if "secondary" in relevance:
        weight *= 0.75
    elif "context" in relevance:
        weight *= 0.45
    elif "low" in relevance:
        weight *= 0.25
    if f.get("scoreRole") == "live_context":
        weight *= 0.55
    return max(0.05, round(weight, 3))


def signed_input_value(group: list[dict[str, Any]], axis: str) -> float:
    anchors = GROWTH_ANCHORS if axis == "growth" else INFLATION_ANCHORS
    vals = []
    for f in group:
        sym = clean(f.get("assetSymbol")).upper()
        if sym in anchors:
            val = numeric(f.get("score"))
            if val is not None:
                vals.append(val)
    if not vals:
        vals = [numeric(f.get("score")) for f in group if numeric(f.get("score")) is not None]
    vals = [float(v) for v in vals if v is not None and abs(float(v)) > 0.001]
    if not vals:
        return 0.0
    pos = [v for v in vals if v > 0]
    neg = [v for v in vals if v < 0]
    if axis == "inflation":
        # Inflation facts should not disappear because different assets react differently.
        if pos and (not neg or max(pos) >= abs(min(neg)) * 0.55):
            return max(pos)
        if neg:
            return min(neg)
    return mean(vals)


def asset_cluster_driver(assets: list[dict[str, Any]], axis: str) -> dict[str, Any] | None:
    weights = ASSET_CLUSTER_WEIGHTS[axis]
    values = []
    for asset in assets:
        sym = asset_symbol(asset)
        if sym not in weights:
            continue
        val = numeric(asset.get("score"))
        if val is None or abs(val) < 0.001:
            continue
        # Raw asset scores can be larger than axis points. Compress for axis use.
        values.append((max(-2.5, min(2.5, val / 6.0)), weights[sym], sym))
    if not values:
        return None
    total_w = sum(w for _, w, _ in values)
    avg = sum(v * w for v, w, _ in values) / total_w
    label = "Growth asset cluster" if axis == "growth" else "Inflation/rate asset cluster"
    return {
        "name": label,
        "group": "Asset pressure summary",
        "source": "Current scanner asset scores",
        "value": round(avg, 3),
        "weight": 0.85,
        "contribution": round(avg * 0.85, 3),
        "reason": "Secondary no-price summary of current scanner pressure anchors.",
    }


def collect_axis(assets: list[dict[str, Any]], axis: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        sym = asset_symbol(asset)
        for f0 in asset.get("factors", []) or []:
            if not is_live_row(f0) or not axis_matches(f0, axis):
                continue
            f = dict(f0)
            f["assetSymbol"] = sym
            groups.setdefault(group_key(f), []).append(f)

    drivers = []
    for _key, group in groups.items():
        sample = group[0]
        value = signed_input_value(group, axis)
        if abs(value) < 0.001:
            continue
        weight = row_weight(sample, axis)
        drivers.append({
            "name": clean(sample.get("name")) or "Unnamed input",
            "group": clean(sample.get("group")) or "Input",
            "source": clean(sample.get("source")) or "Public source",
            "value": round(value, 3),
            "weight": weight,
            "contribution": round(value * weight, 3),
            "reason": clean(sample.get("derived"))[:220],
        })

    cluster = asset_cluster_driver(assets, axis)
    if cluster:
        drivers.append(cluster)

    total_weight = sum(d["weight"] for d in drivers)
    if total_weight > 0:
        score = (sum(d["contribution"] for d in drivers) / total_weight) * 5.0
    else:
        score = 0.0
    score = max(-15.0, min(15.0, score))
    # Four-quad model: every axis resolves to positive or negative. Zero resolves positive by convention.
    label = "positive" if score >= 0 else "negative"
    top_positive = sorted([d for d in drivers if d["contribution"] > 0], key=lambda d: d["contribution"], reverse=True)[:5]
    top_negative = sorted([d for d in drivers if d["contribution"] < 0], key=lambda d: d["contribution"])[:5]
    return {
        "score": round(score, 1),
        "label": label,
        "inputCount": len(drivers),
        "topPositiveDrivers": top_positive,
        "topNegativeDrivers": top_negative,
    }


def classify(growth: str, inflation: str) -> str:
    if growth == "positive" and inflation == "negative":
        return "Goldilocks"
    if growth == "positive" and inflation == "positive":
        return "Reflation"
    if growth == "negative" and inflation == "positive":
        return "Stagflation"
    return "Deflation"


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assets = payload.get("assets", []) or []
    growth = collect_axis(assets, "growth")
    inflation = collect_axis(assets, "inflation")
    state = classify(growth["label"], inflation["label"])
    copy = STATE_COPY[state]
    output = {
        "schemaVersion": "macro_quad_snapshot_v1_2",
        "version": "v0.50.2-simple-four-quad-regime-map",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "No-price four-quad regime map. Growth and inflation axes are built from current public-source scanner evidence and resolve to positive or negative only.",
        "currentState": state,
        "subtitle": copy["subtitle"],
        "simpleRead": copy["simpleRead"],
        "growth": growth,
        "inflation": inflation,
        "states": [{"name": name, **STATE_COPY[name]} for name in ["Goldilocks", "Reflation", "Stagflation", "Deflation"]],
        "limits": ["Uses current public-source pressure only; no price data is used."],
    }
    OUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}: {state} ({copy['subtitle']})")


if __name__ == "__main__":
    main()
