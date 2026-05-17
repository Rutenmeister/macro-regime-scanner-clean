#!/usr/bin/env python3
"""Apply normalized USDA/NASS agriculture fundamentals to Macro Regime Scanner JSON.

v0.23 adds a USDA/NASS Quick Stats crop lane for public-source agriculture
fundamentals. This lane avoids prices and price-derived technicals. It applies
condition, progress, and production inputs to crop assets where the data is
primary, and keeps the effect language direct: stronger supply usually pressures
crop prices; weaker supply or crop stress usually supports them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
USDA_PATH = ROOT / "data" / "normalized" / "usda_agriculture.json"
SOURCE_NAME = "USDA National Agricultural Statistics Service Quick Stats API"

USDA_FACTOR_NAMES = {
    "USDA crop condition",
    "USDA production estimate",
    "USDA crop progress context",
}

ASSET_TO_CROP = {
    "WHEAT": "WHEAT",
    "CORN": "CORN",
    "SOY": "SOY",
    "COTTON": "COTTON",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        return f"{value:,.1f}{suffix}"
    if isinstance(value, int):
        return f"{value:,}{suffix}"
    return str(value)


def status_from_score(score: int | None) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure", None: "Missing"}.get(score, "Neutral")


def obs(usda: dict[str, Any], key: str) -> dict[str, Any]:
    return usda.get("observations", {}).get(key, {}) if isinstance(usda, dict) else {}


def factor(name: str, relevance: str, score: int | None, status: str, derived: str, effect: str) -> dict[str, Any]:
    return {
        "group": "USDA Agriculture Fundamentals",
        "name": name,
        "relevance": relevance,
        "score": score,
        "status": status,
        "derived": derived,
        "effect": effect,
        "source": SOURCE_NAME,
        "freshness": "Fresh" if score is not None else "Missing",
    }


def condition_factor(asset: dict[str, Any], crop_key: str, o: dict[str, Any]) -> dict[str, Any]:
    score = o.get("score") if o else None
    score = None if score is None else int(score)
    derived = (
        f"USDA/NASS {o.get('crop')} crop condition for {o.get('latest_period')}: "
        f"good/excellent {fmt(o.get('good_excellent_pct'), '%')} "
        f"(good {fmt(o.get('good_pct'), '%')}, excellent {fmt(o.get('excellent_pct'), '%')}); "
        f"poor/very poor {fmt((o.get('poor_pct') or 0) + (o.get('very_poor_pct') or 0), '%')}."
    ) if o else "USDA/NASS crop condition observation missing."
    effect = (
        f"Direct effect: For {asset.get('name')}, weak crop condition usually supports prices because it raises supply-risk concerns; "
        "strong crop condition usually pressures prices because the supply outlook improves."
    )
    return factor("USDA crop condition", "Primary", score, status_from_score(score), derived, effect)


def production_factor(asset: dict[str, Any], crop_key: str, o: dict[str, Any]) -> dict[str, Any]:
    score = o.get("score") if o else None
    score = None if score is None else int(score)
    derived = (
        f"USDA/NASS {o.get('crop')} production: {fmt(o.get('latest_value'))} {o.get('unit')} in {o.get('latest_year')} "
        f"vs {fmt(o.get('previous_value'))} {o.get('unit')} in {o.get('previous_year')}; "
        f"change {fmt(o.get('change_pct'), '%')}."
    ) if o else "USDA/NASS production observation missing."
    effect = (
        f"Direct effect: For {asset.get('name')}, larger production usually pressures prices because available supply increases; "
        "smaller production usually supports prices because the supply cushion tightens."
    )
    return factor("USDA production estimate", "Primary", score, status_from_score(score), derived, effect)


def progress_factor(asset: dict[str, Any], crop_key: str, o: dict[str, Any]) -> dict[str, Any]:
    score = o.get("score") if o else None
    score = None if score is None else int(score)
    stages = o.get("stages", []) if o else []
    if stages:
        stage_text = "; ".join(f"{s.get('short_desc')}: {fmt(s.get('value'), '%')}" for s in stages[:4])
        derived = f"USDA/NASS {o.get('crop')} crop progress for {o.get('latest_period')}: {stage_text}."
    else:
        derived = "USDA/NASS crop progress observation missing."
    effect = (
        f"Direct/context effect: For {asset.get('name')}, delayed planting, emergence, or harvest can support prices by increasing supply risk; "
        "smooth progress can reduce risk premium. This row is neutral until compared with normal pace."
    )
    return factor("USDA crop progress context", "Primary", score, status_from_score(score), derived, effect)


def broad_commodity_factor(asset: dict[str, Any], usda: dict[str, Any]) -> list[dict[str, Any]]:
    obs_map = usda.get("observations", {}) if isinstance(usda, dict) else {}
    scores = []
    derived_parts = []
    for key, o in obs_map.items():
        if key.endswith("_CONDITION") and o.get("score") is not None:
            scores.append(int(o["score"]))
            derived_parts.append(f"{o.get('crop')} good/excellent {fmt(o.get('good_excellent_pct'), '%')}")
    score = 0 if not scores else max(-2, min(2, round(sum(scores) / len(scores))))
    derived = "USDA/NASS crop-condition cross-crop read: " + "; ".join(derived_parts) if derived_parts else "USDA/NASS crop-condition observations missing."
    return [factor("USDA crop condition", "Contextual", score, status_from_score(score), derived, "Contextual effect: Crop stress supports the broad commodity basket through food/inflation pressure; strong crop conditions reduce that support.")]


def update_crop_asset(asset: dict[str, Any], usda: dict[str, Any]) -> list[dict[str, Any]]:
    crop_key = ASSET_TO_CROP.get(asset.get("id"))
    if not crop_key:
        return []
    return [
        condition_factor(asset, crop_key, obs(usda, f"{crop_key}_CONDITION")),
        production_factor(asset, crop_key, obs(usda, f"{crop_key}_PRODUCTION")),
        progress_factor(asset, crop_key, obs(usda, f"{crop_key}_PROGRESS")),
    ]


def update_asset(asset: dict[str, Any], usda: dict[str, Any]) -> None:
    old = [
        f for f in asset.setdefault("factors", [])
        if f.get("name") not in USDA_FACTOR_NAMES
        and not str(f.get("source", "")).startswith("USDA National Agricultural Statistics Service")
    ]
    if asset.get("id") in ASSET_TO_CROP:
        new = update_crop_asset(asset, usda)
    elif asset.get("id") == "BCOM":
        new = broad_commodity_factor(asset, usda)
    else:
        new = []
    if new:
        asset["factors"] = old + new
        if asset.get("freshness") == "Sample":
            asset["freshness"] = "Mixed"
        asset["coverage"] = (asset.get("coverage", "") + " | USDA agriculture fundamentals").strip(" |")
        if asset.get("id") in ASSET_TO_CROP:
            asset["topDriver"] = "USDA crop condition / production"
            asset["mainConflict"] = "Read USDA supply signals with COT positioning and energy/input-cost context"
            watch = list(asset.get("watchNext", []))
            for item in ["Next USDA/NASS update", "Crop condition", "Production estimate"]:
                if item not in watch:
                    watch.append(item)
            asset["watchNext"] = watch[:6]


def main() -> int:
    if not USDA_PATH.exists():
        raise SystemExit("missing data/normalized/usda_agriculture.json; run fetch_usda_agriculture.py first")
    data = load_json(DATA_PATH)
    usda = load_json(USDA_PATH)
    applied = 0
    for asset in data.get("assets", []):
        before = len(asset.get("factors", []))
        update_asset(asset, usda)
        if len(asset.get("factors", [])) != before or any(str(f.get("source", "")).startswith("USDA National Agricultural Statistics Service") for f in asset.get("factors", [])):
            applied += 1

    data["schema_version"] = "0.23"
    data["notice"] = "Macro Regime Scanner v0.23 public-source data contract. Treasury, CFTC COT, EIA energy, and USDA/NASS agriculture lanes are live/workflow-ready. USDA adds public crop condition, progress, and production fundamentals. Price-derived lanes remain excluded."
    data["data_mode"] = "public-source-treasury-cot-eia-usda"
    status = data.setdefault("source_status", {})
    status["USDA_PUBLIC"] = {
        "status": "live",
        "latest_date": usda.get("latest_date") or "unknown",
        "note": f"USDA/NASS agriculture fundamentals applied to {applied} assets. Direct for wheat, corn, soybeans, and cotton; contextual for broad commodity pressure.",
    }
    write_json(DATA_PATH, data)
    print(f"Applied USDA/NASS agriculture lane to {applied} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
