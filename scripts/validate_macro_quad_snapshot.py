#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data' / 'macro_quad_snapshot.json'
REQUIRED_STATES = {
    'Goldilocks', 'Goldilocks / Reflation Blend', 'Reflation',
    'Reflation / Stagflation Blend', 'Stagflation', 'Stagflation / Deflation Blend',
    'Deflation', 'Deflation / Goldilocks Blend', 'Neutral / Low-Conviction Macro Pressure'
}

def main():
    if not PATH.exists():
        raise SystemExit('Missing data/macro_quad_snapshot.json')
    data = json.loads(PATH.read_text(encoding='utf-8'))
    for key in ['currentState','subtitle','simpleRead','confidence','growth','inflation','mainConflict','states']:
        if key not in data:
            raise SystemExit(f'Missing macro quad key: {key}')
    if data['currentState'] not in REQUIRED_STATES:
        raise SystemExit(f'Invalid currentState: {data["currentState"]}')
    names = {s.get('name') for s in data.get('states', [])}
    missing = REQUIRED_STATES - names
    if missing:
        raise SystemExit(f'Missing state definitions: {sorted(missing)}')
    for axis in ['growth','inflation']:
        obj = data[axis]
        if obj.get('label') not in {'positive','negative','mixed'}:
            raise SystemExit(f'Invalid {axis} label')
        if not isinstance(obj.get('score'), (int, float)):
            raise SystemExit(f'Invalid {axis} score')
        if not isinstance(obj.get('inputCount'), int):
            raise SystemExit(f'Invalid {axis} inputCount')
    print(f"VALIDATION PASSED: macro quad {data['currentState']} / {data['subtitle']}")

if __name__ == '__main__':
    main()
