# v0.29 Census Real Economy Lane

This lane adds U.S. Census Bureau real-economy context to Macro Regime Scanner without changing the orchestrator workflow.

## Current variables

- Retail sales: retail and food services
- Housing starts
- Building permits
- New single-family home sales
- Durable goods new orders
- U.S. trade balance: goods and services
- Total business inventories

## Source method

The lane uses stable public time series for Census economic-indicator concepts and writes:

- `data/raw/census/census_macro_compact_audit.json`
- `data/normalized/census_macro.json`

If `CENSUS_API_KEY` is available to the runtime, the fetcher also records lightweight Census EITS API probes in the raw audit file. The normalized observations use stable public series so that one Census category-code/API change does not break the full Refresh All run.

## Pipeline behavior

The lane is enabled through `config/source_pipeline.json`:

```json
{
  "id": "census",
  "enabled": true,
  "sourceId": "CENSUS_PUBLIC",
  "fetch": "scripts/sources/fetch_census_macro.py",
  "apply": "scripts/apply_census_lane.py",
  "requiresSecrets": [],
  "status": "live"
}
```

No GitHub workflow rewrite is required. The existing master workflow runs `scripts/refresh_all_sources.py`.

## Interpretation status

This is a source-lane integration, not a final scoring model. The rows provide real-economy evidence for consumer demand, housing activity, business investment, external balance, and inventories. The later scoring engine should decide which Census inputs are direct, secondary, or context-only for each asset.
