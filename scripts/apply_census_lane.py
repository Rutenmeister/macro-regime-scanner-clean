#!/usr/bin/env python3
"""Apply normalized Census real-economy indicators to Macro Regime Scanner JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
CENSUS_PATH = ROOT / "data" / "normalized" / "census_macro.json"
SOURCE_ID = "CENSUS_PUBLIC"
SOURCE_NAME = "U.S. Census Bureau economic indicators"

CENSUS_FACTOR_NAMES = {
    "Census retail sales demand",
    "Census housing starts",
    "Census building permits",
    "Census new home sales",
    "Census durable goods orders",
    "Census trade balance",
    "Census business inventories",
}

FX_USD_BASE = {"USDJPY", "USDCHF", "USDCAD"}
FX_USD_QUOTE = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}
RATES = {"US02Y", "US05Y", "US10Y", "US30Y", "CURVE2S10", "CURVE5S30", "REALY", "BE5Y", "BE10Y"}
EQUITIES = {"SPX", "NDX", "RUT", "DOW", "DAX", "UK100", "NIKKEI", "CHINA50", "HANGSENG", "EM"}
ENERGY = {"WTI", "BRENT", "NG", "GASOLINE", "HEATING"}
CROPS = {"WHEAT", "CORN", "SOY", "COTTON", "COFFEE", "SUGAR"}
PRECIOUS = {"GOLD", "SILVER"}
INDUSTRIAL = {"COPPER", "BCOM"}
CREDIT = {"HY", "IG", "FCI"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        return f"{value:,.2f}{suffix}"
    if isinstance(value, int):
        return f"{value:,}{suffix}"
    return str(value)


def obs(census: dict[str, Any], key: str) -> dict[str, Any]:
    return census.get("observations", {}).get(key, {}) if isinstance(census, dict) else {}


def clamp(score: int | None) -> int | None:
    if score is None:
        return None
    return max(-2, min(2, int(score)))


def status_from_score(score: int | None) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure", None: "Missing"}.get(score, "Neutral")


def factor(name: str, relevance: str, score: int | None, derived: str, effect: str) -> dict[str, Any]:
    return {
        "group": "Census Real Economy",
        "name": name,
        "relevance": relevance,
        "score": score,
        "status": status_from_score(score),
        "derived": derived,
        "effect": effect,
        "source": SOURCE_NAME,
        "freshness": "Fresh" if score is not None else "Missing",
    }


def asset_role(asset: dict[str, Any]) -> str:
    aid = asset.get("id")
    cls = asset.get("assetClass")
    if aid == "DXY" or cls == "FX":
        return "fx"
    if aid in RATES or cls in {"Rates", "Inflation Markets"}:
        return "rates"
    if aid in EQUITIES or cls == "Equity Indices":
        return "equity"
    if aid in CREDIT or cls == "Credit / Liquidity":
        return "credit"
    if aid in PRECIOUS:
        return "precious"
    if aid in ENERGY:
        return "energy"
    if aid in CROPS:
        return "crop"
    if aid in INDUSTRIAL or aid == "BCOM":
        return "industrial_commodity"
    if cls == "Commodities":
        return "commodity"
    return "context"


def relevance_for(asset: dict[str, Any], kind: str) -> str:
    role = asset_role(asset)
    aid = asset.get("id")
    if kind in {"consumer_demand", "business_investment"}:
        if role in {"equity", "credit", "rates", "fx"}:
            return "Primary"
        if role in {"energy", "industrial_commodity", "commodity"}:
            return "Secondary"
        return "Contextual"
    if kind == "housing_activity":
        if role in {"rates", "equity", "credit"} or aid in {"COPPER", "LUMBER"}:
            return "Primary"
        if role in {"industrial_commodity", "energy"}:
            return "Secondary"
        return "Contextual"
    if kind == "trade_balance":
        if role in {"fx", "rates"}:
            return "Secondary"
        return "Contextual"
    if kind == "inventory_cycle":
        if role in {"equity", "credit"}:
            return "Secondary"
        return "Contextual"
    return "Contextual"


def score_for_asset(asset: dict[str, Any], raw_score: int | None, kind: str) -> int | None:
    if raw_score is None:
        return None
    role = asset_role(asset)
    aid = asset.get("id")
    score = int(raw_score)

    if kind in {"consumer_demand", "business_investment", "housing_activity"}:
        # Strong activity supports risk/demand but can keep rates/USD firmer.
        if role in {"equity", "credit", "energy", "industrial_commodity", "commodity"}:
            return clamp(score)
        if role == "rates" or aid == "DXY":
            return clamp(score)
        if aid in FX_USD_BASE:
            return clamp(score)
        if aid in FX_USD_QUOTE:
            return clamp(-score)
        if role == "precious":
            return clamp(-1 if score >= 2 else (1 if score <= -2 else 0))
        if role == "crop":
            return 0
        return 0

    if kind == "trade_balance":
        # Raw score positive = deficit improves / surplus widens.
        if aid == "DXY" or aid in FX_USD_BASE:
            return clamp(score)
        if aid in FX_USD_QUOTE:
            return clamp(-score)
        if role in {"equity", "rates", "credit"}:
            return clamp(1 if score > 0 else (-1 if score < 0 else 0))
        return 0

    if kind == "inventory_cycle":
        # Inventory builds are ambiguous; keep small and mostly contextual.
        if role in {"equity", "credit"}:
            return clamp(score)
        return 0

    return 0


def derived(o: dict[str, Any]) -> str:
    if not o:
        return "Census observation missing from normalized real-economy lane."
    pct = o.get("percentChange")
    pct_text = f"; month-over-month change {fmt(pct, '%')}" if pct is not None else ""
    return (
        f"{o.get('label')} ({o.get('seriesId')}) latest {fmt(o.get('latestValue'))} {o.get('unit', '')} "
        f"for {o.get('period')}; previous {fmt(o.get('previousValue'))} for {o.get('previousPeriod')}"
        f"; absolute change {fmt(o.get('change'))}{pct_text}."
    )


def effect_for(asset: dict[str, Any], kind: str, label: str) -> str:
    name = asset.get("name")
    aid = asset.get("id")
    role = asset_role(asset)
    if kind == "consumer_demand":
        if role == "equity":
            return f"Primary effect: Strong retail demand generally supports {name} earnings and growth expectations; weak retail demand pressures risk appetite."
        if role == "rates":
            return f"Primary effect: Strong consumer demand can support higher rate pressure for {name}; weak demand can reduce rate pressure but raise slowdown risk."
        if aid == "DXY" or aid in FX_USD_BASE:
            return "Primary effect: Strong U.S. demand can support the dollar through growth/rate channels; weak demand can reduce that support."
        if aid in FX_USD_QUOTE:
            return f"Primary effect: Strong U.S. demand can support USD, which usually pressures {asset.get('symbol')}; weak demand can support the pair."
        if role in {"energy", "industrial_commodity", "commodity"}:
            return f"Secondary effect: Strong consumer demand supports broad demand expectations for {name}; weak demand reduces demand pressure."
        if role == "precious":
            return f"Contextual/mixed effect: Strong demand can lift rates and reduce defensive demand for {name}; weak demand can support defensive demand."
        return f"Contextual effect: Retail demand affects {name} through U.S. growth, policy, dollar, and risk-appetite channels."
    if kind == "housing_activity":
        if role == "rates":
            return f"Primary effect: Strong housing activity can support higher rate pressure for {name}; weak housing activity can reduce rate pressure and signal slowdown."
        if role == "equity":
            return f"Primary/secondary effect: Housing activity affects {name} through rate sensitivity, consumer balance sheets, construction demand, and growth expectations."
        if role in {"industrial_commodity", "energy", "commodity"}:
            return f"Secondary effect: Strong housing activity can support construction/material demand for {name}; weak housing reduces that demand channel."
        return f"Contextual effect: Housing data affects {name} through rate-sensitive growth and construction demand channels."
    if kind == "business_investment":
        if role == "equity":
            return f"Primary effect: Strong durable-goods orders support business investment and cyclical earnings expectations for {name}; weakness pressures growth."
        if role in {"rates", "fx"}:
            return f"Primary effect: Strong business investment can support U.S. growth/rate pressure for {name}; weaker orders reduce that support."
        if role in {"industrial_commodity", "energy", "commodity"}:
            return f"Secondary effect: Strong durable orders can support industrial demand expectations for {name}; weakness reduces demand pressure."
        return f"Contextual effect: Durable goods orders are a business-cycle input for {name}."
    if kind == "trade_balance":
        if aid == "DXY" or role == "fx":
            return f"Secondary effect: An improving U.S. trade balance can support USD/external-balance context for {name}; deterioration can pressure it."
        return f"Contextual effect: Trade balance affects {name} through growth, external demand, dollar, and import/export channels."
    if kind == "inventory_cycle":
        return f"Contextual effect: Business inventories affect {name} through restocking/overhang signals; inventory builds are not automatically bullish or bearish without sales context."
    return f"Contextual effect: {label} is useful real-economy context for {name}."


def make_factor(asset: dict[str, Any], o: dict[str, Any], display_name: str) -> dict[str, Any]:
    kind = o.get("kind", "context") if o else "context"
    raw_score = o.get("score") if o else None
    score = score_for_asset(asset, raw_score, kind)
    return factor(display_name, relevance_for(asset, kind), score, derived(o), effect_for(asset, kind, display_name))


def main() -> int:
    if not CENSUS_PATH.exists():
        raise SystemExit(f"Missing normalized Census macro file: {CENSUS_PATH.relative_to(ROOT)}")
    data = load_json(DATA_PATH)
    census = load_json(CENSUS_PATH)
    for asset in data.get("assets", []):
        factors = [f for f in asset.get("factors", []) if f.get("name") not in CENSUS_FACTOR_NAMES]
        new_factors = [
            make_factor(asset, obs(census, "RETAIL_SALES_TOTAL"), "Census retail sales demand"),
            make_factor(asset, obs(census, "HOUSING_STARTS"), "Census housing starts"),
            make_factor(asset, obs(census, "BUILDING_PERMITS"), "Census building permits"),
            make_factor(asset, obs(census, "NEW_HOME_SALES"), "Census new home sales"),
            make_factor(asset, obs(census, "DURABLE_GOODS_ORDERS"), "Census durable goods orders"),
            make_factor(asset, obs(census, "TRADE_BALANCE"), "Census trade balance"),
            make_factor(asset, obs(census, "BUSINESS_INVENTORIES"), "Census business inventories"),
        ]
        asset["factors"] = factors + new_factors

    status = data.setdefault("source_status", {})
    status[SOURCE_ID] = {
        "label": "Census real economy",
        "status": "live",
        "freshness": "Fresh",
        "latest_date": census.get("retrievedAt"),
        "note": "Retail sales, housing, durable orders, trade, and inventory variables from Census/public economic-indicator series.",
    }
    data["schema_version"] = "0.29"
    data["data_mode"] = "public-source-live-with-census-real-economy"
    write_json(DATA_PATH, data)
    print(f"Applied Census macro lane to {len(data.get('assets', []))} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
