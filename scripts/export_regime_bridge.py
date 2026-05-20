#!/usr/bin/env python3
from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'data'/'macro_regime_scanner.json'
OUT_DIR=ROOT/'data'/'exports'

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data=json.loads(DATA_PATH.read_text())
    now=datetime.now(timezone.utc).isoformat()
    rows=[]
    for a in data.get('assets',[]):
        audit=a.get('scoreAudit') or {}
        rows.append({
            'date': now[:10],
            'generatedAt': now,
            'assetId': a.get('id'),
            'symbol': a.get('symbol'),
            'name': a.get('name'),
            'assetClass': a.get('assetClass'),
            'rawScore': a.get('score'),
            'previousScore': a.get('previousScore'),
            'pressureBucket': a.get('pressureBucket'),
            'movementTag': a.get('movementTag'),
            'confidence': a.get('confidence'),
            'conflict': a.get('conflict'),
            'freshness': a.get('freshness'),
            'coverage': a.get('coverage'),
            'countedRows': audit.get('countedRows'),
            'contextRows': audit.get('contextRows'),
            'excludedRows': audit.get('excludedRows'),
            'topDriver': a.get('topDriver'),
            'mainConflict': a.get('mainConflict'),
            'scoreChangeSummary': (a.get('scoreChangeLog') or {}).get('summary'),
        })
    payload={'version':'v0.46-regime-bridge','generatedAt':now,'intendedConsumers':['TradeStream','Capital Trace','Pathwise'],'warning':'Evidence labels are research context, not trade signals.', 'regimes':rows}
    (OUT_DIR/'regime_labels_latest.json').write_text(json.dumps(payload, indent=2)+'\n')
    with (OUT_DIR/'regime_labels_latest.csv').open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['date'])
        w.writeheader(); w.writerows(rows)
    print(f"Wrote exports for {len(rows)} assets")
if __name__=='__main__': main()
