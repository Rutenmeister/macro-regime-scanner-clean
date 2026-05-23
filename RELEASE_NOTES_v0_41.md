# Macro Regime Scanner v0.41 — Official Release Calendar Hardening

Starting baseline: **v0.40 Raw Score History Baseline**.

## Purpose

v0.41 hardens the Upcoming Tracked Reports module so estimated release dates do not look official.

The core scanner remains unchanged:
- raw uncapped net pressure scores,
- repaired Regime Queue primary buckets,
- score snapshots,
- why-score-changed summaries,
- validation framework,
- exportable regime brief.

## What changed

- Rebuilt `scripts/generate_release_calendar.py`.
- Added `calendarConfidence` to every calendar event:
  - `official`
  - `official-pattern`
  - `estimated`
- Added `sourceUrl` to calendar rows.
- Added explicit 2026 federal-holiday protection for Treasury daily curve rows.
- Removed the known false May 20 Retail Sales estimate.
- Fixed PCE / Personal Income and Outlays to May 28, 2026.
- Added official/confirmed near-term entries for:
  - Census Housing Starts / Building Permits — May 21, 2026
  - BEA GDP Second Estimate / Corporate Profits — May 28, 2026
  - BEA Personal Income and Outlays / PCE — May 28, 2026
  - Census Durable Goods — May 28, 2026
  - Census Retail Sales next release — June 17, 2026
- Added `scripts/validate_release_calendar.py`.
- Updated `app.js` release-calendar rendering to show confidence badges.
- Updated `style.css` for release-calendar confidence labels.
- Added an updated `.github/workflows/refresh-all-public-sources.yml` that runs calendar validation after refresh.

## Important caveat

This is **not** yet a full economic-calendar API integration. It is a hardened hybrid:

1. Official date overrides for known official near-term reports.
2. Official-pattern recurring events for weekly/daily releases.
3. Estimated reminders only when official data is not embedded yet.

Estimated entries are now visibly marked and should not be treated as confirmed.

## Validation performed

```text
python scripts/generate_release_calendar.py
python scripts/validate_release_calendar.py
node --check app.js
python scripts/validate_data.py
python scripts/validate_score_history.py
python scripts/validate_signal_framework.py
```

All applicable validations passed in the package environment.

## Freeze condition

Do not freeze v0.41 until:

1. Files are uploaded to `macro-regime-scanner-clean`.
2. Refresh All Public Sources workflow is updated and green.
3. The live site shows calendar confidence badges.
4. The release calendar no longer shows:
   - Retail Sales on May 20, 2026
   - PCE on May 23, 2026
   - Treasury daily curve on Memorial Day May 25, 2026
5. Export Current Regime Brief still works.
