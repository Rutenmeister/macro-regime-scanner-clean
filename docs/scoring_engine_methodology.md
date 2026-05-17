# Macro Regime Scanner v0.32 Scoring Engine Methodology

## Purpose

v0.32 rebuilds the asset header score so it reflects live public-source evidence instead of prototype assumptions.

The score is not a trade signal. It is a source-weighted pressure read that asks:

> What does the current public-source evidence stack imply for this asset, given the asset's actual sensitivity to the source?

## Core rules

1. Only live/fresh rows with numeric source scores and real provenance can affect the top-level asset score.
2. Prototype, sample, candidate, missing, low-relevance, and display-only rows are excluded.
3. Each counted row receives an asset-specific weight.
4. U.S. macro data is not treated as equally direct for every global asset.
5. Each asset receives a `scoreAudit` object showing counted rows, exclusions, contributions, and conflicts.

## Asset treatment

- U.S. equities prioritize inflation, Fed/liquidity, credit stress, Treasury-rate pressure, growth data, and COT.
- Global equities receive lower weights for U.S.-only data unless the channel is global risk, USD liquidity, or credit stress.
- USD pairs receive higher weights for U.S. rates, inflation, Fed policy, and dollar-liquidity channels; non-USD FX crosses receive low weights for U.S.-only macro data.
- Gold and silver prioritize Treasury/real-yield/Fed/inflation/COT/credit-stress channels, while recognizing that inflation and safe-haven channels can conflict.
- Energy assets prioritize EIA physical data, energy COT, and relevant macro demand context.
- Grains and softs prioritize USDA, NOAA/weather, and COT; U.S. CPI or retail activity is usually context only.
- Credit/liquidity assets prioritize financial stress, Fed liquidity, rate pressure, and macro growth/inflation stress.

## Score audit fields

Each asset has:

- `scoreAudit.countedRows`
- `scoreAudit.contextRows`
- `scoreAudit.excludedRows`
- `scoreAudit.positiveContribution`
- `scoreAudit.negativeContribution`
- `scoreAudit.netContribution`
- `scoreAudit.finalScore`
- `scoreAudit.topPositiveDrivers`
- `scoreAudit.topNegativeDrivers`
- `scoreAudit.countedDetails`

This makes every score traceable.

## External reasoning anchors

The methodology reflects standard macro channels: monetary policy influences financial conditions; credit/financial-stress indexes summarize market stress; interest-rate differentials can affect exchange rates; and gold is sensitive to real-rate, dollar, safe-haven, and inflation channels. The implementation is intentionally conservative and should be reviewed against real market examples after each source refresh.
