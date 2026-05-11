#!/usr/bin/env python3
"""Remove duplicate scanner_archive_outcome / outcome_sync_partial rows.

Why this exists
---------------
upsert_scan_archive_outcomes used .eq() on scan_mode and strategy_family,
which never matches NULL columns. Every sync call therefore appended a new
row instead of updating the existing peer. Verified single ticker (058470.KQ
rank=1 in RUN-6ABC01DC) inflated to 39 identical rows. Training read the
duplicates as if they were independent samples — same ticker, same outcome,
counted dozens of times. Once the lookup fix lands, future runs are clean,
but the historical pollution is still in the table.

Scope
-----
Operates only on rows where feature_origin IN (scanner_archive_outcome,
outcome_sync_partial). Never deletes scanner_full or scanner_partial_legacy
rows. If a feature-rich scanner peer exists for the same
(run_id, ticker, market, scan_mode), it merges outcome fields into that peer
and deletes the stub. Otherwise, within each
(run_id, ticker, scan_mode, strategy_family, priority_rank) group, keeps the
row whose alpha_score is most informative and whose created_at is newest,
deletes the rest.

Strategy
--------
Pages through rows in a stable order, builds groups, and emits a delete plan.
In --dry-run mode prints the plan and exits. With --apply it deletes in
batches of 100.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


def _select_cols(db: DBManager, requested: List[str]) -> str:
    known = db._get_table_columns("market_scan_results")
    if not known:
        return ",".join(requested)
    return ",".join([col for col in requested if col in known])


def _load_target_rows(db: DBManager, page_size: int = 1000) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    page = 0
    select_cols = _select_cols(
        db,
        [
            "id",
            "run_id",
            "ticker",
            "market",
            "scan_mode",
            "strategy_family",
            "priority_rank",
            "alpha_score",
            "feature_origin",
            "created_at",
            "recommended_at",
            "return_30d_pct",
            "return_14d_pct",
            "return_7d_pct",
            "return_5d_pct",
            "return_3d_pct",
            "return_2d_pct",
            "return_1d_pct",
            "latest_return_pct",
            "outcome_status",
            "outcome_label",
            "outcome_recorded_at",
            "performance_updated_at",
            "decision",
            "decision_bucket",
            "target_horizon_days",
        ],
    )
    while True:
        res = (
            db.client.table("market_scan_results")
            .select(select_cols)
            .in_("feature_origin", ["scanner_archive_outcome", "outcome_sync_partial"])
            .order("created_at", desc=False)
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        print(f"  loaded: {len(rows):,}", end="\r")
        if len(batch) < page_size:
            break
        page += 1
    print()
    return rows


def _row_score(row: Dict[str, Any]) -> tuple:
    """Higher tuple = keep. Prefer rows with alpha_score, with returns, newest."""
    alpha_present = 1 if row.get("alpha_score") is not None else 0
    has_return = 1 if any(
        row.get(k) is not None for k in ("return_5d_pct", "return_3d_pct", "return_1d_pct")
    ) else 0
    resolved = 1 if (row.get("outcome_status") or "").upper() == "RESOLVED" else 0
    created_at = row.get("created_at") or ""
    return (alpha_present, has_return, resolved, created_at)


def _load_feature_peers(db: DBManager, rows: List[Dict[str, Any]], page_size: int = 1000) -> Dict[tuple, Dict[str, Any]]:
    run_ids = sorted({str(r.get("run_id")) for r in rows if r.get("run_id")})
    peer_by_key: Dict[tuple, Dict[str, Any]] = {}
    select_cols = _select_cols(
        db,
        [
            "id",
            "run_id",
            "ticker",
            "market",
            "scan_mode",
            "feature_origin",
            "alpha_score",
            "created_at",
            "return_30d_pct",
            "return_14d_pct",
            "return_7d_pct",
            "return_5d_pct",
            "return_3d_pct",
            "return_2d_pct",
            "return_1d_pct",
            "outcome_status",
        ],
    )
    for i in range(0, len(run_ids), 50):
        batch_run_ids = run_ids[i : i + 50]
        page = 0
        while True:
            res = (
                db.client.table("market_scan_results")
                .select(select_cols)
                .in_("run_id", batch_run_ids)
                .not_.is_("alpha_score", "null")
                .order("created_at", desc=True)
                .range(page * page_size, page * page_size + page_size - 1)
                .execute()
            )
            batch = res.data or []
            for row in batch:
                if db._is_outcome_sync_origin(row.get("feature_origin")):
                    continue
                key = (row.get("run_id"), row.get("ticker"), row.get("market"), row.get("scan_mode"))
                current = peer_by_key.get(key)
                if current is None or db._feature_rich_row_score(row) > db._feature_rich_row_score(current):
                    peer_by_key[key] = row
            if len(batch) < page_size:
                break
            page += 1
    return peer_by_key


def _merge_payload_from_stub(stub: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "return_30d_pct",
        "return_14d_pct",
        "return_7d_pct",
        "return_5d_pct",
        "return_3d_pct",
        "return_2d_pct",
        "return_1d_pct",
        "latest_return_pct",
        "outcome_status",
        "outcome_label",
        "outcome_recorded_at",
        "performance_updated_at",
        "decision",
        "decision_bucket",
        "target_horizon_days",
    ]
    return {
        key: stub.get(key)
        for key in keys
        if stub.get(key) is not None and not (isinstance(stub.get(key), str) and not stub.get(key).strip())
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--merge-scanner-peers",
        action="store_true",
        help="Merge outcome stubs into feature-rich scanner peers before deleting stubs.",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Specify --dry-run or --apply", file=sys.stderr)
        return 2

    db = DBManager()
    if not db.client:
        print("Supabase client unavailable.", file=sys.stderr)
        return 2

    print("Loading scanner_archive_outcome / outcome_sync_partial rows…")
    rows = _load_target_rows(db)
    print(f"Total candidate rows: {len(rows):,}")

    merge_updates: Dict[str, Dict[str, Any]] = {}
    delete_after_merge: List[str] = []
    if args.merge_scanner_peers and rows:
        print("Loading feature-rich scanner peers…")
        peers = _load_feature_peers(db, rows)
        for stub in rows:
            key = (stub.get("run_id"), stub.get("ticker"), stub.get("market"), stub.get("scan_mode"))
            peer = peers.get(key)
            if not peer:
                continue
            peer_id = peer.get("id")
            stub_id = stub.get("id")
            if not peer_id or not stub_id or peer_id == stub_id:
                continue
            payload = _merge_payload_from_stub(stub)
            if payload:
                merge_updates[peer_id] = db._merge_non_empty_payload(merge_updates.get(peer_id, {}), payload)
            delete_after_merge.append(stub_id)

    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    merged_delete_set = set(delete_after_merge)
    for r in rows:
        if r.get("id") in merged_delete_set:
            continue
        key = (
            r.get("run_id"),
            r.get("ticker"),
            r.get("scan_mode"),
            r.get("strategy_family"),
            r.get("priority_rank"),
        )
        groups[key].append(r)

    delete_ids: List[str] = []
    keep_count = 0
    duplicate_groups = 0
    for key, members in groups.items():
        if len(members) <= 1:
            keep_count += 1
            continue
        duplicate_groups += 1
        members_sorted = sorted(members, key=_row_score, reverse=True)
        keep = members_sorted[0]
        keep_count += 1
        for r in members_sorted[1:]:
            delete_ids.append(r["id"])

    print(f"\nUnique keys total      : {len(groups):,}")
    print(f"  keys with duplicates : {duplicate_groups:,}")
    print(f"  rows to keep         : {keep_count:,}")
    print(f"  rows to merge        : {len(delete_after_merge):,}")
    print(f"  scanner peers update : {len(merge_updates):,}")
    print(f"  rows to delete       : {len(delete_ids) + len(delete_after_merge):,}")

    if not delete_ids and not delete_after_merge:
        print("Nothing to delete. Exit.")
        return 0

    if args.dry_run:
        if delete_after_merge:
            print("\n(dry-run) sample merge-delete stub IDs:")
            for did in delete_after_merge[:10]:
                print(f"  {did}")
        print("\n(dry-run) sample delete IDs:")
        for did in delete_ids[:10]:
            print(f"  {did}")
        return 0

    if merge_updates:
        print(f"\nUpdating {len(merge_updates):,} scanner peers with outcome fields…")
        updated = 0
        for peer_id, payload in merge_updates.items():
            db.client.table("market_scan_results").update(payload).eq("id", peer_id).execute()
            updated += 1
            print(f"  update progress: {updated:,}/{len(merge_updates):,}", end="\r")
        print()

    all_delete_ids = list(dict.fromkeys(delete_after_merge + delete_ids))
    print(f"\nDeleting {len(all_delete_ids):,} rows in batches of {args.batch_size}…")
    deleted = 0
    for i in range(0, len(all_delete_ids), args.batch_size):
        batch = all_delete_ids[i : i + args.batch_size]
        try:
            db.client.table("market_scan_results").delete().in_("id", batch).execute()
            deleted += len(batch)
            print(f"  progress: {deleted:,}/{len(all_delete_ids):,}", end="\r")
        except Exception as exc:
            print(f"\n  ⚠️ batch failed at offset {i}: {exc}")
            break
    print()
    print(f"Done. Deleted {deleted:,} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
