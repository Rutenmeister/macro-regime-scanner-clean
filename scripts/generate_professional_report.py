#!/usr/bin/env python3
from __future__ import annotations
import html, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'macro_regime_scanner.json'
CAL=ROOT/'data'/'release_calendar.json'
SRCQ=ROOT/'data'/'source_quality.json'
VAL=ROOT/'data'/'validation'/'score_validation_summary.json'
QUAD=ROOT/'data'/'macro_quad_snapshot.json'
OUT_DIR=ROOT/'data'/'reports'

def score(a): return float(a.get('score') or 0)
def line(a): return f"- {a.get('symbol')}: {a.get('pressureBucket')} ({score(a):+.1f} raw, confidence {a.get('confidence')}%, conflict {a.get('conflict')}) — {a.get('topDriver')}"

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data=json.loads(DATA.read_text()); assets=data.get('assets',[])
    cal=json.loads(CAL.read_text()) if CAL.exists() else {'events':[]}
    srcq=json.loads(SRCQ.read_text()) if SRCQ.exists() else {'summary':{}}
    val=json.loads(VAL.read_text()) if VAL.exists() else {'status':'not generated'}
    quad=json.loads(QUAD.read_text()) if QUAD.exists() else None
    top_pos=sorted(assets,key=score,reverse=True)[:8]
    top_neg=sorted(assets,key=score)[:8]
    events=cal.get('events',[])[:10]
    now=datetime.now(timezone.utc).isoformat()
    md=f"""# Edgefield Research Macro Regime Brief v0.50

Generated: {now}

This brief ranks official/public-source macro pressure evidence for a U.S.-centered asset universe. Scores are raw, uncapped, and price-free. v0.50 adds a no-price Growth / Inflation Pressure Map. This is a research brief, not a buy/sell signal or investment advice.

## Growth / Inflation Pressure Map
{('- Current state: '+quad.get('currentState','')+' — '+quad.get('subtitle','')+chr(10)+'- Growth pressure: '+str(quad.get('growth',{}).get('score','n/a'))+' ('+quad.get('growth',{}).get('label','mixed')+')'+chr(10)+'- Inflation pressure: '+str(quad.get('inflation',{}).get('score','n/a'))+' ('+quad.get('inflation',{}).get('label','mixed')+')'+chr(10)+'- Confidence: '+quad.get('confidence','Low')+chr(10)+'- Read: '+quad.get('simpleRead','')) if quad else '- Macro quad snapshot not generated.'}

## Strongest positive raw pressure
{chr(10).join(line(a) for a in top_pos)}

## Strongest negative raw pressure
{chr(10).join(line(a) for a in top_neg)}

## Upcoming tracked reports
{chr(10).join('- '+(e.get('date','')+' '+e.get('timeET','')+': '+e.get('report','')+' ['+(e.get('calendarConfidence') or 'unknown')+']') for e in events)}

## Source QA summary
- Lanes: {srcq.get('summary',{}).get('lanes','n/a')}
- Live/fresh lanes: {srcq.get('summary',{}).get('liveOrFreshLanes','n/a')}
- High coverage assets: {srcq.get('summary',{}).get('highCoverageAssets','n/a')}
- Insufficient coverage assets: {srcq.get('summary',{}).get('insufficientCoverageAssets','n/a')}

## Validation status
{val.get('status','unknown')}: {val.get('warning','')}

## Caveats
- Larger absolute raw scores mean more weighted evidence, not guaranteed price movement.
- Missing data is not neutral.
- Official/public-source dates and result fields vary by source; forecast values may require licensed data.
- Use the terminal audit rows to inspect what counted and what was excluded.
- Macro quad blend states describe current ambiguity, not a confirmed historical transition path.
"""
    (OUT_DIR/'current_regime_brief.md').write_text(md)
    body='<pre>'+html.escape(md)+'</pre>'
    (OUT_DIR/'current_regime_brief.html').write_text('<!doctype html><html><head><meta charset="utf-8"><title>Edgefield Research Regime Brief</title><style>body{font-family:system-ui;background:#090317;color:#e5e7eb;padding:32px}pre{white-space:pre-wrap;line-height:1.5}</style></head><body>'+body+'</body></html>')
    print('Wrote data/reports/current_regime_brief.md and .html')
if __name__=='__main__': main()
