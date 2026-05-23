# Macro Regime Scanner v0.50 — Macro Quad Snapshot Baseline

v0.50 preserves the v0.49 beta launch wrapper and adds a compact no-price Growth / Inflation Pressure Map.

## What changed

- Added `data/macro_quad_snapshot.json`.
- Added `scripts/build_macro_quad_snapshot.py`.
- Added `scripts/validate_macro_quad_snapshot.py`.
- Added a top-of-app Macro Quad Snapshot panel.
- Added the 9-state regime model:
  - Goldilocks
  - Goldilocks / Reflation Blend
  - Reflation
  - Reflation / Stagflation Blend
  - Stagflation
  - Stagflation / Deflation Blend
  - Deflation
  - Deflation / Goldilocks Blend
  - Neutral / Low-Conviction Macro Pressure
- Updated the professional regime brief to include the current macro quad.
- Updated workflow validation to build and validate the macro quad snapshot.

## Important boundary

The quad map does not use price. It summarizes current public-source row evidence into two axes: growth pressure and inflation/policy pressure.

Blend states describe current ambiguity between adjacent regimes. They do not claim a historical transition path until more quad snapshots are collected.

## Why it matters

The Regime Queue tells users which assets have the strongest public-source pressure. The Growth / Inflation Pressure Map tells users what broad macro backdrop is producing that pressure.
