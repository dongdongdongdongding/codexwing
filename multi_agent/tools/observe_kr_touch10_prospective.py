"""Capture immutable pre-entry H10 shadow cohorts and evaluate the fixed window.

No routing, model fitting, parameter search, sizing or messages. Historical
misses remain coverage failures; a late report cannot create a prospective pick.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, time, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from modules.kr_contract_settlement import settle
from modules.market_sessions import price_sessions
from research.validate_kr_touch10 import block_ci, metrics

KST = ZoneInfo("Asia/Seoul")


def capture(report, ledger, panel, spec, now):
    day = str(report.get("as_of") or "")
    if day < spec["signal_start"]:
        return None
    signal = datetime.fromisoformat(day).date()
    deadline = datetime.combine(signal+timedelta(days=1),time(9),KST)
    close = datetime.combine(signal,time(15,30),KST)
    generated = datetime.fromisoformat(report["generated_at"])
    registered = datetime.fromisoformat(spec["registered_at"])
    if generated.tzinfo is None or not (registered <= generated <= now < deadline and generated >= close):
        raise ValueError("outside_preregistered_pre_entry_capture_window")
    picks = [r for r in ledger if r.get("date") == day]
    if len({r["ticker"] for r in picks}) != len(picks):
        raise ValueError("duplicate_issued_pick")
    if {(r["market"],r["ticker"]) for r in picks} != {
            (r["market"],r["ticker"]) for r in report.get("picks",[])}:
        raise ValueError("report_ledger_selection_mismatch")
    frozen, universes = [], {}
    for market, rule in spec["selection"].items():
        gate = (report.get("gate") or {}).get(market) or {}
        if any(gate.get(k) != rule[k] for k in ["gate_kind","gate_q"]):
            raise ValueError("selection_gate_changed_or_missing")
        selected = [r for r in picks if r.get("market") == market]
        if (gate.get("fire") is not True and selected) or (gate.get("fire") is True and not selected):
            raise ValueError("gate_pick_mismatch")
        if len(selected) > rule["top_k"]:
            raise ValueError("issued_quota_exceeded")
        eligible = panel[(panel.date == pd.Timestamp(day)) & (panel.market == market)
                         & (panel.liq >= spec["universe_liq_krw"][market]) & (panel.volume > 0)]
        universes[market] = sorted(set(eligible.code.astype(str).str.zfill(6)))
        if not universes[market]:
            raise ValueError("missing_same_day_universe")
        for row in selected:
            stamp = datetime.fromisoformat(row["logged_at"])
            if stamp.tzinfo is None or not (registered <= stamp <= now < deadline):
                raise ValueError("issued_timestamp_outside_prospective_scope")
            if row.get("top_k") != rule["top_k"] or row.get("in_contract") is not True:
                raise ValueError("issued_contract_changed")
            if row.get("policy_ret") is not None:
                raise ValueError("outcome_already_observed_at_capture")
            if row["ticker"].split(".")[0] not in universes[market]:
                raise ValueError("selected_ticker_missing_from_frozen_universe")
            frozen.append({k:row.get(k) for k in ["date","market","ticker","p","close","rank",
                           "top_k","input_sig","label_max_date","logged_at","gate_kind","gate_q"]})
    return {"date":day,"captured_at":now.isoformat(),"producer_generated_at":report["generated_at"],
            "gate":report["gate"],"picks":frozen,"universe":universes,
            "contract":{"horizon_sessions":spec["horizon_sessions"],"tp":spec["tp"],"entry":"next_open"}}


def evaluate(snapshots, prices, sessions, spec):
    calendar = [d for d in sessions if d >= spec["signal_start"]][:spec["evaluation_sessions"]]
    asof = str(prices.date.max().date()) if len(prices) else None
    price_sessions_available = [d for d in sessions if asof and d <= asof]
    byday = {r["date"]:r for r in snapshots if r["date"] in calendar}
    if len(byday) != len([r for r in snapshots if r["date"] in calendar]):
        raise ValueError("duplicate_snapshot_date")
    groups = {str(c).zfill(6):g for c,g in prices.groupby("code")}
    records, paired, pools, control_counts = [], [], {}, Counter()
    def outcome(code,day):
        if code not in groups:
            return {"status":"data_error","reason":"missing_ticker"}
        return settle(groups[code],price_sessions_available,day,spec["horizon_sessions"],spec["tp"])
    for day,snap in sorted(byday.items()):
        for pick in snap["picks"]:
            result = outcome(pick["ticker"].split(".")[0],day)
            row = {**pick,**result}
            if result["status"] == "resolved":
                row["net"] = row["policy_ret"]-spec["cost_pct"]
            records.append(row)
        for market in spec["selection"]:
            selected = {p["ticker"].split(".")[0] for p in snap["picks"] if p["market"] == market}
            values = []
            for code in snap["universe"][market]:
                if code in selected:
                    continue
                result = outcome(code,day)
                control_counts[result["status"]] += 1
                if result["status"] == "resolved":
                    values.append(result["policy_ret"]-spec["cost_pct"])
            if values:
                pools[(market,day)] = np.array(values)
    summaries, controls = {}, {}
    rng = np.random.default_rng(spec["statistics"]["seed"])
    for market in [*spec["selection"],"combined"]:
        rows = [r for r in records if market == "combined" or r["market"] == market]
        summaries[market] = metrics(rows,calendar)
        done = [r for r in rows if r["status"] == "resolved"]
        paired = [{"date":r["date"],"excess":r["net"]-float(pools[(r["market"],r["date"])].mean())}
                  for r in done if (r["market"],r["date"]) in pools]
        placebo = np.zeros(spec["statistics"]["bootstrap_draws"])
        counts = Counter((r["market"],r["date"]) for r in done)
        control_complete = all(key in pools and len(pools[key]) >= n for key,n in counts.items())
        if control_complete and done:
            for key,n in counts.items():
                placebo += np.array([rng.choice(pools[key],n,replace=False).sum() for _ in placebo])
        controls[market] = {"paired_n":len(paired),"excess_block_ci95":block_ci(paired,calendar,"excess"),
                            "same_day_excess_pp":float(np.mean([r["excess"] for r in paired])) if paired else None,
                            "random_ticker_p_ge":float((1+(placebo >= sum(r["net"] for r in done)).sum())/(1+len(placebo)))
                            if control_complete and done else None}
        if market != "combined":
            days = [d for d in calendar if (market,d) in pools]
            indicator = np.array([any(r["date"] == d for r in rows) for d in days])
            benchmark = np.array([pools[(market,d)].mean() for d in days])
            timing = None
            if indicator.any() and len(days) > 1:
                actual = float(benchmark[indicator].mean())
                shifted = [float(benchmark[np.roll(indicator,k)].mean()) for k in range(1,len(days))]
                timing = {"actual_control_return_on_firing_days":actual,
                          "circular_shift_p_ge":(1+sum(v >= actual for v in shifted))/(1+len(shifted)),
                          "rotations":len(shifted),"scope":"gate timing diagnostic, not stock-selection alpha"}
            controls[market]["timing_diagnostic"] = timing
    firing = sorted({r["date"] for r in records})
    frequency = len(firing)*5/len(calendar) if calendar else None
    final_day = calendar[-1] if len(calendar) == spec["evaluation_sessions"] else None
    mature = bool(final_day and len([d for d in price_sessions_available if d > final_day]) >= spec["horizon_sessions"])
    missing = sorted(set(calendar)-set(byday))
    failures = []
    targets = spec["targets"]
    if mature:
        if missing: failures.append("missing_capture_days")
        if frequency is None or not targets["firing_dates_per_five_sessions"][0] <= frequency <= targets["firing_dates_per_five_sessions"][1]:
            failures.append("frequency_outside_target")
        for market,summary in summaries.items():
            for field,minimum in [("n",targets["min_resolved"]),("unique_dates",targets["min_unique_resolved_dates"]),
                                  ("touch_rate",targets["touch_rate_min"])]:
                if summary.get(field) is None or summary[field] < minimum:
                    failures.append(f"{market}:{field}_below_target")
            for key,ci in [("net",summary["net_ev_block_ci95"]),("excess",controls[market]["excess_block_ci95"])]:
                if ci is None or ci[0] <= 0: failures.append(f"{market}:{key}_ci_not_positive")
            p = controls[market]["random_ticker_p_ge"]
            if p is None or p > targets["random_ticker_placebo_p_max"]: failures.append(f"{market}:ticker_placebo_failed")
            if any(summary["status_counts"].get(k,0) for k in ["data_error","pending"]):
                failures.append(f"{market}:unresolved_or_invalid_outcomes")
        if control_counts["data_error"] or control_counts["pending"]:
            failures.append("unresolved_or_invalid_controls")
    return {"decision":("REJECT" if failures else "VALIDATION_PASSED_PENDING_GATE_REVIEW") if mature else "PENDING_FIXED_WINDOW",
            "publication_allowed":False,"calendar_sessions":len(calendar),"target_sessions":spec["evaluation_sessions"],
            "price_asof":asof,"missing_capture_dates":missing,"firing_dates_per_five_sessions":frequency,
            "results":summaries,"controls":controls,"control_status_counts":dict(control_counts),
            "failures":failures,"records":records}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--cache",type=Path,default=Path.home()/"research_cache")
    args = ap.parse_args()
    raw_spec = (args.root/"research/prereg_kr_touch10_prospective_20261007.json").read_bytes()
    spec = json.loads(raw_spec)
    spec_sha = hashlib.sha256(raw_spec).hexdigest()
    directory = args.root/"runtime_state/reports/experimental/kr_touch10_prospective"
    directory.mkdir(parents=True,exist_ok=True)
    now = datetime.now(timezone.utc)
    today = now.astimezone(KST)
    before = today.date()+timedelta(days=int(today.time() >= time(15,30)))
    sessions,_ = price_sessions("KR",before.isoformat())
    # price_sessions uses the standard cache; reject alternate calendars rather
    # than silently mixing a supplied test cache with a different source.
    if args.cache.resolve() != (Path.home()/"research_cache").resolve():
        dates = pd.read_parquet(args.cache/"px_long.parquet",columns=["date"]).date.drop_duplicates()
        sessions = sorted(str(d.date()) for d in pd.to_datetime(dates) if str(d.date()) < before.isoformat())
    with (directory/".lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        latest = json.loads((args.root/"runtime_state/reports/experimental/kr_swing_candidate_latest.json").read_text())
        day = str(latest.get("as_of") or "")
        window = [d for d in sessions if d >= spec["signal_start"]][:spec["evaluation_sessions"]]
        capture_error = None
        path = directory/f"{day}.json"
        if day in window and not path.exists():
            try:
                source = args.root/"multi_agent/tools/report_kr_swing_candidate.py"
                if hashlib.sha256(source.read_bytes()).hexdigest() != spec["producer_sha256"]:
                    raise ValueError("producer_changed_since_preregistration")
                panel_path = args.cache/"px_long.parquet"
                stamp = panel_path.stat().st_mtime_ns
                panel = pd.read_parquet(panel_path,columns=["date","code","market","liq","volume"],
                                         filters=[("date","==",pd.Timestamp(day))])
                ledger = [json.loads(l) for l in (args.root/"runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl").read_text().splitlines() if l]
                snap = capture(latest,ledger,panel,spec,now)
                if panel_path.stat().st_mtime_ns != stamp:
                    raise ValueError("price_panel_changed_during_capture")
                payload = json.dumps({**snap,"prereg_sha256":spec_sha},sort_keys=True,ensure_ascii=False,allow_nan=False)
                temporary = path.with_suffix(".tmp")
                with temporary.open("w") as fh:
                    fh.write(payload)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.link(temporary,path)  # atomic creation; never overwrite a frozen capture
                temporary.unlink()
                if path.read_text() != payload:
                    raise RuntimeError("snapshot_write_verification_failed")
            except (ValueError,KeyError) as exc:
                capture_error = str(exc)
        snapshots = [json.loads(p.read_text()) for p in sorted(directory.glob("20??-??-??.json"))]
        if any(s.get("prereg_sha256") != spec_sha for s in snapshots):
            raise RuntimeError("preregistration changed after capture")
        if window:
            prices = pd.read_parquet(args.cache/"px_delisted.parquet",filters=[("date",">=",pd.Timestamp(spec["signal_start"]))],
                                     columns=["code","date","adj_open","adj_high","adj_close","volume"])
        else:
            prices = pd.DataFrame(columns=["code","date"])
        result = evaluate(snapshots,prices,sessions,spec)
        result.update(generated_at=now.isoformat(),prereg_sha256=spec_sha,capture_error=capture_error)
        out = args.root/"runtime_state/reports/validation/kr_touch10_prospective_latest.json"
        out.parent.mkdir(parents=True,exist_ok=True)
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        tmp.replace(out)
        print(json.dumps({k:result[k] for k in ["decision","publication_allowed","calendar_sessions","target_sessions","capture_error"]}))
        if capture_error:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
