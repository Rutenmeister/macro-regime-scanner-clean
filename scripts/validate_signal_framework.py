#!/usr/bin/env python3
"""Optional v0.40 validation framework for future price/return tests.

This does not add price to the live scanner score. It only checks whether an
optional external CSV has the columns needed for later forward-return analysis.
Expected path: data/validation/forward_returns.csv
Required columns: date,symbol,score,forward_1d,forward_5d,forward_20d
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "validation" / "forward_returns.csv"
REQUIRED = {"date", "symbol", "score", "forward_1d", "forward_5d", "forward_20d"}

if not CSV_PATH.exists():
    print("OPTIONAL VALIDATION SKIPPED: data/validation/forward_returns.csv not present.")
    print("This is expected until separate price/return data is supplied for research validation.")
    raise SystemExit(0)

with CSV_PATH.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    missing = REQUIRED - set(reader.fieldnames or [])
    if missing:
        print("OPTIONAL VALIDATION FAILED")
        print("Missing columns:", ", ".join(sorted(missing)))
        raise SystemExit(1)
    rows = list(reader)

print(f"OPTIONAL VALIDATION READY: {len(rows)} forward-return rows available.")
