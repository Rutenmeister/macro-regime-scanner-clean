#!/usr/bin/env python3
"""Apply normalized CFTC COT positioning data to Macro Regime Scanner JSON.

v0.20 introduced COT interpretation. v0.22 keeps COT interpretation and refresh-all workflow support, splitting COT from a single directional positioning row into several
clearer rows:
  - Spec direction: trend participation
  - Spec weekly change: participation change
  - Crowding risk: extreme spec positioning warning
  - Commercial/hedger extreme: commodity hedger context when available
  - COT conflict: when specs and commercials strongly disagree

This keeps COT honest: large specs can confirm trend participation, but extreme
spec positions can also become crowded unwind risk. Commercials are treated as
hedging/value context, especially at extremes, not as an automatic signal.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
COT_PATH = ROOT / "data" / "normalized" / "cot_positioning.json"
SOURCE_NAME = "CFTC Commitments of Traders public reports"

COT_FACTOR_NAMES = {
    "COT / futures positioning",
    "COT spec direction",
    "COT spec weekly change",
    "COT crowding risk",
    "COT commercial / hedger extreme",
    "COT spec-commercial conflict",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def fmt_int(value: Any) -> str:
    if value is None:
        return "missing"
    return f"{int(value):,}"


def fmt_pct(value: Any) -> str:
    if value is None:
        return "missing"
    return f"{float(value):.2f}%"


def direction_word(score: int) -> str:
    if score > 0:
        return "supportive"
    if score < 0:
        return "pressuring"
    return "neutral"


def net_text(value: Any) -> str:
    val = value or 0
    if val > 0:
        return "net long"
    if val < 0:
        return "net short"
    return "near neutral"


def asset_direction_context(asset: dict[str, Any], obs: dict[str, Any]) -> str:
    group = obs.get("trader_group", "speculative traders")
    net = net_text(obs.get("net"))
    effective_pct = fmt_pct(obs.get("effective_net_pct_of_open_interest"))
    if obs.get("invert_for_asset") and asset.get("assetClass") == "Rates":
        return (
            f"{group} are {net} in the related Treasury futures contract; after yield inversion this is {direction_word(obs.get('score', 0))} for {asset.get('name')}. "
            f"Effective positioning equals {effective_pct} of open interest. Long Treasury futures usually imply bond-price support and lower-yield pressure."
        )
    if obs.get("invert_for_asset") and asset.get("assetClass") == "FX":
        return (
            f"{group} are {net} in the quote-currency futures contract; after USD-base inversion this is {direction_word(obs.get('score', 0))} for {asset.get('symbol')}. "
            f"Effective positioning equals {effective_pct} of open interest. Stronger quote-currency positioning usually pressures a USD-base pair."
        )
    if asset.get("assetClass") == "FX":
        return (
            f"{group} are {net} in the related currency futures contract, which is {direction_word(obs.get('score', 0))} for this FX read. "
            f"Effective positioning equals {effective_pct} of open interest. This reflects speculative participation, not a timing signal."
        )
    if asset.get("assetClass") == "Commodities":
        return (
            f"{group} are {net} in the related commodity futures contract, which is {direction_word(obs.get('score', 0))} for this commodity. "
            f"Effective positioning equals {effective_pct} of open interest. This shows trend participation, but extremes can become unwind risk."
        )
    if asset.get("assetClass") == "Equity Indices":
        return (
            f"{group} are {net} in the related equity-index futures contract, which is {direction_word(obs.get('score', 0))} for risk appetite. "
            f"Effective positioning equals {effective_pct} of open interest. Net long exposure supports participation; net short exposure reflects pressure or hedging."
        )
    return (
        f"{group} are {net}; effective positioning equals {effective_pct} of open interest. "
        "This is positioning context, not price confirmation."
    )


def derived_base(obs: dict[str, Any]) -> str:
    return (
        f"{obs.get('report_name')} for {obs.get('cftc_market')} on {obs.get('report_date')}: "
        f"{obs.get('trader_group')} long {fmt_int(obs.get('long'))}, short {fmt_int(obs.get('short'))}, "
        f"net {fmt_int(obs.get('net'))} ({fmt_pct(obs.get('net_pct_of_open_interest'))} of open interest), "
        f"effective for this asset {fmt_pct(obs.get('effective_net_pct_of_open_interest'))}."
    )


def cot_factor(group: str, name: str, relevance: str, score: int, status: str, derived: str, effect: str) -> dict[str, Any]:
    return {
        "group": group,
        "name": name,
        "relevance": relevance,
        "score": score,
        "status": status,
        "derived": derived,
        "effect": effect,
        "source": SOURCE_NAME,
        "freshness": "Fresh",
    }


def weekly_factor(asset: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any]:
    score = int(obs.get("weekly_change_score", 0) or 0)
    status = obs.get("weekly_change_status", "Neutral")
    change = fmt_int(obs.get("weekly_net_change"))
    eff_change = fmt_pct(obs.get("effective_weekly_change_pct_of_open_interest"))
    return cot_factor(
        "Positioning",
        "COT spec weekly change",
        "Secondary",
        score,
        status,
        f"Weekly net change {change}; effective weekly change {eff_change} of open interest.",
        (
            f"Weekly change shows whether speculative participation is getting stronger or weaker for {asset.get('name')}. "
            "Adding exposure in the supportive direction strengthens the positioning read; reducing exposure weakens it."
        ),
    )


def crowding_factor(asset: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any]:
    score = int(obs.get("crowding_score", 0) or 0)
    status = obs.get("crowding_status", "Neutral")
    percentile = obs.get("spec_percentile_1y")
    return cot_factor(
        "Positioning",
        "COT crowding risk",
        "Contextual",
        score,
        status,
        f"Spec effective positioning percentile over recent lookback: {fmt_pct(percentile)}.",
        obs.get("crowding_effect") or (
            f"Crowding risk measures whether speculative positioning in {asset.get('name')} is stretched enough to become fragile. "
            "Normal positioning is only context; extreme positioning can create unwind or short-covering risk."
        ),
    )


def commercial_factor(asset: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any] | None:
    if obs.get("commercial_net") is None:
        return None
    score = int(obs.get("commercial_extreme_score", 0) or 0)
    status = obs.get("commercial_extreme_status", "Neutral")
    pct = fmt_pct(obs.get("commercial_net_pct_of_open_interest"))
    percentile = fmt_pct(obs.get("commercial_percentile_1y"))
    return cot_factor(
        "Positioning",
        "COT commercial / hedger extreme",
        "Contextual",
        score,
        status,
        (
            f"{obs.get('commercial_group')} net {fmt_int(obs.get('commercial_net'))} "
            f"({pct} of open interest); recent percentile {percentile}."
        ),
        (
            "Commercial/hedger positioning is not an automatic buy/sell signal. "
            f"For {asset.get('name')}, extreme commercial long exposure can suggest value/support context, while extreme commercial short exposure can warn that speculative long exposure may be crowded."
        ),
    )


def conflict_factor(asset: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any] | None:
    if obs.get("commercial_net") is None:
        return None
    conflict = bool(obs.get("cot_conflict"))
    return cot_factor(
        "Positioning",
        "COT spec-commercial conflict",
        "Contextual",
        0,
        "Neutral",
        (
            f"Spec effective positioning {fmt_pct(obs.get('effective_net_pct_of_open_interest'))}; "
            f"commercial/hedger positioning {fmt_pct(obs.get('commercial_net_pct_of_open_interest'))}."
        ),
        (
            f"COT conflict is {'present' if conflict else 'not elevated'} for {asset.get('name')}. "
            "When specs and commercials are strongly opposed, the directional read may still work, but reversal or unwind risk deserves more attention."
        ),
    )


def update_cot_factors(asset: dict[str, Any], obs: dict[str, Any]) -> None:
    old_factors = [f for f in asset.setdefault("factors", []) if f.get("name") not in COT_FACTOR_NAMES]
    new_factors = [
        cot_factor(
            "Positioning",
            "COT spec direction",
            "Secondary",
            int(obs.get("score", 0) or 0),
            obs.get("status", "Neutral"),
            derived_base(obs),
            asset_direction_context(asset, obs),
        ),
        weekly_factor(asset, obs),
        crowding_factor(asset, obs),
    ]
    comm = commercial_factor(asset, obs)
    if comm:
        new_factors.append(comm)
    conflict = conflict_factor(asset, obs)
    if conflict:
        new_factors.append(conflict)
    asset["factors"] = old_factors + new_factors


def update_asset_summary(asset: dict[str, Any], obs: dict[str, Any]) -> None:
    cot_status = obs.get("status", "Neutral")
    asset["freshness"] = "Fresh" if asset.get("freshness") == "Sample" else asset.get("freshness", "Fresh")
    asset["coverage"] = f"COT: {obs.get('trader_group')} / {obs.get('report_date')}"
    if "Treasury" not in str(asset.get("topDriver")):
        asset["topDriver"] = "COT spec direction"
    if cot_status in {"Strong support", "Support"}:
        asset["mainConflict"] = "Spec positioning supports participation, but crowding risk must be checked"
    elif cot_status in {"Strong pressure", "Pressure"}:
        asset["mainConflict"] = "Spec positioning pressures the asset, but short-covering risk must be checked"
    else:
        asset["mainConflict"] = asset.get("mainConflict", "Other public-source lanes not connected yet")
    watch = list(asset.get("watchNext", []))
    for item in ["Next CFTC COT release", "Spec direction", "Crowding risk", "Commercial/hedger extremes"]:
        if item not in watch:
            watch.append(item)
    asset["watchNext"] = watch[:6]


def main() -> int:
    if not COT_PATH.exists():
        raise SystemExit("missing data/normalized/cot_positioning.json; run fetch_cftc_cot.py first")
    data = load_json(DATA_PATH)
    cot = load_json(COT_PATH)
    observations = cot.get("observations", {}) if isinstance(cot, dict) else {}
    if not observations:
        raise SystemExit("COT normalized file contains no observations")
    applied = 0
    for asset in data.get("assets", []):
        obs = observations.get(asset.get("id"))
        if not obs:
            continue
        update_cot_factors(asset, obs)
        update_asset_summary(asset, obs)
        applied += 1
    data["schema_version"] = "0.22"
    data["notice"] = "Macro Regime Scanner v0.22 public-source data contract. Treasury, CFTC COT, and EIA energy lanes are live/workflow-ready. COT separates spec direction, weekly change, crowding risk, commercial/hedger context, and conflict. Price-derived lanes remain excluded."
    status = data.setdefault("source_status", {})
    status["CFTC_COT"] = {
        "status": "live",
        "latest_date": cot.get("latest_report_date") or "unknown",
        "note": f"CFTC COT refreshed for {applied} mapped assets. Interpretation splits directional participation from crowding/contrarian risk.",
    }
    write_json(DATA_PATH, data)
    print(f"Applied upgraded CFTC COT interpretation to {applied} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
