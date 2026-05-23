# Macro Regime Scanner v1.1.1 — Strict/Broad Regime Read + Driver Dedup Fix

This patch keeps the v1.1 credibility-hardening architecture and makes two small credibility fixes:

- Deduplicates regime drivers before scoring and rendering so the same macro driver does not appear twice in the regime audit.
- Adds a separate broad significance-tier regime read next to the strict primary read.

## Strict vs broad

- Strict read: tighter live-factor count from primary/secondary/contextual eligible rows.
- Broad significance read: uses the same public-source regime registry, but weights eligible live factors by significance tier so lower-tier context can influence the read without overpowering primary evidence.

The product still shows one primary regime, and the broad read is framed as context, not a second headline signal.

No new sources, no workflow changes, no price inputs, and no trade-signal framing were added.
