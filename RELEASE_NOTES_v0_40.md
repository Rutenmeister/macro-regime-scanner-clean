# Release Notes — Macro Regime Scanner v0.40

**Name:** Raw Score History Baseline  
**Starts from:** v0.34 Explainable Trust Layer  
**Core purpose:** remove the +/-10 display cap, repair Regime Queue classification, and prepare the scanner for score-history validation.

## Added

- Uncapped raw net pressure score display.
- Primary pressure buckets based on raw score magnitude.
- Secondary tags for improving/deteriorating/conflicted/freshness/confidence.
- `rawScore`, `displayScore`, `pressureBucket`, `movementTag`, and `scoreScale` fields on assets.
- `scoreChangeLog` summaries per asset.
- Score snapshots under `data/history/`.
- `scripts/validate_score_history.py`.
- `scripts/validate_signal_framework.py` for future optional forward-return validation.
- `data/validation/README.md`.
- Updated methodology and export-brief language.

## Changed

- Scores are no longer clamped to +/-10.
- Regime Queue no longer treats Improving/Deteriorating as primary buckets.
- Exported regime brief now uses raw-score language.
- Refresh orchestrator validates score history after data validation.

## Not changed

- No new live data lanes were added.
- Price data is still excluded from live scoring.
- Existing source-health and release-calendar architecture remains intact.
