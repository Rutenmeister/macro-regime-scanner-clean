#!/usr/bin/env python3
"""Apply normalized credit-spread and financial-stress indicators to Macro Regime Scanner JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
STRESS_PATH = ROOT / "data" / "normalized" / "financial_stress.json"
SOURCE_NAME = "Federal Reserve / FRED credit and financial-stress public data"
SOURCE_STATUS_ID = "FINANCIAL_STRESS_FRED"

FACTOR_NAMES = {
    "High-yield credit spread stress",
    "Investment-grade credit spread stress",
    "BBB credit spread stress",
    "National financial conditions",
    "Adjusted financial conditions",
    "St. Louis financial stress",
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

DISPLAY_MAP = [
    ("HY_OAS", "High-yield credit spread stress"),
    ("IG_OAS", "Investment-grade credit spread stress"),
    ("BBB_OAS", "BBB credit spread stress"),
    ("NFCI", "National financial conditions"),
    ("ANFCI", "Adjusted financial conditions"),
    ("STLFSI4", "St. Louis financial stress"),
]


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


def clamp(score: int | None) -> int | None:
    if score is None:
        return None
    return max(-2, min(2, int(score)))


def status_from_score(score: int | None) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure", None: "Missing"}.get(score, "Neutral")


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
    if aid in INDUSTRIAL:
        return "industrial_commodity"
    if cls == "Commodities":
        return "commodity"
    return "context"


def relevance_for(asset: dict[str, Any], kind: str, key: str) -> str:
    role = asset_role(asset)
    aid = asset.get("id")
    if aid == "HY" and key == "HY_OAS":
        return "Primary"
    if aid == "IG" and key in {"IG_OAS", "BBB_OAS"}:
        return "Primary"
    if aid == "FCI" and kind in {"financial_conditions", "financial_stress"}:
        return "Primary"
    if role in {"equity", "credit"}:
        return "Primary"
    if role in {"rates", "fx", "precious"}:
        return "Secondary"
    if role in {"energy", "industrial_commodity", "commodity"}:
        return "Contextual"
    return "Low relevance"


def score_for_asset(asset: dict[str, Any], raw_score: int | None, kind: str) -> int | None:
    if raw_score is None:
        return None
    score = int(raw_score)
    role = asset_role(asset)
    aid = asset.get("id")

    # Raw score convention from fetcher: positive = easier/lower stress, negative = tighter/higher stress.
    if role in {"equity", "credit", "energy", "industrial_commodity", "commodity"}:
        return clamp(score)
    if role == "rates":
        # Credit/financial stress usually lowers growth/risk appetite and can reduce upward yield pressure.
        return clamp(score if score > 0 else -1 if score < 0 else 0)
    if aid == "DXY" or aid in FX_USD_BASE:
        # Dollar can be supported by funding stress/scarcity; easier conditions can reduce that support.
        return clamp(-score)
    if aid in FX_USD_QUOTE:
        return clamp(score)
    if role == "precious":
        # Stress can support defensive precious-metal demand, but dollar/liquidity channels conflict; keep moderate.
        if score < 0:
            return 1
        if score > 0:
            return -1
        return 0
    if role == "crop":
        return 0
    return 0


def derived(o: dict[str, Any]) -> str:
    if not o:
        return "Credit/financial stress observation missing from normalized lane."
    suffix = "%" if o.get("unit") == "percent" else f" {o.get('unit', '')}".rstrip()
    change_suffix = " pts" if o.get("unit") in {"percent", "index"} else f" {o.get('unit', '')}".rstrip()
    return (
        f"{o.get('label')} ({o.get('seriesId')}) latest {fmt(o.get('latestValue'), suffix)} "
        f"for {o.get('period')}; previous {fmt(o.get('previousValue'), suffix)} "
        f"for {o.get('previousPeriod')}; change {fmt(o.get('change'), change_suffix)}. "
        f"Raw lane score uses easier/lower-stress conditions as positive and tighter/higher-stress conditions as negative."
    )


def effect_for(asset: dict[str, Any], o: dict[str, Any], label: str) -> str:
    name = asset.get("name")
    aid = asset.get("id")
    role = asset_role(asset)
    kind = o.get("kind", "context") if o else "context"
    if kind == "credit_spread":
        if aid in {"HY", "IG", "FCI"}:
            return f"Primary effect: Wider credit spreads signal tighter credit and higher stress for {name}; narrower spreads signal easier credit conditions."
        if role == "equity":
            return f"Primary effect: Wider credit spreads usually pressure {name} through risk appetite, financing-cost, and earnings-stress channels; tighter spreads are supportive."
        if role == "rates":
            return f"Secondary effect: Credit-spread stress can reduce growth expectations and lower upward yield pressure for {name}, even while risk premiums rise."
        if aid == "DXY" or aid in FX_USD_BASE:
            return "Secondary effect: Credit stress can support USD through funding/safe-haven demand; easing credit conditions can reduce that support."
        if aid in FX_USD_QUOTE:
            return f"Secondary effect: Credit stress can support USD and pressure {asset.get('symbol')}; easier credit conditions can support the pair."
        if role == "precious":
            return f"Secondary/mixed effect: Credit stress can support defensive demand for {name}, but dollar and real-yield channels may offset."
        return f"Contextual effect: Credit-spread stress affects {name} indirectly through growth, financing conditions, USD funding, and risk appetite."
    if kind in {"financial_conditions", "financial_stress"}:
        if aid == "FCI":
            return f"Primary effect: Tighter financial conditions or higher stress directly pressure {name}; easier conditions support it."
        if role == "equity":
            return f"Primary effect: Tighter financial conditions usually pressure {name}; easier conditions support risk appetite and financing conditions."
        if role == "credit":
            return f"Primary effect: Higher financial stress pressures {name}; easier conditions reduce stress risk."
        if role == "rates":
            return f"Secondary effect: Financial stress can reduce growth/rate pressure for {name}; easier conditions can support risk-taking and rate pressure."
        if aid == "DXY" or aid in FX_USD_BASE:
            return "Secondary effect: Tighter financial conditions can support USD through liquidity and safe-haven channels; easier conditions can reduce that support."
        if aid in FX_USD_QUOTE:
            return f"Secondary effect: Tighter U.S. financial conditions can support USD and pressure {asset.get('symbol')}; easier conditions can support the pair."
        if role == "precious":
            return f"Secondary/mixed effect: Financial stress can support defensive demand for {name}, but USD strength and liquidity pressure can conflict."
        return f"Contextual effect: Financial-stress indexes affect {name} through broad risk appetite, funding, credit, and dollar-liquidity channels."
    return f"Contextual effect: {label} is credit/financial-condition context for {name}."


def make_factor(asset: dict[str, Any], o: dict[str, Any], display_name: str) -> dict[str, Any]:
    kind = o.get("kind", "context") if o else "context"
    key = o.get("key", "") if o else ""
    raw_score = o.get("score") if o else None
    score = score_for_asset(asset, raw_score, kind)
    return {
        "group": "Credit / Financial Stress",
        "name": display_name,
        "relevance": relevance_for(asset, kind, key),
        "score": score,
        "status": status_from_score(score),
        "derived": derived(o),
        "effect": effect_for(asset, o, display_name),
        "source": SOURCE_NAME,
        "freshness": "Fresh" if score is not None else "Missing",
    }


def update_asset(asset: dict[str, Any], stress: dict[str, Any]) -> None:
    old = [
        f for f in asset.setdefault("factors", [])
        if f.get("name") not in FACTOR_NAMES
        and not str(f.get("source", "")).startswith("Federal Reserve / FRED credit")
    ]
    observations = stress.get("observations", {}) if isinstance(stress, dict) else {}
    new: list[dict[str, Any]] = []
    for key, label in DISPLAY_MAP:
        o = observations.get(key)
        if o:
            new.append(make_factor(asset, o, label))
    asset["factors"] = old + new
    if asset.get("freshness") == "Sample":
        asset["freshness"] = "Mixed"
    asset["coverage"] = (asset.get("coverage", "") + " | Credit/financial stress").strip(" |")
    watch = list(asset.get("watchNext", []))
    for item in ["HY OAS", "IG OAS", "NFCI", "financial stress"]:
        if item not in watch:
            watch.append(item)
    asset["watchNext"] = watch[:6]
    role = asset_role(asset)
    if role in {"equity", "credit"}:
        asset["topDriver"] = "Credit stress / liquidity / rates / growth"
        asset["mainConflict"] = "Credit stress can conflict with growth and liquidity support"
    elif role in {"rates", "fx", "precious"}:
        asset["topDriver"] = "Rates / credit stress / dollar liquidity"
        asset["mainConflict"] = "Credit stress can pull safe-haven, dollar, and rate channels in different directions"


def main() -> int:
    if not STRESS_PATH.exists():
        raise SystemExit("missing data/normalized/financial_stress.json; run fetch_financial_stress.py first")
    data = load_json(DATA_PATH)
    stress = load_json(STRESS_PATH)
    applied = 0
    for asset in data.get("assets", []):
        update_asset(asset, stress)
        if any(str(f.get("source", "")).startswith("Federal Reserve / FRED credit") for f in asset.get("factors", [])):
            applied += 1
    data["schema_version"] = "0.24"
    data["notice"] = "Macro Regime Scanner v0.30 public-source data contract. Credit and financial-stress lane added to the v0.29 Census live baseline. Price-derived lanes remain excluded."
    data["data_mode"] = "public-source-treasury-cot-eia-usda-bls-bea-fed-census-credit-stress"
    status = data.setdefault("source_status", {})
    status[SOURCE_STATUS_ID] = {
        "status": "live",
        "latest_date": stress.get("latestDate") or "unknown",
        "note": f"Credit and financial-stress lane applied to {applied} assets. Uses public FRED series for HY OAS, IG OAS, BBB OAS, NFCI, ANFCI, and STLFSI4; no API key required in v0.30.",
    }
    write_json(DATA_PATH, data)
    print(f"Applied credit/financial stress lane to {applied} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
