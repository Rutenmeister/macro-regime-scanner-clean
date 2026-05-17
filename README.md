# Macro Regime Scanner v0.25F Foundation Infrastructure

Public-source macro/fundamental pressure terminal.

This build starts from the clean v0.24 BLS Macro baseline and adds the infrastructure needed to deepen variables without constantly rewriting GitHub workflows.

## What is included

- Working terminal UI from v0.24.
- Existing live source lanes from v0.24:
  - Treasury official yield data
  - CFTC COT positioning
  - EIA energy fundamentals
  - USDA/NASS agriculture scaffold
  - BLS inflation/labor
- Deep source extraction manifest:
  - `config/source_extraction_manifest.json`
  - `docs/source_extraction_manifest.md`
- Foundational input registry:
  - `config/input_registry.json`
- Asset/input relevance map:
  - `config/asset_input_map.json`
- Stable source pipeline config:
  - `config/source_pipeline.json`
- Stable orchestrator:
  - `scripts/refresh_all_sources.py`
- Manual workflow instructions:
  - `docs/master_refresh_workflow.md`

## Important boundary

This is **not** a final scoring build.

The purpose is to create the foundation for deep variable extraction and future scoring. The scoring engine should be rebuilt only after the variables and asset relevance map are reviewed.

## Recommended workflow strategy

Use one master workflow that calls:

```bash
python scripts/refresh_all_sources.py
```

Do not keep adding every source as a separate YAML step.

## Required GitHub secrets

Current live lanes require:

```text
EIA_API_KEY
USDA_API_KEY
```

Future lanes may use:

```text
BEA_API_KEY
CENSUS_API_KEY
```

## Validation

Run locally from repo root:

```bash
python scripts/refresh_all_sources.py --dry-run
python scripts/validate_data.py
```

## Project principle

No placeholder scoring should be treated as truth. Live source data, normalized variables, asset relevance, and scoring methodology are separate layers.


## v0.26D Deep Variable Extraction Upgrade

Deepens existing live lanes from the v0.25F foundation. The master workflow remains orchestrator-based through `scripts/refresh_all_sources.py`; do not rewrite GitHub workflow YAML for source-variable expansion.


## v0.27 BEA Macro Lane

Adds a BEA public-source macro lane for GDP/PCE/growth context through the existing orchestrator. Requires a `BEA_API_KEY` GitHub Actions secret. See `docs/bea_macro_lane.md`.


## v0.28 Federal Reserve / Liquidity Lane

Adds Federal Reserve/FRED public policy and liquidity data: EFFR, total assets, reserve balances, reverse repo usage, and Treasury General Account. No new API secret is required in v0.28.


## v0.30 Credit / Financial Stress Lane

Adds a public FRED-based credit and financial-stress lane with high-yield OAS, investment-grade OAS, BBB OAS, NFCI, ANFCI, and STLFSI4. No new API secret is required. The existing orchestrator workflow continues to run `scripts/refresh_all_sources.py`.


## v0.31 NOAA/NWS Weather Hazard Lane

Adds a NOAA/National Weather Service public active-alerts lane for live weather-hazard context. No API key is required. This lane captures active hazard counts for heat, cold/freeze, winter storms, floods, severe storms/tornadoes, tropical storms/hurricanes, fire weather, and sparse drought wording. It is useful for energy-demand, agriculture/crop stress, logistics, and physical-disruption context, but it is not a full drought monitor, seasonal forecast, or paid weather-model feed.


## v0.33 Release Calendar + Row Toggle

Adds a sidebar toggle to hide/show non-applicable evidence rows and generates `data/release_calendar.json` during the orchestrated refresh so tracked report dates/times can display under Source Health.
