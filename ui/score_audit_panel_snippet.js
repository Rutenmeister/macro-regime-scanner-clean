/*
Macro Regime Scanner v0.34 - Score Audit UI Snippet

Use this if the current app already renders asset cards from JSON.
Expected asset fields after running scripts/recompute_live_scores.py:
  asset.scoreAudit
  asset.pressureLabel
  asset.confidence
  asset.conflict

Minimal integration idea:
  card.innerHTML += renderScoreAudit(asset);
*/

function fmtContribution(value) {
  const n = Number(value || 0);
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}`;
}

function renderDriverList(title, drivers, emptyText) {
  const rows = (drivers || []).map(d => `
    <li>
      <span class="audit-driver-label">${d.label || d.inputKey}</span>
      <span class="audit-driver-score">${fmtContribution(d.contribution)}</span>
      <small>${d.reason || ''}</small>
    </li>
  `).join('');

  return `
    <section class="score-audit-section">
      <h4>${title}</h4>
      <ul class="score-audit-list">${rows || `<li class="muted">${emptyText}</li>`}</ul>
    </section>
  `;
}

function renderScoreAudit(asset) {
  const audit = asset.scoreAudit || {};
  const conflicts = (audit.mainConflicts || []).map(c => `
    <li>
      <span class="audit-driver-label">${c.label || 'Conflict'}</span>
      <small>${c.detail || ''}</small>
    </li>
  `).join('');

  const caveats = (audit.caveats || [
    'This is evidence pressure, not a trade signal.',
    'Missing or stale evidence is excluded, not treated as neutral.'
  ]).map(c => `<li>${c}</li>`).join('');

  return `
    <details class="score-audit-card">
      <summary>
        <span>Score Audit</span>
        <span class="audit-summary-pill">${audit.label || asset.pressureLabel || 'Mixed live evidence'}</span>
      </summary>

      <div class="score-audit-grid">
        <div class="audit-stat"><b>${fmtContribution(audit.netScore)}</b><span>Net pressure</span></div>
        <div class="audit-stat"><b>${audit.confidence || asset.confidence || 'Unknown'}</b><span>Confidence</span></div>
        <div class="audit-stat"><b>${audit.countedRows ?? 0}</b><span>Counted rows</span></div>
        <div class="audit-stat"><b>${audit.contextRows ?? 0}</b><span>Context rows</span></div>
        <div class="audit-stat"><b>${audit.excludedRows ?? 0}</b><span>Excluded rows</span></div>
        <div class="audit-stat"><b>${audit.conflictLevel || 'Low'}</b><span>Conflict</span></div>
      </div>

      ${renderDriverList('Top positive drivers', audit.topPositiveDrivers, 'No positive scored drivers.')}
      ${renderDriverList('Top negative drivers', audit.topNegativeDrivers, 'No negative scored drivers.')}

      <section class="score-audit-section">
        <h4>Main conflicts</h4>
        <ul class="score-audit-list">${conflicts || '<li class="muted">No major internal conflict detected.</li>'}</ul>
      </section>

      <section class="score-audit-section caveats">
        <h4>What this does not prove</h4>
        <ul>${caveats}</ul>
      </section>
    </details>
  `;
}

/* Optional CSS to paste into style.css */
const SCORE_AUDIT_CSS = `
.score-audit-card { margin-top: 10px; border: 1px solid rgba(148,163,184,.24); border-radius: 12px; padding: 10px; background: rgba(15,23,42,.42); }
.score-audit-card summary { cursor: pointer; display:flex; justify-content:space-between; gap:10px; align-items:center; font-size: 12px; letter-spacing:.06em; text-transform:uppercase; }
.audit-summary-pill { border:1px solid rgba(148,163,184,.28); border-radius:999px; padding:3px 8px; opacity:.9; }
.score-audit-grid { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:8px; margin:12px 0; }
.audit-stat { border:1px solid rgba(148,163,184,.18); border-radius:10px; padding:8px; }
.audit-stat b { display:block; font-size:14px; }
.audit-stat span { display:block; font-size:10px; opacity:.72; text-transform:uppercase; letter-spacing:.05em; }
.score-audit-section { margin-top:12px; }
.score-audit-section h4 { margin:0 0 6px; font-size:11px; text-transform:uppercase; letter-spacing:.08em; opacity:.78; }
.score-audit-list { list-style:none; margin:0; padding:0; display:grid; gap:6px; }
.score-audit-list li { display:grid; gap:2px; border-top:1px solid rgba(148,163,184,.12); padding-top:6px; }
.audit-driver-label { font-size:12px; }
.audit-driver-score { font-size:12px; font-variant-numeric: tabular-nums; opacity:.9; }
.score-audit-list small, .caveats li, .muted { font-size:11px; opacity:.7; }
@media (max-width: 640px) { .score-audit-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } }
`;
