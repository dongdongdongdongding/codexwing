from __future__ import annotations

from datetime import date
from typing import Any, Dict, List
from uuid import uuid4

from multi_agent.contracts.serialization import write_json
from multi_agent.contracts.types import RunContext, ScannerCandidate, ScannerHandoff, WarningItem
from multi_agent.storage.memory_layers import MemoryManager
from modules.theme_leader_ranker import assign_theme_ranks


def _pick_ticker(row: Dict[str, Any]) -> str:
    return str(row.get("티커") or row.get("Ticker") or row.get("ticker") or "UNKNOWN")


def _pick_score(row: Dict[str, Any]) -> float:
    try:
        if "Decision Score" in row and row["Decision Score"] is not None:
            return float(row["Decision Score"])
        if "Antigrav" in row and row["Antigrav"] is not None:
            return float(row["Antigrav"])
        if "alpha_score" in row and row["alpha_score"] is not None:
            return float(row["alpha_score"])
        if "score" in row and row["score"] is not None:
            return float(row["score"])
    except Exception:
        return 0.0
    return 0.0


def _extract_whale_num(row: Dict[str, Any]) -> float:
    whale = row.get("Whale") or row.get("수급") or row.get("whale_score")
    if whale is None:
        return 0.0


def _pick_numeric(row: Dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key not in row:
            continue
        value = row.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, str):
            cleaned = value.replace("%", "").replace(",", "").strip()
            if not cleaned:
                continue
            value = cleaned
        try:
            return float(value)
        except Exception:
            continue
    return None
    s = str(whale)
    digits = "".join(ch for ch in s if (ch.isdigit() or ch == "."))
    try:
        return float(digits) if digits else 0.0
    except Exception:
        return 0.0


def build_scanner_handoff_from_legacy_results(
    results: List[Dict[str, Any]],
    context: RunContext,
    source: str = "legacy_streamlit_scanner",
    summary_overrides: Dict[str, Any] | None = None,
) -> ScannerHandoff:
    """Build ScannerHandoff from legacy scanner row dictionaries."""

    candidates: List[ScannerCandidate] = []
    weak_count = 0
    for row in results:
        ticker = _pick_ticker(row)
        score = _pick_score(row)
        whale_score = _extract_whale_num(row)

        reasons: List[str] = []
        for key in ["전략", "Strategy", "급등예측", "Surge", "추세", "Trend", "시장맥락", "Context"]:
            value = row.get(key)
            if value not in (None, "", "-"):
                reasons.append(f"{key}: {value}")
        if not reasons:
            raw_reasons = row.get("reasons")
            if isinstance(raw_reasons, list):
                reasons = [str(item) for item in raw_reasons if str(item).strip()]

        warnings: List[WarningItem] = []
        if score < 55:
            weak_count += 1
            warnings.append(
                WarningItem(
                    code="LOW_DECISION_SCORE",
                    message=f"{ticker} has low decision score ({score:.1f}).",
                    severity="warning",
                )
            )

        feature_snapshot = {
            "stock_name": row.get("종목명") or row.get("Name") or row.get("name"),
            "antigrav": row.get("Antigrav"),
            "whale": row.get("Whale") or row.get("수급"),
            "trend": row.get("추세") or row.get("Trend"),
            "position": row.get("위치") or row.get("Position"),
            "volume": row.get("거래량") or row.get("Volume"),
            "surge": row.get("급등예측") or row.get("Surge"),
            "alpha_score": _pick_numeric(row, "alpha_score", "Alpha", "AI점수", "Antigrav"),
            "conviction_score": _pick_numeric(row, "conviction_score", "Conviction", "확신도"),
            "decision_score": row.get("Decision Score") or row.get("decision_score"),
            "entry_reference_price": row.get("entry_reference_price") or row.get("현재가") or row.get("Current Price") or row.get("curr_price"),
            "prob_5": _pick_numeric(row, "prob_5", "_prob_5", "AI확률", "ml_prob"),
            "prob_clean": _pick_numeric(row, "prob_clean", "_prob_clean", "Clean Hit", "정밀확률"),
            "real_trend": row.get("real_trend") or row.get("추세") or row.get("Trend"),
            "strategy_family": row.get("strategy_family"),
            "scan_mode": row.get("scan_mode"),
            "phase25_variant": row.get("phase25_variant"),
            "phase25_prob": row.get("phase25_prob"),
            "phase25_shadow_variant": row.get("phase25_shadow_variant"),
            "phase25_shadow_prob": row.get("phase25_shadow_prob"),
            "phase25_recommended_threshold": row.get("phase25_recommended_threshold"),
            "phase25_signal_direction": row.get("phase25_signal_direction"),
            "phase25_raw_auc": row.get("phase25_raw_auc"),
            "phase25_oos_auc": row.get("phase25_oos_auc"),
            "phase25_oos_win_rate_pct": row.get("phase25_oos_win_rate_pct"),
            "phase25_oos_avg_return_pct": row.get("phase25_oos_avg_return_pct"),
            "expected_edge_score": row.get("expected_edge_score"),
            "expected_return_1d_pct": row.get("expected_return_1d_pct"),
            "expected_return_3d_pct": row.get("expected_return_3d_pct"),
            "model_prob_available_count": row.get("model_prob_available_count"),
            "model_prob_mean": row.get("model_prob_mean"),
            "low_model_prob_score": row.get("low_model_prob_score"),
            "low_prob_high_score": row.get("low_prob_high_score"),
            "expected_edge_inversion_score": row.get("expected_edge_inversion_score"),
            "model_trace_status": row.get("model_trace_status"),
            "model_error": row.get("model_error"),
            "theme_context": row.get("_theme_context") or row.get("theme_context") or {},
            "leader_metrics": row.get("_leader_metrics") or row.get("leader_metrics") or {},
            "routing_path": row.get("_routing_path") or row.get("routing_path") or "",
            "market_gate": row.get("market_gate"),
            "scanner_timeframe_profile": row.get("scanner_timeframe_profile"),
            "kr_universe_role": row.get("kr_universe_role"),
            "explosive_leader_flag": row.get("explosive_leader_flag"),
            "core_trend_flag": row.get("core_trend_flag"),
        }

        score_breakdown = {
            "decision_score": score,
            "antigrav": float(row.get("Antigrav", 0) or 0),
            "whale_score": whale_score,
        }

        candidates.append(
            ScannerCandidate(
                ticker=ticker,
                score=score,
                reasons=reasons,
                feature_snapshot=feature_snapshot,
                score_breakdown=score_breakdown,
                theme_context=feature_snapshot.get("theme_context", {}) if isinstance(feature_snapshot.get("theme_context"), dict) else {},
                leader_metrics=feature_snapshot.get("leader_metrics", {}) if isinstance(feature_snapshot.get("leader_metrics"), dict) else {},
                routing_path=str(feature_snapshot.get("routing_path") or ""),
                warnings=warnings,
            )
        )

    rank_payload = [{"theme_context": c.theme_context, "leader_metrics": c.leader_metrics} for c in candidates]
    assign_theme_ranks(rank_payload)
    for candidate, ranked in zip(candidates, rank_payload):
        candidate.theme_context = ranked.get("theme_context", candidate.theme_context)
        candidate.leader_metrics = ranked.get("leader_metrics", candidate.leader_metrics)
        candidate.feature_snapshot["theme_context"] = candidate.theme_context
        candidate.feature_snapshot["leader_metrics"] = candidate.leader_metrics

    summary: Dict[str, Any] = {
        "candidate_count": len(candidates),
        "weak_candidate_count": weak_count,
        "source": source,
    }
    if isinstance(summary_overrides, dict):
        summary.update(summary_overrides)

    handoff = ScannerHandoff(
        run_context=context,
        candidates=candidates,
        summary=summary,
    )
    return handoff


def export_legacy_scanner_handoff(
    results: List[Dict[str, Any]],
    market: str,
    strategy_version: str = "legacy-ui-v1",
    model_version: str = "legacy",
    code_version: str = "bridge-v1",
    run_context: RunContext | None = None,
    source: str = "legacy_streamlit_scanner",
    summary_overrides: Dict[str, Any] | None = None,
) -> str:
    """Export legacy scanner results into ScannerHandoff JSON."""

    context = run_context or RunContext(
        run_id=f"RUN-{uuid4().hex[:8].upper()}",
        as_of_date=str(date.today()),
        market=market,
        strategy_version=strategy_version,
        model_version=model_version,
        code_version=code_version,
    )
    handoff = build_scanner_handoff_from_legacy_results(
        results=results,
        context=context,
        source=source,
        summary_overrides=summary_overrides,
    )

    memory = MemoryManager()
    out_path = memory.shared_working(context.run_id) / "scanner_handoff.json"
    write_json(out_path, handoff.to_dict())
    return str(out_path)
