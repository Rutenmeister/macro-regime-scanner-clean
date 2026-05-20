#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'macro_regime_scanner.json'
OUT=ROOT/'data'/'validation'/'score_validation_summary.json'

def bucket(score):
    score=float(score or 0)
    if score>=15: return 'Extreme positive'
    if score>=8: return 'Strong positive'
    if score>=3: return 'Moderate positive'
    if score<=-15: return 'Extreme negative'
    if score<=-8: return 'Strong negative'
    if score<=-3: return 'Moderate negative'
    return 'Mixed neutral'

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data=json.loads(DATA.read_text())
    assets=data.get('assets',[])
    buckets={}
    for a in assets:
        b=bucket(a.get('score'))
        buckets.setdefault(b,0); buckets[b]+=1
    payload={
        'version':'v0.43-validation-framework',
        'generatedAt':datetime.now(timezone.utc).isoformat(),
        'status':'framework_ready_no_price_backtest_attached',
        'warning':'This validates score distribution and history readiness only. It does not claim predictive accuracy until separate price/return data is supplied.',
        'assetCount':len(assets),
        'bucketCounts':buckets,
        'nextValidationInputs':['asset returns 1d/5d/20d','max adverse move','score bucket performance','conflict-adjusted performance'],
    }
    OUT.write_text(json.dumps(payload, indent=2)+'\n')
    print(f"Wrote {OUT.relative_to(ROOT)}")
if __name__=='__main__': main()
