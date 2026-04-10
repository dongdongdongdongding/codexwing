from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        try:
            return float(str(value).strip())
        except Exception:
            return 0.0


def _read_rows(limit: int, market: str | None) -> List[Dict[str, Any]]:
    from modules.db_manager import DBManager

    db = DBManager()
    if not db.client:
        raise RuntimeError("Supabase client unavailable.")

    q = db.client.table("agent_outcome_health").select(
        (
            "run_id,market,window_runs,runs_with_outcomes,outcomes_total,pending,resolved,expired,expired_rate,"
            "fallback_total,fallback_pending,fallback_resolved,fallback_expired,fallback_expired_rate,generated_at"
        )
    )
    if market:
        q = q.eq("market", str(market).upper())
    q = q.order("generated_at", desc=True).limit(max(1, int(limit)))
    res = q.execute()
    rows = res.data if res and hasattr(res, "data") and res.data else []
    return [r for r in rows if isinstance(r, dict)]


def _read_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
            if limit > 0 and len(rows) >= limit:
                break
    return rows


def build_report(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    totals = {
        "outcomes_total": 0,
        "pending": 0,
        "resolved": 0,
        "expired": 0,
        "fallback_total": 0,
        "fallback_pending": 0,
        "fallback_resolved": 0,
        "fallback_expired": 0,
    }
    recent: List[Dict[str, Any]] = []
    for row in rows:
        totals["outcomes_total"] += _safe_int(row.get("outcomes_total"))
        totals["pending"] += _safe_int(row.get("pending"))
        totals["resolved"] += _safe_int(row.get("resolved"))
        totals["expired"] += _safe_int(row.get("expired"))
        totals["fallback_total"] += _safe_int(row.get("fallback_total"))
        totals["fallback_pending"] += _safe_int(row.get("fallback_pending"))
        totals["fallback_resolved"] += _safe_int(row.get("fallback_resolved"))
        totals["fallback_expired"] += _safe_int(row.get("fallback_expired"))
        recent.append(
            {
                "run_id": row.get("run_id"),
                "market": row.get("market"),
                "outcomes_total": _safe_int(row.get("outcomes_total")),
                "pending": _safe_int(row.get("pending")),
                "resolved": _safe_int(row.get("resolved")),
                "expired": _safe_int(row.get("expired")),
                "expired_rate": round(_safe_float(row.get("expired_rate")), 4),
                "fallback_total": _safe_int(row.get("fallback_total")),
                "fallback_expired": _safe_int(row.get("fallback_expired")),
                "fallback_expired_rate": round(_safe_float(row.get("fallback_expired_rate")), 4),
                "generated_at": row.get("generated_at"),
            }
        )

    outcomes_total = int(totals.get("outcomes_total", 0))
    fallback_total = int(totals.get("fallback_total", 0))
    rates = {
        "expired_rate": round((int(totals.get("expired", 0)) / outcomes_total), 4) if outcomes_total > 0 else 0.0,
        "fallback_expired_rate": round((int(totals.get("fallback_expired", 0)) / fallback_total), 4)
        if fallback_total > 0
        else 0.0,
    }
    return {
        "rows_read": len(rows),
        "totals": totals,
        "rates": rates,
        "recent_runs": recent,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report outcome health rows from agent_outcome_health table.")
    parser.add_argument("--limit", type=int, default=50, help="Max rows to read.")
    parser.add_argument("--market", type=str, default=None, help="Optional market filter (e.g., NASDAQ).")
    parser.add_argument(
        "--local-jsonl",
        type=str,
        default="runtime_state/long_term/outcome_health/outcome_health.jsonl",
        help="Fallback local JSONL when DB is unavailable.",
    )
    args = parser.parse_args()

    market_filter = str(args.market or "").upper().strip()
    try:
        rows = _read_rows(limit=int(args.limit), market=args.market)
        source = "supabase"
        db_error = ""
    except Exception as e:
        rows = _read_jsonl(Path(args.local_jsonl), limit=max(1, int(args.limit)))
        if market_filter:
            rows = [r for r in rows if str(r.get("market", "")).upper() == market_filter]
        rows = sorted(rows, key=lambda r: str(r.get("generated_at", "")), reverse=True)
        source = "local_fallback"
        db_error = str(e)

    report = build_report(rows)
    report["source"] = source
    if db_error:
        report["db_error"] = db_error
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
