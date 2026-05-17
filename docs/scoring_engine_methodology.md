# Macro Regime Scanner v0.34 - Explainable Scoring Methodology

## Purpose

v0.34 changes the scoring philosophy from generic scoring to explainable asset-specific evidence pressure.

The goal is not to make the scores more dramatic. The goal is to make them more honest:

- only real live values count;
- only relevant inputs affect each asset;
- each input has the correct directional effect for that asset;
- each input has a reasonable relevance weight;
- U.S. data is treated differently depending on the asset;
- every score can be audited from row-level evidence.

## Core scoring statuses

Each input row is assigned one of four statuses:

| Status | Scores? | Meaning |
|---|---:|---|
| `live_scored` | Yes | Fresh/live row with direct or meaningful asset relevance. |
| `live_context` | No | Fresh/live row that informs interpretation but is too indirect to move the score in this pass. |
| `display_only` | No | Visible row for user awareness only. |
| `not_live` | No | Missing, stale, candidate, scaffold, or unverified row. |

Important rule:

> Missing data is not neutral. Stale data is not neutral. Candidate data is not scored.

## Weight tiers

| Tier | Weight | Use |
|---|---:|---|
| `primary` | 1.00 | Directly important to the asset. |
| `secondary` | 0.60 | Meaningful but not dominant. |
| `contextual` | 0.25 | Useful context but not counted in v0.34 net score. |
| `low` | 0.10 | Barely relevant; visible only in v0.34. |
| `excluded` | 0.00 | Does not score. |

In v0.34, `primary` and `secondary` are counted. `contextual` and `low` are shown in the audit but not counted. This is conservative by design.

## Directional mapping examples

The same input can affect different assets differently.

### Hot U.S. inflation

| Asset | Effect |
|---|---|
| SPX / Nasdaq | Usually negative through rate-pressure and discount-rate channels. |
| 10Y yield | Positive yield pressure. |
| DXY / USD | Often supportive if it raises Fed-rate expectations. |
| EURUSD | Often negative because USD-side pressure strengthens. |
| Gold | Mixed: inflation support can be offset by real-yield pressure. |
| WTI | Mostly contextual unless inflation changes demand/rate expectations. |
| Wheat / Corn | Low direct relevance. |

### Rising 10Y yield pressure

| Asset | Effect |
|---|---|
| 10Y yield | Direct positive pressure. |
| SPX / Nasdaq | Negative pressure through valuation and financing channels. |
| Gold | Usually negative when real-yield/USD pressure dominates. |
| DXY | Supportive through rate differentials. |
| EURUSD | Negative through USD strength. |
| WTI | Contextual, not direct physical energy evidence. |
| Wheat / Corn | Low/directly excluded in this pass. |

## Score audit object

Each asset receives a `scoreAudit` object:

```json
{
  "asset": "SPX500",
  "assetClass": "us_equity_index",
  "label": "Negative live pressure",
  "confidence": "Medium",
  "coverage": 0.5,
  "countedRows": 4,
  "contextRows": 1,
  "excludedRows": 3,
  "positiveWeight": 0.45,
  "negativeWeight": -3.14,
  "netScore": -2.69,
  "conflictLevel": "Low",
  "topPositiveDrivers": [],
  "topNegativeDrivers": [],
  "mainConflicts": []
}
```

## Confidence labels

Confidence is based on counted rows, direct rows, and coverage.

| Confidence | Meaning |
|---|---|
| High | Many counted/direct rows and broad coverage. |
| Medium | Enough direct evidence to interpret, but not fully broad. |
| Low | Some direct evidence, but coverage is partial. |
| Insufficient | Not enough live direct evidence to score honestly. |

## Pressure labels

Avoid buy/sell language. Use evidence-pressure labels:

- Positive live pressure
- Moderately positive live pressure
- Mixed live evidence
- Moderately negative live pressure
- Negative live pressure
- Insufficient live direct evidence

## Caveat language

Every asset audit should remind the user:

- This is evidence pressure, not a trade signal.
- Missing or stale evidence is excluded, not treated as neutral.
- U.S. macro evidence is weighted differently by asset class.
- Asset-specific exceptions may require manual tuning.

## Files in this patch

- `config/scoring_rules.json`
- `config/asset_input_map.json`
- `scripts/recompute_live_scores.py`
- `ui/score_audit_panel_snippet.js`
- `data/sample/sample_macro_regime_scanner.json`

## Recommended freeze name

If this works cleanly in the live repo:

**Macro Regime Scanner v0.34 - Explainable Scoring Baseline**
