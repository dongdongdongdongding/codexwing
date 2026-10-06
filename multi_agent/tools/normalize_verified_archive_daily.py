"""Normalize a captured KR cohort against frozen KIS J adjusted daily bars.

Dry-run by default. Only exact original run/ticker/reference matches qualify.
Preserves recommendation prices and exclusions; these are valuation labels,
not executable contract returns. Every source is hashed before planning/apply.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import base64
import os
import re
from urllib.parse import urlparse

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.repair_issued_outcomes import audit_and_apply, recompute
from research.audit_kr_touch10_price_source import parse_bars
from multi_agent.tools.backfill_scanner_full_returns import _row_scan_date


def cas_sql(before, patch):
    """Typed full-row CAS in the request body avoids oversized REST URLs."""
    if not patch or any(not re.fullmatch(r"[a-z_][a-z0-9_]*", k) for k in set(before) | set(patch)):
        raise ValueError("invalid column identifier")
    if set(patch) - {"feature_snapshot", "latest_return_pct", "max_high_return_5d_pct",
                      "hit_5pct_within_5d", "hit_5pct_within_5d_at", "swing_target_label_version",
                      *(f"return_{h}d_pct" for h in (1, 2, 3, 5, 7, 14, 30))}:
        raise ValueError("outside daily normalization fields")
    def record(value):
        encoded = base64.b64encode(json.dumps(value, allow_nan=False).encode()).decode()
        return "jsonb_populate_record(NULL::public.market_scan_results, convert_from(decode('" + encoded + "','base64'),'UTF8')::jsonb)"
    assignments = ", ".join(f'"{key}" = p."{key}"' for key in sorted(patch))
    predicates = " AND ".join(f't."{key}" IS NOT DISTINCT FROM b."{key}"' for key in sorted(before))
    return (f"WITH b AS (SELECT * FROM {record(before)}), p AS (SELECT * FROM {record(patch)}) "
            f"UPDATE public.market_scan_results t SET {assignments}, performance_updated_at = now() "
            f"FROM b, p WHERE t.id = b.id AND {predicates} RETURNING to_jsonb(t) AS row")


def management_cas(before, patch):
    import requests
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
    ref = (urlparse(os.environ.get("SUPABASE_URL", "")).hostname or "").split(".")[0]
    if not token or not re.fullmatch(r"[a-z0-9]+", ref):
        raise RuntimeError("Management API credentials unavailable")
    response = requests.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
        headers={"Authorization": f"Bearer {token}"}, json={"query": cas_sql(before, patch)}, timeout=30)
    if response.status_code != 201 and response.status_code != 200:
        raise RuntimeError(f"Management API CAS failed: HTTP {response.status_code}")
    result = response.json()
    if not isinstance(result, list):
        raise RuntimeError("unexpected CAS response")
    # Management API serializes NUMERIC columns as strings, unlike PostgREST.
    # A JSONB row envelope retains their JSON number types for verification.
    return [item["row"] for item in result]


def original_matches(row, outcomes):
    matches = [x for x in outcomes if x.get("ticker") == row.get("ticker")]
    return (len(matches) == 1 and matches[0].get("entry_reference_price") is not None
            and matches[0].get("entry_reference_price") == row.get("entry_reference_price")
            and pd.Timestamp(matches[0].get("recommended_at")) == pd.Timestamp(row.get("recommended_at")))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--evidence", type=Path, required=True)
    ap.add_argument("--calendar", type=Path, default=Path.home()/"research_cache/px_long.parquet")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    manifest = read(args.evidence/"price_request.json")
    captured = read(args.evidence/"current_rows_before.json")
    if hashes[str(args.evidence/"current_rows_before.json")] != manifest["cohort_sha256"]:
        raise ValueError("cohort digest mismatch")
    request = manifest["request"]
    if request.get("adjusted") is not True or request.get("market_div") != "J":
        raise ValueError("requires KIS KRX adjusted prices")
    start = pd.to_datetime(request["start_date"], format="%Y%m%d")
    end = pd.to_datetime(request["end_date"], format="%Y%m%d")
    # Read the same bytes whose digest is recorded, even if a producer swaps files.
    import io
    raw_calendar = args.calendar.read_bytes()
    hashes[str(args.calendar)] = hashlib.sha256(raw_calendar).hexdigest()
    dates = pd.read_parquet(io.BytesIO(raw_calendar), columns=["date"]).date.drop_duplicates()
    sessions = dates[(dates >= start) & (dates <= end)]
    from modules.db_manager import DBManager
    client = DBManager().client
    current = client.table("market_scan_results").select("*").in_("id", manifest["ids"]).execute().data
    current = {r["id"]: r for r in current}
    if set(current) != set(manifest["ids"]):
        raise ValueError("incomplete current DB cohort")
    plan, skipped = [], []
    for captured_row in captured:
        row = current[captured_row["id"]]
        if any(row.get(k) != captured_row.get(k) for k in ("run_id", "ticker", "recommended_at", "base_trade_date", "entry_reference_price")):
            raise ValueError("captured identity changed")
        if row.get("market_type") != "KR" or not str(row.get("run_id", "")).startswith("RUN-"):
            raise ValueError("outside generic KR scope")
        original = read(args.root/"runtime_state/shared_working"/row["run_id"]/"realized_outcomes.json")
        if not original_matches(row, original.get("outcomes", [])):
            skipped.append({"id": row["id"], "reason": "original_identity_unverified"})
            continue
        signal_day = _row_scan_date(row)
        eligible = sessions[sessions >= pd.Timestamp(signal_day)].sort_values()
        if signal_day is None or eligible.empty or str(eligible.iloc[0].date()) != row.get("base_trade_date"):
            raise ValueError("base date disagrees with original market-local signal day")
        code = row["ticker"].split(".")[0]
        source_path = args.evidence/f"kis_{code}.json"
        evidence = read(source_path)
        if evidence.get("code") != code or evidence.get("request") != request:
            raise ValueError("price request mismatch")
        prices = parse_bars(evidence["payload"], start, end)
        patch, basis = recompute(row, row, prices, sessions,
                                 price_source="KIS:inquire_daily_itemchartprice:J:adjusted=0")
        basis["evidence_sha256"] = hashes[str(source_path)]
        # recompute compares before provenance is appended; compare the final
        # envelope to keep repeated execution a true no-op.
        if patch.get("feature_snapshot") == row.get("feature_snapshot"):
            patch.pop("feature_snapshot", None)
        if patch:
            plan.append({"before": row, "patch": patch, "basis": basis})

    def guard():
        for path, expected in hashes.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
                raise RuntimeError("source changed after planning")

    guard()
    result = audit_and_apply(plan, args.evidence/"normalization", {"source_sha256": hashes,
        "skipped": skipped, "contract_pnl": False, "cas_transport": "management_api_full_row"},
        client, args.apply, guard, cas_update=management_cas)
    print(json.dumps({**result, "skipped": skipped}, ensure_ascii=False))


if __name__ == "__main__":
    main()
