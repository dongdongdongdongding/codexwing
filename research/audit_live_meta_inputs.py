"""Read-only contract and timing census before reopening meta calibration.

This does not fit a model, change a ledger, infer missing issuance metadata,
or turn recorded returns into independently verified TP5/H10 labels.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.market_sessions import price_sessions

LANES = {
    "kr_swing_candidate": ("kr_swing_candidate_ledger.jsonl", "policy_ret", True),
    "kospi_intraday": ("kospi_intraday_swing_ledger.jsonl", "exit_t5_h5", True),
    "kosdaq_intraday_vwap": ("kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "exit_t10_h5", True),
    "swing_ensemble_retired": ("swing_ensemble_ledger.jsonl", "first_touch_ret", False),
}


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def declared_contract(row):
    horizons, targets = [], []
    for key in ("contract_h", "hold_days"):
        if finite(row.get(key)) and row[key] > 0:
            horizons.append(float(row[key]))
    for key, multiplier in (("contract_tp", 100), ("target_tp_pct", 1)):
        if finite(row.get(key)) and row[key] > 0:
            targets.append(round(row[key] * multiplier, 8))
    text = str(row.get("contract") or row.get("exit_contract") or "")
    h = re.search(r"within\s+(\d+)\s+sessions", text)
    tp = re.search(r"\+(\d+(?:\.\d+)?)%", text)
    if h:
        horizons.append(float(h[1]))
    if tp:
        targets.append(float(tp[1]))
    conflict = len(set(horizons)) > 1 or len(set(targets)) > 1
    return {"horizon": horizons[0] if horizons and not conflict else None,
            "tp_pct": targets[0] if targets and not conflict else None,
            "conflict": conflict}


def aware_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp if stamp.tzinfo is not None else None
    except ValueError:
        return None


def entry_timing(row, lane, sessions):
    """Necessary timestamp check; never a proof of feature availability."""
    logged = aware_timestamp(row.get("logged_at") if lane == "kr_swing_candidate" else row.get("generated_at"))
    if logged is None:
        return "missing_aware_creation_timestamp"
    day = row.get("date")
    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return "unknown_signal_date"
    if lane == "kr_swing_candidate":
        pos = bisect_right(sessions, day)
        if pos == len(sessions):
            return "next_observed_session_unavailable"
        cutoff = datetime.fromisoformat(sessions[pos] + "T09:00:00").replace(tzinfo=ZoneInfo("Asia/Seoul"))
    elif lane == "kosdaq_intraday_vwap":
        value = row.get("ordered_entry_at")
        if not isinstance(value, str):
            return "missing_entry_timestamp"
        try:
            cutoff = datetime.fromisoformat(value)
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=ZoneInfo("Asia/Seoul"))
        except ValueError:
            return "missing_entry_timestamp"
    else:
        return "entry_time_not_reconstructed"
    return "recorded_before_entry" if logged <= cutoff else "recorded_after_entry"


def classify(row, lane, field, sessions, fixed):
    contract = declared_contract(row)
    settled = finite(row.get(field))
    label_contract = {"exit_t5_h5": (5, 5), "exit_t10_h5": (5, 10)}.get(field)
    if contract["conflict"]:
        alignment = "conflicting_contract_metadata"
    elif contract["horizon"] is None or contract["tp_pct"] is None:
        alignment = "unknown_declared_contract"
    elif label_contract:
        alignment = "matches_declared_contract" if (contract["horizon"], contract["tp_pct"]) == label_contract else "shadow_label_differs_from_declared_contract"
    elif field == "policy_ret":
        alignment = "row_specific_policy_requires_price_replay"
    else:
        alignment = "retired_label_requires_price_replay"
    p = row.get("p")
    return {"date": row.get("date"), "ticker": row.get("ticker"), "market": row.get("market"),
            "settled_by_old_harness_field": settled, "declared_contract": contract,
            "old_harness_label_alignment": alignment,
            "declared_tp5_h10": not contract["conflict"] and contract["horizon"] == 10 and contract["tp_pct"] == 5,
            "creation_timing": entry_timing(row, lane, sessions),
            "p_finite_in_unit_interval": finite(p) and 0 <= p <= 1,
            "regime": str(row.get("mkt_state") or "UNKNOWN"),
            "tier": str(row.get("tier") or "UNKNOWN"),
            "in_contract_flag": row.get("in_contract"), "fire_flag": row.get("fire"),
            "fixed_cohort_member": (row.get("date"), row.get("ticker"), row.get("market")) in fixed if lane == "kr_swing_candidate" else False,
            "input_signature_present": bool(row.get("input_sig")),
            "model_label_present": bool(row.get("model_label")),
            "label_max_date": row.get("label_max_date"),
            "settlement_evidence_present": isinstance(row.get("settlement_evidence"), dict) and bool(row["settlement_evidence"])}


def summarize(records):
    settled = [r for r in records if r["settled_by_old_harness_field"]]
    target = [r for r in settled if r["declared_tp5_h10"]]
    timely = [r for r in target if r["creation_timing"] == "recorded_before_entry"]
    return {"rows": len(records), "settled": len(settled),
            "settled_dates": len({r["date"] for r in settled}),
            "settled_regimes": dict(Counter(r["regime"] for r in settled)),
            "settled_label_alignment": dict(Counter(r["old_harness_label_alignment"] for r in settled)),
            "settled_creation_timing": dict(Counter(r["creation_timing"] for r in settled)),
            "settled_declared_tp5_h10": len(target),
            "settled_declared_tp5_h10_dates": len({r["date"] for r in target}),
            "timely_recorded_declared_tp5_h10": len(timely),
            "timely_recorded_declared_tp5_h10_dates": len({r["date"] for r in timely}),
            "timely_recorded_declared_tp5_h10_with_input_signature": sum(r["input_signature_present"] for r in timely),
            "timely_recorded_declared_tp5_h10_with_model_label": sum(r["model_label_present"] for r in timely),
            "fixed_cohort_rows": sum(r["fixed_cohort_member"] for r in records),
            "fixed_cohort_settled_by_original_contract": sum(r["fixed_cohort_member"] for r in settled)}


def run(root, out):
    out.mkdir(parents=True, exist_ok=True)
    snapshots, hashes = {}, {}
    for lane, (name, field, live) in LANES.items():
        path = root / "runtime_state/reports/experimental" / name
        raw = path.read_bytes()
        snapshots[lane] = (path, raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
        backup = out / name
        if backup.exists() and backup.read_bytes() != raw:
            raise ValueError("capture already exists with different ledger bytes")
        if not backup.exists():
            backup.write_bytes(raw)
    spec_path = ROOT / "research/prereg_kr_touch10_price_source_20261007.json"
    spec_raw = spec_path.read_bytes()
    fixed = {(r["date"], r["ticker"], r["market"]) for r in json.loads(spec_raw)["cohort"]}
    sessions, source = price_sessions("KR", datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat())
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "source_hashes": hashes,
              "fixed_cohort_spec_sha256": hashlib.sha256(spec_raw).hexdigest(),
              "calendar_source": source, "calendar_dates": sessions,
              "publication_allowed": False, "model_fit_performed": False, "lanes": {}}
    pooled, live_records = [], []
    for lane, (name, field, live) in LANES.items():
        raw = snapshots[lane][1]
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        records = [classify(row, lane, field, sessions, fixed) for row in rows]
        keys = Counter((r["date"], r["ticker"]) for r in records)
        report["lanes"][lane] = {"old_harness_field": field, "live": live,
            "summary": summarize(records), "duplicate_date_ticker_keys": [list(k) for k,v in keys.items() if v > 1],
            "records": records}
        pooled.extend(records)
        if live:
            live_records.extend(records)
    for path, raw in snapshots.values():
        if path.read_bytes() != raw:
            raise RuntimeError("source ledger changed during audit")
    report["live_summary"] = summarize(live_records)
    report["pooled_with_retired_summary"] = summarize(pooled)
    # The ledger can lag an independently replayed maturity window. Keep that
    # evidence distinct: candidate H10 labels do not alter issued H5 contracts.
    replay_path = root / "runtime_state/reports/validation/kr_kis_rollover_audit_20261007.json"
    if replay_path.exists():
        replay_raw = replay_path.read_bytes()
        replay = json.loads(replay_raw)
        later = replay["later_maturity"]
        known = {}
        for r in later["records"]:
            key = (r["date"], r["ticker"], r["market"], r["variant"])
            if key in known:
                raise ValueError("duplicate independent replay identity")
            known[key] = r
        rows = [json.loads(line) for line in snapshots["kr_swing_candidate"][1].splitlines() if line.strip()]
        newly_mature = []
        for row in rows:
            result = known.get((row["date"], row["ticker"], row["market"], "baseline"))
            if result and result["status"] == "resolved" and not finite(row.get("policy_ret")):
                newly_mature.append({"date":row["date"], "ticker":row["ticker"],
                    "market":row["market"], "declared_contract":declared_contract(row),
                    "independent_policy_ret":result["policy_ret"], "independent_touch":result["touch"]})
        report["prior_independent_replay"] = {"path":str(replay_path),
            "sha256":hashlib.sha256(replay_raw).hexdigest(), "asof":later["asof"],
            "metrics":later["metrics"], "newly_mature_original_contracts_not_yet_in_ledger":newly_mature,
            "limitation":"Prior fixed-cohort price evidence; not new PIT features or an independent selection holdout."}
        if replay_path.read_bytes() != replay_raw:
            raise RuntimeError("independent replay changed during audit")
    report["limitations"] = [
        "Creation timestamps and current-calendar comparisons are necessary checks, not immutable PIT feature proof.",
        "No independent price replay was performed here; previous fixed-cohort audits remain separate evidence.",
        "Old harness predicts cost-adjusted positive returns, not TP5/H10 touch; its shuffled date-group CV is not forward testing.",
        "Declared-contract and timely-record counts are upper bounds before feature provenance, settlement and epoch validation.",
        "No retraining, score promotion, cadence change or 70% probability certification."]
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.root, args.out)
    print(json.dumps(report["live_summary"], ensure_ascii=False, indent=2))
