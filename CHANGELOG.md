
## v0.50.5 — Real Quad Tally Fix

- Rebuilt the Growth / Inflation Regime calculation so Growth Score and Inflation Score are real signed tallies from normalized official/public-source macro observations.
- The regime label now comes directly from the signs of those two scores.
- Validation fails if an axis label says positive or negative while the score is zero.
- Removed the broken positive/score-zero behavior.
- Kept the main scanner, raw asset scores, no-price scoring, and U.S.-centered scope unchanged.

## v0.50.5 — Simple Four-Quad Regime Display Map

- Replaces the prior quad experiment with a simple four-regime model.
- Growth and inflation axes resolve to positive or negative only.
- Current regime is always one of Goldilocks, Reflation, Stagflation, or Deflation.
- Removes quad confidence, and in-between regime outputs.
- Keeps price out of live scoring and leaves the core scanner unchanged.

## v0.49 — Beta Launch Wrapper

- Added landing page, legal pages, support/feedback structure, and changelog.
- Expanded Regime Queue Snapshot from 5 to 10 assets per bucket.

## v0.48 — Distribution-Ready Baseline

- Added Edgefield Research branding.
- Simplified product description and how-to-read language.
- Strengthened research-only disclaimer/footer and report wording.

## Earlier baselines

- v0.47: U.S.-Centered Integrity Baseline.
- v0.46: Research Infrastructure Baseline.
- v0.41: Official Release Calendar Hardening.
- v0.40: Raw Score History Baseline.
- v0.34: Explainable Trust Layer.
