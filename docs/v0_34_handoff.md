# v0.34 Handoff - Explainable Scoring Baseline

## What changed

This patch adds the foundation for asset-specific score audits:

1. Scoring eligibility statuses: `live_scored`, `live_context`, `display_only`, `not_live`.
2. Asset-specific directional maps for U.S. equities, rates, USD FX, foreign/USD pairs, precious metals, energy, and agriculture.
3. Weight tiers: primary, secondary, contextual, low, excluded.
4. A recompute script that enriches each asset with `scoreAudit`.
5. A UI snippet for rendering expandable score audits.
6. Documentation explaining the methodology and caveats.

## What this does not do yet

- It does not fetch new data sources.
- It does not rewrite the GitHub Actions workflow.
- It does not guarantee perfect macro logic.
- It does not make trade recommendations.
- It does not automatically know every existing input key in the live repo; unmapped keys become display-only until mapped.

## Recommended integration order

1. Copy `config/scoring_rules.json` into the repo.
2. Copy `config/asset_input_map.json` into the repo.
3. Copy `scripts/recompute_live_scores.py` into the repo.
4. Run the script against the current normalized scanner JSON.
5. Inspect the enriched output and confirm each asset has `scoreAudit`.
6. Add the UI snippet to `app.js` or adapt it to the current renderer.
7. Paste the optional CSS into the current stylesheet.
8. Validate GitHub Pages rendering.
9. Run Refresh All Public Sources.
10. Freeze as v0.34 only after layout and refresh are green.

## Example local command

```bash
python scripts/recompute_live_scores.py \
  --input data/macro_regime_scanner.json \
  --output data/macro_regime_scanner.json
```

Safer first test:

```bash
python scripts/recompute_live_scores.py \
  --input data/macro_regime_scanner.json \
  --output data/macro_regime_scanner_v0_34_test.json
```

## Validation checklist

- Homepage renders normally.
- Refresh All Public Sources remains green.
- No live source lane is removed.
- No scaffold/sample row is counted.
- Every asset has `scoreAudit`.
- SPX/Nasdaq logic differs from DXY logic.
- DXY/EURUSD/USDJPY logic differs from equity logic.
- Gold handles rates/inflation/COT nuance.
- WTI prioritizes EIA/COT.
- Wheat/Corn prioritize USDA/NOAA/COT.
- Missing/stale rows are visible as excluded, not scored as neutral.
- Upcoming Reports panel remains wide under the center column.
- Row toggle still hides/shows irrelevant rows.

## Next likely iteration

v0.35 should add history/change tracking:

- store previous score snapshot;
- show score delta by asset;
- add improving/deteriorating/conflict queues;
- explain why a score changed since the last refresh.
