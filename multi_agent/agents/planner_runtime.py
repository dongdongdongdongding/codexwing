from __future__ import annotations

from typing import Any, Dict, List

from multi_agent.contracts.types import PlannerDecision, PlannerHandoff, RunContext, WarningItem
from multi_agent.agents.kr_quant_reranker import (
    compute_kr_basket_priority,
    compute_kr_quant_rerank,
    resolve_kr_active_lane,
)


def _decision_from_score(score: float) -> str:
    if score >= 80:
        return "PRIORITY_WATCHLIST"
    if score >= 65:
        return "WATCHLIST"
    if score >= 55:
        return "OBSERVE"
    return "AVOID"


def _decision_rank(decision: str) -> int:
    table = {
        "AVOID": 0,
        "OBSERVE": 1,
        "WATCHLIST": 2,
        "PRIORITY_WATCHLIST": 3,
    }
    return table.get(str(decision or "").upper(), 0)


def _decision_from_rank(rank: int) -> str:
    table = {
        0: "AVOID",
        1: "OBSERVE",
        2: "WATCHLIST",
        3: "PRIORITY_WATCHLIST",
    }
    return table.get(int(rank), "AVOID")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _apply_kosdaq_intraday_gate(
    *,
    decision: str,
    run_market: str,
    scan_mode: str,
    phase25_variant: str,
    raw_phase25_prob: float | None,
    recommended_threshold: float | None,
    rationale: List[str],
    theme_risk: List[str],
) -> str:
    if not (
        run_market == "KOSDAQ"
        and scan_mode.upper() == "INTRADAY"
        and phase25_variant.startswith("phase25_kr_intraday")
        and raw_phase25_prob is not None
        and recommended_threshold is not None
    ):
        return decision
    gap = recommended_threshold - raw_phase25_prob
    original_decision = decision
    if gap >= 10.0:
        decision = "AVOID"
        theme_risk.append("PHASE25_BELOW_THRESHOLD_HARD")
    elif gap >= 5.0:
        decision = _decision_from_rank(max(0, _decision_rank(decision) - 1))
        theme_risk.append("PHASE25_BELOW_THRESHOLD_SOFT")
    if decision != original_decision:
        rationale.append(f"phase25_gate={raw_phase25_prob:.1f}<{recommended_threshold:.1f}")
    return decision


def _apply_kosdaq_swing_gate(
    *,
    decision: str,
    run_market: str,
    scan_mode: str,
    phase25_variant: str,
    raw_phase25_prob: float | None,
    recommended_threshold: float | None,
    prob_clean: Any,
    real_trend: str,
    rationale: List[str],
    theme_risk: List[str],
) -> str:
    if not (
        run_market == "KOSDAQ"
        and scan_mode.upper() == "SWING"
        and phase25_variant.startswith("phase25_kr_swing")
        and raw_phase25_prob is not None
        and recommended_threshold is not None
    ):
        return decision

    original_decision = decision
    gap = recommended_threshold - raw_phase25_prob
    try:
        clean_prob = float(prob_clean) if prob_clean not in (None, "") else None
    except Exception:
        clean_prob = None

    if gap >= 8.0:
        decision = "AVOID"
        theme_risk.append("PHASE25_SWING_BELOW_THRESHOLD_HARD")
    elif gap >= 4.0:
        decision = _decision_from_rank(max(0, _decision_rank(decision) - 1))
        theme_risk.append("PHASE25_SWING_BELOW_THRESHOLD_SOFT")

    if decision != "AVOID" and str(real_trend or "").upper() != "UP":
        decision = _decision_from_rank(max(0, _decision_rank(decision) - 1))
        theme_risk.append("KOSDAQ_SWING_TREND_GUARD")

    if decision != "AVOID" and clean_prob is not None and clean_prob < 28.0:
        decision = _decision_from_rank(max(0, _decision_rank(decision) - 1))
        theme_risk.append("KOSDAQ_SWING_CLEAN_PROB_GUARD")

    if decision != original_decision:
        rationale.append(f"phase25_swing_gate={raw_phase25_prob:.1f}<{recommended_threshold:.1f}")
    return decision


def _apply_kr_market_mode_quality_gate(
    *,
    decision: str,
    run_market: str,
    scan_mode: str,
    score: float,
    phase25_variant: str,
    raw_phase25_prob: float | None,
    recommended_threshold: float | None,
    prob_clean: Any,
    real_trend: str,
    theme_routing_path: str,
    rationale: List[str],
    theme_risk: List[str],
) -> str:
    market = str(run_market or "").upper()
    mode = str(scan_mode or "").upper()
    variant = str(phase25_variant or "")
    route = str(theme_routing_path or "").lower()
    trend_up = str(real_trend or "").upper() == "UP"

    try:
        clean_prob = float(prob_clean) if prob_clean not in (None, "") else None
    except Exception:
        clean_prob = None

    def _demote_to(rank_target: int, risk_code: str, reason: str) -> str:
        original = decision
        new_decision = _decision_from_rank(min(_decision_rank(original), rank_target))
        if new_decision != original:
            theme_risk.append(risk_code)
            rationale.append(reason)
        return new_decision

    # KOSDAQ swing is under probation until true-buy quality recovers.
    if market == "KOSDAQ" and mode == "SWING":
        high_conviction_exception = (
            variant.startswith("phase25_kr_swing")
            and raw_phase25_prob is not None
            and recommended_threshold is not None
            and raw_phase25_prob >= max(recommended_threshold + 12.0, 37.0)
            and (clean_prob is not None and clean_prob >= 38.0)
            and trend_up
            and route == "theme_routed"
            and float(score) >= 88.0
        )
        if not high_conviction_exception:
            return _demote_to(
                1,
                "KOSDAQ_SWING_PROBATION",
                "market_mode_probation=KOSDAQ_SWING",
            )
        if _decision_rank(decision) > 2:
            theme_risk.append("KOSDAQ_SWING_PRIORITY_CAP")
            rationale.append("priority_cap=KOSDAQ_SWING")
            return "WATCHLIST"
        return decision

    # KOSPI swing has not earned priority status yet; only very strong model-backed setups may pass.
    if market == "KOSPI" and mode == "SWING" and _decision_rank(decision) >= 3:
        allow_priority = (
            variant.startswith("phase25_kr_swing")
            and raw_phase25_prob is not None
            and recommended_threshold is not None
            and raw_phase25_prob >= max(recommended_threshold + 10.0, 35.0)
            and (clean_prob is not None and clean_prob >= 35.0)
            and trend_up
            and float(score) >= 86.0
        )
        if not allow_priority:
            return _demote_to(
                2,
                "KOSPI_SWING_PRIORITY_GUARD",
                "priority_guard=KOSPI_SWING",
            )

    if market == "KOSDAQ" and mode == "INTRADAY":
        if _decision_rank(decision) >= 3:
            allow_priority = (
                variant.startswith("phase25_kr_intraday")
                and raw_phase25_prob is not None
                and recommended_threshold is not None
                and raw_phase25_prob >= max(recommended_threshold + 12.0, 72.0)
                and (clean_prob is not None and clean_prob >= 35.0)
                and trend_up
                and float(score) >= 88.0
            )
            if not allow_priority:
                return _demote_to(
                    2,
                    "KOSDAQ_INTRADAY_PRIORITY_GUARD",
                    "priority_guard=KOSDAQ_INTRADAY",
                )
        if _decision_rank(decision) >= 2:
            keep_watch = (
                variant.startswith("phase25_kr_intraday")
                and raw_phase25_prob is not None
                and recommended_threshold is not None
                and raw_phase25_prob >= max(recommended_threshold, 60.0)
                and (clean_prob is None or clean_prob >= 28.0)
            )
            if not keep_watch:
                return _demote_to(
                    1,
                    "KOSDAQ_INTRADAY_WATCH_GUARD",
                    "watch_guard=KOSDAQ_INTRADAY",
                )

    if market == "KOSPI" and mode == "INTRADAY" and _decision_rank(decision) >= 3:
        allow_priority = (
            variant.startswith("phase25_kr_intraday")
            and raw_phase25_prob is not None
            and recommended_threshold is not None
            and raw_phase25_prob >= max(recommended_threshold + 5.0, 65.0)
            and (clean_prob is not None and clean_prob >= 32.0)
            and trend_up
            and float(score) >= 84.0
        )
        if not allow_priority:
            return _demote_to(
                2,
                "KOSPI_INTRADAY_PRIORITY_GUARD",
                "priority_guard=KOSPI_INTRADAY",
            )

    return decision


def _apply_expected_edge_gate(
    *,
    decision: str,
    run_market: str,
    scan_mode: str,
    expected_return_1d_pct: float | None,
    expected_return_3d_pct: float | None,
    score: float,
    real_trend: str,
    rationale: List[str],
    theme_risk: List[str],
) -> str:
    market = str(run_market or "").upper()
    mode = str(scan_mode or "").upper()
    trend_up = str(real_trend or "").upper() == "UP"
    if expected_return_1d_pct is None or expected_return_3d_pct is None:
        return decision

    rank = _decision_rank(decision)
    min_1d = 0.8
    min_3d = 2.5
    priority_1d = 1.8
    priority_3d = 4.5

    if market == "KOSDAQ":
        min_1d, min_3d = 1.1, 3.2
        priority_1d, priority_3d = 2.1, 5.3
    if mode == "SWING":
        min_1d += 0.1
        min_3d += 0.8
        priority_1d += 0.2
        priority_3d += 1.0

    if rank >= 3 and (
        float(expected_return_1d_pct) < priority_1d
        or float(expected_return_3d_pct) < priority_3d
        or not trend_up
        or float(score) < 84.0
    ):
        theme_risk.append("EXPECTED_EDGE_PRIORITY_GUARD")
        rationale.append(
            f"expected_edge_priority_guard={float(expected_return_1d_pct):.2f}/{float(expected_return_3d_pct):.2f}"
        )
        return "WATCHLIST"

    if rank >= 2 and (
        float(expected_return_1d_pct) < min_1d
        or float(expected_return_3d_pct) < min_3d
    ):
        theme_risk.append("EXPECTED_EDGE_WATCH_GUARD")
        rationale.append(
            f"expected_edge_watch_guard={float(expected_return_1d_pct):.2f}/{float(expected_return_3d_pct):.2f}"
        )
        return _decision_from_rank(min(rank, 1))

    return decision


def _to_warning_items(raw_warnings: Any) -> List[WarningItem]:
    if not isinstance(raw_warnings, list):
        return []
    items: List[WarningItem] = []
    for row in raw_warnings:
        if not isinstance(row, dict):
            continue
        items.append(
            WarningItem(
                code=str(row.get("code") or "UNKNOWN"),
                message=str(row.get("message") or ""),
                severity=str(row.get("severity") or "info"),
            )
        )
    return items


def build_planner_handoff(
    context: RunContext,
    candidates: List[Dict[str, Any]],
    weak_ratio: float,
) -> PlannerHandoff:
    run_market = str(getattr(context, "market", "") or "").upper()
    ranked_candidates: List[Dict[str, Any]] = []
    for cand in candidates:
        enriched = dict(cand)
        enriched["_quant_rerank"] = compute_kr_quant_rerank(enriched, run_market)
        ranked_candidates.append(enriched)
    active_lane = resolve_kr_active_lane(ranked_candidates, run_market)
    for cand in ranked_candidates:
        cand["_basket_priority"] = compute_kr_basket_priority(cand, run_market, active_lane)

    def _order_key(row: Dict[str, Any]) -> tuple[float, float, float]:
        basket_meta = row.get("_basket_priority", {}) if isinstance(row.get("_basket_priority"), dict) else {}
        quant_meta = row.get("_quant_rerank", {}) if isinstance(row.get("_quant_rerank"), dict) else {}
        basket_score = float(basket_meta.get("score", quant_meta.get("score", row.get("score", 0.0))) or 0.0)
        quant_score = float(quant_meta.get("score", row.get("score", 0.0)) or 0.0)
        scanner_score = float(row.get("score", 0.0) or 0.0)
        return (basket_score, quant_score, scanner_score)

    ordered = sorted(
        ranked_candidates,
        key=_order_key,
        reverse=True,
    )
    decisions: List[PlannerDecision] = []
    watchlist: List[str] = []
    watchlist_meta: List[Dict[str, Any]] = []
    avoid_list: List[str] = []

    for idx, cand in enumerate(ordered, start=1):
        ticker = str(cand.get("ticker") or "UNKNOWN")
        feature_snapshot = cand.get("feature_snapshot", {}) if isinstance(cand.get("feature_snapshot"), dict) else {}
        theme_context = cand.get("theme_context", {}) if isinstance(cand.get("theme_context"), dict) else {}
        leader_metrics = cand.get("leader_metrics", {}) if isinstance(cand.get("leader_metrics"), dict) else {}
        if not theme_context and isinstance(feature_snapshot.get("theme_context"), dict):
            theme_context = feature_snapshot.get("theme_context", {})
        if not leader_metrics and isinstance(feature_snapshot.get("leader_metrics"), dict):
            leader_metrics = feature_snapshot.get("leader_metrics", {})
        stock_name = str(cand.get("stock_name") or feature_snapshot.get("stock_name") or "")
        scanner_score = float(cand.get("score", 0.0) or 0.0)
        quant_meta = cand.get("_quant_rerank", {}) if isinstance(cand.get("_quant_rerank"), dict) else {}
        basket_meta = cand.get("_basket_priority", {}) if isinstance(cand.get("_basket_priority"), dict) else {}
        score = float(quant_meta.get("score", scanner_score) or scanner_score)
        quant_score_1d = float(quant_meta.get("score_1d", score) or score)
        quant_score_3d = float(quant_meta.get("score_3d", score) or score)
        quant_lane = str(quant_meta.get("lane", "raw") or "raw")
        scanner_timeframe_profile = str(
            quant_meta.get("scanner_timeframe_profile")
            or feature_snapshot.get("scanner_timeframe_profile")
            or cand.get("scanner_timeframe_profile")
            or ""
        )
        kr_universe_role = str(
            quant_meta.get("kr_universe_role")
            or feature_snapshot.get("kr_universe_role")
            or cand.get("kr_universe_role")
            or ""
        )
        explosive_eligible = bool(quant_meta.get("explosive_eligible", False))
        explosive_gate_reasons = [
            str(x) for x in list(quant_meta.get("explosive_gate_reasons", []) or []) if str(x).strip()
        ]
        continuation_eligible = bool(quant_meta.get("continuation_eligible", False))
        continuation_enabled = bool(quant_meta.get("continuation_enabled", False))
        continuation_prob_3d = float(quant_meta.get("continuation_prob_3d", 50.0) or 50.0)
        continuation_evidence = int(quant_meta.get("continuation_evidence", 0) or 0)
        continuation_gate_reasons = [str(x) for x in list(quant_meta.get("continuation_gate_reasons", []) or []) if str(x).strip()]
        basket_priority_score = float(basket_meta.get("score", score) or score)
        alpha_score = feature_snapshot.get("alpha_score")
        decision_score = feature_snapshot.get("decision_score", score)
        entry_reference_price = feature_snapshot.get("entry_reference_price") or feature_snapshot.get("현재가") or feature_snapshot.get("current_price")
        prob_5 = feature_snapshot.get("prob_5", feature_snapshot.get("_prob_5", feature_snapshot.get("ml_prob")))
        prob_clean = feature_snapshot.get("prob_clean", feature_snapshot.get("_prob_clean"))
        real_trend = str(feature_snapshot.get("real_trend") or feature_snapshot.get("trend") or "")
        strategy_family = str(feature_snapshot.get("strategy_family") or "")
        scan_mode = str(feature_snapshot.get("scan_mode") or "")
        phase25_variant = str(feature_snapshot.get("phase25_variant") or "")
        phase25_prob = feature_snapshot.get("phase25_prob")
        phase25_shadow_variant = str(feature_snapshot.get("phase25_shadow_variant") or "")
        phase25_shadow_prob = feature_snapshot.get("phase25_shadow_prob")
        phase25_recommended_threshold = feature_snapshot.get("phase25_recommended_threshold")
        expected_edge_score = feature_snapshot.get("expected_edge_score")
        expected_return_1d_pct = feature_snapshot.get("expected_return_1d_pct")
        expected_return_3d_pct = feature_snapshot.get("expected_return_3d_pct")
        reasons = cand.get("reasons", []) if isinstance(cand.get("reasons"), list) else []
        decision = _decision_from_score(score)
        confidence = _clamp((0.45 + (score / 200.0) - (weak_ratio * 0.1)), 0.05, 0.95)
        rationale = [
            f"scanner_score={scanner_score:.1f}",
            f"quant_priority_score={score:.1f}",
            f"quant_lane={quant_lane}",
            f"quant_score_1d={quant_score_1d:.1f}",
            f"quant_score_3d={quant_score_3d:.1f}",
            f"basket_priority_score={basket_priority_score:.1f}",
            f"active_lane={active_lane}",
            f"rank={idx}",
        ] + [str(x) for x in reasons[:3]]
        if kr_universe_role:
            rationale.append(f"kr_universe_role={kr_universe_role}")
        if scanner_timeframe_profile:
            rationale.append(f"scanner_timeframe_profile={scanner_timeframe_profile}")
        rationale.append(f"explosive_eligible={str(explosive_eligible).lower()}")
        rationale.append(f"continuation_eligible={str(continuation_eligible).lower()}")
        rationale.append(f"continuation_enabled={str(continuation_enabled).lower()}")
        rationale.append(f"continuation_prob_3d={continuation_prob_3d:.1f}")
        rationale.append(f"continuation_evidence={continuation_evidence}")
        if quant_meta.get("reasons"):
            rationale.extend([f"quant_reason={str(x)}" for x in list(quant_meta.get("reasons", []))[:3]])
        lane_overlay_1d = quant_meta.get("lane_overlay_1d", {}) if isinstance(quant_meta.get("lane_overlay_1d"), dict) else {}
        lane_overlay_3d = quant_meta.get("lane_overlay_3d", {}) if isinstance(quant_meta.get("lane_overlay_3d"), dict) else {}
        if lane_overlay_1d.get("enabled"):
            rationale.append(
                f"lane_overlay_1d={str(lane_overlay_1d.get('segment') or '')}:{float(lane_overlay_1d.get('prob_up', 0.0) or 0.0):.1f}"
            )
        if lane_overlay_3d.get("enabled"):
            rationale.append(
                f"lane_overlay_3d={str(lane_overlay_3d.get('segment') or '')}:{float(lane_overlay_3d.get('prob_up', 0.0) or 0.0):.1f}"
            )
        if explosive_gate_reasons:
            rationale.extend([f"explosive_gate={str(x)}" for x in explosive_gate_reasons[:3]])
        if continuation_gate_reasons:
            rationale.extend([f"continuation_gate={str(x)}" for x in continuation_gate_reasons[:3]])
        theme_rationale: List[str] = []
        theme_risk: List[str] = []
        primary_theme = str(theme_context.get("primary_theme") or "").strip()
        theme_direction = str(theme_context.get("theme_direction") or "").upper()
        theme_strength = float(theme_context.get("theme_strength_score", 0.0) or 0.0)
        theme_rank = leader_metrics.get("theme_rank")
        if primary_theme and primary_theme.lower() != "unclassified":
            rationale.append(f"theme={primary_theme}")
            if theme_direction == "BENEFICIARY" and theme_strength >= 60:
                theme_rationale.append("THEME_BENEFICIARY_HIGH")
            elif theme_direction == "BENEFICIARY":
                theme_rationale.append("THEME_BENEFICIARY")
            elif theme_direction == "HEADWIND":
                theme_risk.append("THEME_HEADWIND")
            if theme_rank == 1:
                theme_rationale.append("THEME_LEADER_TOP1")
            elif theme_rank == 2:
                theme_rationale.append("THEME_LEADER_TOP2")

        try:
            raw_phase25_prob = float(phase25_prob) if phase25_prob not in (None, "") else None
        except Exception:
            raw_phase25_prob = None
        try:
            recommended_threshold = (
                float(phase25_recommended_threshold)
                if phase25_recommended_threshold not in (None, "")
                else None
            )
        except Exception:
            recommended_threshold = None

        decision = _apply_kosdaq_intraday_gate(
            decision=decision,
            run_market=run_market,
            scan_mode=scan_mode,
            phase25_variant=phase25_variant,
            raw_phase25_prob=raw_phase25_prob,
            recommended_threshold=recommended_threshold,
            rationale=rationale,
            theme_risk=theme_risk,
        )
        decision = _apply_kosdaq_swing_gate(
            decision=decision,
            run_market=run_market,
            scan_mode=scan_mode,
            phase25_variant=phase25_variant,
            raw_phase25_prob=raw_phase25_prob,
            recommended_threshold=recommended_threshold,
            prob_clean=prob_clean,
            real_trend=real_trend,
            rationale=rationale,
            theme_risk=theme_risk,
        )
        decision = _apply_kr_market_mode_quality_gate(
            decision=decision,
            run_market=run_market,
            scan_mode=scan_mode,
            score=score,
            phase25_variant=phase25_variant,
            raw_phase25_prob=raw_phase25_prob,
            recommended_threshold=recommended_threshold,
            prob_clean=prob_clean,
            real_trend=real_trend,
            theme_routing_path=str(cand.get("routing_path") or theme_context.get("routing_path") or ""),
            rationale=rationale,
            theme_risk=theme_risk,
        )
        decision = _apply_expected_edge_gate(
            decision=decision,
            run_market=run_market,
            scan_mode=scan_mode,
            expected_return_1d_pct=float(expected_return_1d_pct) if expected_return_1d_pct not in (None, "") else None,
            expected_return_3d_pct=float(expected_return_3d_pct) if expected_return_3d_pct not in (None, "") else None,
            score=score,
            real_trend=real_trend,
            rationale=rationale,
            theme_risk=theme_risk,
        )

        warning_items = _to_warning_items(cand.get("warnings"))
        decision_row = PlannerDecision(
            ticker=ticker,
            stock_name=stock_name,
            priority_rank=idx,
            decision=decision,
            confidence=round(confidence, 3),
            alpha_score=float(alpha_score) if alpha_score not in (None, "") else None,
            decision_score=float(decision_score) if decision_score not in (None, "") else round(score, 3),
            entry_reference_price=float(entry_reference_price) if entry_reference_price not in (None, "") else None,
            prob_5=float(prob_5) if prob_5 not in (None, "") else None,
            prob_clean=float(prob_clean) if prob_clean not in (None, "") else None,
            real_trend=real_trend,
            strategy_family=strategy_family,
            scan_mode=scan_mode,
            phase25_variant=phase25_variant,
            phase25_prob=raw_phase25_prob,
            phase25_shadow_variant=phase25_shadow_variant,
            phase25_shadow_prob=float(phase25_shadow_prob) if phase25_shadow_prob not in (None, "") else None,
            phase25_recommended_threshold=float(phase25_recommended_threshold) if phase25_recommended_threshold not in (None, "") else None,
            expected_edge_score=float(expected_edge_score) if expected_edge_score not in (None, "") else None,
            expected_return_1d_pct=float(expected_return_1d_pct) if expected_return_1d_pct not in (None, "") else None,
            expected_return_3d_pct=float(expected_return_3d_pct) if expected_return_3d_pct not in (None, "") else None,
            quant_priority_score=round(float(basket_priority_score), 3),
            quant_score_1d=round(float(quant_score_1d), 3),
            quant_score_3d=round(float(quant_score_3d), 3),
            selection_lane=quant_lane,
            target_horizon_days=1 if quant_lane == "1d" else 3,
            scanner_timeframe_profile=scanner_timeframe_profile,
            kr_universe_role=kr_universe_role,
            explosive_eligible=explosive_eligible,
            explosive_gate_reasons=explosive_gate_reasons,
            continuation_eligible=continuation_eligible,
            continuation_enabled=continuation_enabled,
            continuation_prob_3d=round(float(continuation_prob_3d), 4),
            continuation_evidence=continuation_evidence,
            continuation_gate_reasons=continuation_gate_reasons,
            primary_theme=primary_theme,
            theme_source=str(theme_context.get("theme_source") or ""),
            theme_inference_status=str(theme_context.get("theme_inference_status") or ""),
            secondary_themes=[
                str(x) for x in (theme_context.get("secondary_themes") or []) if str(x).strip()
            ] if isinstance(theme_context.get("secondary_themes"), list) else [],
            theme_routing_path=str(cand.get("routing_path") or theme_context.get("routing_path") or ""),
            theme_rationale=theme_rationale,
            theme_risk=theme_risk,
            rationale=rationale,
            evidence_refs=[
                "scanner_handoff.json",
                "aggregation_handoff.json",
                "backtest_handoff.json",
                "market_context_handoff.json",
            ],
            warnings=warning_items,
            realized_outcome_ref=f"realized_outcomes.json#{ticker}",
        )
        decisions.append(decision_row)

        if decision != "AVOID" and len(watchlist) < 20:
            watchlist.append(ticker)
            watchlist_meta.append(
                {
                    "ticker": ticker,
                    "stock_name": stock_name,
                    "decision": decision,
                    "decision_score": float(decision_score) if decision_score not in (None, "") else None,
                    "quant_priority_score": round(float(basket_priority_score), 3),
                    "quant_score_1d": round(float(quant_score_1d), 3),
                    "quant_score_3d": round(float(quant_score_3d), 3),
                    "selection_lane": quant_lane,
                    "active_lane": active_lane,
                    "target_horizon_days": 1 if quant_lane == "1d" else 3,
                    "scanner_timeframe_profile": scanner_timeframe_profile or None,
                    "kr_universe_role": kr_universe_role or None,
                    "explosive_eligible": explosive_eligible,
                    "explosive_gate_reasons": explosive_gate_reasons,
                    "continuation_eligible": continuation_eligible,
                    "continuation_enabled": continuation_enabled,
                    "continuation_prob_3d": round(float(continuation_prob_3d), 4),
                    "continuation_evidence": continuation_evidence,
                    "continuation_gate_reasons": continuation_gate_reasons,
                    "expected_return_1d_pct": float(expected_return_1d_pct) if expected_return_1d_pct not in (None, "") else None,
                    "expected_return_3d_pct": float(expected_return_3d_pct) if expected_return_3d_pct not in (None, "") else None,
                    "primary_theme": primary_theme or None,
                    "theme_routing_path": str(cand.get("routing_path") or theme_context.get("routing_path") or ""),
                    "reason": "planner_lane_watchlist",
                }
            )
        if decision == "AVOID":
            avoid_list.append(ticker)

    global_warnings: List[WarningItem] = []
    if not decisions:
        global_warnings.append(
            WarningItem(
                code="EMPTY_PLANNER_INPUT",
                message="Planner received no candidates from scanner handoff.",
                severity="error",
            )
        )
    if weak_ratio >= 0.5 and decisions:
        global_warnings.append(
            WarningItem(
                code="LOW_QUALITY_INPUT",
                message="Planner confidence reduced due to weak candidate ratio.",
                severity="warning",
            )
        )

    return PlannerHandoff(
        run_context=context,
        decisions=decisions,
        watchlist=watchlist,
        watchlist_meta=watchlist_meta,
        avoid_list=avoid_list,
        global_warnings=global_warnings,
    )
