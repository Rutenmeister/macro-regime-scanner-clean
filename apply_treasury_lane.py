# Macro Regime Scanner v0.40 — Raw Score History Baseline

v0.40 starts from the frozen v0.34 Explainable Trust Layer and completes the requested ordered upgrade path without adding new data lanes.

## What changed

1. **Uncapped raw score display**
   - The old +/-10 display cap is removed.
   - `asset.score`, `asset.rawScore`, and `asset.displayScore` all show uncapped raw net pressure.
   - Larger absolute values mean more weighted public-source evidence, not guaranteed price movement.

2. **Regime Queue repair**
   - Primary buckets are now score states: extreme/strong/moderate positive, mixed/neutral, moderate/strong/extreme negative, and low evidence.
   - Improving, deteriorating, conflicted, freshness, and confidence are secondary tags.
   - This prevents assets like USD or 10Y from being hidden inside “Improving” instead of appearing in strong positive pressure.

3. **Score audit math cleanup**
   - Expanded rows show counted rows, context rows, excluded rows, positive pressure, negative pressure, net raw score, and top driver contribution values.
   - The score audit explicitly says the score scale is `uncapped_raw_net_pressure`.

4. **Score history snapshots**
   - `scripts/recompute_live_scores.py` now writes snapshots to `data/history/`.
   - `data/history/latest.json` always stores the latest snapshot.
   - These snapshots support future “why score changed” and validation work.

5. **Why-score-changed summaries**
   - Each asset now gets a `scoreChangeLog` object.
   - If a prior snapshot exists, it compares current raw score against the previous saved score.

6. **Optional validation framework**
   - Added `scripts/validate_signal_framework.py`.
   - It expects optional separate price/return data in `data/validation/forward_returns.csv`.
   - Price data is never fed into the live score; it is only for later research validation.

7. **Report/methodology polish**
   - Exported brief language now refers to raw pressure scores.
   - The methodology notes clarify that missing data is not neutral and scores are not trading signals.

## Why this matters

The old capped display could show two assets as `+10` even if one was barely above the cap and another was far stronger underneath. v0.40 makes the score more honest by displaying the raw net pressure directly.

## Freeze criteria

Before freezing v0.40, confirm:

```text
node --check app.js
python scripts/recompute_live_scores.py
python scripts/validate_data.py
python scripts/validate_score_history.py
python scripts/validate_signal_framework.py
```

Then deploy and visually confirm:

- raw scores display in the main queue;
- Regime Queue buckets are not empty when strong assets exist;
- movement appears as tags rather than buckets;
- expanded score audits render;
- Export Current Regime Brief works;
- release calendar still renders wide below the center column.
