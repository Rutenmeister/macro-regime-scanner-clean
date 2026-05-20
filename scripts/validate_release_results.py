#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "release_results.json"
REQUIRED = ["id", "report", "date", "releaseStatus", "actual", "forecast", "previous", "resultConfidence"]

def main() -> int:
    if not PATH.exists():
        raise SystemExit("Missing data/release_results.json. Run scripts/generate_release_results.py")
    data = json.loads(PATH.read_text())
    events = data.get("events")
    if not isinstance(events, list):
        raise SystemExit("release_results.events must be a list")
    for i, ev in enumerate(events):
        missing = [k for k in REQUIRED if k not in ev]
        if missing:
            raise SystemExit(f"event {i} missing {missing}")
        if ev.get("actual") is None and ev.get("resultConfidence") not in {"not_available", "pending", "estimated"}:
            raise SystemExit(f"event {i} has null actual but resultConfidence={ev.get('resultConfidence')}")
    print(f"VALIDATION PASSED: release result schema for {len(events)} events")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
