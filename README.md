# Edgefield Research Macro Regime Scanner v0.50

U.S.-centered public-source macro pressure terminal using raw, uncapped, price-free scores.

## Current baseline

v0.50 starts from the v0.49 Beta Launch Wrapper and adds the Growth / Inflation Pressure Map.

## Core principles

- No price in the live score.
- Raw uncapped pressure scores.
- Official/public-source evidence lanes.
- U.S.-centered asset scope.
- Missing data is not treated as neutral.
- Scores are research evidence, not buy/sell signals.

## Major modules

- Regime Queue Snapshot with up to 10 assets per bucket.
- Asset-level score audits.
- Source health and release calendar confidence.
- Release-result schema for actual/forecast/previous when verified data exists.
- Score history and why-score-changed summaries.
- Professional macro regime brief export.
- Growth / Inflation Pressure Map with 9 no-price macro states.

## Macro Quad Snapshot

The Growth / Inflation Pressure Map summarizes current public-source evidence into two axes:

- Growth pressure
- Inflation / policy pressure

It classifies the backdrop into four main regimes, four blend states, or one low-conviction state using current public-source growth and inflation pressure.

## Validation

Run from the repo root:

```bash
python scripts/validate_data.py
python scripts/validate_score_history.py
python scripts/validate_signal_framework.py
python scripts/validate_release_calendar.py
python scripts/validate_release_results.py
python scripts/validate_source_quality.py
python scripts/validate_regime_bridge.py
python scripts/build_macro_quad_snapshot.py
python scripts/validate_macro_quad_snapshot.py
node --check app.js
```

## Refresh workflow

The GitHub Actions workflow refreshes public-source lanes, recomputes scores, builds research infrastructure, builds the macro quad snapshot, validates outputs, and commits refreshed data.

## Distribution boundary

Research tool only. Not investment advice, not a trade signal, and not a performance guarantee.
