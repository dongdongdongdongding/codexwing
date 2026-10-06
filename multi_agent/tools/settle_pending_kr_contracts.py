#!/usr/bin/env python3
"""Passive KR settlement, including retired lanes. Dry run unless --apply.

Only missing outcomes are populated. Backups and before/after hashes precede
replacement; a concurrent ledger change aborts replacement. No scoring/routing.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from modules.kr_contract_settlement import settle


def digest(data):
    return hashlib.sha256(data).hexdigest()


def apply_verified(path, before, rows, audit):
    after = ("\n".join(json.dumps(r, ensure_ascii=False, allow_nan=False) for r in rows) + "\n").encode()
    audit.mkdir(parents=True, exist_ok=True)
    backup = audit / (path.name + "." + digest(before) + ".bak")
    if not backup.exists():
        backup.write_bytes(before)
    if backup.read_bytes() != before:
        raise RuntimeError("backup verification failed")
    record = {"path": str(path), "before_sha256": digest(before), "after_sha256": digest(after),
              "backup": str(backup), "at": datetime.now(timezone.utc).isoformat()}
    with (audit / "audit.jsonl").open("a") as log:
        log.write(json.dumps({**record, "state": "prepared"}) + "\n")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
        out.write(after)
        temporary = Path(out.name)
    try:
        if path.read_bytes() != before:
            raise RuntimeError("concurrent ledger change; retry from fresh snapshot")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    with (audit / "audit.jsonl").open("a") as log:
        log.write(json.dumps({**record, "state": "committed"}) + "\n")
    return record


def run(root, cache, today, apply=False):
    exp = root / "runtime_state/reports/experimental"
    definitions = [("kr_swing_candidate_ledger.jsonl", "policy_ret", "next_open"),
                   ("kospi_intraday_swing_ledger.jsonl", "exit_t5_h5", "signal_close")]
    work = []
    for name, field, mode in definitions:
        path = exp / name
        if not path.exists():
            continue
        before = path.read_bytes()
        rows = [json.loads(x) for x in before.splitlines() if x.strip()]
        pending = [r for r in rows if r.get(field) is None and r.get("settlement_status") != "unfilled_entry"]
        if pending:
            work.append((path, before, rows, pending, field, mode))
    if not work:
        return {"changed": 0, "errors": [], "applied": apply}
    minimum = min(r["date"] for _, _, _, pending, _, _ in work for r in pending)
    codes = sorted({r["ticker"].split(".")[0] for _, _, _, pending, _, _ in work for r in pending})
    source = cache / "px_delisted.parquet"
    filters = [("date", ">=", pd.Timestamp(minimum)), ("date", "<", pd.Timestamp(today))]
    dates = pd.read_parquet(source, columns=["date"], filters=filters)["date"]
    sessions = sorted(dates.dropna().unique())
    px = pd.read_parquet(source, columns=["code", "date", "adj_open", "adj_high", "adj_low", "adj_close", "volume"],
                         filters=filters + [("code", "in", codes)])
    groups = {str(code): g for code, g in px.groupby("code")}
    result = {"changed": 0, "errors": [], "pending": 0, "unfilled": 0, "applied": apply,
              "source": str(source), "source_mtime_ns": source.stat().st_mtime_ns,
              "price_as_of": str(pd.Timestamp(max(sessions)).date()) if sessions else None, "changes": []}
    for path, before, rows, pending, field, mode in work:
        changes = []
        for row in pending:
            bars = groups.get(row["ticker"].split(".")[0])
            if bars is None:
                result["errors"].append({"ticker": row["ticker"], "reason": "missing_symbol"})
                continue
            horizon = int(row.get("contract_h") or row.get("hold_days") or 5)
            outcome = settle(bars, sessions, row["date"], horizon, float(row.get("contract_tp") or .05), mode)
            status = outcome["status"]
            if status == "data_error":
                result["errors"].append({"ticker": row["ticker"], "date": row["date"], **outcome})
                continue
            if status == "pending":
                result["pending"] += 1
                continue
            if status == "unfilled_entry":
                result["unfilled"] += 1
            else:
                row[field] = round(outcome["policy_ret"], 4)
                if mode == "next_open":
                    row["entry_open"] = round(outcome["entry_open"], 4)
                    row["ft_touch5"] = outcome["touch"]
                else:
                    # Preserve already settled diagnostics; fill only missing fields.
                    for tp, h, ret_key, hit_key in ((.10, 5, "exit_t10_h5", None), (.05, 3, None, "touch5")):
                        extra = settle(bars, sessions, row["date"], h, tp, mode)
                        if extra["status"] == "resolved":
                            if ret_key and row.get(ret_key) is None:
                                row[ret_key] = round(extra["policy_ret"], 4)
                            if hit_key and row.get(hit_key) is None:
                                row[hit_key] = extra["touch"]
                    for h, key in ((3, "ret3d"), (5, "ret5d")):
                        future = bars[bars.date > pd.Timestamp(row["date"])].sort_values("date")
                        if row.get(key) is None and len(future) >= h and future.iloc[h-1].volume > 0:
                            row[key] = round((float(future.iloc[h-1].adj_close) / outcome["entry_open"] - 1) * 100, 4)
            row["settlement_status"] = status
            row["settlement_evidence"] = {**outcome, "source": str(source), "price_as_of": result["price_as_of"],
                                           "at": datetime.now(timezone.utc).isoformat()}
            changes.append({"ticker": row["ticker"], "date": row["date"], "field": field, **outcome})
        if changes:
            if apply:
                apply_verified(path, before, rows, root / "runtime_state/audit/kr_settlement")
            result["changes"].extend(changes)
            result["changed"] += len(changes)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--cache", type=Path, default=Path.home() / "research_cache")
    ap.add_argument("--today", default=datetime.now(timezone.utc).date().isoformat())
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    result = run(args.root, args.cache, args.today, args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
