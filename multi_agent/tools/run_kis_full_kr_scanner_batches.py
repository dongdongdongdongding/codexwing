#!/usr/bin/env python3
"""Run the full KR scanner in small KIS-only batches with checkpoints.

This wrapper exists because a monolithic full-universe phase25 KR scan can run
for a long time before producing durable artifacts. It slices the same universe
used by ``live_full_kr_swing_scan.py`` into small batches and invokes that tool
with ``--tickers`` for each slice.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.live_full_kr_swing_scan import _load_kr_universe  # noqa: E402


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"
LIVE_SCAN_TOOL = PROJECT_ROOT / "multi_agent" / "tools" / "live_full_kr_swing_scan.py"


def _kst_timestamp() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S")
    except Exception:
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def _chunk_rows(rows: Sequence[Mapping[str, str]], batch_size: int) -> List[List[Dict[str, str]]]:
    size = max(1, int(batch_size))
    return [[dict(item) for item in rows[idx : idx + size]] for idx in range(0, len(rows), size)]


def _chunk_rows_by_count(rows: Sequence[Mapping[str, str]], batch_count: int) -> List[List[Dict[str, str]]]:
    count = max(1, int(batch_count))
    if not rows:
        return []
    count = min(count, len(rows))
    base_size, remainder = divmod(len(rows), count)
    chunks: List[List[Dict[str, str]]] = []
    offset = 0
    for index in range(count):
        size = base_size + (1 if index < remainder else 0)
        chunk = rows[offset : offset + size]
        chunks.append([dict(item) for item in chunk])
        offset += size
    return chunks


def _ticker_arg(rows: Sequence[Mapping[str, str]]) -> str:
    return ",".join(f"{str(row.get('Code') or '').strip()}={str(row.get('Name') or '').strip()}" for row in rows)


def _ticker_preview(tickers: Sequence[str], max_items: int = 8) -> str:
    items = [str(item) for item in tickers]
    if len(items) <= max_items:
        return str(items)
    return f"{items[:max_items]} ... (+{len(items) - max_items} more)"


def _default_state_path(batch_size: int) -> Path:
    return REPORT_DIR / f"kis_full_scanner_batches_{_kst_timestamp()}_b{int(batch_size)}.json"


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_state(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(state, ensure_ascii=False, indent=2, default=str)
    path.write_text(text + "\n", encoding="utf-8")
    latest = REPORT_DIR / "kis_full_scanner_batches_latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(text + "\n", encoding="utf-8")


def _tail_lines(lines: Sequence[str], max_lines: int = 80) -> List[str]:
    return [str(line).rstrip("\n") for line in list(lines)[-max(1, int(max_lines)) :]]


def _scan_exception_reasons(lines: Sequence[str]) -> List[str]:
    reasons: List[str] = []
    for line in lines:
        text = str(line).strip()
        if "EXCEPTION:" not in text:
            continue
        reason = text
        if reason.startswith("- "):
            reason = reason[2:].strip()
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def _kis_batch_env(args: argparse.Namespace) -> Dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "PYTHONUNBUFFERED": "1",
            "KIS_ENABLE_LIVE_CALLS": "1",
            "AG_KR_UNIVERSE_PROVIDER": "fdr",
            "AG_KR_MARKET_DATA_PROVIDER": "kis_only",
            "AG_ENABLE_KIS_SIDECAR": "1",
            "AG_KIS_SIDECAR_FETCH_QUOTE": "1",
            "AG_KIS_SIDECAR_FETCH_DAILY": "1",
            "AG_KIS_SIDECAR_FETCH_MINUTE": "1",
            "AG_KIS_SIDECAR_FETCH_FLOW": "1",
            "AG_KIS_SIDECAR_FETCH_RANK": "1",
            "AG_KIS_SIDECAR_FETCH_VI": "1",
            "AG_KIS_SIDECAR_FETCH_NEWS": "1",
            "KIS_LIVE_CALL_SLEEP_SEC": str(args.kis_call_sleep_sec),
            "AG_KIS_SIDECAR_CALL_SLEEP_SEC": str(args.sidecar_call_sleep_sec),
            "MPLCONFIGDIR": str(PROJECT_ROOT / "runtime_state" / "local_short_term" / "matplotlib_cache"),
        }
    )
    return env


def _load_batch_universe(limit: int):
    previous_provider = os.environ.get("AG_KR_UNIVERSE_PROVIDER")
    os.environ["AG_KR_UNIVERSE_PROVIDER"] = "fdr"
    try:
        return _load_kr_universe(int(limit))
    finally:
        if previous_provider is None:
            os.environ.pop("AG_KR_UNIVERSE_PROVIDER", None)
        else:
            os.environ["AG_KR_UNIVERSE_PROVIDER"] = previous_provider


def _run_command(command: Sequence[str], *, env: Mapping[str, str], timeout_sec: float = 0.0) -> Dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.Popen(
        list(command),
        cwd=str(PROJECT_ROOT),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    timed_out = False

    def _kill_on_timeout() -> None:
        nonlocal timed_out
        timed_out = True
        proc.kill()

    timer = None
    if timeout_sec and timeout_sec > 0:
        timer = threading.Timer(float(timeout_sec), _kill_on_timeout)
        timer.daemon = True
        timer.start()

    output_lines: List[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
            output_lines.append(line.rstrip("\n"))
        returncode = proc.wait()
    finally:
        if timer is not None:
            timer.cancel()
    return {
        "returncode": returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "timeout": timed_out,
        "scan_exception_reasons": _scan_exception_reasons(output_lines),
        "output_tail": _tail_lines(output_lines),
    }


def _run_with_retries(command: Sequence[str], *, env: Mapping[str, str], retries: int, timeout_sec: float) -> Dict[str, Any]:
    attempts: List[Dict[str, Any]] = []
    max_attempts = max(1, int(retries) + 1)
    result: Dict[str, Any] = {}
    for attempt_index in range(max_attempts):
        if attempt_index > 0:
            print(f"[retry {attempt_index}/{max_attempts - 1}] rerun failed batch command", flush=True)
        result = _run_command(command, env=env, timeout_sec=float(timeout_sec))
        attempt = dict(result)
        attempt["attempt"] = attempt_index + 1
        attempts.append(attempt)
        if int(result.get("returncode") or 0) == 0:
            break
    result = dict(result)
    result["attempts"] = attempts
    result["retry_count"] = max(0, len(attempts) - 1)
    return result


def _initial_state(args: argparse.Namespace, rows: Sequence[Mapping[str, str]], batches: Sequence[Sequence[Mapping[str, str]]]) -> Dict[str, Any]:
    return {
        "run_id": _kst_timestamp(),
        "tool": "run_kis_full_kr_scanner_batches",
        "batch_size": int(args.batch_size),
        "batch_count_requested": int(args.batch_count),
        "chunk_mode": "batch_count" if int(args.batch_count) > 0 else "batch_size",
        "workers": int(args.workers),
        "limit_per_market": int(args.limit),
        "retries": int(args.retries),
        "batch_timeout_sec": float(args.batch_timeout_sec),
        "universe_count": len(rows),
        "batch_count": len(batches),
        "created_at": datetime.now().isoformat(),
        "kis_only": True,
        "dry_run": bool(args.dry_run),
        "batches": [],
        "summary": {
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "pending": len(batches),
        },
    }


def _summarize(state: MutableMapping[str, Any], total_batches: int) -> None:
    records = list(state.get("batches") or [])
    completed = sum(1 for item in records if item.get("status") == "completed")
    failed = sum(1 for item in records if item.get("status") == "failed")
    skipped = sum(1 for item in records if item.get("status") == "skipped")
    state["summary"] = {
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "pending": max(0, total_batches - completed - failed - skipped),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if args.batch_size < 1:
        raise ValueError("--batch-size must be >= 1")
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")

    df = _load_batch_universe(int(args.limit))
    rows = [
        {"Code": str(row["Code"]), "Name": str(row["Name"])}
        for _, row in df.iterrows()
        if str(row.get("Code") or "").strip()
    ]
    batches = (
        _chunk_rows_by_count(rows, int(args.batch_count))
        if int(args.batch_count) > 0
        else _chunk_rows(rows, int(args.batch_size))
    )
    state_path = Path(args.state_path).resolve() if args.state_path else _default_state_path(int(args.batch_size))
    state = _load_state(state_path) if args.resume else {}
    if not state:
        state = _initial_state(args, rows, batches)

    existing_by_index = {int(item.get("batch_index")): item for item in list(state.get("batches") or [])}
    env = _kis_batch_env(args)
    executed = 0

    for batch_index, batch_rows in enumerate(batches):
        if batch_index < int(args.start_batch):
            continue
        if args.max_batches > 0 and executed >= int(args.max_batches):
            break

        prior = existing_by_index.get(batch_index)
        if args.resume and prior and prior.get("status") == "completed":
            print(f"[batch {batch_index + 1}/{len(batches)}] skip completed", flush=True)
            continue

        tickers = _ticker_arg(batch_rows)
        record: Dict[str, Any] = {
            "batch_index": batch_index,
            "batch_number": batch_index + 1,
            "batch_count": len(batches),
            "ticker_count": len(batch_rows),
            "tickers": [row["Code"] for row in batch_rows],
            "names": {row["Code"]: row["Name"] for row in batch_rows},
            "started_at": datetime.now().isoformat(),
        }

        command = [
            sys.executable,
            str(LIVE_SCAN_TOOL),
            "--workers",
            str(args.workers),
            "--tickers",
            tickers,
            "--allow-empty-results",
        ]
        record["command"] = command
        print(
            f"[batch {batch_index + 1}/{len(batches)}] start "
            f"ticker_count={record['ticker_count']} tickers={_ticker_preview(record['tickers'])}",
            flush=True,
        )
        if args.dry_run:
            record.update({"status": "skipped", "returncode": None, "elapsed_sec": 0.0, "output_tail": []})
        else:
            result = _run_with_retries(
                command,
                env=env,
                retries=max(0, int(args.retries)),
                timeout_sec=max(0.0, float(args.batch_timeout_sec)),
            )
            record.update(result)
            record["status"] = (
                "completed"
                if int(result.get("returncode") or 0) == 0
                and not result.get("timeout")
                and not result.get("scan_exception_reasons")
                else "failed"
            )

        state_batches = [item for item in list(state.get("batches") or []) if int(item.get("batch_index")) != batch_index]
        state_batches.append(record)
        state["batches"] = sorted(state_batches, key=lambda item: int(item.get("batch_index")))
        state["updated_at"] = datetime.now().isoformat()
        _summarize(state, len(batches))
        _write_state(state_path, state)
        print(f"[batch {batch_index + 1}/{len(batches)}] {record['status']} state={state_path}", flush=True)

        executed += 1
        if record["status"] == "failed" and args.fail_fast:
            break

    _summarize(state, len(batches))
    _write_state(state_path, state)
    print(json.dumps({"state_path": str(state_path), "summary": state.get("summary")}, ensure_ascii=False, indent=2))
    return dict(state)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run KIS-only full KR scanner in small checkpointed batches.")
    parser.add_argument("--batch-size", type=int, default=3, help="Tickers per batch. Use 2 or 3 for conservative KIS runs.")
    parser.add_argument("--batch-count", type=int, default=0, help="Split the whole universe into this many batches; overrides --batch-size.")
    parser.add_argument("--workers", type=int, default=1, help="Workers passed to each live_full_kr_swing_scan batch.")
    parser.add_argument("--limit", type=int, default=100000, help="Per-market universe limit passed to loader.")
    parser.add_argument("--start-batch", type=int, default=0, help="0-based batch index to start from.")
    parser.add_argument("--max-batches", type=int, default=0, help="Optional cap on batches to execute; 0 means no cap.")
    parser.add_argument("--state-path", default="", help="Checkpoint JSON path. Defaults to a timestamped validation report.")
    parser.add_argument("--resume", action="store_true", help="Skip completed batches in the checkpoint file.")
    parser.add_argument("--dry-run", action="store_true", help="Write planned batches without executing live scans.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop at first failed batch.")
    parser.add_argument("--retries", type=int, default=0, help="Retries per failed batch before marking it failed.")
    parser.add_argument("--batch-timeout-sec", type=float, default=0.0, help="Optional hard timeout per batch attempt; 0 disables.")
    parser.add_argument("--kis-call-sleep-sec", type=float, default=0.18)
    parser.add_argument("--sidecar-call-sleep-sec", type=float, default=0.40)
    args = parser.parse_args()
    try:
        state = run(args)
        return 1 if any(item.get("status") == "failed" for item in state.get("batches") or []) else 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
