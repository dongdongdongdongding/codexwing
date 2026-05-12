from __future__ import annotations

import os
import math
from typing import Any, Dict, List, Optional

from multi_agent.contracts.types import PlannerDecision, PlannerHandoff, RunContext, WarningItem
from modules.horizon_policy import resolve_horizon_policy
from modules.inverted_signal_features import compute_low_prob_high_score_features
from modules.loss_risk_features import (
    compute_entry_timing_risk_features,
    compute_loss_risk_features,
    get_loss_risk_gate_thresholds,
    get_loss_risk_soft_cap_decision,
)
from multi_agent.agents.kr_quant_reranker import (
    compute_kr_basket_priority,
    compute_kr_quant_rerank,
    resolve_kr_active_lane,
)


KOSPI_RELATIVE_RANK_MODEL = "kospi_floor_win_relative_v2"
KOSPI_RELATIVE_WEIGHTS = {
    "decision_score": 0.55,
    "volume_ratio": 0.20,
    "loss_risk_score": -0.10,
}

KOSDAQ_RELATIVE_RANK_MODEL = "kosdaq_floor_win_relative_v5"
KOSDAQ_RELATIVE_WEIGHTS = {
    "tech_score": 0.10,
    "volume_ratio": 0.22,
    "prob_clean": 0.20,
    "low_model_prob_score": 0.10,
    "low_prob_high_score": 0.15,
    "loss_risk_score": -0.10,
    "entry_timing_risk_score": -0.04,
}


# Phase25 quality-gate thresholds per (market, mode).
# Each entry encodes:
#   raw_buffer   — additive gap above bundle.recommended_threshold required for priority
#   raw_floor    — absolute minimum raw_phase25_prob, overrides buffer when buffer fails
#   clean_min    — minimum clean_prob (non-phase25 probability) required
#   score_min    — minimum decision_score required
# Floors are hard-coded minimums safe regardless of which threshold the model
# happens to emit. Buffers scale with the model's calibrated threshold.
# Values calibrated against archive top-pick win rates as of 2026-04-22.
PHASE25_QUALITY_GATES: Dict[str, Dict[str, float]] = {
    "KOSDAQ_SWING_PRIORITY":   {"raw_buffer": 12.0, "raw_floor": 37.0, "clean_min": 38.0, "score_min": 88.0},
    "KOSPI_SWING_PRIORITY":    {"raw_buffer": 10.0, "raw_floor": 35.0, "clean_min": 35.0, "score_min": 86.0},
    "KOSDAQ_INTRADAY_PRIORITY":{"raw_buffer": 12.0, "raw_floor": 72.0, "clean_min": 35.0, "score_min": 88.0},
    "KOSDAQ_INTRADAY_WATCH":   {"raw_buffer":  0.0, "raw_floor": 60.0, "clean_min": 28.0, "score_min":  0.0},
    "KOSPI_INTRADAY_PRIORITY": {"raw_buffer":  5.0, "raw_floor": 65.0, "clean_min": 32.0, "score_min": 84.0},
}

# Downgrade triggers: how far below recommended_threshold (raw prob) triggers
# soft demote vs hard AVOID. Used by the KOSDAQ swing gate.
PHASE25_DOWNGRADE_SOFT_GAP = 4.0
PHASE25_DOWNGRADE_HARD_GAP = 8.0


# Variant prefix helpers: 2026-04-25 segment split renamed
# phase25_kr_swing → phase25_kospi_swing / phase25_kosdaq_swing (and intraday).
# Old combined names are kept as fallbacks in modules/quant_analysis.py, so the
# gates must recognize both forms or the per-market protection silently
# disappears when the new bundles are loaded.
_SWING_VARIANT_PREFIXES = (
    "phase25_kr_swing",
    "phase25_kospi_swing",
    "phase25_kosdaq_swing",
)
_INTRADAY_VARIANT_PREFIXES = (
    "phase25_kr_intraday",
    "phase25_kospi_intraday",
    "phase25_kosdaq_intraday",
)


def _is_swing_variant(variant: str | None) -> bool:
    return any(str(variant or "").startswith(p) for p in _SWING_VARIANT_PREFIXES)


def _is_intraday_variant(variant: str | None) -> bool:
    return any(str(variant or "").startswith(p) for p in _INTRADAY_VARIANT_PREFIXES)


def _gate_passes(raw_prob: float | None, clean_prob: float | None, score: float, recommended_threshold: float | None, gate_name: str) -> bool:
    """Evaluate phase25 quality gate for the given (market, mode) key.

    Returns True iff the candidate exceeds raw/clean/score thresholds for the
    named gate. Missing (None) inputs never pass. Kept central so threshold
    changes flow from config rather than scattered magic numbers.
    """
    gate = PHASE25_QUALITY_GATES.get(gate_name)
    if gate is None or raw_prob is None or recommended_threshold is None:
        return False
    raw_needed = max(float(recommended_threshold) + gate["raw_buffer"], gate["raw_floor"])
    if float(raw_prob) < raw_needed:
        return False
    if clean_prob is not None and float(clean_prob) < gate["clean_min"]:
        return False
    if gate["score_min"] > 0.0 and float(score) < gate["score_min"]:
        return False
    return True


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


def _resolve_market_gate(*sources: Dict[str, Any]) -> str:
    for source in sources:
        if not isinstance(source, dict):
            continue
        value = source.get("market_gate")
        if isinstance(value, dict):
            gate = str(value.get("gate") or value.get("regime") or "").strip().upper()
        else:
            gate = str(value or "").strip().upper()
        if gate:
            return gate
    return ""


def _apply_loss_risk_gate(
    *,
    decision: str,
    run_market: str,
    scan_mode: str,
    loss_risk_score: float,
    loss_risk_flags: List[str],
    rationale: List[str],
    theme_risk: List[str],
) -> str:
    if str(scan_mode or "").upper() != "SWING" or str(run_market or "").upper() not in {"KOSPI", "KOSDAQ"}:
        return decision
    market = str(run_market or "").upper()
    thresholds = get_loss_risk_gate_thresholds(market)
    hard = float(thresholds["hard"])
    soft = float(thresholds["soft"])
    if loss_risk_score >= hard:
        capped = _decision_from_rank(min(_decision_rank(decision), _decision_rank("OBSERVE")))
        if capped != decision:
            rationale.append(f"loss_risk_hard_cap:{loss_risk_score:.1f}")
        decision = capped
        theme_risk.append("LOSS_RISK_HARD_CAP")
    elif loss_risk_score >= soft:
        soft_cap_decision = get_loss_risk_soft_cap_decision(market)
        capped = _decision_from_rank(min(_decision_rank(decision), _decision_rank(soft_cap_decision)))
        if capped != decision:
            rationale.append(f"loss_risk_soft_cap:{loss_risk_score:.1f}")
        decision = capped
        theme_risk.append("LOSS_RISK_SOFT_CAP")
    if loss_risk_flags:
        theme_risk.extend([flag for flag in loss_risk_flags if flag not in theme_risk])
    return decision


def _apply_phase25_reliability_gate(
    *,
    decision: str,
    phase25_variant: str,
    phase25_signal_direction: str,
    phase25_raw_auc: float | None,
    phase25_oos_auc: float | None,
    rationale: List[str],
    theme_risk: List[str],
    phase25_oos_win_rate_pct: float | None = None,
    phase25_oos_avg_return_pct: float | None = None,
) -> str:
    """Refuse to publish picks from a Phase25 model that is statistically
    unreliable. Triggers on any of:
      - signal_direction='uncertain' UNLESS OOS metrics validate the model
        (oos_auc>=0.55, oos_win_rate>=70, oos_avg_return>=5). Mirrors the
        bundle-load override in modules/quant_analysis.py — without this
        mirror the bundle would publish probabilities normally but the
        planner would still refuse to act on them.
      - bundle raw_auc < 0.50 (at-or-below coin-flip on its own val split);
      - bundle oos_auc < 0.45 (held-out tail evaluation says the model
        breaks under regime shift, even if val_auc looked fine — this
        catches the KOSDAQ swing 2026-04-27 case where val_auc=0.69 but
        OOS=0.32 with CV folds 0.26/0.78/0.28).
    """
    if not phase25_variant:
        return decision
    oos_validates = (
        phase25_oos_auc is not None and phase25_oos_auc >= 0.55
        and phase25_oos_win_rate_pct is not None and phase25_oos_win_rate_pct >= 70.0
        and phase25_oos_avg_return_pct is not None and phase25_oos_avg_return_pct >= 5.0
    )
    triggered = False
    if phase25_signal_direction == "uncertain":
        if oos_validates:
            rationale.append("phase25_uncertain_overridden_by_oos")
        else:
            theme_risk.append("PHASE25_UNCERTAIN_DIRECTION")
            rationale.append("phase25_uncertain_signal_direction")
            triggered = True
    elif phase25_raw_auc is not None and phase25_raw_auc < 0.50:
        theme_risk.append("PHASE25_RAW_AUC_BELOW_RANDOM")
        rationale.append(f"phase25_raw_auc={phase25_raw_auc:.3f}<0.50")
        triggered = True
    elif phase25_oos_auc is not None and phase25_oos_auc < 0.45:
        theme_risk.append("PHASE25_OOS_AUC_REGIME_BREAK")
        rationale.append(f"phase25_oos_auc={phase25_oos_auc:.3f}<0.45")
        triggered = True
    if triggered:
        return "AVOID"
    return decision


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
        and _is_intraday_variant(phase25_variant)
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
    alpha_score: Any = None,
    low_model_prob_score: float | None = None,
    low_prob_high_score: float | None = None,
    rationale: List[str],
    theme_risk: List[str],
) -> str:
    if not (
        run_market == "KOSDAQ"
        and scan_mode.upper() == "SWING"
        and _is_swing_variant(phase25_variant)
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
    try:
        alpha = float(alpha_score) if alpha_score not in (None, "") else None
    except Exception:
        alpha = None

    # 2026-05-08 swing-main-sl3: KR swing archive showed model probability is
    # inverted in the current regime. Do not promote this to PRIORITY by itself,
    # but also do not hard-AVOID a trend-up, high-alpha candidate solely because
    # phase25 is low when the explicit inverted-prob features match validated
    # subsets (low_model_prob_score>=25: win 66.37%, avg +6.14%).
    inversion_override = (
        str(real_trend or "").upper() == "UP"
        and alpha is not None
        and alpha >= 75.0
        and low_model_prob_score is not None
        and low_model_prob_score >= 25.0
        and low_prob_high_score is not None
        and low_prob_high_score >= 40.0
    )

    if gap >= PHASE25_DOWNGRADE_HARD_GAP:
        if inversion_override:
            decision = _decision_from_rank(max(1, _decision_rank(decision) - 1))
            theme_risk.append("PHASE25_SWING_BELOW_THRESHOLD_INVERTED_OVERRIDE")
            rationale.append(
                "kosdaq_swing_inverted_prob_override:"
                f"alpha={alpha:.1f},low_model={low_model_prob_score:.1f},"
                f"low_prob_high={low_prob_high_score:.1f}"
            )
        else:
            decision = "AVOID"
            theme_risk.append("PHASE25_SWING_BELOW_THRESHOLD_HARD")
    elif gap >= PHASE25_DOWNGRADE_SOFT_GAP:
        decision = _decision_from_rank(max(0, _decision_rank(decision) - 1))
        theme_risk.append("PHASE25_SWING_BELOW_THRESHOLD_SOFT")

    if decision != "AVOID" and str(real_trend or "").upper() != "UP":
        decision = _decision_from_rank(max(0, _decision_rank(decision) - 1))
        theme_risk.append("KOSDAQ_SWING_TREND_GUARD")

    if decision != "AVOID" and clean_prob is not None and clean_prob < 28.0:
        decision = _decision_from_rank(max(0, _decision_rank(decision) - 1))
        theme_risk.append("KOSDAQ_SWING_CLEAN_PROB_GUARD")

    if decision != original_decision:
        reasons = []
        if gap >= PHASE25_DOWNGRADE_SOFT_GAP:
            reasons.append(f"phase25_prob={raw_phase25_prob:.1f}<threshold={recommended_threshold:.1f}")
        if str(real_trend or "").upper() != "UP":
            reasons.append(f"trend_guard={str(real_trend or '').upper() or 'UNKNOWN'}")
        if clean_prob is not None and clean_prob < 28.0:
            reasons.append(f"clean_prob={clean_prob:.1f}<28.0")
        rationale.append("kosdaq_swing_gate:" + ",".join(reasons))
    return decision


def _apply_winner_pattern_filter(
    *,
    decision: str,
    run_market: str,
    scan_mode: str,
    feature_snapshot: Dict[str, Any],
    rationale: List[str],
    theme_risk: List[str],
) -> str:
    """Winner-pattern univariate filter (added 2026-05-06).

    Only acts on PRIORITY_WATCHLIST/WATCHLIST. Findings from
    winner_pattern_research.json (FDR-replicated discovery→validation):

    KOSPI swing (5d ≥+10%): rsi_14 ↑, prev_pct_change_5d ↑, is_downtrend == 0.
      Demote one notch if rsi_14 < 50 AND prev_pct_change_5d < 0 — pure
      mean-reversion candidates rarely close +10% on swing horizon.

    KOSDAQ swing (5d ≥+10%): low-vol surge — volatility_20d ↓, atr_pct_14 ↓.
      Demote one notch if both volatility_20d AND atr_pct_14 are above the
      market-wide median ranges (vol_20d > 4.0% / atr > 5.0%) — high-vol
      KOSDAQ candidates failed to surge in OOS data.
    """
    rank = _decision_rank(decision)
    if rank < 2:
        return decision
    market = str(run_market or "").upper()
    mode = str(scan_mode or "").upper()
    if mode != "SWING":
        return decision

    def _safe(name: str) -> Optional[float]:
        v = feature_snapshot.get(name)
        if v in (None, ""):
            return None
        try:
            return float(v)
        except Exception:
            return None

    if market == "KOSPI":
        rsi = _safe("rsi_14")
        mom5 = _safe("prev_pct_change_5d")
        if rsi is not None and mom5 is not None and rsi < 50.0 and mom5 < 0.0:
            theme_risk.append("KOSPI_SWING_MOMENTUM_GUARD")
            rationale.append(f"winner_pattern_kospi: rsi={rsi:.1f}<50 mom5={mom5:.2f}<0")
            return _decision_from_rank(max(0, rank - 1))
    elif market == "KOSDAQ":
        vol20 = _safe("volatility_20d")
        atr = _safe("atr_pct_14")
        if vol20 is not None and atr is not None and vol20 > 4.0 and atr > 5.0:
            theme_risk.append("KOSDAQ_SWING_LOW_VOL_GUARD")
            rationale.append(f"winner_pattern_kosdaq: vol20={vol20:.2f}>4 atr={atr:.2f}>5")
            return _decision_from_rank(max(0, rank - 1))
    return decision


def _apply_intraday_trend_strategy_gate(
    *,
    decision: str,
    scan_mode: str,
    strategy_text: str,
    rationale: List[str],
    theme_risk: List[str],
) -> str:
    """2026-05-08 (swing-main, horizon 진단 STEP 5b 후속).

    INTRADAY scan_mode + scanner가 'Intraday Trend' 라벨을 붙이고 'Breakout'은
    포함 안 된 후보는 dedup 후 PRIORITY_WATCHLIST 행에서 5d -3% 이하 손실
    비율 42.8% (n=1262, bad 540 / ok 722). 같은 윈도우 'Intraday Breakout'은
    16.2% (n=747)로 정상 분포. scanner_services.py L518에서 breakout=False
    분기로 'Intraday Trend' 태그가 붙는데 forward 분포가 명백히 손실 편향.

    PRIORITY 등급(rank>=3)에 도달한 후보 중 'Intraday Trend' 태그면 WATCHLIST로
    한 단계 강등. AVOID로 보내지 않는 이유: 16.2%는 여전히 ok로 통과(완전한
    제거는 표본 노이즈 위험). soft demote로 PRIORITY만 막는다.
    AG_INTRADAY_TREND_DEMOTE=0이면 비활성.
    """
    if os.getenv("AG_INTRADAY_TREND_DEMOTE", "1").strip() in ("0", "", "false", "False"):
        return decision
    mode = str(scan_mode or "").upper()
    if mode != "INTRADAY":
        return decision
    if _decision_rank(decision) < 3:
        return decision
    text = str(strategy_text or "")
    if not text:
        return decision
    if "Intraday Trend" in text and "Breakout" not in text:
        theme_risk.append("INTRADAY_TREND_PRIORITY_DEMOTE")
        rationale.append("intraday_trend_priority_demote=42.8pct_bad_5d")
        return "WATCHLIST"
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
            _is_swing_variant(variant)
            and trend_up
            and route == "theme_routed"
            and _gate_passes(raw_phase25_prob, clean_prob, float(score), recommended_threshold, "KOSDAQ_SWING_PRIORITY")
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

    # KOSPI swing priority guard relaxation (swing-main-0nr, 2026-05-06).
    # Forward-validation over 30d showed gated rows had win_3d=69.4% / avg_3d=3.92%
    # (n=1,228 with EXPECTED_EDGE_WATCH_GUARD combo) versus the passing baseline
    # win_3d=62.1% / avg_3d=2.29% (n=29). The hard demote was net-negative — it
    # blocked candidates that beat the picked baseline by 7pp. Relax to a soft
    # note: keep the rationale/theme_risk markers so audits can still see the
    # phase25 condition, but do not demote. Gated by env toggle so the previous
    # behavior remains one flag away if a forward-week regression appears.
    if market == "KOSPI" and mode == "SWING" and _decision_rank(decision) >= 3:
        allow_priority = (
            _is_swing_variant(variant)
            and trend_up
            and _gate_passes(raw_phase25_prob, clean_prob, float(score), recommended_threshold, "KOSPI_SWING_PRIORITY")
        )
        if not allow_priority:
            relax = os.getenv("AG_KOSPI_SWING_PRIORITY_GUARD_RELAX", "1").strip() not in ("0", "", "false", "False")
            if relax:
                theme_risk.append("KOSPI_SWING_PRIORITY_GUARD_SOFT")
                rationale.append("priority_guard=KOSPI_SWING(soft)")
                return decision
            return _demote_to(
                2,
                "KOSPI_SWING_PRIORITY_GUARD",
                "priority_guard=KOSPI_SWING",
            )

    if market == "KOSDAQ" and mode == "INTRADAY":
        if _decision_rank(decision) >= 3:
            allow_priority = (
                _is_intraday_variant(variant)
                and trend_up
                and _gate_passes(raw_phase25_prob, clean_prob, float(score), recommended_threshold, "KOSDAQ_INTRADAY_PRIORITY")
            )
            if not allow_priority:
                return _demote_to(
                    2,
                    "KOSDAQ_INTRADAY_PRIORITY_GUARD",
                    "priority_guard=KOSDAQ_INTRADAY",
                )
        if _decision_rank(decision) >= 2:
            keep_watch = (
                _is_intraday_variant(variant)
                and _gate_passes(raw_phase25_prob, clean_prob, 0.0, recommended_threshold, "KOSDAQ_INTRADAY_WATCH")
            )
            if not keep_watch:
                return _demote_to(
                    1,
                    "KOSDAQ_INTRADAY_WATCH_GUARD",
                    "watch_guard=KOSDAQ_INTRADAY",
                )

    if market == "KOSPI" and mode == "INTRADAY" and _decision_rank(decision) >= 3:
        allow_priority = (
            _is_intraday_variant(variant)
            and trend_up
            and _gate_passes(raw_phase25_prob, clean_prob, float(score), recommended_threshold, "KOSPI_INTRADAY_PRIORITY")
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
    phase25_signal_direction: str = "",
    phase25_oos_win_rate_pct: float | None = None,
    phase25_oos_avg_return_pct: float | None = None,
) -> str:
    market = str(run_market or "").upper()
    mode = str(scan_mode or "").upper()
    trend_up = str(real_trend or "").upper() == "UP"
    if expected_return_1d_pct is None or expected_return_3d_pct is None:
        return decision

    # OOS-validated bypass: compute_expected_edge_profile uses phase18-era
    # anchors (prob_5/prob_clean centered on 50), but phase25 swing models
    # output ~25-35 prob with documented OOS win >=70 and OOS return >=5.
    # Without this bypass, every phase25 candidate fails min_1d=0.9% even
    # though the bundle's realized OOS metrics would clear it. Mirrors the
    # OOS preserve in _apply_phase25_reliability_gate /
    # _apply_watchlist_only_mode for policy consistency.
    sig_dir = str(phase25_signal_direction or "").lower()
    oos_validated = (
        sig_dir == "normal"
        and phase25_oos_win_rate_pct is not None
        and float(phase25_oos_win_rate_pct) >= 70.0
        and phase25_oos_avg_return_pct is not None
        and float(phase25_oos_avg_return_pct) >= 5.0
    )
    if oos_validated and trend_up:
        rationale.append(
            f"expected_edge_overridden_by_oos:win={float(phase25_oos_win_rate_pct):.1f}%,ret={float(phase25_oos_avg_return_pct):.2f}%"
        )
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
        # KOSPI SWING relaxation (2026-05-08): 0nr이 KOSPI_SWING_PRIORITY_GUARD
        # 와 EXPECTED_EDGE_WATCH_GUARD를 풀었으나 같은 후보가 직후
        # EXPECTED_EDGE_PRIORITY_GUARD에 동일하게 잡혀 KOSPI SWING
        # PRIORITY_WATCHLIST 회복 0건 (5/7 RUN-114752B6 47/47 WATCHLIST 강등).
        # EEPG와 EEWG는 동일 임계 함수에서 priority_*/min_* 만 다른
        # 직렬 단계이므로 같은 패턴으로 KOSPI SWING 한정 soft note 적용.
        kospi_swing_relax = (
            market == "KOSPI"
            and mode == "SWING"
            and os.getenv("AG_EXPECTED_EDGE_PRIORITY_GUARD_RELAX", "1").strip() not in ("0", "", "false", "False")
        )
        if kospi_swing_relax:
            theme_risk.append("EXPECTED_EDGE_PRIORITY_GUARD_SOFT")
            rationale.append(
                f"expected_edge_priority_guard_soft={float(expected_return_1d_pct):.2f}/{float(expected_return_3d_pct):.2f}"
            )
            return decision
        theme_risk.append("EXPECTED_EDGE_PRIORITY_GUARD")
        rationale.append(
            f"expected_edge_priority_guard={float(expected_return_1d_pct):.2f}/{float(expected_return_3d_pct):.2f}"
        )
        return "WATCHLIST"

    if rank >= 2 and (
        float(expected_return_1d_pct) < min_1d
        or float(expected_return_3d_pct) < min_3d
    ):
        # KOSPI SWING relaxation (swing-main-0nr, 2026-05-06): gated rows had
        # win_5d=75.4% / avg_5d=7.53% (n=345 EXPECTED_EDGE alone) and 74.6% /
        # 7.92% in the EXPECTED_EDGE|KOSPI_SWING_PRIORITY combo (n=1,228) —
        # both above the picked baseline (win_5d=72.4% / avg_5d=5.32%, n=29).
        # KOSPI INTRADAY and KOSDAQ keep the hard demote because gated-row
        # win-rates there (61.5% / 56.8%) sit at or below their baselines.
        kospi_swing_relax = (
            market == "KOSPI"
            and mode == "SWING"
            and os.getenv("AG_EXPECTED_EDGE_WATCH_GUARD_RELAX", "1").strip() not in ("0", "", "false", "False")
        )
        if kospi_swing_relax:
            theme_risk.append("EXPECTED_EDGE_WATCH_GUARD_SOFT")
            rationale.append(
                f"expected_edge_watch_guard_soft={float(expected_return_1d_pct):.2f}/{float(expected_return_3d_pct):.2f}"
            )
            return decision
        theme_risk.append("EXPECTED_EDGE_WATCH_GUARD")
        rationale.append(
            f"expected_edge_watch_guard={float(expected_return_1d_pct):.2f}/{float(expected_return_3d_pct):.2f}"
        )
        return _decision_from_rank(min(rank, 1))

    return decision


def _apply_kospi_swing_edge_promotion(
    *,
    decision: str,
    run_market: str,
    scan_mode: str,
    expected_edge_score: float | None,
    decision_score: float | None = None,
    rationale: List[str],
) -> str:
    """Promote KOSPI SWING candidates that clear the high-win 5d target slice.

    2026-05-12 Supabase validation for KOSPI SWING resolved 5d rows showed
    expected_edge_score >= 5.0 OR exception_leader at win_5d 77.95% /
    avg_5d +8.80% (n=254). The broader score-only path also cleared the
    revised target, but with lower win rate, so default live promotion stays
    on edge-supported planner candidates plus separately admitted exception
    leaders. Keep this KOSPI-only and let later loss/inference gates demote
    unsafe rows.
    """
    market = str(run_market or "").upper()
    mode = str(scan_mode or "").upper()
    if market != "KOSPI" or mode != "SWING":
        return decision
    if os.getenv("AG_KOSPI_SWING_EDGE_PROMOTION", "1").strip() in ("0", "", "false", "False"):
        return decision
    if _decision_rank(decision) >= _decision_rank("PRIORITY_WATCHLIST"):
        return decision
    if _decision_rank(decision) < _decision_rank("OBSERVE"):
        return decision
    try:
        edge = float(expected_edge_score) if expected_edge_score not in (None, "") else None
    except Exception:
        edge = None
    if edge is None or not math.isfinite(edge):
        edge = None
    try:
        min_edge = float(os.getenv("AG_KOSPI_SWING_EDGE_PROMOTION_MIN", "5.0"))
    except Exception:
        min_edge = 5.0
    score_promotion_enabled = os.getenv("AG_KOSPI_SWING_SCORE_PROMOTION", "0").strip() not in (
        "0",
        "",
        "false",
        "False",
    )
    score = None
    min_score = 95.0
    if score_promotion_enabled:
        try:
            score = float(decision_score) if decision_score not in (None, "") else None
        except Exception:
            score = None
        if score is not None and not math.isfinite(score):
            score = None
        try:
            min_score = float(os.getenv("AG_KOSPI_SWING_SCORE_PROMOTION_MIN", "95.0"))
        except Exception:
            min_score = 95.0
    edge_pass = edge is not None and edge >= min_edge
    score_pass = score is not None and score >= min_score
    if not (edge_pass or score_pass):
        return decision
    reason_parts = []
    if edge_pass:
        reason_parts.append(f"edge={edge:.2f}>=min{min_edge:.2f}")
    if score_pass:
        reason_parts.append(f"decision_score={score:.2f}>=min{min_score:.2f}")
    rationale.append("kospi_swing_edge_promotion=" + ";".join(reason_parts))
    return "PRIORITY_WATCHLIST"


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


def _candidate_market(cand: Dict[str, Any], run_market: str) -> str:
    feature_snapshot = cand.get("feature_snapshot", {}) if isinstance(cand.get("feature_snapshot"), dict) else {}
    ticker = str(cand.get("ticker") or feature_snapshot.get("ticker") or "").upper()
    market = str(feature_snapshot.get("market") or cand.get("market") or run_market or "").upper()
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    return market or "UNKNOWN"


def _candidate_feature_float(cand: Dict[str, Any], key: str) -> Optional[float]:
    feature_snapshot = cand.get("feature_snapshot", {}) if isinstance(cand.get("feature_snapshot"), dict) else {}
    for source in (feature_snapshot, cand):
        value = source.get(key) if isinstance(source, dict) else None
        if value in (None, ""):
            continue
        try:
            return float(value)
        except Exception:
            continue
    return None


def _percentile_by_feature(rows: List[Dict[str, Any]], feature: str) -> Dict[int, float]:
    values: List[tuple[int, float]] = []
    for idx, row in enumerate(rows):
        value = _candidate_feature_float(row, feature)
        if value is None and feature in {"low_model_prob_score", "low_prob_high_score"}:
            inverted = compute_low_prob_high_score_features(
                alpha_score=_candidate_feature_float(row, "alpha_score"),
                tech_score=_candidate_feature_float(row, "tech_score"),
                ml_prob=_candidate_feature_float(row, "prob_5") or _candidate_feature_float(row, "ml_prob"),
                prob_clean=_candidate_feature_float(row, "prob_clean"),
                phase25_prob=_candidate_feature_float(row, "phase25_prob"),
                expected_edge_score=_candidate_feature_float(row, "expected_edge_score"),
            )
            value = inverted.get(feature)
        if value is None and feature == "loss_risk_score":
            value = compute_loss_risk_features(
                market_subtype=_candidate_market(row, ""),
                alpha_score=_candidate_feature_float(row, "alpha_score"),
                tech_score=_candidate_feature_float(row, "tech_score"),
                whale_score=_candidate_feature_float(row, "whale_score"),
                ml_prob=_candidate_feature_float(row, "prob_5") or _candidate_feature_float(row, "ml_prob"),
                prob_clean=_candidate_feature_float(row, "prob_clean"),
                volume_ratio=_candidate_feature_float(row, "volume_ratio"),
                volume_confirmed=(
                    row.get("feature_snapshot", {}).get("volume_confirmed")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("volume_confirmed")
                ),
                position=(
                    row.get("feature_snapshot", {}).get("position")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("position")
                )
                or "",
                tier=(
                    row.get("feature_snapshot", {}).get("tier")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("tier")
                )
                or "",
                trend=(
                    row.get("feature_snapshot", {}).get("real_trend")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("real_trend")
                )
                or (
                    row.get("feature_snapshot", {}).get("trend")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("trend")
                )
                or "",
            ).get("loss_risk_score")
        if value is None and feature == "entry_timing_risk_score":
            loss_risk = _candidate_feature_float(row, "loss_risk_score")
            if loss_risk is None:
                loss_risk = compute_loss_risk_features(
                    market_subtype=_candidate_market(row, ""),
                    alpha_score=_candidate_feature_float(row, "alpha_score"),
                    tech_score=_candidate_feature_float(row, "tech_score"),
                    whale_score=_candidate_feature_float(row, "whale_score"),
                    ml_prob=_candidate_feature_float(row, "prob_5") or _candidate_feature_float(row, "ml_prob"),
                    prob_clean=_candidate_feature_float(row, "prob_clean"),
                    volume_ratio=_candidate_feature_float(row, "volume_ratio"),
                    volume_confirmed=(
                        row.get("feature_snapshot", {}).get("volume_confirmed")
                        if isinstance(row.get("feature_snapshot"), dict)
                        else row.get("volume_confirmed")
                    ),
                    position=(
                        row.get("feature_snapshot", {}).get("position")
                        if isinstance(row.get("feature_snapshot"), dict)
                        else row.get("position")
                    )
                    or "",
                    tier=(
                        row.get("feature_snapshot", {}).get("tier")
                        if isinstance(row.get("feature_snapshot"), dict)
                        else row.get("tier")
                    )
                    or "",
                    trend=(
                        row.get("feature_snapshot", {}).get("real_trend")
                        if isinstance(row.get("feature_snapshot"), dict)
                        else row.get("trend")
                    )
                    or "",
                ).get("loss_risk_score")
            value = compute_entry_timing_risk_features(
                market_subtype=_candidate_market(row, ""),
                expected_return_1d_pct=_candidate_feature_float(row, "expected_return_1d_pct"),
                expected_return_3d_pct=_candidate_feature_float(row, "expected_return_3d_pct"),
                expected_edge_score=_candidate_feature_float(row, "expected_edge_score"),
                prev_pct_change_1d=_candidate_feature_float(row, "prev_pct_change_1d"),
                prev_pct_change_5d=_candidate_feature_float(row, "prev_pct_change_5d"),
                volume_ratio=_candidate_feature_float(row, "volume_ratio"),
                prob_clean=_candidate_feature_float(row, "prob_clean"),
                loss_risk_score=loss_risk,
                position=(
                    row.get("feature_snapshot", {}).get("position")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("position")
                )
                or "",
                tier=(
                    row.get("feature_snapshot", {}).get("tier")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("tier")
                )
                or "",
                trend=(
                    row.get("feature_snapshot", {}).get("real_trend")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("trend")
                )
                or "",
            ).get("entry_timing_risk_score")
        if value is None:
            continue
        if not math.isfinite(float(value)):
            continue
        values.append((idx, float(value)))
    if len(values) < 2:
        return {idx: 50.0 for idx, _ in values}
    ordered = sorted(values, key=lambda item: item[1])
    denom = max(len(ordered) - 1, 1)
    out: Dict[int, float] = {}
    pos = 0
    while pos < len(ordered):
        end = pos
        while end + 1 < len(ordered) and ordered[end + 1][1] == ordered[pos][1]:
            end += 1
        pct = ((pos + end) / 2.0) / denom * 100.0
        for i in range(pos, end + 1):
            out[ordered[i][0]] = pct
        pos = end + 1
    return out


def _attach_market_relative_scores(
    rows: List[Dict[str, Any]],
    *,
    market: str,
    weights: Dict[str, float],
    model: str,
) -> None:
    percentiles = {
        feature: _percentile_by_feature(rows, feature)
        for feature in weights
    }
    thresholds = get_loss_risk_gate_thresholds(market)
    soft_cap = float(thresholds.get("soft", 50.0))
    hard_cap = float(thresholds.get("hard", 65.0))
    for idx, row in enumerate(rows):
        total = 0.0
        score = 0.0
        for feature, weight in weights.items():
            feature_pct = percentiles.get(feature, {}).get(idx)
            if feature_pct is None:
                feature_pct = 50.0
            signed_weight = float(weight)
            directional_pct = feature_pct if signed_weight >= 0 else 100.0 - feature_pct
            score += float(directional_pct) * abs(signed_weight)
            total += abs(signed_weight)
        relative_score = round(score / total, 4) if total > 0 else None
        loss_risk_score = _candidate_feature_float(row, "loss_risk_score")
        if loss_risk_score is None:
            loss_risk_score = compute_loss_risk_features(
                market_subtype=market,
                alpha_score=_candidate_feature_float(row, "alpha_score"),
                tech_score=_candidate_feature_float(row, "tech_score"),
                whale_score=_candidate_feature_float(row, "whale_score"),
                ml_prob=_candidate_feature_float(row, "prob_5") or _candidate_feature_float(row, "ml_prob"),
                prob_clean=_candidate_feature_float(row, "prob_clean"),
                volume_ratio=_candidate_feature_float(row, "volume_ratio"),
                volume_confirmed=(
                    row.get("feature_snapshot", {}).get("volume_confirmed")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("volume_confirmed")
                ),
                position=(
                    row.get("feature_snapshot", {}).get("position")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("position")
                )
                or "",
                tier=(
                    row.get("feature_snapshot", {}).get("tier")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("tier")
                )
                or "",
                trend=(
                    row.get("feature_snapshot", {}).get("real_trend")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("real_trend")
                )
                or (
                    row.get("feature_snapshot", {}).get("trend")
                    if isinstance(row.get("feature_snapshot"), dict)
                    else row.get("trend")
                )
                or "",
            ).get("loss_risk_score")
        if relative_score is not None and loss_risk_score is not None:
            if float(loss_risk_score) >= hard_cap:
                relative_score = min(relative_score, 30.0)
            elif float(loss_risk_score) >= soft_cap:
                relative_score = min(relative_score, 55.0)
        row["_relative_rank_score"] = relative_score
        row["_relative_rank_model"] = model


def _attach_kospi_relative_scores(rows: List[Dict[str, Any]]) -> None:
    _attach_market_relative_scores(
        rows,
        market="KOSPI",
        weights=KOSPI_RELATIVE_WEIGHTS,
        model=KOSPI_RELATIVE_RANK_MODEL,
    )


def _attach_kosdaq_relative_scores(rows: List[Dict[str, Any]]) -> None:
    _attach_market_relative_scores(
        rows,
        market="KOSDAQ",
        weights=KOSDAQ_RELATIVE_WEIGHTS,
        model=KOSDAQ_RELATIVE_RANK_MODEL,
    )


def _relative_rank_score(cand: Dict[str, Any], market: str) -> tuple[Optional[float], str]:
    feature_snapshot = cand.get("feature_snapshot", {}) if isinstance(cand.get("feature_snapshot"), dict) else {}
    if market == "KOSPI":
        value = _candidate_feature_float(cand, "decision_score")
        if value is None:
            value = _candidate_feature_float(cand, "score")
        return value, KOSPI_RELATIVE_RANK_MODEL
    if market == "KOSDAQ":
        inverted = compute_low_prob_high_score_features(
            alpha_score=_candidate_feature_float(cand, "alpha_score"),
            tech_score=_candidate_feature_float(cand, "tech_score"),
            ml_prob=_candidate_feature_float(cand, "prob_5") or _candidate_feature_float(cand, "ml_prob"),
            prob_clean=_candidate_feature_float(cand, "prob_clean"),
            phase25_prob=_candidate_feature_float(cand, "phase25_prob"),
            expected_edge_score=_candidate_feature_float(cand, "expected_edge_score"),
        )
        low_model = _candidate_feature_float(cand, "low_model_prob_score")
        low_prob_high = _candidate_feature_float(cand, "low_prob_high_score")
        tech = _candidate_feature_float(cand, "tech_score")
        alpha = _candidate_feature_float(cand, "alpha_score")
        low_model = inverted["low_model_prob_score"] if low_model is None else low_model
        low_prob_high = inverted["low_prob_high_score"] if low_prob_high is None else low_prob_high
        volume_ratio = _candidate_feature_float(cand, "volume_ratio")
        prob_clean = _candidate_feature_float(cand, "prob_clean")
        loss_risk = _candidate_feature_float(cand, "loss_risk_score")
        if loss_risk is None:
            loss_risk = compute_loss_risk_features(
                market_subtype=market,
                alpha_score=alpha,
                tech_score=tech,
                whale_score=_candidate_feature_float(cand, "whale_score"),
                ml_prob=_candidate_feature_float(cand, "prob_5") or _candidate_feature_float(cand, "ml_prob"),
                prob_clean=prob_clean,
                volume_ratio=volume_ratio,
                volume_confirmed=feature_snapshot.get("volume_confirmed") or cand.get("volume_confirmed"),
                position=feature_snapshot.get("position") or cand.get("position") or "",
                tier=feature_snapshot.get("tier") or cand.get("tier") or "",
                trend=feature_snapshot.get("real_trend") or feature_snapshot.get("trend") or cand.get("trend") or "",
            ).get("loss_risk_score")
        entry_timing_risk = _candidate_feature_float(cand, "entry_timing_risk_score")
        if entry_timing_risk is None:
            entry_timing_risk = compute_entry_timing_risk_features(
                market_subtype=market,
                expected_return_1d_pct=_candidate_feature_float(cand, "expected_return_1d_pct"),
                expected_return_3d_pct=_candidate_feature_float(cand, "expected_return_3d_pct"),
                expected_edge_score=_candidate_feature_float(cand, "expected_edge_score"),
                prev_pct_change_1d=_candidate_feature_float(cand, "prev_pct_change_1d"),
                prev_pct_change_5d=_candidate_feature_float(cand, "prev_pct_change_5d"),
                volume_ratio=volume_ratio,
                prob_clean=prob_clean,
                loss_risk_score=loss_risk,
                position=feature_snapshot.get("position") or cand.get("position") or "",
                tier=feature_snapshot.get("tier") or cand.get("tier") or "",
                trend=feature_snapshot.get("real_trend") or feature_snapshot.get("trend") or cand.get("trend") or "",
            ).get("entry_timing_risk_score")
        pieces = [
            (tech, 0.10),
            (volume_ratio, 0.22),
            (prob_clean, 0.20),
            (low_model, 0.10),
            (low_prob_high, 0.15),
            (loss_risk, -0.10),
            (entry_timing_risk, -0.04),
        ]
        total = sum(abs(weight) for value, weight in pieces if value is not None)
        if total <= 0:
            return None, KOSDAQ_RELATIVE_RANK_MODEL
        score = sum(float(value) * weight for value, weight in pieces if value is not None) / total
        return score, KOSDAQ_RELATIVE_RANK_MODEL
    value = _candidate_feature_float(cand, "decision_score")
    if value is None:
        value = _candidate_feature_float(cand, "score")
    return value, "generic_decision_score_relative_v1"


def _grade_from_relative_pct(rank_pct: Optional[float]) -> str:
    if rank_pct is None:
        return ""
    if rank_pct <= 0.15:
        return "RELATIVE_PRIORITY"
    if rank_pct <= 0.30:
        return "RELATIVE_WATCHLIST"
    return "RELATIVE_OBSERVE"


def _attach_relative_ranks(candidates: List[Dict[str, Any]], run_market: str) -> None:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for cand in candidates:
        market = _candidate_market(cand, run_market)
        score, model = _relative_rank_score(cand, market)
        cand["_relative_market"] = market
        cand["_relative_rank_score"] = score
        cand["_relative_rank_model"] = model
        groups.setdefault(market, []).append(cand)

    for market, rows in groups.items():
        if market == "KOSPI":
            _attach_kospi_relative_scores(rows)
        if market == "KOSDAQ":
            _attach_kosdaq_relative_scores(rows)
        scored = [row for row in rows if row.get("_relative_rank_score") is not None]
        scored.sort(key=lambda row: float(row.get("_relative_rank_score") or 0.0), reverse=True)
        n = len(scored)
        for pos, row in enumerate(scored, start=1):
            rank_pct = float(pos - 1) / max(n - 1, 1)
            row["_relative_rank_pct"] = round(rank_pct, 6)
            row["_regime_adjusted_grade"] = _grade_from_relative_pct(rank_pct)


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
    _attach_relative_ranks(ranked_candidates, run_market)

    def _order_key(row: Dict[str, Any]) -> tuple[float, ...]:
        basket_meta = row.get("_basket_priority", {}) if isinstance(row.get("_basket_priority"), dict) else {}
        quant_meta = row.get("_quant_rerank", {}) if isinstance(row.get("_quant_rerank"), dict) else {}
        relative_score = float(row.get("_relative_rank_score") or 0.0)
        basket_score = float(basket_meta.get("score", quant_meta.get("score", row.get("score", 0.0))) or 0.0)
        quant_score = float(quant_meta.get("score", row.get("score", 0.0)) or 0.0)
        scanner_score = float(row.get("score", 0.0) or 0.0)
        if run_market in {"KOSPI", "KOSDAQ"}:
            return (relative_score, basket_score, quant_score, scanner_score)
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
        market_gate = _resolve_market_gate(quant_meta, feature_snapshot, cand)
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
        tech_score = feature_snapshot.get("tech_score")
        conviction_score = feature_snapshot.get("conviction_score")
        decision_score = feature_snapshot.get("decision_score", score)
        whale_score = feature_snapshot.get("whale_score")
        volume = feature_snapshot.get("volume")
        volume_ratio = feature_snapshot.get("volume_ratio")
        volume_confirmed = feature_snapshot.get("volume_confirmed")
        entry_reference_price = (
            feature_snapshot.get("entry_reference_price")
            or feature_snapshot.get("entry_price")
            or feature_snapshot.get("Entry Price")
            or feature_snapshot.get("Entry(-2%)")
            or feature_snapshot.get("매수가(-2%)")
            or feature_snapshot.get("현재가")
            or feature_snapshot.get("Current Price")
            or feature_snapshot.get("current_price")
            or feature_snapshot.get("curr_price")
            or feature_snapshot.get("price")
        )
        if entry_reference_price not in (None, ""):
            try:
                entry_reference_price = float(str(entry_reference_price).replace(",", "").replace("%", "").strip())
            except Exception:
                entry_reference_price = None
        prob_5 = feature_snapshot.get("prob_5", feature_snapshot.get("_prob_5", feature_snapshot.get("ml_prob")))
        prob_clean = feature_snapshot.get("prob_clean", feature_snapshot.get("_prob_clean"))
        real_trend = str(feature_snapshot.get("real_trend") or feature_snapshot.get("trend") or "")
        loss_risk_features = compute_loss_risk_features(
            market_subtype=run_market,
            alpha_score=alpha_score,
            tech_score=tech_score,
            whale_score=whale_score,
            ml_prob=prob_5,
            prob_clean=prob_clean,
            volume_ratio=volume_ratio,
            volume_confirmed=volume_confirmed,
            position=feature_snapshot.get("position") or cand.get("position") or "",
            tier=feature_snapshot.get("tier") or cand.get("tier") or "",
            trend=real_trend or feature_snapshot.get("trend") or cand.get("trend") or "",
        )
        loss_risk_score = float(loss_risk_features.get("loss_risk_score", 0.0) or 0.0)
        loss_risk_flags = [
            name.upper()
            for name, value in loss_risk_features.items()
            if name.endswith("_risk") and float(value or 0.0) >= 1.0
        ]
        strategy_family = str(feature_snapshot.get("strategy_family") or "")
        scan_mode = str(feature_snapshot.get("scan_mode") or "")
        phase25_variant = str(feature_snapshot.get("phase25_variant") or "")
        phase25_prob = feature_snapshot.get("phase25_prob")
        phase25_shadow_variant = str(feature_snapshot.get("phase25_shadow_variant") or "")
        phase25_shadow_prob = feature_snapshot.get("phase25_shadow_prob")
        phase25_recommended_threshold = feature_snapshot.get("phase25_recommended_threshold")
        phase25_signal_direction = str(feature_snapshot.get("phase25_signal_direction") or "").lower()
        try:
            phase25_raw_auc = float(feature_snapshot.get("phase25_raw_auc")) if feature_snapshot.get("phase25_raw_auc") is not None else None
        except Exception:
            phase25_raw_auc = None
        # cv_median_auc is surfaced via feature_snapshot for downstream telemetry
        # (outcome_health tracking, drift dashboards). The reliability gate uses
        # raw_auc + oos_auc + signal_direction; cv_median collapses fold-level
        # variance into a point estimate that hides the regime-break pattern OOS
        # AUC catches directly.
        try:
            phase25_oos_auc = float(feature_snapshot.get("phase25_oos_auc")) if feature_snapshot.get("phase25_oos_auc") is not None else None
        except Exception:
            phase25_oos_auc = None
        try:
            phase25_oos_win_rate_pct = float(feature_snapshot.get("phase25_oos_win_rate_pct")) if feature_snapshot.get("phase25_oos_win_rate_pct") is not None else None
        except Exception:
            phase25_oos_win_rate_pct = None
        try:
            phase25_oos_avg_return_pct = float(feature_snapshot.get("phase25_oos_avg_return_pct")) if feature_snapshot.get("phase25_oos_avg_return_pct") is not None else None
        except Exception:
            phase25_oos_avg_return_pct = None
        expected_edge_score = feature_snapshot.get("expected_edge_score")
        expected_return_1d_pct = feature_snapshot.get("expected_return_1d_pct")
        expected_return_3d_pct = feature_snapshot.get("expected_return_3d_pct")
        entry_timing_risk = compute_entry_timing_risk_features(
            market_subtype=run_market,
            expected_return_1d_pct=expected_return_1d_pct,
            expected_return_3d_pct=expected_return_3d_pct,
            expected_edge_score=expected_edge_score,
            prev_pct_change_1d=feature_snapshot.get("prev_pct_change_1d"),
            prev_pct_change_5d=feature_snapshot.get("prev_pct_change_5d"),
            volume_ratio=volume_ratio,
            prob_clean=prob_clean,
            loss_risk_score=loss_risk_score,
            position=feature_snapshot.get("position") or cand.get("position") or "",
            tier=feature_snapshot.get("tier") or cand.get("tier") or "",
            trend=real_trend or feature_snapshot.get("trend") or cand.get("trend") or "",
        )
        entry_timing_risk_score = float(entry_timing_risk.get("entry_timing_risk_score", 0.0) or 0.0)
        inverted_signal_features = compute_low_prob_high_score_features(
            alpha_score=alpha_score,
            tech_score=feature_snapshot.get("tech_score"),
            ml_prob=prob_5,
            prob_clean=prob_clean,
            phase25_prob=phase25_prob,
            expected_edge_score=expected_edge_score,
        )

        def _snapshot_or_inverted_float(name: str) -> Optional[float]:
            value = feature_snapshot.get(name, inverted_signal_features.get(name))
            if value in (None, ""):
                return None
            try:
                return float(value)
            except Exception:
                return None

        model_prob_available_count = _snapshot_or_inverted_float("model_prob_available_count")
        model_prob_mean = _snapshot_or_inverted_float("model_prob_mean")
        low_model_prob_score = _snapshot_or_inverted_float("low_model_prob_score")
        low_prob_high_score = _snapshot_or_inverted_float("low_prob_high_score")
        expected_edge_inversion_score = _snapshot_or_inverted_float("expected_edge_inversion_score")
        relative_rank_score = cand.get("_relative_rank_score")
        relative_rank_pct = cand.get("_relative_rank_pct")
        regime_adjusted_grade = str(cand.get("_regime_adjusted_grade") or "")
        relative_rank_model = str(cand.get("_relative_rank_model") or "")
        try:
            target_horizon_days = int(feature_snapshot.get("phase25_target_horizon_days") or 0)
        except Exception:
            target_horizon_days = 0
        if target_horizon_days <= 0:
            policy_market = run_market if run_market in ("KOSPI", "KOSDAQ") else str(feature_snapshot.get("market") or run_market)
            target_horizon_days = int(resolve_horizon_policy(policy_market, scan_mode).get("horizon_days") or (1 if quant_lane == "1d" else 3))
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
        theme_rationale: List[str] = []
        theme_risk: List[str] = []
        if explosive_gate_reasons:
            rationale.extend([f"explosive_gate={str(x)}" for x in explosive_gate_reasons[:3]])
        if continuation_gate_reasons:
            rationale.extend([f"continuation_gate={str(x)}" for x in continuation_gate_reasons[:3]])
        if low_model_prob_score is not None or low_prob_high_score is not None:
            rationale.append(
                "inverted_prob_features:"
                f"available={float(model_prob_available_count or 0.0):.0f},"
                f"mean={float(model_prob_mean or 0.0):.1f},"
                f"low_model={float(low_model_prob_score or 0.0):.1f},"
                f"low_prob_high={float(low_prob_high_score or 0.0):.1f}"
            )
        if loss_risk_score > 0:
            rationale.append(f"loss_risk_score={loss_risk_score:.1f}")
            if loss_risk_flags:
                rationale.append("loss_risk_flags=" + ",".join(loss_risk_flags[:4]))
        if entry_timing_risk_score > 0:
            rationale.append(f"entry_timing_risk_score={entry_timing_risk_score:.1f}")
            if entry_timing_risk_score >= 45.0:
                theme_risk.append("ENTRY_TIMING_RISK_HIGH")
        if regime_adjusted_grade:
            rationale.append(
                f"relative_rank={regime_adjusted_grade}:pct={float(relative_rank_pct or 0.0):.3f},"
                f"score={float(relative_rank_score or 0.0):.1f},model={relative_rank_model}"
            )
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

        decision = _apply_phase25_reliability_gate(
            decision=decision,
            phase25_variant=phase25_variant,
            phase25_signal_direction=phase25_signal_direction,
            phase25_raw_auc=phase25_raw_auc,
            phase25_oos_auc=phase25_oos_auc,
            phase25_oos_win_rate_pct=phase25_oos_win_rate_pct,
            phase25_oos_avg_return_pct=phase25_oos_avg_return_pct,
            rationale=rationale,
            theme_risk=theme_risk,
        )
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
            alpha_score=alpha_score,
            low_model_prob_score=low_model_prob_score,
            low_prob_high_score=low_prob_high_score,
            rationale=rationale,
            theme_risk=theme_risk,
        )
        decision = _apply_winner_pattern_filter(
            decision=decision,
            run_market=run_market,
            scan_mode=scan_mode,
            feature_snapshot=feature_snapshot,
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
            phase25_signal_direction=phase25_signal_direction or "",
            phase25_oos_win_rate_pct=phase25_oos_win_rate_pct,
            phase25_oos_avg_return_pct=phase25_oos_avg_return_pct,
        )
        decision = _apply_kospi_swing_edge_promotion(
            decision=decision,
            run_market=run_market,
            scan_mode=scan_mode,
            expected_edge_score=float(expected_edge_score) if expected_edge_score not in (None, "") else None,
            decision_score=float(decision_score) if decision_score not in (None, "") else None,
            rationale=rationale,
        )
        # 2026-05-08: Intraday Trend (breakout=False) 라벨 PRIORITY 격하.
        # cand/feature_snapshot에서 strategy 텍스트 후보 수집.
        _strategy_text = (
            str(cand.get("strategy") or "")
            or str(cand.get("note") or "")
            or str(feature_snapshot.get("strategy") or "")
            or str(feature_snapshot.get("note") or "")
        )
        decision = _apply_intraday_trend_strategy_gate(
            decision=decision,
            scan_mode=scan_mode,
            strategy_text=_strategy_text,
            rationale=rationale,
            theme_risk=theme_risk,
        )
        decision = _apply_loss_risk_gate(
            decision=decision,
            run_market=run_market,
            scan_mode=scan_mode,
            loss_risk_score=loss_risk_score,
            loss_risk_flags=loss_risk_flags,
            rationale=rationale,
            theme_risk=theme_risk,
        )

        if bool(feature_snapshot.get("inference_failed", False)):
            target_rank = min(_decision_rank(decision), _decision_rank("OBSERVE"))
            downgraded = _decision_from_rank(target_rank)
            if downgraded != decision:
                rationale.append("ML_INFERENCE_FAILED_DOWNGRADE")
            decision = downgraded
            if "ML_INFERENCE_FAILED" not in theme_risk:
                theme_risk.append("ML_INFERENCE_FAILED")

        warning_items = _to_warning_items(cand.get("warnings"))
        decision_row = PlannerDecision(
            ticker=ticker,
            stock_name=stock_name,
            priority_rank=idx,
            decision=decision,
            confidence=round(confidence, 3),
            alpha_score=float(alpha_score) if alpha_score not in (None, "") else None,
            tech_score=float(tech_score) if tech_score not in (None, "") else None,
            conviction_score=float(conviction_score) if conviction_score not in (None, "") else None,
            decision_score=float(decision_score) if decision_score not in (None, "") else round(score, 3),
            whale_score=float(whale_score) if whale_score not in (None, "") else None,
            volume=volume,
            volume_ratio=float(volume_ratio) if volume_ratio not in (None, "") else None,
            volume_confirmed=bool(volume_confirmed) if volume_confirmed is not None else None,
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
            phase25_signal_direction=phase25_signal_direction or "",
            phase25_raw_auc=phase25_raw_auc,
            phase25_oos_auc=phase25_oos_auc,
            phase25_oos_win_rate_pct=phase25_oos_win_rate_pct,
            phase25_oos_avg_return_pct=phase25_oos_avg_return_pct,
            expected_edge_score=float(expected_edge_score) if expected_edge_score not in (None, "") else None,
            expected_return_1d_pct=float(expected_return_1d_pct) if expected_return_1d_pct not in (None, "") else None,
            expected_return_3d_pct=float(expected_return_3d_pct) if expected_return_3d_pct not in (None, "") else None,
            model_prob_available_count=model_prob_available_count,
            model_prob_mean=model_prob_mean,
            low_model_prob_score=low_model_prob_score,
            low_prob_high_score=low_prob_high_score,
            expected_edge_inversion_score=expected_edge_inversion_score,
            loss_risk_score=loss_risk_score,
            relative_rank_score=float(relative_rank_score) if relative_rank_score not in (None, "") else None,
            relative_rank_pct=float(relative_rank_pct) if relative_rank_pct not in (None, "") else None,
            regime_adjusted_grade=regime_adjusted_grade,
            relative_rank_model=relative_rank_model,
            quant_priority_score=round(float(basket_priority_score), 3),
            quant_score_1d=round(float(quant_score_1d), 3),
            quant_score_3d=round(float(quant_score_3d), 3),
            selection_lane=quant_lane,
            target_horizon_days=target_horizon_days,
            market_gate=market_gate,
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
                    "tech_score": float(tech_score) if tech_score not in (None, "") else None,
                    "whale_score": float(whale_score) if whale_score not in (None, "") else None,
                    "volume": volume,
                    "volume_ratio": float(volume_ratio) if volume_ratio not in (None, "") else None,
                    "volume_confirmed": bool(volume_confirmed) if volume_confirmed is not None else None,
                    "quant_priority_score": round(float(basket_priority_score), 3),
                    "quant_score_1d": round(float(quant_score_1d), 3),
                    "quant_score_3d": round(float(quant_score_3d), 3),
                    "selection_lane": quant_lane,
                    "active_lane": active_lane,
                    "target_horizon_days": target_horizon_days,
                    "market_gate": market_gate or None,
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
                    "model_prob_available_count": model_prob_available_count,
                    "model_prob_mean": model_prob_mean,
                    "low_model_prob_score": low_model_prob_score,
                    "low_prob_high_score": low_prob_high_score,
                    "expected_edge_inversion_score": expected_edge_inversion_score,
                    "loss_risk_score": loss_risk_score,
                    "relative_rank_score": float(relative_rank_score) if relative_rank_score not in (None, "") else None,
                    "relative_rank_pct": float(relative_rank_pct) if relative_rank_pct not in (None, "") else None,
                    "regime_adjusted_grade": regime_adjusted_grade or None,
                    "relative_rank_model": relative_rank_model or None,
                    "primary_theme": primary_theme or None,
                    "theme_routing_path": str(cand.get("routing_path") or theme_context.get("routing_path") or ""),
                    "reason": "planner_lane_watchlist",
                }
            )
        if decision == "AVOID":
            avoid_list.append(ticker)

    if run_market == "KOSDAQ" and decisions:
        hard_cap = float(get_loss_risk_gate_thresholds("KOSDAQ").get("hard", 65.0))
        has_tradeable_below_hard = any(
            dec.decision != "AVOID"
            and dec.loss_risk_score is not None
            and float(dec.loss_risk_score) < hard_cap
            for dec in decisions
        )
    else:
        hard_cap = 0.0
        has_tradeable_below_hard = True

    kosdaq_relative_floor_enabled = os.getenv("AG_KOSDAQ_RELATIVE_ADMISSION_FLOOR", "0").strip() not in (
        "0",
        "",
        "false",
        "False",
    )
    if run_market == "KOSDAQ" and decisions and not has_tradeable_below_hard and kosdaq_relative_floor_enabled:
        relative_candidates = [
            dec
            for dec in decisions
            if dec.relative_rank_model == KOSDAQ_RELATIVE_RANK_MODEL
            and dec.loss_risk_score is not None
            and float(dec.loss_risk_score) < hard_cap
        ]
        if relative_candidates:
            promoted = sorted(
                relative_candidates,
                key=lambda dec: (
                    float(dec.relative_rank_score or 0.0),
                    -float(dec.loss_risk_score or 0.0),
                ),
                reverse=True,
            )[0]
            promoted.decision = "WATCHLIST_ONLY"
            promoted.rationale.append("kosdaq_relative_admission_floor:no_tradeable_candidate")
            if "KOSDAQ_RELATIVE_ADMISSION_FLOOR" not in promoted.theme_risk:
                promoted.theme_risk.append("KOSDAQ_RELATIVE_ADMISSION_FLOOR")
            if promoted.ticker in avoid_list:
                avoid_list.remove(promoted.ticker)
            if promoted.ticker not in watchlist:
                watchlist.insert(0, promoted.ticker)
                watchlist_meta.insert(
                    0,
                    {
                        "ticker": promoted.ticker,
                        "stock_name": promoted.stock_name,
                        "decision": promoted.decision,
                        "decision_score": promoted.decision_score,
                        "tech_score": promoted.tech_score,
                        "whale_score": promoted.whale_score,
                        "volume": promoted.volume,
                        "volume_ratio": promoted.volume_ratio,
                        "volume_confirmed": promoted.volume_confirmed,
                        "loss_risk_score": promoted.loss_risk_score,
                        "relative_rank_score": promoted.relative_rank_score,
                        "relative_rank_pct": promoted.relative_rank_pct,
                        "regime_adjusted_grade": promoted.regime_adjusted_grade,
                        "relative_rank_model": promoted.relative_rank_model,
                        "market_gate": promoted.market_gate or None,
                        "scanner_timeframe_profile": promoted.scanner_timeframe_profile or None,
                        "kr_universe_role": promoted.kr_universe_role or None,
                        "reason": "kosdaq_relative_admission_floor",
                    },
                )

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
