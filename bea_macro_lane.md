# v0.27 BEA Macro Lane

This build adds a BEA macro lane on top of the frozen v0.26D.1 deep extraction baseline.

## Purpose

The BEA lane adds official growth and PCE macro evidence to the scanner without changing the master GitHub workflow. The existing orchestrator reads `config/source_pipeline.json` and runs enabled lanes.

## Source

- Source: U.S. Bureau of Economic Analysis API
- Required secret: `BEA_API_KEY`
- Raw/audit output: `data/raw/bea/bea_macro_compact_audit.json`
- Normalized output: `data/normalized/bea_macro.json`

## Initial target observations

The fetcher queries BEA NIPA tables and extracts matching line descriptions for:

- Real GDP growth
- PCE inflation pressure
- Core PCE inflation pressure
- Real personal consumption growth
- Personal income growth, if available from the optional table
- Personal saving rate, if available from the optional table

Missing optional observations are recorded in the audit output and are not faked.

## Applied evidence rows

The apply script adds BEA rows to all assets with asset-specific relevance and effect language:

- Rates / USD: primary growth and PCE policy pressure context
- Equities / credit: growth support vs inflation/rate pressure
- Precious metals: growth/rates/PCE mixed macro context
- Energy / broad commodities: growth-demand and inflation context
- Crops: mostly contextual macro demand/inflation background

## Workflow behavior

No GitHub workflow rewrite is required beyond the existing orchestrator workflow:

```yaml
run: python scripts/refresh_all_sources.py
```

To activate the BEA lane, add the `BEA_API_KEY` repository secret and run **Refresh All Public Sources**.
