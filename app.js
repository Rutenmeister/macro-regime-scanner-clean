let ASSETS = [];
let DATA_NOTICE = 'Loading data/macro_regime_scanner.json';
let DATA_MODE = 'public-source-prototype-json';
let SOURCE_STATUS = {};
let RELEASE_CALENDAR = null;
let RELEASE_RESULTS = null;
let SOURCE_QUALITY = null;
let VALIDATION_SUMMARY = null;
let REGIME_BRIDGE = null;
let MACRO_QUAD = null;
let SHOW_ALL_ROWS = false;

let expanded = new Set();
let selectedId = 'GOLD';
const $ = id => document.getElementById(id);
function esc(v){ return String(v ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function oneDecimal(n){ return Number(n||0).toFixed(1); }
function signed(n){ const x=Number(n||0); return x>0?'+'+oneDecimal(x):oneDecimal(x); }
function fmtScore(n){ if(n===null||n===undefined) return 'MISS'; const x=Number(n||0); const text=Number.isInteger(x)?String(x):x.toFixed(1); return x>0?'+'+text:text; }
function scoreClass(n){ return n>0?'score-pos':n<0?'score-neg':'score-neu'; }
function statusClass(score){ if(score===null||score===undefined) return 'missing'; if(score>0) return 'support'; if(score<0) return 'pressure'; return 'neutral'; }
function change(a){ const d=(a.score||0)-(a.previousScore||0); return fmtScore(d); }
function freshnessRank(f){ return ({Fresh:7,Sample:5,Mixed:4,Aging:3,Stale:2})[f]||4; }
function conflictRank(c){ return ({Low:1,Medium:2,High:3})[c]||2; }
function biasType(a){ const b=String(a.bias||''); if(b.includes('Positive')||b.includes('Bullish')) return 'Bullish'; if(b.includes('Negative')||b.includes('Bearish')) return 'Bearish'; return 'Neutral / Mixed'; }
function setupFilters(){ const toggle=$('showAllRowsToggle'); if(toggle){ toggle.checked = SHOW_ALL_ROWS; toggle.addEventListener('change', e=>{ SHOW_ALL_ROWS = e.target.checked; renderAll(false); }); } renderReleaseCalendar(); const classes=['All Asset Classes',...Array.from(new Set(ASSETS.map(a=>a.assetClass)))]; $('assetClass').innerHTML=classes.map(c=>`<option>${c}</option>`).join(''); const fresh=['All',...Array.from(new Set(ASSETS.map(a=>a.freshness).filter(Boolean)))]; $('freshFilter').innerHTML=fresh.map(f=>`<option>${f}</option>`).join(''); updateSubgroups(); renderSourcePills(); renderSourceHealth(); }
function updateSubgroups(){ const cls=$('assetClass').value; const list=cls==='All Asset Classes'?ASSETS:ASSETS.filter(a=>a.assetClass===cls); const subs=['All Subgroups',...Array.from(new Set(list.map(a=>a.subgroup)))]; $('subgroup').innerHTML=subs.map(s=>`<option>${s}</option>`).join(''); }
function getRows(){ let rows=[...ASSETS]; const q=$('searchBox').value.trim().toLowerCase(); const uni=$('universe').value; const cls=$('assetClass').value; const sub=$('subgroup').value; const bias=$('biasFilter').value; const cf=$('conflictFilter').value; const fr=$('freshFilter').value; if(q) rows=rows.filter(a=>(a.symbol+' '+a.name+' '+a.assetClass+' '+a.subgroup).toLowerCase().includes(q)); if(uni==='Watchlist Only') rows=rows.filter(a=>a.watchlist); if(uni==='Rankable Markets') rows=rows.filter(a=>a.rankType==='rankable'); if(uni==='Regime Anchors') rows=rows.filter(a=>a.rankType==='anchor'); if(cls!=='All Asset Classes') rows=rows.filter(a=>a.assetClass===cls); if(sub&&sub!=='All Subgroups') rows=rows.filter(a=>a.subgroup===sub); if(bias!=='All') rows=rows.filter(a=>biasType(a)===bias); if(cf!=='All') rows=rows.filter(a=>a.conflict===cf); if(fr!=='All') rows=rows.filter(a=>a.freshness===fr); const sort=$('sortMode').value; rows.sort((a,b)=>{ if(sort==='bullish') return b.score-a.score; if(sort==='bearish') return a.score-b.score; if(sort==='confidence') return b.confidence-a.confidence; if(sort==='conflict') return conflictRank(b.conflict)-conflictRank(a.conflict); if(sort==='freshest') return freshnessRank(b.freshness)-freshnessRank(a.freshness); if(sort==='stalest') return freshnessRank(a.freshness)-freshnessRank(b.freshness); if(sort==='improvement') return ((b.score-b.previousScore)-(a.score-a.previousScore)); if(sort==='deterioration') return ((a.score-a.previousScore)-(b.score-b.previousScore)); if(sort==='riskOn') return (b.score + (b.subgroup.includes('Equity')?2:0)) - (a.score + (a.subgroup.includes('Equity')?2:0)); if(sort==='riskOff') return (conflictRank(b.conflict)*2 + (b.assetClass.includes('Volatility')?3:0)) - (conflictRank(a.conflict)*2 + (a.assetClass.includes('Volatility')?3:0)); if(sort==='watchlist') return Number(b.watchlist)-Number(a.watchlist) || b.score-a.score; return b.score-a.score; }); return rows.slice(0, Number($('rowLimit').value)); }

function sourceLabel(status){
  const v = String(status || 'candidate').toLowerCase();
  if(v.includes('live')) return 'Live';
  if(v.includes('workflow')) return 'Workflow ready';
  if(v.includes('candidate')) return 'Candidate';
  if(v.includes('pending')) return 'Pending';
  return status || 'Candidate';
}
function sourceHealthClass(status){
  const v = String(status || '').toLowerCase();
  if(v.includes('live')) return 'source-live';
  if(v.includes('workflow')) return 'source-ready';
  if(v.includes('candidate')) return 'source-candidate';
  return 'source-candidate';
}
function renderSourcePills(){
  const box = $('sourcePills');
  if(!box) return;
  const items = Object.entries(SOURCE_STATUS || {});
  const treasury = items.find(([id]) => id === 'TREASURY_OFFICIAL');
  const liveCount = items.filter(([,s]) => String(s.status || '').toLowerCase().includes('live')).length;
  const candidateCount = items.filter(([,s]) => String(s.status || '').toLowerCase().includes('candidate')).length;
  box.innerHTML = `<span class="pill">Reads: data/macro_regime_scanner.json</span><span class="pill">Live lanes: ${liveCount}</span><span class="pill">Candidates: ${candidateCount}</span>${treasury ? `<span class="pill">Treasury: ${sourceLabel(treasury[1].status)}${treasury[1].latest_date ? ' · ' + treasury[1].latest_date : ''}</span>` : ''}`;
}
function renderSourceHealth(){
  const list = $('sourceHealthList');
  if(!list) return;
  const items = Object.entries(SOURCE_STATUS || {});
  if(!items.length){
    list.innerHTML = '<div class="text-slate-500">No source status data loaded yet.</div>';
    return;
  }
  const order = ['TREASURY_OFFICIAL','CFTC_COT','EIA_OPEN_DATA','USDA_PUBLIC','BLS_PUBLIC','BEA_PUBLIC','FED_FRED_SELECTED','FEDERAL_RESERVE_PUBLIC','CENSUS_PUBLIC','FINANCIAL_STRESS_FRED','NOAA_NWS','NOAA_NWS_PUBLIC','FRED_SELECTED'];
  items.sort(([a],[b]) => (order.indexOf(a) === -1 ? 999 : order.indexOf(a)) - (order.indexOf(b) === -1 ? 999 : order.indexOf(b)) || a.localeCompare(b));
  list.innerHTML = items.map(([id,s]) => {
    const label = sourceLabel(s.status);
    const cls = sourceHealthClass(s.status);
    const latest = s.latest_date ? `<div class="text-[11px] text-slate-500 mt-1">Latest: ${s.latest_date}</div>` : '';
    const note = s.note || s.production_note || '';
    const q = sourceQualityFor(id);
    const qLine = q ? `<div class="text-[11px] text-slate-500 mt-1">QA: ${esc(q.qualityGrade)} · ${q.qualityScore}/100</div>` : '';
    return `<div class="source-health-row rounded-xl p-2 ${cls}"><div class="flex items-center justify-between gap-2"><span class="font-semibold text-slate-200">${id.replaceAll('_',' ')}</span><span class="source-dot-label">${label}</span></div>${latest}${qLine}<div class="text-[11px] text-slate-400 mt-1 leading-snug">${note}</div></div>`;
  }).join('');
}

function driverPills(list, emptyText){
  const items=(list||[]).slice(0,5);
  if(!items.length) return `<span class="pill">${emptyText}</span>`;
  return items.map(d=>`<span class="pill">${esc(d.name||'driver')}: ${signed(d.contribution)}</span>`).join('');
}
function exampleList(list, emptyText){
  const items=(list||[]).slice(0,4);
  if(!items.length) return `<div class="text-xs text-slate-500">${emptyText}</div>`;
  return `<ul class="audit-list">${items.map(x=>`<li><span class="text-slate-200">${esc(x.name||'row')}</span><span class="text-slate-500"> · ${esc(x.reason||x.sourceLane||'audit context')}</span></li>`).join('')}</ul>`;
}
function assetChangeSummary(asset){
  const delta=(asset.score||0)-(asset.previousScore||0);
  if(delta>0) return `${asset.symbol} improved by ${signed(delta)} since the previous score snapshot.`;
  if(delta<0) return `${asset.symbol} deteriorated by ${signed(delta)} since the previous score snapshot.`;
  return `${asset.symbol} is unchanged versus the previous score snapshot.`;
}
function caveatText(asset){
  const bucket=asset.scoreAudit?.assetBucket || asset.assetClass || 'asset';
  return `This pressure read does not predict immediate price movement, does not replace trade setup confirmation, and does not account for unexpected news shocks. Coverage is strongest where live public-source rows exist for this ${esc(bucket)} bucket; missing rows are not treated as neutral.`;
}
function scoreAuditPanel(asset){
  const a = asset.scoreAudit;
  if(!a) return `<div class="soft-card rounded-2xl p-3 mb-4 text-xs text-slate-400">No score audit object found for this asset. Run <code>python scripts/recompute_live_scores.py</code> after refresh.</div>`;
  const counted=a.countedRows||0, context=a.contextRows||0, excluded=a.excludedRows||0;
  const total=counted+context+excluded;
  const coverage = total ? Math.round(((counted+context)/total)*100) : 0;
  const method=esc(a.methodVersion||'live scoring');
  return `<div class="score-audit-shell soft-card rounded-2xl p-4 mb-4">
    <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
      <div><div class="tiny-label">Asset detail / score audit · ${method}</div><h3 class="text-lg font-semibold text-slate-100 mt-1">${esc(asset.symbol)} · ${esc(asset.bias || 'Evidence pressure')}</h3><p class="text-xs text-slate-400 mt-1">${esc(asset.quick || '')}</p></div>
      <div class="text-right"><div class="metric-value text-3xl font-bold ${scoreClass(a.finalScore||asset.score||0)}">${fmtScore(a.finalScore ?? asset.score ?? 0)}</div><div class="score-scale-note">uncapped raw pressure</div><div class="text-[11px] text-slate-500">${esc(asset.confidence)}% confidence · ${esc(asset.conflict)} conflict · ${esc(asset.movementTag||'Stable')}</div></div>
    </div>
    <div class="audit-grid mt-4">
      <div><span class="text-slate-500">Counted rows</span><div class="metric-value">${counted}</div></div>
      <div><span class="text-slate-500">Context rows</span><div class="metric-value">${context}</div></div>
      <div><span class="text-slate-500">Excluded rows</span><div class="metric-value">${excluded}</div></div>
      <div><span class="text-slate-500">Coverage</span><div class="metric-value">${coverage}%</div></div>
      <div><span class="text-slate-500">Positive pressure</span><div class="metric-value score-pos">${signed(a.positiveContribution)}</div></div>
      <div><span class="text-slate-500">Negative pressure</span><div class="metric-value score-neg">${signed(a.negativeContribution)}</div></div>
    </div>
    <div class="grid xl:grid-cols-2 gap-3 mt-4">
      <div class="audit-box"><div class="tiny-label">Top positive drivers</div><div class="flex flex-wrap gap-2 mt-2">${driverPills(a.topPositiveDrivers,'No positive scored driver')}</div></div>
      <div class="audit-box"><div class="tiny-label">Top negative drivers</div><div class="flex flex-wrap gap-2 mt-2">${driverPills(a.topNegativeDrivers,'No negative scored driver')}</div></div>
      <div class="audit-box"><div class="tiny-label">Why it changed</div><p class="text-xs text-slate-400 mt-2">${esc(assetChangeSummary(asset))}</p></div>
      <div class="audit-box"><div class="tiny-label">What this does not prove</div><p class="text-xs text-slate-400 mt-2 leading-relaxed">${caveatText(asset)}</p></div>
      <div class="audit-box"><div class="tiny-label">Context examples</div>${exampleList(a.contextExamples,'No context-only examples in audit.')}</div>
      <div class="audit-box"><div class="tiny-label">Excluded examples</div>${exampleList(a.excludedExamples,'No excluded examples in audit.')}</div>
    </div>
  </div>`;
}

function factorAppliesToAsset(f){
  const role = String(f.scoreRole || '').toLowerCase();
  const freshness = String(f.freshness || '').toLowerCase();
  const source = String(f.source || '').toLowerCase();
  const derived = String(f.derived || '').toLowerCase();
  const relevance = String(f.relevance || '').toLowerCase();
  if(role === 'live_scored' || role === 'live_context') return true;
  if(relevance === 'not applicable' || relevance === 'low relevance') return false;
  if(source.includes('prototype') || source.includes('sample') || source.includes('candidate')) return false;
  if(derived.includes('prototype') || derived.includes('sample') || derived.includes('candidate')) return false;
  if(freshness.includes('prototype') || freshness.includes('sample') || freshness.includes('candidate')) return false;
  if(freshness.includes('fresh') || freshness.includes('live')) return true;
  return false;
}
function filteredFactorsForAsset(asset){
  const factors = asset.factors || [];
  return SHOW_ALL_ROWS ? factors : factors.filter(factorAppliesToAsset);
}
function rowRolePill(f){
  const role = String(f.scoreRole || '').toLowerCase();
  if(role === 'live_scored') return '<span class="row-role row-role-scored">Scored</span>';
  if(role === 'live_context') return '<span class="row-role row-role-context">Context</span>';
  if(role === 'display_only') return '<span class="row-role row-role-display">Display</span>';
  if(role === 'not_live') return '<span class="row-role row-role-muted">Not live</span>';
  if(factorAppliesToAsset(f)) return '<span class="row-role row-role-context">Applies</span>';
  return '<span class="row-role row-role-muted">Hidden default</span>';
}

function axisClass(label){
  if(label === 'positive') return 'score-pos';
  if(label === 'negative') return 'score-neg';
  return 'score-neu';
}
function axisWord(label, positiveWord='positive', negativeWord='negative'){
  return label === 'negative' ? negativeWord : positiveWord;
}
function driverListForQuad(list, emptyText){
  const items=(list||[]).slice(0,4);
  if(!items.length) return `<span class="pill">${emptyText}</span>`;
  return items.map(d=>`<span class="pill">${esc(d.name||'driver')}: ${signed(d.contribution||0)}</span>`).join('');
}
function renderMacroQuadSnapshot(){
  const box=$('macroQuadSnapshot');
  if(!box) return;
  if(!MACRO_QUAD){
    box.innerHTML = `<div class="tiny-label">Growth / Inflation Regime</div><div class="text-sm text-slate-400 mt-1">Regime snapshot not loaded yet. Run the refresh workflow.</div>`;
    return;
  }
  const g=MACRO_QUAD.growth || {};
  const i=MACRO_QUAD.inflation || {};
  const state=MACRO_QUAD.currentState || 'Reflation';
  const subtitle=MACRO_QUAD.subtitle || '';
  const simple=MACRO_QUAD.simpleRead || '';
  box.innerHTML = `<div class="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
    <div class="min-w-0">
      <div class="tiny-label">Growth / Inflation Regime</div>
      <h2 class="text-xl md:text-2xl font-semibold text-slate-100 mt-1">${esc(state)}</h2>
      <div class="macro-quad-subtitle mt-1">${esc(subtitle)}</div>
      <p class="text-xs text-slate-400 mt-2 max-w-4xl leading-relaxed">${esc(simple)}</p>
    </div>
    <div class="macro-quad-axis-grid macro-quad-axis-grid-simple">
      <div class="macro-axis-card"><div class="tiny-label">Growth pressure</div><div class="metric-value text-2xl font-bold ${axisClass(g.label)}">${fmtScore(g.score || 0)}</div><div class="text-[11px] text-slate-400">${axisWord(g.label, 'positive', 'negative')} · ${g.inputCount || 0} inputs</div></div>
      <div class="macro-axis-card"><div class="tiny-label">Inflation pressure</div><div class="metric-value text-2xl font-bold ${axisClass(i.label)}">${fmtScore(i.score || 0)}</div><div class="text-[11px] text-slate-400">${axisWord(i.label, 'positive', 'negative')} · ${i.inputCount || 0} inputs</div></div>
    </div>
  </div>
  <div class="grid xl:grid-cols-2 gap-3 mt-4">
    <div class="macro-driver-box"><div class="tiny-label">Growth drivers</div><div class="flex flex-wrap gap-2 mt-2">${driverListForQuad(g.topPositiveDrivers, 'No positive growth driver')} ${driverListForQuad(g.topNegativeDrivers, 'No negative growth driver')}</div></div>
    <div class="macro-driver-box"><div class="tiny-label">Inflation / policy drivers</div><div class="flex flex-wrap gap-2 mt-2">${driverListForQuad(i.topPositiveDrivers, 'No positive inflation driver')} ${driverListForQuad(i.topNegativeDrivers, 'No negative inflation driver')}</div></div>
  </div>`;
}

function pressureBucket(asset){
  const counted=asset.scoreAudit?.countedRows || 0;
  if(asset.pressureBucket) return asset.pressureBucket;
  const score=Number(asset.score||0);
  if(counted===0) return 'Low evidence / avoid';
  if(score>=15) return 'Extreme positive pressure';
  if(score>=8) return 'Strong positive pressure';
  if(score>=3) return 'Moderate positive pressure';
  if(score<=-15) return 'Extreme negative pressure';
  if(score<=-8) return 'Strong negative pressure';
  if(score<=-3) return 'Moderate negative pressure';
  return 'Mixed / neutral pressure';
}
function movementTag(asset){
  if(asset.movementTag) return asset.movementTag;
  const d=Number(asset.score||0)-Number(asset.previousScore||0);
  if(d>=2) return 'Improving';
  if(d<=-2) return 'Deteriorating';
  return 'Stable';
}
function regimeTags(asset){
  const tags=[];
  const move=movementTag(asset);
  if(move && move!=='Stable') tags.push(move);
  if(asset.conflict==='High') tags.push('Conflicted');
  else if(asset.conflict==='Medium') tags.push('Some conflict');
  const counted=asset.scoreAudit?.countedRows || 0;
  if(counted<=0) tags.push('Low evidence');
  else if((asset.confidence||0)>=75) tags.push('High confidence');
  if(asset.freshness) tags.push(asset.freshness);
  return tags.slice(0,4);
}
function renderRegimeSnapshot(){
  const box=$('regimeSnapshot');
  if(!box) return;
  const groups=['Extreme positive pressure','Strong positive pressure','Moderate positive pressure','Mixed / neutral pressure','Moderate negative pressure','Strong negative pressure','Extreme negative pressure','Low evidence / avoid'];
  const rows=[...ASSETS];
  const cards=groups.map(g=>{
    const items=rows.filter(a=>pressureBucket(a)===g).sort((a,b)=>Math.abs(b.score||0)-Math.abs(a.score||0)).slice(0,10);
    const html=items.length ? items.map(a=>`<button class="snapshot-chip" data-jump="${esc(a.id)}"><span>${esc(a.symbol)}</span><strong class="${scoreClass(a.score)}">${fmtScore(a.score)}</strong><em>${regimeTags(a).join(' · ')}</em></button>`).join('') : '<div class="text-[11px] text-slate-500">No assets in this bucket.</div>';
    return `<div class="snapshot-card"><div class="tiny-label">${g}</div><div class="snapshot-chip-wrap mt-2">${html}</div></div>`;
  }).join('');
  box.innerHTML=`<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-3"><div><div class="tiny-label">Regime Queue Snapshot</div><h3 class="text-lg font-semibold text-slate-100 mt-1">What deserves attention first?</h3><p class="text-xs text-slate-500 mt-1">Primary buckets use uncapped raw pressure scores. Improving, deteriorating, conflicted, freshness, and confidence are tags, not buckets that hide strong positive/negative pressure.</p></div><span class="pill self-start md:self-auto">v0.50.2 simple four-quad regime</span></div><div class="snapshot-grid">${cards}</div>`;
  box.querySelectorAll('[data-jump]').forEach(btn=>btn.addEventListener('click',e=>{ const id=btn.dataset.jump; selectedId=id; expanded.add(id); const row=document.querySelector(`.market-row[data-id="${CSS.escape(id)}"]`); if(row){ row.scrollIntoView({behavior:'smooth', block:'center'}); } renderAll(); }));
}
function generateRegimeBrief(){
  const now=new Date().toISOString();
  const topPos=[...ASSETS].filter(a=>(a.scoreAudit?.countedRows||0)>0).sort((a,b)=>(b.score||0)-(a.score||0)).slice(0,7);
  const topNeg=[...ASSETS].filter(a=>(a.scoreAudit?.countedRows||0)>0).sort((a,b)=>(a.score||0)-(b.score||0)).slice(0,7);
  const conflicted=[...ASSETS].filter(a=>a.conflict==='High' || pressureBucket(a)==='Mixed / neutral pressure').sort((a,b)=>Math.abs(b.score||0)-Math.abs(a.score||0)).slice(0,7);
  const changed=[...ASSETS].sort((a,b)=>Math.abs((b.score||0)-(b.previousScore||0))-Math.abs((a.score||0)-(a.previousScore||0))).slice(0,8);
  const fmt=a=>`- ${a.symbol}: ${pressureBucket(a)} (${fmtScore(a.score)} raw, confidence ${a.confidence}%, ${regimeTags(a).join(' · ') || 'stable'}) — ${a.topDriver || a.quick || 'see audit'}`;
  const sourceLines=Object.entries(SOURCE_STATUS||{}).map(([id,s])=>`- ${id}: ${sourceLabel(s.status)}${s.latest_date ? ' · latest '+s.latest_date : ''}`).join('\n');
  const events=(RELEASE_CALENDAR?.events||[]).slice(0,8).map(ev=>`- ${ev.date || ''} ${ev.timeET || ''}: ${ev.report} (${ev.source}, ${ev.calendarConfidence || ev.scheduleType || 'unverified'})`).join('\n') || '- No generated release calendar loaded.';
  const changes=changed.map(a=>`- ${a.symbol}: ${fmtScore((a.score||0)-(a.previousScore||0))} change, now ${fmtScore(a.score)} raw — ${a.scoreChangeLog?.summary || a.bias}`).join('\n');
  const quad = MACRO_QUAD ? `- Current regime: ${MACRO_QUAD.currentState || ''} — ${MACRO_QUAD.subtitle || ''}\n- Growth pressure: ${fmtScore(MACRO_QUAD.growth?.score || 0)} (${MACRO_QUAD.growth?.label || 'positive'})\n- Inflation pressure: ${fmtScore(MACRO_QUAD.inflation?.score || 0)} (${MACRO_QUAD.inflation?.label || 'positive'})\n- Read: ${MACRO_QUAD.simpleRead || ''}` : '- Growth / Inflation Regime not loaded.';
  return `# Edgefield Research Macro Regime Brief v0.50.2\n\nGenerated: ${now}\n\nThis brief ranks public-source fundamental pressure evidence using uncapped raw net pressure scores. It is not a buy/sell signal and does not predict immediate price movement. Missing, stale, candidate, and display-only rows are not treated as neutral. v0.50.2 preserves the U.S.-centered, raw-score, no-price scanner while adding a simple four-quad Growth / Inflation Regime map.\n\n## Growth / Inflation Regime\n${quad}\n\n## Strongest positive raw pressure\n${topPos.map(fmt).join('\n') || '- No positive live-scored assets.'}\n\n## Strongest negative raw pressure\n${topNeg.map(fmt).join('\n') || '- No negative live-scored assets.'}\n\n## Conflicted / neutral candidates\n${conflicted.map(fmt).join('\n') || '- No conflicted or neutral candidates in current view.'}\n\n## Largest score changes\n${changes}\n\n## Source health\n${sourceLines || '- No source status loaded.'}\n\n## Upcoming tracked reports\n${events}\n\n## Caveats\n- Public-source macro/fundamental pressure only.\n- Scores are uncapped raw net pressure; larger absolute numbers mean more weighted evidence, not guaranteed price movement.\n- Mostly U.S.-based inputs, so relevance varies by asset.\n- Scores depend on current source freshness, row eligibility, and asset-specific mapping.\n- Open each asset row in the terminal to inspect counted, context, and excluded evidence.\n`;
}


function releaseResultForEvent(ev){
  const events = RELEASE_RESULTS?.events || [];
  const eventId = `${ev.date || ''}__${String(ev.lane || ev.source || 'event').toLowerCase().replaceAll(' ','-')}__${String(ev.report || 'report').toLowerCase().replaceAll(' ','-').replaceAll('/','-')}`.slice(0,180);
  return events.find(r => r.id === eventId) || events.find(r => r.report === ev.report && r.date === ev.date) || null;
}
function valueOrDash(v){ return (v === null || v === undefined || v === '') ? '—' : esc(v); }
function renderReleaseResultMini(ev){
  const r = releaseResultForEvent(ev);
  if(!r) return '<div class="release-results-mini muted">Result feed: not loaded</div>';
  const status = r.releaseStatus || 'unknown';
  const conf = r.resultConfidence || 'not_available';
  const hasAny = r.actual !== null || r.forecast !== null || r.previous !== null;
  const resultClass = hasAny ? 'result-ready' : (status === 'upcoming' ? 'result-upcoming' : 'result-pending');
  return `<div class="release-results-mini ${resultClass}">
    <span>Status: ${esc(status)}</span>
    <span>Actual ${valueOrDash(r.actual)}</span>
    <span>Forecast ${valueOrDash(r.forecast)}</span>
    <span>Previous ${valueOrDash(r.previous)}</span>
    <span>${esc(conf)}</span>
  </div>`;
}
function sourceQualityFor(id){
  if(!SOURCE_QUALITY?.lanes) return null;
  return SOURCE_QUALITY.lanes[id] || SOURCE_QUALITY.lanes[String(id || '').replaceAll(' ','_').toUpperCase()] || null;
}
function validationStatusText(){
  if(!VALIDATION_SUMMARY) return 'Validation framework not loaded.';
  return `${VALIDATION_SUMMARY.status || 'validation loaded'} · ${VALIDATION_SUMMARY.assetCount || 0} assets · ${(VALIDATION_SUMMARY.warning || '').slice(0,130)}`;
}

function renderReleaseCalendar(){
  const list = $('releaseCalendarList');
  const meta = $('releaseCalendarMeta');
  if(!list || !meta) return;
  const events = (RELEASE_CALENDAR && Array.isArray(RELEASE_CALENDAR.events)) ? RELEASE_CALENDAR.events : [];
  if(!events.length){
    meta.textContent = 'No release calendar generated yet.';
    list.innerHTML = '<div class="text-slate-500">Run Refresh All to generate report watchlist.</div>';
    return;
  }
  const generated = RELEASE_CALENDAR.generatedAt ? new Date(RELEASE_CALENDAR.generatedAt).toLocaleString() : 'unknown';
  const summary = RELEASE_CALENDAR.confidenceSummary || {};
  const confText = `Official ${summary.official ?? 0} · Official-pattern ${summary.officialPattern ?? 0} · Estimated ${summary.estimated ?? 0}`;
  meta.textContent = `Generated ${generated}. Times shown in ET. ${confText}.`;
  const nextEvents = [...events].sort((a,b)=>String(a.datetimeUTC).localeCompare(String(b.datetimeUTC))).slice(0,14);
  list.innerHTML = nextEvents.map(ev=>{
    const imp = ev.importance || 'Medium';
    const cls = imp === 'Very High' ? 'release-highest' : imp === 'High' ? 'release-high' : 'release-normal';
    const inputs = (ev.trackedInputs || []).slice(0,4).join(' / ');
    const confidence = ev.calendarConfidence || 'estimated';
    const confidenceClass = confidence === 'official' ? 'calendar-official' : confidence === 'official-pattern' ? 'calendar-pattern' : 'calendar-estimated';
    const confidenceLabel = confidence === 'official' ? 'Official date' : confidence === 'official-pattern' ? 'Official pattern' : 'Estimated';
    const sourceLink = ev.sourceUrl ? `<a href="${ev.sourceUrl}" target="_blank" rel="noopener" class="release-source-link">source</a>` : '';
    const note = ev.note ? `<div class="text-[11px] text-slate-500 mt-1 leading-snug">${ev.note}</div>` : '';
    return `<div class="release-row ${cls}"><div class="flex items-start justify-between gap-2"><div class="font-semibold text-slate-200 leading-tight">${ev.report}</div><div class="release-time">${ev.timeET || ''}</div></div><div class="text-[11px] text-slate-500 mt-1">${ev.source} · ${ev.date || ''} · ${ev.scheduleType || ''} ${sourceLink}</div><div class="mt-2"><span class="calendar-confidence ${confidenceClass}">${confidenceLabel}</span></div>${renderReleaseResultMini(ev)}<div class="text-[11px] text-slate-400 mt-1 leading-snug">${inputs}</div>${note}</div>`;
  }).join('');
}
function inputTable(asset){
  const audit=scoreAuditPanel(asset);
  const allFactors = asset.factors || [];
  const visibleFactors = filteredFactorsForAsset(asset);
  const hiddenCount = allFactors.length - visibleFactors.length;
  const groups={};
  visibleFactors.forEach(f=>{ if(!groups[f.group]) groups[f.group]=[]; groups[f.group].push(f); });
  const hiddenNote = (!SHOW_ALL_ROWS && hiddenCount>0) ? `<div class="mb-3 soft-card rounded-2xl p-3 text-xs text-slate-400">Hidden by default: ${hiddenCount} non-applicable, display-only, candidate, or not-live rows. Use the sidebar toggle to show the full audit table.</div>` : '';
  if(!visibleFactors.length){
    return audit + hiddenNote + `<div class="p-4 text-slate-400">No applicable live/context rows for this asset under the current row filter.</div>`;
  }
  return audit + hiddenNote + Object.entries(groups).map(([g,fs])=>`<div class="mb-4"><div class="group-title rounded-2xl px-3 py-2 mb-2"><div class="tiny-label">${g}</div></div><div class=""><table class="factor-table"><thead><tr><th style="width:190px">Input</th><th style="width:120px">Relevance</th><th style="width:130px">Status</th><th style="width:130px">Score role</th><th style="width:300px">Derived from</th><th>Brief effect on this asset</th><th style="width:190px">Source / freshness</th></tr></thead><tbody>${fs.map(f=>`<tr><td><div class="font-semibold text-slate-100">${f.name}</div><div class="mt-1">${rowRolePill(f)}</div></td><td><span class="pill">${f.relevance||'Contextual'}</span></td><td><span class="status-chip ${statusClass(f.score)}"><span class="metric-value">${fmtScore(f.score)}</span> ${f.status}</span></td><td><span class="pill">${f.scoreRole||'unclassified'}</span><div class="text-[11px] text-slate-500 mt-1">w ${f.scoreWeight||0} · c ${f.scoreContribution||0}</div></td><td class="text-sm text-slate-300 leading-relaxed">${f.derived||''}</td><td class="text-sm text-slate-300 leading-relaxed">${f.effect}</td><td class="text-xs text-slate-400"><div>${f.source}</div><div class="mt-1">${f.freshness}</div></td></tr>`).join('')}</tbody></table></div></div>`).join('');
}

function renderQueue(){ const rows=getRows(); $('queueSub').textContent=`${rows.length} markets shown. Closed rows are quick reads; open rows show relevance, derivation, source, and effect for the public-source input universe. `; const total=ASSETS.length; const commodities=ASSETS.filter(a=>a.assetClass==='Commodities').length; const open=expanded.size; const liveInputs=ASSETS.filter(a=>(a.factors||[]).some(f=>(f.freshness||'')==='Fresh')).length; const applicableRows=ASSETS.reduce((n,a)=>n+filteredFactorsForAsset(a).length,0); $('statCards').innerHTML=`<div class="soft-card rounded-2xl p-3"><div class="tiny-label">Universe</div><div class="font-semibold">${total}</div></div><div class="soft-card rounded-2xl p-3"><div class="tiny-label">Shown</div><div class="font-semibold">${rows.length}</div></div><div class="soft-card rounded-2xl p-3"><div class="tiny-label">Live-input assets</div><div class="font-semibold">${liveInputs}</div></div><div class="soft-card rounded-2xl p-3"><div class="tiny-label">Visible rows</div><div class="font-semibold">${applicableRows}</div></div>`; if(!rows.length){ $('queue').innerHTML='<div class="p-4 text-slate-400">No markets match the current filters.</div>'; return; } $('queue').innerHTML=rows.map(a=>{ const isOpen=expanded.has(a.id); return `<div class="market-row" data-id="${a.id}"><div class="row-grid row-closed cursor-pointer"><div><div class="font-semibold text-slate-100">${a.symbol}</div><div class="text-[11px] text-slate-500 mt-1">${a.assetClass}</div></div><div><div class="font-semibold text-slate-100">${a.name}</div><div class="text-xs text-slate-400 mt-1 leading-snug">${a.quick}</div><div class="flex flex-wrap gap-2 mt-2 text-[11px]"><span class="pill">Driver: ${a.topDriver}</span><span class="pill">Conflict: ${a.mainConflict}</span><span class="pill">Watch: ${a.watchNext.slice(0,3).join(' / ')}</span></div></div><div class="text-right metric-value text-xl font-bold ${scoreClass(a.score)}">${fmtScore(a.score)}</div><div><div class="text-sm text-slate-200">${a.bias}</div><div class="text-[11px] text-slate-500 mt-1">${a.rankType}</div></div><div class="text-right metric-value">${a.confidence}%</div><div><span class="pill">${a.conflict}</span></div><div><span class="pill">${a.freshness}</span></div><div class="text-right metric-value ${scoreClass(a.score-a.previousScore)}">${change(a)}</div><div><button class="open-btn rounded-xl px-3 py-2 text-xs">${isOpen?'Close':'Open'}</button></div></div>${isOpen?`<div class="open-panel compact-open">${inputTable(a)}</div>`:''}</div>`; }).join(''); document.querySelectorAll('.market-row .row-closed').forEach(el=>el.addEventListener('click',e=>{ const id=el.closest('.market-row').dataset.id; selectedId=id; if(expanded.has(id)) expanded.delete(id); else expanded.add(id); renderAll(false); })); }
function renderDiagnosis(){ /* right readout not included; public-source edition; selected row stays open inline. */ }
function renderAll(){ renderMacroQuadSnapshot(); renderRegimeSnapshot(); renderQueue(); renderDiagnosis(); }
function download(filename,text,type='application/json'){ const blob=new Blob([text],{type}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=filename; a.click(); URL.revokeObjectURL(url); }
['searchBox','universe','assetClass','subgroup','biasFilter','conflictFilter','freshFilter','sortMode','rowLimit'].forEach(id=>$(id).addEventListener('input',()=>{ if(id==='assetClass') updateSubgroups(); renderAll(); }));
$('exportJson').addEventListener('click',()=>download('macro_regime_scanner_public_source_data_contract_v0_50_2.json',JSON.stringify({notice:'Public-source data contract. v0.50.2 is the simple four-quad regime baseline: U.S.-centered, raw-score, price-free macro pressure research data plus a no-price Growth / Inflation Regime map.',assets:ASSETS,source_status:SOURCE_STATUS,release_calendar:RELEASE_CALENDAR,release_results:RELEASE_RESULTS,source_quality:SOURCE_QUALITY,validation_summary:VALIDATION_SUMMARY,regime_bridge:REGIME_BRIDGE,macro_quad:MACRO_QUAD},null,2)));
const briefBtn=$('exportBrief');
if(briefBtn) briefBtn.addEventListener('click',()=>download('edgefield_macro_regime_brief_v0_50_2.md', generateRegimeBrief(), 'text/markdown'));
async function loadData(){
  try {
    const response = await fetch('data/macro_regime_scanner.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const payload = await response.json();
    ASSETS = Array.isArray(payload.assets) ? payload.assets : [];
    DATA_NOTICE = payload.notice || DATA_NOTICE;
    DATA_MODE = payload.data_mode || DATA_MODE;
    SOURCE_STATUS = payload.source_status || {};
    try {
      const calRes = await fetch('data/release_calendar.json', { cache: 'no-store' });
      if (calRes.ok) RELEASE_CALENDAR = await calRes.json();
    } catch (calendarError) {
      RELEASE_CALENDAR = null;
    }
    const optionalLoads = [
      ['data/release_results.json', value => RELEASE_RESULTS = value],
      ['data/source_quality.json', value => SOURCE_QUALITY = value],
      ['data/validation/score_validation_summary.json', value => VALIDATION_SUMMARY = value],
      ['data/exports/regime_labels_latest.json', value => REGIME_BRIDGE = value],
      ['data/macro_quad_snapshot.json', value => MACRO_QUAD = value],
    ];
    for (const [url, setter] of optionalLoads) {
      try {
        const res = await fetch(url, { cache: 'no-store' });
        if (res.ok) setter(await res.json());
      } catch (optionalError) {}
    }
  } catch (error) {
    document.getElementById('queue').innerHTML = `<div class="p-4 text-rose-200">Could not load data/macro_regime_scanner.json. Open this project through a local server or GitHub Pages, not directly as a file. Error: ${error.message}</div>`;
    throw error;
  }
}
async function initApp(){
  await loadData();
  setupFilters();
  expanded.add('GOLD');
  renderAll();
}
initApp();