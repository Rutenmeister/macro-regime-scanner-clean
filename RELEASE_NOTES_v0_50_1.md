# Macro Regime Scanner v0.50.1 — Quad Scoring Calibration

This is a narrow repair iteration for the Growth / Inflation Pressure Map.

It preserves v0.50's 9-state no-price macro quad overlay, but changes the axis extraction so asset-level scoring conflicts do not accidentally cancel obvious macro pressure into zero.

## What changed

- Growth and inflation axes now use calibrated source-row grouping.
- Inflation/rate rows no longer cancel simply because the same macro input helps one asset and hurts another.
- Blend states are used when one axis is clear and the other is mixed.
- Confidence remains separate from pressure direction.
- No price data is added.
- No scanner asset scores are changed.

## Product intent

The quad panel is a top-level macro weather map. It summarizes growth pressure and inflation/policy pressure from existing public-source scanner evidence. It does not replace asset-specific score audits and does not create buy/sell signals.
