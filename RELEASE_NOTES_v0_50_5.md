# Macro Regime Scanner v0.50.5 — Real Quad Tally Fix

This iteration keeps the Growth / Inflation Regime panel simple and honest.

## What changed

- Keeps only four regimes: Goldilocks, Reflation, Stagflation, and Deflation.
- Keeps price out of the regime calculation.
- Calculates Growth Score and Inflation Score from normalized official/public-source macro observations, not from asset reactions.
- Derives the regime label directly from the signs of those two scores.
- Fails validation if an axis says positive or negative while its score is zero.
- Removes the broken positive-zero behavior.

## Product rule

No fake positive labels. No positive score zero. The regime label must come from the real signed tally.
