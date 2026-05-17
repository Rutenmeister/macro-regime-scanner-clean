#!/usr/bin/env python3
"""Apply normalized EIA energy fundamentals to Macro Regime Scanner JSON.

v0.22 adds EIA as a physical energy/fundamental public-source lane. It avoids
prices, price trend, momentum, moving averages, and price-derived spreads. The
lane is intentionally explicit about relevance: EIA energy data is primary for
energy commodities, contextual for the broad commodity basket, and low/indirect
for non-energy commodities unless a biofuel/input-cost channel exists.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
EIA_PATH = ROOT / "data" / "normalized" / "eia_energy.json"
SOURCE_NAME = "U.S. Energy Information Administration open data/API"

EIA_FACTOR_NAMES = {
    "EIA crude inventories",
    "EIA Cushing inventories",
    "EIA gasoline inventories",
    "EIA distillate inventories",
    "EIA natural gas storage",
    "EIA petroleum inventory balance",
    "EIA energy balance context",
    "Product supplied / demand",
    "Natural gas storage",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def fmt_value(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        return f"{value:,.1f}"
    return str(value)


def status_from_score(score: int | None) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure", None: "Missing"}.get(score, "Neutral")


def obs(eia: dict[str, Any], key: str) -> dict[str, Any]:
    return eia.get("observations", {}).get(key, {}) if isinstance(eia, dict) else {}


def derived_from(o: dict[str, Any]) -> str:
    if not o:
        return "EIA observation missing from normalized energy lane."
    base = (
        f"{o.get('label')} ({o.get('series')}) latest {fmt_value(o.get('latest_value'))} {o.get('unit')} "
        f"on {o.get('latest_period')}; previous {fmt_value(o.get('previous_value'))} {o.get('unit')} "
        f"on {o.get('previous_period')}."
    )
    if o.get("weekly_change") is not None:
        base += f" Weekly change: {fmt_value(o.get('weekly_change'))} {o.get('unit')}."
    if o.get("pct_vs_5yr_avg") is not None:
        base += f" Storage versus five-year average: {fmt_value(o.get('pct_vs_5yr_avg'))}%."
    return base


def factor(name: str, relevance: str, score: int | None, status: str, derived: str, effect: str) -> dict[str, Any]:
    return {
        "group": "EIA Energy Fundamentals",
        "name": name,
        "relevance": relevance,
        "score": score,
        "status": status,
        "derived": derived,
        "effect": effect,
        "source": SOURCE_NAME,
        "freshness": "Fresh" if score is not None else "Missing",
    }


def inv_factor(name: str, relevance: str, o: dict[str, Any], effect: str, invert_score: bool = False) -> dict[str, Any]:
    raw_score = o.get("score") if o else None
    score = None if raw_score is None else int(raw_score)
    if invert_score and score is not None:
        score = -score
    return factor(name, relevance, score, status_from_score(score), derived_from(o), effect)


def natgas_factor(relevance: str, o: dict[str, Any], effect: str, use_score: bool = True) -> dict[str, Any]:
    raw_score = o.get("score") if o else None
    score = int(raw_score) if use_score and raw_score is not None else 0
    status = status_from_score(score) if use_score else "Low relevance"
    return factor("EIA natural gas storage", relevance, score, status, derived_from(o), effect)


def petroleum_balance_factor(asset: dict[str, Any], relevance: str, observations: list[dict[str, Any]], effect: str) -> dict[str, Any]:
    scores = [int(o.get("score", 0) or 0) for o in observations if o]
    score = 0 if not scores else max(-2, min(2, round(sum(scores) / len(scores))))
    derived = " | ".join(derived_from(o) for o in observations if o) or "EIA petroleum observations missing."
    return factor("EIA petroleum inventory balance", relevance, score, status_from_score(score), derived, effect)


def update_energy_asset(asset: dict[str, Any], eia: dict[str, Any]) -> list[dict[str, Any]]:
    aid = asset.get("id")
    crude = obs(eia, "CRUDE_STOCKS")
    cushing = obs(eia, "CUSHING_STOCKS")
    gasoline = obs(eia, "GASOLINE_STOCKS")
    dist = obs(eia, "DISTILLATE_STOCKS")
    ngs = obs(eia, "NATGAS_STORAGE")

    if aid == "WTI":
        return [
            inv_factor("EIA crude inventories", "Primary", crude, "Direct effect: crude inventory draws usually support WTI because visible U.S. supply tightens; builds usually pressure WTI."),
            inv_factor("EIA Cushing inventories", "Primary", cushing, "Direct effect: Cushing stocks matter strongly for WTI because Cushing is the delivery/storage hub tied to the benchmark."),
            inv_factor("EIA gasoline inventories", "Secondary", gasoline, "Secondary effect: gasoline draws can support crude by implying stronger refinery/product demand; builds can weaken crude demand context."),
            inv_factor("EIA distillate inventories", "Secondary", dist, "Secondary effect: distillate draws can support crude through broader product tightness; builds can pressure the energy complex."),
            natgas_factor("Low relevance", ngs, "Low direct effect: natural gas storage does not normally drive WTI, but it can affect the broader energy/inflation backdrop.", use_score=False),
        ]
    if aid == "BRENT":
        return [
            inv_factor("EIA crude inventories", "Secondary", crude, "Secondary effect: U.S. crude draws can support Brent as global oil-balance context, but Brent is less directly tied to U.S. stocks than WTI."),
            inv_factor("EIA Cushing inventories", "Low relevance", cushing, "Low direct effect: Cushing is WTI-specific. It affects Brent mostly through U.S. export/arbitrage and global crude-balance context."),
            inv_factor("EIA gasoline inventories", "Contextual", gasoline, "Contextual effect: U.S. gasoline draws can support oil demand sentiment; builds can weaken product-demand context."),
            inv_factor("EIA distillate inventories", "Contextual", dist, "Contextual effect: distillate tightness supports the global oil-products backdrop; builds reduce that support."),
            natgas_factor("Low relevance", ngs, "Low direct effect: natural gas storage is not a direct Brent input except through broad energy/inflation conditions.", use_score=False),
        ]
    if aid == "GASOLINE":
        return [
            inv_factor("EIA gasoline inventories", "Primary", gasoline, "Direct effect: gasoline inventory draws usually support gasoline because product supply tightens; builds usually pressure gasoline."),
            inv_factor("EIA crude inventories", "Secondary", crude, "Secondary effect: crude draws can support input-cost and energy-complex context, but gasoline stocks are the more direct input."),
            inv_factor("EIA Cushing inventories", "Low relevance", cushing, "Low direct effect: Cushing is crude-specific; it matters for gasoline only through crude-market context."),
            inv_factor("EIA distillate inventories", "Contextual", dist, "Contextual effect: distillate stocks help read overall refined-product tightness but are not the main gasoline driver."),
        ]
    if aid == "HEATING":
        return [
            inv_factor("EIA distillate inventories", "Primary", dist, "Direct effect: distillate inventory draws usually support heating oil/distillates because product supply tightens; builds usually pressure it."),
            inv_factor("EIA crude inventories", "Secondary", crude, "Secondary effect: crude draws can support the broader refinery/input-cost backdrop, but distillate stocks are more direct."),
            inv_factor("EIA gasoline inventories", "Contextual", gasoline, "Contextual effect: gasoline stocks help read product-market balance but are not the main distillate driver."),
            natgas_factor("Contextual", ngs, "Contextual effect: natural gas storage can affect winter heating-energy sentiment, but distillate inventories remain the direct input."),
        ]
    if aid == "NG":
        return [
            natgas_factor("Primary", ngs, "Direct effect: lower-than-normal gas storage supports natural gas because the supply cushion is tighter; above-normal storage pressures natural gas."),
            inv_factor("EIA crude inventories", "Low relevance", crude, "Low direct effect: crude inventories do not normally drive natural gas. They matter only through broad energy/inflation context."),
            inv_factor("EIA gasoline inventories", "Low relevance", gasoline, "Low direct effect: gasoline stocks do not normally drive natural gas except through broad energy-complex context."),
            inv_factor("EIA distillate inventories", "Contextual", dist, "Contextual effect: distillate tightness can matter during winter heating stress, but gas storage is the primary input."),
        ]
    return []


def update_non_energy_commodity(asset: dict[str, Any], eia: dict[str, Any]) -> list[dict[str, Any]]:
    aid = asset.get("id")
    crude = obs(eia, "CRUDE_STOCKS")
    gasoline = obs(eia, "GASOLINE_STOCKS")
    dist = obs(eia, "DISTILLATE_STOCKS")
    ngs = obs(eia, "NATGAS_STORAGE")

    if aid == "BCOM":
        return [
            petroleum_balance_factor(asset, "Secondary", [crude, gasoline, dist], "Secondary effect: EIA petroleum draws support the broad commodity basket through energy tightness and inflation pressure; builds reduce that support."),
            natgas_factor("Contextual", ngs, "Contextual effect: natural gas storage affects the energy component of a broad commodity read, but it is not the whole basket."),
        ]
    if aid in {"GOLD", "SILVER"}:
        return [
            petroleum_balance_factor(asset, "Low relevance", [crude, gasoline, dist], f"Low direct effect: EIA petroleum balance does not normally drive {asset.get('name')}. It matters indirectly if energy shocks change inflation expectations, real-yield pressure, or risk sentiment."),
            natgas_factor("Low relevance", ngs, f"Low direct effect: natural gas storage does not normally drive {asset.get('name')}; it only matters through broad inflation or energy-stress channels.", use_score=False),
        ]
    if aid == "COPPER":
        return [
            petroleum_balance_factor(asset, "Contextual", [crude, gasoline, dist], "Contextual effect: energy tightness can raise industrial cost pressure and inflation concerns, but copper is driven more directly by growth, China demand, inventories, and positioning."),
            natgas_factor("Low relevance", ngs, "Low direct effect: natural gas storage only matters to copper through energy-cost and industrial-demand context.", use_score=False),
        ]
    if aid in {"CORN", "SOY", "SUGAR"}:
        return [
            petroleum_balance_factor(asset, "Contextual", [gasoline, crude], f"Contextual effect: fuel-demand and energy-market tightness can affect {asset.get('name')} through biofuel economics, transport costs, and inflation pressure, but crop supply/demand reports are more direct."),
            natgas_factor("Low relevance", ngs, f"Low direct effect: natural gas storage does not normally drive {asset.get('name')} except through fertilizer, energy-cost, or broad inflation channels.", use_score=False),
        ]
    if aid in {"WHEAT", "COFFEE", "COTTON"}:
        return [
            petroleum_balance_factor(asset, "Low relevance", [crude, gasoline, dist], f"Low direct effect: EIA energy data does not normally drive {asset.get('name')}. It matters mainly through transport, input-cost, or broad inflation channels."),
            natgas_factor("Low relevance", ngs, f"Low direct effect: natural gas storage is not a normal driver of {asset.get('name')}; crop/weather/export data matters more.", use_score=False),
        ]
    return []


def update_macro_context(asset: dict[str, Any], eia: dict[str, Any]) -> list[dict[str, Any]]:
    crude = obs(eia, "CRUDE_STOCKS")
    gasoline = obs(eia, "GASOLINE_STOCKS")
    dist = obs(eia, "DISTILLATE_STOCKS")
    aid = asset.get("id")
    if aid == "USDCAD":
        return [petroleum_balance_factor(asset, "Contextual", [crude, gasoline, dist], "Contextual effect: stronger oil/energy fundamentals can support CAD through Canada's commodity linkage; because this pair is USD/CAD, CAD support can pressure the pair.")]
    if aid in {"DXY", "SPX", "NDX", "RUT", "DOW", "BE5Y", "BE10Y", "REALY"}:
        return [petroleum_balance_factor(asset, "Contextual", [crude, gasoline, dist], f"Contextual effect: EIA energy tightness can affect {asset.get('name')} through inflation pressure, rate expectations, and risk appetite. It is not the main direct driver.")]
    return []


def update_asset(asset: dict[str, Any], eia: dict[str, Any]) -> None:
    old = [f for f in asset.setdefault("factors", []) if f.get("name") not in EIA_FACTOR_NAMES and not str(f.get("source", "")).startswith("U.S. Energy Information Administration")]
    if asset.get("assetClass") == "Commodities":
        new = update_energy_asset(asset, eia) or update_non_energy_commodity(asset, eia)
    else:
        new = update_macro_context(asset, eia)
    if new:
        asset["factors"] = old + new
        if asset.get("freshness") == "Sample":
            asset["freshness"] = "Mixed"
        asset["coverage"] = (asset.get("coverage", "") + " | EIA energy fundamentals").strip(" |")
        if asset.get("id") in {"WTI", "BRENT", "NG", "GASOLINE", "HEATING"}:
            asset["topDriver"] = "EIA physical balance / COT"
            asset["mainConflict"] = "Energy fundamentals must be read with COT and macro pressure"
            watch = list(asset.get("watchNext", []))
            for item in ["Next EIA energy release", "Inventory change", "Storage vs 5-year average"]:
                if item not in watch:
                    watch.append(item)
            asset["watchNext"] = watch[:6]


def main() -> int:
    if not EIA_PATH.exists():
        raise SystemExit("missing data/normalized/eia_energy.json; run fetch_eia_energy.py first")
    data = load_json(DATA_PATH)
    eia = load_json(EIA_PATH)
    applied = 0
    for asset in data.get("assets", []):
        before = len(asset.get("factors", []))
        update_asset(asset, eia)
        if len(asset.get("factors", [])) != before or any(str(f.get("source", "")).startswith("U.S. Energy Information Administration") for f in asset.get("factors", [])):
            applied += 1

    data["schema_version"] = "0.22"
    data["notice"] = "Macro Regime Scanner v0.22 public-source data contract. Treasury, CFTC COT, and EIA energy lanes are live/workflow-ready. EIA adds public energy fundamentals with explicit relevance for direct, contextual, low, and indirect asset effects. Price-derived lanes remain excluded."
    data["data_mode"] = "public-source-treasury-cot-eia"
    status = data.setdefault("source_status", {})
    status["EIA_OPEN_DATA"] = {
        "status": "live",
        "latest_date": eia.get("latest_date") or "unknown",
        "note": f"EIA energy fundamentals applied to {applied} assets. Direct for energy commodities; contextual/low relevance for other affected assets.",
    }
    write_json(DATA_PATH, data)
    print(f"Applied EIA energy lane to {applied} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
