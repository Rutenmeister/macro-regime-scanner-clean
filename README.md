# Macro Regime Scanner Public-Source Prototype v0.24

GitHub-ready public-source fundamental pressure terminal for Edgefield Systems.

## What this is

Macro Regime Scanner is a no-price-data public-source market pressure terminal. It reads `data/macro_regime_scanner.json` and displays compact scan rows plus expandable input-first evidence tables.

It does **not** use price trend, momentum, moving averages, technical confirmation, or manual market-value entry.

## v0.24 change

v0.24 adds the **BLS Inflation / Labor Lane** scaffold.

New files:

- `.github/workflows/refresh-bls.yml`
- `scripts/sources/fetch_bls_macro.py`
- `scripts/apply_bls_lane.py`
- `data/raw/bls/`
- `data/normalized/bls_macro.json` after the workflow runs

BLS inputs added by the lane:

- CPI pressure
- Core CPI pressure
- PPI pressure
- Unemployment rate
- Payroll growth
- Wage pressure

The BLS lane uses the public BLS API and does not require an API key at the current request size. It should still cite BLS as source and should not imply BLS endorsement of Edgefield scores or analysis.

## Current live/source-lane architecture

Already supported:

- U.S. Treasury official daily rates
- CFTC COT positioning
- EIA energy fundamentals
- USDA/NASS agriculture scaffold
- BLS inflation/labor scaffold

## Workflows

- `Validate Macro Regime Scanner Data`
- `Refresh Treasury Lane`
- `Refresh CFTC COT Lane`
- `Refresh EIA Energy Lane`
- `Refresh USDA Agriculture Lane`
- `Refresh BLS Inflation Labor Lane`
- `Refresh All Public Sources`

Use **Refresh All Public Sources** as the main workflow after BLS has been tested by itself.

## Files

- `index.html` - UI shell
- `style.css` - Edgefield visual styling
- `app.js` - dashboard behavior; loads `data/macro_regime_scanner.json`
- `data/macro_regime_scanner.json` - dashboard data contract
- `config/` - source, asset, input, scoring, and freshness registries
- `scripts/` - validation and source-lane scripts

## Validation

Run locally from the project root:

```bash
python scripts/validate_data.py
```

The validator checks that the public-source edition remains free of price-derived/technical inputs and that all factors preserve relevance, score, provenance, effect, source, and freshness fields.
