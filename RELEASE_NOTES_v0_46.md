# Release Notes — Macro Regime Scanner v0.46 Research Infrastructure Baseline

## Summary

v0.46 is a five-version integrated upgrade from v0.41. It does not add new source lanes. It strengthens the research infrastructure around the existing scanner.

## Added

- v0.42 release-result schema with actual/forecast/previous/revision/surprise fields.
- v0.43 score validation summary framework.
- v0.44 source-lane QA and asset coverage scoring.
- v0.45 professional Markdown/HTML report generation.
- v0.46 suite bridge exports for TradeStream, Capital Trace, and Pathwise.
- Updated UI support for release-result fields in Upcoming Tracked Reports.
- Updated Source Health UI with QA grades and scores.
- Updated workflow steps for the new v0.46 scripts.

## Preserved

- v0.40 uncapped raw pressure scores.
- Repaired Regime Queue buckets.
- Movement/conflict tags.
- Score snapshots and why-score-changed summaries.
- v0.41 official release calendar hardening.
- Calendar confidence labels and source links.
- Release-calendar validation.

## Important limitation

The release-result schema is ready for actual/forecast/previous figures, but v0.46 does not invent values. Forecast and consensus data may require a third-party or licensed data source. Null values are explicitly shown as unavailable.

