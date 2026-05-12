#!/usr/bin/env python3
"""Repair stale feature-quality metadata on feature-complete scanner rows.

This does not fabricate source data. It only updates scanner_full KR SWING rows
whose stored required feature fields are already complete, but whose quality
metadata still says incomplete because an outcome/archive merge overwrote it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


QUALITY_COLUMNS = (
    "feature_quality",
    "feature_completeness",
    "feature_missing_fields",
    "validation_excluded",
    "validation_excluded_reason",
)

SELECT_COLUMNS = ",".join(
    [
        "id",
        "ticker",
        "market",
        "market_type",
        "scan_mode",
        "feature_origin",
        "alpha_score",
        "tech_score",
        "ml_prob",
        "whale_score",
        "trend",
        "volume_ratio",
        "position",
        "tier",
        "decision_score",
        "entry_reference_price",
        "is_dummy_data",
        *QUALITY_COLUMNS,
    ]
)


def _is_kr_swing_scanner_full(row: Dict[str, Any]) -> bool:
    ticker = str(row.get("ticker") or "").upper()
    market = str(row.get("market") or row.get("market_type") or "").upper()
    scan_mode = str(row.get("scan_mode") or "").upper()
    return (
        row.get("feature_origin") == "scanner_full"
        and scan_mode == "SWING"
        and (market in {"KOSPI", "KOSDAQ"} or ticker.endswith((".KS", ".KQ")))
    )


def _metadata_diff(row: Dict[str, Any], recomputed: Dict[str, Any]) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}
    for key in QUALITY_COLUMNS:
        if row.get(key) != recomputed.get(key):
            updates[key] = recomputed.get(key)
    return updates


def _iter_scanner_full_rows(db: DBManager, page_size: int) -> Iterable[Dict[str, Any]]:
    page = 0
    while True:
        res = (
            db.client.table("market_scan_results")
            .select(SELECT_COLUMNS)
            .eq("feature_origin", "scanner_full")
            .eq("scan_mode", "SWING")
            .order("id", desc=False)
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        batch = res.data or []
        for row in batch:
            if _is_kr_swing_scanner_full(row):
                yield row
        if len(batch) < page_size:
            break
        page += 1


def build_repair_plan(db: DBManager, page_size: int, limit: int = 0) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    for row in _iter_scanner_full_rows(db, page_size=page_size):
        recomputed = db._recompute_feature_quality_payload(row, origin="scanner_full")
        if recomputed.get("feature_quality") != "complete":
            continue
        updates = _metadata_diff(row, recomputed)
        if not updates:
            continue
        plan.append(
            {
                "id": row.get("id"),
                "ticker": row.get("ticker"),
                "market": row.get("market") or row.get("market_type"),
                "old": {key: row.get(key) for key in QUALITY_COLUMNS},
                "updates": updates,
            }
        )
        if limit > 0 and len(plan) >= limit:
            break
    return plan


def apply_plan(db: DBManager, plan: List[Dict[str, Any]]) -> int:
    updated = 0
    for item in plan:
        row_id = item.get("id")
        if row_id is None:
            continue
        db.client.table("market_scan_results").update(item["updates"]).eq("id", row_id).execute()
        updated += 1
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write repairs to Supabase. Default is dry-run.")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=0, help="Limit repair plan rows for a staged run.")
    args = parser.parse_args()

    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")

    plan = build_repair_plan(db, page_size=args.page_size, limit=args.limit)
    updated = apply_plan(db, plan) if args.apply else 0
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry_run",
                "planned_updates": len(plan),
                "updated_rows": updated,
                "sample": plan[:5],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
