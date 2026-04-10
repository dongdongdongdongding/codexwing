from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
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
    return str(value).strip().lower() in {"1", "true", "y", "yes"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return int(default)


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_horizon_days(value: Any, default: int = 3) -> int:
    if value is None:
        return max(1, int(default))
    text = str(value).strip().upper()
    if text.startswith("T+"):
        text = text[2:]
    if text.endswith("D"):
        text = text[:-1]
    try:
        return max(1, int(float(text)))
    except Exception:
        return max(1, int(default))


def _batch(seq: List[str], size: int) -> List[List[str]]:
    out: List[List[str]] = []
    step = max(1, int(size))
    for i in range(0, len(seq), step):
        out.append(seq[i : i + step])
    return out


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_profile_rows(limit_runs: int, market: str | None) -> tuple[Any, List[Dict[str, Any]]]:
    from modules.db_manager import DBManager

    db = DBManager()
    if not db.client:
        raise RuntimeError("Supabase client unavailable.")
    q = db.client.table("agent_profile_diagnostics").select(
        "run_id,market,current_profile,fallback_watchlist,generated_at"
    )
    if market:
        q = q.eq("market", str(market).upper())
    q = q.order("generated_at", desc=True).limit(max(1, int(limit_runs)))
    res = q.execute()
    rows = res.data if res and hasattr(res, "data") and res.data else []
    rows = [r for r in rows if isinstance(r, dict)]
    return db, rows


def _read_outcome_rows(db: Any, run_ids: List[str]) -> List[Dict[str, Any]]:
    if not run_ids:
        return []
    rows: List[Dict[str, Any]] = []
    for chunk in _batch(run_ids, size=100):
        q = db.client.table("agent_realized_outcomes").select("run_id,ticker,decision,status,horizon,recommended_at")
        q = q.in_("run_id", chunk)
        res = q.execute()
        data = res.data if res and hasattr(res, "data") and res.data else []
        rows.extend([r for r in data if isinstance(r, dict)])
    return rows


def build_report(profile_rows: List[Dict[str, Any]], outcome_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    run_meta: Dict[str, Dict[str, Any]] = {}
    for row in profile_rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        fb = row.get("fallback_watchlist", {})
        if not isinstance(fb, dict):
            fb = {}
        run_meta[run_id] = {
            "market": row.get("market"),
            "profile": str(row.get("current_profile", "unknown")).lower(),
            "fallback_applied": _safe_bool(fb.get("applied")),
            "fallback_source_run_id": fb.get("source_run_id"),
            "generated_at": row.get("generated_at"),
        }

    per_run: Dict[str, Dict[str, Any]] = {}
    now_dt = datetime.now(timezone.utc)
    for row in outcome_rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        bucket = per_run.setdefault(
            run_id,
            {
                "outcomes_total": 0,
                "pending": 0,
                "resolved": 0,
                "expired": 0,
                "fallback_total": 0,
                "fallback_pending": 0,
                "fallback_resolved": 0,
                "fallback_expired": 0,
                "fallback_stale_pending": 0,
            },
        )
        bucket["outcomes_total"] += 1
        status = str(row.get("status", "")).upper()
        if status == "PENDING":
            bucket["pending"] += 1
        elif status == "RESOLVED":
            bucket["resolved"] += 1
        elif status == "EXPIRED":
            bucket["expired"] += 1

        if str(row.get("decision", "")).upper() != "FALLBACK_WATCHLIST":
            continue
        bucket["fallback_total"] += 1
        if status == "PENDING":
            bucket["fallback_pending"] += 1
            rec_dt = _parse_iso(row.get("recommended_at"))
            horizon_days = _parse_horizon_days(row.get("horizon"), default=3)
            if rec_dt is not None and now_dt >= (rec_dt + timedelta(days=horizon_days)):
                bucket["fallback_stale_pending"] += 1
        elif status == "RESOLVED":
            bucket["fallback_resolved"] += 1
        elif status == "EXPIRED":
            bucket["fallback_expired"] += 1

    totals = {
        "outcomes_total": 0,
        "pending": 0,
        "resolved": 0,
        "expired": 0,
        "fallback_total": 0,
        "fallback_pending": 0,
        "fallback_resolved": 0,
        "fallback_expired": 0,
        "fallback_stale_pending": 0,
    }
    recent_runs: List[Dict[str, Any]] = []
    runs_with_fallback = 0
    fallback_applied_runs = 0

    for run_id, meta in run_meta.items():
        agg = per_run.get(
            run_id,
            {
                "outcomes_total": 0,
                "pending": 0,
                "resolved": 0,
                "expired": 0,
                "fallback_total": 0,
                "fallback_pending": 0,
                "fallback_resolved": 0,
                "fallback_expired": 0,
                "fallback_stale_pending": 0,
            },
        )
        if int(agg.get("fallback_total", 0)) > 0:
            runs_with_fallback += 1
        if bool(meta.get("fallback_applied")):
            fallback_applied_runs += 1
        for key in totals.keys():
            totals[key] += int(agg.get(key, 0))

        fallback_total = int(agg.get("fallback_total", 0))
        recent_runs.append(
            {
                "run_id": run_id,
                "market": meta.get("market"),
                "profile": meta.get("profile"),
                "fallback_applied": bool(meta.get("fallback_applied")),
                "fallback_source_run_id": meta.get("fallback_source_run_id"),
                "generated_at": meta.get("generated_at"),
                "outcomes_total": int(agg.get("outcomes_total", 0)),
                "pending": int(agg.get("pending", 0)),
                "resolved": int(agg.get("resolved", 0)),
                "expired": int(agg.get("expired", 0)),
                "fallback_total": fallback_total,
                "fallback_pending": int(agg.get("fallback_pending", 0)),
                "fallback_resolved": int(agg.get("fallback_resolved", 0)),
                "fallback_expired": int(agg.get("fallback_expired", 0)),
                "fallback_stale_pending": int(agg.get("fallback_stale_pending", 0)),
                "fallback_expired_rate": round((int(agg.get("fallback_expired", 0)) / fallback_total), 4)
                if fallback_total > 0
                else 0.0,
            }
        )

    recent_runs = sorted(recent_runs, key=lambda r: str(r.get("generated_at", "")), reverse=True)
    fallback_total_all = int(totals.get("fallback_total", 0))
    outcomes_total_all = int(totals.get("outcomes_total", 0))
    return {
        "rows_profile_read": len(profile_rows),
        "rows_outcome_read": len(outcome_rows),
        "runs_considered": len(run_meta),
        "runs_with_fallback": int(runs_with_fallback),
        "fallback_applied_runs": int(fallback_applied_runs),
        "totals": totals,
        "rates": {
            "outcome_expired_rate": round((int(totals.get("expired", 0)) / outcomes_total_all), 4)
            if outcomes_total_all > 0
            else 0.0,
            "fallback_expired_rate": round((int(totals.get("fallback_expired", 0)) / fallback_total_all), 4)
            if fallback_total_all > 0
            else 0.0,
            "fallback_closure_rate": round(
                ((int(totals.get("fallback_resolved", 0)) + int(totals.get("fallback_expired", 0))) / fallback_total_all),
                4,
            )
            if fallback_total_all > 0
            else 0.0,
        },
        "recent_runs": recent_runs,
    }


def _build_local_fallback_report(shared_dir: Path, limit_runs: int, market: str | None) -> Dict[str, Any]:
    market_filter = str(market or "").upper().strip()
    if not shared_dir.exists():
        return {
            "rows_profile_read": 0,
            "rows_outcome_read": 0,
            "runs_considered": 0,
            "runs_with_fallback": 0,
            "fallback_applied_runs": 0,
            "totals": {},
            "rates": {},
            "recent_runs": [],
        }

    run_dirs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
    run_dirs = sorted(run_dirs, key=lambda p: p.name, reverse=True)
    if limit_runs > 0:
        run_dirs = run_dirs[: int(limit_runs)]

    profile_rows: List[Dict[str, Any]] = []
    outcome_rows: List[Dict[str, Any]] = []
    for run_dir in run_dirs:
        profile_payload = _load_json(run_dir / "profile_diagnostics.json")
        if not profile_payload:
            continue
        run_market = str(profile_payload.get("market", "")).upper()
        if market_filter and run_market != market_filter:
            continue

        profile_rows.append(
            {
                "run_id": run_dir.name,
                "market": run_market,
                "current_profile": profile_payload.get("current_profile"),
                "fallback_watchlist": profile_payload.get("fallback_watchlist", {}),
                "generated_at": profile_payload.get("generated_at"),
            }
        )

        outcomes_payload = _load_json(run_dir / "realized_outcomes.json")
        outcomes = outcomes_payload.get("outcomes", []) if isinstance(outcomes_payload.get("outcomes"), list) else []
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            outcome_rows.append(
                {
                    "run_id": run_dir.name,
                    "ticker": row.get("ticker"),
                    "decision": row.get("decision"),
                    "status": row.get("status"),
                    "horizon": row.get("horizon"),
                    "recommended_at": row.get("recommended_at"),
                }
            )

    return build_report(profile_rows=profile_rows, outcome_rows=outcome_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report fallback watchlist outcome health from DB tables.")
    parser.add_argument("--limit-runs", type=int, default=100, help="Recent runs to inspect from profile diagnostics.")
    parser.add_argument("--market", type=str, default=None, help="Optional market filter (e.g., NASDAQ).")
    parser.add_argument(
        "--shared-dir",
        type=str,
        default="runtime_state/shared_working",
        help="Local fallback source when DB is unavailable.",
    )
    args = parser.parse_args()

    try:
        db, profile_rows = _read_profile_rows(limit_runs=int(args.limit_runs), market=args.market)
        run_ids = [str(r.get("run_id")) for r in profile_rows if isinstance(r, dict) and r.get("run_id")]
        outcome_rows = _read_outcome_rows(db=db, run_ids=run_ids)
        report = build_report(profile_rows=profile_rows, outcome_rows=outcome_rows)
        report["source"] = "supabase"
    except Exception as e:
        report = _build_local_fallback_report(
            shared_dir=Path(args.shared_dir),
            limit_runs=int(args.limit_runs),
            market=args.market,
        )
        report["source"] = "local_fallback"
        report["db_error"] = str(e)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
