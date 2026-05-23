#!/usr/bin/env python3
"""Validate v0.40 score-history snapshot structure."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "data" / "history" / "latest.json"
DATA = ROOT / "data" / "macro_regime_scanner.json"

errors: list[str] = []

def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"could not load {path.relative_to(ROOT)}: {exc}")
        return None

snap = load(LATEST)
data = load(DATA)
if isinstance(snap, dict):
    if snap.get("snapshotVersion") != "v0.40-score-history":
        errors.append("latest snapshot has wrong snapshotVersion")
    assets = snap.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("latest snapshot assets must be a non-empty list")
    else:
        for i, a in enumerate(assets):
            for key in ["id", "symbol", "score", "pressureBucket", "movementTag", "confidence", "conflict"]:
                if key not in a:
                    errors.append(f"snapshot assets[{i}] missing {key}")
            if not isinstance(a.get("score"), (int, float)):
                errors.append(f"snapshot assets[{i}].score must be numeric")
if isinstance(data, dict):
    if data.get("score_history", {}).get("scoreScale") != "uncapped raw net pressure; no +/-10 display cap":
        errors.append("dashboard data missing v0.40 score_history scoreScale")

if errors:
    print("SCORE HISTORY VALIDATION FAILED")
    for e in errors[:100]:
        print("-", e)
    raise SystemExit(1)
print("SCORE HISTORY VALIDATION PASSED")
