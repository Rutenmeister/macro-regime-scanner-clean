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
