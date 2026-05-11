from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from multi_agent.agents.aggregation_runtime import build_aggregation_handoff
from multi_agent.agents.backtest_runtime import build_backtest_handoff
from multi_agent.agents.market_context_runtime import build_market_context_handoff
from multi_agent.agents.planner_runtime import build_planner_handoff
from multi_agent.contracts.serialization import read_json, write_json
from multi_agent.contracts.types import (
    PlannerDecision,
    PostmortemReport,
    RunContext,
    WarningItem,
)
from multi_agent.storage.memory_layers import MemoryManager
from multi_agent.storage.long_term_memory import (
    log_improvement_tickets,
    log_outcome_health,
    log_postmortem,
    log_profile_diagnostics,
    log_run_summary,
)
from multi_agent.workflows.postmortem import build_postmortem_report, create_improvement_ticket
from multi_agent.workflows.outcome_buckets import classify_decision_bucket
from modules.market_data import get_history
from modules.loss_risk_features import (
    compute_loss_risk_features,
    get_loss_risk_gate_thresholds,
    get_loss_risk_soft_cap_decision,
)
from modules.regime_market_policy import get_market_policy
from modules.regime_ticker_profiles import compute_profile_adjustment, get_ticker_profile, resolve_profile_market, resolve_profile_regime
from modules.kr_stock_theme_master import get_stock_theme_record
from modules.quant_analysis import QuantStrategy

_REFERENCE_PRICE_CACHE: Dict[str, float | None] = {}


def _resolve_detail_price(detail: Dict[str, Any]) -> float | None:
    if not isinstance(detail, dict):
        return None
    for key in ["entry_reference_price", "curr_price", "price", "close"]:
        value = detail.get(key)
        if value is not None:
            try:
                return float(value)
            except Exception:
                pass
    for nested_key in ["amex_features", "intraday_setup"]:
        nested = detail.get(nested_key)
        if not isinstance(nested, dict):
            continue
        for key in ["price", "curr_price", "close"]:
            value = nested.get(key)
            if value is not None:
                try:
                    return float(value)
                except Exception:
                    pass
    return None


def _resolve_reference_price(ticker: str, seed_price: Any = None, cache_date: str | None = None) -> float | None:
    try:
        if seed_price is not None:
            return float(seed_price)
    except Exception:
        pass
    key = str(ticker or "").strip().upper()
    if not key:
        return None
    cache_key = f"{key}:{str(cache_date or '').strip() or 'unknown'}"
    if cache_key in _REFERENCE_PRICE_CACHE:
        return _REFERENCE_PRICE_CACHE[cache_key]
    try:
        hist = get_history(key, period="10d", interval="1d")
        if hist is not None and not hist.empty and "Close" in hist.columns:
            value = float(hist["Close"].dropna().iloc[-1])
            _REFERENCE_PRICE_CACHE[cache_key] = value
            return value
    except Exception:
        pass
    _REFERENCE_PRICE_CACHE[cache_key] = None
    return None


def _parse_run_context(scanner_payload: Dict[str, Any], run_id_hint: str) -> RunContext:
    raw = scanner_payload.get("run_context", {})
    run_id = str(raw.get("run_id") or run_id_hint or "RUN-UNKNOWN")
    created_at = str(raw.get("created_at") or "")

    if created_at:
        return RunContext(
            run_id=run_id,
            created_at=created_at,
            as_of_date=str(raw.get("as_of_date") or ""),
            market=str(raw.get("market") or ""),
            strategy_version=str(raw.get("strategy_version") or ""),
            model_version=str(raw.get("model_version") or ""),
            code_version=str(raw.get("code_version") or ""),
        )

    return RunContext(
        run_id=run_id,
        as_of_date=str(raw.get("as_of_date") or ""),
        market=str(raw.get("market") or ""),
        strategy_version=str(raw.get("strategy_version") or ""),
        model_version=str(raw.get("model_version") or ""),
        code_version=str(raw.get("code_version") or ""),
    )


def _build_realized_outcomes_placeholder(context: RunContext, planner_handoff: Any, scanner_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    scanner_summary = scanner_payload.get("summary", {}) if isinstance(scanner_payload, dict) and isinstance(scanner_payload.get("summary"), dict) else {}
    input_meta = scanner_summary.get("input_meta", {}) if isinstance(scanner_summary.get("input_meta"), dict) else {}
    scan_mode = str(input_meta.get("scan_mode") or scanner_summary.get("scan_mode") or "SWING").upper()
    strategy_family = str(input_meta.get("strategy_family") or scanner_summary.get("strategy_family") or "").upper()
    scanner_market_gate = _resolve_scanner_market_gate(scanner_payload or {}) if isinstance(scanner_payload, dict) else ""
    decisions = getattr(planner_handoff, "decisions", []) or []
    seen_tickers: set[str] = set()
    trade_priority_rank = 0
    for dec in decisions:
        ticker = str(getattr(dec, "ticker", "UNKNOWN"))
        seen_tickers.add(ticker)
        decision_bucket = classify_decision_bucket(getattr(dec, "decision", "UNKNOWN"))
        loss_risk_score = getattr(dec, "loss_risk_score", None)
        loss_hard_cap = float(get_loss_risk_gate_thresholds(context.market).get("hard", 65.0))
        try:
            is_loss_hard_cap = loss_risk_score is not None and float(loss_risk_score) >= loss_hard_cap
        except Exception:
            is_loss_hard_cap = False
        if decision_bucket == "ignored" or is_loss_hard_cap:
            archive_priority_rank = None
        else:
            trade_priority_rank += 1
            archive_priority_rank = trade_priority_rank
        rows.append(
            {
                "run_id": context.run_id,
                "market": context.market,
                "ticker": ticker,
                "stock_name": str(getattr(dec, "stock_name", "") or ""),
                "priority_rank": archive_priority_rank,
                "decision": str(getattr(dec, "decision", "UNKNOWN")),
                "decision_bucket": decision_bucket,
                "status": "PENDING",
                "horizon": f"T+{int(getattr(dec, 'target_horizon_days', 3) or 3)}D",
                "recommended_at": context.created_at,
                "scan_mode": str(getattr(dec, "scan_mode", "") or scan_mode).upper(),
                "strategy_family": str(getattr(dec, "strategy_family", "") or strategy_family or "").upper() or None,
                "alpha_score": getattr(dec, "alpha_score", None),
                "tech_score": getattr(dec, "tech_score", None),
                "conviction_score": getattr(dec, "conviction_score", None),
                "decision_score": getattr(dec, "decision_score", None),
                "whale_score": getattr(dec, "whale_score", None),
                "volume": getattr(dec, "volume", None),
                "volume_ratio": getattr(dec, "volume_ratio", None),
                "volume_confirmed": getattr(dec, "volume_confirmed", None),
                "prob_5": getattr(dec, "prob_5", None),
                "prob_clean": getattr(dec, "prob_clean", None),
                "real_trend": getattr(dec, "real_trend", ""),
                "phase25_variant": getattr(dec, "phase25_variant", "") or None,
                "phase25_prob": getattr(dec, "phase25_prob", None),
                "phase25_shadow_variant": getattr(dec, "phase25_shadow_variant", "") or None,
                "phase25_shadow_prob": getattr(dec, "phase25_shadow_prob", None),
                "phase25_recommended_threshold": getattr(dec, "phase25_recommended_threshold", None),
                "phase25_signal_direction": getattr(dec, "phase25_signal_direction", "") or None,
                "phase25_raw_auc": getattr(dec, "phase25_raw_auc", None),
                "phase25_oos_auc": getattr(dec, "phase25_oos_auc", None),
                "phase25_oos_win_rate_pct": getattr(dec, "phase25_oos_win_rate_pct", None),
                "phase25_oos_avg_return_pct": getattr(dec, "phase25_oos_avg_return_pct", None),
                "expected_edge_score": getattr(dec, "expected_edge_score", None),
                "expected_return_1d_pct": getattr(dec, "expected_return_1d_pct", None),
                "expected_return_3d_pct": getattr(dec, "expected_return_3d_pct", None),
                "model_prob_available_count": getattr(dec, "model_prob_available_count", None),
                "model_prob_mean": getattr(dec, "model_prob_mean", None),
                "low_model_prob_score": getattr(dec, "low_model_prob_score", None),
                "low_prob_high_score": getattr(dec, "low_prob_high_score", None),
                "expected_edge_inversion_score": getattr(dec, "expected_edge_inversion_score", None),
                "loss_risk_score": getattr(dec, "loss_risk_score", None),
                "relative_rank_score": getattr(dec, "relative_rank_score", None),
                "relative_rank_pct": getattr(dec, "relative_rank_pct", None),
                "regime_adjusted_grade": getattr(dec, "regime_adjusted_grade", "") or None,
                "relative_rank_model": getattr(dec, "relative_rank_model", "") or None,
                "selection_lane": getattr(dec, "selection_lane", "") or None,
                "rationale": list(getattr(dec, "rationale", []) or []) or None,
                "theme_risk": list(getattr(dec, "theme_risk", []) or []) or None,
                "quant_priority_score": getattr(dec, "quant_priority_score", None),
                "quant_score_1d": getattr(dec, "quant_score_1d", None),
                "quant_score_3d": getattr(dec, "quant_score_3d", None),
                "market_gate": getattr(dec, "market_gate", "") or scanner_market_gate or None,
                "scanner_timeframe_profile": getattr(dec, "scanner_timeframe_profile", "") or None,
                "kr_universe_role": getattr(dec, "kr_universe_role", "") or None,
                "explosive_eligible": getattr(dec, "explosive_eligible", False),
                "explosive_gate_reasons": list(getattr(dec, "explosive_gate_reasons", []) or []),
                "continuation_eligible": getattr(dec, "continuation_eligible", False),
                "continuation_enabled": getattr(dec, "continuation_enabled", False),
                "continuation_prob_3d": getattr(dec, "continuation_prob_3d", None),
                "continuation_evidence": getattr(dec, "continuation_evidence", None),
                "continuation_gate_reasons": list(getattr(dec, "continuation_gate_reasons", []) or []),
                "primary_theme": getattr(dec, "primary_theme", "") or None,
                "theme_source": getattr(dec, "theme_source", "") or None,
                "theme_inference_status": getattr(dec, "theme_inference_status", "") or None,
                "secondary_themes": list(getattr(dec, "secondary_themes", []) or []),
                "theme_routing_path": getattr(dec, "theme_routing_path", "") or None,
                "entry_reference_price": _resolve_reference_price(
                    ticker,
                    getattr(dec, "entry_reference_price", None),
                    cache_date=context.as_of_date,
                ),
                "realized_return_pct": None,
                "outcome_label": None,
                "outcome_recorded_at": None,
                "source_ref": f"planner_handoff.json#{ticker}",
            }
        )

    # Fallback watchlist should also be outcome-tracked when planner decisions are empty.
    watchlist = getattr(planner_handoff, "watchlist", []) or []
    watchlist_meta = getattr(planner_handoff, "watchlist_meta", []) or []
    meta_by_ticker: Dict[str, Dict[str, Any]] = {}
    if isinstance(watchlist_meta, list):
        for row in watchlist_meta:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").strip()
            if ticker:
                meta_by_ticker[ticker] = row

    for rank, ticker_raw in enumerate(watchlist, start=1):
        ticker = str(ticker_raw or "").strip()
        if not ticker or ticker in seen_tickers:
            continue
        meta = _enrich_tracking_meta(
            meta_by_ticker.get(ticker, {}),
            ticker=ticker,
            source_run_id=str((meta_by_ticker.get(ticker, {}) or {}).get("source_run_id") or ""),
        )
        horizon_days = _safe_int(meta.get("horizon_days", 3))
        if horizon_days <= 0:
            horizon_days = 3
        source_profile = str(meta.get("source_profile", "") or "").strip().lower()
        watchlist_reason = str(meta.get("reason", "") or "").strip().lower()
        decision_label = "FALLBACK_WATCHLIST"
        if (
            source_profile == "learned_market_policy"
            or watchlist_reason == "market_policy_watchlist_only"
            or watchlist_reason == "near_miss_watchlist"
        ):
            decision_label = "WATCHLIST_ONLY"
        if watchlist_reason == "exception_leader_watchlist":
            decision_label = "EXCEPTION_LEADER"
        loss_risk_score = meta.get("loss_risk_score")
        loss_hard_cap = float(get_loss_risk_gate_thresholds(context.market).get("hard", 65.0))
        try:
            is_loss_hard_cap = loss_risk_score is not None and float(loss_risk_score) >= loss_hard_cap
        except Exception:
            is_loss_hard_cap = False
        if is_loss_hard_cap:
            decision_label = "OBSERVE"
            archive_priority_rank = None
        else:
            archive_priority_rank = int(rank)
        rows.append(
            {
                "run_id": context.run_id,
                "market": context.market,
                "ticker": ticker,
                "stock_name": str(meta.get("stock_name", "") or ""),
                "priority_rank": archive_priority_rank,
                "decision": decision_label,
                "decision_bucket": classify_decision_bucket(decision_label),
                "status": "PENDING",
                "horizon": f"T+{horizon_days}D",
                "recommended_at": context.created_at,
                "scan_mode": scan_mode,
                "strategy_family": strategy_family or None,
                "alpha_score": meta.get("alpha_score"),
                "tech_score": meta.get("tech_score"),
                "conviction_score": meta.get("conviction_score"),
                "decision_score": meta.get("decision_score") or meta.get("exception_score") or meta.get("conviction_score"),
                "whale_score": meta.get("whale_score"),
                "volume": meta.get("volume"),
                "volume_ratio": meta.get("volume_ratio"),
                "volume_confirmed": meta.get("volume_confirmed"),
                "prob_5": meta.get("prob_5"),
                "prob_clean": meta.get("prob_clean"),
                "real_trend": meta.get("real_trend"),
                "phase25_variant": meta.get("phase25_variant"),
                "phase25_prob": meta.get("phase25_prob"),
                "phase25_shadow_variant": meta.get("phase25_shadow_variant"),
                "phase25_shadow_prob": meta.get("phase25_shadow_prob"),
                "phase25_recommended_threshold": meta.get("phase25_recommended_threshold"),
                "expected_edge_score": meta.get("expected_edge_score"),
                "expected_return_1d_pct": meta.get("expected_return_1d_pct"),
                "expected_return_3d_pct": meta.get("expected_return_3d_pct"),
                "model_prob_available_count": meta.get("model_prob_available_count"),
                "model_prob_mean": meta.get("model_prob_mean"),
                "low_model_prob_score": meta.get("low_model_prob_score"),
                "low_prob_high_score": meta.get("low_prob_high_score"),
                "expected_edge_inversion_score": meta.get("expected_edge_inversion_score"),
                "loss_risk_score": meta.get("loss_risk_score"),
                "relative_rank_score": meta.get("relative_rank_score"),
                "relative_rank_pct": meta.get("relative_rank_pct"),
                "regime_adjusted_grade": meta.get("regime_adjusted_grade"),
                "relative_rank_model": meta.get("relative_rank_model"),
                "market_gate": meta.get("market_gate") or scanner_market_gate or None,
                "scanner_timeframe_profile": meta.get("scanner_timeframe_profile"),
                "kr_universe_role": meta.get("kr_universe_role"),
                "explosive_eligible": meta.get("explosive_eligible"),
                "explosive_gate_reasons": meta.get("explosive_gate_reasons"),
                "continuation_eligible": meta.get("continuation_eligible"),
                "continuation_enabled": meta.get("continuation_enabled"),
                "continuation_prob_3d": meta.get("continuation_prob_3d"),
                "continuation_evidence": meta.get("continuation_evidence"),
                "continuation_gate_reasons": meta.get("continuation_gate_reasons"),
                "primary_theme": meta.get("primary_theme"),
                "theme_source": meta.get("theme_source"),
                "theme_inference_status": meta.get("theme_inference_status"),
                "secondary_themes": meta.get("secondary_themes"),
                "theme_routing_path": meta.get("theme_routing_path"),
                "entry_reference_price": _resolve_reference_price(
                    ticker,
                    meta.get("entry_reference_price"),
                    cache_date=context.as_of_date,
                ),
                "realized_return_pct": None,
                "outcome_label": None,
                "outcome_recorded_at": None,
                "source_ref": f"planner_handoff.watchlist_meta#{ticker}",
            }
        )
        seen_tickers.add(ticker)

    return {
        "run_context": context.to_dict(),
        "outcomes": rows,
        "summary": {
            "pending_count": len(rows),
            "resolved_count": 0,
        },
        "produced_at": datetime.now(timezone.utc).isoformat(),
    }


def _resolve_scanner_market_gate(scanner_payload: Dict[str, Any]) -> str:
    summary = scanner_payload.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    input_meta = summary.get("input_meta", {})
    if not isinstance(input_meta, dict):
        input_meta = {}
    market_gate = input_meta.get("market_gate", summary.get("market_gate", {}))
    if not isinstance(market_gate, dict):
        market_gate = {}
    return str(market_gate.get("gate", "") or "").upper()


def _resolve_watchlist_only_policy(
    *,
    context: RunContext,
    scanner_payload: Dict[str, Any],
) -> Dict[str, Any]:
    market_gate = _resolve_scanner_market_gate(scanner_payload)
    policy = get_market_policy(market_type=context.market, ticker=None, market_gate=market_gate) or {}
    mode = str(policy.get("mode", "") or "").lower()
    summary = scanner_payload.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    diagnostics = summary.get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    reject_counts = diagnostics.get("reject_reason_counts", {})
    if not isinstance(reject_counts, dict):
        reject_counts = {}
    market_policy_avoid_count = _safe_int(reject_counts.get("MARKET_POLICY_AVOID", 0))
    total_rejects = sum(_safe_int(v) for v in reject_counts.values())
    apply = mode == "avoid"
    return {
        "apply": bool(apply),
        "market_gate": market_gate,
        "policy": policy,
        "mode": mode,
        "market_policy_avoid_count": int(market_policy_avoid_count),
        "total_rejects": int(total_rejects),
    }


def _build_watchlist_only_meta(
    *,
    watchlist: List[str],
    policy_summary: Dict[str, Any],
    ticker_names: Dict[str, str] | None = None,
    decision_details: Dict[str, Dict[str, Any]] | None = None,
    horizon_days: int = 2,
) -> List[Dict[str, Any]]:
    generated_at = datetime.now(timezone.utc)
    expires_at = generated_at + timedelta(days=max(1, int(horizon_days)))
    market_gate = str(policy_summary.get("market_gate") or "").upper()
    policy = policy_summary.get("policy", {})
    if not isinstance(policy, dict):
        policy = {}
    mode = str(policy_summary.get("mode") or policy.get("mode") or "unknown").lower()
    avg_5d_pct = _safe_float(policy.get("avg_5d_pct", 0.0))
    win_5d_pct = _safe_float(policy.get("win_5d_pct", 0.0))
    meta: List[Dict[str, Any]] = []
    for ticker in watchlist:
        extra = (decision_details or {}).get(str(ticker), {})
        meta.append(
            {
                "ticker": str(ticker),
                "stock_name": str(extra.get("stock_name") or (ticker_names or {}).get(str(ticker), "") or ""),
                "source_profile": "learned_market_policy",
                "risk_label": "WATCHLIST_ONLY",
                "generated_at": generated_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "horizon_days": int(horizon_days),
                "reason": "market_policy_watchlist_only",
                "market_gate": market_gate,
                "policy_mode": mode,
                "policy_win_5d_pct": round(win_5d_pct, 2),
                "policy_avg_5d_pct": round(avg_5d_pct, 2),
                "alpha_score": extra.get("alpha_score"),
                "tech_score": extra.get("tech_score"),
                "conviction_score": extra.get("conviction_score"),
                "decision_score": extra.get("decision_score"),
                "whale_score": extra.get("whale_score"),
                "volume": extra.get("volume"),
                "volume_ratio": extra.get("volume_ratio"),
                "volume_confirmed": extra.get("volume_confirmed"),
                "prob_5": extra.get("prob_5"),
                "prob_clean": extra.get("prob_clean"),
                "real_trend": extra.get("real_trend"),
                "entry_reference_price": extra.get("entry_reference_price"),
                "phase25_prob": extra.get("phase25_prob"),
                "phase25_variant": extra.get("phase25_variant"),
                "phase25_shadow_variant": extra.get("phase25_shadow_variant"),
                "phase25_shadow_prob": extra.get("phase25_shadow_prob"),
                "phase25_recommended_threshold": extra.get("phase25_recommended_threshold"),
                "expected_edge_score": extra.get("expected_edge_score"),
                "expected_return_1d_pct": extra.get("expected_return_1d_pct"),
                "expected_return_3d_pct": extra.get("expected_return_3d_pct"),
                "primary_theme": extra.get("primary_theme"),
                "theme_source": extra.get("theme_source"),
                "theme_inference_status": extra.get("theme_inference_status"),
                "secondary_themes": extra.get("secondary_themes"),
                "theme_routing_path": extra.get("theme_routing_path"),
            }
        )
    return meta


def _apply_watchlist_only_mode(
    *,
    context: RunContext,
    planner_handoff: Any,
    policy_summary: Dict[str, Any],
    max_watchlist: int = 10,
) -> bool:
    if not bool(policy_summary.get("apply")):
        return False
    decisions = list(getattr(planner_handoff, "decisions", []) or [])
    if not decisions:
        return False

    watchlist: List[str] = []
    for dec in decisions:
        ticker = str(getattr(dec, "ticker", "") or "").strip()
        if not ticker or ticker in watchlist:
            continue
        watchlist.append(ticker)
        if len(watchlist) >= max_watchlist:
            break

    if not watchlist:
        return False

    preserved_decisions: List[Any] = []
    downgraded_decisions: List[Any] = []
    for dec in decisions:
        routing_path = str(getattr(dec, "theme_routing_path", "") or "").strip().lower()
        theme_source = str(getattr(dec, "theme_source", "") or "").strip().lower()
        primary_theme = str(getattr(dec, "primary_theme", "") or "").strip().lower()
        decision_score = _safe_float(getattr(dec, "decision_score", 0.0))
        real_trend = str(getattr(dec, "real_trend", "") or "").strip().upper()
        phase25_prob_raw = getattr(dec, "phase25_prob", None)
        phase25_threshold_raw = getattr(dec, "phase25_recommended_threshold", None)
        phase25_prob = None if phase25_prob_raw in (None, "") else _safe_float(phase25_prob_raw)
        phase25_threshold = None if phase25_threshold_raw in (None, "") else _safe_float(phase25_threshold_raw)
        phase25_gap_ok = (
            phase25_prob is None
            or phase25_threshold is None
            or (phase25_threshold - phase25_prob) <= 8.0
        )
        # OOS-validated preserve: when the model bundle the user is about to
        # trade was independently validated on the held-out 15% slice with
        # production-quality stats, watchlist-only downgrade is stale (the
        # learned policy was set when KOSDAQ swing was alpha-only at 50% win;
        # it is no longer the current model). Mirror the same gate used by
        # quant_analysis.py and planner_runtime: oos_win_rate>=70,
        # oos_avg_return>=5, signal_direction='normal' (or upgraded from
        # 'uncertain' via OOS).
        oos_win = getattr(dec, "phase25_oos_win_rate_pct", None)
        oos_ret = getattr(dec, "phase25_oos_avg_return_pct", None)
        sig_dir = str(getattr(dec, "phase25_signal_direction", "") or "").lower()
        oos_validated_preserve = (
            sig_dir == "normal"
            and oos_win is not None and _safe_float(oos_win) >= 70.0
            and oos_ret is not None and _safe_float(oos_ret) >= 5.0
            and decision_score >= 55.0
            and real_trend == "UP"
        )
        if oos_validated_preserve:
            preserved_decisions.append(dec)
            continue
        if (
            routing_path in {"theme_exception_candidate", "theme_routed"}
            and theme_source == "stock_master"
            and primary_theme not in {"", "unclassified"}
            and decision_score >= 66.0
            and real_trend == "UP"
            and phase25_gap_ok
        ):
            setattr(dec, "theme_routing_path", "theme_routed")
            preserved_decisions.append(dec)
            continue
        downgraded_decisions.append(dec)

    planner_handoff.decisions = preserved_decisions[:2]
    planner_handoff.watchlist = [
        str(getattr(dec, "ticker", "") or "").strip()
        for dec in downgraded_decisions
        if str(getattr(dec, "ticker", "") or "").strip()
    ][:max_watchlist]
    decision_details = {
        str(getattr(dec, "ticker", "") or ""): {
            "stock_name": str(getattr(dec, "stock_name", "") or ""),
            "alpha_score": getattr(dec, "alpha_score", None),
            "tech_score": getattr(dec, "tech_score", None),
            "conviction_score": getattr(dec, "conviction_score", None),
            "decision_score": getattr(dec, "decision_score", None),
            "whale_score": getattr(dec, "whale_score", None),
            "volume": getattr(dec, "volume", None),
            "volume_ratio": getattr(dec, "volume_ratio", None),
            "volume_confirmed": getattr(dec, "volume_confirmed", None),
            "prob_5": getattr(dec, "prob_5", None),
            "prob_clean": getattr(dec, "prob_clean", None),
            "real_trend": getattr(dec, "real_trend", ""),
            "entry_reference_price": getattr(dec, "entry_reference_price", None),
            "phase25_prob": getattr(dec, "phase25_prob", None),
            "phase25_variant": getattr(dec, "phase25_variant", None),
            "phase25_shadow_variant": getattr(dec, "phase25_shadow_variant", None),
            "phase25_shadow_prob": getattr(dec, "phase25_shadow_prob", None),
            "phase25_recommended_threshold": getattr(dec, "phase25_recommended_threshold", None),
            "expected_edge_score": getattr(dec, "expected_edge_score", None),
            "expected_return_1d_pct": getattr(dec, "expected_return_1d_pct", None),
            "expected_return_3d_pct": getattr(dec, "expected_return_3d_pct", None),
            "primary_theme": getattr(dec, "primary_theme", ""),
            "theme_source": getattr(dec, "theme_source", ""),
            "theme_inference_status": getattr(dec, "theme_inference_status", ""),
            "secondary_themes": list(getattr(dec, "secondary_themes", []) or []),
            "theme_routing_path": getattr(dec, "theme_routing_path", ""),
        }
        for dec in downgraded_decisions
        if str(getattr(dec, "ticker", "") or "").strip()
    }
    planner_handoff.watchlist_meta = _build_watchlist_only_meta(
        watchlist=planner_handoff.watchlist,
        policy_summary=policy_summary,
        ticker_names={str(getattr(dec, "ticker", "")): str(getattr(dec, "stock_name", "") or "") for dec in downgraded_decisions},
        decision_details=decision_details,
        horizon_days=2,
    )
    if preserved_decisions:
        planner_handoff.global_warnings.append(
            WarningItem(
                code="THEME_ROUTE_PARTIAL_OVERRIDE",
                message=(
                    f"Planner preserved {len(planner_handoff.decisions)} theme-routed leader candidate(s) despite "
                    f"watchlist-only policy because beneficiary theme leadership remained strong."
                ),
                severity="warning",
            )
        )
    planner_handoff.global_warnings.append(
        WarningItem(
            code="MARKET_POLICY_WATCHLIST_ONLY",
            message=(
                f"Planner downgraded active recommendations to watchlist-only because learned policy for "
                f"{context.market}/{policy_summary.get('market_gate') or 'UNKNOWN'} is avoid."
            ),
            severity="warning",
        )
    )
    return True


def _build_postmortem(
    context: RunContext,
    candidate_count: int,
    weak_ratio: float,
    market_context_warning_codes: List[str],
    profile_diagnostics: Dict[str, Any] | None = None,
    outcome_health: Dict[str, Any] | None = None,
) -> Tuple[PostmortemReport, List[Dict[str, Any]]]:
    likely_causes: List[str] = []
    tickets = []

    if candidate_count == 0:
        likely_causes.append("Scanner produced zero candidates; filter or data pipeline mismatch is likely.")
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="scanner_agent",
                owner_module="app.py|auto_bot.py scanner bridge",
                title="Investigate zero-candidate scan runs",
                hypothesis="Threshold coupling or upstream data fetch failures can collapse candidate output.",
                requested_change="Add per-filter reject counters and surface them in scanner_trace.",
                priority="high",
            )
        )

    if candidate_count > 0 and weak_ratio >= 0.5:
        likely_causes.append("Candidate quality is low under current thresholds or market pressure.")
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="aggregation_agent",
                owner_module="candidate quality diagnostics",
                title="Reduce weak candidate concentration",
                hypothesis="Ranking emphasis may over-weight technical score in weak regime.",
                requested_change="Add concentration-aware penalty and enforce diversity gate.",
                priority="medium",
            )
        )

    if candidate_count < 20:
        likely_causes.append("Sample size is small; confidence may be overstated.")
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="backtest_learning_agent",
                owner_module="backtest diagnostics",
                title="Strengthen small-sample safeguards",
                hypothesis="Current run size is insufficient for stable inference.",
                requested_change="Attach sample-size penalty to planner confidence and show warning banner.",
                priority="medium",
            )
        )

    context_fail_codes = {"MARKET_CONTEXT_NOT_WIRED", "MACRO_CONTEXT_FETCH_FAIL", "NEWS_CONTEXT_FETCH_FAIL"}
    if any(code in context_fail_codes for code in market_context_warning_codes):
        likely_causes.append("Market/news context is incomplete and should be stabilized before high-conviction automation.")
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="market_news_context_agent",
                owner_module="modules/macro_scheduler.py + modules/market_intelligence.py",
                title="Stabilize live market context handoff",
                hypothesis="Missing or unstable regime/news overlay can cause false positives in weak markets.",
                requested_change="Raise macro/news data fetch reliability and reduce fallback/no-context frequency.",
                priority="high",
            )
        )

    diag = profile_diagnostics if isinstance(profile_diagnostics, dict) else {}
    flags = diag.get("flags", {})
    if not isinstance(flags, dict):
        flags = {}
    current_profile = str(diag.get("current_profile", "unknown")).lower()
    watchlist_only_policy = diag.get("watchlist_only_policy", {})
    if not isinstance(watchlist_only_policy, dict):
        watchlist_only_policy = {}
    prod_dev_gap = bool(flags.get("prod_dev_gap", False))
    prod_zero_streak_alert = bool(flags.get("prod_zero_streak_alert", False))
    if bool(watchlist_only_policy.get("applied", False)):
        policy_mode = str(watchlist_only_policy.get("mode", "unknown"))
        market_gate = str(watchlist_only_policy.get("market_gate", "UNKNOWN"))
        likely_causes.append(
            f"Learned market policy downgraded planner to watchlist-only ({context.market}/{market_gate}, mode={policy_mode})."
        )
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="pm_planner_agent",
                owner_module="planner policy + regime scan policy",
                title="Review watchlist-only market policy coverage",
                hypothesis="Planner is suppressing active recommendations because the learned market/regime bucket is currently avoid.",
                requested_change=(
                    "Validate whether watchlist-only mode is appropriate for this market/regime bucket and retrain policy "
                    "once more realized outcomes accumulate."
                ),
                priority="medium",
            )
        )
    if current_profile == "prod" and prod_dev_gap:
        likely_causes.append(
            "Prod gate profile appears over-restrictive versus recent dev baseline, causing candidate starvation."
        )
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="scanner_agent",
                owner_module="multi_agent/config/scan_profiles.py + modules/scanner_services.py",
                title="Calibrate prod gate thresholds against observed profile gap",
                hypothesis="Prod thresholds may be too strict relative to current regime and suppress viable candidates.",
                requested_change="Compare prod/dev reject-reason distributions and retune prod thresholds with guardrails.",
                priority="high",
            )
        )
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="backtest_learning_agent",
                owner_module="backtest diagnostics + threshold calibration",
                title="Validate threshold changes with regime-sliced backtests",
                hypothesis="Threshold relaxation without regime validation can increase false positives.",
                requested_change="Run regime-sliced backtests for candidate filters and attach calibration delta report.",
                priority="medium",
            )
        )

    if current_profile == "prod" and prod_zero_streak_alert:
        likely_causes.append("Prod profile has repeated zero-result runs and requires immediate fallback policy.")
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="pm_planner_agent",
                owner_module="planner policy / fallback mode",
                title="Harden fallback watchlist governance in prod",
                hypothesis="Fallback watchlist is now active but still needs explicit risk caps and expiry rules.",
                requested_change="Enforce fallback expiry in outcome-tracking jobs and alert when stale fallback rows accumulate.",
                priority="high",
            )
        )

    health = outcome_health if isinstance(outcome_health, dict) else {}
    outcomes_total = _safe_int(health.get("outcomes_total", 0))
    expired_total = _safe_int(health.get("expired", 0))
    fallback_total = _safe_int(health.get("fallback_total", 0))
    fallback_expired = _safe_int(health.get("fallback_expired", 0))
    expired_rate = _safe_float(health.get("expired_rate", 0.0))
    fallback_expired_rate = _safe_float(health.get("fallback_expired_rate", 0.0))
    expired_min = _safe_int(os.getenv("AG_POSTMORTEM_EXPIRED_MIN", "5"))
    expired_rate_min = _safe_float(os.getenv("AG_POSTMORTEM_EXPIRED_RATE_MIN", "0.25"))
    fallback_expired_min = _safe_int(os.getenv("AG_POSTMORTEM_FALLBACK_EXPIRED_MIN", "2"))
    should_ticket_expiry = (
        (outcomes_total > 0 and expired_total >= max(1, expired_min) and expired_rate >= max(0.0, expired_rate_min))
        or (fallback_expired >= max(1, fallback_expired_min))
    )
    if should_ticket_expiry:
        delta = health.get("delta_vs_prev_run", {})
        if not isinstance(delta, dict):
            delta = {}
        delta_expired = _safe_int(delta.get("expired", 0))
        delta_pending = _safe_int(delta.get("pending", 0))
        delta_text = ""
        if delta:
            delta_text = f" (delta_vs_prev: pending={delta_pending:+d}, expired={delta_expired:+d})"
        likely_causes.append(
            "Stale pending/expired outcomes are accumulating, indicating weak closure policy and degraded feedback loop."
            + delta_text
        )
        tickets.append(
            create_improvement_ticket(
                run_id=context.run_id,
                owner_agent="pm_planner_agent",
                owner_module="outcome updater + planner fallback policy",
                title="Reduce stale outcome backlog and fallback expiry",
                hypothesis=(
                    "High expired ratio suggests horizon policy and follow-up cadence are misaligned with current execution flow."
                ),
                requested_change=(
                    "Tighten fallback admission/horizon rules, enforce daily closure review, and escalate stale backlog thresholds."
                    + (
                        f" Delta evidence: pending={delta_pending:+d}, expired={delta_expired:+d}, "
                        f"base_run={delta.get('base_run_id')}."
                        if delta
                        else ""
                    )
                ),
                priority="high" if fallback_expired > 0 else "medium",
            )
        )

    if candidate_count > 0 and weak_ratio < 0.5:
        summary = "No critical pre-outcome failure. Postmortem generated as a preventive trace."
    else:
        summary = "Pre-outcome quality risk detected. See tickets for agent-specific fixes."

    report = build_postmortem_report(
        context=context,
        scope="pre_outcome_quality_gate",
        failure_summary=summary,
        likely_causes=likely_causes,
        evidence_refs=[
            "scanner_handoff.json",
            "aggregation_handoff.json",
            "backtest_handoff.json",
            "market_context_handoff.json",
            "planner_handoff.json",
            "realized_outcomes.json",
            "outcome_health.json",
            "profile_diagnostics.json",
        ],
        decision_refs=["planner_handoff.decisions"],
        tickets=tickets,
    )
    return report, [t.to_dict() for t in tickets]


def _safe_int(value: Any) -> int:
    try:
        return int(value)
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


def _detail_feature_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    out: Dict[str, Any] = {}
    for key in ("market_gate", "scanner_timeframe_profile", "kr_universe_role"):
        if _detail_has_feature(row.get(key)):
            out[key] = row.get(key)
    if "tech_score" in row:
        out["tech_score"] = round(_safe_float(row.get("tech_score")), 2)
    if "whale_score" in row:
        out["whale_score"] = round(_safe_float(row.get("whale_score")), 2)
    if "volume_ratio" in row:
        volume_ratio = _safe_float(row.get("volume_ratio"))
        out["volume_ratio"] = round(volume_ratio, 3)
        volume_confirmed = bool(row.get("volume_confirmed", False))
        out["volume_confirmed"] = volume_confirmed
        out["volume"] = row.get("volume") or f"{'✅' if volume_confirmed else '⚠️'} x{volume_ratio:.2f}"
    elif row.get("volume") is not None:
        out["volume"] = row.get("volume")
    return out


def _detail_has_feature(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "?", "nan", "none", "null", "unknown", "na", "n/a"}
    try:
        result = float(value)
        return result == result
    except Exception:
        return True


def _normalize_profile(value: Any) -> str:
    raw = str(value or "unknown").strip().lower()
    return raw or "unknown"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _load_source_run_outcome_meta(source_run_id: str, ticker: str) -> Dict[str, Any]:
    run_id = str(source_run_id or "").strip()
    symbol = str(ticker or "").strip().upper()
    if not run_id or not symbol:
        return {}
    try:
        memory = MemoryManager()
        payload = _load_json(memory.shared_working(run_id) / "realized_outcomes.json")
        outcomes = payload.get("outcomes", [])
        if isinstance(outcomes, list):
            for row in outcomes:
                if isinstance(row, dict) and str(row.get("ticker") or "").strip().upper() == symbol:
                    return row
    except Exception:
        pass
    return {}


def _enrich_tracking_meta(meta: Dict[str, Any], *, ticker: str, source_run_id: str | None = None) -> Dict[str, Any]:
    enriched = dict(meta or {})
    symbol = str(ticker or enriched.get("ticker") or "").strip().upper()
    if not symbol:
        return enriched
    enriched["ticker"] = symbol

    if source_run_id:
        source_meta = _load_source_run_outcome_meta(source_run_id, symbol)
        for key in [
            "phase25_variant",
            "phase25_prob",
            "phase25_shadow_variant",
            "phase25_shadow_prob",
            "phase25_recommended_threshold",
            "expected_edge_score",
            "expected_return_1d_pct",
            "expected_return_3d_pct",
            "market_gate",
            "scanner_timeframe_profile",
            "kr_universe_role",
            "explosive_eligible",
            "explosive_gate_reasons",
            "primary_theme",
            "theme_source",
            "theme_inference_status",
            "secondary_themes",
            "theme_routing_path",
            "scan_mode",
            "strategy_family",
        ]:
            if enriched.get(key) in (None, "", []):
                value = source_meta.get(key)
                if value not in (None, "", []):
                    enriched[key] = value

    stock_meta = get_stock_theme_record(symbol)
    if isinstance(stock_meta, dict) and stock_meta:
        if not str(enriched.get("stock_name") or "").strip():
            enriched["stock_name"] = str(stock_meta.get("stock_name") or "").strip()
        if str(enriched.get("primary_theme") or "").strip() in {"", "None"} or enriched.get("primary_theme") is None:
            enriched["primary_theme"] = str(stock_meta.get("primary_theme") or "unclassified")
        if str(enriched.get("theme_source") or "").strip() in {"", "None"} or enriched.get("theme_source") is None:
            enriched["theme_source"] = "stock_master"
        if str(enriched.get("theme_inference_status") or "").strip() in {"", "None"} or enriched.get("theme_inference_status") is None:
            enriched["theme_inference_status"] = str(stock_meta.get("theme_inference_status") or "blank")
        if enriched.get("secondary_themes") in (None, ""):
            enriched["secondary_themes"] = list(stock_meta.get("secondary_themes") or [])
        if enriched.get("secondary_themes") is None:
            enriched["secondary_themes"] = []
    if enriched.get("secondary_themes") is None:
        enriched["secondary_themes"] = []
    return enriched


def _top_reason_from_counts(counts: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(counts, dict) or not counts:
        return {}
    best_reason = ""
    best_count = -1
    for reason, value in counts.items():
        c = _safe_int(value)
        if c > best_count:
            best_reason = str(reason)
            best_count = c
    if best_count < 0:
        return {}
    return {"reason": best_reason, "count": best_count}


def _extract_scanner_meta(scanner_payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = scanner_payload.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    input_meta = summary.get("input_meta", {})
    if not isinstance(input_meta, dict):
        input_meta = {}
    diagnostics = summary.get("diagnostics", input_meta.get("diagnostics", {}))
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    reject_counts = diagnostics.get("reject_reason_counts", {})
    if not isinstance(reject_counts, dict):
        reject_counts = {}
    current_profile = _normalize_profile(summary.get("execution_profile", input_meta.get("execution_profile", "unknown")))
    return {
        "current_profile": current_profile,
        "total_scans": _safe_int(summary.get("total_scans", input_meta.get("total_scans", 0))),
        "reject_reason_counts": reject_counts,
        "top_reject_reason": _top_reason_from_counts(reject_counts),
    }


def _build_profile_diagnostics(
    *,
    context: RunContext,
    scanner_payload: Dict[str, Any],
    candidate_count: int,
    history_limit: int = 80,
) -> Dict[str, Any]:
    memory = MemoryManager()
    artifacts_root = memory.root / "artifacts"
    scanner_meta = _extract_scanner_meta(scanner_payload)
    current_profile = str(scanner_meta.get("current_profile", "unknown"))
    current_total_scans = _safe_int(scanner_meta.get("total_scans", 0))

    profile_stats: Dict[str, Dict[str, Any]] = {}
    recent_prod_pass_flags: List[bool] = []
    runs_seen = 0
    runs_considered = 0

    if artifacts_root.exists():
        run_dirs = [p for p in artifacts_root.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
        run_dirs = sorted(run_dirs, key=lambda p: p.name)
        if history_limit > 0:
            run_dirs = run_dirs[-history_limit:]
        for run_dir in run_dirs:
            runs_seen += 1
            summary_path = run_dir / "scan_pipeline_summary.json"
            if not summary_path.exists():
                continue
            payload = _load_json(summary_path)
            run_market = str(payload.get("market", "")).upper()
            if run_market != str(context.market).upper():
                continue
            runs_considered += 1

            profile = _normalize_profile(payload.get("execution_profile", "unknown"))
            total_scans = _safe_int(payload.get("total_scans", 0))
            result_count = _safe_int(payload.get("result_count", 0))
            filtered_count = _safe_int(payload.get("filtered_count", 0))
            reject_counts = payload.get("reject_reason_counts", {})
            if not isinstance(reject_counts, dict):
                reject_counts = {}

            bucket = profile_stats.setdefault(
                profile,
                {
                    "runs": 0,
                    "total_scans": 0,
                    "result_count": 0,
                    "filtered_count": 0,
                    "zero_result_runs": 0,
                    "reject_reason_counts": {},
                },
            )
            bucket["runs"] += 1
            bucket["total_scans"] += total_scans
            bucket["result_count"] += result_count
            bucket["filtered_count"] += filtered_count
            if total_scans > 0 and result_count == 0:
                bucket["zero_result_runs"] += 1
            rr = bucket["reject_reason_counts"]
            for reason, value in reject_counts.items():
                rr[str(reason)] = _safe_int(rr.get(str(reason), 0)) + _safe_int(value)
            if profile == "prod" and total_scans > 0:
                recent_prod_pass_flags.append(result_count > 0)

    if current_profile == "prod" and current_total_scans > 0:
        recent_prod_pass_flags.append(candidate_count > 0)
    if len(recent_prod_pass_flags) > 10:
        recent_prod_pass_flags = recent_prod_pass_flags[-10:]

    prod_zero_streak = 0
    for passed in reversed(recent_prod_pass_flags):
        if passed:
            break
        prod_zero_streak += 1
    if current_profile != "prod":
        prod_zero_streak = 0

    summary_by_profile: Dict[str, Any] = {}
    for profile, bucket in profile_stats.items():
        scans = _safe_int(bucket.get("total_scans", 0))
        results = _safe_int(bucket.get("result_count", 0))
        filtered = _safe_int(bucket.get("filtered_count", 0))
        summary_by_profile[profile] = {
            "runs": _safe_int(bucket.get("runs", 0)),
            "total_scans": scans,
            "result_count": results,
            "filtered_count": filtered,
            "zero_result_runs": _safe_int(bucket.get("zero_result_runs", 0)),
            "weighted_pass_rate_pct": round((results / scans * 100.0), 2) if scans > 0 else 0.0,
            "weighted_filtered_rate_pct": round((filtered / scans * 100.0), 2) if scans > 0 else 0.0,
            "top_reject_reason": _top_reason_from_counts(bucket.get("reject_reason_counts", {})),
        }

    prod_summary = summary_by_profile.get("prod", {})
    dev_summary = summary_by_profile.get("dev", {})
    prod_rate = float(prod_summary.get("weighted_pass_rate_pct", 0.0) or 0.0)
    dev_rate = float(dev_summary.get("weighted_pass_rate_pct", 0.0) or 0.0)
    prod_runs = _safe_int(prod_summary.get("runs", 0))
    dev_runs = _safe_int(dev_summary.get("runs", 0))

    prod_dev_gap = (
        current_profile == "prod"
        and current_total_scans > 0
        and candidate_count == 0
        and prod_runs >= 1
        and dev_runs >= 1
        and prod_rate <= 10.0
        and dev_rate >= 40.0
    )
    prod_zero_streak_alert = (
        current_profile == "prod"
        and current_total_scans > 0
        and candidate_count == 0
        and prod_zero_streak >= 3
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": context.run_id,
        "market": context.market,
        "current_profile": current_profile,
        "current_total_scans": current_total_scans,
        "current_result_count": _safe_int(candidate_count),
        "current_top_reject_reason": scanner_meta.get("top_reject_reason", {}),
        "history_window_runs_seen": runs_seen,
        "history_window_runs_considered": runs_considered,
        "history_limit": int(history_limit),
        "profile_summary": summary_by_profile,
        "flags": {
            "prod_dev_gap": bool(prod_dev_gap),
            "prod_zero_streak_alert": bool(prod_zero_streak_alert),
            "prod_zero_streak": int(prod_zero_streak),
        },
    }


def _collect_recent_outcome_health(
    *,
    context: RunContext,
    exclude_run_id: str,
    history_limit: int = 120,
) -> Dict[str, Any]:
    memory = MemoryManager()
    shared_root = memory.root / "shared_working"
    if not shared_root.exists():
        return {
            "window_runs": 0,
            "runs_with_outcomes": 0,
            "outcomes_total": 0,
            "pending": 0,
            "resolved": 0,
            "expired": 0,
            "expired_rate": 0.0,
            "fallback_total": 0,
            "fallback_pending": 0,
            "fallback_resolved": 0,
            "fallback_expired": 0,
            "fallback_expired_rate": 0.0,
        }

    run_dirs = [p for p in shared_root.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
    run_dirs = sorted(run_dirs, key=lambda p: p.name, reverse=True)
    if history_limit > 0:
        run_dirs = run_dirs[:history_limit]

    runs_considered = 0
    runs_with_outcomes = 0
    outcomes_total = 0
    pending = 0
    resolved = 0
    expired = 0
    fallback_total = 0
    fallback_pending = 0
    fallback_resolved = 0
    fallback_expired = 0

    for run_dir in run_dirs:
        run_id = run_dir.name
        if run_id == exclude_run_id:
            continue

        market_value = ""
        scanner_payload = _load_json(run_dir / "scanner_handoff.json")
        if scanner_payload:
            rc = scanner_payload.get("run_context", {})
            if isinstance(rc, dict):
                market_value = str(rc.get("market", "")).upper()
        if not market_value:
            profile_payload = _load_json(run_dir / "profile_diagnostics.json")
            if profile_payload:
                market_value = str(profile_payload.get("market", "")).upper()
        if market_value and market_value != str(context.market).upper():
            continue

        runs_considered += 1
        payload = _load_json(run_dir / "realized_outcomes.json")
        rows = payload.get("outcomes", []) if isinstance(payload.get("outcomes"), list) else []
        if not rows:
            continue
        runs_with_outcomes += 1

        for row in rows:
            if not isinstance(row, dict):
                continue
            outcomes_total += 1
            status = str(row.get("status", "")).upper()
            decision = str(row.get("decision", "")).upper()
            if status == "RESOLVED":
                resolved += 1
            elif status == "EXPIRED":
                expired += 1
            elif status == "PENDING":
                pending += 1

            if decision == "FALLBACK_WATCHLIST":
                fallback_total += 1
                if status == "RESOLVED":
                    fallback_resolved += 1
                elif status == "EXPIRED":
                    fallback_expired += 1
                elif status == "PENDING":
                    fallback_pending += 1

    expired_rate = (expired / outcomes_total) if outcomes_total > 0 else 0.0
    fallback_expired_rate = (fallback_expired / fallback_total) if fallback_total > 0 else 0.0
    return {
        "window_runs": int(runs_considered),
        "runs_with_outcomes": int(runs_with_outcomes),
        "outcomes_total": int(outcomes_total),
        "pending": int(pending),
        "resolved": int(resolved),
        "expired": int(expired),
        "expired_rate": round(expired_rate, 4),
        "fallback_total": int(fallback_total),
        "fallback_pending": int(fallback_pending),
        "fallback_resolved": int(fallback_resolved),
        "fallback_expired": int(fallback_expired),
        "fallback_expired_rate": round(fallback_expired_rate, 4),
    }


def _compute_outcome_health_delta(
    *,
    memory: MemoryManager,
    current_row: Dict[str, Any],
) -> Dict[str, Any]:
    path = memory.long_term("outcome_health") / "outcome_health.jsonl"
    if not path.exists() or not isinstance(current_row, dict):
        return {}

    cur_market = str(current_row.get("market", "")).upper()
    cur_run_id = str(current_row.get("run_id", ""))
    previous: Dict[str, Any] = {}
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        for line in reversed(lines):
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            run_id = str(row.get("run_id", ""))
            market = str(row.get("market", "")).upper()
            if run_id == cur_run_id:
                continue
            if cur_market and market and market != cur_market:
                continue
            previous = row
            break
    except Exception:
        return {}

    if not previous:
        return {}

    def _d(key: str) -> int:
        return _safe_int(current_row.get(key, 0)) - _safe_int(previous.get(key, 0))

    return {
        "base_run_id": previous.get("run_id"),
        "base_generated_at": previous.get("generated_at"),
        "outcomes_total": _d("outcomes_total"),
        "pending": _d("pending"),
        "resolved": _d("resolved"),
        "expired": _d("expired"),
        "fallback_total": _d("fallback_total"),
        "fallback_pending": _d("fallback_pending"),
        "fallback_resolved": _d("fallback_resolved"),
        "fallback_expired": _d("fallback_expired"),
    }


def _pick_ticker_from_row(row: Dict[str, Any]) -> str:
    return str(
        row.get("티커")
        or row.get("Ticker")
        or row.get("ticker")
        or row.get("symbol")
        or row.get("Symbol")
        or ""
    ).strip()


def _collect_fallback_watchlist_from_recent_dev(
    *,
    context: RunContext,
    exclude_run_id: str,
    max_watchlist: int = 10,
    history_limit: int = 120,
) -> Dict[str, Any]:
    memory = MemoryManager()
    artifacts_root = memory.root / "artifacts"
    if not artifacts_root.exists():
        return {"watchlist": [], "source_run_id": None, "considered_dev_runs": 0}

    run_dirs = [p for p in artifacts_root.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
    run_dirs = sorted(run_dirs, key=lambda p: p.name, reverse=True)
    if history_limit > 0:
        run_dirs = run_dirs[:history_limit]

    watchlist: List[str] = []
    seen: set[str] = set()
    source_run_id: str | None = None
    considered_dev_runs = 0

    for run_dir in run_dirs:
        run_id = run_dir.name
        if run_id == exclude_run_id:
            continue
        summary_path = run_dir / "scan_pipeline_summary.json"
        if not summary_path.exists():
            continue
        summary = _load_json(summary_path)
        if str(summary.get("market", "")).upper() != str(context.market).upper():
            continue
        if _normalize_profile(summary.get("execution_profile", "unknown")) != "dev":
            continue
        if _safe_int(summary.get("result_count", 0)) <= 0:
            continue
        considered_dev_runs += 1

        raw_path = run_dir / "raw_scan_results.json"
        raw = _load_json(raw_path) if raw_path.exists() else {}
        rows = raw.get("results_sorted", [])
        if not isinstance(rows, list):
            rows = []
        if not rows:
            scan_result = raw.get("scan_result", {})
            if isinstance(scan_result, dict) and isinstance(scan_result.get("results"), list):
                rows = scan_result.get("results", [])

        for row in rows:
            if not isinstance(row, dict):
                continue
            ticker = _pick_ticker_from_row(row)
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            watchlist.append(ticker)
            if len(watchlist) >= max_watchlist:
                break

        if watchlist:
            source_run_id = run_id
            break

    return {
        "watchlist": watchlist[:max_watchlist],
        "source_run_id": source_run_id,
        "considered_dev_runs": considered_dev_runs,
    }


def _build_fallback_watchlist_meta(
    *,
    watchlist: List[str],
    source_run_id: str | None,
    ticker_names: Dict[str, str] | None = None,
    horizon_days: int = 3,
) -> List[Dict[str, Any]]:
    generated_at = datetime.now(timezone.utc)
    expires_at = generated_at + timedelta(days=max(1, int(horizon_days)))
    meta: List[Dict[str, Any]] = []
    for ticker in watchlist:
        meta.append(
            _enrich_tracking_meta(
                {
                    "ticker": str(ticker),
                    "stock_name": str((ticker_names or {}).get(str(ticker), "") or ""),
                    "source_profile": "dev",
                    "source_run_id": source_run_id,
                    "risk_label": "HIGH_RISK_FALLBACK",
                    "generated_at": generated_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "horizon_days": int(horizon_days),
                    "reason": "prod_zero_streak_alert",
                },
                ticker=str(ticker),
                source_run_id=source_run_id,
            )
        )
    return meta


def _resolve_ticker_names(*, market: str, tickers: List[str]) -> Dict[str, str]:
    unique = [str(t).strip().upper() for t in tickers if str(t).strip()]
    if not unique:
        return {}
    try:
        market_map = QuantStrategy.get_market_tickers(market)
        if not isinstance(market_map, dict):
            return {}
        normalized = {str(k).strip().upper(): str(v) for k, v in market_map.items() if str(k).strip()}
        return {ticker: normalized.get(ticker, "") for ticker in unique}
    except Exception:
        return {}


def _collect_near_miss_watchlist_from_scanner_payload(
    scanner_payload: Dict[str, Any],
    context: RunContext,
    max_watchlist: int = 8,
) -> Dict[str, Any]:
    summary = scanner_payload.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    diagnostics = summary.get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    reject_by_symbol = diagnostics.get("reject_reasons_by_symbol", {})
    if not isinstance(reject_by_symbol, dict):
        reject_by_symbol = {}
    detail_by_symbol = diagnostics.get("reject_details_by_symbol", {})
    if not isinstance(detail_by_symbol, dict):
        detail_by_symbol = {}

    ticker_names = _resolve_ticker_names(market=context.market, tickers=list(reject_by_symbol.keys()))
    scored: List[Tuple[float, str, Dict[str, Any]]] = []
    for ticker, reason_value in reject_by_symbol.items():
        reason = str(reason_value or "").strip().upper()
        if reason in {"LIQUIDITY_FILTER_FAIL", "FETCH_DATA_FAIL", "MISSING_ANTIGRAV_SCORE"}:
            continue
        detail_rows = detail_by_symbol.get(ticker, [])
        if not isinstance(detail_rows, list) or not detail_rows:
            detail_rows = [{}]
        for row in detail_rows:
            if not isinstance(row, dict):
                row = {}
            alpha_score = _safe_float(row.get("alpha_score", 0.0))
            conviction_score = _safe_float(row.get("conviction_score", 0.0))
            prob_5 = _safe_float(row.get("prob_5", 0.0))
            prob_clean = _safe_float(row.get("prob_clean", 0.0))
            tier_sort = _safe_int(row.get("tier_sort", 3))
            real_trend = str(row.get("real_trend", ""))
            entry_reference_price = _resolve_detail_price(row)
            score = alpha_score * 1.0 + conviction_score * 0.7 + prob_5 * 0.2 + prob_clean * 0.15 - tier_sort * 4.0
            if real_trend == "UP":
                score += 4.0
            elif real_trend == "DOWN":
                score -= 4.0
            scored.append(
                (
                    float(score),
                    str(ticker),
                    {
                        "ticker": str(ticker),
                        "stock_name": str(ticker_names.get(str(ticker).upper(), "") or ""),
                        "reason": reason.lower(),
                        "alpha_score": round(alpha_score, 2),
                        **_detail_feature_fields(row),
                        "conviction_score": round(conviction_score, 2),
                        "prob_5": round(prob_5, 2),
                        "prob_clean": round(prob_clean, 2),
                        "tier_sort": int(tier_sort),
                        "real_trend": real_trend,
                        "entry_reference_price": entry_reference_price,
                        "decision_score": round(score, 2),
                    },
                )
            )

    scored.sort(key=lambda item: item[0], reverse=True)
    watchlist: List[str] = []
    watchlist_meta: List[Dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc)
    expires_at = generated_at + timedelta(days=2)
    for _, ticker, meta in scored:
        if ticker in watchlist:
            continue
        alpha_score = _safe_float(meta.get("alpha_score", 0.0))
        conviction_score = _safe_float(meta.get("conviction_score", 0.0))
        if alpha_score < 38.0 and conviction_score < 45.0:
            continue
        watchlist.append(ticker)
        watchlist_meta.append(
            _enrich_tracking_meta(
                {
                    "ticker": ticker,
                    "stock_name": str(meta.get("stock_name", "") or ""),
                    "source_profile": "current_run_near_miss",
                    "risk_label": "WATCHLIST_ONLY",
                    "generated_at": generated_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "horizon_days": 2,
                    "reason": "near_miss_watchlist",
                    "reject_reason": meta.get("reason"),
                    "market_gate": meta.get("market_gate"),
                    "scanner_timeframe_profile": meta.get("scanner_timeframe_profile"),
                    "kr_universe_role": meta.get("kr_universe_role"),
                    "alpha_score": meta.get("alpha_score"),
                    "tech_score": meta.get("tech_score"),
                    "conviction_score": meta.get("conviction_score"),
                    "prob_5": meta.get("prob_5"),
                    "prob_clean": meta.get("prob_clean"),
                    "whale_score": meta.get("whale_score"),
                    "volume": meta.get("volume"),
                    "volume_ratio": meta.get("volume_ratio"),
                    "volume_confirmed": meta.get("volume_confirmed"),
                    "real_trend": meta.get("real_trend"),
                    "entry_reference_price": meta.get("entry_reference_price"),
                    "decision_score": meta.get("decision_score"),
                },
                ticker=ticker,
            )
        )
        if len(watchlist) >= max_watchlist:
            break
    return {
        "watchlist": watchlist,
        "watchlist_meta": watchlist_meta,
        "considered_filtered_symbols": len(reject_by_symbol),
    }


def _build_relative_zero_pass_decisions(
    *,
    watchlist_meta: List[Dict[str, Any]],
    max_decisions: int = 5,
) -> List[PlannerDecision]:
    decisions: List[PlannerDecision] = []
    seen: set[str] = set()
    for meta in watchlist_meta:
        if not isinstance(meta, dict):
            continue
        ticker = str(meta.get("ticker") or "").strip()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        alpha_score = _safe_float(meta.get("alpha_score"))
        conviction_score = _safe_float(meta.get("conviction_score"))
        decision_score = _safe_float(meta.get("decision_score"))
        decision = "WATCHLIST" if max(alpha_score, conviction_score, decision_score) >= 50.0 else "OBSERVE"
        confidence = max(0.35, min(0.72, conviction_score / 100.0 if conviction_score > 0 else decision_score / 180.0))
        reject_reason = str(meta.get("reject_reason") or "").strip().lower()
        market_gate = str(meta.get("market_gate") or "").strip().upper()
        rationale = [
            "relative_zero_pass_promotion",
            "strict_filter_candidates_empty",
            f"source_profile:{meta.get('source_profile') or 'current_run_near_miss'}",
        ]
        if reject_reason:
            rationale.append(f"reject_reason:{reject_reason}")
        if market_gate:
            rationale.append(f"market_gate:{market_gate}")
        loss_risk_market = "KOSPI" if ticker.endswith(".KS") else "KOSDAQ" if ticker.endswith(".KQ") else ""
        loss_risk = compute_loss_risk_features(
            market_subtype=loss_risk_market,
            alpha_score=meta.get("alpha_score"),
            tech_score=meta.get("tech_score"),
            whale_score=meta.get("whale_score"),
            ml_prob=meta.get("prob_5"),
            prob_clean=meta.get("prob_clean"),
            volume_ratio=meta.get("volume_ratio"),
            volume_confirmed=meta.get("volume_confirmed"),
            position=meta.get("position"),
            tier=meta.get("tier"),
            trend=meta.get("real_trend"),
        )
        loss_risk_score = float(loss_risk.get("loss_risk_score", 0.0) or 0.0)
        loss_risk_flags = [
            key.upper()
            for key, value in loss_risk.items()
            if key.endswith("_risk") and float(value or 0.0) >= 1.0
        ]
        if loss_risk_score > 0:
            rationale.append(f"loss_risk_score={loss_risk_score:.1f}")
        if loss_risk_flags:
            rationale.append("loss_risk_flags=" + ",".join(loss_risk_flags[:4]))
        thresholds = get_loss_risk_gate_thresholds(loss_risk_market)
        if loss_risk_score >= thresholds["hard"]:
            decision = "OBSERVE"
        elif loss_risk_score >= thresholds["soft"]:
            decision = get_loss_risk_soft_cap_decision(loss_risk_market)
        decisions.append(
            PlannerDecision(
                ticker=ticker,
                stock_name=str(meta.get("stock_name") or ""),
                priority_rank=len(decisions) + 1,
                decision=decision,
                confidence=round(float(confidence), 3),
                alpha_score=alpha_score if meta.get("alpha_score") not in (None, "") else None,
                tech_score=_safe_float(meta.get("tech_score")) if meta.get("tech_score") not in (None, "") else None,
                conviction_score=conviction_score if meta.get("conviction_score") not in (None, "") else None,
                decision_score=decision_score if meta.get("decision_score") not in (None, "") else None,
                whale_score=_safe_float(meta.get("whale_score")) if meta.get("whale_score") not in (None, "") else None,
                volume=meta.get("volume"),
                volume_ratio=_safe_float(meta.get("volume_ratio")) if meta.get("volume_ratio") not in (None, "") else None,
                volume_confirmed=bool(meta.get("volume_confirmed")) if meta.get("volume_confirmed") is not None else None,
                entry_reference_price=meta.get("entry_reference_price"),
                prob_5=meta.get("prob_5"),
                prob_clean=meta.get("prob_clean"),
                real_trend=str(meta.get("real_trend") or ""),
                strategy_family=str(meta.get("strategy_family") or "KR_CORE"),
                scan_mode=str(meta.get("scan_mode") or "SWING"),
                market_gate=market_gate,
                scanner_timeframe_profile=str(meta.get("scanner_timeframe_profile") or ""),
                kr_universe_role=str(meta.get("kr_universe_role") or ""),
                target_horizon_days=max(1, _safe_int(meta.get("horizon_days", 2))),
                primary_theme=str(meta.get("primary_theme") or ""),
                theme_source=str(meta.get("theme_source") or ""),
                theme_inference_status=str(meta.get("theme_inference_status") or ""),
                secondary_themes=[
                    str(x) for x in (meta.get("secondary_themes") or []) if str(x).strip()
                ] if isinstance(meta.get("secondary_themes"), list) else [],
                theme_routing_path=str(meta.get("theme_routing_path") or ""),
                theme_risk=[
                    "ZERO_STRICT_PASS_RELATIVE_CANDIDATE",
                    f"REJECT_REASON_{reject_reason.upper()}" if reject_reason else "REJECT_REASON_UNKNOWN",
                ] + loss_risk_flags,
                rationale=rationale,
                evidence_refs=[
                    "scanner_handoff.json",
                    "planner_handoff.watchlist_meta",
                    "realized_outcomes.json",
                ],
                warnings=[
                    WarningItem(
                        code="RELATIVE_ZERO_PASS_PROMOTION",
                        message="Strict scanner filters produced no decisions; this candidate was promoted from real current-run near-miss evidence.",
                        severity="warning",
                    )
                ],
                realized_outcome_ref=f"realized_outcomes.json#{ticker}",
            )
        )
        if len(decisions) >= max_decisions:
            break
    return decisions


def _collect_exception_leaders_from_scanner_payload(
    *,
    scanner_payload: Dict[str, Any],
    context: RunContext,
    max_watchlist: int = 6,
) -> Dict[str, Any]:
    summary = scanner_payload.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    diagnostics = summary.get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    reject_by_symbol = diagnostics.get("reject_reasons_by_symbol", {})
    if not isinstance(reject_by_symbol, dict):
        reject_by_symbol = {}
    detail_by_symbol = diagnostics.get("reject_details_by_symbol", {})
    if not isinstance(detail_by_symbol, dict):
        detail_by_symbol = {}

    market_gate = str((summary.get("input_meta", {}) or {}).get("market_gate", {}).get("gate", "") or summary.get("market_gate", {}).get("gate", "") or "")
    regime = resolve_profile_regime(market_gate)
    ticker_names = _resolve_ticker_names(market=context.market, tickers=list(reject_by_symbol.keys()))

    scored: List[Tuple[float, str, Dict[str, Any]]] = []
    skipped_missing_features = 0
    skipped_hard_loss_risk = 0
    skipped_missing_feature_examples: List[Dict[str, Any]] = []
    for ticker_raw, reason_value in reject_by_symbol.items():
        ticker = str(ticker_raw or "").strip().upper()
        reason = str(reason_value or "").strip().upper()
        if not ticker or reason in {"LIQUIDITY_FILTER_FAIL", "FETCH_DATA_FAIL", "MISSING_ANTIGRAV_SCORE"}:
            continue
        detail_rows = detail_by_symbol.get(ticker, [])
        if not isinstance(detail_rows, list) or not detail_rows:
            detail_rows = [{}]
        detail = detail_rows[0] if isinstance(detail_rows[0], dict) else {}
        required_detail = {
            "alpha_score": detail.get("alpha_score"),
            "tech_score": detail.get("tech_score"),
            "whale_score": detail.get("whale_score"),
            "volume_ratio": detail.get("volume_ratio"),
            "prob_5": detail.get("prob_5"),
            "prob_clean": detail.get("prob_clean"),
            "real_trend": detail.get("real_trend"),
            "tier_sort": detail.get("tier_sort"),
        }
        missing_detail = [key for key, value in required_detail.items() if not _detail_has_feature(value)]
        if missing_detail:
            skipped_missing_features += 1
            if len(skipped_missing_feature_examples) < 8:
                skipped_missing_feature_examples.append(
                    {
                        "ticker": ticker,
                        "reject_reason": reason.lower(),
                        "missing_fields": missing_detail,
                    }
                )
            continue

        market = resolve_profile_market(context.market, ticker)
        profile = get_ticker_profile(ticker=ticker, market_type=market, market_gate=regime)
        overlay = compute_profile_adjustment(profile)
        alpha_score = _safe_float(detail.get("alpha_score", 0.0))
        conviction_score = _safe_float(detail.get("conviction_score", 0.0))
        prob_5 = _safe_float(detail.get("prob_5", 0.0))
        prob_clean = _safe_float(detail.get("prob_clean", 0.0))
        real_trend = str(detail.get("real_trend", "") or "").upper()
        tier_sort = _safe_int(detail.get("tier_sort", 3))
        entry_reference_price = _resolve_detail_price(detail)

        exception_score = 0.0
        if str(overlay.get("policy", "NONE")) == "POSITIVE":
            exception_score += 30.0 + _safe_float(overlay.get("score_adjustment", 0.0))
            if profile:
                if _safe_float(profile.get("win_5d_pct", 0.0)) >= 65.0:
                    exception_score += 8.0
                if _safe_float(profile.get("avg_5d_pct", 0.0)) >= 8.0:
                    exception_score += 8.0
        if alpha_score >= 55.0:
            exception_score += 18.0
        elif alpha_score >= 45.0:
            exception_score += 10.0
        if conviction_score >= 65.0:
            exception_score += 12.0
        elif conviction_score >= 58.0:
            exception_score += 6.0
        if prob_5 >= 35.0:
            exception_score += 6.0
        if prob_clean >= 25.0:
            exception_score += 5.0
        if real_trend == "UP":
            exception_score += 8.0
        elif real_trend == "NEUTRAL":
            exception_score += 2.0
        if reason == "KR_HARD_FILTER_FAIL" and alpha_score >= 45.0:
            exception_score += 8.0
        if reason == "PRECISION_GATE_T3_LOW_ML_SUPPORT" and conviction_score >= 58.0:
            exception_score += 8.0
        if reason in {"KR_SIGNAL_WINDOW_FAIL", "KR_BASELINE_FILTER_FAIL"}:
            exception_score -= 6.0

        if exception_score < 28.0:
            continue

        loss_risk_market = resolve_profile_market(context.market, ticker)
        loss_risk = compute_loss_risk_features(
            market_subtype=loss_risk_market,
            alpha_score=alpha_score,
            tech_score=detail.get("tech_score"),
            whale_score=detail.get("whale_score"),
            ml_prob=prob_5,
            prob_clean=prob_clean,
            volume_ratio=detail.get("volume_ratio"),
            volume_confirmed=detail.get("volume_confirmed"),
            position=detail.get("position"),
            tier=detail.get("tier"),
            trend=real_trend,
        )
        loss_risk_score = float(loss_risk.get("loss_risk_score", 0.0) or 0.0)
        if loss_risk_score >= float(get_loss_risk_gate_thresholds(loss_risk_market).get("hard", 65.0)):
            skipped_hard_loss_risk += 1
            continue

        scored.append(
            (
                float(exception_score),
                ticker,
                {
                    "ticker": ticker,
                    "stock_name": str(ticker_names.get(ticker, "") or ""),
                    "source_profile": "exception_leader",
                    "risk_label": "EXCEPTION_LEADER",
                    "reason": "exception_leader_watchlist",
                    "reject_reason": reason.lower(),
                    "exception_score": round(exception_score, 1),
                    "alpha_score": round(alpha_score, 2),
                    **_detail_feature_fields(detail),
                    "conviction_score": round(conviction_score, 2),
                    "prob_5": round(prob_5, 2),
                    "prob_clean": round(prob_clean, 2),
                    "real_trend": real_trend,
                    "tier_sort": int(tier_sort),
                    "profile_policy": str(overlay.get("policy", "NONE")),
                    "profile_adjustment": _safe_float(overlay.get("score_adjustment", 0.0)),
                    "profile_confidence": _safe_float(overlay.get("confidence", 0.0)),
                    "profile_signals": _safe_int((profile or {}).get("signals", 0)),
                    "profile_win_5d_pct": _safe_float((profile or {}).get("win_5d_pct", 0.0)),
                    "profile_avg_5d_pct": _safe_float((profile or {}).get("avg_5d_pct", 0.0)),
                    "loss_risk_score": round(loss_risk_score, 3),
                    "market_gate": str(market_gate).upper(),
                    "regime": regime,
                    "entry_reference_price": entry_reference_price,
                },
            )
        )

    scored.sort(key=lambda item: item[0], reverse=True)
    generated_at = datetime.now(timezone.utc)
    expires_at = generated_at + timedelta(days=3)
    watchlist: List[str] = []
    watchlist_meta: List[Dict[str, Any]] = []
    for _, ticker, meta in scored:
        if ticker in watchlist:
            continue
        meta["generated_at"] = generated_at.isoformat()
        meta["expires_at"] = expires_at.isoformat()
        meta["horizon_days"] = 3
        watchlist.append(ticker)
        watchlist_meta.append(_enrich_tracking_meta(meta, ticker=ticker))
        if len(watchlist) >= max_watchlist:
            break
    return {
        "watchlist": watchlist,
        "watchlist_meta": watchlist_meta,
        "considered_filtered_symbols": len(reject_by_symbol),
        "skipped_missing_features": skipped_missing_features,
        "skipped_hard_loss_risk": skipped_hard_loss_risk,
        "skipped_missing_feature_examples": skipped_missing_feature_examples,
    }


def run_legacy_orchestration(
    scanner_handoff_path: str,
    emit_postmortem: bool = True,
) -> Dict[str, str]:
    """Generate all downstream 5-agent handoffs from a legacy scanner handoff.

    This bridge is additive and does not modify core scanner/model behavior.
    """

    scanner_path = Path(scanner_handoff_path)
    scanner_payload = read_json(scanner_path)
    run_id_hint = scanner_path.parent.name
    context = _parse_run_context(scanner_payload, run_id_hint=run_id_hint)
    memory = MemoryManager()
    run_dir = memory.shared_working(context.run_id)
    scanner_out_path = write_json(run_dir / "scanner_handoff.json", scanner_payload)

    candidates = scanner_payload.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []

    aggregation_handoff, agg_metrics = build_aggregation_handoff(context, candidates)
    backtest_handoff = build_backtest_handoff(
        context=context,
        candidates=candidates,
        weak_ratio=float(agg_metrics.get("weak_ratio", 1.0)),
    )
    market_handoff = build_market_context_handoff(context)
    planner_handoff = build_planner_handoff(
        context=context,
        candidates=candidates,
        weak_ratio=float(agg_metrics.get("weak_ratio", 1.0)),
    )
    profile_diagnostics = _build_profile_diagnostics(
        context=context,
        scanner_payload=scanner_payload,
        candidate_count=int(agg_metrics.get("candidate_count", 0.0)),
    )

    flags = profile_diagnostics.get("flags", {})
    if not isinstance(flags, dict):
        flags = {}
    should_apply_fallback = (
        _normalize_profile(profile_diagnostics.get("current_profile", "unknown")) == "prod"
        and bool(flags.get("prod_zero_streak_alert", False))
        and len(getattr(planner_handoff, "decisions", []) or []) == 0
    )
    if should_apply_fallback:
        fb = _collect_fallback_watchlist_from_recent_dev(
            context=context,
            exclude_run_id=context.run_id,
            max_watchlist=10,
        )
        fb_watch = fb.get("watchlist", [])
        if isinstance(fb_watch, list) and fb_watch:
            planner_handoff.watchlist = [str(x) for x in fb_watch[:10]]
            ticker_names = _resolve_ticker_names(market=context.market, tickers=planner_handoff.watchlist)
            planner_handoff.watchlist_meta = _build_fallback_watchlist_meta(
                watchlist=planner_handoff.watchlist,
                source_run_id=str(fb.get("source_run_id")) if fb.get("source_run_id") else None,
                ticker_names=ticker_names,
                horizon_days=3,
            )
            planner_handoff.global_warnings.append(
                WarningItem(
                    code="FALLBACK_WATCHLIST_ENABLED",
                    message=(
                        f"Prod zero-result streak detected. Applied fallback watchlist from dev baseline "
                        f"(source_run={fb.get('source_run_id')})."
                    ),
                    severity="warning",
                )
            )
            profile_diagnostics["fallback_watchlist"] = {
                "applied": True,
                "source_profile": "dev",
                "source_run_id": fb.get("source_run_id"),
                "tickers": planner_handoff.watchlist,
                "watchlist_meta": planner_handoff.watchlist_meta,
                "considered_dev_runs": int(fb.get("considered_dev_runs", 0) or 0),
            }
        else:
            planner_handoff.global_warnings.append(
                WarningItem(
                    code="FALLBACK_WATCHLIST_UNAVAILABLE",
                    message="Prod zero-result streak detected but no recent dev baseline watchlist was available.",
                    severity="warning",
                )
            )
            profile_diagnostics["fallback_watchlist"] = {
                "applied": False,
                "source_profile": "dev",
                "source_run_id": None,
                "tickers": [],
                "watchlist_meta": [],
                "considered_dev_runs": int(fb.get("considered_dev_runs", 0) or 0),
            }

    should_apply_near_miss_watchlist = (
        len(getattr(planner_handoff, "decisions", []) or []) == 0
        and len(getattr(planner_handoff, "watchlist", []) or []) == 0
    )
    if should_apply_near_miss_watchlist:
        nm = _collect_near_miss_watchlist_from_scanner_payload(scanner_payload=scanner_payload, context=context, max_watchlist=8)
        nm_watch = nm.get("watchlist", [])
        if isinstance(nm_watch, list) and nm_watch:
            planner_handoff.watchlist = [str(x) for x in nm_watch[:8]]
            planner_handoff.watchlist_meta = list(nm.get("watchlist_meta", []))[:8]
            planner_handoff.decisions = _build_relative_zero_pass_decisions(
                watchlist_meta=planner_handoff.watchlist_meta,
                max_decisions=5,
            )
            planner_handoff.global_warnings.append(
                WarningItem(
                    code="NEAR_MISS_RELATIVE_CANDIDATES_ENABLED",
                    message="Planner generated ranked relative candidates from current-run near-miss evidence after zero strict-pass decisions.",
                    severity="warning",
                )
            )
            profile_diagnostics["near_miss_watchlist"] = {
                "applied": True,
                "tickers": planner_handoff.watchlist,
                "watchlist_meta": planner_handoff.watchlist_meta,
                "promoted_decisions": [d.ticker for d in planner_handoff.decisions],
                "considered_filtered_symbols": int(nm.get("considered_filtered_symbols", 0) or 0),
            }
        else:
            profile_diagnostics["near_miss_watchlist"] = {
                "applied": False,
                "tickers": [],
                "watchlist_meta": [],
                "considered_filtered_symbols": int(nm.get("considered_filtered_symbols", 0) or 0),
            }

    exception_leaders = _collect_exception_leaders_from_scanner_payload(
        scanner_payload=scanner_payload,
        context=context,
        max_watchlist=6,
    )
    ex_watch = exception_leaders.get("watchlist", [])
    ex_meta = exception_leaders.get("watchlist_meta", [])
    if isinstance(ex_watch, list) and ex_watch:
        current_watch = list(getattr(planner_handoff, "watchlist", []) or [])
        current_meta = list(getattr(planner_handoff, "watchlist_meta", []) or [])
        seen = {str(x) for x in current_watch}
        for row in ex_meta:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").strip()
            if not ticker or ticker in seen:
                continue
            current_watch.append(ticker)
            current_meta.append(row)
            seen.add(ticker)
        planner_handoff.watchlist = current_watch[:20]
        planner_handoff.watchlist_meta = current_meta[:20]
        planner_handoff.global_warnings.append(
            WarningItem(
                code="EXCEPTION_LEADERS_ENABLED",
                message="Planner attached bear-market exception leaders from rejected candidates for follow-up tracking.",
                severity="warning",
            )
        )
        profile_diagnostics["exception_leaders"] = {
            "applied": True,
            "tickers": [str(x) for x in ex_watch[:6]],
            "watchlist_meta": ex_meta[:6],
            "considered_filtered_symbols": int(exception_leaders.get("considered_filtered_symbols", 0) or 0),
            "skipped_missing_features": int(exception_leaders.get("skipped_missing_features", 0) or 0),
            "skipped_missing_feature_examples": list(exception_leaders.get("skipped_missing_feature_examples", []) or []),
        }
    else:
        profile_diagnostics["exception_leaders"] = {
            "applied": False,
            "tickers": [],
            "watchlist_meta": [],
            "considered_filtered_symbols": int(exception_leaders.get("considered_filtered_symbols", 0) or 0),
            "skipped_missing_features": int(exception_leaders.get("skipped_missing_features", 0) or 0),
            "skipped_missing_feature_examples": list(exception_leaders.get("skipped_missing_feature_examples", []) or []),
        }

    watchlist_only_policy = _resolve_watchlist_only_policy(
        context=context,
        scanner_payload=scanner_payload,
    )
    watchlist_only_applied = _apply_watchlist_only_mode(
        context=context,
        planner_handoff=planner_handoff,
        policy_summary=watchlist_only_policy,
        max_watchlist=10,
    )
    profile_diagnostics["watchlist_only_policy"] = {
        "applied": bool(watchlist_only_applied),
        "market_gate": watchlist_only_policy.get("market_gate"),
        "mode": watchlist_only_policy.get("mode"),
        "policy": watchlist_only_policy.get("policy", {}),
        "market_policy_avoid_count": int(watchlist_only_policy.get("market_policy_avoid_count", 0) or 0),
        "total_rejects": int(watchlist_only_policy.get("total_rejects", 0) or 0),
        "watchlist_count": len(getattr(planner_handoff, "watchlist", []) or []),
    }

    realized_outcomes = _build_realized_outcomes_placeholder(context=context, planner_handoff=planner_handoff, scanner_payload=scanner_payload)
    outcome_health = _collect_recent_outcome_health(
        context=context,
        exclude_run_id=context.run_id,
        history_limit=120,
    )
    outcome_health_row = {
        "run_id": context.run_id,
        "market": context.market,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **outcome_health,
    }
    delta_vs_prev_run = _compute_outcome_health_delta(memory=memory, current_row=outcome_health_row)
    if delta_vs_prev_run:
        outcome_health_row["delta_vs_prev_run"] = delta_vs_prev_run

    out_paths = {
        "scanner_handoff": str(scanner_out_path),
        "aggregation_handoff": str(write_json(run_dir / "aggregation_handoff.json", aggregation_handoff.to_dict())),
        "backtest_handoff": str(write_json(run_dir / "backtest_handoff.json", backtest_handoff.to_dict())),
        "market_context_handoff": str(write_json(run_dir / "market_context_handoff.json", market_handoff.to_dict())),
        "planner_handoff": str(write_json(run_dir / "planner_handoff.json", planner_handoff.to_dict())),
        "realized_outcomes": str(write_json(run_dir / "realized_outcomes.json", realized_outcomes)),
        "outcome_health": str(write_json(run_dir / "outcome_health.json", outcome_health_row)),
    }

    postmortem_dict: Dict[str, Any] = {}
    tickets_payload: List[Dict[str, Any]] = []
    out_paths["profile_diagnostics"] = str(write_json(run_dir / "profile_diagnostics.json", profile_diagnostics))
    if emit_postmortem:
        market_warning_codes = [w.code for w in market_handoff.warnings]
        report, tickets = _build_postmortem(
            context=context,
            candidate_count=int(agg_metrics.get("candidate_count", 0.0)),
            weak_ratio=float(agg_metrics.get("weak_ratio", 1.0)),
            market_context_warning_codes=market_warning_codes,
            profile_diagnostics=profile_diagnostics,
            outcome_health=outcome_health_row,
        )
        postmortem_dict = report.to_dict()
        tickets_payload = tickets
        out_paths["postmortem_report"] = str(write_json(run_dir / "postmortem_report.json", postmortem_dict))
        out_paths["improvement_tickets"] = str(write_json(run_dir / "improvement_tickets.json", {"tickets": tickets_payload}))

    manifest = {
        "run_id": context.run_id,
        "market": context.market,
        "strategy_version": context.strategy_version,
        "model_version": context.model_version,
        "code_version": context.code_version,
        "files": out_paths,
    }
    out_paths["run_manifest"] = str(write_json(run_dir / "run_manifest.json", manifest))

    # Long-term memory append (non-blocking for runtime stability).
    try:
        log_run_summary(
            memory=memory,
            run_id=context.run_id,
            market=context.market,
            strategy_version=context.strategy_version,
            model_version=context.model_version,
            code_version=context.code_version,
            artifact_refs=out_paths,
        )
        if postmortem_dict:
            log_postmortem(
                memory=memory,
                row={
                    "run_id": context.run_id,
                    "market": context.market,
                    "scope": postmortem_dict.get("scope"),
                    "failure_summary": postmortem_dict.get("failure_summary"),
                    "likely_causes": postmortem_dict.get("likely_causes", []),
                    "produced_at": postmortem_dict.get("produced_at"),
                    "evidence_refs": postmortem_dict.get("evidence_refs", []),
                },
            )
        if profile_diagnostics:
            log_profile_diagnostics(
                memory=memory,
                row={
                    "run_id": context.run_id,
                    "market": context.market,
                    "current_profile": profile_diagnostics.get("current_profile"),
                    "current_total_scans": profile_diagnostics.get("current_total_scans"),
                    "current_result_count": profile_diagnostics.get("current_result_count"),
                    "current_top_reject_reason": profile_diagnostics.get("current_top_reject_reason", {}),
                    "profile_summary": profile_diagnostics.get("profile_summary", {}),
                    "flags": profile_diagnostics.get("flags", {}),
                    "fallback_watchlist": profile_diagnostics.get("fallback_watchlist", {}),
                    "near_miss_watchlist": profile_diagnostics.get("near_miss_watchlist", {}),
                    "watchlist_only_policy": profile_diagnostics.get("watchlist_only_policy", {}),
                    "generated_at": profile_diagnostics.get("generated_at"),
                },
            )
        if outcome_health_row:
            log_outcome_health(memory=memory, row=outcome_health_row)
        if tickets_payload:
            log_improvement_tickets(memory=memory, tickets=tickets_payload)
    except Exception:
        pass

    # Optional DB sink append (non-blocking, additive).
    try:
        from modules import db_manager as _db_manager

        db = _db_manager.DBManager()
        db.save_agent_run_summary(
            {
                "run_id": context.run_id,
                "market": context.market,
                "strategy_version": context.strategy_version,
                "model_version": context.model_version,
                "code_version": context.code_version,
                "artifact_refs": out_paths,
            }
        )
        db.save_agent_realized_outcomes(
            run_id=context.run_id,
            outcomes=realized_outcomes.get("outcomes", []),
        )
        db.upsert_scan_archive_outcomes(
            run_id=context.run_id,
            market=context.market,
            outcomes=realized_outcomes.get("outcomes", []),
        )
        if profile_diagnostics:
            db.save_agent_profile_diagnostics(
                {
                    "run_id": context.run_id,
                    "market": context.market,
                    "current_profile": profile_diagnostics.get("current_profile"),
                    "current_total_scans": profile_diagnostics.get("current_total_scans"),
                    "current_result_count": profile_diagnostics.get("current_result_count"),
                    "current_top_reject_reason": profile_diagnostics.get("current_top_reject_reason", {}),
                    "profile_summary": profile_diagnostics.get("profile_summary", {}),
                    "flags": profile_diagnostics.get("flags", {}),
                    "fallback_watchlist": profile_diagnostics.get("fallback_watchlist", {}),
                    "generated_at": profile_diagnostics.get("generated_at"),
                }
            )
        if outcome_health_row:
            db.save_agent_outcome_health(outcome_health_row)
        if postmortem_dict:
            db.save_agent_postmortem(
                {
                    "run_id": context.run_id,
                    "market": context.market,
                    "scope": postmortem_dict.get("scope"),
                    "failure_summary": postmortem_dict.get("failure_summary"),
                    "likely_causes": postmortem_dict.get("likely_causes", []),
                    "evidence_refs": postmortem_dict.get("evidence_refs", []),
                    "produced_at": postmortem_dict.get("produced_at"),
                }
            )
        if tickets_payload:
            db.save_agent_improvement_tickets(tickets_payload)
    except Exception:
        pass

    return out_paths


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run legacy scanner handoff orchestration.")
    parser.add_argument("scanner_handoff_path", type=str, help="Path to scanner_handoff.json")
    parser.add_argument(
        "--no-postmortem",
        action="store_true",
        help="Skip postmortem and ticket generation.",
    )
    args = parser.parse_args()

    result = run_legacy_orchestration(
        scanner_handoff_path=args.scanner_handoff_path,
        emit_postmortem=not args.no_postmortem,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
