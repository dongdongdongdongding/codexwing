"""Apply pinned responses for previously failed minute requests, without network.

Only missing, valid OHLCV rows may be inserted. Conflicting overlaps fail before
any mutation. Slice checkpoints are acquisition receipts, not session proof.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import fcntl
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools import backfill_kr_intraday as backfill
from multi_agent.tools.intraday_cache_journal import digest, save_json

FIELDS = {"Open": "stck_oprc", "High": "stck_hgpr", "Low": "stck_lwpr",
          "Close": "stck_prpr", "Volume": "cntg_vol"}


def strict_frame(payload, day):
    if payload.get("rt_cd") != "0":
        raise ValueError("unsuccessful_payload")
    rows = []
    for raw in payload.get("output2", []):
        if raw.get("stck_bsop_date") != day:
            continue
        date = pd.to_datetime(day + raw["stck_cntg_hour"], format="%Y%m%d%H%M%S")
        rows.append({"Date": date, **{col: float(str(raw[key]).replace(",", ""))
                                      for col, key in FIELDS.items()}})
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).set_index("Date")
    if frame.index.has_duplicates:
        for _, group in frame.groupby(level=0):
            if len(group.drop_duplicates()) != 1:
                raise ValueError("conflicting_duplicate_bars")
    return backfill.filter_bars(frame, day)


def prepare(evidence, cache):
    manifest = json.loads((evidence / "apply_manifest.json").read_text())
    receipt_path = evidence / "original_receipt.json"
    if digest(receipt_path) != manifest["receipt_sha256"]:
        raise ValueError("receipt_hash_mismatch")
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("market_div") != "J":
        raise ValueError("only_regular_J_receipts_supported")
    original = {(e["code"], e["day"], e["hour"]) for e in receipt["request_errors"]}
    seen, grouped, unresolved = set(), {}, []
    for item in manifest["files"]:
        if Path(item["path"]).name != item["path"]:
            raise ValueError("capture_path_must_be_local_filename")
        path = evidence / item["path"]
        if digest(path) != item["sha256"]:
            raise ValueError("capture_hash_mismatch")
        capture = json.loads(path.read_text())
        q = capture["request"]
        key = (q["code"], q["day"], q["hour"])
        if key not in original or key in seen or q["hour"] not in backfill.HOURS:
            raise ValueError("unexpected_or_duplicate_request")
        if len(q["code"]) != 6 or not q["code"].isdigit():
            raise ValueError("invalid_code")
        seen.add(key)
        if capture["status"] != "VALID":
            unresolved.append({"request": q, "status": capture["status"]})
            continue
        frame = strict_frame(capture["payload"], q["day"])
        if frame.empty:
            raise ValueError("valid_capture_has_no_requested_bars")
        grouped.setdefault(q["code"], []).append((q, frame))
    if seen != original:
        raise ValueError("capture_cohort_incomplete")
    prepared = []
    out = cache / "intraday"
    for code, captures in sorted(grouped.items()):
        path, state_path = out / (code + ".parquet"), out / ".backfill" / (code + ".json")
        old, state = pd.read_parquet(path), json.loads(state_path.read_text())
        stat = path.stat()
        if state.get("identity") != [stat.st_mtime_ns, stat.st_size]:
            raise ValueError("checkpoint_identity_changed")
        parts = []
        for query, frame in captures:
            cell = state.get("days", {}).get(query["day"])
            if not isinstance(cell, dict) or not set(cell.get("successful_hours", [])).issubset(backfill.HOURS):
                raise ValueError("invalid_existing_checkpoint")
            backfill.filter_bars(old, query["day"])
            common = old.index.intersection(frame.index)
            if not old.loc[common, list(FIELDS)].astype(float).equals(frame.loc[common, list(FIELDS)]):
                raise ValueError("overlapping_prices_changed")
            frame = frame.copy()
            frame["code"] = code
            parts.append(frame)
        added = pd.concat(parts)
        for _, group in added.groupby(level=0):
            if len(group.drop_duplicates()) != 1:
                raise ValueError("captures_disagree")
        prepared.append({"code": code, "path": path, "state_path": state_path, "old": old,
                         "state": state, "captures": captures, "added": added,
                         "before_sha": digest(path), "state_sha": digest(state_path)})
    return manifest, prepared, unresolved


def run(evidence, cache, *, apply=False):
    out = cache / "intraday"
    state_dir = out / ".backfill"
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "writer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if backfill.legacy_writers(cache):
            raise ValueError("legacy_writer_alive")
        manifest, prepared, unresolved = prepare(evidence, cache)
        audit = evidence / ("apply_" + datetime.now(backfill.KST).strftime("%Y%m%dT%H%M%S%f"))
        audit.mkdir(parents=True)
        report = {"apply": apply, "manifest_sha256": digest(evidence / "apply_manifest.json"),
                  "receipt_sha256": manifest["receipt_sha256"], "unresolved": unresolved,
                  "session_completeness": "NOT_ESTABLISHED", "rows": [], "audit": str(audit)}
        for item in prepared:
            path, state_path = item["path"], item["state_path"]
            if digest(path) != item["before_sha"] or digest(state_path) != item["state_sha"]:
                raise ValueError("input_changed_after_validation")
            old = item["old"]
            combined = pd.concat([old, item["added"]])
            combined = combined.loc[~combined.index.duplicated(keep="first")].sort_index()
            state = item["state"]
            before_state = json.dumps(state, sort_keys=True)
            for query, _ in item["captures"]:
                cell = state["days"][query["day"]]
                hours = set(cell.get("successful_hours", [])) | {query["hour"]}
                observed = backfill.filter_bars(combined, query["day"])
                cell.update(successful_hours=sorted(hours), rows_observed=len(observed),
                            first_bar=str(observed.index.min()), last_bar=str(observed.index.max()),
                            session_complete=None,
                            status="REQUESTED_ALL_SLICES" if hours == set(backfill.HOURS) else "PARTIAL_OR_EMPTY")
                if hours == set(backfill.HOURS):
                    cell.pop("retry_after", None)
            changed_state = before_state != json.dumps(state, sort_keys=True)
            if apply:
                (audit / (item["code"] + "_state_before.json")).write_bytes(state_path.read_bytes())
                combined = backfill.persist_bars(path, old, item["added"], item["before_sha"],
                    audit / "cache_journal", item["code"], "captured_retry")
                stat = path.stat()
                state["identity"] = [stat.st_mtime_ns, stat.st_size]
                if changed_state or len(combined) != len(old):
                    save_json(state_path, state)
            report["rows"].append({"code": item["code"], "added": len(combined)-len(old),
                "checkpoint_changed": changed_state, "before_sha256": item["before_sha"],
                "after_sha256": digest(path), "validated_requests": len(item["captures"])})
        save_json(audit / "report.json", report)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--cache", type=Path, default=Path.home() / "research_cache")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = run(args.evidence, args.cache, apply=args.apply)
    print(json.dumps({"audit": report["audit"], "files": len(report["rows"]),
                      "added": sum(r["added"] for r in report["rows"]),
                      "unresolved_requests": len(report["unresolved"]), "apply": args.apply}))


if __name__ == "__main__":
    main()
