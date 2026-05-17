#!/usr/bin/env python3
"""
Macro Regime Scanner v0.34 - Explainable Scoring Engine

Purpose:
- Read a normalized macro regime scanner JSON file.
- Apply asset-specific relevance and directional scoring rules.
- Generate a scoreAudit object for every asset.
- Preserve existing data as much as possible.

Expected input shapes supported:
1) {"assets": [...], "inputs": [...]} where inputs are shared rows.
2) {"assets": [{..., "evidence": [...]}]} where each asset carries its own rows.
3) A list of asset objects.

Evidence row recommended fields:
- id / input_id / key / type / category
- value_score / signal / score / normalized_score in range -2..2 where positive means row's own raw pressure is rising/supportive
- status / freshness / live_status
- source / provenance
- label / name

This script intentionally treats missing or stale data as not scored.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RULES = BASE_DIR / "config" / "scoring_rules.json"
DEFAULT_MAP = BASE_DIR / "config" / "asset_input_map.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def norm(s: Any) -> str:
    return str(s or "").strip().lower().replace(" ", "_").replace("-", "_")


def as_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    try:
        return float(str(value).replace("+", "").strip())
    except Exception:
        return default


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def get_signal(row: Dict[str, Any]) -> float:
    """Return row's raw evidence pressure in -2..2 before asset directional map."""
    for key in ("value_score", "signal", "normalized_score", "score", "pressure", "effect_score"):
        if key in row and row[key] is not None:
            return clamp(as_number(row[key]), -2, 2)

    # Fallback textual interpretation. Kept conservative.
    text = norm(row.get("effect") or row.get("direction") or row.get("bias") or row.get("label"))
    if any(w in text for w in ("strong_positive", "very_positive", "bullish", "tightening_supply", "inventory_draw")):
        return 2.0
    if any(w in text for w in ("positive", "supportive", "higher", "rising", "hawkish")):
        return 1.0
    if any(w in text for w in ("strong_negative", "very_negative", "bearish", "inventory_build")):
        return -2.0
    if any(w in text for w in ("negative", "pressure", "lower", "falling", "dovish")):
        return -1.0
    return 0.0


def get_input_key(row: Dict[str, Any]) -> str:
    for key in ("input_key", "input_id", "id", "key", "type", "category", "lane"):
        if row.get(key):
            return norm(row[key])
    name = norm(row.get("name") or row.get("label") or row.get("title"))
    # broad fallback mapping based on words likely already in live rows
    if "10y" in name or "treasury" in name or "yield" in name:
        return "treasury_yield_pressure"
    if "real_yield" in name or "real yield" in name:
        return "real_yield_pressure"
    if "cpi" in name or "pce" in name or "inflation" in name:
        return "inflation_pressure"
    if "fed" in name or "policy" in name or "rate" in name:
        return "fed_hawkish_pressure"
    if "credit" in name or "stress" in name or "financial_conditions" in name:
        return "credit_stress"
    if "liquidity" in name or "reserve" in name:
        return "liquidity_pressure"
    if "eia" in name or "crude" in name or "oil" in name or "inventory" in name:
        return "eia_energy_balance"
    if "usda" in name or "crop" in name or "wasde" in name:
        return "usda_crop_balance"
    if "noaa" in name or "weather" in name or "drought" in name or "freeze" in name:
        return "noaa_weather_hazard"
    if "cot" in name and ("gold" in name or "metal" in name):
        return "cot_metal_positioning"
    if "cot" in name and ("oil" in name or "energy" in name):
        return "cot_energy_positioning"
    if "cot" in name and ("wheat" in name or "corn" in name or "grain" in name or "ag" in name):
        return "cot_ag_positioning"
    if "cot" in name:
        return "cot_equity_positioning"
    if "gdp" in name or "retail" in name or "growth" in name or "bea" in name or "census" in name:
        return "growth_strength"
    if "labor" in name or "payroll" in name or "claims" in name or "unemployment" in name or "bls" in name:
        return "labor_tightness"
    return "unmapped"


def is_live(row: Dict[str, Any], rules: Dict[str, Any]) -> Tuple[bool, float, str]:
    status = norm(row.get("status") or row.get("freshness") or row.get("live_status") or row.get("source_status"))
    policy = rules.get("freshness_policy", {})
    fresh = set(policy.get("fresh_statuses", []))
    aging = set(policy.get("aging_statuses", []))
    stale = set(policy.get("stale_statuses", []))

    if not status:
        # If source exists and no status is provided, allow but mark as unverified-current.
        if row.get("source") or row.get("provenance"):
            return True, 1.0, "live_unverified_status"
        return False, 0.0, "not_live_missing_status"
    if status in fresh:
        return True, 1.0, status
    if status in aging:
        return True, as_number(policy.get("aging_penalty", 0.75), 0.75), status
    if status in stale:
        return False, 0.0, status
    if "fresh" in status or "live" in status or "current" in status:
        return True, 1.0, status
    if "aging" in status:
        return True, as_number(policy.get("aging_penalty", 0.75), 0.75), status
    return False, 0.0, status


def classify_asset(asset: Dict[str, Any], mapping: Dict[str, Any]) -> str:
    symbol = norm(asset.get("symbol") or asset.get("id") or asset.get("ticker") or asset.get("name"))
    explicit = norm(asset.get("asset_class") or asset.get("class") or asset.get("group"))
    classes = mapping.get("asset_classes", {})

    if explicit in classes:
        return explicit

    for cls, spec in classes.items():
        aliases = [norm(a) for a in spec.get("aliases", [])]
        if symbol in aliases:
            return cls
        if any(symbol == a or symbol.startswith(a + "_") for a in aliases):
            return cls

    # conservative fallbacks
    if any(k in symbol for k in ("spx", "nasdaq", "ndx", "russell")):
        return "us_equity_index"
    if any(k in symbol for k in ("10y", "2y", "yield")):
        return "us_rates"
    if symbol in ("dxy", "usdollar", "usd") or symbol.startswith("usd"):
        return "usd_fx"
    if symbol.endswith("usd") and symbol not in ("xauusd", "xagusd"):
        return "foreign_usd_pair"
    if any(k in symbol for k in ("gold", "xau", "silver", "xag")):
        return "precious_metals"
    if any(k in symbol for k in ("wti", "brent", "oil", "crude", "natgas")):
        return "energy_commodity"
    if any(k in symbol for k in ("wheat", "corn", "soy")):
        return "agriculture_commodity"
    return "unmapped"


def get_rule(asset_class: str, input_key: str, mapping: Dict[str, Any]) -> Dict[str, Any]:
    cls_rules = mapping.get("asset_classes", {}).get(asset_class, {}).get("rules", {})
    return copy.deepcopy(cls_rules.get(input_key) or mapping.get("default_rule", {"direction": 0, "weight": "excluded", "reason": "Unmapped."}))


def label_score(net: float, counted: int, confidence: str, rules: Dict[str, Any]) -> str:
    if confidence == "Insufficient":
        return "Insufficient live direct evidence"
    for item in rules.get("score_labels", []):
        if net >= as_number(item.get("min"), -999):
            return item.get("label", "Mixed live evidence")
    return "Mixed live evidence"


def confidence(counted: int, direct: int, coverage: float, rules: Dict[str, Any]) -> str:
    cr = rules.get("confidence_rules", {})
    high = cr.get("high", {})
    med = cr.get("medium", {})
    low = cr.get("low", {})
    if counted >= high.get("min_counted_rows", 7) and direct >= high.get("min_direct_rows", 4) and coverage >= high.get("min_coverage", 0.7):
        return "High"
    if counted >= med.get("min_counted_rows", 4) and direct >= med.get("min_direct_rows", 2) and coverage >= med.get("min_coverage", 0.45):
        return "Medium"
    if counted >= low.get("min_counted_rows", 2) and direct >= low.get("min_direct_rows", 1) and coverage >= low.get("min_coverage", 0.25):
        return "Low"
    return "Insufficient"


def summarize_driver(row: Dict[str, Any], contribution: float, rule: Dict[str, Any], input_key: str) -> Dict[str, Any]:
    return {
        "inputKey": input_key,
        "label": row.get("label") or row.get("name") or row.get("title") or input_key,
        "contribution": round(contribution, 3),
        "rawSignal": get_signal(row),
        "weight": rule.get("weight"),
        "reason": rule.get("reason", ""),
        "source": row.get("source") or row.get("provenance") or row.get("derived_from") or "Unspecified source"
    }


def compute_audit(asset: Dict[str, Any], evidence_rows: List[Dict[str, Any]], rules: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
    weights = rules.get("weights", {})
    asset_class = classify_asset(asset, mapping)
    counted: List[Dict[str, Any]] = []
    context: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    positive = 0.0
    negative = 0.0
    direct_rows = 0

    for row in evidence_rows:
        row = copy.deepcopy(row)
        input_key = get_input_key(row)
        rule = get_rule(asset_class, input_key, mapping)
        weight_name = rule.get("weight", "excluded")
        weight = as_number(weights.get(weight_name, 0), 0)
        direction = as_number(rule.get("direction", 0), 0)
        live, freshness_mult, live_reason = is_live(row, rules)
        raw = get_signal(row)

        if not live:
            row["scoringStatus"] = "not_live"
            row["excludedReason"] = f"Not live or stale: {live_reason}"
            row["inputKey"] = input_key
            excluded.append(row)
            continue

        if weight <= 0 or direction == 0:
            row["scoringStatus"] = "display_only"
            row["excludedReason"] = rule.get("reason", "Display only / no explicit score mapping.")
            row["inputKey"] = input_key
            excluded.append(row)
            continue

        contribution = raw * direction * weight * freshness_mult
        row["inputKey"] = input_key
        row["mappedWeight"] = weight_name
        row["mappedDirection"] = direction
        row["contribution"] = round(contribution, 3)
        row["mappingReason"] = rule.get("reason", "")

        if weight_name in ("contextual", "low"):
            row["scoringStatus"] = "live_context"
            context.append(row)
            # v0.34: contextual/low rows are shown as context, not counted.
            continue

        row["scoringStatus"] = "live_scored"
        counted.append(row)
        if weight_name in ("primary", "secondary"):
            direct_rows += 1
        if contribution >= 0:
            positive += contribution
        else:
            negative += contribution

    total_abs = abs(positive) + abs(negative)
    conflict_ratio = (min(abs(positive), abs(negative)) / total_abs) if total_abs else 0.0
    coverage_den = len(evidence_rows) if evidence_rows else 1
    coverage = len(counted) / coverage_den
    conf = confidence(len(counted), direct_rows, coverage, rules)
    net = positive + negative

    pos_drivers = sorted([summarize_driver(r, r.get("contribution", 0), get_rule(asset_class, r.get("inputKey"), mapping), r.get("inputKey")) for r in counted if r.get("contribution", 0) > 0], key=lambda x: x["contribution"], reverse=True)[:5]
    neg_drivers = sorted([summarize_driver(r, r.get("contribution", 0), get_rule(asset_class, r.get("inputKey"), mapping), r.get("inputKey")) for r in counted if r.get("contribution", 0) < 0], key=lambda x: x["contribution"])[:5]

    conflict_level = "Low"
    crules = rules.get("conflict_rules", {})
    if conflict_ratio >= as_number(crules.get("high_conflict_threshold", 0.55), 0.55):
        conflict_level = "High"
    elif conflict_ratio >= as_number(crules.get("medium_conflict_threshold", 0.3), 0.3):
        conflict_level = "Medium"

    main_conflicts = []
    if positive > 0 and negative < 0:
        main_conflicts.append({
            "label": f"{conflict_level} internal evidence conflict",
            "detail": f"Positive scored pressure {positive:.2f} vs negative scored pressure {negative:.2f}."
        })
    if context:
        main_conflicts.append({"label": "Context not counted", "detail": f"{len(context)} live context rows were visible but not counted in v0.34."})

    return {
        "asset": asset.get("symbol") or asset.get("id") or asset.get("name"),
        "assetClass": asset_class,
        "label": label_score(net, len(counted), conf, rules),
        "confidence": conf,
        "coverage": round(coverage, 3),
        "countedRows": len(counted),
        "contextRows": len(context),
        "excludedRows": len(excluded),
        "directRows": direct_rows,
        "positiveWeight": round(positive, 3),
        "negativeWeight": round(negative, 3),
        "netScore": round(net, 3),
        "conflictLevel": conflict_level,
        "conflictRatio": round(conflict_ratio, 3),
        "topPositiveDrivers": pos_drivers,
        "topNegativeDrivers": neg_drivers,
        "mainConflicts": main_conflicts,
        "countedEvidence": counted,
        "contextEvidence": context,
        "excludedEvidence": excluded,
        "caveats": [
            "This is evidence pressure, not a trade signal.",
            "Missing or stale evidence is excluded, not treated as neutral.",
            "U.S. macro evidence is weighted differently by asset class.",
            "Asset-specific exceptions may require manual tuning."
        ]
    }


def extract_assets_and_evidence(data: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    if isinstance(data, list):
        return data, [], "list"
    if isinstance(data, dict):
        assets = data.get("assets") or data.get("markets") or data.get("regimes") or []
        shared = data.get("inputs") or data.get("evidence") or data.get("rows") or data.get("live_inputs") or []
        return assets, shared, "dict"
    raise ValueError("Unsupported input JSON shape.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to existing macro_regime_scanner JSON")
    parser.add_argument("--output", required=True, help="Path to write enriched JSON")
    parser.add_argument("--rules", default=str(DEFAULT_RULES))
    parser.add_argument("--map", default=str(DEFAULT_MAP))
    args = parser.parse_args()

    data = load_json(Path(args.input))
    rules = load_json(Path(args.rules))
    mapping = load_json(Path(args.map))
    assets, shared_evidence, shape = extract_assets_and_evidence(data)

    enriched_assets = []
    for asset in assets:
        asset_copy = copy.deepcopy(asset)
        asset_evidence = asset_copy.get("evidence") or asset_copy.get("rows") or asset_copy.get("inputs") or shared_evidence
        if not isinstance(asset_evidence, list):
            asset_evidence = []
        audit = compute_audit(asset_copy, asset_evidence, rules, mapping)
        asset_copy["scoreAudit"] = audit
        asset_copy["score"] = audit["netScore"]
        asset_copy["pressureLabel"] = audit["label"]
        asset_copy["confidence"] = audit["confidence"]
        asset_copy["conflict"] = audit["conflictLevel"]
        enriched_assets.append(asset_copy)

    if shape == "list":
        out = enriched_assets
    else:
        out = copy.deepcopy(data)
        if "assets" in out:
            out["assets"] = enriched_assets
        elif "markets" in out:
            out["markets"] = enriched_assets
        elif "regimes" in out:
            out["regimes"] = enriched_assets
        else:
            out["assets"] = enriched_assets
        out.setdefault("metadata", {})
        out["metadata"].update({
            "scoringVersion": "0.34",
            "scoringName": "Explainable Scoring Baseline",
            "scoringGeneratedAt": datetime.now(timezone.utc).isoformat(),
            "scoringNote": "Scores are asset-specific evidence pressure readings, not buy/sell signals."
        })

    write_json(Path(args.output), out)
    print(f"[OK] wrote {args.output} with {len(enriched_assets)} enriched assets")


if __name__ == "__main__":
    main()
