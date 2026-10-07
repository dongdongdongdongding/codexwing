"""Restore verified flow provenance only; dry-run by default.

Each batch keeps immutable full-row backups. Three metadata fields are updated
by a typed full-row compare-and-swap in one SQL statement, then independently
read back. No labels, values, timestamps, schema or model fields are assigned.
"""
from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from modules.investor_flow_units import FLOW_VALUE_FIELDS, flow_metadata_for_values

META = ("flow_source", "flow_unit", "flow_asof")
TABLE = "public.scan_universe_snapshots"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as fh:
        temporary = Path(fh.name)
        try:
            json.dump(value, fh, ensure_ascii=False, allow_nan=False)
            fh.flush()
            os.fsync(fh.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def validate_plan(plan):
    entries = plan.get("updates", [])
    if not entries or len(entries) != plan.get("rows"):
        raise ValueError("invalid plan row count")
    ids = [e["id"] for e in entries]
    if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("invalid or duplicate ID")
    for e in entries:
        if set(e["before"]) != set(META) or set(e["after"]) != set(META):
            raise ValueError("only the three provenance fields may change")
        if set(e["expected_flow_values"]) != set(FLOW_VALUE_FIELDS):
            raise ValueError("incomplete flow value guard")
        if e["before"]["flow_source"] != "scan_universe_snapshot" or e["before"]["flow_unit"] != "source_units":
            raise ValueError("outside legacy generic provenance scope")
    return sorted(entries, key=lambda e: e["id"])


def owner_projection_sql():
    pairs = [("snapshot_source", "flow_source"), ("snapshot_unit", "flow_unit"),
             ("snapshot_asof", "flow_asof"), *[("snapshot_" + k, k) for k in FLOW_VALUE_FIELDS]]
    terms = [f"'{alias}',t.feature_snapshot->>'{key}'" for alias, key in pairs]
    terms.append("'snapshot_flow',t.feature_snapshot->'flow'")
    return "jsonb_build_object(" + ",".join(terms) + ")"


def read_sql(ids):
    if not ids or any(type(i) is not int or i <= 0 for i in ids):
        raise ValueError("invalid IDs")
    return (f"SELECT to_jsonb(t) AS row, {owner_projection_sql()} AS owner FROM {TABLE} t "
            f"WHERE id IN ({','.join(map(str, ids))}) ORDER BY id")


def cas_sql(updates):
    if not updates or any(set(x["after"]) != set(META) for x in updates):
        raise ValueError("only the three provenance fields may change")
    ids = [x["before"]["id"] for x in updates]
    if len(set(ids)) != len(ids) or any(type(i) is not int or i <= 0 for i in ids):
        raise ValueError("invalid or duplicate ID")
    encoded = base64.b64encode(json.dumps(updates, allow_nan=False).encode()).decode()
    return ("WITH p AS (SELECT jsonb_populate_record(NULL::" + TABLE + ",x->'before') AS b, "
            "x->'after' AS patch FROM jsonb_array_elements(convert_from(decode('" + encoded +
            "','base64'),'UTF8')::jsonb) x) UPDATE " + TABLE + " t SET " +
            ",".join(f"{k}=p.patch->>'{k}'" for k in META) +
            " FROM p WHERE t.id=(p.b).id AND to_jsonb(t)=to_jsonb(p.b) RETURNING t.id")


class Database:
    def __init__(self):
        import requests
        self.session = requests.Session()
        token = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
        ref = (urlparse(os.environ.get("SUPABASE_URL", "")).hostname or "").split(".")[0]
        if not token or not re.fullmatch(r"[a-z0-9]+", ref):
            raise RuntimeError("Management API credentials unavailable")
        self.endpoint = f"https://api.supabase.com/v1/projects/{ref}/database/query"
        self.session.headers["Authorization"] = f"Bearer {token}"

    def query(self, sql):
        response = self.session.post(self.endpoint, json={"query": sql}, timeout=60)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Database HTTP {response.status_code}")
        result = response.json()
        if not isinstance(result, list):
            raise RuntimeError("Unexpected database response")
        return result

    def read(self, ids):
        return self.query(read_sql(ids))

    def cas(self, updates):
        return self.query(cas_sql(updates))


def matches_evidence(entry, captured):
    row = captured["row"]
    if any(row.get(k) != entry[k] for k in ("id", "run_id", "ticker")):
        return False
    if any(row.get(k) != v for k, v in entry["expected_flow_values"].items()):
        return False
    if captured["owner"] != entry["expected_owner"]:
        return False
    resolved = flow_metadata_for_values({**row, **entry["before"]}, row)
    return all(resolved[k] == entry["after"][k] for k in META)


def process_batch(entries, db, directory, plan_sha, *, apply=False):
    directory.mkdir(parents=True, exist_ok=True)
    ids = [e["id"] for e in entries]
    current = db.read(ids)
    if len({x["row"]["id"] for x in current}) != len(current):
        raise ValueError("duplicate database rows")
    backup_path = directory / "before.json"
    if backup_path.exists():
        saved = json.loads(backup_path.read_bytes())
        if saved["plan_sha256"] != plan_sha or saved["ids"] != ids:
            raise ValueError("backup belongs to another plan/batch")
        expected_hash = (directory / "before.sha256").read_text().strip()
        if digest(backup_path.read_bytes()) != expected_hash:
            raise ValueError("backup hash mismatch")
    else:
        saved = {"plan_sha256": plan_sha, "ids": ids, "rows": current}
        write_json(backup_path, saved)
        (directory / "before.sha256").write_text(digest(backup_path.read_bytes()) + "\n")
    original = {x["row"]["id"]: x for x in saved["rows"]}
    present = {x["row"]["id"]: x for x in current}
    statuses, updates = {}, []
    for e in entries:
        i = e["id"]
        if i not in present or i not in original:
            statuses[i] = "missing_row"
            continue
        before = original[i]["row"]
        now = present[i]["row"]
        if not matches_evidence(e, present[i]) or not matches_evidence(e, original[i]):
            statuses[i] = "evidence_changed"
            continue
        meta = {k: now.get(k) for k in META}
        if meta == e["after"]:
            statuses[i] = "already_correct" if now == {**before, **e["after"]} else "other_fields_changed"
        elif meta != e["before"] or now != before:
            statuses[i] = "compare_and_swap_conflict"
        elif apply:
            updates.append({"before": before, "after": e["after"]})
        else:
            statuses[i] = "eligible"
    error = None
    if updates:
        try:
            db.cas(updates)
        except Exception as exc:
            # The server may have committed even if its response was lost.
            # Re-read and reconcile; never retry an unconditional mutation.
            error = type(exc).__name__
        after = {x["row"]["id"]: x["row"] for x in db.read([x["before"]["id"] for x in updates])}
        for u in updates:
            i = u["before"]["id"]
            actual = after.get(i)
            if actual == {**u["before"], **u["after"]}:
                statuses[i] = "applied_verified"
            elif actual == u["before"]:
                statuses[i] = "not_applied"
            else:
                statuses[i] = "concurrent_or_unexpected_change"
    from collections import Counter
    counts = dict(Counter(statuses.values()))
    ok = all(s in {"applied_verified", "already_correct", "eligible"} for s in statuses.values())
    receipt = {"plan_sha256": plan_sha, "apply": apply, "status": "ok" if ok else "degraded",
               "counts": counts, "row_status": statuses, "transport_error": error,
               "backup_sha256": digest(backup_path.read_bytes()),
               "recorded_at": datetime.now(timezone.utc).isoformat()}
    event = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    write_json(directory / "events" / f"{event}.json", receipt)
    write_json(directory / ("apply.json" if apply else "preview.json"), receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-batches", type=int, default=0)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    raw = args.plan.read_bytes()
    if digest(raw) != args.plan_sha256:
        raise ValueError("plan hash mismatch")
    entries = validate_plan(json.loads(raw))
    if not 1 <= args.batch_size <= 100:
        raise ValueError("batch size outside 1..100")
    if args.max_batches < 0:
        raise ValueError("max batches must be nonnegative")
    args.audit.mkdir(parents=True, exist_ok=True)
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env.local")
    db = Database()
    receipts = []
    from collections import Counter
    counts = Counter()
    with (args.audit / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for index, start in enumerate(range(0, len(entries), args.batch_size)):
            if args.max_batches and index >= args.max_batches:
                break
            if digest(args.plan.read_bytes()) != args.plan_sha256:
                raise ValueError("plan changed during execution")
            receipt = process_batch(entries[start:start + args.batch_size], db,
                                    args.audit / f"batch_{index:05d}", args.plan_sha256, apply=args.apply)
            receipts.append(receipt)
            counts.update(receipt["counts"])
            summary = {"plan_sha256": args.plan_sha256, "apply": args.apply, "planned_rows": len(entries),
                       "observed_rows": sum(counts.values()), "batches": len(receipts), "counts": dict(counts),
                       "status": "ok" if all(r["status"] == "ok" for r in receipts) else "degraded"}
            summary["complete"] = summary["observed_rows"] == len(entries) and summary["status"] == "ok"
            write_json(args.audit / "latest.json", summary)
            print(json.dumps(summary), flush=True)
            if receipt["transport_error"] and receipt["status"] != "ok":
                break
    return 0 if summary["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
