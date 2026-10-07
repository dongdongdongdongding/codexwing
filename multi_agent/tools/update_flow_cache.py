"""Auditable, append-only KIS flow collection; never equate failed calls with freshness.

The existing top-liquidity cohort is a collection scope, not a PIT universe.
Amounts retain their raw provider units. Historical rows are never revised here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.backfill_kr_intraday import request_deadline

FIELDS = dict(frgn_ntby="frgn_ntby_qty", orgn_ntby="orgn_ntby_qty",
              prsn_ntby="prsn_ntby_qty", frgn_val="frgn_ntby_tr_pbmn",
              orgn_val="orgn_ntby_tr_pbmn", acml_val="acml_tr_pbmn")
COLUMNS = ["code", "date", *FIELDS]


def sha(path):
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


def parse_rows(payload, code, today):
    if not isinstance(payload, dict) or str(payload.get("rt_cd")) != "0":
        raise ValueError("provider_failure")
    rows = payload.get("output2")
    if not isinstance(rows, list):
        raise ValueError("missing_output2")
    parsed = {}
    excluded = 0
    for row in rows:
        rawdate = row.get("stck_bsop_date")
        if not isinstance(rawdate, str) or not re.fullmatch(r"\d{8}", rawdate):
            raise ValueError("invalid_date")
        date = pd.to_datetime(rawdate, format="%Y%m%d", errors="raise")
        if date >= today:
            excluded += 1
            continue
        item = {"code": code, "date": date}
        for field, source in FIELDS.items():
            value = row.get(source)
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise ValueError("missing_numeric_" + source)
            value = str(value)
            if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)", value):
                raise ValueError("invalid_numeric_" + source)
            number = int(value.replace(",", ""))
            if not -(2**63) <= number < 2**63 or (field == "acml_val" and number < 0):
                raise ValueError("out_of_range_" + source)
            item[field] = number
        if date in parsed and parsed[date] != item:
            raise ValueError("conflicting_provider_duplicate")
        parsed[date] = item
    return list(parsed.values()), excluded


def validate_old(old):
    if list(old.columns) != COLUMNS:
        raise ValueError("unexpected_cache_schema")
    if old.isna().any().any() or old.duplicated(["code", "date"]).any():
        raise ValueError("invalid_existing_cache")
    if not old.code.map(lambda x: isinstance(x, str) and bool(re.fullmatch(r"\d{6}", x))).all():
        raise ValueError("invalid_existing_code")
    if not pd.api.types.is_datetime64_ns_dtype(old.date) or not (old.date == old.date.dt.normalize()).all():
        raise ValueError("invalid_existing_dates")
    if any(not pd.api.types.is_integer_dtype(old[f]) for f in FIELDS):
        raise ValueError("invalid_existing_numbers")


def collect(cache, audit, client, *, now, universe=600, apply=False):
    """Caller owns the writer lock. Partial success is saved but returns degraded."""
    today = pd.Timestamp(now.astimezone(ZoneInfo("Asia/Seoul")).date())
    target = cache / "flow.parquet"
    before = sha(target)
    old = pd.read_parquet(target) if target.exists() else pd.DataFrame({
        "code": pd.Series(dtype=str), "date": pd.Series(dtype="datetime64[ns]"),
        **{k: pd.Series(dtype="int64") for k in FIELDS}})
    validate_old(old)
    px_path = cache / "px_long.parquet"
    px_sha = sha(px_path)
    px = pd.read_parquet(px_path, columns=["code", "date", "liq"])
    px["date"] = pd.to_datetime(px.date)
    px = px[px.date < today]
    if px.empty or px_sha != sha(px_path):
        raise ValueError("missing_or_changing_price_calendar")
    recent = px[px.date >= px.date.max() - pd.Timedelta(days=120)]
    codes = recent.groupby("code").liq.median().sort_values(ascending=False).head(universe).index.tolist()
    if not codes or any(not isinstance(c, str) or not re.fullmatch(r"\d{6}", c) for c in codes):
        raise ValueError("invalid_cohort")
    expected = px[px.code.isin(codes)].groupby("code").date.max()
    existing = old[old.code.isin(codes)].set_index(["code", "date"])
    additions, evidence = [], []
    for code in codes:
        record = {"code": code, "expected_latest": str(expected[code].date()),
                  "status": "error", "added_rows": 0, "overlap_conflicts": 0}
        try:
            with request_deadline(30):
                payload = client.investor_trading_daily(code, trade_date=today.strftime("%Y%m%d"))
            capture = audit / (code + ".json")
            write_json(capture, payload)
            record["capture_sha256"] = sha(capture)
            rows, excluded = parse_rows(payload, code, today)
            record.update(status="valid" if rows else "empty", returned_rows=len(rows),
                          excluded_current_or_future_rows=excluded)
            for row in rows:
                key = (code, row["date"])
                if key in existing.index:
                    if any(int(existing.loc[key, f]) != row[f] for f in FIELDS):
                        record["overlap_conflicts"] += 1
                    continue
                additions.append(row)
                record["added_rows"] += 1
        except Exception as exc:
            # Provider exception messages can contain request details: store the class only.
            record["error_type"] = type(exc).__name__
        evidence.append(record)
        if len(evidence) % 100 == 0:
            print(f"flow collected {len(evidence)}/{len(codes)}", flush=True)
    result = pd.concat([old, pd.DataFrame(additions, columns=COLUMNS)], ignore_index=True) if additions else old
    validate_old(result)
    latest = result.groupby("code").date.max()
    result_keys = set(zip(result.code, result.date))
    for row in evidence:
        day = latest.get(row["code"])
        row["cached_latest"] = str(day.date()) if pd.notna(day) else None
        row["covers_expected_latest"] = (row["code"], expected[row["code"]]) in result_keys
    counts = {"requested_symbols": len(codes), "valid_symbols": sum(x["status"] == "valid" for x in evidence),
              "error_symbols": sum(x["status"] == "error" for x in evidence),
              "empty_symbols": sum(x["status"] == "empty" for x in evidence),
              "stale_symbols": sum(not x["covers_expected_latest"] for x in evidence),
              "overlap_conflicts": sum(x["overlap_conflicts"] for x in evidence),
              "added_rows": len(additions), "existing_rows": len(old), "result_rows": len(result)}
    degraded = any(counts[k] for k in ("error_symbols", "empty_symbols", "stale_symbols", "overlap_conflicts"))
    report = {"status": "degraded" if degraded else "ok", "apply": apply, **counts,
              "source": "KIS:investor_trading_daily:J:raw_provider_units",
              "cohort": "current_120_calendar_day_median_liquidity_collection_only",
              "historical_completeness_verified": False, "point_in_time_universe": False,
              "excluded_on_or_after": str(today.date()), "price_calendar_latest": str(px.date.max().date()),
              "cache_latest": str(result.date.max().date()) if len(result) else None,
              "cache_before_sha256": before, "price_calendar_sha256": px_sha, "symbols": evidence,
              "audit_dir": str(audit), "committed": False}
    write_json(audit / "plan.json", report)
    if apply and additions:
        if sha(target) != before:
            raise RuntimeError("cache_changed_during_collection")
        backup = audit / "flow.before.parquet"
        if target.exists():
            shutil.copy2(target, backup)
            if sha(backup) != before:
                raise RuntimeError("backup_mismatch")
        temp = target.with_name("flow." + audit.name + ".tmp.parquet")
        try:
            result.to_parquet(temp, index=False)
            with temp.open("rb") as f:
                os.fsync(f.fileno())
            if sha(target) != before:
                raise RuntimeError("cache_changed_before_commit")
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        report["committed"] = True
    report["cache_after_sha256"] = sha(target)
    write_json(audit / "result.json", report)
    return report


def legacy_writers():
    lines = subprocess.check_output(["ps", "-axo", "pid=,comm=,args="], text=True).splitlines()
    found = []
    for line in lines:
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and int(parts[0]) != os.getpid() and "python" in parts[1].lower():
            if any(Path(token).name in {"flow_update.py", "flow_bf.py"} for token in parts[2].split()):
                found.append(int(parts[0]))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path.home() / "research_cache")
    parser.add_argument("--report", type=Path, default=Path(os.environ.get("FLOW_RECEIPT_PATH",
        str(ROOT / "runtime_state/long_term/ops/flow_latest.json"))))
    parser.add_argument("--universe", type=int, default=int(os.environ.get("FLOW_UNIVERSE_N", "600")))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    audit = args.cache / ".flow_updates" / now.strftime("%Y%m%dT%H%M%S%f")
    audit.mkdir(parents=True)
    report = {"status": "running", "started_at": now.isoformat(), "audit_dir": str(audit)}
    write_json(args.report, report)
    try:
        if args.universe <= 0:
            raise ValueError("invalid_universe")
        with (args.cache / ".flow_writer.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if legacy_writers():
                raise RuntimeError("legacy_flow_writer_active")
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env.local")
            os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
            from modules.kis_openapi import KISOpenAPIClient
            report.update(collect(args.cache, audit, KISOpenAPIClient(timeout=8), now=now,
                                  universe=args.universe, apply=args.apply))
    except Exception as exc:
        report.update(status="failed", error_type=type(exc).__name__)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json(audit / "receipt.json", report)
    write_json(args.report, report)
    print(json.dumps({k: v for k, v in report.items() if k != "symbols"}, ensure_ascii=False), flush=True)
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
