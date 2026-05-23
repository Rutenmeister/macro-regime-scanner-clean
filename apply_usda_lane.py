# Macro Regime Scanner v0.47 — U.S.-Centered Integrity Baseline

This is a narrow robustness and distribution-scope pass after v0.46.

## Why this version exists

The scanner is intentionally not a price model and should not overstate what the current source stack can support. The live source stack is heavily U.S.-centered: Treasury, CFTC COT, EIA, USDA, BLS, BEA, Federal Reserve/liquidity, Census, credit/financial stress, and NOAA/NWS weather.

Because of that, v0.47 removes non-USD FX crosses from the displayed asset universe:

- EURGBP
- EURJPY
- AUDJPY
- NZDJPY

These instruments can be restored later only if direct non-U.S. macro/central-bank source lanes are added.

## What stayed

- Uncapped raw pressure scores.
- No price data in live score.
- Release calendar confidence labels.
- Release result fields when verified.
- Score snapshots and why-score-changed summaries.
- Source QA, professional reports, and suite bridge exports.

## Product principle

If an asset cannot be scored honestly from the available official/public-source lanes, it should be removed or clearly labeled as unsupported rather than displayed as low-evidence noise.
