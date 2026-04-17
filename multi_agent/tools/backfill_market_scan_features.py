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
    theme_context = snapshot.get("theme_context", {}) if isinstance(snapshot.get("theme_context"), dict) else {}
    decision_score = _safe_float(snapshot.get("decision_score", candidate.get("score")), 0.0)
    alpha_score = _safe_int(snapshot.get("alpha_score"), 0)
    if alpha_score <= 0:
        alpha_score = _safe_int(snapshot.get("antigrav"), 0)
    return {
        "stock_name": snapshot.get("stock_name"),
        "alpha_score": alpha_score or None,
        "tech_score": alpha_score or None,
        "ml_prob": round(_safe_float(snapshot.get("prob_5", snapshot.get("ml_prob")), 0.0), 1),
        "whale_score": _parse_whale(snapshot.get("whale")),
        "trend": snapshot.get("real_trend") or snapshot.get("trend"),
        "position": snapshot.get("position"),
        "strategy": _extract_strategy(candidate.get("reasons") or []),
        "tier": snapshot.get("tier") or _derive_tier(decision_score),
        "volume": snapshot.get("volume"),
        "surge": snapshot.get("surge"),
        "decision_score": round(decision_score, 1),
        "strategy_family": snapshot.get("strategy_family"),
        "entry_reference_price": snapshot.get("entry_reference_price"),
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
        "primary_theme": theme_context.get("primary_theme"),
        "theme_source": theme_context.get("theme_source"),
        "theme_inference_status": theme_context.get("theme_inference_status"),
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


def run_backfill(*, market: str, scan_mode: str, dry_run: bool, page_size: int, max_rows: int) -> Dict[str, Any]:
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
        "unmatched_examples": [],
    }

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
            db.client.table("market_scan_results").update(payload).eq("id", row["id"]).execute()
        stats["rows_updated"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill market_scan_results feature columns from shared_working scanner_handoff.")
    parser.add_argument("--market", default="KOSDAQ")
    parser.add_argument("--scan-mode", default="SWING")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-rows", type=int, default=10000)
    args = parser.parse_args()

    result = run_backfill(
        market=str(args.market).upper(),
        scan_mode=str(args.scan_mode).upper(),
        dry_run=bool(args.dry_run),
        page_size=int(args.page_size),
        max_rows=int(args.max_rows),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
