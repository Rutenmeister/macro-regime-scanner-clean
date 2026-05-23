#!/usr/bin/env python3
"""Refresh all enabled public-source lanes from a stable config.

This is the workflow orchestrator for Macro Regime Scanner v0.25F.
The GitHub Actions YAML should call this one script instead of listing every
source step directly. Future sources should be enabled in config/source_pipeline.json
after their fetch/apply scripts are present and tested.

Usage:
    python scripts/refresh_all_sources.py
    python scripts/refresh_all_sources.py --dry-run
    python scripts/refresh_all_sources.py --lane treasury --lane bls
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "config" / "source_pipeline.json"
REPORT_PATH = ROOT / "data" / "refresh_report.json"
VALIDATE_PATH = ROOT / "scripts" / "validate_data.py"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required config: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_script(script_path: str, dry_run: bool = False) -> dict[str, Any]:
    path = ROOT / script_path
    if not path.exists():
        raise FileNotFoundError(f"Pipeline script not found: {script_path}")

    if dry_run:
        return {"script": script_path, "status": "dry_run", "returncode": 0}

    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    record = {
        "script": script_path,
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stdoutTail": result.stdout[-4000:],
        "stderrTail": result.stderr[-4000:],
    }
    if result.returncode != 0:
        raise RuntimeError(
            f"Script failed: {script_path}\n"
            f"Return code: {result.returncode}\n"
            f"STDOUT:\n{result.stdout[-2000:]}\n"
            f"STDERR:\n{result.stderr[-2000:]}"
        )
    return record


def check_required_secrets(lane: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for secret in lane.get("requiresSecrets", []):
        if not os.environ.get(secret):
            missing.append(secret)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Check config/scripts without running source fetches")
    parser.add_argument("--lane", action="append", default=[], help="Run only selected lane id; can be repeated")
    args = parser.parse_args()

    started = datetime.now(timezone.utc).isoformat()
    pipeline = load_json(PIPELINE_PATH)
    selected = set(args.lane or [])
    report: dict[str, Any] = {
        "pipelineVersion": pipeline.get("pipelineVersion"),
        "startedAt": started,
        "finishedAt": None,
        "dryRun": args.dry_run,
        "selectedLanes": sorted(selected) if selected else "all enabled",
        "lanes": [],
        "validation": None,
        "status": "running",
    }

    try:
        for lane in pipeline.get("lanes", []):
            lane_id = lane.get("id")
            if selected and lane_id not in selected:
                continue
            if not lane.get("enabled", False):
                report["lanes"].append({"id": lane_id, "status": "skipped_disabled"})
                continue

            missing = check_required_secrets(lane)
            if missing and not args.dry_run:
                raise RuntimeError(f"Lane {lane_id} missing required GitHub secrets/environment variables: {', '.join(missing)}")

            lane_record = {"id": lane_id, "sourceId": lane.get("sourceId"), "steps": []}
            lane_record["steps"].append(run_script(lane["fetch"], dry_run=args.dry_run))
            lane_record["steps"].append(run_script(lane["apply"], dry_run=args.dry_run))
            lane_record["status"] = "ok" if not args.dry_run else "dry_run"
            report["lanes"].append(lane_record)

        recompute_path = ROOT / "scripts" / "recompute_live_scores.py"
        if recompute_path.exists():
            report["scoreRecompute"] = run_script("scripts/recompute_live_scores.py", dry_run=args.dry_run)

        release_calendar_path = ROOT / "scripts" / "generate_release_calendar.py"
        if release_calendar_path.exists():
            report["releaseCalendar"] = run_script("scripts/generate_release_calendar.py", dry_run=args.dry_run)

        if pipeline.get("global", {}).get("runValidation", True):
            report["validation"] = run_script(str(VALIDATE_PATH.relative_to(ROOT)), dry_run=args.dry_run)
            history_validator = ROOT / "scripts" / "validate_score_history.py"
            if history_validator.exists():
                report["scoreHistoryValidation"] = run_script(str(history_validator.relative_to(ROOT)), dry_run=args.dry_run)
            optional_signal_validator = ROOT / "scripts" / "validate_signal_framework.py"
            if optional_signal_validator.exists():
                report["optionalSignalValidation"] = run_script(str(optional_signal_validator.relative_to(ROOT)), dry_run=args.dry_run)

        report["status"] = "ok" if not args.dry_run else "dry_run_ok"
        return 0
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Refresh report written to {REPORT_PATH.relative_to(ROOT)}")
        print(f"Pipeline status: {report['status']}")


if __name__ == "__main__":
    raise SystemExit(main())
