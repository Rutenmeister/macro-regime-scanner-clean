#!/usr/bin/env python3
"""Apply normalized BEA growth/PCE macro data to Macro Regime Scanner JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
BEA_PATH = ROOT / "data" / "normalized" / "bea_macro.json"
SOURCE_NAME = "U.S. Bureau of Economic Analysis API"

BEA_FACTOR_NAMES = {
    "BEA real GDP growth",
    "BEA PCE inflation pressure",
    "BEA core PCE inflation pressure",
    "BEA real consumption growth",
    "BEA personal income growth",
    "BEA savings rate",
}

FX_USD_BASE = {"USDJPY", "USDCHF", "USDCAD"}
FX_USD_QUOTE = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}
RATES = {"US02Y", "US05Y", "US10Y", "US30Y", "CURVE2S10", "CURVE5S30", "REALY", "BE5Y", "BE10Y"}
EQUITIES = {"SPX", "NDX", "RUT", "DOW", "DAX", "UK100", "NIKKEI", "CHINA50", "HANGSENG", "EM"}
ENERGY = {"WTI", "BRENT", "NG", "GASOLINE", "HEATING"}
CROPS = {"WHEAT", "CORN", "SOY", "COTTON", "COFFEE", "SUGAR"}
PRECIOUS = {"GOLD", "SILVER"}
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


def obs(bea: dict[str, Any], key: str) -> dict[str, Any]:
    return bea.get("observations", {}).get(key, {}) if isinstance(bea, dict) else {}


def clamp(score: int | None) -> int | None:
    if score is None:
        return None
    return max(-2, min(2, int(score)))


def status_from_score(score: int | None) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure", None: "Missing"}.get(score, "Neutral")


def factor(name: str, relevance: str, score: int | None, derived: str, effect: str) -> dict[str, Any]:
    return {
        "group": "BEA Growth / PCE",
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
    if aid == "BCOM":
        return "broad_commodity"
    if cls == "Commodities":
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
        return "Contextual"
    if kind == "growth":
        if role in {"equity", "credit", "rates", "fx"}:
            return "Primary"
        if role in {"energy", "broad_commodity", "commodity"}:
            return "Secondary"
        if role in {"precious", "crop"}:
            return "Contextual"
    if kind == "level":
        return "Contextual"
    return "Contextual"


def score_for_asset(asset: dict[str, Any], raw_score: int | None, kind: str) -> int | None:
    if raw_score is None:
        return None
    role = asset_role(asset)
    aid = asset.get("id")
    score = int(raw_score)

    if kind == "inflation":
        # PCE inflation is the Fed's preferred inflation channel: rate/USD support, risk/metal pressure.
        if role == "rates" or aid == "DXY":
            return clamp(score)
        if aid in FX_USD_QUOTE:
            return clamp(-score)
        if aid in FX_USD_BASE:
            return clamp(score)
        if role in {"equity", "credit", "precious"}:
            return clamp(-score)
        if role in {"energy", "crop", "broad_commodity", "commodity"}:
            return clamp(1 if score >= 2 else (0 if score >= 0 else -1))
        return 0

    if kind == "growth":
        # Strong growth supports risk/demand and can also keep rates/USD firmer.
        if role in {"equity", "credit"}:
            return clamp(score)
        if role == "rates" or aid == "DXY":
            return clamp(score)
        if aid in FX_USD_QUOTE:
            return clamp(-score)
        if aid in FX_USD_BASE:
            return clamp(score)
        if role in {"energy", "broad_commodity", "commodity"}:
            return clamp(1 if score > 0 else (-1 if score < 0 else 0))
        if role == "crop":
            return 0
        if role == "precious":
            # Growth can reduce recession hedging but can also lift rates; keep muted.
            return clamp(-1 if score >= 2 else (1 if score <= -2 else 0))
        return 0

    # Savings rate and other levels are context-only for now.
    return 0


def derived(o: dict[str, Any]) -> str:
    if not o:
        return "BEA observation missing from normalized macro lane."
    return (
        f"{o.get('label')} ({o.get('seriesId')}) latest {fmt(o.get('latestValue'), '%' if o.get('unit','').startswith('percent') else '')} "
        f"for {o.get('period')}; previous {fmt(o.get('previousValue'), '%' if o.get('unit','').startswith('percent') else '')} "
        f"for {o.get('previousPeriod')}; change {fmt(o.get('change'), ' pts' if o.get('unit','').startswith('percent') else '')}."
    )


def effect_for(asset: dict[str, Any], kind: str, label: str) -> str:
    name = asset.get("name")
    aid = asset.get("id")
    role = asset_role(asset)
    if kind == "inflation":
        if role == "rates":
            return f"Primary effect: Higher BEA PCE inflation usually supports higher rate pressure for {name}; softer PCE inflation reduces that pressure."
        if aid == "DXY":
            return "Primary effect: Higher PCE inflation can support the dollar if it raises Fed-policy/yield pressure; softer PCE inflation can weaken that support."
        if aid in FX_USD_QUOTE:
            return f"Primary effect: Higher U.S. PCE inflation can support USD through Fed expectations, which usually pressures {asset.get('symbol')}; softer PCE inflation can support the pair."
        if aid in FX_USD_BASE:
            return f"Primary effect: Higher U.S. PCE inflation can support USD through Fed expectations, which usually supports {asset.get('symbol')}; softer PCE inflation can reduce that support."
        if role == "equity":
            return f"Secondary effect: Hot PCE inflation usually pressures {name} through higher rate/real-yield expectations; softer PCE inflation generally eases that pressure."
        if role == "precious":
            return f"Secondary/mixed effect: PCE inflation can support the hedge narrative for {name}, but if it lifts real yields or the dollar, it can pressure the metal."
        return f"Contextual effect: {label} affects {name} through Fed policy, dollar pressure, inflation expectations, and broad demand conditions, but it is not the main physical driver."
    if kind == "growth":
        if role == "equity":
            return f"Primary effect: Stronger BEA growth/consumption usually supports {name} earnings and demand expectations; weaker growth usually pressures risk appetite."
        if role == "rates":
            return f"Primary effect: Stronger growth usually supports higher yield pressure for {name}; weaker growth usually reduces rate pressure but can raise recession risk."
        if aid == "DXY":
            return "Primary effect: Stronger U.S. growth can support the dollar through growth and rate-differential channels; weaker growth can pressure it."
        if aid in FX_USD_QUOTE:
            return f"Primary effect: Stronger U.S. growth can support USD, which usually pressures {asset.get('symbol')}; weaker U.S. growth can support the pair."
        if aid in FX_USD_BASE:
            return f"Primary effect: Stronger U.S. growth can support USD, which usually supports {asset.get('symbol')}; weaker U.S. growth can pressure the pair."
        if role in {"energy", "broad_commodity", "commodity"}:
            return f"Secondary effect: Stronger U.S. consumption/growth can support demand expectations for {name}; weaker growth reduces demand pressure."
        if role == "precious":
            return f"Contextual/mixed effect: Strong growth can reduce safe-haven demand for {name} and lift rates, while weak growth can support defensive demand."
        return f"Contextual effect: BEA growth data affects {name} through broad demand, policy, dollar, and risk-appetite channels."
    return f"Contextual effect: {label} is useful macro context for {name}, but it is not scored as a direct driver yet."


def make_factor(asset: dict[str, Any], o: dict[str, Any], display_name: str) -> dict[str, Any]:
    kind = o.get("kind", "context") if o else "context"
    raw_score = o.get("score") if o else None
    score = score_for_asset(asset, raw_score, kind)
    return factor(display_name, relevance_for(asset, kind), score, derived(o), effect_for(asset, kind, display_name))


def update_asset(asset: dict[str, Any], bea: dict[str, Any]) -> None:
    old = [
        f for f in asset.setdefault("factors", [])
        if f.get("name") not in BEA_FACTOR_NAMES
        and not str(f.get("source", "")).startswith("U.S. Bureau of Economic Analysis")
    ]
    new: list[dict[str, Any]] = []
    mapping = [
        ("REAL_GDP_GROWTH", "BEA real GDP growth"),
        ("PCE_PRICE_PRESSURE", "BEA PCE inflation pressure"),
        ("CORE_PCE_PRICE_PRESSURE", "BEA core PCE inflation pressure"),
        ("REAL_PCE_GROWTH", "BEA real consumption growth"),
        ("PERSONAL_INCOME_GROWTH", "BEA personal income growth"),
        ("SAVING_RATE", "BEA savings rate"),
    ]
    for key, label in mapping:
        o = obs(bea, key)
        if o:
            new.append(make_factor(asset, o, label))
    asset["factors"] = old + new
    if asset.get("freshness") == "Sample":
        asset["freshness"] = "Mixed"
    asset["coverage"] = (asset.get("coverage", "") + " | BEA growth/PCE").strip(" |")
    watch = list(asset.get("watchNext", []))
    for item in ["GDP", "PCE", "Core PCE"]:
        if item not in watch:
            watch.append(item)
    asset["watchNext"] = watch[:6]
    role = asset_role(asset)
    if role in {"rates", "fx"}:
        asset["topDriver"] = "Rates / BLS / BEA / COT"
        asset["mainConflict"] = "Growth, inflation, and positioning must be read together"
    elif role in {"equity", "credit"}:
        asset["topDriver"] = "Growth / inflation / rates pressure"
        asset["mainConflict"] = "Growth support can conflict with inflation/rate pressure"


def main() -> int:
    if not BEA_PATH.exists():
        raise SystemExit("missing data/normalized/bea_macro.json; run fetch_bea_macro.py first")
    data = load_json(DATA_PATH)
    bea = load_json(BEA_PATH)
    applied = 0
    for asset in data.get("assets", []):
        update_asset(asset, bea)
        if any(str(f.get("source", "")).startswith("U.S. Bureau of Economic Analysis") for f in asset.get("factors", [])):
            applied += 1
    data["schema_version"] = "0.27"
    data["notice"] = "Macro Regime Scanner v0.27 public-source data contract. BEA growth/PCE macro lane added to the v0.26D.1 deep extraction baseline. Price-derived lanes remain excluded."
    data["data_mode"] = "public-source-treasury-cot-eia-usda-bls-bea"
    status = data.setdefault("source_status", {})
    status["BEA_PUBLIC"] = {
        "status": "live",
        "latest_date": bea.get("latestDate") or "unknown",
        "note": f"BEA GDP/PCE/growth lane applied to {applied} assets. Direct for rates, USD, equities/growth; contextual for commodities. Missing optional observations are not faked.",
    }
    write_json(DATA_PATH, data)
    print(f"Applied BEA macro lane to {applied} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
