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
outcome_sync_partial). Never touches scanner_full or scanner_partial_legacy
rows. Within each (run_id, ticker, scan_mode, strategy_family, priority_rank)
group, keeps the row whose alpha_score is most informative and whose
created_at is newest, deletes the rest.

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


def _load_target_rows(db: DBManager, page_size: int = 1000) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    page = 0
    select_cols = "id,run_id,ticker,scan_mode,strategy_family,priority_rank,alpha_score,feature_origin,created_at,return_5d_pct,return_3d_pct,return_1d_pct,outcome_status"
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
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

    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
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
    print(f"  rows to delete       : {len(delete_ids):,}")

    if not delete_ids:
        print("Nothing to delete. Exit.")
        return 0

    if args.dry_run:
        print("\n(dry-run) sample delete IDs:")
        for did in delete_ids[:10]:
            print(f"  {did}")
        return 0

    print(f"\nDeleting {len(delete_ids):,} rows in batches of {args.batch_size}…")
    deleted = 0
    for i in range(0, len(delete_ids), args.batch_size):
        batch = delete_ids[i : i + args.batch_size]
        try:
            db.client.table("market_scan_results").delete().in_("id", batch).execute()
            deleted += len(batch)
            print(f"  progress: {deleted:,}/{len(delete_ids):,}", end="\r")
        except Exception as exc:
            print(f"\n  ⚠️ batch failed at offset {i}: {exc}")
            break
    print()
    print(f"Done. Deleted {deleted:,} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
