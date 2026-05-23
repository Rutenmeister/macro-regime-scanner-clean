#!/usr/bin/env python3
"""Fetch CFTC Commitments of Traders public data.

This scaffold uses CFTC's public Socrata endpoints only. It intentionally avoids
price data, price trend, momentum, moving averages, or other price-derived
inputs. It produces a compact normalized positioning file that the scanner can
map into each asset's COT / futures positioning row.

Outputs:
  data/raw/cftc/cftc_tff_recent.json
  data/raw/cftc/cftc_disaggregated_recent.json
  data/normalized/cot_positioning.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "cftc"
NORM_DIR = ROOT / "data" / "normalized"
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)

TFF_ENDPOINT = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
DISAGG_ENDPOINT = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"

# Financial futures use the Traders in Financial Futures (TFF) report. Commodity
# futures use Disaggregated Futures Only. Patterns are intentionally broad but
# conservative; the matcher chooses the highest-open-interest matching contract
# if multiple rows match.
CONTRACT_MAP: dict[str, dict[str, Any]] = {
    # FX / financial futures. Inversion means the futures contract represents the quote currency in a USD-base pair.
    "EURUSD": {"endpoint": "tff", "pattern": "EURO FX", "group": "leveraged", "invert": False},
    "GBPUSD": {"endpoint": "tff", "pattern": "BRITISH POUND", "group": "leveraged", "invert": False},
    "USDJPY": {"endpoint": "tff", "pattern": "JAPANESE YEN", "group": "leveraged", "invert": True},
    "USDCHF": {"endpoint": "tff", "pattern": "SWISS FRANC", "group": "leveraged", "invert": True},
    "USDCAD": {"endpoint": "tff", "pattern": "CANADIAN DOLLAR", "group": "leveraged", "invert": True},
    "AUDUSD": {"endpoint": "tff", "pattern": "AUSTRALIAN DOLLAR", "group": "leveraged", "invert": False},
    "NZDUSD": {"endpoint": "tff", "pattern": "NEW ZEALAND DOLLAR", "group": "leveraged", "invert": False},
    # Rates. Treasury futures are price-like bond futures; long futures positioning is usually pressure on yields.
    "US02Y": {"endpoint": "tff", "pattern": "UST 2Y NOTE", "group": "leveraged", "invert": True},
    "US05Y": {"endpoint": "tff", "pattern": "UST 5Y NOTE", "group": "leveraged", "invert": True},
    "US10Y": {"endpoint": "tff", "pattern": "UST 10Y NOTE", "group": "leveraged", "invert": True},
    "US30Y": {"endpoint": "tff", "pattern": "UST BOND", "group": "leveraged", "invert": True},
    # Equity index futures.
    "SPX": {"endpoint": "tff", "pattern": "E-MINI S&P 500", "group": "leveraged", "invert": False},
    "NDX": {"endpoint": "tff", "pattern": "NASDAQ MINI", "group": "leveraged", "invert": False},
    "RUT": {"endpoint": "tff", "pattern": "RUSSELL E-MINI", "group": "leveraged", "invert": False},
    "DOW": {"endpoint": "tff", "pattern": "DJIA", "group": "leveraged", "invert": False},
    # Commodities.
    "GOLD": {"endpoint": "disagg", "pattern": "GOLD - COMMODITY", "group": "managed_money", "invert": False},
    "SILVER": {"endpoint": "disagg", "pattern": "SILVER - COMMODITY", "group": "managed_money", "invert": False},
    "COPPER": {"endpoint": "disagg", "pattern": "COPPER- #1", "group": "managed_money", "invert": False},
    "WTI": {"endpoint": "disagg", "pattern": "WTI-PHYSICAL", "group": "managed_money", "invert": False},
    "BRENT": {"endpoint": "disagg", "pattern": "BRENT", "group": "managed_money", "invert": False},
    "NG": {"endpoint": "disagg", "pattern": "NAT GAS NYME", "group": "managed_money", "invert": False},
    "GASOLINE": {"endpoint": "disagg", "pattern": "GASOLINE", "group": "managed_money", "invert": False},
    "HEATING": {"endpoint": "disagg", "pattern": "NY HARBOR ULSD", "group": "managed_money", "invert": False},
    "WHEAT": {"endpoint": "disagg", "pattern": "WHEAT - CHICAGO", "group": "managed_money", "invert": False},
    "CORN": {"endpoint": "disagg", "pattern": "CORN - CHICAGO", "group": "managed_money", "invert": False},
    "SOY": {"endpoint": "disagg", "pattern": "SOYBEANS - CHICAGO", "group": "managed_money", "invert": False},
    "COFFEE": {"endpoint": "disagg", "pattern": "COFFEE C", "group": "managed_money", "invert": False},
    "SUGAR": {"endpoint": "disagg", "pattern": "SUGAR NO. 11", "group": "managed_money", "invert": False},
    "COTTON": {"endpoint": "disagg", "pattern": "COTTON NO. 2", "group": "managed_money", "invert": False},
}

NUMERIC_ALIASES = {
    "open_interest": ["open_interest_all"],
    "tff_long": ["lev_money_positions_long", "lev_money_positions_long_all"],
    "tff_short": ["lev_money_positions_short", "lev_money_positions_short_all"],
    "tff_change_long": ["change_in_lev_money_long", "change_in_lev_money_long_all"],
    "tff_change_short": ["change_in_lev_money_short", "change_in_lev_money_short_all"],
    "disagg_long": ["m_money_positions_long_all", "m_money_positions_long", "managed_money_positions_long_all"],
    "disagg_short": ["m_money_positions_short_all", "m_money_positions_short", "managed_money_positions_short_all"],
    "disagg_change_long": ["change_in_m_money_long_all", "change_in_m_money_long", "change_in_managed_money_long_all"],
    "disagg_change_short": ["change_in_m_money_short_all", "change_in_m_money_short", "change_in_managed_money_short_all"],
    "disagg_commercial_long": ["prod_merc_positions_long_all", "prod_merc_positions_long"],
    "disagg_commercial_short": ["prod_merc_positions_short_all", "prod_merc_positions_short"],
    "disagg_commercial_change_long": ["change_in_prod_merc_long_all", "change_in_prod_merc_long"],
    "disagg_commercial_change_short": ["change_in_prod_merc_short_all", "change_in_prod_merc_short"],
}


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def fetch_json(endpoint: str, label: str) -> list[dict[str, Any]]:
    since = (dt.date.today() - dt.timedelta(days=370)).isoformat() + "T00:00:00"
    params = {
        "$where": f"report_date_as_yyyy_mm_dd >= '{since}'",
        "$limit": "50000",
        "$order": "report_date_as_yyyy_mm_dd ASC",
    }
    url = endpoint + "?" + urllib.parse.urlencode(params)
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Edgefield-Macro-Regime-Scanner/0.20"})
            with urllib.request.urlopen(req, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, list):
                raise RuntimeError(f"{label} endpoint did not return a JSON array")
            return payload
        except Exception as exc:  # pragma: no cover - network guard
            last_exc = exc
            if attempt < 2:
                time.sleep(3)
    raise RuntimeError(f"could not fetch CFTC {label}: {last_exc}")


def to_float(row: dict[str, Any], aliases: list[str]) -> float | None:
    for key in aliases:
        if key in row and row[key] not in (None, ""):
            try:
                return float(str(row[key]).replace(",", ""))
            except ValueError:
                continue
    return None


def row_date(row: dict[str, Any]) -> str:
    val = str(row.get("report_date_as_yyyy_mm_dd") or row.get("report_date_as_mm_dd_yyyy") or "")
    return val[:10] if val else ""


def match_rows(rows: list[dict[str, Any]], pattern: str) -> list[dict[str, Any]]:
    patt = pattern.upper()
    matched = []
    for row in rows:
        name = str(row.get("market_and_exchange_names", "")).upper()
        if not name:
            continue
        if name == patt or name.startswith(patt) or patt in name:
            matched.append(row)
    return matched


def choose_contract_rows(rows: list[dict[str, Any]], pattern: str) -> list[dict[str, Any]]:
    matched = match_rows(rows, pattern)
    if not matched:
        return []
    # If more than one contract name matches, keep the one with the highest average open interest.
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in matched:
        by_name.setdefault(str(row.get("market_and_exchange_names", "UNKNOWN")), []).append(row)
    best_name = max(by_name, key=lambda n: sum(to_float(r, NUMERIC_ALIASES["open_interest"]) or 0 for r in by_name[n]) / max(1, len(by_name[n])))
    return sorted(by_name[best_name], key=row_date)


def percentile_rank(values: list[float], current: float | None) -> float | None:
    """Simple 0-100 percentile rank within the fetched lookback window."""
    if current is None or len(values) < 8:
        return None
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    below_or_equal = sum(1 for v in vals if v <= current)
    return round((below_or_equal / len(vals)) * 100.0, 1)


def status_from_score(score: int) -> str:
    return {2: "Strong support", 1: "Support", 0: "Neutral", -1: "Pressure", -2: "Strong pressure"}.get(score, "Neutral")


def effective_values(net: float | None, oi: float | None, weekly_change: float | None, invert: bool) -> tuple[float | None, float | None]:
    if net is None or oi in (None, 0):
        return None, None
    pct = net / oi
    change_pct = None if weekly_change is None else weekly_change / oi
    if invert:
        pct = -pct
        if change_pct is not None:
            change_pct = -change_pct
    return pct, change_pct


def score_from_net(net: float | None, oi: float | None, weekly_change: float | None, invert: bool) -> tuple[int, str]:
    pct, change_pct = effective_values(net, oi, weekly_change, invert)
    if pct is None:
        return 0, "Neutral"
    if pct >= 0.15 and (change_pct or 0) >= 0:
        return 2, "Strong support"
    if pct > 0.03:
        return 1, "Support"
    if pct <= -0.15 and (change_pct or 0) <= 0:
        return -2, "Strong pressure"
    if pct < -0.03:
        return -1, "Pressure"
    return 0, "Neutral"


def score_weekly_change(weekly_change: float | None, oi: float | None, invert: bool) -> tuple[int, str]:
    if weekly_change is None or oi in (None, 0):
        return 0, "Neutral"
    change_pct = weekly_change / oi
    if invert:
        change_pct = -change_pct
    if change_pct >= 0.03:
        return 2, "Strong support"
    if change_pct >= 0.01:
        return 1, "Support"
    if change_pct <= -0.03:
        return -2, "Strong pressure"
    if change_pct <= -0.01:
        return -1, "Pressure"
    return 0, "Neutral"


def crowding_score(effective_pct: float | None, percentile: float | None) -> tuple[int, str, str]:
    if effective_pct is None or percentile is None:
        return 0, "Neutral", "No reliable crowding read from the current lookback window."
    if effective_pct > 0 and percentile >= 90:
        return -1, "Pressure", "Spec positioning is supportive but stretched near the high end of its recent range, so crowded-long unwind risk rises."
    if effective_pct < 0 and percentile <= 10:
        return 1, "Support", "Spec positioning is pressuring the asset but is stretched short, so short-covering can become supportive if other evidence turns."
    return 0, "Neutral", "Spec positioning is not at a recent extreme, so crowding risk is not a major signal yet."


def commercial_score(commercial_pct: float | None, percentile: float | None) -> tuple[int, str]:
    if commercial_pct is None or percentile is None:
        return 0, "Neutral"
    if percentile >= 90:
        return 1, "Support"
    if percentile <= 10:
        return -1, "Pressure"
    return 0, "Neutral"


def build_observation(asset_id: str, cfg: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    contract_rows = choose_contract_rows(rows, cfg["pattern"])
    if not contract_rows:
        return None
    latest = contract_rows[-1]
    previous = contract_rows[-2] if len(contract_rows) > 1 else None
    if cfg["endpoint"] == "tff":
        long_val = to_float(latest, NUMERIC_ALIASES["tff_long"])
        short_val = to_float(latest, NUMERIC_ALIASES["tff_short"])
        change_long = to_float(latest, NUMERIC_ALIASES["tff_change_long"])
        change_short = to_float(latest, NUMERIC_ALIASES["tff_change_short"])
        trader_group = "Leveraged Funds"
        report_name = "Traders in Financial Futures - Futures Only"
        commercial_long = commercial_short = commercial_change_long = commercial_change_short = None
        commercial_group = None
    else:
        long_val = to_float(latest, NUMERIC_ALIASES["disagg_long"])
        short_val = to_float(latest, NUMERIC_ALIASES["disagg_short"])
        change_long = to_float(latest, NUMERIC_ALIASES["disagg_change_long"])
        change_short = to_float(latest, NUMERIC_ALIASES["disagg_change_short"])
        trader_group = "Managed Money"
        report_name = "Disaggregated - Futures Only"
        commercial_long = to_float(latest, NUMERIC_ALIASES["disagg_commercial_long"])
        commercial_short = to_float(latest, NUMERIC_ALIASES["disagg_commercial_short"])
        commercial_change_long = to_float(latest, NUMERIC_ALIASES["disagg_commercial_change_long"])
        commercial_change_short = to_float(latest, NUMERIC_ALIASES["disagg_commercial_change_short"])
        commercial_group = "Producer/Merchant/Processor/User"
    oi = to_float(latest, NUMERIC_ALIASES["open_interest"])
    if long_val is None or short_val is None:
        return None
    net = long_val - short_val
    if change_long is None or change_short is None:
        if previous:
            prev_long = to_float(previous, NUMERIC_ALIASES["tff_long" if cfg["endpoint"] == "tff" else "disagg_long"])
            prev_short = to_float(previous, NUMERIC_ALIASES["tff_short" if cfg["endpoint"] == "tff" else "disagg_short"])
            weekly_change = (net - (prev_long - prev_short)) if prev_long is not None and prev_short is not None else None
        else:
            weekly_change = None
    else:
        weekly_change = change_long - change_short

    score, status = score_from_net(net, oi, weekly_change, bool(cfg.get("invert")))
    weekly_score, weekly_status = score_weekly_change(weekly_change, oi, bool(cfg.get("invert")))
    effective_pct, effective_change_pct = effective_values(net, oi, weekly_change, bool(cfg.get("invert")))

    effective_history: list[float] = []
    commercial_history: list[float] = []
    for row in contract_rows:
        hist_oi = to_float(row, NUMERIC_ALIASES["open_interest"])
        if cfg["endpoint"] == "tff":
            hist_long = to_float(row, NUMERIC_ALIASES["tff_long"])
            hist_short = to_float(row, NUMERIC_ALIASES["tff_short"])
            hist_comm_long = hist_comm_short = None
        else:
            hist_long = to_float(row, NUMERIC_ALIASES["disagg_long"])
            hist_short = to_float(row, NUMERIC_ALIASES["disagg_short"])
            hist_comm_long = to_float(row, NUMERIC_ALIASES["disagg_commercial_long"])
            hist_comm_short = to_float(row, NUMERIC_ALIASES["disagg_commercial_short"])
        if hist_oi not in (None, 0) and hist_long is not None and hist_short is not None:
            hist_pct = (hist_long - hist_short) / hist_oi
            if cfg.get("invert"):
                hist_pct = -hist_pct
            effective_history.append(hist_pct)
        if hist_oi not in (None, 0) and hist_comm_long is not None and hist_comm_short is not None:
            commercial_history.append((hist_comm_long - hist_comm_short) / hist_oi)

    spec_percentile = percentile_rank(effective_history, effective_pct)
    crowd_score, crowd_status, crowd_effect = crowding_score(effective_pct, spec_percentile)

    commercial_net = None
    commercial_weekly_change = None
    commercial_pct = None
    commercial_percentile = None
    commercial_extreme_score = 0
    commercial_extreme_status = "Neutral"
    if commercial_long is not None and commercial_short is not None:
        commercial_net = commercial_long - commercial_short
        if commercial_change_long is not None and commercial_change_short is not None:
            commercial_weekly_change = commercial_change_long - commercial_change_short
        commercial_pct = None if not oi else commercial_net / oi
        commercial_percentile = percentile_rank(commercial_history, commercial_pct)
        commercial_extreme_score, commercial_extreme_status = commercial_score(commercial_pct, commercial_percentile)

    conflict = False
    if effective_pct is not None and commercial_pct is not None:
        conflict = abs(effective_pct) >= 0.03 and abs(commercial_pct) >= 0.03 and (effective_pct > 0) != (commercial_pct > 0)

    net_pct = None if not oi else round((net / oi) * 100.0, 2)
    return {
        "asset_id": asset_id,
        "report_type": cfg["endpoint"],
        "report_name": report_name,
        "trader_group": trader_group,
        "commercial_group": commercial_group,
        "cftc_market": latest.get("market_and_exchange_names"),
        "contract_code": latest.get("cftc_contract_market_code"),
        "report_date": row_date(latest),
        "open_interest": int(oi) if oi is not None else None,
        "long": int(long_val),
        "short": int(short_val),
        "net": int(net),
        "net_pct_of_open_interest": net_pct,
        "effective_net_pct_of_open_interest": None if effective_pct is None else round(effective_pct * 100.0, 2),
        "weekly_net_change": int(weekly_change) if weekly_change is not None else None,
        "effective_weekly_change_pct_of_open_interest": None if effective_change_pct is None else round(effective_change_pct * 100.0, 2),
        "invert_for_asset": bool(cfg.get("invert")),
        "score": score,
        "status": status,
        "weekly_change_score": weekly_score,
        "weekly_change_status": weekly_status,
        "spec_percentile_1y": spec_percentile,
        "crowding_score": crowd_score,
        "crowding_status": crowd_status,
        "crowding_effect": crowd_effect,
        "commercial_long": int(commercial_long) if commercial_long is not None else None,
        "commercial_short": int(commercial_short) if commercial_short is not None else None,
        "commercial_net": int(commercial_net) if commercial_net is not None else None,
        "commercial_weekly_change": int(commercial_weekly_change) if commercial_weekly_change is not None else None,
        "commercial_net_pct_of_open_interest": None if commercial_pct is None else round(commercial_pct * 100.0, 2),
        "commercial_percentile_1y": commercial_percentile,
        "commercial_extreme_score": commercial_extreme_score,
        "commercial_extreme_status": commercial_extreme_status,
        "cot_conflict": conflict,
    }

def compact_contract_rows(rows: list[dict[str, Any]], asset_id: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only the recent rows needed for audit, not the full CFTC dataset.

    GitHub blocks files over 100 MB. The public CFTC endpoints can return very
    large JSON arrays, so this project stores a compact raw audit file containing
    only the matched contract rows used by the normalized observations.
    """
    contract_rows = choose_contract_rows(rows, cfg["pattern"])
    out: list[dict[str, Any]] = []
    for row in contract_rows[-4:]:
        out.append({
            "asset_id": asset_id,
            "market_and_exchange_names": row.get("market_and_exchange_names"),
            "cftc_contract_market_code": row.get("cftc_contract_market_code"),
            "report_date_as_yyyy_mm_dd": row.get("report_date_as_yyyy_mm_dd"),
            "open_interest_all": row.get("open_interest_all"),
            "lev_money_positions_long_all": row.get("lev_money_positions_long_all"),
            "lev_money_positions_short_all": row.get("lev_money_positions_short_all"),
            "change_in_lev_money_long_all": row.get("change_in_lev_money_long_all"),
            "change_in_lev_money_short_all": row.get("change_in_lev_money_short_all"),
            "m_money_positions_long_all": row.get("m_money_positions_long_all"),
            "m_money_positions_short_all": row.get("m_money_positions_short_all"),
            "change_in_m_money_long_all": row.get("change_in_m_money_long_all"),
            "change_in_m_money_short_all": row.get("change_in_m_money_short_all"),
            "prod_merc_positions_long_all": row.get("prod_merc_positions_long_all"),
            "prod_merc_positions_short_all": row.get("prod_merc_positions_short_all"),
            "change_in_prod_merc_long_all": row.get("change_in_prod_merc_long_all"),
            "change_in_prod_merc_short_all": row.get("change_in_prod_merc_short_all"),
        })
    return out


def main() -> int:
    fetched_at = iso_now()
    tff = fetch_json(TFF_ENDPOINT, "TFF futures only")
    disagg = fetch_json(DISAGG_ENDPOINT, "Disaggregated futures only")
    observations: dict[str, Any] = {}
    compact_raw = {
        "fetched_at": fetched_at,
        "note": "Compact audit rows only. Full CFTC JSON datasets are intentionally not committed because they can exceed GitHub's 100 MB file limit.",
        "datasets": {
            "tff_futures_only": TFF_ENDPOINT,
            "disaggregated_futures_only": DISAGG_ENDPOINT,
        },
        "rows": [],
    }
    for asset_id, cfg in CONTRACT_MAP.items():
        rows = tff if cfg["endpoint"] == "tff" else disagg
        compact_raw["rows"].extend(compact_contract_rows(rows, asset_id, cfg))
        obs = build_observation(asset_id, cfg, rows)
        if obs:
            observations[asset_id] = obs
    (RAW_DIR / "cftc_recent_compact_audit.json").write_text(json.dumps(compact_raw, indent=2), encoding="utf-8")
    # Remove obsolete large raw files from earlier scaffold runs if present.
    for obsolete in ["cftc_tff_recent.json", "cftc_disaggregated_recent.json"]:
        old_path = RAW_DIR / obsolete
        if old_path.exists():
            old_path.unlink()
    dates = sorted({obs["report_date"] for obs in observations.values() if obs.get("report_date")})
    normalized = {
        "source_id": "CFTC_COT",
        "source_name": "CFTC Commitments of Traders public reports",
        "fetched_at": fetched_at,
        "latest_report_date": dates[-1] if dates else None,
        "reporting_note": "COT is a weekly public report based on Tuesday open interest and normally released Friday afternoon. This lane uses positioning only, not market prices.",
        "datasets": {
            "tff_futures_only": TFF_ENDPOINT,
            "disaggregated_futures_only": DISAGG_ENDPOINT,
        },
        "observations": observations,
        "missing_asset_ids": [aid for aid in CONTRACT_MAP if aid not in observations],
    }
    (NORM_DIR / "cot_positioning.json").write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    print(f"Fetched CFTC COT observations: {len(observations)} assets; latest report date: {normalized['latest_report_date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
