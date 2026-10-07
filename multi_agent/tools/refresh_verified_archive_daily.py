"""Refresh already verified generic KR valuations from captured KIS J prices.

The original normalization evidence fixes the cohort and recommendation identity.
No admission, contract settlement, or new recommendation is performed here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.normalize_verified_archive_daily import (
    management_cas, original_matches, scanner_matches,
)
from multi_agent.tools.repair_issued_outcomes import recompute, audit_and_apply
from multi_agent.tools.us_daily_panel_cache import file_sha
from multi_agent.tools.backfill_scanner_full_returns import _row_scan_date
from multi_agent.tools.backfill_kr_intraday import request_deadline
from research.audit_kr_touch10_price_source import parse_bars

SOURCE = "KIS:inquire_daily_itemchartprice:J:adjusted=0"
IDENTITY = ("run_id", "ticker", "recommended_at", "base_trade_date", "entry_reference_price",
            "market_type", "market", "scan_mode")


def completed_sessions(dates, now):
    """Observed market sessions only; never count an in-progress Korean day."""
    local = now.astimezone(ZoneInfo("Asia/Seoul"))
    last = local.date() if local.hour >= 16 else local.date() - timedelta(days=1)
    days = pd.DatetimeIndex(pd.to_datetime(dates)).drop_duplicates().sort_values()
    if days.isna().any() or days.tz is not None:
        raise ValueError("invalid_observed_calendar")
    return days[days <= pd.Timestamp(last)]


def request_windows(start, end):
    """At most 90 calendar days per request, below the provider's 100-bar cap."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    while start <= end:
        stop = min(start + pd.Timedelta(days=89), end)
        yield {"start_date": start.strftime("%Y%m%d"), "end_date": stop.strftime("%Y%m%d"),
               "adjusted": True, "market_div": "J"}
        start = stop + pd.Timedelta(days=1)


def finalized_groups(groups, sessions):
    """KIS can revise its newest date at rollover even after the market closes.

    Require a later provider bar to witness rollover. Its prices never enter
    valuation labels, whether that later day is live or already closed.
    """
    rollover = min(prices.date.max() for prices in groups.values())
    final = sessions[sessions < rollover]
    if final.empty:
        raise ValueError("waiting_provider_date_rollover")
    return ({code: prices[prices.date <= final[-1]].copy() for code, prices in groups.items()}, final)


def verify_capture_receipt(capture, codes, read):
    receipt = read(capture / "receipt.json")
    expected_files = {"request.json"} | {f"kis_{code}.json" for code in codes}
    if set(receipt) != expected_files or any(file_sha(capture / name) != sha for name, sha in receipt.items()):
        raise ValueError("capture_receipt_mismatch")


def validate_identity(row, captured, root, read):
    if any(row.get(k) != captured.get(k) for k in IDENTITY):
        raise ValueError("captured_identity_changed")
    if row.get("market_type") != "KR" or not str(row.get("run_id", "")).startswith("RUN-"):
        raise ValueError("outside_verified_generic_KR_scope")
    basis = (row.get("feature_snapshot") or {}).get("daily_outcome_basis") or {}
    if (basis.get("source") != SOURCE or basis.get("kind") != "adjusted_signal_close_to_close"
            or basis.get("signal_date") != row.get("base_trade_date")
            or basis.get("issued_reference_price") != row.get("entry_reference_price")
            or basis.get("contract_pnl") is not False or not basis.get("evidence_sha256")):
        raise ValueError("prior_verified_price_basis_missing")
    run = root / "runtime_state/shared_working" / row["run_id"]
    outcomes = read(run / "realized_outcomes.json").get("outcomes", [])
    if original_matches(row, outcomes):
        return "realized_outcomes.json"
    if any(x.get("ticker") == row["ticker"] for x in outcomes):
        raise ValueError("contradictory_original_outcome")
    if not scanner_matches(row, read(run / "scanner_handoff.json")):
        raise ValueError("original_scanner_identity_unverified")
    return "scanner_handoff.json"


def plan_refresh(rows, groups, sessions, evidence_sha):
    plan = []
    for row in rows:
        code = row["ticker"].split(".")[0]
        prior = row["feature_snapshot"]["daily_outcome_basis"]
        if pd.Timestamp(prior["asof"]) > max(sessions):
            raise ValueError("cannot_regress_price_asof")
        signal_day = _row_scan_date(row)
        eligible = sessions[sessions >= pd.Timestamp(signal_day)] if signal_day else []
        if not len(eligible) or str(eligible[0].date()) != row["base_trade_date"]:
            raise ValueError("signal_day_calendar_mismatch")
        prices = groups[code]
        patch, basis = recompute(row, row, prices, sessions, price_source=SOURCE)
        # Stable numerical provenance prevents fetched_at/request IDs from
        # generating a DB write on every replay of the same price observations.
        used = prices[prices.date >= pd.Timestamp(row["base_trade_date"])].sort_values("date")
        digest = hashlib.sha256(used.to_json(orient="records", date_format="iso",
                                           double_precision=15).encode()).hexdigest()
        basis["prices_sha256"] = digest
        basis["evidence_sha256"] = (prior["evidence_sha256"]
            if prior.get("prices_sha256") == digest else evidence_sha[code])
        patch.pop("validation_excluded", None)
        patch.pop("validation_excluded_reason", None)
        if patch.get("feature_snapshot") == row.get("feature_snapshot"):
            patch.pop("feature_snapshot", None)
        if patch:
            plan.append({"before": row, "patch": patch, "basis": basis})
    return plan


def refresh(args):
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    def guard():
        if any(file_sha(path) != sha for path, sha in hashes.items()):
            raise RuntimeError("source_changed_after_planning")

    manifest = read(args.evidence / "price_request.json")
    captured = read(args.evidence / "current_rows_before.json")
    if hashes[str(args.evidence / "current_rows_before.json")] != manifest["cohort_sha256"]:
        raise ValueError("cohort_digest_mismatch")
    ids = manifest["ids"]
    if len(set(ids)) != len(ids) or sorted(r["id"] for r in captured) != sorted(ids) or not ids:
        raise ValueError("ambiguous_or_incomplete_cohort")
    request = manifest["request"]
    if request.get("adjusted") is not True or request.get("market_div") != "J":
        raise ValueError("original_price_basis_mismatch")
    from modules.db_manager import DBManager
    client = DBManager().client
    if client is None:
        raise RuntimeError("database_unavailable")
    rows = []
    for pos in range(0, len(ids), 50):
        rows.extend(client.table("market_scan_results").select("*").in_("id", ids[pos:pos+50]).execute().data)
    if sorted(r["id"] for r in rows) != sorted(ids):
        raise ValueError("incomplete_current_DB_cohort")
    original = {r["id"]: r for r in captured}
    identity = {r["id"]: validate_identity(r, original[r["id"]], args.root, read) for r in rows}
    calendar_sha = file_sha(args.calendar)
    dates = pd.read_parquet(args.calendar, columns=["date"]).date.drop_duplicates()
    if file_sha(args.calendar) != calendar_sha:
        raise RuntimeError("calendar_changed_during_read")
    hashes[str(args.calendar)] = calendar_sha
    sessions = completed_sessions(dates, datetime.now(timezone.utc))
    start = min(r["base_trade_date"] for r in rows)
    sessions = sessions[sessions >= pd.Timestamp(start)]
    if sessions.empty:
        raise ValueError("no_completed_observed_sessions")
    audit = args.root / "runtime_state/audit/verified_archive_daily_refresh"
    audit.mkdir(parents=True, exist_ok=True)
    if args.capture:
        capture = args.capture
        spec = read(capture / "request.json")
        expected = {"cohort_sha256": manifest["cohort_sha256"], "ids": ids,
                    "sessions": sessions.strftime("%Y-%m-%d").tolist()}
        if any(spec.get(k) != v for k, v in expected.items()):
            raise ValueError("capture_scope_or_completed_calendar_changed")
        if pd.Timestamp(spec["request_end"]).date() > datetime.now(ZoneInfo("Asia/Seoul")).date():
            raise ValueError("capture_from_future")
    else:
        capture = audit / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        capture.mkdir()
        spec = {"cohort_sha256": manifest["cohort_sha256"], "ids": ids,
                "sessions": sessions.strftime("%Y-%m-%d").tolist(),
                "calendar_sha256": calendar_sha, "source": SOURCE,
                "request_end": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()}
        (capture / "request.json").write_text(json.dumps(spec, indent=2))
        read(capture / "request.json")
        from modules.kis_openapi import KISOpenAPIClient
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
        os.environ["KIS_LIVE_RETRY_COUNT"] = "0"
        kis = KISOpenAPIClient(timeout=10)
        for code in sorted({r["ticker"].split(".")[0] for r in rows}):
            pages = []
            for req in request_windows(start, spec["request_end"]):
                try:
                    with request_deadline(20):
                        payload = kis.daily_bars(code, **req)
                except Exception as exc:
                    pages.append({"request": req, "error_type": type(exc).__name__})
                    (capture / f"kis_{code}.json").write_text(json.dumps({"code": code, "pages": pages}))
                    raise
                pages.append({"request": req, "payload": payload})
                (capture / f"kis_{code}.json").write_text(json.dumps({"code": code, "pages": pages}))
                time.sleep(.3)
            print(json.dumps({"captured": code, "pages": len(pages)}), flush=True)
        receipt = {p.name: file_sha(p) for p in capture.glob("*.json")}
        (capture / "receipt.json").write_text(json.dumps(receipt, indent=2))
    verify_capture_receipt(capture, {r["ticker"].split(".")[0] for r in rows}, read)
    groups, evidence_sha = {}, {}
    windows = list(request_windows(start, spec["request_end"]))
    for code in sorted({r["ticker"].split(".")[0] for r in rows}):
        path = capture / f"kis_{code}.json"
        evidence = read(path)
        if evidence.get("code") != code or [p["request"] for p in evidence["pages"]] != windows:
            raise ValueError("captured_price_request_mismatch")
        groups[code] = pd.concat([parse_bars(p["payload"], p["request"]["start_date"],
            p["request"]["end_date"]) for p in evidence["pages"]], ignore_index=True).sort_values("date")
        evidence_sha[code] = hashes[str(path)]
    observed_asof = sessions[-1]
    observed_count = len(sessions)
    groups, sessions = finalized_groups(groups, sessions)
    plan = plan_refresh(rows, groups, sessions, evidence_sha)
    guard()
    result = audit_and_apply(plan, capture / "normalization", {"source_sha256": hashes,
        "identity_evidence": identity, "cohort_ids": ids, "contract_pnl": False},
        client, args.apply, guard, cas_update=management_cas)
    result.update(status="PASS", capture=str(capture), rows_read=len(rows),
                  price_asof=str(sessions[-1].date()), calendar_kind="observed_completed_sessions",
                  observed_calendar_asof=str(observed_asof.date()), provider_rollover_required=True,
                  provider_lag_observed_sessions=observed_count-len(sessions),
                  freshness_status=("CURRENT_COMPLETED_SESSIONS" if sessions[-1] == observed_asof
                                    else "WAITING_PROVIDER_ROLLOVER"),
                  immutable_references=True, contract_pnl=False)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--evidence", type=Path)
    ap.add_argument("--calendar", type=Path, default=Path.home()/"research_cache/px_long.parquet")
    ap.add_argument("--capture", type=Path, help="Replay an immutable capture for the same completed sessions")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    args.evidence = args.evidence or args.root / "runtime_state/audit/archive_conflict_normalization"
    from dotenv import load_dotenv
    load_dotenv(args.root / ".env.local")
    audit = args.root / "runtime_state/audit/verified_archive_daily_refresh"
    audit.mkdir(parents=True, exist_ok=True)
    report = args.root / "runtime_state/reports/validation/verified_archive_daily_refresh_latest.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    with (audit / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = refresh(args)
        except Exception as exc:
            # Provider exceptions may carry secrets; retain the type and raw
            # non-credentialed capture instead of printing their text.
            result = {"status": "FAILED", "error_type": type(exc).__name__}
            if isinstance(exc, ValueError) and str(exc).replace("_", "").isalnum():
                result["reason"] = str(exc)
        finally:
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            tmp = report.with_suffix(".tmp")
            tmp.write_text(json.dumps(result, indent=2))
            tmp.replace(report)
    print(json.dumps(result))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
