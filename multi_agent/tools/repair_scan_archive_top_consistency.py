#!/usr/bin/env python3
"""Repair Supabase scan archive rows from scan-time local artifacts.

This is intentionally narrow: it only inserts planner top-N rows that are
missing from market_scan_results for the same run_id. It does not delete or
rewrite unrelated historical rows.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager
from modules.db_schema import DEFAULT_FALLBACK_KEYS, build_scan_result_payload
from multi_agent.tools.verify_scan_archive_top_consistency import (
    _db_rows_for_run,
    _load_planner,
    _planner_top,
)


PLANNER_OVERLAY_KEYS = (
    "decision",
    "decision_bucket",
    "outcome_status",
    "horizon",
    "strategy_family",
    "conviction_score",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "loss_risk_score",
    "relative_rank_score",
    "relative_rank_pct",
    "regime_adjusted_grade",
    "relative_rank_model",
    "market_gate",
    "scanner_timeframe_profile",
    "kr_universe_role",
    "selection_lane",
    "rationale",
    "theme_risk",
    "primary_theme",
    "theme_source",
    "theme_inference_status",
    "secondary_themes",
    "theme_routing_path",
    "target_tp_pct",
    "stop_sl_pct",
    "hold_days",
)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _first_present(*values: Any) -> Any:
    for value in values:
        if _present(value):
            return value
    return None


def _candidate_index(scanner_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for row in scanner_payload.get("candidates") or []:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip()
        if ticker:
            result[ticker] = row
    return result


def _planner_meta_index(planner_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for section in ("decisions", "watchlist_meta"):
        for row in planner_payload.get(section) or []:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").strip()
            if ticker and ticker not in result:
                result[ticker] = row
    return result


def _snapshot(candidate: Dict[str, Any]) -> Dict[str, Any]:
    value = candidate.get("feature_snapshot")
    return value if isinstance(value, dict) else {}


def _theme_context(snapshot: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    for value in (meta.get("theme_context"), snapshot.get("theme_context")):
        if isinstance(value, dict):
            return value
    return {}


def _build_repair_payload(
    *,
    run_id: str,
    rank: int,
    ticker: str,
    planner_payload: Dict[str, Any],
    scanner_payload: Dict[str, Any],
    candidate: Dict[str, Any],
    meta: Dict[str, Any],
    default_scan_mode: str,
) -> Dict[str, Any]:
    ctx = planner_payload.get("run_context") or {}
    summary = scanner_payload.get("summary") if isinstance(scanner_payload.get("summary"), dict) else {}
    snap = _snapshot(candidate)
    theme = _theme_context(snap, meta)
    market = str(_first_present(ctx.get("market"), summary.get("market"), meta.get("market")) or "").upper()
    scan_mode = str(
        _first_present(ctx.get("scan_mode"), summary.get("scan_mode"), meta.get("scan_mode"), default_scan_mode)
        or "SWING"
    ).upper()
    decision = str(_first_present(meta.get("decision"), "WATCHLIST_ONLY"))
    bucket = str(_first_present(meta.get("decision_bucket"), "watchlist")).lower()
    recommended_at = _first_present(ctx.get("created_at"), scanner_payload.get("produced_at"), meta.get("generated_at"))
    stock_name = _first_present(
        meta.get("stock_name"),
        snap.get("stock_name"),
        candidate.get("stock_name"),
        candidate.get("name"),
        ticker,
    )
    return {
        "ticker": ticker,
        "name": stock_name,
        "market": market,
        "market_type": _first_present(meta.get("market_type"), snap.get("market_type"), "KR"),
        "scan_mode": scan_mode,
        "run_id": run_id,
        "priority_rank": int(rank),
        "decision": decision,
        "decision_bucket": bucket,
        "outcome_status": _first_present(meta.get("outcome_status"), "PENDING"),
        "recommended_at": recommended_at,
        "horizon": _first_present(meta.get("horizon"), f"T+{int(meta.get('horizon_days') or 3)}D"),
        "source_ref": _first_present(meta.get("source_ref"), f"repair_scan_archive_top_consistency#{ticker}"),
        "feature_origin": "scanner_full",
        "alpha_score": _first_present(meta.get("alpha_score"), snap.get("alpha_score"), snap.get("antigrav")),
        "tech_score": _first_present(meta.get("tech_score"), snap.get("tech_score"), snap.get("alpha_score"), snap.get("antigrav")),
        "ml_prob": _first_present(meta.get("ml_prob"), meta.get("prob_5"), snap.get("ml_prob"), snap.get("prob_5")),
        "prob_clean": _first_present(meta.get("prob_clean"), snap.get("prob_clean")),
        "whale_score": _first_present(meta.get("whale_score"), snap.get("whale_score"), snap.get("whale")),
        "decision_score": _first_present(
            meta.get("decision_score"),
            meta.get("exception_score"),
            meta.get("conviction_score"),
            snap.get("decision_score"),
            candidate.get("score"),
        ),
        "conviction_score": _first_present(meta.get("conviction_score"), snap.get("conviction_score")),
        "trend": _first_present(meta.get("real_trend"), meta.get("trend"), snap.get("real_trend"), snap.get("trend")),
        "tier": _first_present(meta.get("tier"), snap.get("tier")),
        "volume": _first_present(meta.get("volume"), snap.get("volume")),
        "volume_ratio": _first_present(meta.get("volume_ratio"), snap.get("volume_ratio")),
        "volume_confirmed": _first_present(meta.get("volume_confirmed"), snap.get("volume_confirmed")),
        "position": _first_present(meta.get("position"), snap.get("position")),
        "strategy_family": _first_present(meta.get("strategy_family"), snap.get("strategy_family")),
        "entry_reference_price": _first_present(meta.get("entry_reference_price"), snap.get("entry_reference_price")),
        "phase25_variant": _first_present(meta.get("phase25_variant"), snap.get("phase25_variant")),
        "phase25_prob": _first_present(meta.get("phase25_prob"), snap.get("phase25_prob")),
        "phase25_shadow_variant": _first_present(meta.get("phase25_shadow_variant"), snap.get("phase25_shadow_variant")),
        "phase25_shadow_prob": _first_present(meta.get("phase25_shadow_prob"), snap.get("phase25_shadow_prob")),
        "phase25_recommended_threshold": _first_present(meta.get("phase25_recommended_threshold"), snap.get("phase25_recommended_threshold")),
        "phase25_signal_direction": _first_present(meta.get("phase25_signal_direction"), snap.get("phase25_signal_direction")),
        "phase25_raw_auc": _first_present(meta.get("phase25_raw_auc"), snap.get("phase25_raw_auc")),
        "phase25_oos_auc": _first_present(meta.get("phase25_oos_auc"), snap.get("phase25_oos_auc")),
        "expected_edge_score": _first_present(meta.get("expected_edge_score"), snap.get("expected_edge_score")),
        "expected_return_1d_pct": _first_present(meta.get("expected_return_1d_pct"), snap.get("expected_return_1d_pct")),
        "expected_return_3d_pct": _first_present(meta.get("expected_return_3d_pct"), snap.get("expected_return_3d_pct")),
        "loss_risk_score": _first_present(meta.get("loss_risk_score"), snap.get("loss_risk_score")),
        "relative_rank_score": _first_present(meta.get("relative_rank_score"), snap.get("relative_rank_score")),
        "relative_rank_pct": _first_present(meta.get("relative_rank_pct"), snap.get("relative_rank_pct")),
        "regime_adjusted_grade": _first_present(meta.get("regime_adjusted_grade"), snap.get("regime_adjusted_grade")),
        "relative_rank_model": _first_present(meta.get("relative_rank_model"), snap.get("relative_rank_model")),
        "market_gate": _first_present(meta.get("market_gate"), snap.get("market_gate")),
        "scanner_timeframe_profile": _first_present(meta.get("scanner_timeframe_profile"), snap.get("scanner_timeframe_profile")),
        "kr_universe_role": _first_present(meta.get("kr_universe_role"), snap.get("kr_universe_role")),
        "selection_lane": _first_present(meta.get("selection_lane"), snap.get("selection_lane")),
        "rationale": _first_present(meta.get("rationale"), candidate.get("reasons")),
        "theme_risk": _first_present(meta.get("theme_risk"), snap.get("theme_risk")),
        "primary_theme": _first_present(meta.get("primary_theme"), theme.get("primary_theme")),
        "theme_source": _first_present(meta.get("theme_source"), theme.get("theme_source")),
        "theme_inference_status": _first_present(meta.get("theme_inference_status"), theme.get("theme_inference_status")),
        "secondary_themes": _first_present(meta.get("secondary_themes"), theme.get("secondary_themes")),
        "theme_routing_path": _first_present(meta.get("theme_routing_path"), snap.get("routing_path"), theme.get("routing_path")),
    }


def _same_day_peer(
    db: DBManager,
    *,
    run_id: str,
    ticker: str,
    market: str,
    scan_mode: str,
    recommended_at: str,
) -> Optional[Dict[str, Any]]:
    rec_date = str(recommended_at or "")[:10]
    if not (rec_date and ticker and market and scan_mode):
        return None
    rows = (
        db.client.table("market_scan_results")
        .select("*")
        .eq("ticker", ticker)
        .eq("market", market)
        .eq("scan_mode", scan_mode)
        .gte("recommended_at", f"{rec_date}T00:00:00")
        .lte("recommended_at", f"{rec_date}T23:59:59.999")
        .neq("run_id", run_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )
    return db._choose_authoritative_scan_row(rows)


def _insert_payload(db: DBManager, payload: Dict[str, Any]) -> bool:
    filtered = db._filter_payload_to_existing_columns("market_scan_results", dict(payload))
    if not filtered:
        return False
    try:
        db.client.table("market_scan_results").insert(filtered).execute()
    except Exception as exc:
        if "23505" not in str(exc) and "duplicate key" not in str(exc):
            raise
        existing = db._find_scan_result_conflict_row(filtered)
        if not existing:
            raise
        merged = db._merge_non_empty_payload(dict(existing), filtered)
        merged = db._filter_payload_to_existing_columns("market_scan_results", merged)
        db.client.table("market_scan_results").update(merged).eq("id", existing["id"]).execute()
    return True


def _local_artifact_insert_payload(db: DBManager, payload: Dict[str, Any]) -> Dict[str, Any]:
    now_ts = datetime.now(timezone.utc).isoformat()
    origin = "scanner_partial_legacy"
    data = dict(payload)
    data["feature_origin"] = origin
    quality = db._feature_quality_payload(data, origin=origin)
    overrides = {
        "market": data.get("market"),
        "created_at": now_ts,
        "recommended_at": data.get("recommended_at") or now_ts,
        **quality,
    }
    return build_scan_result_payload(data, overrides=overrides, fallback_keys=DEFAULT_FALLBACK_KEYS)


def _clone_peer_payload(
    *,
    peer: Dict[str, Any],
    repair_payload: Dict[str, Any],
    rank: int,
    run_id: str,
    ticker: str,
) -> Dict[str, Any]:
    payload = dict(peer or {})
    payload.pop("id", None)
    payload.pop("updated_at", None)
    payload["run_id"] = run_id
    payload["ticker"] = ticker
    payload["priority_rank"] = int(rank)
    payload["recommended_at"] = repair_payload.get("recommended_at") or payload.get("recommended_at")
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    payload["source_ref"] = f"repair_scan_archive_top_consistency:clone#{peer.get('run_id')}#{ticker}"
    for key in PLANNER_OVERLAY_KEYS:
        if _present(repair_payload.get(key)):
            payload[key] = repair_payload.get(key)
    return payload


def repair(
    *,
    shared_dir: Path,
    top_n: int,
    limit_runs: int,
    bucket: str,
    dry_run: bool,
    default_scan_mode: str,
) -> Dict[str, Any]:
    db = DBManager()
    if not db.client:
        raise RuntimeError("Supabase client unavailable.")
    run_dirs = sorted(
        [d for d in shared_dir.iterdir() if d.is_dir() and d.name.startswith("RUN-")],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )[:limit_runs]
    stats: Dict[str, Any] = {
        "runs_scanned": len(run_dirs),
        "missing_rows_seen": 0,
        "rows_inserted": 0,
        "dry_run": bool(dry_run),
        "unrepairable": [],
        "inserted_examples": [],
    }
    for run_dir in run_dirs:
        planner = _load_planner(run_dir)
        if not planner:
            continue
        scanner = _load_json(run_dir / "scanner_handoff.json")
        run_id = str((planner.get("run_context") or {}).get("run_id") or run_dir.name)
        planner_top = _planner_top(planner, top_n, bucket=bucket)
        if not planner_top:
            continue
        db_rows = _db_rows_for_run(db, run_id, bucket=bucket)
        db_by_rank: Dict[int, str] = {
            int(row.get("priority_rank") or 0): str(row.get("ticker") or "")
            for row in db_rows
            if row.get("priority_rank")
        }
        candidates = _candidate_index(scanner)
        meta_by_ticker = _planner_meta_index(planner)
        for rank, ticker in planner_top:
            if db_by_rank.get(int(rank)) == ticker:
                continue
            stats["missing_rows_seen"] += 1
            candidate = candidates.get(ticker) or {}
            meta = meta_by_ticker.get(ticker) or {"ticker": ticker, "priority_rank": rank}
            if not candidate and not meta:
                stats["unrepairable"].append({"run_id": run_id, "rank": rank, "ticker": ticker, "reason": "no_local_artifact"})
                continue
            payload = _build_repair_payload(
                run_id=run_id,
                rank=int(rank),
                ticker=ticker,
                planner_payload=planner,
                scanner_payload=scanner,
                candidate=candidate,
                meta=meta,
                default_scan_mode=default_scan_mode,
            )
            peer = _same_day_peer(
                db,
                run_id=run_id,
                ticker=ticker,
                market=str(payload.get("market") or ""),
                scan_mode=str(payload.get("scan_mode") or ""),
                recommended_at=str(payload.get("recommended_at") or ""),
            )
            write_payload = _clone_peer_payload(
                peer=peer,
                repair_payload=payload,
                rank=int(rank),
                run_id=run_id,
                ticker=ticker,
            ) if peer else payload
            source = "db_peer_clone" if peer else "local_artifact"
            if not dry_run:
                if peer:
                    ok = _insert_payload(db, write_payload)
                else:
                    ok = _insert_payload(db, _local_artifact_insert_payload(db, write_payload))
                if not ok:
                    stats["unrepairable"].append({"run_id": run_id, "rank": rank, "ticker": ticker, "reason": "insert_failed"})
                    continue
            stats["rows_inserted"] += 1
            if len(stats["inserted_examples"]) < 20:
                stats["inserted_examples"].append({"run_id": run_id, "rank": rank, "ticker": ticker, "source": source})
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--limit-runs", type=int, default=10)
    parser.add_argument("--bucket", default="watchlist_field")
    parser.add_argument("--scan-mode", default="SWING")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = repair(
        shared_dir=Path(args.shared_dir),
        top_n=int(args.top_n),
        limit_runs=int(args.limit_runs),
        bucket=str(args.bucket),
        dry_run=bool(args.dry_run),
        default_scan_mode=str(args.scan_mode).upper(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result.get("unrepairable") else 1


if __name__ == "__main__":
    raise SystemExit(main())
