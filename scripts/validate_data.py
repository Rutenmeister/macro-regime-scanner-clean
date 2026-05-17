#!/usr/bin/env python3
"""Validate Macro Regime Scanner public-source data contract.

Run from repository root:
    python scripts/validate_data.py

This validator is intentionally conservative. It checks that the public-source
edition stays free of price-derived/technical inputs and that all displayed
inputs preserve relevance, provenance, effect, and source/freshness fields.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
CONFIG_DIR = ROOT / "config"

VALID_RELEVANCE = {"Primary", "Secondary", "Contextual", "Low relevance", "Not applicable"}
VALID_STATUS = {"Strong support", "Support", "Neutral", "Pressure", "Strong pressure", "Low relevance", "N/A", "Missing"}
VALID_SCORES = {-2, -1, 0, 1, 2, None}
VALID_CONFLICT = {"Low", "Medium", "High", "Sample"}
VALID_RANK_TYPE = {"rankable", "anchor", None}

# Terms that should not appear as input names / derived-from lanes in the public-source edition.
# This does not ban ordinary words such as "pressure" or "level"; it targets price-derived/technical lanes.
BANNED_PRICE_DERIVED_TERMS = [
    "price trend",
    "momentum",
    "moving average",
    "ma50",
    "ma200",
    "50d",
    "200d",
    "technical confirmation",
    "technical trend",
    "market price lane",
    "relative strength",
    "breakout",
    "breakdown",
    "volatility regime",
    "futures term structure",
    "crack spread",
    "gold/silver ratio",
    "copper/gold ratio",
    "etf flows",
    "crypto price",
]

errors: list[str] = []
warnings: list[str] = []


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - CLI guard
        errors.append(f"could not read JSON {path.relative_to(ROOT)}: {exc}")
        return None


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_no_banned_terms(text: Any, location: str) -> None:
    if not isinstance(text, str):
        return
    lowered = text.lower()
    for term in BANNED_PRICE_DERIVED_TERMS:
        if term in lowered:
            errors.append(f"{location} contains banned price-derived/technical term: {term!r}")


def validate_configs() -> None:
    required = [
        "asset_registry.json",
        "input_registry.json",
        "asset_input_map.json",
        "source_registry.json",
        "freshness_rules.json",
        "scoring_rules.json",
    ]
    for name in required:
        path = CONFIG_DIR / name
        if not path.exists():
            errors.append(f"missing config/{name}")
            continue
        obj = load_json(path)
        if obj is None:
            continue
        if not isinstance(obj, dict):
            errors.append(f"config/{name} must be a JSON object")

    source_registry = load_json(CONFIG_DIR / "source_registry.json") if (CONFIG_DIR / "source_registry.json").exists() else None
    if isinstance(source_registry, dict):
        sources = source_registry.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append("config/source_registry.json sources must be a non-empty list")
        else:
            ids: set[str] = set()
            for i, src in enumerate(sources):
                prefix = f"source_registry.sources[{i}]"
                if not isinstance(src, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                for field in ["id", "name", "status", "public_access", "primary_uses", "asset_classes", "expected_frequency", "attribution_note", "production_note"]:
                    if field not in src:
                        errors.append(f"{prefix} missing {field}")
                sid = src.get("id")
                if not is_nonempty_string(sid):
                    errors.append(f"{prefix}.id must be non-empty string")
                elif sid in ids:
                    errors.append(f"duplicate source id in source_registry: {sid}")
                else:
                    ids.add(sid)


def validate_assets(data: dict[str, Any]) -> None:
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("data.assets must be a non-empty list")
        return

    ids: set[str] = set()
    symbols: set[str] = set()

    for i, asset in enumerate(assets):
        prefix = f"assets[{i}]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be an object")
            continue

        required_asset_fields = [
            "id", "symbol", "name", "assetClass", "subgroup", "rankType", "score", "previousScore",
            "bias", "confidence", "conflict", "freshness", "coverage", "topDriver", "mainConflict",
            "watchNext", "quick", "factors",
        ]
        for field in required_asset_fields:
            if field not in asset:
                errors.append(f"{prefix} missing {field}")

        aid = asset.get("id")
        sym = asset.get("symbol")
        if not is_nonempty_string(aid):
            errors.append(f"{prefix}.id must be non-empty string")
        elif aid in ids:
            errors.append(f"duplicate asset id: {aid}")
        else:
            ids.add(aid)
        if is_nonempty_string(sym):
            symbols.add(sym)

        if asset.get("rankType") not in VALID_RANK_TYPE:
            errors.append(f"{prefix}.rankType invalid: {asset.get('rankType')!r}")
        if not isinstance(asset.get("score"), (int, float)):
            errors.append(f"{prefix}.score must be numeric")
        if not isinstance(asset.get("previousScore"), (int, float)):
            errors.append(f"{prefix}.previousScore must be numeric")
        conf = asset.get("confidence")
        if not isinstance(conf, (int, float)) or not (0 <= conf <= 100):
            errors.append(f"{prefix}.confidence must be numeric 0-100")
        if asset.get("conflict") not in VALID_CONFLICT:
            errors.append(f"{prefix}.conflict invalid: {asset.get('conflict')!r}")
        if not isinstance(asset.get("watchNext"), list):
            errors.append(f"{prefix}.watchNext must be a list")
        elif not all(is_nonempty_string(item) for item in asset.get("watchNext", [])):
            errors.append(f"{prefix}.watchNext must contain only non-empty strings")

        for field in ["id", "symbol", "name", "assetClass", "subgroup", "bias", "freshness", "coverage", "topDriver", "mainConflict", "quick"]:
            if field in asset and not is_nonempty_string(asset[field]):
                errors.append(f"{prefix}.{field} must be non-empty string")

        for field in ["quick", "topDriver", "mainConflict", "coverage", "freshness"]:
            check_no_banned_terms(asset.get(field), f"{prefix}.{field}")

        factors = asset.get("factors")
        if not isinstance(factors, list) or not factors:
            errors.append(f"{prefix}.factors must be a non-empty list")
            continue

        primary_count = 0
        for j, factor in enumerate(factors):
            fp = f"{prefix}.factors[{j}]"
            if not isinstance(factor, dict):
                errors.append(f"{fp} must be an object")
                continue

            required_factor_fields = ["group", "name", "relevance", "score", "status", "derived", "effect", "source", "freshness"]
            for field in required_factor_fields:
                if field not in factor:
                    errors.append(f"{fp} missing {field}")

            relevance = factor.get("relevance")
            if relevance not in VALID_RELEVANCE:
                errors.append(f"{fp}.relevance invalid: {relevance!r}")
            if relevance == "Primary":
                primary_count += 1
            if factor.get("score") not in VALID_SCORES:
                errors.append(f"{fp}.score invalid: {factor.get('score')!r}")
            if factor.get("status") not in VALID_STATUS:
                errors.append(f"{fp}.status invalid: {factor.get('status')!r}")

            for field in ["group", "name", "derived", "effect", "source", "freshness"]:
                if field in factor and not is_nonempty_string(factor[field]):
                    errors.append(f"{fp}.{field} must be non-empty string")
                check_no_banned_terms(factor.get(field), f"{fp}.{field}")

            # Honest scoring: inputs tagged not applicable should not carry a directional score.
            if relevance == "Not applicable" and factor.get("score") not in (0, None):
                errors.append(f"{fp} Not applicable input must have neutral/null score")

        if primary_count == 0:
            warnings.append(f"{prefix} has no Primary factors")

    if len(assets) < 40:
        warnings.append(f"asset universe looks small: {len(assets)} assets")


def main() -> int:
    validate_configs()
    data = load_json(DATA_PATH)
    if isinstance(data, dict):
        if data.get("schema_version") != "0.24":
            warnings.append(f"schema_version is {data.get('schema_version')!r}; expected '0.24'")
        validate_assets(data)
    else:
        errors.append("dashboard data must be a JSON object")

    if errors:
        print("VALIDATION FAILED")
        for err in errors[:250]:
            print("-", err)
        if len(errors) > 250:
            print(f"... {len(errors) - 250} more errors")
        return 1

    assets = data.get("assets", []) if isinstance(data, dict) else []
    print(f"VALIDATION PASSED: {len(assets)} assets")
    if warnings:
        print("WARNINGS:")
        for warning in warnings[:100]:
            print("-", warning)
    return 0


if __name__ == "__main__":
    sys.exit(main())
