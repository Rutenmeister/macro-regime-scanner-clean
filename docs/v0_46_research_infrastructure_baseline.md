# Macro Regime Scanner v0.46 — Research Infrastructure Baseline

v0.46 is a five-version jump from the frozen v0.41 Official Release Calendar Hardening baseline. It preserves the v0.40/v0.41 core: uncapped raw pressure scores, repaired Regime Queue buckets, movement/conflict tags, score snapshots, why-score-changed summaries, validation framework, official/official-pattern/estimated calendar confidence labels, source URLs, and release-calendar validation.

## Internal version steps included

### v0.42 — Release Result Fields
Adds `data/release_results.json` with fields for actual, forecast, previous, revision, surprise, unit, release status, and result confidence. This is schema-ready but intentionally does not invent figures when no official/licensed result feed is attached.

### v0.43 — Validation Summary Framework
Adds `data/validation/score_validation_summary.json` and validation scaffolding for future forward-return testing. It currently validates distribution/readiness, not predictive accuracy.

### v0.44 — Source QA / Coverage Scoring
Adds `data/source_quality.json`, lane quality grades, lane quality scores, and asset coverage labels based on counted/context/excluded evidence rows.

### v0.45 — Professional Reports
Adds generated Markdown and HTML reports under `data/reports/`.

### v0.46 — Suite Bridge Export Schema
Adds `data/exports/regime_labels_latest.json` and `.csv` so TradeStream, Capital Trace, and Pathwise can later import regime labels without coupling directly to the UI.

## Trust rule

Null actual/forecast/previous fields mean the app does not have a trusted result feed for that event. Null values must never be interpreted as zero, neutral, or unchanged.

## Freeze criteria

Before freezing v0.46 live:

1. Upload package contents into the repo root.
2. Run Refresh All Public Sources.
3. Confirm workflow green.
4. Confirm the live site loads normally.
5. Confirm release cards show result fields.
6. Confirm source QA renders in Source Health.
7. Confirm export buttons still work.
8. Confirm `data/exports/regime_labels_latest.json` exists.
9. Confirm `data/reports/current_regime_brief.md` exists.

