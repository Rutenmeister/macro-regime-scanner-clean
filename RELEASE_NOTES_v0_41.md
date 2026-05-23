#!/usr/bin/env python3
"""Apply NOAA/NWS weather-hazard context to Macro Regime Scanner assets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
NOAA_PATH = ROOT / "data" / "normalized" / "noaa_weather.json"
SOURCE_NAME = "NOAA/National Weather Service public weather alerts"
SOURCE_STATUS_ID = "NOAA_NWS"

FACTOR_NAMES = {
    "NOAA active weather hazards",
    "NOAA heat stress",
    "NOAA cold / freeze stress",
    "NOAA winter storm stress",
    "NOAA flood stress",
    "NOAA severe storm / tornado stress",
    "NOAA tropical storm / hurricane stress",
    "NOAA fire weather stress",
    "NOAA drought alert context",
}

DISPLAY_MAP = [
    ("ACTIVE_ALERTS", "NOAA active weather hazards"),
    ("HEAT_STRESS", "NOAA heat stress"),
    ("COLD_FREEZE_STRESS", "NOAA cold / freeze stress"),
    ("WINTER_STORM_STRESS", "NOAA winter storm stress"),
    ("FLOOD_STRESS", "NOAA flood stress"),
    ("SEVERE_CONVECTIVE_STRESS", "NOAA severe storm / tornado stress"),
    ("TROPICAL_STORM_STRESS", "NOAA tropical storm / hurricane stress"),
    ("FIRE_WEATHER_STRESS", "NOAA fire weather stress"),
    ("DROUGHT_STRESS", "NOAA drought alert context"),
]

ENERGY = {"WTI", "BRENT", "NG", "GASOLINE", "HEATING"}
CROPS = {"WHEAT", "CORN", "SOY", "COTTON", "COFFEE", "SUGAR"}
EQUITIES = {"SPX", "NDX", "RUT", "DOW", "DAX", "UK100", "NIKKEI", "CHINA50", "HANGSENG", "EM"}
FX = {"DXY", "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD"}
RATES = {"US02Y", "US05Y", "US10Y", "US30Y", "CURVE2S10", "CURVE5S30", "REALY", "BE5Y", "BE10Y"}
PRECIOUS = {"GOLD", "SILVER"}
INDUSTRIAL = {"COPPER", "BCOM"}

ENERGY_DIRECT_KEYS = {"HEAT_STRESS", "COLD_FREEZE_STRESS", "WINTER_STORM_STRESS", "TROPICAL_STORM_STRESS"}
CROP_DIRECT_KEYS = {"HEAT_STRESS", "COLD_FREEZE_STRESS", "FLOOD_STRESS", "SEVERE_CONVECTIVE_STRESS", "FIRE_WEATHER_STRESS", "DROUGHT_STRESS"}
MACRO_CONTEXT_KEYS = {"ACTIVE_ALERTS", "FLOOD_STRESS", "TROPICAL_STORM_STRESS", "WINTER_STORM_STRESS"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def clamp(score: int | None) -> int | None:
    if score is None:
        return None
    return max(-2, min(2, int(score)))


def status_from_score(score: int | None) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure", None: "Missing"}.get(score, "Neutral")


def asset_role(asset: dict[str, Any]) -> str:
    aid = asset.get("id")
    cls = asset.get("assetClass")
    if aid in ENERGY:
        return "energy"
    if aid in CROPS:
        return "crop"
    if aid in EQUITIES or cls == "Equity Indices":
        return "equity"
    if aid in FX or cls == "FX":
        return "fx"
    if aid in RATES or cls in {"Rates", "Inflation Markets"}:
        return "rates"
    if aid in PRECIOUS:
        return "precious"
    if aid in INDUSTRIAL:
        return "industrial_commodity"
    if cls == "Commodities":
        return "commodity"
    return "context"


def include_factor(asset: dict[str, Any], key: str) -> bool:
    role = asset_role(asset)
    if key == "ACTIVE_ALERTS":
        return True
    if role == "energy" and key in ENERGY_DIRECT_KEYS:
        return True
    if role == "crop" and key in CROP_DIRECT_KEYS:
        return True
    if role in {"equity", "fx", "rates", "precious", "industrial_commodity", "commodity"} and key in MACRO_CONTEXT_KEYS:
        return True
    return False


def relevance_for(asset: dict[str, Any], key: str) -> str:
    role = asset_role(asset)
    if role == "energy" and key in ENERGY_DIRECT_KEYS:
        return "Primary"
    if role == "crop" and key in CROP_DIRECT_KEYS:
        return "Primary"
    if role in {"equity", "fx", "rates", "precious", "industrial_commodity", "commodity"} and key in MACRO_CONTEXT_KEYS:
        return "Contextual"
    return "Low relevance"


def score_for_asset(asset: dict[str, Any], raw_score: int | None, key: str) -> int | None:
    if raw_score is None:
        return None
    raw = int(raw_score)
    role = asset_role(asset)
    # Raw NOAA score convention: positive = calm/low hazard, negative = elevated hazard/disruption.
    if role in {"energy", "crop"}:
        if key == "ACTIVE_ALERTS":
            return clamp(0 if raw >= 0 else 1)
        return clamp(-raw)  # elevated weather stress can support commodity price pressure.
    if role == "equity":
        return clamp(raw)  # disruption pressures activity/risk; calm is supportive.
    if role in {"fx", "rates", "precious", "industrial_commodity", "commodity"}:
        if raw < 0:
            return -1 if role in {"industrial_commodity", "commodity"} else 0
        return 0
    return 0


def derived(o: dict[str, Any]) -> str:
    if not o:
        return "NOAA/NWS weather observation missing from normalized lane."
    sample = o.get("sampleEvents") or []
    sample_text = f" Sample events: {', '.join(sample[:5])}." if sample else ""
    weighted = o.get("weightedCount")
    weighted_text = f" weighted count {fmt(weighted)};" if weighted is not None else ""
    return (
        f"{o.get('label')} ({o.get('seriesId')}) latest {fmt(o.get('latestValue'))} active alerts "
        f"for {o.get('period')};{weighted_text} release/effective date {o.get('releaseDate')}. "
        f"Raw lane score treats low active hazard load as positive and elevated weather disruption as negative."
        f"{sample_text}"
    )


def effect_for(asset: dict[str, Any], o: dict[str, Any], key: str) -> str:
    name = asset.get("name")
    role = asset_role(asset)
    kind = o.get("kind", "weather_hazard") if o else "weather_hazard"
    if role == "energy":
        if kind in {"heat_stress", "cold_freeze_stress", "winter_storm_stress"}:
            return f"Primary effect: Weather stress can affect {name} through heating/cooling demand, power load, refinery/transport disruption, and fuel logistics."
        if kind == "tropical_storm_stress":
            return f"Primary/secondary effect: Tropical storm or hurricane risk can affect {name} through Gulf production, refinery, port, and pipeline disruption."
        return f"Contextual effect: Weather hazards can affect {name} through demand, supply logistics, and regional infrastructure risk."
    if role == "crop":
        if kind in {"heat_stress", "cold_freeze_stress", "flood_stress", "fire_weather_stress", "drought_stress"}:
            return f"Primary effect: Weather stress can affect {name} through crop condition, yield risk, planting/harvest disruption, and regional supply uncertainty."
        return f"Contextual effect: Severe weather can affect {name} through logistics and crop-region disruption."
    if role == "equity":
        return f"Contextual effect: Weather hazards can pressure {name} through activity disruption, insurance/infrastructure losses, logistics, energy demand, and regional spending impacts."
    if role == "rates":
        return f"Contextual effect: Weather hazards usually affect {name} indirectly through temporary growth, energy-demand, inflation, and disruption channels."
    if role == "fx":
        return f"Contextual effect: U.S. weather hazards usually affect {name} indirectly through risk appetite, energy prices, growth noise, and dollar-liquidity context."
    if role == "precious":
        return f"Contextual/mixed effect: Weather stress can affect {name} through risk sentiment, energy inflation, USD, and real-yield channels rather than direct supply/demand."
    return f"Contextual effect: NOAA/NWS weather hazards are indirect physical-economy context for {name}."


def make_factor(asset: dict[str, Any], o: dict[str, Any], key: str, display_name: str) -> dict[str, Any]:
    score = score_for_asset(asset, o.get("score") if o else None, key)
    return {
        "group": "Weather / Physical Disruption",
        "name": display_name,
        "relevance": relevance_for(asset, key),
        "score": score,
        "status": status_from_score(score),
        "derived": derived(o),
        "effect": effect_for(asset, o, key),
        "source": SOURCE_NAME,
        "freshness": "Fresh" if score is not None else "Missing",
    }


def update_asset(asset: dict[str, Any], noaa: dict[str, Any]) -> None:
    old = [
        f for f in asset.setdefault("factors", [])
        if f.get("name") not in FACTOR_NAMES
        and not str(f.get("source", "")).startswith("NOAA/National Weather Service")
    ]
    observations = noaa.get("observations", {}) if isinstance(noaa, dict) else {}
    new: list[dict[str, Any]] = []
    for key, label in DISPLAY_MAP:
        if include_factor(asset, key):
            o = observations.get(key)
            if o:
                new.append(make_factor(asset, o, key, label))
    asset["factors"] = old + new
    if asset.get("freshness") == "Sample":
        asset["freshness"] = "Mixed"
    asset["coverage"] = (asset.get("coverage", "") + " | NOAA/NWS weather").strip(" |")
    watch = list(asset.get("watchNext", []))
    for item in ["NOAA alerts", "heat/cold demand", "crop weather", "storm disruption"]:
        if item not in watch:
            watch.append(item)
    asset["watchNext"] = watch[:6]
    role = asset_role(asset)
    if role == "energy":
        asset["topDriver"] = "Energy balances / COT / weather demand"
        asset["mainConflict"] = "Weather demand can conflict with inventories, production, and positioning"
    elif role == "crop":
        asset["topDriver"] = "USDA crop data / COT / weather stress"
        asset["mainConflict"] = "Weather risk can conflict with USDA supply estimates and export demand"


def main() -> int:
    if not NOAA_PATH.exists():
        raise SystemExit("missing data/normalized/noaa_weather.json; run fetch_noaa_weather.py first")
    data = load_json(DATA_PATH)
    noaa = load_json(NOAA_PATH)
    applied = 0
    for asset in data.get("assets", []):
        update_asset(asset, noaa)
        if any(str(f.get("source", "")).startswith("NOAA/National Weather Service") for f in asset.get("factors", [])):
            applied += 1
    data["schema_version"] = "0.24"
    data["notice"] = "Macro Regime Scanner v0.31 public-source data contract. NOAA/NWS weather-hazard lane added to the v0.30 credit/financial-stress live baseline. Price-derived lanes remain excluded."
    data["data_mode"] = "public-source-treasury-cot-eia-usda-bls-bea-fed-census-credit-stress-noaa-weather"
    status = data.setdefault("source_status", {})
    status[SOURCE_STATUS_ID] = {
        "status": "live",
        "latest_date": noaa.get("latestDate") or "unknown",
        "note": f"NOAA/NWS weather-hazard lane applied to {applied} assets. Uses public NOAA/NWS active alerts endpoint; no API key required in v0.31.",
    }
    write_json(DATA_PATH, data)
    print(f"Applied NOAA/NWS weather lane to {applied} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
