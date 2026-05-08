#!/usr/bin/env python3
"""Backfill feature_origin / validation_excluded / feature_quality metadata on
existing market_scan_results rows so no-dummy training gates and validation
reports can distinguish scanner-origin rows from outcome-sync partial rows.

2026-04-23 q7h added these columns to the Supabase schema but pre-existing
20k+ rows remained NULL. This script computes the provenance retroactively
from the fields that are present on each row.

Usage:
  python multi_agent/tools/backfill_scan_feature_provenance.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


REQUIRED_FEATURE_FIELDS = [
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
]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, str) and value.strip().lower() in {"", "?", "nan", "none", "null", "unknown", "na", "n/a"}:
        return True
    return False


def _infer_origin(row: Dict[str, Any]) -> str:
    alpha = row.get("alpha_score")
    tech = row.get("tech_score")
    whale = row.get("whale_score")
    volume_ratio = row.get("volume_ratio")
    if not _is_missing(alpha) and not _is_missing(tech) and not _is_missing(whale):
        if not _is_missing(volume_ratio):
            return "scanner_full_legacy"
        return "scanner_partial_legacy"
    if not _is_missing(alpha):
        return "scanner_archive_outcome"
    return "outcome_sync_partial"


def _compute_provenance(row: Dict[str, Any]) -> Dict[str, Any]:
    missing = [key for key in REQUIRED_FEATURE_FIELDS if _is_missing(row.get(key))]
    if not missing and _is_missing(row.get("trend")):
        missing.append("trend")
    completeness = round((len(REQUIRED_FEATURE_FIELDS) - len(missing)) / len(REQUIRED_FEATURE_FIELDS), 4)
    origin = _infer_origin(row)
    quality = "complete" if not missing else "incomplete"
    reason = "FEATURE_MISSING:" + ",".join(missing) if missing else None
    validation_excluded = bool(missing)
    return {
        "feature_origin": origin,
        "feature_quality": quality,
        "feature_completeness": completeness,
        "feature_missing_fields": missing,
        "validation_excluded": validation_excluded,
        "validation_excluded_reason": reason,
        "is_dummy_data": False,
    }


def _needs_backfill(row: Dict[str, Any]) -> bool:
    return any(
        row.get(key) is None
        for key in (
            "feature_origin",
            "feature_quality",
            "feature_completeness",
            "feature_missing_fields",
            "validation_excluded",
        )
    )


def _load_rows(db: DBManager, limit: int | None, market_filter: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    page = 0
    page_size = 1000
    while True:
        q = db.client.table("market_scan_results").select("*").order("created_at", desc=False)
        q = q.range(page * page_size, page * page_size + page_size - 1)
        res = q.execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
        if limit and len(rows) >= limit:
            rows = rows[:limit]
            break
    if market_filter == "kr_swing":
        rows = [r for r in rows if _is_kr_swing(r)]
    return rows


def _is_kr_swing(row: Dict[str, Any]) -> bool:
    scan_mode = str(row.get("scan_mode") or "").upper()
    if scan_mode and scan_mode != "SWING":
        return False
    ticker = str(row.get("ticker") or "").upper()
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        return True
    market_type = str(row.get("market_type") or "").upper()
    if market_type in {"KOSPI", "KOSDAQ", "KR"}:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Cap rows processed (0=all)")
    parser.add_argument("--batch", type=int, default=100, help="Rows per UPDATE batch")
    parser.add_argument(
        "--scope",
        choices=["all", "kr_swing"],
        default="all",
        help="Restrict to KR SWING rows (scan_mode=SWING AND market in KOSPI/KOSDAQ/KR or ticker .KS/.KQ)",
    )
    args = parser.parse_args()

    db = DBManager()
    if not db.client:
        print("ERROR: Supabase client unavailable")
        return 1

    market_filter = "kr_swing" if args.scope == "kr_swing" else None
    rows = _load_rows(db, limit=args.limit or None, market_filter=market_filter)
    print(f"loaded_rows={len(rows)} scope={args.scope}")

    buckets: Dict[str, int] = {}
    updates_needed: List[Dict[str, Any]] = []
    for row in rows:
        if not _needs_backfill(row):
            continue
        prov = _compute_provenance(row)
        buckets[prov["feature_origin"]] = buckets.get(prov["feature_origin"], 0) + 1
        updates_needed.append(
            {
                "id": row.get("id"),
                "payload": prov,
            }
        )

    print(f"needs_backfill={len(updates_needed)}")
    print(f"bucket_breakdown={json.dumps(buckets, ensure_ascii=False)}")

    if args.dry_run:
        print("dry-run: no updates performed")
        return 0

    updated = 0
    failures = 0
    for entry in updates_needed:
        row_id = entry["id"]
        payload = db._filter_payload_to_existing_columns("market_scan_results", entry["payload"])
        if not payload or row_id is None:
            continue
        try:
            db.client.table("market_scan_results").update(payload).eq("id", row_id).execute()
            updated += 1
            if updated % args.batch == 0:
                print(f"  updated_so_far={updated}")
        except Exception as exc:
            failures += 1
            print(f"  update_failed id={row_id} err={exc}")

    print(f"done updated={updated} failed={failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
