# v0.26D Deep Variable Extraction Upgrade

This build starts from the frozen v0.25F foundation and deepens existing source lanes without changing the GitHub workflow architecture. The master workflow should continue to run only `scripts/refresh_all_sources.py`.

## Scope

- Treasury: full public par-yield curve, major curve spreads, daily point/spread changes.
- EIA: existing inventory/storage variables plus optional deep variables for refinery utilization, crude production, imports, exports, gasoline product supplied, and distillate product supplied. Optional EIA series failures are recorded in normalized output rather than breaking the whole lane.
- BLS: expanded inflation/labor variables including CPI shelter, CPI energy, CPI food, services inflation, core PPI, labor-force participation, and U-6 unemployment.
- CFTC COT: keeps the upgraded live COT interpretation model; deeper historical percentiles remain a future history-backfill task.
- USDA/NASS: keeps the live scaffold; deeper WASDE/export-sales integration remains a future official-source task because those are not the same as the NASS Quick Stats crop-progress/production endpoint.

## Guardrails

- No price-derived market data.
- No workflow YAML expansion per source.
- No scoring-engine rebuild in this version.
- Optional deep variables can be missing without corrupting the app.
