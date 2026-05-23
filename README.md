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


## v0.34 Explainable Trust Layer

Starts from the working v0.33.1 Wide Release Calendar baseline and adds rating-raising trust features without changing the live-source architecture:

- Regime Queue Snapshot above the main evidence queue.
- Stronger expanded asset score-audit panel.
- Counted/context/excluded row visibility in the audit.
- Asset-level caveats explaining what the score does not prove.
- Sidebar trust guide.
- Export Current Regime Brief markdown button.

This version is meant to raise scoring trust, UX clarity, and commercial readiness by making every score explain itself. It does not add new source lanes.

Validation:

```bash
node --check app.js
python scripts/recompute_live_scores.py
python scripts/validate_data.py
```

## v0.40 Raw Score History Baseline

This package advances the frozen v0.34 Explainable Trust Layer by removing the +/-10 display cap, repairing Regime Queue buckets, adding raw pressure score labels/tags, writing score snapshots, adding why-score-changed summaries, and preparing an optional forward-return validation framework that stays separate from live scoring.

Run the validation set before deploying:

```bash
node --check app.js
python scripts/recompute_live_scores.py
python scripts/validate_data.py
python scripts/validate_score_history.py
python scripts/validate_signal_framework.py
```

## v0.46 note — Official Release Calendar Hardening

v0.46 keeps the v0.40 raw-score/history scanner intact and hardens the Upcoming Tracked Reports module. Calendar events now include `calendarConfidence` (`official`, `official-pattern`, or `estimated`) and `sourceUrl`, with validation to prevent known false dates such as Retail Sales May 20, PCE May 23, and Treasury releases on Memorial Day.



## v0.46 Research Infrastructure Additions

This package includes five integrated version steps after v0.41:

- v0.42 release-result schema (`data/release_results.json`).
- v0.43 validation summary framework (`data/validation/score_validation_summary.json`).
- v0.44 source QA / asset coverage (`data/source_quality.json`).
- v0.45 generated professional reports (`data/reports/`).
- v0.46 suite bridge exports (`data/exports/regime_labels_latest.json` and `.csv`).

Run the workflow or execute the scripts in this order after refreshing source lanes:

```bash
python scripts/generate_release_calendar.py
python scripts/recompute_live_scores.py
python scripts/validate_data.py
python scripts/validate_score_history.py
python scripts/validate_signal_framework.py
python scripts/validate_release_calendar.py
python scripts/generate_release_results.py
python scripts/validate_release_results.py
python scripts/build_validation_report.py
python scripts/build_source_quality.py
python scripts/validate_source_quality.py
python scripts/export_regime_bridge.py
python scripts/validate_regime_bridge.py
python scripts/generate_professional_report.py
```

Do not treat null actual/forecast/previous values as zero or neutral. They mean no trusted result feed is attached yet.

## v0.47 note — U.S.-Centered Integrity Baseline

v0.47 is a robustness/scope cleanup. It preserves v0.46 research infrastructure while removing non-USD FX crosses (EURGBP, EURJPY, AUDJPY, NZDJPY) from the displayed asset universe because the current source stack is U.S.-centered. The product keeps price data out of the live score, uses raw uncapped pressure scores, and prioritizes honest coverage over breadth.


## v0.48 note — Distribution-Ready Baseline

v0.48 is a final packaging and clarity pass. It keeps the v0.47 U.S.-centered integrity scope, raw uncapped scores, and price-free live scoring, while simplifying the top description, using the **Edgefield Research** brand label, adding a concise reading guide, and strengthening research-only disclaimer language.

## v0.49 Beta Launch Wrapper

v0.49 adds the lightweight business wrapper needed for private beta distribution while preserving the v0.48 scanner core. It includes a product overview page, beta legal/disclaimer pages, support feedback guidance, a changelog, and expands the Regime Queue Snapshot from 5 assets to 10 assets per bucket.

Core scoring remains U.S.-centered, price-free, raw-score based, and evidence-first.

## v1.0 Beta — Regime + Evidence Release

- Adds a compact Current Macro Regime card using Growth Score and Inflation Score tallies.
- Keeps the scanner price-free and public-source based.
- Adds explicit regime-factor registry logic, a methodology note, a What changed line, and regime export support.
- Does not add source lanes or workflow dependencies.
