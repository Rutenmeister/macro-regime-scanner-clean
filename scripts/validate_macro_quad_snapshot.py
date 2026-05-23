#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data' / 'macro_quad_snapshot.json'
REQUIRED_STATES = {'Goldilocks', 'Reflation', 'Stagflation', 'Deflation'}


def main():
    if not PATH.exists():
        raise SystemExit('Missing data/macro_quad_snapshot.json')
    data = json.loads(PATH.read_text(encoding='utf-8'))
    for key in ['currentState', 'subtitle', 'simpleRead', 'growth', 'inflation', 'states']:
        if key not in data:
            raise SystemExit(f'Missing macro quad key: {key}')
    if data['currentState'] not in REQUIRED_STATES:
        raise SystemExit(f'Invalid currentState: {data["currentState"]}')
    names = {s.get('name') for s in data.get('states', [])}
    missing = REQUIRED_STATES - names
    if missing:
        raise SystemExit(f'Missing state definitions: {sorted(missing)}')
    extra = names - REQUIRED_STATES
    if extra:
        raise SystemExit(f'Unexpected state definitions: {sorted(extra)}')
    if 'confidence' in data:
        raise SystemExit('Unexpected confidence key in simple four-quad snapshot')
    for axis in ['growth', 'inflation']:
        obj = data[axis]
        label = obj.get('label')
        score = obj.get('score')
        if label not in {'positive', 'negative'}:
            raise SystemExit(f'Invalid {axis} label: {label}')
        if not isinstance(score, (int, float)):
            raise SystemExit(f'Invalid {axis} score')
        if score == 0:
            raise SystemExit(f'Invalid {axis}: score is 0. Do not publish positive/negative zero.')
        if label == 'positive' and score <= 0:
            raise SystemExit(f'Invalid {axis}: positive label with non-positive score {score}')
        if label == 'negative' and score >= 0:
            raise SystemExit(f'Invalid {axis}: negative label with non-negative score {score}')
    print(f"VALIDATION PASSED: macro regime {data['currentState']} / {data['subtitle']}")


if __name__ == '__main__':
    main()
