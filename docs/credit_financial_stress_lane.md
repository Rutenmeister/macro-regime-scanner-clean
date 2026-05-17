# v0.30 Credit / Financial Stress Lane

This lane adds public credit-spread and financial-stress context to the Macro Regime Scanner.

## Source approach

The lane uses public FRED CSV/plain-text endpoints and does not require a GitHub secret in v0.30.

## Normalized output

- `data/normalized/financial_stress.json`
- `data/raw/financial_stress/financial_stress_compact_audit.json`

## Target variables

- High-yield option-adjusted spread (`BAMLH0A0HYM2`)
- Investment-grade corporate option-adjusted spread (`BAMLC0A0CM`)
- BBB corporate option-adjusted spread (`BAMLC0A4CBBB`)
- Chicago Fed National Financial Conditions Index (`NFCI`)
- Chicago Fed Adjusted National Financial Conditions Index (`ANFCI`)
- St. Louis Fed Financial Stress Index (`STLFSI4`)

## Directional convention

The fetcher normalizes raw scores so:

- positive = easier/lower-stress credit or financial conditions
- negative = tighter/higher-stress credit or financial conditions

The apply script then maps that into asset-specific effects:

- Equities and credit: wider spreads / higher stress = pressure
- USD: stress can be supportive through funding/safe-haven channels
- Rates: stress can reduce upward yield pressure through growth/risk channels
- Precious metals: stress is mixed/secondary because defensive demand can conflict with USD and liquidity pressure
- Commodities: mostly contextual unless the asset is tied to growth/risk demand

## Notes

This lane is not a price-technical lane. It uses public macro/credit-condition series to describe credit stress and financial conditions.
