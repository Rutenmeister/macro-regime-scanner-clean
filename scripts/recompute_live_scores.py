#!/usr/bin/env python3
"""Recompute Macro Regime Scanner asset scores from live source rows only.

v0.40 scoring principles:
- do not cap displayed asset scores at +/-10;
- do not count prototype/sample/candidate/missing observations;
- weight rows by source lane, asset class, and relevance;
- treat U.S. macro data differently for U.S. equities, USD pairs,
  USD pairs, rates, gold, energy, and agriculture; non-USD FX crosses are excluded from v0.47 distribution scope;
- preserve row-level source text and add an asset-level scoreAudit object;
- write score snapshots so future versions can explain score changes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
HISTORY_DIR = ROOT / "data" / "history"
LATEST_HISTORY_PATH = HISTORY_DIR / "latest.json"

USD_BASE = {"USDJPY", "USDCHF", "USDCAD"}
USD_QUOTE = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}
FX_CROSSES = set()  # v0.47: non-USD FX crosses removed until direct non-U.S. source lanes exist
RATES = {"US02Y", "US05Y", "US10Y", "US30Y"}
CURVES = {"CURVE2S10", "CURVE5S30"}
INFLATION_MARKETS = {"REALY", "BE5Y", "BE10Y"}
US_EQUITIES = {"SPX", "NDX", "RUT", "DOW"}
GLOBAL_EQUITIES = {"DAX", "UK100", "NIKKEI", "CHINA50", "HANGSENG", "EM"}
CREDIT = {"HY", "IG", "FCI"}
PRECIOUS = {"GOLD", "SILVER"}
INDUSTRIAL = {"COPPER"}
ENERGY = {"WTI", "BRENT", "NG", "GASOLINE", "HEATING"}
GRAINS = {"WHEAT", "CORN", "SOY"}
SOFTS = {"COFFEE", "SUGAR", "COTTON"}
BROAD_COMMODITY = {"BCOM"}

LIVE_FRESHNESS = {"fresh", "live"}
BAD_SOURCE_MARKERS = ["prototype", "sample", "candidate", "not connected", "placeholder"]


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def round_score(value: float) -> float:
    return round(float(value), 1)


def asset_bucket(asset: dict[str, Any]) -> str:
    aid = safe_text(asset.get("id"))
    cls = safe_text(asset.get("assetClass"))
    subgroup = safe_text(asset.get("subgroup")).lower()
    if aid == "DXY":
        return "usd_index"
    if aid in USD_BASE:
        return "usd_base_fx"
    if aid in USD_QUOTE:
        return "usd_quote_fx"
    if aid in FX_CROSSES or cls == "FX":
        return "fx_cross"
    if aid in RATES:
        return "us_rates"
    if aid in CURVES:
        return "yield_curve"
    if aid in INFLATION_MARKETS:
        return "inflation_market"
    if aid in US_EQUITIES:
        return "us_equity"
    if aid in GLOBAL_EQUITIES or cls == "Equity Indices":
        return "global_equity"
    if aid in CREDIT or cls == "Credit / Liquidity":
        return "credit_liquidity"
    if aid in PRECIOUS or "precious" in subgroup:
        return "precious_metals"
    if aid in INDUSTRIAL:
        return "industrial_metals"
    if aid in ENERGY or "energy" in subgroup:
        return "energy"
    if aid in GRAINS or "grain" in subgroup:
        return "grains"
    if aid in SOFTS or "soft" in subgroup:
        return "softs"
    if aid in BROAD_COMMODITY:
        return "broad_commodity"
    if cls == "Commodities":
        return "commodity"
    return "other"


def source_lane(factor: dict[str, Any]) -> str:
    text = " ".join([
        safe_text(factor.get("group")),
        safe_text(factor.get("name")),
        safe_text(factor.get("source")),
    ]).lower()
    if "treasury" in text or "yield curve" in text or "10y yield" in text or "2y yield" in text:
        return "treasury"
    if "cot" in text or "commitments of traders" in text or "cftc" in text:
        return "cot"
    if "eia" in text or "energy information administration" in text:
        return "eia"
    if "usda" in text or "nass" in text or "crop" in text:
        return "usda"
    if "bls" in text or "bureau of labor statistics" in text or "cpi" in text or "ppi" in text or "payroll" in text or "unemployment" in text:
        return "bls"
    if "bea" in text or "pce" in text or "gdp" in text or "personal income" in text:
        return "bea"
    if "federal reserve" in text or "fed " in text or "reverse repo" in text or "reserve balances" in text:
        return "fed"
    if "census" in text or "retail sales" in text or "housing" in text or "durable" in text or "trade balance" in text:
        return "census"
    if "credit" in text or "financial stress" in text or "financial conditions" in text or "st. louis financial stress" in text:
        return "financial_stress"
    if "noaa" in text or "weather" in text or "flood" in text or "storm" in text or "drought" in text:
        return "noaa"
    return "unknown"


def is_live_factor(factor: dict[str, Any]) -> tuple[bool, str]:
    score = factor.get("score")
    if score is None or not isinstance(score, (int, float)):
        return False, "missing numeric score"
    if safe_text(factor.get("status")).lower() in {"missing", "n/a"}:
        return False, "missing status"
    if safe_text(factor.get("relevance")) in {"Not applicable", "Low relevance"}:
        return False, "not applicable or low relevance"
    freshness = safe_text(factor.get("freshness")).lower()
    source = safe_text(factor.get("source")).lower()
    derived = safe_text(factor.get("derived")).lower()
    if freshness not in LIVE_FRESHNESS and not freshness.startswith("fresh"):
        return False, f"not live freshness: {freshness or 'blank'}"
    combined = " ".join([source, derived, freshness])
    if any(marker in combined for marker in BAD_SOURCE_MARKERS):
        return False, "prototype/candidate/sample source"
    if not source or not derived:
        return False, "missing source or derived text"
    if "missing" in derived[:120] or "did not provide" in derived[:160]:
        return False, "missing observation"
    return True, "live"


def relevance_weight(factor: dict[str, Any]) -> float:
    return {
        "Primary": 1.00,
        "Secondary": 0.62,
        "Contextual": 0.28,
        "Low relevance": 0.08,
        "Not applicable": 0.0,
    }.get(safe_text(factor.get("relevance")), 0.25)


def lane_weight(lane: str, bucket: str, factor: dict[str, Any]) -> float:
    name = safe_text(factor.get("name")).lower()
    table: dict[str, dict[str, float]] = {
        "treasury": {"us_rates": 1.30, "yield_curve": 1.25, "inflation_market": 0.95, "usd_index": 0.90, "usd_base_fx": 0.82, "usd_quote_fx": 0.82, "fx_cross": 0.18, "us_equity": 1.05, "global_equity": 0.48, "credit_liquidity": 0.80, "precious_metals": 1.10, "industrial_metals": 0.35, "energy": 0.20, "grains": 0.12, "softs": 0.12, "broad_commodity": 0.24, "commodity": 0.18},
        "bls": {"us_rates": 1.05, "yield_curve": 0.70, "inflation_market": 1.00, "usd_index": 0.90, "usd_base_fx": 0.80, "usd_quote_fx": 0.80, "fx_cross": 0.18, "us_equity": 0.90, "global_equity": 0.42, "credit_liquidity": 0.70, "precious_metals": 0.80, "industrial_metals": 0.32, "energy": 0.28, "grains": 0.18, "softs": 0.16, "broad_commodity": 0.35, "commodity": 0.22},
        "bea": {"us_rates": 0.72, "yield_curve": 0.55, "inflation_market": 0.70, "usd_index": 0.65, "usd_base_fx": 0.58, "usd_quote_fx": 0.58, "fx_cross": 0.15, "us_equity": 0.85, "global_equity": 0.38, "credit_liquidity": 0.55, "precious_metals": 0.45, "industrial_metals": 0.52, "energy": 0.48, "grains": 0.18, "softs": 0.18, "broad_commodity": 0.46, "commodity": 0.32},
        "fed": {"us_rates": 1.05, "yield_curve": 0.75, "inflation_market": 0.95, "usd_index": 0.85, "usd_base_fx": 0.78, "usd_quote_fx": 0.78, "fx_cross": 0.18, "us_equity": 1.05, "global_equity": 0.50, "credit_liquidity": 1.10, "precious_metals": 0.90, "industrial_metals": 0.32, "energy": 0.25, "grains": 0.12, "softs": 0.12, "broad_commodity": 0.24, "commodity": 0.18},
        "financial_stress": {"us_rates": 0.55, "yield_curve": 0.45, "inflation_market": 0.35, "usd_index": 0.62, "usd_base_fx": 0.52, "usd_quote_fx": 0.52, "fx_cross": 0.22, "us_equity": 1.25, "global_equity": 0.72, "credit_liquidity": 1.45, "precious_metals": 0.62, "industrial_metals": 0.54, "energy": 0.42, "grains": 0.20, "softs": 0.18, "broad_commodity": 0.42, "commodity": 0.34},
        "cot": {"us_rates": 0.72, "yield_curve": 0.30, "inflation_market": 0.40, "usd_index": 0.72, "usd_base_fx": 0.72, "usd_quote_fx": 0.72, "fx_cross": 0.42, "us_equity": 0.72, "global_equity": 0.32, "credit_liquidity": 0.25, "precious_metals": 1.05, "industrial_metals": 1.05, "energy": 1.05, "grains": 1.05, "softs": 1.05, "broad_commodity": 0.65, "commodity": 0.85},
        "eia": {"us_rates": 0.12, "yield_curve": 0.12, "inflation_market": 0.22, "usd_index": 0.16, "usd_base_fx": 0.14, "usd_quote_fx": 0.14, "fx_cross": 0.08, "us_equity": 0.20, "global_equity": 0.18, "credit_liquidity": 0.16, "precious_metals": 0.16, "industrial_metals": 0.24, "energy": 1.35, "grains": 0.22, "softs": 0.18, "broad_commodity": 0.72, "commodity": 0.42},
        "usda": {"us_rates": 0.08, "yield_curve": 0.06, "inflation_market": 0.16, "usd_index": 0.06, "usd_base_fx": 0.06, "usd_quote_fx": 0.06, "fx_cross": 0.04, "us_equity": 0.08, "global_equity": 0.08, "credit_liquidity": 0.05, "precious_metals": 0.08, "industrial_metals": 0.08, "energy": 0.14, "grains": 1.35, "softs": 0.90, "broad_commodity": 0.55, "commodity": 0.70},
        "noaa": {"us_rates": 0.06, "yield_curve": 0.04, "inflation_market": 0.12, "usd_index": 0.05, "usd_base_fx": 0.05, "usd_quote_fx": 0.05, "fx_cross": 0.04, "us_equity": 0.10, "global_equity": 0.08, "credit_liquidity": 0.08, "precious_metals": 0.06, "industrial_metals": 0.08, "energy": 0.75, "grains": 1.05, "softs": 0.90, "broad_commodity": 0.40, "commodity": 0.55},
        "census": {"us_rates": 0.55, "yield_curve": 0.42, "inflation_market": 0.28, "usd_index": 0.48, "usd_base_fx": 0.42, "usd_quote_fx": 0.42, "fx_cross": 0.12, "us_equity": 0.75, "global_equity": 0.34, "credit_liquidity": 0.45, "precious_metals": 0.24, "industrial_metals": 0.58, "energy": 0.45, "grains": 0.14, "softs": 0.14, "broad_commodity": 0.42, "commodity": 0.30},
        "unknown": {},
    }
    weight = table.get(lane, {}).get(bucket, 0.18)
    if lane == "cot" and any(k in name for k in ["crowding", "commercial", "conflict"]):
        weight *= 0.60
    if lane == "noaa" and "active weather hazards" in name:
        weight *= 0.55
    return weight


def directional_score(asset: dict[str, Any], factor: dict[str, Any]) -> float:
    raw = float(factor.get("score", 0) or 0)
    bucket = asset_bucket(asset)
    lane = source_lane(factor)
    name = safe_text(factor.get("name")).lower()
    if lane == "treasury" and ("yield" in name or "treasury" in name):
        if bucket in {"us_rates", "yield_curve", "inflation_market"}:
            return raw
        if bucket in {"usd_index", "usd_base_fx"}:
            return raw
        if bucket == "usd_quote_fx":
            return -raw
        if bucket in {"us_equity", "global_equity", "credit_liquidity", "precious_metals", "industrial_metals"}:
            return -raw
        if bucket in {"energy", "grains", "softs", "broad_commodity", "commodity"}:
            return -0.35 * raw
        return 0.0
    if bucket == "fx_cross" and lane in {"treasury", "bls", "bea", "fed", "census"}:
        return 0.0
    if lane == "financial_stress" and bucket == "precious_metals":
        return raw * 0.75
    return raw


def classify_row(asset: dict[str, Any], factor: dict[str, Any]) -> tuple[str, str]:
    live, reason = is_live_factor(factor)
    if not live:
        return "not_live", reason
    bucket = asset_bucket(asset)
    lane = source_lane(factor)
    lw = lane_weight(lane, bucket, factor)
    rw = relevance_weight(factor)
    total_weight = lw * rw
    if total_weight >= 0.45:
        return "live_scored", "direct/relevant live row"
    if total_weight >= 0.12:
        return "live_context", "live context row, below scoring threshold"
    return "display_only", "too indirect for scoring"


def bias_from_score(score: float, counted: int, direct_count: int, pos: float, neg: float) -> str:
    if counted == 0 or direct_count == 0:
        return "Insufficient Live Direct Evidence"
    if abs(score) < 3 and pos >= 0.75 and neg >= 0.75:
        return "Mixed Live Evidence"
    if score >= 15:
        return "Extreme Positive Live Pressure"
    if score >= 8:
        return "Strong Positive Live Pressure"
    if score >= 3:
        return "Positive Live Pressure"
    if score <= -15:
        return "Extreme Negative Live Pressure"
    if score <= -8:
        return "Strong Negative Live Pressure"
    if score <= -3:
        return "Negative Live Pressure"
    return "Neutral / Limited Live Pressure"


def pressure_bucket(score: float, counted: int) -> str:
    if counted <= 0:
        return "Low evidence / avoid"
    if score >= 15:
        return "Extreme positive pressure"
    if score >= 8:
        return "Strong positive pressure"
    if score >= 3:
        return "Moderate positive pressure"
    if score <= -15:
        return "Extreme negative pressure"
    if score <= -8:
        return "Strong negative pressure"
    if score <= -3:
        return "Moderate negative pressure"
    return "Mixed / neutral pressure"


def movement_label(delta: float) -> str:
    if delta >= 2:
        return "Improving"
    if delta <= -2:
        return "Deteriorating"
    return "Stable"


def conflict_from_weights(pos: float, neg: float, score: float) -> str:
    if pos >= 2.0 and neg >= 2.0 and abs(score) <= 3:
        return "High"
    if pos >= 1.0 and neg >= 1.0:
        return "Medium"
    return "Low"


def top_label(row: dict[str, Any]) -> str:
    return f"{row['name']} ({row['sourceLane']}, {row['contribution']:+.2f})"


def load_previous_snapshot() -> dict[str, dict[str, Any]]:
    prev = load_json(LATEST_HISTORY_PATH, default={})
    if not isinstance(prev, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for asset in prev.get("assets", []):
        if isinstance(asset, dict) and asset.get("id"):
            out[str(asset["id"])] = asset
    return out


def change_log(asset: dict[str, Any], previous: dict[str, Any] | None, sorted_counted: list[dict[str, Any]], delta: float) -> dict[str, Any]:
    if not previous:
        return {
            "status": "new_or_no_prior_snapshot",
            "summary": "No prior score snapshot was available for this asset.",
            "delta": 0,
            "drivers": [top_label(row) for row in sorted_counted[:3]],
        }
    old_score = float(previous.get("score", 0) or 0)
    new_score = float(asset.get("score", 0) or 0)
    movement = movement_label(new_score - old_score)
    drivers = [top_label(row) for row in sorted_counted[:4]]
    return {
        "status": movement.lower(),
        "summary": f"{asset.get('symbol')} moved {new_score - old_score:+.1f} points versus the previous saved snapshot; current primary state is {asset.get('pressureBucket')}." if movement != "Stable" else f"{asset.get('symbol')} is broadly stable versus the previous saved snapshot.",
        "priorScore": round_score(old_score),
        "currentScore": round_score(new_score),
        "delta": round_score(new_score - old_score),
        "drivers": drivers,
    }


def recompute_asset(asset: dict[str, Any], previous_assets: dict[str, dict[str, Any]]) -> None:
    bucket = asset_bucket(asset)
    counted: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    live_context: list[dict[str, Any]] = []

    for idx, factor in enumerate(asset.get("factors", [])):
        lane = source_lane(factor)
        cls, reason = classify_row(asset, factor)
        raw = factor.get("score") if isinstance(factor.get("score"), (int, float)) else 0
        transformed = directional_score(asset, factor) if cls in {"live_scored", "live_context"} else 0.0
        weight = lane_weight(lane, bucket, factor) * relevance_weight(factor)
        contribution = transformed * weight
        factor["scoreRole"] = cls
        factor["scoreWeight"] = round(weight, 3) if cls == "live_scored" else 0
        factor["scoreContribution"] = round(contribution, 3) if cls == "live_scored" else 0
        factor["scoreReason"] = reason

        record = {
            "index": idx,
            "name": safe_text(factor.get("name")),
            "group": safe_text(factor.get("group")),
            "sourceLane": lane,
            "relevance": safe_text(factor.get("relevance")),
            "rawScore": raw,
            "assetAdjustedScore": round(transformed, 3),
            "weight": round(weight, 3),
            "contribution": round(contribution, 3),
            "reason": reason,
        }
        if cls == "live_scored":
            counted.append(record)
        elif cls == "live_context":
            live_context.append(record)
        else:
            excluded.append(record)

    net = sum(row["contribution"] for row in counted)
    raw_score = round_score(net)
    pos = sum(max(0.0, row["contribution"]) for row in counted)
    neg = abs(sum(min(0.0, row["contribution"]) for row in counted))
    direct_count = sum(1 for row in counted if row["weight"] >= 0.45)
    sorted_counted = sorted(counted, key=lambda r: abs(r["contribution"]), reverse=True)
    positives = [r for r in sorted_counted if r["contribution"] > 0]
    negatives = [r for r in sorted_counted if r["contribution"] < 0]

    prev = previous_assets.get(str(asset.get("id")))
    if prev and isinstance(prev.get("score"), (int, float)):
        previous_score = round_score(prev.get("score", 0))
    else:
        previous_score = round_score(asset.get("score", 0) if isinstance(asset.get("score"), (int, float)) else 0)

    asset["previousScore"] = previous_score
    asset["score"] = raw_score
    asset["rawScore"] = raw_score
    asset["displayScore"] = raw_score
    asset["scoreScale"] = "uncapped_raw_net_pressure"
    asset["bias"] = bias_from_score(raw_score, len(counted), direct_count, pos, neg)
    asset["pressureBucket"] = pressure_bucket(raw_score, len(counted))
    asset["movementTag"] = movement_label(raw_score - previous_score)
    asset["conflict"] = conflict_from_weights(pos, neg, raw_score)
    asset["freshness"] = "Fresh" if counted else "Mixed"
    asset["coverage"] = f"Live-scored {len(counted)} rows; context-only {len(live_context)}; excluded/not-live {len(excluded)}."
    if sorted_counted:
        asset["topDriver"] = top_label(sorted_counted[0])
    else:
        asset["topDriver"] = "No live-scored direct driver yet"
    if positives and negatives:
        main_conflict = f"{top_label(positives[0])} vs {top_label(negatives[0])}"
    elif len(sorted_counted) > 1:
        main_conflict = "Low conflict among counted live rows"
    else:
        main_conflict = "Insufficient counted live evidence"
    asset["mainConflict"] = main_conflict
    base_conf = 22 + min(48, len(counted) * 5) + min(15, direct_count * 4) + min(8, abs(raw_score) * 0.7)
    if asset["conflict"] == "High":
        base_conf -= 12
    elif asset["conflict"] == "Medium":
        base_conf -= 6
    if len(counted) == 0:
        base_conf = 18
    asset["confidence"] = int(clamp(round(base_conf), 10, 90))
    if counted:
        direction_word = "positive" if raw_score > 0 else "negative" if raw_score < 0 else "mixed/neutral"
        asset["quick"] = (
            f"Live-only scoring shows {direction_word} raw pressure from {len(counted)} counted rows. "
            f"Top driver: {asset['topDriver']}. Raw score is uncapped, source-weighted, and excludes non-live rows."
        )
    else:
        asset["quick"] = "No live-scored direct evidence is available for this asset yet; displayed rows remain context/provenance only."

    watch = []
    for row in sorted_counted[:4]:
        if row["name"] and row["name"] not in watch:
            watch.append(row["name"])
    while len(watch) < 3:
        watch.append("Next source refresh")
    asset["watchNext"] = watch[:5]
    asset["scoreAudit"] = {
        "methodVersion": "v0.40-raw-score-history-validation",
        "assetBucket": bucket,
        "pressureBucket": asset["pressureBucket"],
        "movementTag": asset["movementTag"],
        "countedRows": len(counted),
        "contextRows": len(live_context),
        "excludedRows": len(excluded),
        "positiveContribution": round(pos, 3),
        "negativeContribution": round(neg, 3),
        "netContribution": round(net, 3),
        "rawScore": raw_score,
        "finalScore": raw_score,
        "displayScore": raw_score,
        "scoreScale": "uncapped_raw_net_pressure",
        "topPositiveDrivers": positives[:5],
        "topNegativeDrivers": negatives[:5],
        "countedDetails": sorted_counted[:20],
        "contextExamples": live_context[:10],
        "excludedExamples": excluded[:10],
    }
    asset["scoreChangeLog"] = change_log(asset, prev, sorted_counted, raw_score - previous_score)


def build_snapshot(data: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "snapshotVersion": "v0.40-score-history",
        "generatedAt": generated_at,
        "dataMode": data.get("data_mode"),
        "assets": [
            {
                "id": a.get("id"),
                "symbol": a.get("symbol"),
                "score": a.get("score"),
                "previousScore": a.get("previousScore"),
                "pressureBucket": a.get("pressureBucket"),
                "movementTag": a.get("movementTag"),
                "bias": a.get("bias"),
                "confidence": a.get("confidence"),
                "conflict": a.get("conflict"),
                "freshness": a.get("freshness"),
                "topDriver": a.get("topDriver"),
                "scoreAudit": {
                    "countedRows": a.get("scoreAudit", {}).get("countedRows"),
                    "contextRows": a.get("scoreAudit", {}).get("contextRows"),
                    "excludedRows": a.get("scoreAudit", {}).get("excludedRows"),
                    "positiveContribution": a.get("scoreAudit", {}).get("positiveContribution"),
                    "negativeContribution": a.get("scoreAudit", {}).get("negativeContribution"),
                    "netContribution": a.get("scoreAudit", {}).get("netContribution"),
                },
            }
            for a in data.get("assets", [])
        ],
    }


def main() -> int:
    data = load_json(DATA_PATH)
    previous_assets = load_previous_snapshot()
    for asset in data.get("assets", []):
        recompute_asset(asset, previous_assets)
    generated_at = datetime.now(timezone.utc).isoformat()
    data["data_mode"] = "live-public-source-raw-pressure-scoring-v0.40"
    data["notice"] = (
        "v0.40 displays uncapped raw net pressure scores, classifies assets into primary pressure buckets, "
        "uses movement/conflict as tags, writes score snapshots, and preserves live-only scoring discipline."
    )
    data["score_history"] = {
        "latestSnapshotPath": "data/history/latest.json",
        "lastSnapshotAt": generated_at,
        "scoreScale": "uncapped raw net pressure; no +/-10 display cap",
    }
    write_json(DATA_PATH, data)
    snapshot = build_snapshot(data, generated_at)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    write_json(HISTORY_DIR / f"{stamp}.json", snapshot)
    write_json(LATEST_HISTORY_PATH, snapshot)
    print(f"Recomputed uncapped raw pressure scores for {len(data.get('assets', []))} assets.")
    print(f"Snapshot written to data/history/{stamp}.json and data/history/latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
