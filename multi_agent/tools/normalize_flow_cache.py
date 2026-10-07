"""Verify captured KIS flow conflicts across endpoints before bounded replacement.

All controls are from KIS; this is source normalization, not independent-vendor
verification or point-in-time research data. No network calls occur during apply.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.update_flow_cache import (
    FIELDS, legacy_writers, request_deadline, sha, validate_old, write_json,
)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("invalid_number")
    if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)", str(value)):
        raise ValueError("invalid_number")
    result = int(str(value).replace(",", ""))
    if not -(2**63) <= result < 2**63:
        raise ValueError("number_overflow")
    return result


def keyed(payload, output):
    if not isinstance(payload, dict) or str(payload.get("rt_cd")) != "0":
        raise ValueError("provider_failure")
    if not isinstance(payload.get(output), list):
        raise ValueError("missing_output")
    rows = {}
    for row in payload[output]:
        day = row.get("stck_bsop_date")
        if not isinstance(day, str) or not re.fullmatch(r"\d{8}", day):
            raise ValueError("invalid_date")
        pd.to_datetime(day, format="%Y%m%d", errors="raise")
        if day in rows:
            raise ValueError("duplicate_date")
        rows[day] = row
    return rows


def verify_row(raw, repeated, current, price):
    """Every cached field needs corroboration; no tolerances or date shifting."""
    if any(x is None for x in (repeated, current, price)):
        raise ValueError("control_date_missing")
    day = raw["stck_bsop_date"]
    if any(x.get("stck_bsop_date") != day for x in (repeated, current, price)):
        raise ValueError("date_mismatch")
    values = {f: number(raw[s]) for f, s in FIELDS.items()}
    if any(number(repeated[s]) != values[f] for f, s in FIELDS.items()):
        raise ValueError("repeat_flow_changed")
    if any(number(current[s]) != values[f] for f, s in FIELDS.items() if f != "acml_val"):
        raise ValueError("current_flow_disagrees")
    for field in ("acml_tr_pbmn", "acml_vol", "stck_clpr"):
        if number(price[field]) != number(raw[field]):
            raise ValueError("price_control_disagrees_" + field)
    if values["acml_val"] < 0 or number(raw["acml_vol"]) < 0:
        raise ValueError("negative_activity")
    if sum(number(raw[side + "_ntby_qty"]) for side in ("frgn", "orgn", "prsn", "etc")):
        raise ValueError("net_quantity_not_balanced")
    for side in ("frgn", "orgn", "prsn"):
        if number(raw[side + "_shnu_vol"]) - number(raw[side + "_seln_vol"]) != number(raw[side + "_ntby_qty"]):
            raise ValueError("buy_sell_quantity_disagrees")
    return values


def initialize(receipt, audit):
    baseline = json.loads(receipt.read_text())
    plan = {"receipt_path": str(receipt.resolve()), "receipt_sha256": sha(receipt),
            "cache_before_sha256": baseline["cache_after_sha256"],
            "source_dir": baseline["audit_dir"], "excluded_on_or_after": baseline["excluded_on_or_after"],
            "codes": [x["code"] for x in baseline["symbols"]],
            "policy": "stable_repeat_plus_current_flow_plus_unadjusted_J_price_exact_v1"}
    audit.mkdir(parents=True, exist_ok=True)
    dest = audit / "capture_plan.json"
    if dest.exists() and json.loads(dest.read_text()) != plan:
        raise ValueError("capture_plan_changed")
    if not dest.exists():
        write_json(dest, plan)
    return plan, baseline


def capture(receipt, audit, client):
    plan, baseline = initialize(receipt, audit)
    source = Path(plan["source_dir"])
    manifest_path = audit / "captures.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    failures = []
    for index, symbol in enumerate(baseline["symbols"], 1):
        code = symbol["code"]
        origin = source / (code + ".json")
        if sha(origin) != symbol["capture_sha256"]:
            raise ValueError("initial_capture_changed")
        original = keyed(json.loads(origin.read_text()), "output2")
        start = min(original)
        end = symbol["request_trade_date"]
        # Current price date is a rollover witness only; never inserted into flow.
        price_end = plan["excluded_on_or_after"].replace("-", "")
        for endpoint in ("repeat", "current", "price"):
            name = code + "_" + endpoint + ".json"
            dest = audit / name
            if name in manifest:
                if sha(dest) != manifest[name]["sha256"]:
                    raise ValueError("saved_capture_changed")
                continue
            try:
                with request_deadline(30):
                    if endpoint == "repeat":
                        response = client.investor_trading_daily(code, trade_date=end)
                    elif endpoint == "current":
                        response = client.investor_trading_current(code)
                    else:
                        response = client.daily_bars(code, start_date=start, end_date=price_end, adjusted=False)
                keyed(response, "output" if endpoint == "current" else "output2")
                write_json(dest, response)
                manifest[name] = {"sha256": sha(dest), "captured_at": datetime.now(timezone.utc).isoformat(),
                                  "code": code, "endpoint": endpoint, "market_div": "J"}
                write_json(manifest_path, manifest)
            except Exception as exc:
                failures.append({"code": code, "endpoint": endpoint, "error_type": type(exc).__name__})
        if index % 100 == 0:
            print(f"controls {index}/{len(plan['codes'])}, failures={len(failures)}", flush=True)
    summary = {"captured": len(manifest), "expected": 3 * len(plan["codes"]), "failures": failures,
               "finished_at": datetime.now(timezone.utc).isoformat()}
    write_json(audit / "capture_result.json", summary)
    return summary


def build_plan(receipt, audit, cache):
    plan, baseline = initialize(receipt, audit)
    target = cache / "flow.parquet"
    if sha(target) != plan["cache_before_sha256"]:
        raise ValueError("cache_no_longer_matches_baseline")
    old = pd.read_parquet(target)
    validate_old(old)
    indexed = old.set_index(["code", "date"])
    manifest = json.loads((audit / "captures.json").read_text())
    replacements, deferred = [], []
    checked = 0
    cutoff = pd.Timestamp(plan["excluded_on_or_after"])
    for symbol in baseline["symbols"]:
        code = symbol["code"]
        origin = Path(plan["source_dir"]) / (code + ".json")
        if sha(origin) != symbol["capture_sha256"]:
            raise ValueError("initial_capture_changed")
        original = keyed(json.loads(origin.read_text()), "output2")
        controls = {}
        for endpoint in ("repeat", "current", "price"):
            name = code + "_" + endpoint + ".json"
            if name not in manifest:
                controls[endpoint] = {}
                continue
            path = audit / name
            if sha(path) != manifest[name]["sha256"]:
                raise ValueError("control_capture_changed")
            controls[endpoint] = keyed(json.loads(path.read_text()), "output" if endpoint == "current" else "output2")
        for day, raw in original.items():
            date = pd.to_datetime(day, format="%Y%m%d")
            key = (code, date)
            if date >= cutoff or key not in indexed.index:
                raise ValueError("unbounded_source_key")
            before = {field: int(indexed.loc[key, field]) for field in FIELDS}
            after = {field: number(raw[source]) for field, source in FIELDS.items()}
            if before == after:
                continue
            try:
                verified = verify_row(raw, *(controls[e].get(day) for e in ("repeat", "current", "price")))
                assert verified == after
            except (ValueError, KeyError) as exc:
                deferred.append({"code": code, "date": str(date.date()), "reason": str(exc)})
                continue
            checked += 1
            replacements.append({"code": code, "date": str(date.date()), "before": before, "after": after})
    result = {**plan, "capture_manifest_sha256": sha(audit / "captures.json"),
              "verified_conflict_rows": checked, "deferred_conflict_rows": len(deferred),
              "replacements": replacements, "deferred": deferred,
              "same_provider_controls": True, "point_in_time_verified": False}
    if sha(target) != plan["cache_before_sha256"]:
        raise ValueError("cache_changed_during_validation")
    write_json(audit / "replacement_plan.json", result)
    return old, result


def apply_plan(old, plan, cache, audit):
    target = cache / "flow.parquet"
    if sha(target) != plan["cache_before_sha256"]:
        raise ValueError("cache_changed_before_apply")
    if not old.index.equals(pd.RangeIndex(len(old))):
        raise ValueError("unexpected_cache_index")
    result = old.copy()
    positions = {(r.code, r.date): i for i, r in enumerate(old[["code", "date"]].itertuples(index=False))}
    changed_positions = set()
    for item in plan["replacements"]:
        i = positions[(item["code"], pd.Timestamp(item["date"]))]
        if {f: int(result.at[i, f]) for f in FIELDS} != item["before"]:
            raise ValueError("row_before_mismatch")
        for field, value in item["after"].items():
            result.at[i, field] = value
        changed_positions.add(i)
    validate_old(result)
    untouched = ~old.index.isin(changed_positions)
    pd.testing.assert_frame_equal(old.loc[untouched], result.loc[untouched], check_exact=True)
    pd.testing.assert_frame_equal(old[["code", "date"]], result[["code", "date"]], check_exact=True)
    backup = audit / "flow.before.parquet"
    if backup.exists() and sha(backup) != plan["cache_before_sha256"]:
        raise ValueError("backup_mismatch")
    if not backup.exists():
        shutil.copy2(target, backup)
    if sha(backup) != plan["cache_before_sha256"]:
        raise ValueError("backup_mismatch")
    report = {"status": "degraded" if plan["deferred"] else "ok", "changed_rows": len(changed_positions),
              "unchanged_rows": len(old) - len(changed_positions), "total_rows": len(old),
              "deferred_conflict_rows": len(plan["deferred"]), "before_sha256": plan["cache_before_sha256"],
              "replacement_plan_sha256": sha(audit / "replacement_plan.json"), "backup": str(backup),
              "state": "prepared", "prepared_at": datetime.now(timezone.utc).isoformat()}
    temp = target.with_name("flow.normalization.tmp.parquet")
    try:
        result.to_parquet(temp, index=False)
        pd.testing.assert_frame_equal(result, pd.read_parquet(temp), check_exact=True)
        with temp.open("rb") as f:
            os.fsync(f.fileno())
        report["after_sha256"] = sha(temp)
        write_json(audit / "apply_receipt.json", report)
        if sha(target) != plan["cache_before_sha256"]:
            raise ValueError("cache_changed_before_commit")
        os.replace(temp, target)
        report.update(state="committed", finished_at=datetime.now(timezone.utc).isoformat())
        write_json(audit / "apply_receipt.json", report)
    finally:
        temp.unlink(missing_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path.home() / "research_cache")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.capture:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env.local")
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
        from modules.kis_openapi import KISOpenAPIClient
        report = capture(args.source_receipt, args.audit, KISOpenAPIClient(timeout=8))
        print(json.dumps(report))
        return 2 if report["failures"] else 0
    with (args.cache / ".flow_writer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if legacy_writers():
            raise RuntimeError("legacy_writer_active")
        journal = args.audit / "apply_receipt.json"
        if journal.exists():
            prior = json.loads(journal.read_text())
            if sha(args.cache / "flow.parquet") == prior.get("after_sha256"):
                initialize(args.source_receipt, args.audit)
                if (sha(args.audit / "replacement_plan.json") != prior["replacement_plan_sha256"]
                        or sha(Path(prior["backup"])) != prior["before_sha256"]):
                    raise ValueError("prior_apply_evidence_changed")
                print(json.dumps({"status": "already_applied", "changed_rows": 0,
                                  "deferred_conflict_rows": prior["deferred_conflict_rows"]}))
                return 2 if prior["deferred_conflict_rows"] else 0
            if prior.get("state") == "committed":
                raise ValueError("cache_changed_after_prior_apply")
        old, plan = build_plan(args.source_receipt, args.audit, args.cache)
        if args.apply:
            report = apply_plan(old, plan, args.cache, args.audit)
        else:
            report = {"verified_conflict_rows": plan["verified_conflict_rows"],
                      "deferred_conflict_rows": plan["deferred_conflict_rows"], "apply": False}
        print(json.dumps(report))
        return 2 if plan["deferred"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
