# Macro Regime Scanner v0.34 — Explainable Trust Layer

Starting point: **v0.33.1 Wide Release Calendar**.

This iteration intentionally preserves the working v0.33.1 app shape, live-source stack, row toggle, and wide center-column upcoming reports panel. The goal is not to add more data lanes. The goal is to raise trust, explainability, and commercial readability from the existing data.

## What changed

### 1. Regime Queue Snapshot

A new panel above the main evidence queue groups assets into research-triage buckets:

- Strong positive pressure
- Strong negative pressure
- Conflicted / transition
- Improving
- Deteriorating
- Low evidence / avoid

This turns the terminal from a long table into a faster “what deserves attention first?” workflow.

### 2. Stronger score audit panel

Open any asset row to see a larger asset-detail audit:

- headline pressure read
- score, confidence, and conflict
- counted rows
- context-only rows
- excluded rows
- coverage percentage
- positive and negative contribution totals
- top positive drivers
- top negative drivers
- why it changed versus the prior score
- what the score does not prove
- context examples
- excluded examples

The purpose is to answer: **what evidence counted, what did not count, and why?**

### 3. Trust guide

The left sidebar now includes a short guide explaining that the scanner is not a buy/sell signal, that scores rank public-source pressure evidence, and that green/red should be interpreted through alignment, conflict, freshness, and change.

### 4. Export Current Regime Brief

The sidebar now has an export button that creates a markdown brief containing:

- strongest positive pressure assets
- strongest negative pressure assets
- conflicted assets
- largest score changes
- source health summary
- upcoming tracked reports
- caveats

This is designed to make the terminal useful outside the UI as a shareable research snapshot.

### 5. Safer caveat language

Each asset audit includes a “What this does not prove” section. It clarifies that the score does not predict immediate price movement, does not replace trade setup confirmation, and does not account for unexpected news shocks.

## Files changed

- `index.html`
- `app.js`
- `style.css`
- `README.md`
- `docs/v0_34_explainable_trust_layer.md`

## Files intentionally preserved

- Existing public-source fetch/apply scripts
- Existing orchestrator workflow pattern
- Existing data structure
- Existing release calendar generation
- Existing row toggle behavior
- Existing v0.32 live-weighted scoring script

## Validation run

From repo root:

```bash
node --check app.js
python scripts/recompute_live_scores.py
python scripts/validate_data.py
```

Expected result:

```text
Recomputed live weighted scores for 49 assets.
VALIDATION PASSED: 49 assets
```

## Freeze condition

Freeze only after:

- GitHub Pages renders normally.
- `data/macro_regime_scanner.json` loads.
- `data/release_calendar.json` loads or fails gracefully.
- Regime Queue Snapshot renders above the evidence queue.
- Asset rows still open and close.
- Score audits render inside expanded rows.
- Export scanner JSON works.
- Export Current Regime Brief works.
- Refresh All Public Sources remains green.

If those pass, this can be frozen as:

**Macro Regime Scanner v0.34 — Explainable Trust Layer**
