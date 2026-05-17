# Macro Regime Scanner v0.25F Foundation Infrastructure

This version is a foundation build, not a scoring rebuild.

## Purpose

v0.25F is designed to stop the endless cycle of one-off source patches. The project now has a basic infrastructure layer for deep source extraction:

1. `config/source_extraction_manifest.json` defines the target data universe.
2. `config/input_registry.json` defines every intended input variable.
3. `config/asset_input_map.json` defines which inputs are direct or contextual for each asset.
4. `config/source_pipeline.json` defines the enabled source lanes.
5. `scripts/refresh_all_sources.py` is the stable orchestrator that runs enabled source lanes from config.

## What this version does not do

- It does not claim final scoring is correct.
- It does not add BEA, Fed, or Census fetchers yet.
- It does not rewrite every source fetcher to extract every planned variable yet.
- It does not use the failed contract/audit experiments from v0.26/v0.27.

## Current live lanes carried from clean v0.24

- Treasury official rates
- CFTC COT positioning
- EIA energy fundamentals
- USDA/NASS agriculture scaffold
- BLS inflation/labor

## Planned source lanes

- BEA growth/PCE/income/consumption
- Federal Reserve policy/liquidity
- Census retail/housing/trade/durable goods

## Workflow strategy

The GitHub Actions file should not list every source step forever. It should run one orchestrator:

```yaml
- name: Refresh all enabled public-source lanes
  env:
    EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
    USDA_API_KEY: ${{ secrets.USDA_API_KEY }}
    BEA_API_KEY: ${{ secrets.BEA_API_KEY }}
    CENSUS_API_KEY: ${{ secrets.CENSUS_API_KEY }}
  run: python scripts/refresh_all_sources.py
```

The orchestrator reads `config/source_pipeline.json` and runs only enabled lanes.

## Adding future variables without touching workflow YAML

For new variables in an existing source:

1. Add/update the variable in `config/input_registry.json`.
2. Add/update direct/context mapping in `config/asset_input_map.json`.
3. Update the source fetch/apply scripts.
4. Keep the master workflow unchanged.

For a new source lane:

1. Add fetch/apply scripts.
2. Add the lane to `config/source_pipeline.json`.
3. Enable only after local/script testing.
4. Keep the master workflow unchanged.

## Scoring principle

The registry and asset map are infrastructure. Scoring should be rebuilt later from this foundation, using:

- source reliability,
- variable relevance,
- asset-specific direction,
- live-vs-context classification,
- freshness,
- conflicts between sources.

No score should be treated as final until the scoring rulebook is written and tested.
