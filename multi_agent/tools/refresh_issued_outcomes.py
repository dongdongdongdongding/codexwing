"""Refresh current-cohort issued swing archive labels after adjusted prices update.

Dry-run by default. No new picks or rows are created, exclusions are preserved,
and every applied update has a verified backup and compare-and-set audit.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from multi_agent.tools.repair_issued_outcomes import recompute, audit_and_apply


def plan_refresh(rows, issued, prices, sessions):
    plan, problems = [], []
    counts = Counter()
    for row in rows:
        key = (row.get("run_id"),row.get("ticker"))
        pick = issued.get(key)
        if not pick:
            counts["not_in_issued_ledger"] += 1
            continue
        if (row.get("base_trade_date") != pick["date"] or
                row.get("entry_reference_price") != pick.get("close")):
            problems.append({"id":row["id"],"reason":"issued_reference_mismatch"})
            continue
        bars = prices[prices.code == row["ticker"].split(".")[0]]
        if len(sessions) == 0 or pick["date"] > str(max(sessions).date()):
            counts["waiting_signal_day_price"] += 1
            continue
        try:
            patch,basis = recompute(row,row,bars,sessions)
        except ValueError as exc:
            problems.append({"id":row["id"],"reason":str(exc)})
            continue
        # Refresh must never restore eligibility or alter any exclusion reason.
        patch.pop("validation_excluded",None)
        patch.pop("validation_excluded_reason",None)
        if patch:
            plan.append({"before":row,"patch":patch,"basis":basis})
        else:
            counts["unchanged"] += 1
    return plan,dict(counts),problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--cache",type=Path,default=Path.home()/"research_cache")
    ap.add_argument("--since",default="2026-08-24")
    ap.add_argument("--lookback-days",type=int,default=90)
    ap.add_argument("--apply",action="store_true")
    args = ap.parse_args()
    ledger = args.root/"runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl"
    raw = ledger.read_bytes()
    since = args.since
    if args.lookback_days > 0:
        since = max(since,(datetime.now(timezone.utc).date()-timedelta(days=args.lookback_days)).isoformat())
    issued = {}
    for line in raw.splitlines():
        pick = json.loads(line)
        if pick["date"] < since:
            continue
        key = ("SWING-CAND-"+pick["date"].replace("-",""),pick["ticker"])
        if key in issued:
            raise ValueError("duplicate issued key; cannot infer original pick")
        issued[key] = pick
    from modules.db_manager import DBManager
    client = DBManager().client
    if client is None:
        raise RuntimeError("database unavailable; run from configured service checkout")
    run_ids = sorted({k[0] for k in issued})
    rows = []
    for start in range(0,len(run_ids),20):
        batch = client.table("market_scan_results").select("*").in_("run_id",run_ids[start:start+20]).limit(1000).execute().data
        if len(batch) >= 1000:
            raise RuntimeError("bounded database read may be truncated")
        rows.extend(batch)
    source = args.cache/"px_delisted.parquet"
    calendar = args.cache/"px_long.parquet"
    stamps = {p:p.stat().st_mtime_ns for p in [source,calendar,ledger]}
    codes = sorted({p["ticker"].split(".")[0] for p in issued.values()})
    prices = pd.read_parquet(source,columns=["code","date","adj_close","adj_high","volume"],
                             filters=[("date",">=",pd.Timestamp(since)),("code","in",codes)])
    sessions = pd.to_datetime(pd.read_parquet(calendar,columns=["date"]).date.drop_duplicates()).sort_values()
    if prices.empty and issued:
        raise RuntimeError("no adjusted prices for issued scope")
    asof = prices.date.max()
    mature_sessions = sessions[sessions <= asof]
    plan,counts,problems = plan_refresh(rows,issued,prices,mature_sessions)
    audit = args.root/"runtime_state/audit/issued_outcomes_refresh"
    audit.mkdir(parents=True,exist_ok=True)
    # Preserve precisely the price rows used, not merely the path of a moving cache.
    evidence = prices.to_json(orient="records",date_format="iso").encode()
    price_sha = hashlib.sha256(evidence).hexdigest()
    price_backup = audit/f"prices_{price_sha}.json"
    price_backup.write_bytes(evidence)
    if price_backup.read_bytes() != evidence:
        raise RuntimeError("price backup verification failed")
    def source_guard():
        if any(p.stat().st_mtime_ns != stamp for p,stamp in stamps.items()) or ledger.read_bytes() != raw:
            raise RuntimeError("inputs changed while planning; rerun")
    source_guard()
    result = audit_and_apply(plan,audit,{"ledger_sha256":hashlib.sha256(raw).hexdigest(),
        "price_snapshot":str(price_backup),"price_sha256":price_sha,
        "calendar_sessions":[str(d.date()) for d in mature_sessions],"since":since},
        client,args.apply,source_guard)
    result.update(generated_at=datetime.now(timezone.utc).isoformat(),rows_read=len(rows),issued_picks=len(issued),
                  price_asof=str(asof.date()) if pd.notna(asof) else None,
                  price_lag_sessions=int((sessions > asof).sum()),counts=counts,problems=problems,
                  missing_archive_keys=[list(k) for k in issued if k not in {(r["run_id"],r["ticker"]) for r in rows}])
    report = args.root/"runtime_state/reports/validation/issued_outcomes_refresh_latest.json"
    report.parent.mkdir(parents=True,exist_ok=True)
    tmp = report.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    tmp.replace(report)
    print(json.dumps(result,ensure_ascii=False))
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
