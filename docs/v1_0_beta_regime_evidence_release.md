# v1.0 Beta Regime + Evidence Release

## Purpose

The v1.0 beta finish adds a concise top-level macro regime read without changing the scanner's core asset scoring architecture.

The feature answers:

> What broad growth/inflation regime does the current public-source factor evidence imply?

The asset queue then answers:

> Which markets are most pressured by that regime and by other source-lane evidence?

## Four-regime model

- **Goldilocks**: Growth Score positive, Inflation Score negative.
- **Reflation**: Growth Score positive, Inflation Score positive.
- **Stagflation**: Growth Score negative, Inflation Score positive.
- **Deflation**: Growth Score negative, Inflation Score negative.

## Score construction

The regime card uses explicit live-factor tallies from the already-loaded scanner data.

- Growth rows feed the Growth Score.
- Inflation, rates, policy, energy, and agriculture rows feed the Inflation Score.
- Price is not used.
- Missing data is not treated as neutral.
- Candidate, display-only, not-live, and zero-score rows do not drive the regime score.

The scores are not probabilities. They are evidence-pressure tallies inside this scanner.

## Why explicit registry matters

The first working regime card used broader text matching. v1.0 beta keeps the UI simple but makes the logic more defensible by using an explicit factor-name registry in `app.js`.

Examples:

- CPI/PPI/PCE pressure → Inflation Score.
- GDP, retail sales, labor → Growth Score.
- Credit spreads and financial conditions → Growth Score.
- Treasury yields, real yields, breakevens, policy rates → Inflation/policy pressure.
- Energy and agriculture balance rows → Inflation/physical supply pressure.

## Boundaries

The regime card does not override asset scores. It summarizes the macro backdrop. Asset-specific pressure, conflicts, freshness, and caveats still need to be read in the evidence queue.


## Sensitivity read polish

The current regime card now keeps one primary strict regime while optionally showing a compact sensitivity read when the growth or inflation axis has mixed evidence. This keeps the headline decisive while acknowledging that a broader interpretation may still fit nearby macro debate, especially between Stagflationary Pressure and Inflationary Growth / Reflation.
