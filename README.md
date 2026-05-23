# Edgefield Research Macro Regime Scanner v0.50.4

U.S.-centered macro pressure terminal using official and public-source data. Raw, uncapped scores rank fundamental pressure across assets without using price.

v0.50.4 preserves the v0.49/v0.48 distribution baseline and replaces the prior quad experiment with a simple four-quad Growth / Inflation Regime map.

## Growth / Inflation Regime

The top regime panel uses two current public-source axes:

- Growth pressure
- Inflation pressure

It resolves those two axes into one of four regimes:

- Goldilocks: Growth positive / Inflation negative
- Reflation: Growth positive / Inflation positive
- Stagflation: Growth negative / Inflation positive
- Deflation: Growth negative / Inflation negative

No price is used. No confidence score is shown. No blend or transition states are used.

## Core product rules

- Raw uncapped scores stay.
- Price stays out of live scoring.
- U.S.-centered asset scope stays.
- Unsupported non-USD FX crosses remain removed.
- Missing, stale, candidate, and display-only rows are not treated as neutral.
- The regime panel is a summary lens; asset rows remain the detailed evidence layer.

## Refresh

Run the normal Refresh All Public Sources workflow. The workflow rebuilds live source data, recomputes scores, builds the Growth / Inflation Regime, validates outputs, and writes refreshed JSON/report files.
