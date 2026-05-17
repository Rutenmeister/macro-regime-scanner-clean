# v0.33 Release Calendar + Row Applicability Toggle

## Purpose

v0.33 adds two prototype usability upgrades on top of the v0.32 scoring rebuild:

1. **Evidence row visibility toggle**
   - Default expanded tables hide rows that are clearly non-applicable, display-only, candidate, sample/prototype, or not-live.
   - The sidebar toggle shows the full audit table when deeper inspection is needed.
   - Live-scored and live-context rows stay visible by default.

2. **Upcoming report calendar**
   - `scripts/generate_release_calendar.py` writes `data/release_calendar.json` during refresh.
   - The sidebar shows the next report releases/watch times for tracked lanes.
   - Times are shown in Eastern Time.

## Important boundary

This is a release-watch panel, not a fully parsed official calendar system yet. Entries are rule-based using standard release patterns, and estimated items are labeled as estimated. Official source calendars remain controlling when agencies change dates because of holidays, shutdowns, or revisions.

## Files changed

- `index.html`
- `app.js`
- `style.css`
- `scripts/generate_release_calendar.py`
- `scripts/refresh_all_sources.py`
- `data/release_calendar.json`

## Workflow impact

No GitHub workflow YAML change should be required if the workflow already runs:

```text
python scripts/refresh_all_sources.py
```

The orchestrator now runs the calendar generator after score recomputation and before validation.
