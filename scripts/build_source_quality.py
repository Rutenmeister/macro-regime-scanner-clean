#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "macro_regime_scanner.json"
OUT_PATH = ROOT / "data" / "source_quality.json"

def lane_quality(status: dict) -> dict:
    text = " ".join(str(status.get(k, "")) for k in ("status", "note", "production_note")).lower()
    latest = status.get("latest_date")
    if "live" in text or "fresh" in text:
        grade = "live_or_fresh"
        score = 90
    elif "workflow" in text or "ready" in text:
        grade = "workflow_ready"
        score = 72
    elif "candidate" in text:
        grade = "candidate"
        score = 45
    else:
        grade = "unknown"
        score = 50
    if not latest:
        score = max(0, score - 10)
    return {"qualityGrade": grade, "qualityScore": score, "latestDate": latest, "status": status.get("status"), "note": status.get("note") or status.get("production_note")}

def asset_coverage(asset: dict) -> dict:
    audit = asset.get("scoreAudit") or {}
    counted = int(audit.get("countedRows") or 0)
    context = int(audit.get("contextRows") or 0)
    excluded = int(audit.get("excludedRows") or 0)
    total = counted + context + excluded
    direct_ratio = counted / total if total else 0
    if counted >= 8 and direct_ratio >= .20:
        label = "High"
    elif counted >= 4:
        label = "Medium"
    elif counted >= 1:
        label = "Low"
    else:
        label = "Insufficient direct live evidence"
    return {"symbol": asset.get("symbol"), "coverageLabel": label, "countedRows": counted, "contextRows": context, "excludedRows": excluded, "directEvidenceRatio": round(direct_ratio, 3)}

def main() -> int:
    data = json.loads(DATA_PATH.read_text())
    source_status = data.get("source_status") or {}
    lanes = {k: lane_quality(v) for k, v in source_status.items()}
    assets = [asset_coverage(a) for a in data.get("assets", [])]
    payload = {
        "version": "v0.44-source-quality",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "lanes": len(lanes),
            "liveOrFreshLanes": sum(1 for v in lanes.values() if v["qualityGrade"] == "live_or_fresh"),
            "highCoverageAssets": sum(1 for a in assets if a["coverageLabel"] == "High"),
            "insufficientCoverageAssets": sum(1 for a in assets if a["coverageLabel"].startswith("Insufficient")),
        },
        "lanes": lanes,
        "assets": assets,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
