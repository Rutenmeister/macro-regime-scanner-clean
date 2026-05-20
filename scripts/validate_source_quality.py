#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'data'/'source_quality.json'
def main():
    if not PATH.exists(): raise SystemExit('Missing data/source_quality.json')
    data=json.loads(PATH.read_text())
    if not isinstance(data.get('lanes'), dict): raise SystemExit('source_quality.lanes must be an object')
    if not isinstance(data.get('assets'), list): raise SystemExit('source_quality.assets must be a list')
    for k,v in data['lanes'].items():
        if 'qualityScore' not in v or 'qualityGrade' not in v: raise SystemExit(f'lane {k} missing quality fields')
    print(f"VALIDATION PASSED: source quality lanes={len(data['lanes'])} assets={len(data['assets'])}")
if __name__=='__main__': main()
