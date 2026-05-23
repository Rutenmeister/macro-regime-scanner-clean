# Macro Regime Scanner v1.1 — Full Credibility Hardening

This release builds on the frozen v1.0 Beta / Regime + Evidence Release in a separate package.

## Ten hardening additions

1. Regime card hardening: primary strict regime, sensitivity read, driver line, coverage/freshness status, and disclaimer in one card.
2. Explicit regime factor registry documentation in `config/regime_factor_registry.json`.
3. Regime driver audit expandable inside the regime card.
4. Asset score audit enhanced with asset-specific directional notes and input eligibility summary.
5. Input eligibility visibility: scored/context/display/not-live counts are shown per asset.
6. Asset directional map documentation in `config/asset_directional_map.json`.
7. Source freshness and coverage mini-status directly attached to the regime read.
8. Methodology page added at `docs/methodology_v1_1.md`.
9. Existing score history is used for a compact movement summary and remains ready for fuller historical snapshots.
10. Validation framework file added at `data/validation/regime_validation_framework.json` to define future forward-check tests without claiming predictive proof.

## Non-goals

- No new source lanes.
- No price data added to live scoring.
- No workflow dependency added.
- No extra regimes or blend-state dashboard.
- No claim of investment advice or predictive certainty.
