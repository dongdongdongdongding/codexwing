"""Bounded, resumable KIS collection, newest observed session first.

The four requested slices are an acquisition checkpoint, NOT proof of a complete
trading session. Existing bars are retained. All writes use verified backups,
compare-and-set, atomic replacement and an audit. No liquidity universe cutoff.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from modules.kis_operational_adapter import normalize_kis_minute_bars
from multi_agent.tools.intraday_cache_journal import digest, atomic_write, save_json, prepare_states
import uuid

HOURS = ("153000", "133000", "113000", "100000")
KST = ZoneInfo("Asia/Seoul")
VERSION = 1


class BudgetExpired(Exception):
    pass


class StorageBudgetExceeded(Exception):
    pass


def targets(panel, now, retention, close_time=(15, 30)):
    """Include every observed code/date pair in the retention window, even delisted codes."""
    frame = panel.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    if not frame.code.str.fullmatch(r"[0-9]{6}").all():
        raise ValueError("invalid_panel_code")
    today = pd.Timestamp(now.date())
    latest = today if (now.hour, now.minute) >= close_time else today - pd.Timedelta(days=1)
    frame = frame[(frame.date >= today-pd.Timedelta(days=retention)) & (frame.date <= latest)]
    if frame.empty:
        raise ValueError("no_observed_closed_sessions_in_retention_window")
    return {day.strftime("%Y%m%d"): sorted(set(rows.code))
            for day, rows in frame.groupby("date", sort=True)}


def legacy_writers(cache, process_text=None, entrypoints=("intraday_backfill.py",)):
    if process_text is None:
        process_text = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    result = []
    for line in process_text.splitlines():
        bits = line.strip().split(None, 1)
        if len(bits) != 2 or not bits[0].isdigit() or int(bits[0]) == os.getpid():
            continue
        try:
            argv = shlex.split(bits[1])
        except ValueError:
            continue
        # Legacy Python jobs do not honor our lock. Refuse coexistence with any
        # directly executed old entry point (including relative script paths).
        if argv and "python" in Path(argv[0]).name.lower() and any(
                Path(arg).name in entrypoints for arg in argv[1:]):
            result.append(int(bits[0]))
    return result


@contextmanager
def request_deadline(seconds):
    """Bound even token refresh, throttling and retries inside a single API call."""
    if seconds <= 0:
        raise BudgetExpired()
    def expired(*_):
        raise BudgetExpired()
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def filter_bars(frame, day, session_start="09:00", session_end="15:30"):
    if frame.empty:
        return frame
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is not None:
        raise ValueError("expected_naive_KST_datetime_index")
    frame = frame.loc[(frame.index.strftime("%Y%m%d") == day)]
    frame = frame.between_time(session_start, session_end)
    values = frame[["Open", "High", "Low", "Close", "Volume"]].apply(pd.to_numeric, errors="coerce")
    valid = (values.notna().all(axis=1) & values.apply(lambda col: col.map(math.isfinite)).all(axis=1)
             & (values[["Open", "High", "Low", "Close"]] > 0).all(axis=1)
             & (values.Volume >= 0) & (values.High >= values[["Open", "Close", "Low"]].max(axis=1))
             & (values.Low <= values[["Open", "Close", "High"]].min(axis=1)))
    if not valid.all():
        raise ValueError("invalid_minute_OHLCV")
    return frame.loc[~frame.index.duplicated(keep="first")].sort_index()


def persist_bars(path, old, added, before_sha, audit, code, day, min_free_bytes=10*1024**3):
    """Never overwrite a damaged/unreadable cache or a concurrently changed file."""
    combined = pd.concat([old, added]) if old is not None else added
    combined = combined.loc[~combined.index.duplicated(keep="first")].sort_index()
    if old is not None and combined.equals(old):
        if digest(path) != before_sha:
            raise ValueError("cache_changed_concurrently")
        return old  # Validating existing slices is not a cache mutation.
    estimate = 3*max(path.stat().st_size if path.exists() else 0,
                     int(combined.memory_usage(index=True,deep=True).sum()))
    if shutil.disk_usage(path.parent).free < min_free_bytes + estimate:
        raise StorageBudgetExceeded("insufficient_space_for_verified_backup_and_replace")
    audit.mkdir(parents=True, exist_ok=True)
    recovery = prepare_states(path, old, combined, before_sha)
    record = {"code": code, "day": day, "before_sha256": before_sha,
              "recovery": recovery, "status": "PREPARED"}
    record_path = audit / f"{code}-{day}-{uuid.uuid4().hex}.json"
    save_json(record_path, record)
    def write(temp):
        combined.to_parquet(temp)
        # A complete readable temporary file must exist before replacing the cache.
        verified = pd.read_parquet(temp)
        if not verified.equals(combined):
            raise ValueError("parquet_verification_failed")
        if digest(path) != before_sha:
            raise ValueError("cache_changed_concurrently")
    atomic_write(path, write)
    record.update(status="APPLIED", after_sha256=digest(path), rows=len(combined))
    save_json(record_path, record)
    save_json(Path(recovery["head_path"]), {"file_sha256": record["after_sha256"],
                                          "state": recovery["after_state"]})
    return combined


def collect(schedule, out, client, budget=7200., pause=.03, *, clock=time.monotonic,
            sleep=time.sleep, now=None, bounded_request=True, progress=print, min_free_bytes=10*1024**3,
            hours=HOURS, market_div="J", session_start="09:00", session_end="15:30",
            universe="all_observed_panel_pairs"):
    start = clock()
    deadline = start + budget
    now = now or datetime.now(KST)
    run_id = now.strftime("%Y%m%dT%H%M%S%f")
    state_dir = out / ".backfill"
    audit = state_dir / "audit" / run_id
    report = {"version": VERSION, "status": "RUNNING", "run_id": run_id,
              "latest_observed_session": max(schedule), "target_pairs": sum(map(len, schedule.values())),
              "requests": 0, "pairs_attempted": 0, "pairs_skipped": 0, "rows_received": 0, "rows_added":0,
              "request_errors": [], "storage_errors": [], "requested_all_slices": 0,
              "empty_pairs": 0, "empty_responses": 0, "retry_deferred_pairs": 0, "budget_seconds": budget,
              "session_completeness": "NOT_ESTABLISHED", "universe": universe,
              "market_div": market_div, "session_start": session_start, "session_end": session_end,
              "minimum_free_bytes":min_free_bytes}
    blocked_codes = set()
    states = {}
    for day in sorted(schedule, reverse=True):
        for code in schedule[day]:
            if shutil.disk_usage(out).free < min_free_bytes:
                report["status"] = "STORAGE_BUDGET_EXHAUSTED"
                break
            if clock() >= deadline:
                report["status"] = "BUDGET_EXHAUSTED"
                break
            if code in blocked_codes:
                continue
            path = out / f"{code}.parquet"
            state_path = state_dir / f"{code}.json"
            try:
                if code not in states:
                    states[code] = json.loads(state_path.read_text()) if state_path.exists() else {"days": {}}
                state = states[code]
                stat = path.stat() if path.exists() else None
                identity = [stat.st_mtime_ns, stat.st_size] if stat else None
                if state.get("identity") != identity:
                    state = states[code] = {"days": {}}  # external writer invalidates checkpoints
                cell = state["days"].get(day, {})
                if cell.get("status") == "REQUESTED_ALL_SLICES" or cell.get("retry_after", 0) > now.timestamp():
                    report["pairs_skipped"] += 1
                    if cell.get("status") != "REQUESTED_ALL_SLICES":
                        report["retry_deferred_pairs"] += 1
                    continue
                before_sha = digest(path)
                old = pd.read_parquet(path) if path.exists() else None
                if old is not None and (not isinstance(old.index, pd.DatetimeIndex) or
                                         old.index.tz is not None or old.index.hasnans or old.index.has_duplicates):
                    raise ValueError("invalid_existing_cache_index")
            except Exception as exc:
                blocked_codes.add(code)
                report["storage_errors"].append({"code": code, "error": type(exc).__name__})
                continue
            report["pairs_attempted"] += 1
            succeeded = set(cell.get("successful_hours", []))
            parts = []
            for hour in hours:
                if hour in succeeded:
                    continue
                if clock() >= deadline:
                    report["status"] = "BUDGET_EXHAUSTED"
                    break
                report["requests"] += 1
                try:
                    kwargs = dict(trade_date=day, input_hour=hour, include_past=True)
                    if market_div != "J":
                        kwargs["market_div"] = market_div
                    if bounded_request:
                        with request_deadline(deadline-clock()):
                            payload = client.daily_minute_bars(code, **kwargs)
                    else:
                        payload = client.daily_minute_bars(code, **kwargs)
                    frame = filter_bars(normalize_kis_minute_bars(code, payload, trade_date=day), day,
                                        session_start, session_end)
                    if len(frame):
                        frame["code"] = code
                        parts.append(frame)
                        succeeded.add(hour)
                    else:
                        report["empty_responses"] += 1
                except BudgetExpired:
                    report["status"] = "BUDGET_EXHAUSTED"
                    break
                except Exception as exc:
                    report["request_errors"].append({"code": code, "day": day, "hour": hour,
                                                     "error": type(exc).__name__})
                sleep(min(pause, max(0., deadline-clock())))
            try:
                if parts:
                    added = pd.concat(parts)
                    before_rows = len(old) if old is not None else 0
                    old = persist_bars(path, old, added, before_sha, audit, code, day, min_free_bytes)
                    report["rows_added"] += len(old)-before_rows
                    report["rows_received"] += len(added)
                elif digest(path) != before_sha:
                    raise ValueError("cache_changed_concurrently")
                observed = filter_bars(old, day, session_start, session_end) if old is not None else pd.DataFrame()
                all_slices = len(succeeded) == len(hours)
                cell = {"successful_hours": sorted(succeeded), "rows_observed": len(observed),
                        "first_bar": str(observed.index.min()) if len(observed) else None,
                        "last_bar": str(observed.index.max()) if len(observed) else None,
                        "session_complete": None,
                        "status": "REQUESTED_ALL_SLICES" if all_slices and len(observed) else "PARTIAL_OR_EMPTY"}
                if all_slices and len(observed):
                    report["requested_all_slices"] += 1
                elif not len(observed):
                    report["empty_pairs"] += 1
                if not (all_slices and len(observed)) and report["status"] != "BUDGET_EXHAUSTED":
                    cell["retry_after"] = now.timestamp() + 24*3600
                state["days"][day] = cell
                stat = path.stat() if path.exists() else None
                state["identity"] = [stat.st_mtime_ns, stat.st_size] if stat else None
                save_json(state_path, state)
            except StorageBudgetExceeded:
                report["status"] = "STORAGE_BUDGET_EXHAUSTED"
                break
            except Exception as exc:
                blocked_codes.add(code)
                report["storage_errors"].append({"code": code, "error": type(exc).__name__})
            if report["pairs_attempted"] % 10 == 0:
                progress(f"[intraday] session={day} pairs={report['pairs_attempted']} requests={report['requests']} elapsed={clock()-start:.1f}s", flush=True)
        if report["status"] in {"BUDGET_EXHAUSTED", "STORAGE_BUDGET_EXHAUSTED"}:
            break
    if report["status"] == "RUNNING":
        report["status"] = "PASS_FINISHED"  # a scheduling pass, not full session coverage
    report["elapsed_seconds"] = round(clock()-start, 3)
    report["unvisited_pairs"] = report["target_pairs"] - report["pairs_attempted"] - report["pairs_skipped"]
    report["audit_path"] = str(audit)
    save_json(state_dir / "latest.json", report)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=Path.home()/"research_cache")
    ap.add_argument("--budget", type=float, default=float(os.getenv("ITD_TIME_BUDGET", "7200")))
    ap.add_argument("--retention-days", type=int, default=int(os.getenv("ITD_RETENTION_DAYS", "355")))
    ap.add_argument("--sleep", type=float, default=float(os.getenv("ITD_SLEEP", ".03")))
    ap.add_argument("--plan", action="store_true", help="Read panel only; no API calls or cache writes")
    ap.add_argument("--min-free-gb", type=float, default=float(os.getenv("ITD_MIN_FREE_GB", "10")))
    args = ap.parse_args()
    if not math.isfinite(args.budget) or args.budget <= 0 or args.retention_days <= 0 or not math.isfinite(args.sleep) or args.sleep < 0 or not math.isfinite(args.min_free_gb) or args.min_free_gb < 0:
        ap.error("budget/retention must be positive; sleep and min-free-gb must be nonnegative")
    now = datetime.now(KST)
    schedule = targets(pd.read_parquet(args.cache/"px_long.parquet", columns=["code", "date"]), now, args.retention_days)
    codes = {code for members in schedule.values() for code in members}
    if int(os.getenv("ITD_UNIVERSE_N", "99999")) < len(codes):
        ap.error("ITD_UNIVERSE_N truncates observed universe; use the entire panel")
    summary = {"latest_observed_session": max(schedule), "oldest_session": min(schedule),
               "sessions": len(schedule), "codes": len(codes), "target_pairs": sum(map(len, schedule.values())),
               "order": "date_desc_then_code", "point_in_time_universe_verified": False}
    if args.plan:
        print(json.dumps(summary))
        return 0
    out = args.cache/"intraday"
    state_dir = out/".backfill"
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir/"writer.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "BUSY", "reason": "writer_lock"}))
            return 2
        pids = legacy_writers(args.cache)
        if pids:
            print(json.dumps({"status": "BUSY", "reason": "legacy_writer", "pids": pids}))
            return 2
        from dotenv import load_dotenv
        from modules.kis_openapi import KISOpenAPIClient
        load_dotenv(ROOT/".env.local")
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
        os.environ["KIS_LIVE_RETRY_COUNT"] = "0"  # resume next pass; do not burn the budget on retry storms
        client = KISOpenAPIClient(timeout=10.)
        print(json.dumps(summary), flush=True)
        report = collect(schedule, out, client, args.budget, args.sleep, now=now, min_free_bytes=int(args.min_free_gb*1024**3))
        print(json.dumps(report, ensure_ascii=False))
        return 1 if report["storage_errors"] or report["request_errors"] or report["status"] == "STORAGE_BUDGET_EXHAUSTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
