"""Recalculate quarantined archive daily labels from adjusted session closes.

These are signal-close returns, not next-open contract P&L. Issued reference
prices remain immutable. The original contract-repair backup supplies the scope
and prior exclusions; no unrelated exclusion is lifted. Dry-run by default.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.update_outcome_return_metrics import _compute_row_returns

QUARANTINE = "issued_reference_repaired_outcomes_need_recalculation"


def recompute(row, original, prices, sessions, *, price_source="px_delisted.parquet"):
    """Require every observed market session; never compress missing ticker bars."""
    day = pd.Timestamp(row["base_trade_date"])
    prices = prices.sort_values("date").copy()
    if prices.empty or prices.date.duplicated().any():
        raise ValueError("missing or duplicate price history")
    expected = pd.DatetimeIndex(sessions)
    expected = expected[expected >= day].sort_values()
    prices = prices[prices.date >= day]
    if expected.empty or expected[0] != day or set(expected) != set(prices.date):
        raise ValueError("incomplete market-session price coverage")
    if not (np.isfinite(prices.adj_close).all() and (prices.adj_close > 0).all()):
        raise ValueError("invalid adjusted prices")
    invalid_high = ~np.isfinite(prices.adj_high) | (prices.adj_high <= 0)
    no_trade = prices.get("volume",pd.Series(index=prices.index,dtype=float)).eq(0)
    if (invalid_high & ~no_trade).any():
        raise ValueError("invalid adjusted prices")
    # Keep suspended sessions in the calendar. A retained close is a valuation,
    # not an executable exit; missing highs cannot establish a full-window label.
    prices.loc[invalid_high & no_trade,"adj_high"] = np.nan
    hist = prices.rename(columns={"adj_close": "Close", "adj_high": "High"}).reset_index(drop=True)
    hist["trade_date"] = hist.date.dt.date
    # Daily label routine uses the signal day's adjusted close as denominator.
    work = {**row, "recommended_at": None}
    _compute_row_returns(work, hist, row.get("market") or "KOSPI")
    keys = [f"return_{h}d_pct" for h in (1, 2, 3, 5, 7, 14, 30)] + [
        "latest_return_pct", "max_high_return_5d_pct",
        "hit_5pct_within_5d", "hit_5pct_within_5d_at", "swing_target_label_version"]
    patch = {k: work.get(k) for k in keys if work.get(k) != row.get(k)}
    if row.get("validation_excluded_reason") == QUARANTINE:
        # A recalculation does not repair missing scanner features or earn
        # publication eligibility. Retain the exclusion that predated quarantine.
        patch.update(validation_excluded=True,
                     validation_excluded_reason=original.get("validation_excluded_reason")
                     if original.get("validation_excluded") else "issued_outcomes_recomputed_not_validated")
    basis = {"kind": "adjusted_signal_close_to_close", "source": price_source,
             "signal_date": str(day.date()), "asof": str(prices.date.max().date()),
             "adjusted_base_close": float(prices.adj_close.iloc[0]),
             "issued_reference_price": row.get("entry_reference_price"),
             "contract_pnl": False,"valuation_only":True,
             "nontrading_sessions":prices.loc[no_trade,"date"].dt.strftime("%Y-%m-%d").tolist()}
    snapshot = row.get("feature_snapshot") or {}
    if not isinstance(snapshot, dict):
        raise ValueError("unexpected feature_snapshot type")
    # DB has no latest_trade_date column. Persist the as-of and denominator in
    # the existing JSON envelope, explicitly named as outcome metadata.
    snapshot = {**snapshot, "daily_outcome_basis": basis}
    if snapshot != row.get("feature_snapshot"):
        patch["feature_snapshot"] = snapshot
    return patch, basis


def audit_and_apply(plan, audit_dir, provenance, client, apply=False, source_guard=None):
    """Verify a complete reversible plan before the first compare-and-set write."""
    audit_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({**provenance,"plan":plan},
                         sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    digest = hashlib.sha256(payload).hexdigest()
    backup = audit_dir/f"{digest}.json"
    backup.write_bytes(payload)
    if backup.read_bytes() != payload:
        raise RuntimeError("backup verification failed")
    def log(state, **data):
        with (audit_dir/"audit.jsonl").open("a") as fh:
            fh.write(json.dumps({"at":datetime.now(timezone.utc).isoformat(),
                                 "state":state,"snapshot":str(backup),"sha256":digest,**data})+"\n")
    log("prepared" if apply else "dry_run", changes=len(plan))
    if apply:
        if source_guard:
            source_guard()
        for item in plan:
            before, patch = item["before"], item["patch"]
            q = client.table("market_scan_results").update({**patch,
                "performance_updated_at":datetime.now(timezone.utc).isoformat()}).eq("id",before["id"])
            for key in set(patch) | {"entry_reference_price", "performance_updated_at", "validation_excluded_reason"}:
                old = before.get(key)
                q = q.is_(key,"null") if old is None else q.eq(
                    key, json.dumps(old,ensure_ascii=False) if isinstance(old,(dict,list)) else old)
            try:
                updated = q.execute().data
            except Exception as exc:
                log("failed", id=before["id"], error_type=type(exc).__name__)
                raise
            if len(updated) != 1 or any(updated[0].get(k) != v for k,v in patch.items()):
                log("conflict", id=before["id"])
                raise RuntimeError("compare-and-set conflict; replan")
            log("committed", id=before["id"], fields=list(patch))
    return {"applied":apply,"changes":len(plan),"backup":str(backup)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repair-backup", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=Path.home()/"research_cache")
    ap.add_argument("--audit-dir", type=Path, default=ROOT/"runtime_state/audit/issued_outcomes")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    original_bytes = args.repair_backup.read_bytes()
    original = {i["before"]["id"]: i["before"] for i in json.loads(original_bytes)["plan"]
                if i["table"] == "market_scan_results" and
                i["patch"].get("validation_excluded_reason") == QUARANTINE}
    if not original:
        raise ValueError("no quarantined rows in repair backup")
    from modules.db_manager import DBManager
    client = DBManager().client
    rows = client.table("market_scan_results").select("*").in_("id",list(original)).execute().data
    if len(rows) != len(original):
        raise RuntimeError("incomplete database snapshot")
    source = args.cache/"px_delisted.parquet"
    source_stat = source.stat().st_mtime_ns
    codes = list({r["ticker"].split(".")[0] for r in rows})
    prices = pd.read_parquet(source, columns=["code", "date", "adj_close", "adj_high", "volume"],
                             filters=[("code", "in", codes),
                                      ("date", ">=", pd.Timestamp(min(r["base_trade_date"] for r in rows)))])
    sessions = pd.read_parquet(args.cache/"px_long.parquet", columns=["date"]).date.drop_duplicates()
    sessions = sessions[sessions <= prices.date.max()]
    plan = []
    for row in rows:
        patch, basis = recompute(row, original[row["id"]],
                                 prices[prices.code == row["ticker"].split(".")[0]], sessions)
        if patch:
            plan.append({"before": row, "patch": patch, "basis": basis})
    def source_guard():
        if source.stat().st_mtime_ns != source_stat:
            raise RuntimeError("price source changed after planning")
    result = audit_and_apply(plan,args.audit_dir,
                            {"original_backup_sha256":hashlib.sha256(original_bytes).hexdigest(),
                             "source_mtime_ns":source_stat},client,args.apply,source_guard)
    print(json.dumps(result,ensure_ascii=False))


if __name__ == "__main__":
    main()
