#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _iter_run_dirs(shared_dir: Path) -> Iterable[Path]:
    if not shared_dir.exists():
        return []
    return sorted([p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")], key=lambda p: p.name)


def _load_learning_state(state_path: Path) -> Dict[str, Any]:
    payload = _load_json(state_path)
    if not payload:
        return {
            "last_nightly_resolved_total": 0,
            "last_weekly_resolved_total": 0,
            "last_nightly_run_at": None,
            "last_weekly_run_at": None,
            "last_weekly_train_at": None,
        }
    return payload


def _collect_outcomes(shared_dir: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "runs_seen": 0,
        "runs_with_outcomes": 0,
        "markets": Counter(),
        "buckets": Counter(),
        "statuses": Counter(),
    }
    for run_dir in _iter_run_dirs(shared_dir):
        stats["runs_seen"] += 1
        payload = _load_json(run_dir / "realized_outcomes.json")
        if not payload:
            continue
        outcomes = payload.get("outcomes", [])
        if not isinstance(outcomes, list) or not outcomes:
            continue
        stats["runs_with_outcomes"] += 1
        run_ctx = payload.get("run_context", {}) if isinstance(payload.get("run_context"), dict) else {}
        market = str(run_ctx.get("market", "") or "UNKNOWN").upper()
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            out = dict(row)
            out["run_id"] = out.get("run_id") or run_dir.name
            out["market"] = market
            out["outcome_key"] = f"{out['run_id']}:{out.get('ticker','')}:{int(out.get('priority_rank', 0) or 0)}"
            rows.append(out)
            stats["markets"][market] += 1
            stats["buckets"][str(out.get("decision_bucket", "") or "unknown")] += 1
            stats["statuses"][str(out.get("status", "") or "UNKNOWN").upper()] += 1
    stats["markets"] = dict(stats["markets"])
    stats["buckets"] = dict(stats["buckets"])
    stats["statuses"] = dict(stats["statuses"])
    return rows, stats


def _resolved_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    resolved = [r for r in rows if str(r.get("status", "")).upper() == "RESOLVED"]
    by_market: Dict[str, int] = defaultdict(int)
    by_bucket: Dict[str, int] = defaultdict(int)
    for row in resolved:
        by_market[str(row.get("market", "UNKNOWN")).upper()] += 1
        by_bucket[str(row.get("decision_bucket", "unknown") or "unknown")] += 1
    return {
        "total_resolved": len(resolved),
        "resolved_keys": sorted({str(r.get("outcome_key")) for r in resolved if r.get("outcome_key")}),
        "resolved_by_market": dict(by_market),
        "resolved_by_bucket": dict(by_bucket),
    }


def _run_command(cmd: List[str], cwd: Path) -> Dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )
        return {
            "cmd": cmd,
            "returncode": int(proc.returncode),
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-40:]),
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-40:]),
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": proc.returncode == 0,
        }
    except Exception as e:
        return {
            "cmd": cmd,
            "returncode": -1,
            "stdout_tail": "",
            "stderr_tail": str(e),
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": False,
        }


def _render_report(report: Dict[str, Any]) -> str:
    lines = [
        f"# Learning Cycle Report ({report.get('mode')})",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- action: {report.get('action')}",
        f"- reason: {report.get('reason')}",
        f"- total_resolved: {report.get('total_resolved', 0)}",
        f"- new_resolved_since_last_cycle: {report.get('new_resolved_since_last_cycle', 0)}",
        f"- resolved_by_market: {report.get('resolved_by_market', {})}",
        f"- resolved_by_bucket: {report.get('resolved_by_bucket', {})}",
        "",
        "## Commands",
    ]
    commands = report.get("commands", [])
    if isinstance(commands, list) and commands:
        for item in commands:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {' '.join(item.get('cmd', []))}: "
                f"{'OK' if item.get('ok') else 'FAIL'} "
                f"(returncode={item.get('returncode')})"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def run_learning_cycle(
    *,
    mode: str,
    shared_dir: Path,
    report_dir: Path,
    state_path: Path,
    nightly_min_new_resolved: int,
    weekly_min_total_resolved: int,
    weekly_min_new_resolved: int,
) -> Dict[str, Any]:
    rows, collect_stats = _collect_outcomes(shared_dir)
    resolved = _resolved_summary(rows)
    state = _load_learning_state(state_path)
    total_resolved = int(resolved["total_resolved"])

    if mode == "nightly":
        previous_total = int(state.get("last_nightly_resolved_total", 0) or 0)
        new_resolved = max(0, total_resolved - previous_total)
        min_needed = int(nightly_min_new_resolved)
        action = "skip"
        reason = "insufficient_new_resolved"
        commands: List[Dict[str, Any]] = []
        if new_resolved >= min_needed:
            commands.append(
                _run_command(
                    ["python3", "multi_agent/tools/export_scan_archive_learning_dataset.py"],
                    PROJECT_ROOT,
                )
            )
            action = "dataset_refresh"
            reason = "nightly_learning_dataset_refreshed"
        report = {
            "mode": mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "reason": reason,
            "total_resolved": total_resolved,
            "new_resolved_since_last_cycle": new_resolved,
            "minimum_required_new_resolved": min_needed,
            "resolved_by_market": resolved["resolved_by_market"],
            "resolved_by_bucket": resolved["resolved_by_bucket"],
            "collection_stats": collect_stats,
            "commands": commands,
        }
        state["last_nightly_run_at"] = report["generated_at"]
        if action != "skip":
            state["last_nightly_resolved_total"] = total_resolved
    else:
        previous_total = int(state.get("last_weekly_resolved_total", 0) or 0)
        new_resolved = max(0, total_resolved - previous_total)
        commands = []
        if total_resolved < int(weekly_min_total_resolved):
            action = "skip"
            reason = "insufficient_total_resolved"
        elif new_resolved < int(weekly_min_new_resolved):
            action = "skip"
            reason = "insufficient_new_resolved"
        else:
            commands.append(
                _run_command(
                    ["python3", "multi_agent/tools/export_scan_archive_learning_dataset.py"],
                    PROJECT_ROOT,
                )
            )
            commands.append(_run_command(["python3", "retrain_ml.py"], PROJECT_ROOT))
            action = "weekly_retrain"
            reason = "weekly_retrain_executed" if all(cmd.get("ok") for cmd in commands) else "weekly_retrain_failed"
        report = {
            "mode": mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "reason": reason,
            "total_resolved": total_resolved,
            "new_resolved_since_last_cycle": new_resolved,
            "minimum_required_total_resolved": int(weekly_min_total_resolved),
            "minimum_required_new_resolved": int(weekly_min_new_resolved),
            "resolved_by_market": resolved["resolved_by_market"],
            "resolved_by_bucket": resolved["resolved_by_bucket"],
            "collection_stats": collect_stats,
            "commands": commands,
        }
        state["last_weekly_run_at"] = report["generated_at"]
        if action == "weekly_retrain" and all(cmd.get("ok") for cmd in commands):
            state["last_weekly_resolved_total"] = total_resolved
            state["last_weekly_train_at"] = report["generated_at"]

    report_json = report_dir / f"learning_cycle_{mode}.json"
    report_md = report_dir / f"learning_cycle_{mode}.md"
    _write_json(report_json, report)
    _write_text(report_md, _render_report(report))
    _write_json(state_path, state)
    report["report_paths"] = {"json_path": str(report_json), "md_path": str(report_md), "state_path": str(state_path)}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run nightly learning refresh or weekly retraining with safety gates.")
    parser.add_argument("--mode", choices=["nightly", "weekly"], required=True)
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--report-dir", default="runtime_state/reports/learning")
    parser.add_argument("--state-path", default="runtime_state/long_term/learning/training_state.json")
    parser.add_argument("--nightly-min-new-resolved", type=int, default=20)
    parser.add_argument("--weekly-min-total-resolved", type=int, default=50)
    parser.add_argument("--weekly-min-new-resolved", type=int, default=10)
    args = parser.parse_args()

    report = run_learning_cycle(
        mode=str(args.mode),
        shared_dir=Path(args.shared_dir),
        report_dir=Path(args.report_dir),
        state_path=Path(args.state_path),
        nightly_min_new_resolved=int(args.nightly_min_new_resolved),
        weekly_min_total_resolved=int(args.weekly_min_total_resolved),
        weekly_min_new_resolved=int(args.weekly_min_new_resolved),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
