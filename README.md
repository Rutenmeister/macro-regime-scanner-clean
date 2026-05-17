# Macro Regime Scanner v0.34 Patch Kit

This is a drop-in patch kit for the next Macro Regime Scanner iteration:

**v0.34 - Explainable Scoring Baseline**

It was created because the live GitHub repo files were not available in this sandbox. The kit is designed to be copied into the existing `macro-regime-scanner-clean` repo and adapted with minimal disruption.

## Contents

```text
config/scoring_rules.json
config/asset_input_map.json
scripts/recompute_live_scores.py
ui/score_audit_panel_snippet.js
data/sample/sample_macro_regime_scanner.json
docs/scoring_engine_methodology.md
docs/v0_34_handoff.md
tests/test_recompute_live_scores.py
```

## Test the kit itself

From this folder:

```bash
python scripts/recompute_live_scores.py \
  --input data/sample/sample_macro_regime_scanner.json \
  --output data/sample/sample_macro_regime_scanner_enriched.json
```

Then inspect:

```bash
cat data/sample/sample_macro_regime_scanner_enriched.json
```

## Apply to the live repo

1. Copy `config/`, `scripts/`, `docs/`, and the useful parts of `ui/` into the repo.
2. Run the scoring script on a copy of the current live data first.
3. Confirm score audits look reasonable.
4. Integrate `renderScoreAudit(asset)` into the asset-card renderer.
5. Paste optional CSS from `SCORE_AUDIT_CSS` into the stylesheet.
6. Validate page render and GitHub Actions refresh.

## Design principles

- Evidence pressure, not buy/sell signals.
- No hype language.
- Missing data does not become neutral.
- Asset-specific directional logic.
- Every score must explain what counted and what did not.
