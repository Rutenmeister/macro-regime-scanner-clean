let ASSETS = [];
let DATA_NOTICE = 'Loading data/macro_regime_scanner.json';
let DATA_MODE = 'public-source-prototype-json';
let SOURCE_STATUS = {}; 
let expanded = new Set();
let selectedId = 'GOLD';
const $ = id => document.getElementById(id);
function fmtScore(n){ if(n===null||n===undefined) return 'MISS'; return n>0?'+'+n:String(n); }
function scoreClass(n){ return n>0?'score-pos':n<0?'score-neg':'score-neu'; }
function statusClass(score){ if(score===null||score===undefined) return 'missing'; if(score>0) return 'support'; if(score<0) return 'pressure'; return 'neutral'; }
function change(a){ const d=(a.score||0)-(a.previousScore||0); return d>0?'+'+d:String(d); }
function freshnessRank(f){ return ({Fresh:7,Sample:5,Mixed:4,Aging:3,Stale:2})[f]||4; }
function conflictRank(c){ return ({Low:1,Medium:2,High:3})[c]||2; }
function biasType(a){ if(a.bias.includes('Bullish')) return 'Bullish'; if(a.bias.includes('Bearish')) return 'Bearish'; return 'Neutral / Mixed'; }
function setupFilters(){ const classes=['All Asset Classes',...Array.from(new Set(ASSETS.map(a=>a.assetClass)))]; $('assetClass').innerHTML=classes.map(c=>`<option>${c}</option>`).join(''); const fresh=['All',...Array.from(new Set(ASSETS.map(a=>a.freshness).filter(Boolean)))]; $('freshFilter').innerHTML=fresh.map(f=>`<option>${f}</option>`).join(''); updateSubgroups(); renderSourcePills(); renderSourceHealth(); }
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
  const order = ['TREASURY_OFFICIAL','CFTC_COT','EIA_OPEN_DATA','USDA_PUBLIC','BLS_PUBLIC','BEA_PUBLIC','FRED_SELECTED','FEDERAL_RESERVE_PUBLIC','NOAA_NWS_PUBLIC','CENSUS_PUBLIC'];
  items.sort(([a],[b]) => (order.indexOf(a) === -1 ? 999 : order.indexOf(a)) - (order.indexOf(b) === -1 ? 999 : order.indexOf(b)) || a.localeCompare(b));
  list.innerHTML = items.map(([id,s]) => {
    const label = sourceLabel(s.status);
    const cls = sourceHealthClass(s.status);
    const latest = s.latest_date ? `<div class="text-[11px] text-slate-500 mt-1">Latest: ${s.latest_date}</div>` : '';
    const note = s.note || s.production_note || '';
    return `<div class="source-health-row rounded-xl p-2 ${cls}"><div class="flex items-center justify-between gap-2"><span class="font-semibold text-slate-200">${id.replaceAll('_',' ')}</span><span class="source-dot-label">${label}</span></div>${latest}<div class="text-[11px] text-slate-400 mt-1 leading-snug">${note}</div></div>`;
  }).join('');
}

function inputTable(asset){ const groups={}; asset.factors.forEach(f=>{ if(!groups[f.group]) groups[f.group]=[]; groups[f.group].push(f); }); return Object.entries(groups).map(([g,fs])=>`<div class="mb-4"><div class="group-title rounded-2xl px-3 py-2 mb-2"><div class="tiny-label">${g}</div></div><div class=""><table class="factor-table"><thead><tr><th style="width:190px">Input</th><th style="width:120px">Relevance</th><th style="width:130px">Status</th><th style="width:300px">Derived from</th><th>Brief effect on this asset</th><th style="width:190px">Source / freshness</th></tr></thead><tbody>${fs.map(f=>`<tr><td><div class="font-semibold text-slate-100">${f.name}</div></td><td><span class="pill">${f.relevance||'Contextual'}</span></td><td><span class="status-chip ${statusClass(f.score)}"><span class="metric-value">${fmtScore(f.score)}</span> ${f.status}</span></td><td class="text-sm text-slate-300 leading-relaxed">${f.derived||''}</td><td class="text-sm text-slate-300 leading-relaxed">${f.effect}</td><td class="text-xs text-slate-400"><div>${f.source}</div><div class="mt-1">${f.freshness}</div></td></tr>`).join('')}</tbody></table></div></div>`).join(''); }
function renderQueue(){ const rows=getRows(); $('queueSub').textContent=`${rows.length} markets shown. Closed rows are quick reads; open rows show relevance, derivation, source, and effect for the public-source input universe. `; const total=ASSETS.length; const commodities=ASSETS.filter(a=>a.assetClass==='Commodities').length; const open=expanded.size; const liveInputs=ASSETS.filter(a=>(a.factors||[]).some(f=>(f.freshness||'')==='Fresh')).length; $('statCards').innerHTML=`<div class="soft-card rounded-2xl p-3"><div class="tiny-label">Universe</div><div class="font-semibold">${total}</div></div><div class="soft-card rounded-2xl p-3"><div class="tiny-label">Shown</div><div class="font-semibold">${rows.length}</div></div><div class="soft-card rounded-2xl p-3"><div class="tiny-label">Live-input assets</div><div class="font-semibold">${liveInputs}</div></div><div class="soft-card rounded-2xl p-3"><div class="tiny-label">Open</div><div class="font-semibold">${open}</div></div>`; if(!rows.length){ $('queue').innerHTML='<div class="p-4 text-slate-400">No markets match the current filters.</div>'; return; } $('queue').innerHTML=rows.map(a=>{ const isOpen=expanded.has(a.id); return `<div class="market-row" data-id="${a.id}"><div class="row-grid row-closed cursor-pointer"><div><div class="font-semibold text-slate-100">${a.symbol}</div><div class="text-[11px] text-slate-500 mt-1">${a.assetClass}</div></div><div><div class="font-semibold text-slate-100">${a.name}</div><div class="text-xs text-slate-400 mt-1 leading-snug">${a.quick}</div><div class="flex flex-wrap gap-2 mt-2 text-[11px]"><span class="pill">Driver: ${a.topDriver}</span><span class="pill">Conflict: ${a.mainConflict}</span><span class="pill">Watch: ${a.watchNext.slice(0,3).join(' / ')}</span></div></div><div class="text-right metric-value text-xl font-bold ${scoreClass(a.score)}">${fmtScore(a.score)}</div><div><div class="text-sm text-slate-200">${a.bias}</div><div class="text-[11px] text-slate-500 mt-1">${a.rankType}</div></div><div class="text-right metric-value">${a.confidence}%</div><div><span class="pill">${a.conflict}</span></div><div><span class="pill">${a.freshness}</span></div><div class="text-right metric-value ${scoreClass(a.score-a.previousScore)}">${change(a)}</div><div><button class="open-btn rounded-xl px-3 py-2 text-xs">${isOpen?'Close':'Open'}</button></div></div>${isOpen?`<div class="open-panel compact-open">${inputTable(a)}</div>`:''}</div>`; }).join(''); document.querySelectorAll('.market-row .row-closed').forEach(el=>el.addEventListener('click',e=>{ const id=el.closest('.market-row').dataset.id; selectedId=id; if(expanded.has(id)) expanded.delete(id); else expanded.add(id); renderAll(false); })); }
function renderDiagnosis(){ /* right readout not included; public-source edition; selected row stays open inline. */ }
function renderAll(){ renderQueue(); renderDiagnosis(); }
function download(filename,text,type='application/json'){ const blob=new Blob([text],{type}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=filename; a.click(); URL.revokeObjectURL(url); }
['searchBox','universe','assetClass','subgroup','biasFilter','conflictFilter','freshFilter','sortMode','rowLimit'].forEach(id=>$(id).addEventListener('input',()=>{ if(id==='assetClass') updateSubgroups(); renderAll(); }));
$('exportJson').addEventListener('click',()=>download('macro_regime_scanner_public_source_data_contract_v0_23.json',JSON.stringify({notice:'Public-source data contract. v0.24 includes Treasury, CFTC COT, EIA energy, USDA/NASS agriculture, and BLS inflation/labor public-source lanes; price-derived lanes remain excluded.',assets:ASSETS},null,2)));
async function loadData(){
  try {
    const response = await fetch('data/macro_regime_scanner.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const payload = await response.json();
    ASSETS = Array.isArray(payload.assets) ? payload.assets : [];
    DATA_NOTICE = payload.notice || DATA_NOTICE;
    DATA_MODE = payload.data_mode || DATA_MODE;
    SOURCE_STATUS = payload.source_status || {};
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