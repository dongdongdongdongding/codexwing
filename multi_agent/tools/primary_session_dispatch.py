"""Durable session requests, independently serviced by KR, US and batch workers.

The launchd poller only records requests. A slow global batch cannot occupy the
poller or either scan worker. Files are receipts, not backdated market evidence.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from multi_agent.tools import run_primary_market_session_ops as ops

DEFAULT_QUEUE = ROOT / "runtime_state/long_term/ops/session_dispatch"
ROLES = {"kr_scan": "kr_confirmed_scan", "us_scan": "nasdaq_full_universe_scan",
         "daily_ops": "primary_daily_ops"}
SCRIPTS = {"kr_scan": "run_kr_daily_auto_scans.py",
           "us_scan": "run_us_full_universe_research.py", "daily_ops": "run_daily_ops.sh"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8",
                                     delete=False) as f:
        temp = Path(f.name)
        try:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


@contextmanager
def lock(path, *, blocking=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def requests(queue):
    return [json.loads(p.read_text()) for p in sorted((queue / "requests").glob("*.json"))]


def result_path(queue, request, role):
    return queue / "results" / request["id"] / (role + ".json")


def enqueue(spec, now, queue=DEFAULT_QUEUE):
    key = ops._state_key(spec, now)
    ident = key.replace("::", "__")
    path = queue / "requests" / (ident + ".json")
    with lock(queue / "enqueue.lock"):
        if path.exists():
            return json.loads(path.read_text())
        commands = ops.build_command_plan(spec)
        request = {"id": ident, "key": key, "session_id": spec.session_id,
                   "requested_at": stamp(), "due_evaluated_at": now.isoformat(),
                   "commands": commands}
        write_json(path, request)
        return request


def materialize(request, queue, state_path, report_dir):
    with lock(queue / "state.lock"):
        return _materialize_locked(request, queue, state_path, report_dir)


def _materialize_locked(request, queue, state_path, report_dir):
    commands = []
    for command in request["commands"]:
        role = next(k for k, v in ROLES.items() if v == command["name"])
        path = result_path(queue, request, role)
        result = json.loads(path.read_text()) if path.exists() else {"dispatch_status": "queued"}
        commands.append({**command, **result})
    pending = any(c["dispatch_status"] in ("queued", "running") for c in commands)
    failed = [c for c in commands if c.get("returncode", 0) != 0]
    superseded = any(c["dispatch_status"] == "superseded" for c in commands)
    status = ("running" if pending else "failed" if any(c["required"] for c in failed)
              else "degraded" if failed or superseded else "ok")
    spec = ops._session_map()[request["session_id"]]
    path = report_dir / ("primary_market_session_ops_" + request["id"] + "_dispatch.json")
    report = {"version": "primary_market_session_dispatch_v1", "generated_at": stamp(),
              "session_id": spec.session_id, "label_ko": spec.label_ko,
              "status": status, "dry_run": False, "markets": list(spec.markets),
              "scheduled_timezone": spec.timezone_name, "scheduled_trigger_time": spec.trigger_time,
              "scan_scope": spec.scan_scope, "requested_at": request["requested_at"],
              "due_evaluated_at": request["due_evaluated_at"], "commands": commands,
              "required_failure_count": sum(bool(c["required"]) for c in failed),
              "optional_failure_count": sum(not c["required"] for c in failed),
              "pending_command_count": sum(c["dispatch_status"] in ("queued", "running") for c in commands),
              "report_path": str(path)}
    if path.exists():
        old_report = json.loads(path.read_text())
        if {k: v for k, v in old_report.items() if k != "generated_at"} == {
                k: v for k, v in report.items() if k != "generated_at"}:
            report = old_report
    # Workers finish independently; merge only their request under one short lock.
    write_json(path, report)
    state = ops._load_state(state_path)
    state.setdefault("runs", {})[request["key"]] = {
        "session_id": spec.session_id, "status": status, "dry_run": False,
        "report_path": str(path), "recorded_at": report["generated_at"], "dispatch_request": request["id"]}
    write_json(state_path, state)
    return report


def dispatch(now, *, queue=DEFAULT_QUEUE, state_path=ops.DEFAULT_STATE_PATH,
             report_dir=ops.DEFAULT_REPORT_DIR, include_weekends=False, catch_up=True,
             due_window_minutes=10):
    with lock(queue / "poller.lock"):
        state = ops._load_state(state_path)
        # Durable requests remain authoritative if a legacy in-flight process
        # overwrites the old aggregate state during migration.
        for request in requests(queue):
            state.setdefault("runs", {}).setdefault(request["key"], {"status": "queued"})
        due = ops.due_sessions(now, state=state, include_weekends=include_weekends,
                               catch_up=catch_up, due_window_minutes=due_window_minutes)
        added = [enqueue(spec, now, queue) for spec in due]
        for request in requests(queue):
            materialize(request, queue, state_path, report_dir)
        return {"status": "dispatched", "sessions": [r["session_id"] for r in added],
                "queued_count": len(added), "execution_complete": False}


def legacy_pids(role):
    """Actual live child processes, not stale PID/lock files."""
    result = subprocess.run(["ps", "-axo", "pid=,args="], capture_output=True, text=True, check=True)
    found = []
    for line in result.stdout.splitlines():
        try:
            pid, command = line.strip().split(None, 1)
            argv = shlex.split(command)
            executable = Path(argv[0]).name.lower() if argv else ""
            if (int(pid) != os.getpid() and ("python" in executable or executable == "bash")
                    and any(Path(arg).name == SCRIPTS[role] for arg in argv[1:])):
                found.append(int(pid))
        except ValueError:
            continue
    return found


def worker(role, *, queue=DEFAULT_QUEUE, state_path=ops.DEFAULT_STATE_PATH,
           report_dir=ops.DEFAULT_REPORT_DIR, now=None):
    now = now or datetime.now(timezone.utc)
    with lock(queue / (role + ".lock"), blocking=False) as acquired:
        if not acquired:
            return {"status": "busy", "reason": "worker_lock"}
        busy = legacy_pids(role)
        if busy:
            return {"status": "busy", "reason": "live_command", "pids": busy}
        pending = []
        for request in requests(queue):
            command = next((c for c in request["commands"] if c["name"] == ROLES[role]), None)
            if command is None:
                continue
            path = result_path(queue, request, role)
            old = json.loads(path.read_text()) if path.exists() else None
            if old and old["dispatch_status"] == "running":
                # Lock is now ours and no command is alive: outcome unknown.
                # Do not execute a possibly completed scan twice after a crash.
                write_json(path, {**old, "dispatch_status": "interrupted", "returncode": 1,
                                  "finished_at": stamp(), "reason": "worker_exit_outcome_unknown"})
                materialize(request, queue, state_path, report_dir)
            elif old is None:
                spec = ops._session_map()[request["session_id"]]
                if role != "daily_ops" and ops._state_key(spec, now) != request["key"]:
                    write_json(path, {"dispatch_status": "superseded", "returncode": 0,
                                      "reason": "market_local_day_expired", "finished_at": stamp()})
                    materialize(request, queue, state_path, report_dir)
                else:
                    pending.append((request, command))
        if not pending:
            return {"status": "idle"}
        pending.sort(key=lambda pair: pair[0]["due_evaluated_at"])
        request, command = pending[-1]
        if role == "daily_ops":
            def batch_signature(cmd):
                return (cmd["argv"], {k: v for k, v in cmd["env"].items()
                                     if not k.startswith("AG_PRIMARY_SESSION_")})
            pending = [pair for pair in pending if batch_signature(pair[1]) == batch_signature(command)]
        prior = pending[:-1]
        started = stamp()
        if role != "daily_ops":
            # Never fabricate a scan at an older missed cutoff.
            for older, _ in prior:
                write_json(result_path(queue, older, role), {
                    "dispatch_status": "superseded", "returncode": 0,
                    "reason": "newer_pending_market_boundary", "superseded_by": request["id"],
                    "finished_at": started})
                materialize(older, queue, state_path, report_dir)
        served = pending if role == "daily_ops" else [(request, command)]
        for item, _ in served:
            write_json(result_path(queue, item, role), {"dispatch_status": "running",
                "started_at": started, "worker_pid": os.getpid(), "served_by": request["id"]})
            materialize(item, queue, state_path, report_dir)
        try:
            # Restoring computation does not authorize messaging other people.
            execution = {**command, "env": {**command.get("env", {}),
                "DISCORD_DRY_RUN": "1", "AG_STALE_FALLBACK_ALERT_DRY_RUN": "1",
                "AG_DRIFT_ALERT_DRY_RUN": "1"}}
            result = ops._run_command(execution, dry_run=False)
        except Exception as exc:
            result = {"returncode": 1, "started_at": started, "finished_at": stamp(),
                      "error": type(exc).__name__}
        for item, _ in served:
            write_json(result_path(queue, item, role), {**result, "dispatch_status": "finished",
                "served_by": request["id"], "shared_batch": role == "daily_ops" and len(served) > 1})
            materialize(item, queue, state_path, report_dir)
        return {"status": "finished", "role": role, "served": [x[0]["id"] for x in served],
                "returncode": result.get("returncode")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", required=True, choices=sorted(ROLES))
    args = parser.parse_args()
    result = worker(args.worker)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("returncode", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
