#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager
from modules.scan_universe_admission import _extract_feature_columns as _extract_admission_feature_columns


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _parse_whale(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(float(value))
    match = re.search(r"(-?\d+(?:\.\d+)?)", str(value))
    if not match:
        return None
    return int(float(match.group(1)))


def _round_or_none(value: Any, ndigits: int = 1) -> float | None:
    try:
        if value is None or value == "":
            return None
        return round(float(value), ndigits)
    except Exception:
        return None


def _extract_strategy(reasons: Any) -> str:
    for reason in list(reasons or []):
        text = str(reason or "").strip()
        if text.startswith("전략:"):
            return text.split("전략:", 1)[1].strip()
        if text.startswith("Strategy:"):
            return text.split("Strategy:", 1)[1].strip()
    return ""


def _derive_tier(score: float) -> str:
    if score >= 85.0:
        return "🏆T1"
    if score >= 72.0:
        return "⭐T2"
    return "T3"


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.startswith("local_returns:") or value.startswith("planner_handoff.")
    return False


def _shared_feature_row(candidate: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = candidate.get("feature_snapshot", {}) if isinstance(candidate.get("feature_snapshot"), dict) else {}
    candidate_theme_context = candidate.get("theme_context", {}) if isinstance(candidate.get("theme_context"), dict) else {}
    theme_context = snapshot.get("theme_context", {}) if isinstance(snapshot.get("theme_context"), dict) else candidate_theme_context
    leader_metrics = candidate.get("leader_metrics", {}) if isinstance(candidate.get("leader_metrics"), dict) else {}
    if not leader_metrics and isinstance(snapshot.get("leader_metrics"), dict):
        leader_metrics = snapshot.get("leader_metrics", {})
    combined_row = dict(snapshot)
    combined_row.setdefault("ticker", candidate.get("ticker"))
    combined_row.setdefault("score", candidate.get("score"))
    combined_row.setdefault("decision_score", snapshot.get("decision_score") or candidate.get("score"))
    combined_row["feature_snapshot"] = snapshot
    if leader_metrics:
        combined_row["leader_metrics"] = leader_metrics
    if theme_context:
        combined_row["theme_context"] = theme_context
    features = _extract_admission_feature_columns(combined_row, market=str(snapshot.get("market") or ""))
    decision_score = _safe_float(features.get("decision_score"), _safe_float(snapshot.get("decision_score", candidate.get("score")), 0.0))
    alpha_score = _safe_int(features.get("alpha_score"), 0)
    tech_score = _safe_int(features.get("tech_score"), 0)
    whale_score = _parse_whale(features.get("whale_score"))
    if whale_score is None:
        whale_score = _parse_whale(snapshot.get("whale"))
    ml_prob = _round_or_none(features.get("ml_prob"), 1)
    prob_clean = _round_or_none(features.get("prob_clean"), 1)
    volume_ratio = _round_or_none(features.get("volume_ratio"), 3)
    foreigner_1d = _round_or_none(features.get("foreigner_1d"), 6)
    institution_1d = _round_or_none(features.get("institution_1d"), 6)
    retail_1d = _round_or_none(features.get("retail_1d"), 6)
    has_flow = any(value is not None for value in (foreigner_1d, institution_1d, retail_1d))
    return {
        "stock_name": snapshot.get("stock_name"),
        "alpha_score": alpha_score or None,
        "tech_score": tech_score or alpha_score or None,
        "ml_prob": ml_prob,
        "prob_clean": prob_clean,
        "whale_score": whale_score,
        "foreigner": foreigner_1d,
        "foreign_flow": foreigner_1d,
        "institution": institution_1d,
        "institution_flow": institution_1d,
        "retail": retail_1d,
        "retail_flow": retail_1d,
        "foreigner_1d": foreigner_1d,
        "institution_1d": institution_1d,
        "retail_1d": retail_1d,
        "foreigner_3d": _round_or_none(features.get("foreigner_3d"), 6),
        "institution_3d": _round_or_none(features.get("institution_3d"), 6),
        "retail_3d": _round_or_none(features.get("retail_3d"), 6),
        "foreigner_10d": _round_or_none(features.get("foreigner_10d"), 6),
        "institution_10d": _round_or_none(features.get("institution_10d"), 6),
        "retail_10d": _round_or_none(features.get("retail_10d"), 6),
        "whale_flow_1d": _round_or_none(features.get("whale_flow_1d"), 6),
        "whale_flow_3d": _round_or_none(features.get("whale_flow_3d"), 6),
        "whale_flow_10d": _round_or_none(features.get("whale_flow_10d"), 6),
        "flow_window": snapshot.get("flow_window") or ("1d/3d/10d" if has_flow else None),
        "flow_asof": snapshot.get("flow_asof") or (snapshot.get("base_trade_date") if has_flow else None),
        "flow_consensus_buying": features.get("flow_consensus_buying"),
        "retail_dominant": features.get("retail_dominant"),
        "dominant": features.get("dominant"),
        "whale_trend": features.get("whale_trend"),
        "trend": snapshot.get("real_trend") or snapshot.get("trend"),
        "position": snapshot.get("position"),
        "strategy": _extract_strategy(candidate.get("reasons") or []),
        "tier": snapshot.get("tier") or _derive_tier(decision_score),
        "volume": snapshot.get("volume"),
        "volume_ratio": volume_ratio,
        "day_return_pct": _round_or_none(features.get("day_return_pct"), 3),
        "surge": snapshot.get("surge"),
        "decision_score": round(decision_score, 1),
        "strategy_family": snapshot.get("strategy_family"),
        "entry_reference_price": features.get("entry_reference_price") or snapshot.get("entry_reference_price"),
        "phase25_variant": snapshot.get("phase25_variant"),
        "phase25_shadow_variant": snapshot.get("phase25_shadow_variant"),
        "phase25_shadow_prob": snapshot.get("phase25_shadow_prob"),
        "phase25_recommended_threshold": snapshot.get("phase25_recommended_threshold"),
        "expected_edge_score": snapshot.get("expected_edge_score"),
        "expected_return_1d_pct": snapshot.get("expected_return_1d_pct"),
        "expected_return_3d_pct": snapshot.get("expected_return_3d_pct"),
        "scanner_timeframe_profile": snapshot.get("scanner_timeframe_profile"),
        "kr_universe_role": snapshot.get("kr_universe_role"),
        "explosive_leader_flag": snapshot.get("explosive_leader_flag"),
        "core_trend_flag": snapshot.get("core_trend_flag"),
        "primary_theme": features.get("primary_theme") or theme_context.get("primary_theme"),
        "theme_source": features.get("theme_source") or theme_context.get("theme_source"),
        "theme_inference_status": features.get("theme_inference_status") or theme_context.get("theme_inference_status"),
        "secondary_themes": theme_context.get("secondary_themes"),
        "theme_routing_path": snapshot.get("routing_path") or theme_context.get("routing_path"),
    }


def _build_shared_index(shared_root: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for path in shared_root.glob("RUN-*/scanner_handoff.json"):
        payload = _load_json(path)
        run_id = path.parent.name
        for candidate in list(payload.get("candidates") or []):
            if not isinstance(candidate, dict):
                continue
            ticker = str(candidate.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            index[(run_id, ticker)] = _shared_feature_row(candidate)
    return index


def _iter_market_rows(db: DBManager, market: str, scan_mode: str, page_size: int, max_rows: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    start = 0
    while start < max_rows:
        query = (
            db.client.table("market_scan_results")
            .select("*")
            .eq("market", market)
            .eq("scan_mode", scan_mode)
            .order("created_at", desc=True)
            .range(start, start + page_size - 1)
        )
        response = query.execute()
        batch = list(response.data or [])
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return rows


def _write_updates(db: DBManager, updates: List[Dict[str, Any]], *, batch_size: int) -> int:
    if not updates:
        return 0
    written = 0
    total = len(updates)
    progress_every = max(1, int(batch_size))
    for update in updates:
        row_id = update.get("id")
        if row_id is None:
            continue
        payload = {key: value for key, value in update.items() if key != "id"}
        payload = db._filter_payload_to_existing_columns("market_scan_results", payload)
        if not payload:
            continue
        db.client.table("market_scan_results").update(payload).eq("id", row_id).execute()
        written += 1
        if written % progress_every == 0 or written == total:
            print(
                f"[INFO] updated market_scan_results feature rows {written}/{total}",
                flush=True,
            )
    return written


def run_backfill(*, market: str, scan_mode: str, dry_run: bool, page_size: int, max_rows: int, batch_size: int) -> Dict[str, Any]:
    db = DBManager()
    if not db.client:
        raise RuntimeError("Supabase client unavailable. Check SUPABASE_URL / SUPABASE_KEY.")

    shared_index = _build_shared_index(PROJECT_ROOT / "runtime_state/shared_working")
    rows = _iter_market_rows(db=db, market=market, scan_mode=scan_mode, page_size=page_size, max_rows=max_rows)
    stats = {
        "market": market,
        "scan_mode": scan_mode,
        "rows_read": len(rows),
        "shared_candidates_indexed": len(shared_index),
        "rows_matched": 0,
        "rows_updated": 0,
        "fields_updated": 0,
        "write_method": "dry_run" if dry_run else "row_update_by_id",
        "unmatched_examples": [],
    }
    updates: List[Dict[str, Any]] = []

    for row in rows:
        run_id = str(row.get("run_id") or "").strip()
        ticker = str(row.get("ticker") or "").strip().upper()
        if not run_id or not ticker:
            continue
        shared = shared_index.get((run_id, ticker))
        if not shared:
            if len(stats["unmatched_examples"]) < 20:
                stats["unmatched_examples"].append({"run_id": run_id, "ticker": ticker})
            continue
        stats["rows_matched"] += 1
        payload: Dict[str, Any] = {}
        for key, value in shared.items():
            if value is None:
                continue
            current = row.get(key)
            if _is_missing(current):
                payload[key] = value
        if not payload:
            continue
        payload = db._filter_payload_to_existing_columns("market_scan_results", payload)
        if not payload:
            continue
        stats["fields_updated"] += len(payload)
        if not dry_run:
            updates.append({"id": row["id"], **payload})
        stats["rows_updated"] += 1

    if updates:
        stats["rows_written"] = _write_updates(db, updates, batch_size=batch_size)
    else:
        stats["rows_written"] = 0

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill market_scan_results feature columns from shared_working scanner_handoff.")
    parser.add_argument("--market", default="KOSDAQ")
    parser.add_argument("--scan-mode", default="SWING")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-rows", type=int, default=10000)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    result = run_backfill(
        market=str(args.market).upper(),
        scan_mode=str(args.scan_mode).upper(),
        dry_run=bool(args.dry_run),
        page_size=int(args.page_size),
        max_rows=int(args.max_rows),
        batch_size=int(args.batch_size),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
