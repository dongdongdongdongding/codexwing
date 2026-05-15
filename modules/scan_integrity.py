from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from multi_agent.contracts.serialization import write_json


COMMON_FIELD_ALIASES: Dict[str, Tuple[str, ...]] = {
    "ticker": ("ticker", "Ticker", "symbol", "Symbol", "티커"),
    "stock_name": ("stock_name", "name", "Name", "종목명", "Stock Name"),
    "market": ("market",),
    "market_type": ("market_type",),
    "scan_mode": ("scan_mode",),
    "priority_rank": ("priority_rank", "rank", "Rank"),
    "decision": ("decision", "Decision", "signal_label"),
    "decision_bucket": ("decision_bucket",),
    "decision_score": ("decision_score", "Decision Score", "buy_score", "Score"),
    "alpha_score": ("alpha_score", "Antigrav", "Alpha"),
    "tech_score": ("tech_score", "Tech", "technical_score"),
    "ml_prob": ("ml_prob", "prob_5", "AI Prob", "probability"),
    "prob_clean": ("prob_clean",),
    "whale_score": ("whale_score", "Whale", "세력점수"),
    "foreigner": ("foreigner",),
    "foreign_flow": ("foreign_flow",),
    "institution": ("institution",),
    "institution_flow": ("institution_flow",),
    "retail": ("retail",),
    "retail_flow": ("retail_flow",),
    "flow_consensus_buying": ("flow_consensus_buying",),
    "retail_dominant": ("retail_dominant",),
    "dominant": ("dominant",),
    "whale_trend": ("whale_trend",),
    "volume": ("volume", "Volume", "거래량"),
    "volume_ratio": ("volume_ratio", "Volume Ratio", "거래량비율"),
    "day_return_pct": ("day_return_pct", "day_change_pct", "Change %", "전일비"),
    "trend": ("trend", "initial_trend", "real_trend"),
    "position": ("position",),
    "tier": ("tier",),
    "entry_reference_price": ("entry_reference_price", "Entry Price", "Entry(-2%)", "매수가(-2%)"),
    "target_tp_pct": ("target_tp_pct",),
    "stop_sl_pct": ("stop_sl_pct",),
    "hold_days": ("hold_days",),
    "selection_lane": ("selection_lane",),
    "target_horizon_days": ("target_horizon_days",),
    "scanner_timeframe_profile": ("scanner_timeframe_profile",),
    "kr_universe_role": ("kr_universe_role",),
    "market_gate": ("market_gate",),
    "expected_edge_score": ("expected_edge_score",),
    "expected_return_1d_pct": ("expected_return_1d_pct",),
    "expected_return_3d_pct": ("expected_return_3d_pct",),
    "loss_risk_score": ("loss_risk_score",),
    "relative_rank_score": ("relative_rank_score",),
    "relative_rank_pct": ("relative_rank_pct",),
    "relative_rank_model": ("relative_rank_model",),
    "regime_adjusted_grade": ("regime_adjusted_grade",),
    "phase25_variant": ("phase25_variant",),
    "phase25_prob": ("phase25_prob",),
    "phase25_signal_direction": ("phase25_signal_direction",),
    "phase25_shadow_variant": ("phase25_shadow_variant",),
    "phase25_shadow_prob": ("phase25_shadow_prob",),
    "phase25_recommended_threshold": ("phase25_recommended_threshold",),
    "phase25_degraded": ("phase25_degraded",),
    "model_trace_status": ("model_trace_status",),
    "model_error": ("model_error",),
    "primary_theme": ("primary_theme",),
    "theme_source": ("theme_source",),
    "theme_inference_status": ("theme_inference_status",),
    "secondary_themes": ("secondary_themes",),
    "theme_routing_path": ("theme_routing_path", "routing_path"),
    "theme_score_adjustment": ("theme_score_adjustment",),
    "rationale": ("rationale",),
    "theme_risk": ("theme_risk",),
    "source_ref": ("source_ref",),
    "feature_origin": ("feature_origin",),
}

CORE_REQUIRED_FIELDS = (
    "ticker",
    "stock_name",
    "decision_score",
    "alpha_score",
    "tech_score",
    "ml_prob",
    "whale_score",
    "volume_ratio",
    "day_return_pct",
    "trend",
    "entry_reference_price",
)

KR_REQUIRED_FIELDS = CORE_REQUIRED_FIELDS + (
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "loss_risk_score",
    "selection_lane",
    "primary_theme",
    "theme_routing_path",
    "foreigner",
    "institution",
    "retail",
)

US_REQUIRED_FIELDS = CORE_REQUIRED_FIELDS + (
    "phase25_variant",
    "phase25_prob",
    "phase25_signal_direction",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "?", "nan", "none", "null", "unknown", "na", "n/a"}
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def _first_present(*rows_and_keys: Tuple[Dict[str, Any], Iterable[str]]) -> Any:
    for row, keys in rows_and_keys:
        if not isinstance(row, dict):
            continue
        for key in keys:
            value = row.get(key)
            if not _is_missing(value):
                return value
    return None


def _safe_float(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").replace("pts", "").replace("점", "").strip()
        if value in (None, ""):
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        f = _safe_float(value)
        return int(f) if f is not None else None
    except Exception:
        return None


def _load_json(path: str | Path | None) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        raw = Path(str(path))
        if not raw.exists():
            return {}
        payload = json.loads(raw.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _planner_rows(bridge_info: Dict[str, Any] | None) -> List[Tuple[str, Dict[str, Any]]]:
    info = bridge_info if isinstance(bridge_info, dict) else {}
    planner = _load_json(info.get("planner_handoff"))
    profile = _load_json(info.get("profile_diagnostics"))
    rows: List[Tuple[str, Dict[str, Any]]] = []
    if isinstance(planner.get("decisions"), list):
        rows.extend(("planner_decisions", row) for row in planner["decisions"] if isinstance(row, dict))
    if isinstance(planner.get("watchlist_meta"), list):
        rows.extend(("planner_watchlist_meta", row) for row in planner["watchlist_meta"] if isinstance(row, dict))
    exception_leaders = profile.get("exception_leaders") if isinstance(profile.get("exception_leaders"), dict) else {}
    exception_meta = (
        exception_leaders.get("watchlist_meta")
        if isinstance(exception_leaders.get("watchlist_meta"), list)
        else []
    )
    rows.extend(("profile_exception_leaders", row) for row in exception_meta if isinstance(row, dict))
    return rows


def _ticker(row: Dict[str, Any]) -> str:
    value = _first_present((row, COMMON_FIELD_ALIASES["ticker"]))
    return str(value or "").strip().upper()


def _planner_index(rows: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    source_order = {"planner_decisions": 3, "planner_watchlist_meta": 2, "profile_exception_leaders": 1}
    for source, row in rows:
        ticker = _ticker(row)
        if not ticker:
            continue
        existing = index.get(ticker)
        if existing and source_order.get(existing.get("_planner_source"), 0) >= source_order.get(source, 0):
            continue
        enriched = dict(row)
        enriched["_planner_source"] = source
        if source in {"planner_watchlist_meta", "profile_exception_leaders"}:
            enriched.setdefault("decision_bucket", "exception_leader")
            enriched.setdefault("decision", "EXCEPTION_LEADER")
        index[ticker] = enriched
    return index


def _required_fields_for_market(market: str) -> Tuple[str, ...]:
    market_key = str(market or "").upper()
    if market_key in {"KOSPI", "KOSDAQ", "KR"}:
        return KR_REQUIRED_FIELDS
    if market_key in {"NASDAQ", "S&P500", "AMEX", "US", "NYSE"}:
        return US_REQUIRED_FIELDS
    return CORE_REQUIRED_FIELDS


def _canonical_snapshot(
    *,
    row: Dict[str, Any],
    planner_row: Dict[str, Any] | None,
    run_id: str,
    market: str,
    scan_mode: str,
    created_at: str,
    raw_rank: int | None,
    source_sections: List[str],
) -> Dict[str, Any]:
    planner = planner_row if isinstance(planner_row, dict) else {}
    factors: Dict[str, Any] = {}
    field_sources: Dict[str, str] = {}
    for field, aliases in COMMON_FIELD_ALIASES.items():
        raw_value = _first_present((row, aliases))
        planner_value = _first_present((planner, aliases))
        value = raw_value if not _is_missing(raw_value) else planner_value
        if not _is_missing(value):
            field_sources[field] = "raw_scan" if not _is_missing(raw_value) else str(planner.get("_planner_source") or "planner")
        factors[field] = _json_safe(value)

    ticker = str(factors.get("ticker") or _ticker(row) or _ticker(planner)).strip().upper()
    rank = _safe_int(factors.get("priority_rank")) or raw_rank
    decision_bucket = str(factors.get("decision_bucket") or "").strip()
    decision = str(factors.get("decision") or "").strip()
    if not decision_bucket:
        if decision.upper() == "EXCEPTION_LEADER":
            decision_bucket = "exception_leader"
        elif rank:
            decision_bucket = "picked"
        else:
            decision_bucket = "watchlist"
        factors["decision_bucket"] = decision_bucket

    return {
        "snapshot_version": "observed_factor_snapshot_v1",
        "observation_origin": "observed",
        "run_id": run_id,
        "ticker": ticker,
        "market": str(factors.get("market") or market or ""),
        "scan_mode": str(factors.get("scan_mode") or scan_mode or "SWING").upper(),
        "created_at": created_at,
        "raw_rank": raw_rank,
        "priority_rank": rank,
        "decision": decision,
        "decision_bucket": decision_bucket,
        "source_sections": source_sections,
        "raw_scan_present": "raw_scan" in source_sections,
        "planner_present": any(section.startswith("planner") or section.startswith("profile") for section in source_sections),
        "field_sources": field_sources,
        "factors": factors,
    }


def build_observed_factor_snapshots(
    *,
    run_id: str,
    market: str,
    scan_mode: str,
    results: List[Dict[str, Any]],
    created_at: str,
    bridge_info: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    planner_rows = _planner_rows(bridge_info)
    planner_by_ticker = _planner_index(planner_rows)
    snapshots: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for idx, row in enumerate(results or [], start=1):
        if not isinstance(row, dict):
            continue
        ticker = _ticker(row)
        planner = planner_by_ticker.get(ticker, {})
        sources = ["raw_scan"]
        if planner:
            sources.append(str(planner.get("_planner_source") or "planner"))
        snapshot = _canonical_snapshot(
            row=row,
            planner_row=planner,
            run_id=run_id,
            market=market,
            scan_mode=scan_mode,
            created_at=created_at,
            raw_rank=idx,
            source_sections=sources,
        )
        if snapshot["ticker"]:
            seen.add(snapshot["ticker"])
            snapshots.append(snapshot)

    for ticker, planner in planner_by_ticker.items():
        if ticker in seen:
            continue
        source = str(planner.get("_planner_source") or "planner")
        snapshot = _canonical_snapshot(
            row={},
            planner_row=planner,
            run_id=run_id,
            market=market,
            scan_mode=scan_mode,
            created_at=created_at,
            raw_rank=None,
            source_sections=[source],
        )
        if snapshot["ticker"]:
            snapshots.append(snapshot)

    return snapshots


def build_scan_integrity_report(
    *,
    run_id: str,
    market: str,
    scan_mode: str,
    snapshots: List[Dict[str, Any]],
    raw_result_count: int,
    total_scans: int,
    diagnostics: Dict[str, Any] | None = None,
    top_deep_reports: Dict[str, Any] | None = None,
    created_at: str | None = None,
) -> Dict[str, Any]:
    required_fields = _required_fields_for_market(market)
    diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
    top_deep_reports = top_deep_reports if isinstance(top_deep_reports, dict) else {}
    field_missing_counts = {field: 0 for field in required_fields}
    missing_by_ticker: Dict[str, List[str]] = {}
    picked = 0
    exception = 0
    raw_present = 0
    planner_only = 0

    for snapshot in snapshots or []:
        factors = snapshot.get("factors") if isinstance(snapshot.get("factors"), dict) else {}
        ticker = str(snapshot.get("ticker") or "").strip()
        missing: List[str] = []
        for field in required_fields:
            if _is_missing(factors.get(field)):
                field_missing_counts[field] += 1
                missing.append(field)
        if ticker and missing:
            missing_by_ticker[ticker] = missing
        bucket = str(snapshot.get("decision_bucket") or factors.get("decision_bucket") or "").lower()
        if bucket == "exception_leader":
            exception += 1
        elif bucket == "picked" or snapshot.get("priority_rank"):
            picked += 1
        if snapshot.get("raw_scan_present"):
            raw_present += 1
        elif snapshot.get("planner_present"):
            planner_only += 1

    total_snapshots = len(snapshots or [])
    total_required_values = max(1, total_snapshots * len(required_fields))
    missing_total = sum(field_missing_counts.values())
    completeness = 1.0 - (missing_total / total_required_values)
    quality_flags: List[str] = []
    if raw_result_count > 0 and raw_present != raw_result_count:
        quality_flags.append("RAW_RESULT_COUNT_MISMATCH")
    if total_snapshots == 0 and raw_result_count > 0:
        quality_flags.append("SNAPSHOT_EMPTY")
    if total_snapshots > 0 and completeness < 0.95:
        quality_flags.append("FACTOR_COMPLETENESS_BELOW_95")
    if picked < min(5, raw_result_count) and raw_result_count >= 5:
        quality_flags.append("PICKED_COUNT_BELOW_TOP5")
    if top_deep_reports.get("count") is not None:
        try:
            deep_count = int(top_deep_reports.get("count") or 0)
            if deep_count < min(5, raw_result_count) and raw_result_count >= 5:
                quality_flags.append("TOP_DEEP_COUNT_BELOW_TOP5")
            if exception > 0 and deep_count < min(raw_result_count + exception, 10):
                quality_flags.append("TOP_DEEP_MAY_MISS_EXCEPTION_LEADERS")
        except Exception:
            pass

    report = {
        "report_version": "scan_integrity_report_v1",
        "observation_origin": "observed",
        "run_id": run_id,
        "market": str(market or ""),
        "scan_mode": str(scan_mode or "SWING").upper(),
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "raw_result_count": int(raw_result_count or 0),
        "snapshot_count": total_snapshots,
        "raw_present_snapshot_count": raw_present,
        "planner_only_snapshot_count": planner_only,
        "total_scans": int(total_scans or 0),
        "filtered_count": int(diagnostics.get("filtered_count", 0) or 0),
        "worker_error_count": int(diagnostics.get("worker_error_count", 0) or 0),
        "executor_exception_count": int(diagnostics.get("executor_exception_count", 0) or 0),
        "picked_count": picked,
        "exception_leader_count": exception,
        "top_deep_report_count": top_deep_reports.get("count"),
        "required_fields": list(required_fields),
        "feature_completeness": round(float(completeness), 4),
        "field_missing_counts": field_missing_counts,
        "missing_by_ticker": missing_by_ticker,
        "quality_flags": quality_flags,
        "validation_excluded": bool(quality_flags),
    }
    return _json_safe(report)


def write_scan_integrity_artifacts(
    *,
    artifact_dir: str | Path,
    run_id: str,
    market: str,
    scan_mode: str,
    results: List[Dict[str, Any]],
    total_scans: int,
    diagnostics: Dict[str, Any] | None = None,
    bridge_info: Dict[str, Any] | None = None,
    top_deep_reports: Dict[str, Any] | None = None,
    created_at: str | None = None,
) -> Dict[str, Any]:
    created_at = created_at or datetime.now(timezone.utc).isoformat()
    target_dir = Path(artifact_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    snapshots = build_observed_factor_snapshots(
        run_id=run_id,
        market=market,
        scan_mode=scan_mode,
        results=results,
        created_at=created_at,
        bridge_info=bridge_info,
    )
    report = build_scan_integrity_report(
        run_id=run_id,
        market=market,
        scan_mode=scan_mode,
        snapshots=snapshots,
        raw_result_count=len([row for row in (results or []) if isinstance(row, dict)]),
        total_scans=total_scans,
        diagnostics=diagnostics,
        top_deep_reports=top_deep_reports,
        created_at=created_at,
    )
    snapshot_path = target_dir / "observed_factor_snapshots.json"
    report_path = target_dir / "scan_integrity_report.json"
    write_json(
        snapshot_path,
        {
            "snapshot_version": "observed_factor_snapshot_v1",
            "run_id": run_id,
            "market": str(market or ""),
            "scan_mode": str(scan_mode or "SWING").upper(),
            "created_at": created_at,
            "observation_origin": "observed",
            "snapshots": snapshots,
        },
    )
    write_json(report_path, report)
    return {
        "ok": snapshot_path.exists() and report_path.exists(),
        "observed_factor_snapshots": str(snapshot_path),
        "scan_integrity_report": str(report_path),
        "report": report,
    }


__all__ = [
    "build_observed_factor_snapshots",
    "build_scan_integrity_report",
    "write_scan_integrity_artifacts",
]
