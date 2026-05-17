# v0.28 Federal Reserve / Liquidity Lane

Adds a public Federal Reserve/FRED policy and liquidity lane without requiring a new API secret in v0.28.

## Series

- `EFFR` — Effective federal funds rate.
- `WALCL` — Federal Reserve total assets, converted from millions to billions USD.
- `WRESBAL` — Reserve balances with Federal Reserve Banks, converted from millions to billions USD.
- `RRPONTSYD` — Overnight reverse repo usage, billions USD.
- `WTREGEN` — Treasury General Account at the Fed, converted from millions to billions USD.

## Interpretation

Policy-rate rows are primary for rates and USD, and generally pressure risk assets and precious metals when restrictive. Liquidity rows are positive when liquidity is easier and negative when liquidity is tighter. Reverse repo and TGA are treated as liquidity drains: falling balances are easier/liquidity supportive; rising balances are tighter/liquidity pressure.

## Workflow

No GitHub workflow rewrite is required if the repo already uses the orchestrator:

```text
python scripts/refresh_all_sources.py
```

The lane is enabled in `config/source_pipeline.json`.
