#!/usr/bin/env python3
"""Build the Edgefield Growth / Inflation Regime.

v0.50.5 rules:
- No price is used.
- Four regimes only: Goldilocks, Reflation, Stagflation, Deflation.
- Growth and inflation scores are real signed axis tallies from normalized
  public-source macro observations.
- The regime label is derived directly from the two score signs.
- No confidence score, no blend states, no transition language.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NORM_DIR = ROOT / "data" / "normalized"
OUT_PATH = ROOT / "data" / "macro_quad_snapshot.json"

STATE_COPY = {
    "Goldilocks": {
        "subtitle": "Growth positive / Inflation negative",
        "simpleRead": "Growth evidence is supportive while inflation pressure is easing.",
    },
    "Reflation": {
        "subtitle": "Growth positive / Inflation positive",
        "simpleRead": "Growth evidence is supportive while inflation pressure is elevated.",
    },
    "Stagflation": {
        "subtitle": "Growth negative / Inflation positive",
        "simpleRead": "Growth evidence is weakening while inflation pressure remains elevated.",
    },
    "Deflation": {
        "subtitle": "Growth negative / Inflation negative",
        "simpleRead": "Growth evidence is weakening while inflation pressure is easing.",
    },
}

# These are official/public-source normalized observations already produced by
# the existing refresh pipeline. Scores are interpreted as macro-axis pressure,
# not as asset reactions. Example: CPI is inflation pressure; it should not be
# canceled because it hurts one asset and helps another.
SOURCE_FILES = {
    "bls": "bls_macro.json",
    "bea": "bea_macro.json",
    "census": "census_macro.json",
    "fed": "fed_macro.json",
    "financial_stress": "financial_stress.json",
    "treasury": "treasury_yields.json",
    "eia": "eia_energy.json",
    "usda": "usda_agriculture.json",
    "noaa": "noaa_weather.json",
}

INFLATION_KEYS = (
    "cpi", "core", "pce", "ppi", "inflation", "wage", "earnings",
    "yield", "rate", "policy", "energy", "crude", "gasoline",
    "distillate", "natural gas", "crop", "weather", "drought", "usda",
)
GROWTH_KEYS = (
    "gdp", "growth", "retail", "consumer", "labor", "payroll",
    "unemployment", "claims", "income", "spending", "durable", "housing",
    "census", "credit", "spread", "stress", "financial", "liquidity",
    "reserve", "assets", "demand", "product supplied",
)

PRIMARY_GROWTH = (
    "gdp", "retail", "payroll", "unemployment", "labor", "credit", "stress",
    "liquidity", "reserve", "durable", "housing",
)
PRIMARY_INFLATION = (
    "cpi", "pce", "ppi", "inflation", "yield", "rate", "policy", "energy",
    "crude", "gasoline", "wage", "crop", "drought",
)


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def text_blob(*parts: Any) -> str:
    return " ".join(str(p or "").lower() for p in parts)


def score_value(obs: dict[str, Any]) -> float | None:
    value = obs.get("score")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def observation_label(source: str, key: str, obs: dict[str, Any]) -> str:
    return str(obs.get("label") or obs.get("input") or obs.get("name") or key or source)


def axis_for_observation(source: str, key: str, obs: dict[str, Any]) -> str | None:
    kind = str(obs.get("kind") or "").lower()
    label = observation_label(source, key, obs).lower()
    blob = text_blob(source, key, kind, label, obs.get("interpretation"), obs.get("status"))

    if source == "bls":
        if "payroll" in blob or "unemployment" in blob or kind in {"labor", "employment"}:
            return "growth"
        if any(k in blob for k in ("cpi", "ppi", "inflation", "wage", "earnings", "core")):
            return "inflation"
    if source == "bea":
        if kind == "growth":
            return "growth"
        if kind == "inflation":
            return "inflation"
    if source == "census":
        if kind in {"consumer_demand", "housing_activity", "business_investment", "trade_balance", "inventory_cycle"}:
            return "growth"
    if source == "fed":
        if kind == "policy_rate":
            return "inflation"
        if kind in {"liquidity_supply", "liquidity_drain"}:
            return "growth"
    if source == "financial_stress":
        return "growth"
    if source == "treasury":
        return "inflation"
    if source in {"eia", "usda", "noaa"}:
        return "inflation"

    if any(k in blob for k in INFLATION_KEYS):
        return "inflation"
    if any(k in blob for k in GROWTH_KEYS):
        return "growth"
    return None


def observation_weight(axis: str, source: str, key: str, obs: dict[str, Any]) -> int:
    kind = str(obs.get("kind") or "").lower()
    label = observation_label(source, key, obs).lower()
    blob = text_blob(source, key, kind, label)
    primary = PRIMARY_GROWTH if axis == "growth" else PRIMARY_INFLATION
    if any(term in blob for term in primary):
        return 2
    return 1


def add_driver(drivers: list[dict[str, Any]], source: str, key: str, obs: dict[str, Any]) -> None:
    val = score_value(obs)
    if val is None or abs(val) < 0.001:
        return
    axis = axis_for_observation(source, key, obs)
    if axis not in {"growth", "inflation"}:
        return
    weight = observation_weight(axis, source, key, obs)
    contribution = int(max(-2, min(2, round(val)))) * weight
    if contribution == 0:
        return
    drivers.append({
        "axis": axis,
        "source": source,
        "key": key,
        "label": observation_label(source, key, obs),
        "score": int(max(-2, min(2, round(val)))),
        "weight": weight,
        "contribution": contribution,
    })


def iter_observations(source: str, data: Any):
    if not isinstance(data, dict):
        return
    observations = data.get("observations")
    if isinstance(observations, dict):
        for key, obs in observations.items():
            if isinstance(obs, dict):
                yield str(key), obs
        return
    # Treasury may not use the observations wrapper in older builds; scan shallow dicts.
    for key, value in data.items():
        if isinstance(value, dict) and "score" in value:
            yield str(key), value


def collect_drivers() -> list[dict[str, Any]]:
    drivers: list[dict[str, Any]] = []
    for source, filename in SOURCE_FILES.items():
        data = load_json(NORM_DIR / filename)
        if data is None:
            continue
        for key, obs in iter_observations(source, data) or []:
            add_driver(drivers, source, key, obs)
    return drivers


def resolve_axis(drivers: list[dict[str, Any]], axis: str) -> dict[str, Any]:
    axis_drivers = [d for d in drivers if d["axis"] == axis]
    raw_score = sum(int(d["contribution"]) for d in axis_drivers)
    positive_count = sum(1 for d in axis_drivers if d["contribution"] > 0)
    negative_count = sum(1 for d in axis_drivers if d["contribution"] < 0)

    score = raw_score
    if score == 0 and axis_drivers:
        # Resolve exact cancellation with the strongest actual macro observation.
        strongest = max(axis_drivers, key=lambda d: abs(int(d["contribution"])))
        score = 1 if strongest["contribution"] > 0 else -1

    if score == 0:
        # No usable official/public-source axis observations were found. This is
        # a pipeline problem, not a market regime. Validation will fail so the
        # app does not publish positive/zero nonsense.
        label = "unavailable"
    else:
        label = "positive" if score > 0 else "negative"

    return {
        "score": int(score),
        "label": label,
        "factorTally": {
            "positive": positive_count,
            "negative": negative_count,
            "net": int(score),
        },
    }


def classify(growth_label: str, inflation_label: str) -> str:
    if growth_label == "positive" and inflation_label == "negative":
        return "Goldilocks"
    if growth_label == "positive" and inflation_label == "positive":
        return "Reflation"
    if growth_label == "negative" and inflation_label == "positive":
        return "Stagflation"
    if growth_label == "negative" and inflation_label == "negative":
        return "Deflation"
    raise SystemExit("Macro quad axis unavailable: refresh normalized public-source data before building the regime map.")


def main() -> None:
    drivers = collect_drivers()
    growth = resolve_axis(drivers, "growth")
    inflation = resolve_axis(drivers, "inflation")
    state = classify(growth["label"], inflation["label"])
    copy = STATE_COPY[state]
    output = {
        "schemaVersion": "macro_quad_snapshot_v1_5",
        "version": "v0.50.5-real-quad-tally-fix",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "No-price four-quad regime map. Growth and inflation scores are signed tallies from normalized official/public-source macro observations. Regime labels are derived directly from score signs.",
        "currentState": state,
        "subtitle": copy["subtitle"],
        "simpleRead": copy["simpleRead"],
        "growth": growth,
        "inflation": inflation,
        "states": [{"name": name, **STATE_COPY[name]} for name in ["Goldilocks", "Reflation", "Stagflation", "Deflation"]],
        "limits": ["Uses current public-source pressure only; no price data is used."],
    }
    OUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}: {state} ({copy['subtitle']})")


if __name__ == "__main__":
    main()
