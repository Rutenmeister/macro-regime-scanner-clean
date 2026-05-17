#!/usr/bin/env python3
"""Apply normalized BLS inflation/labor macro data to Macro Regime Scanner JSON.

v0.24 adds a BLS public-source macro lane. The lane is intentionally clear
about direction and channel: inflation/labor data is primary for rates, the
U.S. dollar, inflation markets, and policy pressure; secondary/contextual for
risk assets and commodities; low/directly limited for assets where other source
lanes matter more.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
BLS_PATH = ROOT / "data" / "normalized" / "bls_macro.json"
SOURCE_NAME = "U.S. Bureau of Labor Statistics public API"

BLS_FACTOR_NAMES = {
    "CPI pressure",
    "PPI pressure",
    "Labor strength",
    "BLS CPI pressure",
    "BLS core CPI pressure",
    "BLS CPI shelter pressure",
    "BLS CPI energy pressure",
    "BLS CPI food pressure",
    "BLS services inflation pressure",
    "BLS PPI pressure",
    "BLS core PPI pressure",
    "BLS unemployment rate",
    "BLS payroll growth",
    "BLS wage pressure",
    "BLS labor participation",
    "BLS U-6 unemployment",
}

FX_USD_BASE = {"USDJPY", "USDCHF", "USDCAD"}
FX_USD_QUOTE = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}
RATES = {"US02Y", "US05Y", "US10Y", "US30Y", "CURVE2S10", "CURVE5S30", "REALY", "BE5Y", "BE10Y"}
EQUITIES = {"SPX", "NDX", "RUT", "DOW", "DAX", "UK100", "NIKKEI", "CHINA50", "HANGSENG", "EM"}
ENERGY = {"WTI", "BRENT", "NG", "GASOLINE", "HEATING"}
CROPS = {"WHEAT", "CORN", "SOY", "COTTON", "COFFEE", "SUGAR"}
PRECIOUS = {"GOLD", "SILVER"}


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


def obs(bls: dict[str, Any], key: str) -> dict[str, Any]:
    return bls.get("observations", {}).get(key, {}) if isinstance(bls, dict) else {}


def status_from_score(score: int | None) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure", None: "Missing"}.get(score, "Neutral")


def factor(name: str, relevance: str, score: int | None, status: str, derived: str, effect: str) -> dict[str, Any]:
    return {
        "group": "BLS Inflation / Labor",
        "name": name,
        "relevance": relevance,
        "score": score,
        "status": status,
        "derived": derived,
        "effect": effect,
        "source": SOURCE_NAME,
        "freshness": "Fresh" if score is not None else "Missing",
    }


def clamp_score(score: int | None) -> int | None:
    if score is None:
        return None
    return max(-2, min(2, int(score)))


def derived_inflation(o: dict[str, Any]) -> str:
    if not o:
        return "BLS inflation observation missing from normalized macro lane."
    parts = [
        f"{o.get('label')} ({o.get('series_id')}) latest {fmt(o.get('latest_value'))} on {o.get('latest_date')}",
        f"year-over-year change {fmt(o.get('yoy_pct_change'), '%')}",
    ]
    if o.get("three_month_annualized_pct") is not None:
        parts.append(f"3-month annualized pace {fmt(o.get('three_month_annualized_pct'), '%')}")
    return "; ".join(parts) + "."


def derived_level(o: dict[str, Any]) -> str:
    if not o:
        return "BLS labor observation missing from normalized macro lane."
    parts = [
        f"{o.get('label')} ({o.get('series_id')}) latest {fmt(o.get('latest_value'))} {o.get('unit')} on {o.get('latest_date')}",
    ]
    if o.get("month_change") is not None:
        parts.append(f"one-month change {fmt(o.get('month_change'))} {o.get('unit')}")
    if o.get("yoy_pct_change") is not None:
        parts.append(f"year-over-year change {fmt(o.get('yoy_pct_change'), '%')}")
    return "; ".join(parts) + "."


def asset_role(asset: dict[str, Any]) -> str:
    aid = asset.get("id")
    if aid == "DXY" or asset.get("assetClass") == "FX":
        return "fx"
    if aid in RATES or asset.get("assetClass") == "Rates" or asset.get("assetClass") == "Inflation Markets":
        return "rates"
    if aid in EQUITIES or asset.get("assetClass") == "Equity Indices":
        return "equity"
    if asset.get("assetClass") == "Credit / Liquidity":
        return "credit"
    if aid in PRECIOUS:
        return "precious"
    if aid in ENERGY:
        return "energy"
    if aid in CROPS:
        return "crop"
    if aid == "BCOM":
        return "broad_commodity"
    if asset.get("assetClass") == "Commodities":
        return "commodity"
    return "context"


def relevance_for(asset: dict[str, Any], kind: str) -> str:
    role = asset_role(asset)
    aid = asset.get("id")
    if kind == "inflation":
        if role in {"rates", "fx"} or aid in {"BE5Y", "BE10Y", "REALY"}:
            return "Primary"
        if role in {"equity", "precious", "credit"}:
            return "Secondary"
        if role in {"energy", "crop", "broad_commodity", "commodity"}:
            return "Contextual"
    if kind == "labor":
        if role in {"rates", "fx"}:
            return "Primary"
        if role in {"equity", "credit", "precious"}:
            return "Secondary"
        if role in {"energy", "crop", "broad_commodity", "commodity"}:
            return "Contextual"
    return "Contextual"


def score_for_asset(asset: dict[str, Any], raw_score: int | None, kind: str) -> int | None:
    if raw_score is None:
        return None
    role = asset_role(asset)
    aid = asset.get("id")
    score = int(raw_score)
    # Inflation/labor pressure supports rates, inflation markets, and often USD policy-pressure reads.
    if role == "rates" or aid in {"DXY"}:
        return clamp_score(score)
    # USD-quote pairs generally move opposite broad USD support; USD-base pairs move with it.
    if aid in FX_USD_QUOTE:
        return clamp_score(-score)
    if aid in FX_USD_BASE:
        return clamp_score(score)
    # JPY crosses without USD are contextual: strong U.S. data is not their direct driver.
    if role == "fx":
        return 0
    # Risk assets often dislike hot inflation/tight labor because it can lift policy-rate pressure.
    if role in {"equity", "credit"}:
        return clamp_score(-score)
    # Gold/silver: inflation can help the hedge narrative, but strong CPI/labor often raises rates/real yields.
    if role == "precious":
        return clamp_score(-score if kind in {"inflation", "labor"} else 0)
    # Commodities: BLS data is mostly macro context; keep score muted unless inflation pressure is strong.
    if role in {"energy", "crop", "broad_commodity", "commodity"}:
        if kind == "inflation":
            return clamp_score(1 if score >= 2 else (0 if score >= 0 else -1))
        return 0
    return 0


def effect_for(asset: dict[str, Any], input_name: str, kind: str) -> str:
    role = asset_role(asset)
    name = asset.get("name")
    aid = asset.get("id")
    if kind == "inflation":
        if role == "rates":
            return f"Direct effect: Stronger inflation usually supports higher U.S. rate pressure for {name} because markets expect tighter policy or firmer nominal yields; softer inflation reduces that pressure."
        if aid == "DXY":
            return "Primary effect: Stronger U.S. inflation can support the dollar if it raises Fed-policy and yield pressure; softer inflation can reduce that support."
        if aid in FX_USD_QUOTE:
            return f"Primary effect: Stronger U.S. inflation can support USD through rate expectations, which usually pressures {asset.get('symbol')}; softer inflation can support the pair by reducing USD pressure."
        if aid in FX_USD_BASE:
            return f"Primary effect: Stronger U.S. inflation can support USD through rate expectations, which usually supports {asset.get('symbol')}; softer inflation can reduce that support."
        if role == "equity":
            return f"Secondary effect: Hot inflation usually pressures {name} because it can raise rate/real-yield pressure and reduce valuation support; softer inflation usually eases that pressure."
        if role == "credit":
            return f"Secondary effect: Hot inflation can pressure {name} through tighter policy, higher financing costs, and weaker risk appetite; softer inflation usually eases that stress."
        if role == "precious":
            return f"Secondary/mixed effect: Inflation can support {name} as a hedge, but if CPI raises real-yield or dollar pressure faster, it can hurt the metal."
        if role in {"energy", "crop", "broad_commodity", "commodity"}:
            return f"Contextual effect: BLS inflation does not directly set {name} supply/demand, but it affects macro pressure, policy expectations, and broad commodity inflation sentiment."
    if kind == "labor":
        if role == "rates":
            return f"Direct effect: Strong labor data usually supports {name} rate pressure because it can keep Fed policy firmer; weak labor usually reduces rate pressure but can raise recession concerns."
        if aid == "DXY":
            return "Primary effect: Strong U.S. labor data can support the dollar through Fed-policy and growth channels; weak labor can pressure the dollar if rate expectations fall."
        if aid in FX_USD_QUOTE:
            return f"Primary effect: Strong U.S. labor data can support USD, which usually pressures {asset.get('symbol')}; weak labor can reduce USD pressure and support the pair."
        if aid in FX_USD_BASE:
            return f"Primary effect: Strong U.S. labor data can support USD, which usually supports {asset.get('symbol')}; weak labor can reduce that support."
        if role == "equity":
            return f"Secondary/mixed effect: Strong labor supports growth for {name}, but can pressure risk assets if it keeps rates higher. Weak labor lowers rate pressure but can hurt risk appetite through recession fear."
        if role == "credit":
            return f"Secondary effect: Strong labor supports credit through growth, while weak labor can widen stress if recession risk rises. Very strong labor can still pressure credit through higher rates."
        if role == "precious":
            return f"Secondary effect: Strong labor usually pressures {name} through higher rate/real-yield expectations; weak labor can support it if yields fall or safe-haven demand rises."
        if role in {"energy", "crop", "broad_commodity", "commodity"}:
            return f"Contextual effect: BLS labor data does not directly drive {name} supply, but it affects growth demand, Fed expectations, dollar pressure, and risk appetite."
    return f"Contextual effect: {input_name} can affect {name} through macro policy, growth, inflation, and risk channels, but it is not the main direct driver."


def make_inflation_factor(asset: dict[str, Any], o: dict[str, Any], name: str) -> dict[str, Any]:
    raw_score = o.get("score") if o else None
    score = score_for_asset(asset, raw_score, "inflation")
    return factor(
        name,
        relevance_for(asset, "inflation"),
        score,
        status_from_score(score),
        derived_inflation(o),
        effect_for(asset, name, "inflation"),
    )


def make_labor_factor(asset: dict[str, Any], o: dict[str, Any], name: str) -> dict[str, Any]:
    raw_score = o.get("score") if o else None
    score = score_for_asset(asset, raw_score, "labor")
    return factor(
        name,
        relevance_for(asset, "labor"),
        score,
        status_from_score(score),
        derived_level(o),
        effect_for(asset, name, "labor"),
    )


def update_asset(asset: dict[str, Any], bls: dict[str, Any]) -> None:
    old = [
        f for f in asset.setdefault("factors", [])
        if f.get("name") not in BLS_FACTOR_NAMES
        and not str(f.get("source", "")).startswith("BLS")
        and not str(f.get("source", "")).startswith("U.S. Bureau of Labor Statistics")
    ]
    cpi = obs(bls, "CPI_HEADLINE")
    core_cpi = obs(bls, "CPI_CORE")
    shelter = obs(bls, "CPI_SHELTER")
    energy_cpi = obs(bls, "CPI_ENERGY")
    food_cpi = obs(bls, "CPI_FOOD")
    services = obs(bls, "CPI_SERVICES_LESS_ENERGY")
    ppi = obs(bls, "PPI_FINAL_DEMAND")
    core_ppi = obs(bls, "PPI_CORE_FINAL_DEMAND")
    unemp = obs(bls, "UNEMPLOYMENT_RATE")
    payrolls = obs(bls, "NONFARM_PAYROLLS")
    wages = obs(bls, "AVG_HOURLY_EARNINGS")
    participation = obs(bls, "LABOR_FORCE_PARTICIPATION")
    u6 = obs(bls, "U6_UNEMPLOYMENT")
    new = [
        make_inflation_factor(asset, cpi, "BLS CPI pressure"),
        make_inflation_factor(asset, core_cpi, "BLS core CPI pressure"),
        make_inflation_factor(asset, shelter, "BLS CPI shelter pressure"),
        make_inflation_factor(asset, energy_cpi, "BLS CPI energy pressure"),
        make_inflation_factor(asset, food_cpi, "BLS CPI food pressure"),
        make_inflation_factor(asset, services, "BLS services inflation pressure"),
        make_inflation_factor(asset, ppi, "BLS PPI pressure"),
        make_inflation_factor(asset, core_ppi, "BLS core PPI pressure"),
        make_labor_factor(asset, unemp, "BLS unemployment rate"),
        make_labor_factor(asset, payrolls, "BLS payroll growth"),
        make_labor_factor(asset, wages, "BLS wage pressure"),
        make_labor_factor(asset, participation, "BLS labor participation"),
        make_labor_factor(asset, u6, "BLS U-6 unemployment"),
    ]
    asset["factors"] = old + new
    if asset.get("freshness") == "Sample":
        asset["freshness"] = "Mixed"
    asset["coverage"] = (asset.get("coverage", "") + " | BLS inflation/labor").strip(" |")
    watch = list(asset.get("watchNext", []))
    for item in ["CPI", "Payrolls", "Unemployment"]:
        if item not in watch:
            watch.append(item)
    asset["watchNext"] = watch[:6]
    role = asset_role(asset)
    if role in {"rates", "fx"}:
        asset["topDriver"] = "Rates / BLS macro / COT"
        asset["mainConflict"] = "Inflation and labor must be read with Treasury pressure and positioning"
    elif role in {"equity", "credit"}:
        asset["topDriver"] = "BLS macro / rates pressure"
        asset["mainConflict"] = "Strong growth can support risk, but hot inflation/labor can keep rates restrictive"


def main() -> int:
    if not BLS_PATH.exists():
        raise SystemExit("missing data/normalized/bls_macro.json; run fetch_bls_macro.py first")
    data = load_json(DATA_PATH)
    bls = load_json(BLS_PATH)
    applied = 0
    for asset in data.get("assets", []):
        before_names = [f.get("name") for f in asset.get("factors", [])]
        update_asset(asset, bls)
        after_names = [f.get("name") for f in asset.get("factors", [])]
        if before_names != after_names or any(str(f.get("source", "")).startswith("U.S. Bureau of Labor Statistics") for f in asset.get("factors", [])):
            applied += 1
    data["schema_version"] = "0.26D"
    data["notice"] = "Macro Regime Scanner v0.26D public-source data contract. Existing live lanes are deepened according to the source extraction manifest while price-derived lanes remain excluded."
    data["data_mode"] = "public-source-treasury-cot-eia-usda-bls"
    status = data.setdefault("source_status", {})
    status["BLS_PUBLIC"] = {
        "status": "live",
        "latest_date": bls.get("latest_date") or "unknown",
        "note": f"BLS inflation/labor macro data applied to {applied} assets. Direct for rates, USD, and inflation pressure; secondary/contextual for risk assets and commodities.",
    }
    write_json(DATA_PATH, data)
    print(f"Applied BLS inflation/labor lane to {applied} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
