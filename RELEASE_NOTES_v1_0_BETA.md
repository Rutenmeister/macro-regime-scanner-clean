# Macro Regime Scanner v1.0 Beta — Regime + Evidence Release

This release starts from the restored v0.49 working baseline and keeps the product U.S.-centered, public-source, price-free, and raw-score based.

## What changed

- Adds a compact **Current Macro Regime** card above the Regime Queue.
- Classifies only four regimes: Goldilocks, Reflation, Stagflation, and Deflation.
- Shows **Growth Score** and **Inflation Score** as point tallies instead of hiding the magnitude behind labels.
- Replaces broad keyword-only regime inference with an explicit in-app factor registry for the regime tally.
- Adds a short methodology note explaining that regime scores are live-factor tallies and price is not used.
- Adds a compact **What changed** line above the Regime Queue using prior-score movement where available.
- Adds the current macro regime to the exported markdown regime brief.
- Strengthens top-strip and footer language around known limits, evidence pressure, and research-only use.
- Loads optional support JSON files when available: release results, source quality, validation summary, regime bridge, and refresh report.

## What did not change

- No price data was added to live scoring.
- No new source lane was added.
- No workflow step was added.
- No new generated regime JSON file was added.
- The main asset scores and source pipeline remain based on the existing scanner architecture.

## Product intent

The terminal should be read top-down:

1. Current macro regime.
2. Raw-pressure Regime Queue.
3. Open-row score audit and factor evidence.
4. Source health, upcoming reports, and caveats.

This remains a research tool, not a buy/sell signal or investment advice.
