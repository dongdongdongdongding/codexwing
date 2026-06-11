from __future__ import annotations

import math
from typing import Any, Dict, Mapping


POLICY_VERSION = "kis_shadow_dynamic_exit_policy_v2_touch5_dd10"
FRICTION_PCT = 0.35


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except Exception:
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _max_present(*values: Any) -> float | None:
    numbers = [_safe_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    return max(numbers) if numbers else None


def _risk_level(score: float, *, bad_path: float, stop5: float, min_low: float) -> str:
    if score >= 80.0 or bad_path >= 45.0 or stop5 >= 35.0 or min_low <= -18.0:
        return "EXTREME"
    if score >= 60.0 or bad_path >= 30.0 or stop5 >= 20.0 or min_low <= -14.0:
        return "HIGH"
    if score >= 40.0 or bad_path >= 15.0 or stop5 >= 10.0 or min_low <= -10.0:
        return "MODERATE"
    return "LOW"


def build_kis_shadow_exit_policy(
    *,
    features: Mapping[str, Any],
    metrics: Mapping[str, Any],
    identity: Mapping[str, Any],
    market: str,
) -> Dict[str, Any]:
    """Create a deterministic shadow-only TP/SL plan from model and path risk.

    This is not a production execution policy. It makes the remaining path risk
    explicit and keeps high-risk candidates on tighter TP/SL and shorter holds.
    """

    prior_score = _max_present(
        features.get("close_failure_prior_ticker_risk_score"),
        features.get("close_failure_prior_theme_risk_score"),
        features.get("close_failure_prior_kis_theme_risk_score"),
        features.get("close_failure_prior_kis_sector_risk_score"),
        features.get("close_failure_prior_market_risk_score"),
    )
    label = str(identity.get("label") or "").lower()
    is_touch5_dd10 = label == "touch5_dd10_5d"
    bad_path = _safe_float(metrics.get("bad_path_pct"), 100.0) or 100.0
    stop5 = _safe_float(metrics.get("stop5_pct"), 100.0) or 100.0
    min_low = _safe_float(metrics.get("min_min_low_5d_pct"), 0.0) or 0.0
    stop_before_target = _safe_float(metrics.get("stop_before_target_5d_pct"), stop5) or stop5
    if is_touch5_dd10:
        score = max(prior_score or 0.0, max(0.0, -10.0 - min_low) * 10.0)
        if min_low < -12.0 or (prior_score is not None and prior_score >= 80.0):
            level = "HIGH"
        elif min_low < -10.0 or (prior_score is not None and prior_score >= 60.0):
            level = "MODERATE"
        else:
            level = "LOW"
    else:
        score = max(prior_score or 0.0, bad_path, stop5 * 1.25, stop_before_target * 1.15, max(0.0, abs(min_low) * 3.0))
        level = _risk_level(score, bad_path=bad_path, stop5=stop5, min_low=min_low)

    base_target = 10.0 if label.startswith("touch10") else 5.0
    avg_mfe = _safe_float(metrics.get("avg_max_high_5d_pct"), 0.0) or 0.0
    hit10 = _safe_float(metrics.get("hit10_5d_pct"), 0.0) or 0.0

    reason_codes = []
    if prior_score is not None:
        reason_codes.append(f"prior_risk_score={prior_score:.1f}")
    if is_touch5_dd10:
        reason_codes.append("touch5_dd10_target_plus5_drawdown_minus10")
        if min_low < -10.0:
            reason_codes.append("min_low_below_10")
    else:
        if bad_path > 15.0:
            reason_codes.append("bad_path_gt_15")
        if stop5 > 10.0:
            reason_codes.append("stop5_gt_10")
        if stop_before_target > 15.0:
            reason_codes.append("stop_before_target_gt_15")
        if min_low < -12.0:
            reason_codes.append("min_low_below_12")

    if is_touch5_dd10:
        target = 5.0
        stop = -10.0
        hold = 5
        sizing = "half_size_shadow_review"
        exit_bias = "5일 내 +5% 터치 우선, -10% 하방 제한"
        early_exit_rules = [
            "5거래일 이내 +5% 목표가를 터치하면 익절 우선",
            "진입가 대비 -10% 이탈 시 실패 경로로 보고 청산/재검토",
            "KIS 수급이 외인+기관 동반 매도로 전환되면 신규 추격 금지",
            "테마/뉴스 위험 태그가 새로 붙으면 보유 축소 검토",
        ]
    elif level in {"EXTREME", "HIGH"}:
        target = 5.0
        stop = -3.0
        hold = 3
        sizing = "half_size_shadow_review"
        exit_bias = "빠른 익절/짧은 보유"
        early_exit_rules = [
            "1거래일 종가가 진입가 대비 -3% 이하이면 재평가",
            "KIS 수급이 외인+기관 동반 매도로 전환되면 재평가",
            "테마/뉴스 위험 태그가 새로 붙으면 신규 추격 금지",
            "목표가 터치 후 종가가 목표가 아래로 되밀리면 익절 우선",
        ]
    elif level == "MODERATE":
        target = 7.0 if avg_mfe >= 12.0 and hit10 >= 50.0 else base_target
        stop = -4.0
        hold = 5
        sizing = "normal_shadow_watch"
        exit_bias = "중간 목표/표준 보유"
        early_exit_rules = [
            "1거래일 종가가 진입가 대비 -3% 이하이면 재평가",
            "KIS 수급이 외인+기관 동반 매도로 전환되면 재평가",
            "테마/뉴스 위험 태그가 새로 붙으면 신규 추격 금지",
            "목표가 터치 후 종가가 목표가 아래로 되밀리면 익절 우선",
        ]
    else:
        target = 10.0 if (base_target >= 10.0 or avg_mfe >= 18.0 or hit10 >= 65.0) else 7.0
        stop = -5.0
        hold = 5
        sizing = "normal_shadow_watch"
        exit_bias = "추세 유지 허용"
        early_exit_rules = [
            "1거래일 종가가 진입가 대비 -3% 이하이면 재평가",
            "KIS 수급이 외인+기관 동반 매도로 전환되면 재평가",
            "테마/뉴스 위험 태그가 새로 붙으면 신규 추격 금지",
            "목표가 터치 후 종가가 목표가 아래로 되밀리면 익절 우선",
        ]

    expected_avg = _safe_float(metrics.get("avg_5d_pct"))
    net_avg = round(expected_avg - FRICTION_PCT, 4) if expected_avg is not None else None
    return {
        "version": POLICY_VERSION,
        "shadow_only": True,
        "market": str(market or "").upper(),
        "entry_policy": "scan_reference_plus_2pct_assumption",
        "entry_premium_assumption_pct": 2.0,
        "target_tp_pct": target,
        "stop_sl_pct": stop,
        "hold_days": hold,
        "position_sizing": sizing,
        "exit_bias": exit_bias,
        "risk_level": level,
        "risk_score": round(score, 4),
        "prior_risk_score": round(prior_score, 4) if prior_score is not None else None,
        "bad_path_pct": bad_path,
        "stop5_pct": stop5,
        "stop_before_target_5d_pct": stop_before_target,
        "target_before_stop_5d_pct": _safe_float(metrics.get("target_before_stop_5d_pct")),
        "min_min_low_5d_pct": min_low,
        "expected_avg_5d_pct": expected_avg,
        "expected_net_avg_5d_pct": net_avg,
        "friction_pct": FRICTION_PCT,
        "reason_codes": reason_codes,
        "early_exit_rules": early_exit_rules,
    }
