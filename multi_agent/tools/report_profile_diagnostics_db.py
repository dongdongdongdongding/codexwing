from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in {"1", "true", "y", "yes"}


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return 0


def _rows_from_db(limit: int, market: str | None, profile: str | None) -> List[Dict[str, Any]]:
    from modules.db_manager import DBManager

    db = DBManager()
    if not db.client:
        raise RuntimeError("Supabase client unavailable.")

    q = db.client.table("agent_profile_diagnostics").select(
        "run_id,market,current_profile,current_total_scans,current_result_count,flags,fallback_watchlist,generated_at"
    )
    if market:
        q = q.eq("market", str(market).upper())
    if profile:
        q = q.eq("current_profile", str(profile).lower())
    q = q.order("generated_at", desc=True).limit(max(1, int(limit)))
    res = q.execute()
    rows = res.data if res and hasattr(res, "data") and res.data else []
    return [r for r in rows if isinstance(r, dict)]


def build_report(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    profile_counts: Dict[str, int] = {}
    prod_gap_runs = 0
    prod_zero_alert_runs = 0
    fallback_applied_runs = 0
    recent_rows: List[Dict[str, Any]] = []

    for row in rows:
        profile = str(row.get("current_profile", "unknown")).lower()
        profile_counts[profile] = int(profile_counts.get(profile, 0)) + 1

        flags = row.get("flags", {})
        if not isinstance(flags, dict):
            flags = {}
        if _safe_bool(flags.get("prod_dev_gap")):
            prod_gap_runs += 1
        if _safe_bool(flags.get("prod_zero_streak_alert")):
            prod_zero_alert_runs += 1

        fb = row.get("fallback_watchlist", {})
        if not isinstance(fb, dict):
            fb = {}
        if _safe_bool(fb.get("applied")):
            fallback_applied_runs += 1

        recent_rows.append(
            {
                "run_id": row.get("run_id"),
                "market": row.get("market"),
                "profile": profile,
                "total_scans": _safe_int(row.get("current_total_scans")),
                "result_count": _safe_int(row.get("current_result_count")),
                "prod_dev_gap": _safe_bool(flags.get("prod_dev_gap")),
                "prod_zero_streak_alert": _safe_bool(flags.get("prod_zero_streak_alert")),
                "prod_zero_streak": _safe_int(flags.get("prod_zero_streak")),
                "fallback_applied": _safe_bool(fb.get("applied")),
                "fallback_source_run_id": fb.get("source_run_id"),
                "generated_at": row.get("generated_at"),
            }
        )

    return {
        "rows_read": len(rows),
        "profile_counts": profile_counts,
        "prod_gap_runs": prod_gap_runs,
        "prod_zero_alert_runs": prod_zero_alert_runs,
        "fallback_applied_runs": fallback_applied_runs,
        "recent_runs": recent_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report profile diagnostics from Supabase table.")
    parser.add_argument("--limit", type=int, default=50, help="Max rows to read.")
    parser.add_argument("--market", type=str, default=None, help="Optional market filter (e.g., NASDAQ).")
    parser.add_argument("--profile", type=str, default=None, help="Optional profile filter (e.g., prod/dev).")
    args = parser.parse_args()

    rows = _rows_from_db(limit=int(args.limit), market=args.market, profile=args.profile)
    report = build_report(rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

