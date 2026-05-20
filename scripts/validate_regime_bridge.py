#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'data'/'exports'/'regime_labels_latest.json'
def main():
    if not PATH.exists(): raise SystemExit('Missing data/exports/regime_labels_latest.json')
    data=json.loads(PATH.read_text())
    regs=data.get('regimes')
    if not isinstance(regs, list) or not regs: raise SystemExit('regimes must be a non-empty list')
    required={'symbol','rawScore','pressureBucket','confidence','conflict'}
    for i,r in enumerate(regs):
        if not required.issubset(r): raise SystemExit(f'regime row {i} missing {required-set(r)}')
    print(f"VALIDATION PASSED: regime bridge rows={len(regs)}")
if __name__=='__main__': main()
