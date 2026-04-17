#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scanner_services import (
    compute_kosdaq_continuation_signal,
    compute_kosdaq_quant_signal,
    compute_segment_score_overlay,
)

MODE_TO_METRIC = {
    "SWING": "return_3d_pct",
    "INTRADAY": "return_1d_pct",
}
TARGET_TOP5_ACCURACY_PCT = 75.0
TARGET_HIGH_CONVICTION_RETURN_PCT = 15.0


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


def _load_env() -> Tuple[str, str]:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.local")
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY")
    if not url or not key:
        raise SystemExit("Supabase credentials are required in .env.local or environment.")
    return str(url).rstrip("/"), str(key)


def _fetch_rows(
    *,
    base_url: str,
    api_key: str,
    market: str,
    scan_mode: str,
    metric_column: str,
    page_size: int,
    max_rows: int,
) -> List[Dict[str, Any]]:
    endpoint = f"{base_url}/rest/v1/market_scan_results"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Range-Unit": "items",
    }
    params = {
        "select": ",".join(
            [
                "run_id",
                "created_at",
                "base_trade_date",
                "market",
                "scan_mode",
                "ticker",
                "decision_score",
                "position",
                "strategy",
                "tier",
                "volume",
                "alpha_score",
                "ml_prob",
                "whale_score",
                "trend",
                "validation_excluded",
                metric_column,
            ]
        ),
        "market": f"eq.{market}",
        "scan_mode": f"eq.{scan_mode}",
        metric_column: "not.is.null",
        "order": "created_at.desc",
    }
    rows: List[Dict[str, Any]] = []
    start = 0
    while start < max_rows:
        headers["Range"] = f"{start}-{start + page_size - 1}"
        resp = requests.get(endpoint, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        batch = list(resp.json() or [])
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return rows


def _dedupe_latest(rows: Iterable[Dict[str, Any]], metric_column: str) -> List[Dict[str, Any]]:
    latest: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        run_id = str(row.get("run_id") or "").strip()
        ticker = str(row.get("ticker") or "").strip().upper()
        if not run_id or not ticker or row.get(metric_column) is None:
            continue
        key = (run_id, ticker)
        prev = latest.get(key)

        def _richness(candidate: Dict[str, Any]) -> Tuple[int, str]:
            strategy_text = str(candidate.get("strategy") or "")
            strategy_valid = int(bool(strategy_text) and not strategy_text.startswith("local_returns:") and not strategy_text.startswith("planner_handoff."))
            score = (
                strategy_valid
                + int(bool(candidate.get("position")))
                + int(bool(candidate.get("tier")))
                + int(bool(candidate.get("volume")))
                + int(_safe_float(candidate.get("alpha_score"), 0.0) > 0.0)
                + int(_safe_float(candidate.get("whale_score"), 0.0) > 0.0)
                + int(bool(candidate.get("trend")))
            )
            return score, str(candidate.get("created_at") or "")

        if prev is None or _richness(row) > _richness(prev):
            latest[key] = row
    return list(latest.values())


def _extract_ticker(row: Dict[str, Any]) -> str:
    return str(row.get("티커") or row.get("Ticker") or "").strip().upper()


def _extract_bridge_score(row: Dict[str, Any]) -> float:
    return round(_safe_float(row.get("Decision Score"), 0.0), 1)


def _extract_run_signature(scanner_payload: Dict[str, Any], topn: int) -> Tuple[Tuple[str, float], ...]:
    candidates = scanner_payload.get("candidates") or []
    ordered = list(candidates)[:topn]
    signature: List[Tuple[str, float]] = []
    for row in ordered:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        score = round(_safe_float(row.get("score"), 0.0), 1)
        if ticker:
            signature.append((ticker, score))
    return tuple(signature)


def _extract_bridge_signature(payload: Dict[str, Any], topn: int) -> Tuple[Tuple[str, float], ...]:
    rows = payload.get("results") or []
    signature: List[Tuple[str, float]] = []
    for row in list(rows)[:topn]:
        if not isinstance(row, dict):
            continue
        ticker = _extract_ticker(row)
        score = _extract_bridge_score(row)
        if ticker:
            signature.append((ticker, score))
    return tuple(signature)


def _extract_bridge_market(payload: Dict[str, Any]) -> str:
    meta = payload.get("meta") or {}
    market_gate = meta.get("market_gate") or {}
    selected = str(market_gate.get("selected_market") or market_gate.get("primary_label") or "").upper()
    if selected in {"KOSPI", "KOSDAQ", "NASDAQ", "AMEX"}:
        return selected
    return ""


def _extract_bridge_scan_mode(payload: Dict[str, Any]) -> str:
    meta = payload.get("meta") or {}
    summary = meta.get("summary") or {}
    return str(summary.get("scan_mode") or meta.get("scan_mode") or "SWING").upper()


def _parse_whale_score(row: Dict[str, Any]) -> float:
    raw = row.get("수급") or row.get("Whale") or ""
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw)
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not match:
        return 0.0
    return float(match.group(1))


def _build_bridge_index(bridge_root: Path, topn: int) -> Dict[Tuple[str, str, Tuple[Tuple[str, float], ...]], Dict[str, Any]]:
    index: Dict[Tuple[str, str, Tuple[Tuple[str, float], ...]], Dict[str, Any]] = {}
    for path in bridge_root.glob("BRIDGE-*/legacy_scan_results.json"):
        payload = _load_json(path)
        results = payload.get("results") or []
        if not isinstance(results, list) or not results:
            continue
        market = _extract_bridge_market(payload)
        scan_mode = _extract_bridge_scan_mode(payload)
        signature = _extract_bridge_signature(payload, topn=topn)
        if not market or not scan_mode or not signature:
            continue
        key = (market, scan_mode, signature)
        index.setdefault(key, {"path": str(path), "payload": payload})
    return index


def _extract_strategy_from_reasons(reasons: Any) -> str:
    for reason in list(reasons or []):
        text = str(reason or "").strip()
        if not text:
            continue
        if text.startswith("전략:"):
            return text.split("전략:", 1)[1].strip()
        if text.startswith("Strategy:"):
            return text.split("Strategy:", 1)[1].strip()
    return ""


def _derive_tier(decision_score: float) -> str:
    score = float(decision_score or 0.0)
    if score >= 85.0:
        return "🏆T1"
    if score >= 72.0:
        return "⭐T2"
    return "T3"


def _parse_whale_text(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "")
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not match:
        return 0.0
    return float(match.group(1))


def _shared_feature_row(candidate: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = candidate.get("feature_snapshot", {}) if isinstance(candidate.get("feature_snapshot"), dict) else {}
    decision_score = _safe_float(snapshot.get("decision_score", candidate.get("score")), 0.0)
    alpha_score = _safe_float(snapshot.get("alpha_score"), 0.0)
    if alpha_score <= 0.0:
        alpha_score = _safe_float(snapshot.get("antigrav"), 0.0)
    prob_5 = _safe_float(snapshot.get("prob_5", snapshot.get("ml_prob")), 0.0)
    prob_clean = _safe_float(snapshot.get("prob_clean"), prob_5)
    strategy = _extract_strategy_from_reasons(candidate.get("reasons") or [])
    return {
        "position": str(snapshot.get("position") or ""),
        "strategy": str(strategy or ""),
        "tier": str(snapshot.get("tier") or _derive_tier(decision_score)),
        "volume": str(snapshot.get("volume") or ""),
        "alpha_score": alpha_score,
        "prob_5": prob_5,
        "prob_clean": prob_clean,
        "whale_score": _parse_whale_text(snapshot.get("whale")),
        "real_trend": str(snapshot.get("real_trend") or snapshot.get("trend") or ""),
        "decision_score": decision_score,
        "routing_path": str(snapshot.get("routing_path") or candidate.get("routing_path") or ""),
        "expected_return_1d_pct": snapshot.get("expected_return_1d_pct"),
        "expected_return_3d_pct": snapshot.get("expected_return_3d_pct"),
        "theme_context": snapshot.get("theme_context") if isinstance(snapshot.get("theme_context"), dict) else candidate.get("theme_context", {}),
        "leader_metrics": snapshot.get("leader_metrics") if isinstance(snapshot.get("leader_metrics"), dict) else candidate.get("leader_metrics", {}),
        "kr_universe_role": str(snapshot.get("kr_universe_role") or ""),
        "scanner_timeframe_profile": str(snapshot.get("scanner_timeframe_profile") or ""),
        "feature_source": "shared_working",
    }


def _build_shared_candidate_index(shared_root: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
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


def _supabase_feature_row(row: Dict[str, Any]) -> Dict[str, Any]:
    decision_score = _safe_float(row.get("decision_score"), 0.0)
    strategy_text = str(row.get("strategy") or "")
    if strategy_text.startswith("local_returns:") or strategy_text.startswith("planner_handoff."):
        strategy_text = ""
    return {
        "position": str(row.get("position") or ""),
        "strategy": strategy_text,
        "tier": str(row.get("tier") or _derive_tier(decision_score)),
        "volume": str(row.get("volume") or ""),
        "alpha_score": _safe_float(row.get("alpha_score"), 0.0),
        "prob_5": _safe_float(row.get("ml_prob"), 0.0),
        "prob_clean": 0.0,
        "whale_score": _safe_float(row.get("whale_score"), 0.0),
        "real_trend": str(row.get("trend") or ""),
        "decision_score": decision_score,
        "routing_path": "",
        "expected_return_1d_pct": None,
        "expected_return_3d_pct": None,
        "theme_context": {},
        "leader_metrics": {},
        "kr_universe_role": "",
        "scanner_timeframe_profile": "",
        "feature_source": "supabase",
    }


def _feature_row_usable(feature_row: Dict[str, Any]) -> bool:
    return bool(
        str(feature_row.get("position") or "").strip()
        and str(feature_row.get("strategy") or "").strip()
        and str(feature_row.get("volume") or "").strip()
        and float(feature_row.get("alpha_score", 0.0) or 0.0) > 0.0
    )


def _classify_row_origin(row: Dict[str, Any]) -> str:
    strategy_text = str(row.get("strategy") or "").strip()
    if strategy_text.startswith("planner_handoff."):
        return "PLANNER"
    if strategy_text.startswith("local_returns:"):
        return "OUTCOME_ONLY"
    if strategy_text:
        return "SCANNER"
    if (
        str(row.get("position") or "").strip()
        or str(row.get("tier") or "").strip()
        or str(row.get("volume") or "").strip()
        or _safe_float(row.get("alpha_score"), 0.0) > 0.0
    ):
        return "SCANNER"
    return "UNKNOWN"


def _bridge_feature_row(bridge_row: Dict[str, Any]) -> Dict[str, Any]:
    decision_score = _extract_bridge_score(bridge_row)
    return {
        "position": str(bridge_row.get("위치") or bridge_row.get("Position") or ""),
        "strategy": str(bridge_row.get("전략") or bridge_row.get("Strategy") or ""),
        "tier": str(bridge_row.get("Tier") or _derive_tier(decision_score)),
        "volume": str(bridge_row.get("거래량") or bridge_row.get("Volume") or ""),
        "alpha_score": _safe_float(bridge_row.get("Antigrav"), 0.0),
        "prob_5": _safe_float(bridge_row.get("_prob_5"), 0.0),
        "prob_clean": _safe_float(bridge_row.get("_prob_clean"), 0.0),
        "whale_score": _parse_whale_score(bridge_row),
        "real_trend": str(bridge_row.get("추세") or bridge_row.get("Trend") or ""),
        "decision_score": decision_score,
        "feature_source": "bridge",
    }


def _metric_block(run_blocks: List[Dict[str, float]]) -> Dict[str, Any]:
    if not run_blocks:
        return {
            "runs": 0,
            "positive_rate_pct": 0.0,
            "avg_return_pct": 0.0,
            "hit5_rate_pct": 0.0,
            "hit10_rate_pct": 0.0,
            "accuracy_gap_to_target_pct": -TARGET_TOP5_ACCURACY_PCT,
            "return_gap_to_target_pct": -TARGET_HIGH_CONVICTION_RETURN_PCT,
        }
    return {
        "runs": len(run_blocks),
        "positive_rate_pct": round(sum(r["positive_rate"] for r in run_blocks) / len(run_blocks) * 100.0, 2),
        "avg_return_pct": round(sum(r["avg_return_pct"] for r in run_blocks) / len(run_blocks), 4),
        "hit5_rate_pct": round(sum(r["hit5_rate"] for r in run_blocks) / len(run_blocks) * 100.0, 2),
        "hit10_rate_pct": round(sum(r["hit10_rate"] for r in run_blocks) / len(run_blocks) * 100.0, 2),
        "accuracy_gap_to_target_pct": round(
            sum(r["positive_rate"] for r in run_blocks) / len(run_blocks) * 100.0 - TARGET_TOP5_ACCURACY_PCT,
            2,
        ),
        "return_gap_to_target_pct": round(
            sum(r["avg_return_pct"] for r in run_blocks) / len(run_blocks) - TARGET_HIGH_CONVICTION_RETURN_PCT,
            4,
        ),
    }


def _evaluate_run(rows: List[Dict[str, Any]], score_key: str, metric_column: str, topn: int) -> Dict[str, float]:
    ordered = sorted(rows, key=lambda row: (-_safe_float(row.get(score_key), 0.0), str(row.get("ticker") or "")))[:topn]
    metrics = [_safe_float(row.get(metric_column), 0.0) for row in ordered if row.get(metric_column) is not None]
    if not metrics:
        return {
            "positive_rate": 0.0,
            "avg_return_pct": 0.0,
            "hit5_rate": 0.0,
            "hit10_rate": 0.0,
        }
    return {
        "positive_rate": sum(v > 0 for v in metrics) / len(metrics),
        "avg_return_pct": sum(metrics) / len(metrics),
        "hit5_rate": sum(v >= 5.0 for v in metrics) / len(metrics),
        "hit10_rate": sum(v >= 10.0 for v in metrics) / len(metrics),
    }


def build_report(*, segments: List[str], topn: int, recent_days: int, page_size: int, max_rows: int) -> Dict[str, Any]:
    base_url, api_key = _load_env()
    bridge_index = _build_bridge_index(PROJECT_ROOT / "runtime_state/local_short_term/orchestrator_bridge", topn=topn)
    shared_index = _build_shared_candidate_index(PROJECT_ROOT / "runtime_state/shared_working")
    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "supabase.market_scan_results + shared_working/scanner_handoff + bridge_fallback",
        "topn": topn,
        "recent_days": recent_days,
        "targets": {
            "top5_accuracy_pct": TARGET_TOP5_ACCURACY_PCT,
            "high_conviction_avg_return_pct": TARGET_HIGH_CONVICTION_RETURN_PCT,
        },
        "segments": {},
    }

    for segment_key in segments:
        market, scan_mode = segment_key.split(":", 1)
        metric_column = MODE_TO_METRIC[str(scan_mode).upper()]
        fetched = _fetch_rows(
            base_url=base_url,
            api_key=api_key,
            market=market,
            scan_mode=scan_mode,
            metric_column=metric_column,
            page_size=page_size,
            max_rows=max_rows,
        )
        deduped = _dedupe_latest(fetched, metric_column)
        runs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        origin_counts: Counter[str] = Counter()
        scanner_rows = 0
        for row in deduped:
            if row.get("validation_excluded") is True:
                continue
            origin = _classify_row_origin(row)
            origin_counts[origin] += 1
            if origin != "SCANNER":
                continue
            scanner_rows += 1
            run_id = str(row.get("run_id") or "").strip()
            if run_id:
                runs[run_id].append(row)

        matched_runs = 0
        unmatched_runs: List[str] = []
        overlay_reason_counts: Counter[str] = Counter()
        continuation_reason_counts: Counter[str] = Counter()
        quant_reason_counts: Counter[str] = Counter()
        feature_source_counts: Counter[str] = Counter()
        run_metrics_all_base: List[Dict[str, float]] = []
        run_metrics_all_overlay: List[Dict[str, float]] = []
        run_metrics_recent_base: List[Dict[str, float]] = []
        run_metrics_recent_overlay: List[Dict[str, float]] = []
        dates_by_run: Dict[str, str] = {}
        rows_matched = 0

        for run_id, run_rows in runs.items():
            scanner_payload = _load_json(PROJECT_ROOT / "runtime_state/shared_working" / run_id / "scanner_handoff.json")
            bridge_map: Dict[str, Dict[str, Any]] = {}
            if scanner_payload:
                run_signature = _extract_run_signature(scanner_payload, topn=topn)
                bridge = bridge_index.get((market, scan_mode, run_signature))
                if bridge:
                    bridge_rows = bridge["payload"].get("results") or []
                    bridge_map = {_extract_ticker(row): row for row in bridge_rows if isinstance(row, dict) and _extract_ticker(row)}
            enriched_rows: List[Dict[str, Any]] = []
            for row in run_rows:
                ticker = str(row.get("ticker") or "").strip().upper()
                feature_row = shared_index.get((run_id, ticker))
                if not _feature_row_usable(feature_row or {}):
                    feature_row = _supabase_feature_row(row)
                if not _feature_row_usable(feature_row):
                    bridge_row = bridge_map.get(ticker)
                    if bridge_row:
                        feature_row = _bridge_feature_row(bridge_row)
                if not _feature_row_usable(feature_row or {}):
                    continue
                overlay = compute_segment_score_overlay(
                    market_type=market,
                    scan_mode=scan_mode,
                    position=str(feature_row.get("position") or ""),
                    strategy_tag=str(feature_row.get("strategy") or ""),
                    tier=str(feature_row.get("tier") or ""),
                    volume_badge=str(feature_row.get("volume") or ""),
                    whale_score=_safe_float(feature_row.get("whale_score"), 0.0),
                    alpha_score=_safe_float(feature_row.get("alpha_score"), 0.0),
                    prob_5=_safe_float(feature_row.get("prob_5"), 0.0),
                    prob_clean=_safe_float(feature_row.get("prob_clean"), 0.0),
                )
                decision_score = _safe_float(row.get("decision_score"), 0.0)
                for reason in overlay.get("reasons", []) or []:
                    overlay_reason_counts[str(reason)] += 1
                continuation = compute_kosdaq_continuation_signal(
                    market_type=market,
                    scan_mode=scan_mode,
                    decision_score=decision_score,
                    alpha_score=_safe_float(feature_row.get("alpha_score"), 0.0),
                    prob_5=_safe_float(feature_row.get("prob_5"), 0.0),
                    real_trend=str(feature_row.get("real_trend") or ""),
                )
                quant_signal = compute_kosdaq_quant_signal(
                    market_type=market,
                    scan_mode=scan_mode,
                    decision_score=decision_score,
                    alpha_score=_safe_float(feature_row.get("alpha_score"), 0.0),
                    whale_score=_safe_float(feature_row.get("whale_score"), 0.0),
                    prob_5=_safe_float(feature_row.get("prob_5"), 0.0),
                    prob_clean=_safe_float(feature_row.get("prob_clean"), 0.0),
                    real_trend=str(feature_row.get("real_trend") or ""),
                    position=str(feature_row.get("position") or ""),
                    strategy_tag=str(feature_row.get("strategy") or ""),
                    tier=str(feature_row.get("tier") or ""),
                    routing_path=str(feature_row.get("routing_path") or ""),
                    expected_return_1d_pct=feature_row.get("expected_return_1d_pct"),
                    expected_return_3d_pct=feature_row.get("expected_return_3d_pct"),
                    theme_context=feature_row.get("theme_context"),
                    leader_metrics=feature_row.get("leader_metrics"),
                    kr_universe_role=str(feature_row.get("kr_universe_role") or ""),
                    scanner_timeframe_profile=str(feature_row.get("scanner_timeframe_profile") or ""),
                )
                if continuation.get("enabled", False):
                    continuation_reason_counts["KOSDAQ_CONTINUATION_ENABLED"] += 1
                for reason in continuation.get("reasons", []) or []:
                    continuation_reason_counts[str(reason)] += 1
                for reason in quant_signal.get("reasons", []) or []:
                    quant_reason_counts[str(reason)] += 1
                feature_source_counts[str(feature_row.get("feature_source") or "unknown")] += 1
                enriched_rows.append(
                    {
                        **row,
                        "overlay_adjustment": _safe_float(overlay.get("adjustment"), 0.0),
                        "continuation_adjustment": _safe_float(continuation.get("score_adjustment"), 0.0),
                        "quant_adjustment": _safe_float(quant_signal.get("score_adjustment"), 0.0),
                        "overlay_score": round(
                            decision_score
                            + _safe_float(overlay.get("adjustment"), 0.0)
                            + _safe_float(continuation.get("score_adjustment"), 0.0)
                            + _safe_float(quant_signal.get("score_adjustment"), 0.0),
                            1,
                        ),
                    }
                )
            if not enriched_rows:
                unmatched_runs.append(run_id)
                continue
            matched_runs += 1
            rows_matched += len(enriched_rows)
            run_date = str((enriched_rows[0].get("base_trade_date") or enriched_rows[0].get("created_at") or ""))[:10]
            dates_by_run[run_id] = run_date
            base_block = _evaluate_run(enriched_rows, "decision_score", metric_column, topn)
            overlay_block = _evaluate_run(enriched_rows, "overlay_score", metric_column, topn)
            run_metrics_all_base.append(base_block)
            run_metrics_all_overlay.append(overlay_block)

        recent_dates = sorted({d for d in dates_by_run.values() if d})[-recent_days:] if recent_days > 0 else sorted({d for d in dates_by_run.values() if d})
        recent_date_set = set(recent_dates)
        for run_id, run_date in dates_by_run.items():
            if run_date not in recent_date_set:
                continue
            scanner_payload = _load_json(PROJECT_ROOT / "runtime_state/shared_working" / run_id / "scanner_handoff.json")
            bridge_map: Dict[str, Dict[str, Any]] = {}
            if scanner_payload:
                run_signature = _extract_run_signature(scanner_payload, topn=topn)
                bridge = bridge_index.get((market, scan_mode, run_signature))
                if bridge:
                    bridge_rows = bridge["payload"].get("results") or []
                    bridge_map = {_extract_ticker(row): row for row in bridge_rows if isinstance(row, dict) and _extract_ticker(row)}
            run_rows = runs.get(run_id, [])
            enriched_rows: List[Dict[str, Any]] = []
            for row in run_rows:
                ticker = str(row.get("ticker") or "").strip().upper()
                feature_row = shared_index.get((run_id, ticker))
                if not _feature_row_usable(feature_row or {}):
                    feature_row = _supabase_feature_row(row)
                if not _feature_row_usable(feature_row):
                    bridge_row = bridge_map.get(ticker)
                    if bridge_row:
                        feature_row = _bridge_feature_row(bridge_row)
                if not _feature_row_usable(feature_row or {}):
                    continue
                overlay = compute_segment_score_overlay(
                    market_type=market,
                    scan_mode=scan_mode,
                    position=str(feature_row.get("position") or ""),
                    strategy_tag=str(feature_row.get("strategy") or ""),
                    tier=str(feature_row.get("tier") or ""),
                    volume_badge=str(feature_row.get("volume") or ""),
                    whale_score=_safe_float(feature_row.get("whale_score"), 0.0),
                    alpha_score=_safe_float(feature_row.get("alpha_score"), 0.0),
                    prob_5=_safe_float(feature_row.get("prob_5"), 0.0),
                    prob_clean=_safe_float(feature_row.get("prob_clean"), 0.0),
                )
                continuation = compute_kosdaq_continuation_signal(
                    market_type=market,
                    scan_mode=scan_mode,
                    decision_score=_safe_float(row.get("decision_score"), 0.0),
                    alpha_score=_safe_float(feature_row.get("alpha_score"), 0.0),
                    prob_5=_safe_float(feature_row.get("prob_5"), 0.0),
                    real_trend=str(feature_row.get("real_trend") or ""),
                )
                quant_signal = compute_kosdaq_quant_signal(
                    market_type=market,
                    scan_mode=scan_mode,
                    decision_score=_safe_float(row.get("decision_score"), 0.0),
                    alpha_score=_safe_float(feature_row.get("alpha_score"), 0.0),
                    whale_score=_safe_float(feature_row.get("whale_score"), 0.0),
                    prob_5=_safe_float(feature_row.get("prob_5"), 0.0),
                    prob_clean=_safe_float(feature_row.get("prob_clean"), 0.0),
                    real_trend=str(feature_row.get("real_trend") or ""),
                    position=str(feature_row.get("position") or ""),
                    strategy_tag=str(feature_row.get("strategy") or ""),
                    tier=str(feature_row.get("tier") or ""),
                    routing_path=str(feature_row.get("routing_path") or ""),
                    expected_return_1d_pct=feature_row.get("expected_return_1d_pct"),
                    expected_return_3d_pct=feature_row.get("expected_return_3d_pct"),
                    theme_context=feature_row.get("theme_context"),
                    leader_metrics=feature_row.get("leader_metrics"),
                    kr_universe_role=str(feature_row.get("kr_universe_role") or ""),
                    scanner_timeframe_profile=str(feature_row.get("scanner_timeframe_profile") or ""),
                )
                decision_score = _safe_float(row.get("decision_score"), 0.0)
                enriched_rows.append(
                    {
                        **row,
                        "overlay_adjustment": _safe_float(overlay.get("adjustment"), 0.0),
                        "continuation_adjustment": _safe_float(continuation.get("score_adjustment"), 0.0),
                        "quant_adjustment": _safe_float(quant_signal.get("score_adjustment"), 0.0),
                        "overlay_score": round(
                            decision_score
                            + _safe_float(overlay.get("adjustment"), 0.0)
                            + _safe_float(continuation.get("score_adjustment"), 0.0)
                            + _safe_float(quant_signal.get("score_adjustment"), 0.0),
                            1,
                        ),
                    }
                )
            if not enriched_rows:
                continue
            run_metrics_recent_base.append(_evaluate_run(enriched_rows, "decision_score", metric_column, topn))
            run_metrics_recent_overlay.append(_evaluate_run(enriched_rows, "overlay_score", metric_column, topn))

        base_all = _metric_block(run_metrics_all_base)
        overlay_all = _metric_block(run_metrics_all_overlay)
        base_recent = _metric_block(run_metrics_recent_base)
        overlay_recent = _metric_block(run_metrics_recent_overlay)

        report["segments"][segment_key] = {
            "market": market,
            "scan_mode": scan_mode,
            "metric_column": metric_column,
            "supabase_rows": len(deduped),
            "scanner_origin_rows": scanner_rows,
            "matched_rows": rows_matched,
            "supabase_runs": len({str(row.get("run_id") or "").strip() for row in deduped if str(row.get("run_id") or "").strip()}),
            "scanner_origin_runs": len(runs),
            "matched_runs": matched_runs,
            "recent_scan_dates": recent_dates,
            "origin_counts": dict(origin_counts.most_common()),
            "all_history": {
                "baseline": base_all,
                "overlay": overlay_all,
                "delta": {
                    "positive_rate_pct": round(overlay_all["positive_rate_pct"] - base_all["positive_rate_pct"], 2),
                    "avg_return_pct": round(overlay_all["avg_return_pct"] - base_all["avg_return_pct"], 4),
                    "hit5_rate_pct": round(overlay_all["hit5_rate_pct"] - base_all["hit5_rate_pct"], 2),
                    "hit10_rate_pct": round(overlay_all["hit10_rate_pct"] - base_all["hit10_rate_pct"], 2),
                },
            },
            "recent_window": {
                "baseline": base_recent,
                "overlay": overlay_recent,
                "delta": {
                    "positive_rate_pct": round(overlay_recent["positive_rate_pct"] - base_recent["positive_rate_pct"], 2),
                    "avg_return_pct": round(overlay_recent["avg_return_pct"] - base_recent["avg_return_pct"], 4),
                    "hit5_rate_pct": round(overlay_recent["hit5_rate_pct"] - base_recent["hit5_rate_pct"], 2),
                    "hit10_rate_pct": round(overlay_recent["hit10_rate_pct"] - base_recent["hit10_rate_pct"], 2),
                },
            },
            "overlay_reason_counts": dict(overlay_reason_counts.most_common()),
            "continuation_reason_counts": dict(continuation_reason_counts.most_common()),
            "quant_reason_counts": dict(quant_reason_counts.most_common()),
            "feature_source_counts": dict(feature_source_counts.most_common()),
            "unmatched_runs": unmatched_runs[:20],
        }

    return report


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# Segment Overlay Proxy Validation (Top {report['topn']})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- source: {report['source']}",
        f"- recent_days: {report['recent_days']}",
        "",
    ]
    for segment_key, payload in sorted(report.get("segments", {}).items()):
        recent = payload.get("recent_window") or {}
        recent_base = recent.get("baseline") or {}
        recent_overlay = recent.get("overlay") or {}
        recent_delta = recent.get("delta") or {}
        all_history = payload.get("all_history") or {}
        all_base = all_history.get("baseline") or {}
        all_overlay = all_history.get("overlay") or {}
        lines.extend(
            [
                f"## {segment_key}",
                f"- supabase_rows: {payload.get('supabase_rows', 0)} | scanner_origin_rows: {payload.get('scanner_origin_rows', 0)} | matched_rows: {payload.get('matched_rows', 0)}",
                f"- supabase_runs: {payload.get('supabase_runs', 0)} | scanner_origin_runs: {payload.get('scanner_origin_runs', 0)} | matched_runs: {payload.get('matched_runs', 0)}",
                f"- recent dates: {payload.get('recent_scan_dates', [])}",
                f"- recent baseline positive-rate: {recent_base.get('positive_rate_pct', 0.0):.2f}% | avg return {recent_base.get('avg_return_pct', 0.0):+.2f}%",
                f"- recent overlay positive-rate: {recent_overlay.get('positive_rate_pct', 0.0):.2f}% | avg return {recent_overlay.get('avg_return_pct', 0.0):+.2f}%",
                f"- recent delta positive-rate: {recent_delta.get('positive_rate_pct', 0.0):+.2f}% | avg return {recent_delta.get('avg_return_pct', 0.0):+.2f}% | hit5 {recent_delta.get('hit5_rate_pct', 0.0):+.2f}%",
                f"- all-history baseline positive-rate: {all_base.get('positive_rate_pct', 0.0):.2f}% | avg return {all_base.get('avg_return_pct', 0.0):+.2f}%",
                f"- all-history overlay positive-rate: {all_overlay.get('positive_rate_pct', 0.0):.2f}% | avg return {all_overlay.get('avg_return_pct', 0.0):+.2f}%",
                f"- row origins: {payload.get('origin_counts', {})}",
                f"- overlay reasons: {payload.get('overlay_reason_counts', {})}",
                f"- continuation reasons: {payload.get('continuation_reason_counts', {})}",
                f"- quant reasons: {payload.get('quant_reason_counts', {})}",
                f"- feature sources: {payload.get('feature_source_counts', {})}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate segment-specific overlay using Supabase outcomes and local rich bridge artifacts.")
    parser.add_argument("--segments", default="KOSPI:INTRADAY,KOSDAQ:SWING")
    parser.add_argument("--topn", type=int, default=5)
    parser.add_argument("--recent-days", type=int, default=20)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-rows", type=int, default=10000)
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    args = parser.parse_args()

    segments = [part.strip().upper() for part in str(args.segments).split(",") if part.strip()]
    report = build_report(
        segments=segments,
        topn=int(args.topn),
        recent_days=int(args.recent_days),
        page_size=int(args.page_size),
        max_rows=int(args.max_rows),
    )
    output_dir = PROJECT_ROOT / str(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "segment_overlay_proxy_validation"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(build_markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "segments": segments}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
