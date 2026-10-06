"""Repair persisted current-cohort contracts from the issued ledger; dry-run default.

Only existing rows are updated. Original rows, planned field changes and checksums
are backed up and read back before writing. Compare-and-set prevents racing a run.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from modules.model_lane_contract import model_lane_contract


def changes(table, row, issued):
    pick = issued.get((row["run_id"], row["ticker"]))
    if not pick:
        if table == "market_scan_results":
            patch = {"validation_excluded": True,
                     "validation_excluded_reason": "not_in_frozen_issued_ledger"}
        else:
            ci = {**(row.get("candidate_interpretation") or {}), "stream_excluded": True,
                  "stream_excluded_reason": "not_in_frozen_issued_ledger"}
            patch = {"candidate_interpretation": ci}
    else:
        contract = model_lane_contract(pick, "swing_candidate")
        entry = float(pick["close"])
        p = float(pick["p"])
        if p > 1.5:
            p /= 100
        if table == "market_scan_results":
            patch = {"entry_reference_price": entry, "scan_entry_reference_price": entry,
                     "hold_days": contract["hold_days"], "horizon": f"T+{contract['hold_days']}D",
                     "base_trade_date": contract["signal_date"], "target_tp_pct": contract["target_tp_pct"],
                     "ml_prob": round(p*100, 2), "decision_score": p}
            # Existing outcomes calculated against a different reference cannot
            # be silently blessed by correcting only the reference price.
            outcomes = [v for k,v in row.items() if (k.startswith("return_") or k == "latest_return_pct")
                        and v is not None]
            if row.get("entry_reference_price") != entry and outcomes:
                patch.update(validation_excluded=True,
                             validation_excluded_reason="issued_reference_repaired_outcomes_need_recalculation")
        else:
            target = round(entry*(1+contract["contract_tp"]), 2)
            plan = {**(row.get("trade_plan") or {}), **contract,
                    "entry_reference_price": entry, "target_price": target}
            ci = {**(row.get("candidate_interpretation") or {}), **contract,
                  "entry_reference_price": entry, "target_price": target,
                  "entry_label": "익일 시가", "model_hit_prob_pct": round(p*100, 1),
                  "buy_score": p, "operational_total_score": round(p*100, 1),
                  "realized_expectancy_3d_prob": None, "realized_expectancy_5d_prob": None}
            thesis = f"{contract['model_prob_label']} {p*100:.1f}. 기준가 {entry:g}, {contract['hold_note']}."
            ci.update(selection_thesis=thesis, touch_vs_buy_ready_explanation=thesis)
            patch = {"trade_plan": plan, "candidate_interpretation": ci,
                     "realized_expectancy_admission": {}, "buy_score": p,
                     "prediction": {**(row.get("prediction") or {}), "phase25_prob": round(p*100, 1),
                                    "expected_edge_score": float(pick.get("score") or p)},
                     "selection_thesis": thesis, "price": {**(row.get("price") or {}), "last": entry}}
    return {k:v for k,v in patch.items() if row.get(k) != v}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--since", default="2026-08-24")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    from modules.db_manager import DBManager
    client = DBManager().client
    if client is None:
        raise RuntimeError("database unavailable")
    ledger = args.root / "runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl"
    raw = ledger.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    issued = {("SWING-CAND-"+r["date"].replace("-", ""),r["ticker"]):r
              for r in rows if r["date"] >= args.since}
    run_ids = sorted({run for run,_ in issued})
    plan = []
    for table, key in [("market_scan_results", "id"), ("scan_deep_reports", "report_id")]:
        stored = client.table(table).select("*").in_("run_id",run_ids).limit(1000).execute().data
        if len(stored) >= 1000:
            raise RuntimeError("repair scope exceeds bounded read")
        for row in stored:
            patch = changes(table,row,issued)
            if patch:
                plan.append({"table":table,"key":key,"before":row,"patch":patch})
    audit = args.root / "runtime_state/audit/issued_contract_repair"
    audit.mkdir(parents=True,exist_ok=True)
    snapshot = json.dumps({"ledger_sha256":hashlib.sha256(raw).hexdigest(),"plan":plan},
                          ensure_ascii=False,sort_keys=True,allow_nan=False).encode()
    sha = hashlib.sha256(snapshot).hexdigest()
    backup = audit / f"{sha}.json"
    backup.write_bytes(snapshot)
    if backup.read_bytes() != snapshot:
        raise RuntimeError("backup verification failed")
    log_path = audit / "audit.jsonl"
    def log(data):
        with log_path.open("a") as log_file:
            log_file.write(json.dumps({"at":datetime.now(timezone.utc).isoformat(),
                                       "snapshot":str(backup),"sha256":sha,**data})+"\n")
    log({"state":"prepared" if args.apply else "dry_run", "changes":len(plan)})
    if args.apply:
        if ledger.read_bytes() != raw:
            raise RuntimeError("ledger changed after planning")
        for item in plan:
            table,key,before,patch = (item[k] for k in ["table","key","before","patch"])
            q = client.table(table).update(patch).eq(key,before[key])
            for field in patch:
                old = before.get(field)
                if old is None:
                    q = q.is_(field,"null")
                else:
                    q = q.eq(field,json.dumps(old,ensure_ascii=False) if isinstance(old,(dict,list)) else old)
            updated = q.execute().data
            if len(updated) != 1 or any(updated[0].get(k) != v for k,v in patch.items()):
                log({"state":"conflict", "table":table,"id":before[key]})
                raise RuntimeError(f"compare-and-set conflict in {table}; replan")
            log({"state":"committed", "table":table,"id":before[key],"fields":list(patch)})
    print(json.dumps({"applied":args.apply,"changes":len(plan),"backup":str(backup),
                      "tables":{t:sum(i['table']==t for i in plan)
                                for t in ['market_scan_results','scan_deep_reports']}},ensure_ascii=False))


if __name__ == "__main__":
    main()
