#!/usr/bin/env python3
"""Apply normalized Federal Reserve / liquidity data to Macro Regime Scanner JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
FED_PATH = ROOT / "data" / "normalized" / "fed_macro.json"
SOURCE_NAME = "Federal Reserve / FRED public data"

FED_FACTOR_NAMES = {
    "Fed effective funds rate",
    "Fed total assets",
    "Fed reserve balances",
    "Fed reverse repo usage",
    "Fed Treasury General Account",
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


def obs(fed: dict[str, Any], key: str) -> dict[str, Any]:
    return fed.get("observations", {}).get(key, {}) if isinstance(fed, dict) else {}


def clamp(score: int | None) -> int | None:
    if score is None:
        return None
    return max(-2, min(2, int(score)))


def status_from_score(score: int | None) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure", None: "Missing"}.get(score, "Neutral")


def factor(name: str, relevance: str, score: int | None, derived: str, effect: str) -> dict[str, Any]:
    return {
        "group": "Federal Reserve / Liquidity",
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
    if kind == "policy_rate":
        if role in {"rates", "fx"} or aid in {"REALY", "BE5Y", "BE10Y"}:
            return "Primary"
        if role in {"equity", "credit", "precious"}:
            return "Secondary"
        return "Contextual"
    if kind in {"liquidity_supply", "liquidity_drain"}:
        if role in {"equity", "credit"}:
            return "Primary"
        if role in {"rates", "fx", "precious"}:
            return "Secondary"
        return "Contextual"
    return "Contextual"


def score_for_asset(asset: dict[str, Any], raw_score: int | None, kind: str) -> int | None:
    if raw_score is None:
        return None
    role = asset_role(asset)
    aid = asset.get("id")
    score = int(raw_score)
    if kind == "policy_rate":
        # Restrictive/higher policy rate supports rate/USD pressure; it pressures risk, credit, and metals.
        if role == "rates" or aid == "DXY":
            return clamp(score)
        if aid in FX_USD_BASE:
            return clamp(score)
        if aid in FX_USD_QUOTE:
            return clamp(-score)
        if role in {"equity", "credit", "precious"}:
            return clamp(-score)
        return 0
    if kind in {"liquidity_supply", "liquidity_drain"}:
        # Raw score is already positive when liquidity is easier, negative when liquidity is tighter.
        if role in {"equity", "credit", "precious", "energy", "broad_commodity", "commodity"}:
            return clamp(score)
        if role == "rates":
            return clamp(-score)  # easier liquidity usually reduces upward rate pressure
        if aid == "DXY":
            return clamp(-score)  # easier liquidity can reduce dollar scarcity/support
        if aid in FX_USD_BASE:
            return clamp(-score)
        if aid in FX_USD_QUOTE:
            return clamp(score)
        return 0
    return 0


def derived(o: dict[str, Any]) -> str:
    if not o:
        return "Federal Reserve/FRED observation missing from normalized lane."
    suffix = "%" if o.get("unit") == "percent" else f" {o.get('unit', '')}".rstrip()
    change_suffix = " pts" if o.get("unit") == "percent" else f" {o.get('unit', '')}".rstrip()
    return (
        f"{o.get('label')} ({o.get('seriesId')}) latest {fmt(o.get('latestValue'), suffix)} "
        f"for {o.get('period')}; previous {fmt(o.get('previousValue'), suffix)} "
        f"for {o.get('previousPeriod')}; change {fmt(o.get('change'), change_suffix)}."
    )


def effect_for(asset: dict[str, Any], o: dict[str, Any], label: str) -> str:
    name = asset.get("name")
    aid = asset.get("id")
    role = asset_role(asset)
    kind = o.get("kind", "context") if o else "context"
    if kind == "policy_rate":
        if role == "rates":
            return f"Primary effect: A higher/restrictive effective fed funds rate supports higher policy-rate pressure for {name}; easing reduces that pressure."
        if aid == "DXY":
            return "Primary effect: A higher/restrictive fed funds rate can support the U.S. dollar through rate-differential and cash-yield channels."
        if aid in FX_USD_QUOTE:
            return f"Primary effect: A higher U.S. policy-rate backdrop can support USD, which usually pressures {asset.get('symbol')}; easing can support the pair."
        if aid in FX_USD_BASE:
            return f"Primary effect: A higher U.S. policy-rate backdrop can support USD, which usually supports {asset.get('symbol')}; easing can pressure the pair."
        if role == "equity":
            return f"Secondary effect: A restrictive Fed policy-rate backdrop usually pressures {name} through discount-rate and liquidity channels."
        if role == "precious":
            return f"Secondary effect: A restrictive Fed policy-rate backdrop can pressure {name} through real-yield and dollar channels; easing can reduce that headwind."
        return f"Contextual effect: Fed policy-rate pressure affects {name} through rates, USD, liquidity, and risk appetite rather than direct physical supply."
    if kind in {"liquidity_supply", "liquidity_drain"}:
        if role == "equity":
            return f"Primary effect: Easier Fed/liquidity conditions usually support {name} risk appetite; tighter liquidity usually pressures it."
        if role == "credit":
            return f"Primary effect: Easier liquidity generally supports credit conditions for {name}; tighter liquidity raises stress risk."
        if role == "rates":
            return f"Secondary effect: Easier liquidity can reduce upward yield pressure for {name}; tighter liquidity can increase funding/rate pressure."
        if aid == "DXY":
            return "Secondary effect: Tighter dollar liquidity can support DXY through scarcity/funding channels; easier liquidity can reduce that support."
        if role == "precious":
            return f"Secondary/mixed effect: Easier liquidity can support {name}, while tighter liquidity and a stronger dollar can pressure it."
        return f"Contextual effect: Fed balance-sheet, reserves, RRP, and TGA conditions affect {name} indirectly through liquidity, USD funding, and risk appetite."
    return f"Contextual effect: {label} is useful Fed/liquidity context for {name}, but it is not a direct physical driver."


def make_factor(asset: dict[str, Any], o: dict[str, Any], display_name: str) -> dict[str, Any]:
    kind = o.get("kind", "context") if o else "context"
    raw_score = o.get("score") if o else None
    score = score_for_asset(asset, raw_score, kind)
    return factor(display_name, relevance_for(asset, kind), score, derived(o), effect_for(asset, o, display_name))


def update_asset(asset: dict[str, Any], fed: dict[str, Any]) -> None:
    old = [
        f for f in asset.setdefault("factors", [])
        if f.get("name") not in FED_FACTOR_NAMES
        and not str(f.get("source", "")).startswith("Federal Reserve / FRED")
    ]
    mapping = [
        ("EFFR", "Fed effective funds rate"),
        ("FED_TOTAL_ASSETS", "Fed total assets"),
        ("RESERVE_BALANCES", "Fed reserve balances"),
        ("REVERSE_REPO", "Fed reverse repo usage"),
        ("TREASURY_GENERAL_ACCOUNT", "Fed Treasury General Account"),
    ]
    new: list[dict[str, Any]] = []
    for key, label in mapping:
        o = obs(fed, key)
        if o:
            new.append(make_factor(asset, o, label))
    asset["factors"] = old + new
    if asset.get("freshness") == "Sample":
        asset["freshness"] = "Mixed"
    asset["coverage"] = (asset.get("coverage", "") + " | Fed liquidity").strip(" |")
    watch = list(asset.get("watchNext", []))
    for item in ["EFFR", "Fed balance sheet", "RRP", "TGA"]:
        if item not in watch:
            watch.append(item)
    asset["watchNext"] = watch[:6]
    role = asset_role(asset)
    if role in {"equity", "credit"}:
        asset["topDriver"] = "Liquidity / rates / growth / inflation"
        asset["mainConflict"] = "Liquidity support can conflict with inflation and policy-rate pressure"
    elif role in {"rates", "fx"}:
        asset["topDriver"] = "Policy rate / liquidity / macro data"
        asset["mainConflict"] = "Policy-rate pressure and liquidity conditions can point in different directions"


def main() -> int:
    if not FED_PATH.exists():
        raise SystemExit("missing data/normalized/fed_macro.json; run fetch_fed_macro.py first")
    data = load_json(DATA_PATH)
    fed = load_json(FED_PATH)
    applied = 0
    for asset in data.get("assets", []):
        update_asset(asset, fed)
        if any(str(f.get("source", "")).startswith("Federal Reserve / FRED") for f in asset.get("factors", [])):
            applied += 1
    data["schema_version"] = "0.28"
    data["notice"] = "Macro Regime Scanner v0.28 public-source data contract. Federal Reserve/FRED liquidity lane added to the v0.27 BEA live baseline. Price-derived lanes remain excluded."
    data["data_mode"] = "public-source-treasury-cot-eia-usda-bls-bea-fed"
    status = data.setdefault("source_status", {})
    status["FED_FRED_SELECTED"] = {
        "status": "live",
        "latest_date": fed.get("latestDate") or "unknown",
        "note": f"Federal Reserve/FRED policy and liquidity lane applied to {applied} assets. Uses public FRED CSV series for EFFR, WALCL, reserves, RRP, and TGA; no API key required in v0.28.",
    }
    write_json(DATA_PATH, data)
    print(f"Applied Federal Reserve/FRED liquidity lane to {applied} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
