from __future__ import annotations

import math
from typing import Any, Dict, List


def _num(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _grade(score: float | None) -> str:
    if score is None:
        return "N/A"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B+"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def _fmt_pct(value: Any) -> str:
    numeric = _num(value)
    if numeric is None:
        return "-"
    return f"{numeric:+.1f}%"


def _fmt_num(value: Any, digits: int = 1) -> str:
    numeric = _num(value)
    if numeric is None:
        return "-"
    return f"{numeric:.{digits}f}"


def _first(source: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _weighted_average(parts: List[tuple[float, float]], default: float = 50.0) -> float:
    valid = [(float(v), float(w)) for v, w in parts if w > 0]
    if not valid:
        return default
    weight_sum = sum(w for _, w in valid)
    if weight_sum <= 0:
        return default
    return _clip(sum(_clip(v) * w for v, w in valid) / weight_sum)


def _score_from_positive_pct(value: Any, neutral: float = 50.0, scale: float = 2.0) -> float | None:
    numeric = _num(value)
    if numeric is None:
        return None
    return _clip(neutral + numeric * scale)


def _build_quality_score(candidate: Dict[str, Any], prediction: Dict[str, Any], news: Dict[str, Any]) -> Dict[str, Any]:
    evidence: List[str] = []
    warnings: List[str] = []
    parts: List[tuple[float, float]] = []

    rank_score = _num(_first(candidate, "relative_rank_score", "decision_score", "Decision Score", "score", "buy_score"))
    if rank_score is not None:
        parts.append((rank_score, 0.28))
        evidence.append(f"스캐너/플래너 품질 점수 {_fmt_num(rank_score)}")

    accuracy = _num(_first(candidate, "phase25_oos_win_rate_pct", "prob_clean", "accuracy"))
    if accuracy is not None:
        parts.append((accuracy, 0.18))
        evidence.append(f"검증/정밀 확률 {_fmt_pct(accuracy)}")

    expected_edge = _num(prediction.get("expected_edge_score") or candidate.get("expected_edge_score"))
    if expected_edge is not None:
        edge_score = _clip(50.0 + expected_edge * 5.0)
        parts.append((edge_score, 0.16))
        evidence.append(f"기대 엣지 {expected_edge:.1f}")

    volume_ratio = _num(_first(candidate, "volume_ratio", "volume_ratio_20d"))
    if volume_ratio is not None:
        volume_score = _clip(45.0 + min(volume_ratio, 4.0) * 13.0)
        parts.append((volume_score, 0.14))
        evidence.append(f"거래대금/거래량 유입 x{volume_ratio:.2f}")

    trend = str(_first(candidate, "real_trend", "trend", "Trend") or "").upper()
    if trend:
        trend_score = {"UP": 75.0, "MIXED": 55.0, "NEUTRAL": 50.0, "DOWN": 35.0}.get(trend, 50.0)
        parts.append((trend_score, 0.10))
        evidence.append(f"추세 {trend}")

    news_score = _num(news.get("sentiment_score"))
    if news_score is not None:
        parts.append((_clip(50.0 + news_score * 12.0), 0.08))
        evidence.append(f"뉴스 감성 {_fmt_num(news_score, 2)}")

    fundamental_parts: List[tuple[float, float]] = []
    for key in ("revenue_growth_pct", "sales_growth_pct", "operating_profit_growth_pct", "op_margin_change_pct"):
        score = _score_from_positive_pct(candidate.get(key), scale=1.4)
        if score is not None:
            fundamental_parts.append((score, 1.0))
    for key in ("order_backlog_growth_pct", "consensus_revision_pct"):
        score = _score_from_positive_pct(candidate.get(key), scale=1.2)
        if score is not None:
            fundamental_parts.append((score, 1.0))
    if fundamental_parts:
        parts.append((_weighted_average(fundamental_parts), 0.16))
        evidence.append("실적/수주/컨센서스 개선 데이터 반영")
        fundamental_status = "available"
    else:
        fundamental_status = "not_connected"
        warnings.append("실적·수주잔고·컨센서스 데이터는 현재 자동 정밀분석 원천에 미연결")

    score = round(_weighted_average(parts), 1)
    return {
        "score": score,
        "grade": _grade(score),
        "label": "종목 품질",
        "source_status": fundamental_status,
        "evidence": evidence[:6],
        "warnings": warnings,
    }


def _chase_filters(price: Dict[str, Any]) -> List[Dict[str, Any]]:
    ret5 = _num(price.get("return_5d_pct"))
    ret20 = _num(price.get("return_20d_pct"))
    ret60 = _num(price.get("return_60d_pct"))
    high_gap = _num(price.get("pct_from_52w_high"))
    volume_ratio = _num(price.get("volume_ratio_20d"))
    gap_after_long = bool(price.get("gap_up_after_long_bullish"))

    within_high_5 = high_gap is not None and high_gap >= -5.0
    volume_spike = volume_ratio is not None and volume_ratio >= 2.0
    return [
        {
            "code": "RET_5D_GT_25",
            "label": "최근 5거래일 상승률 > 25%",
            "value": _fmt_pct(ret5),
            "triggered": bool(ret5 is not None and ret5 > 25.0),
            "severity": "high",
        },
        {
            "code": "RET_20D_GT_60",
            "label": "최근 20거래일 상승률 > 60%",
            "value": _fmt_pct(ret20),
            "triggered": bool(ret20 is not None and ret20 > 60.0),
            "severity": "very_high",
        },
        {
            "code": "RET_60D_GT_150",
            "label": "최근 60거래일 상승률 > 150%",
            "value": _fmt_pct(ret60),
            "triggered": bool(ret60 is not None and ret60 > 150.0),
            "severity": "block",
        },
        {
            "code": "NEAR_52W_HIGH_VOLUME_SPIKE",
            "label": "52주 고점 -5% 이내 + 거래량 폭발",
            "value": f"{_fmt_pct(high_gap)} / x{_fmt_num(volume_ratio, 2)}",
            "triggered": bool(within_high_5 and volume_spike),
            "severity": "very_high",
        },
        {
            "code": "LONG_CANDLE_GAP_UP",
            "label": "장대양봉 다음날 갭상승 출발",
            "value": _fmt_pct(price.get("gap_up_pct")),
            "triggered": gap_after_long,
            "severity": "high",
        },
    ]


def _build_upside_score(price: Dict[str, Any]) -> Dict[str, Any]:
    score = 82.0
    evidence: List[str] = []
    warnings: List[str] = []
    filters = _chase_filters(price)

    ret5 = _num(price.get("return_5d_pct"))
    ret20 = _num(price.get("return_20d_pct"))
    ret60 = _num(price.get("return_60d_pct"))
    high_gap = _num(price.get("pct_from_52w_high"))
    volume_ratio = _num(price.get("volume_ratio_20d"))

    if ret5 is None or ret20 is None:
        warnings.append("5D/20D 상승률 계산을 위한 가격 이력이 부족")
    if ret60 is None:
        warnings.append("60D 상승률 계산을 위한 가격 이력이 부족")

    if ret5 is not None:
        evidence.append(f"5D {_fmt_pct(ret5)}")
        if ret5 > 25:
            score -= 24
        elif ret5 > 15:
            score -= 12
    if ret20 is not None:
        evidence.append(f"20D {_fmt_pct(ret20)}")
        if ret20 > 60:
            score -= 34
        elif ret20 > 35:
            score -= 22
        elif ret20 > 20:
            score -= 10
    if ret60 is not None:
        evidence.append(f"60D {_fmt_pct(ret60)}")
        if ret60 > 150:
            score -= 48
        elif ret60 > 80:
            score -= 28
        elif ret60 > 40:
            score -= 12
    if high_gap is not None:
        evidence.append(f"52주 고점 대비 {_fmt_pct(high_gap)}")
        if high_gap >= -5.0:
            score -= 14
    if volume_ratio is not None and volume_ratio >= 2.0 and high_gap is not None and high_gap >= -5.0:
        score -= 12
        evidence.append(f"고점권 거래량 x{volume_ratio:.2f}")

    score = round(_clip(score), 1)
    triggered = [row for row in filters if row["triggered"]]
    if any(row["severity"] == "block" for row in triggered):
        chase_level = "신규 진입 금지"
    elif any(row["severity"] == "very_high" for row in triggered):
        chase_level = "매우 높음"
    elif any(row["severity"] == "high" for row in triggered):
        chase_level = "높음"
    elif score < 55:
        chase_level = "주의"
    else:
        chase_level = "낮음"
    return {
        "score": score,
        "grade": _grade(score),
        "label": "상승 여력",
        "chase_risk_level": chase_level,
        "filters": filters,
        "evidence": evidence[:6],
        "warnings": warnings,
    }


def _build_timing_score(price: Dict[str, Any]) -> Dict[str, Any]:
    close = _num(price.get("current_price"))
    ma5 = _num(price.get("ma5"))
    ma20 = _num(price.get("ma20"))
    prior_high = _num(price.get("prior_20d_high"))
    volume_ratio = _num(price.get("volume_ratio_20d"))
    gap_up = _num(price.get("gap_up_pct"))
    close_location = _num(price.get("close_location_pct"))

    score = 50.0
    evidence: List[str] = []
    warnings: List[str] = []

    if close is None:
        warnings.append("현재가 데이터 부족")
    if close is not None and ma20 is not None and ma20 > 0:
        dist20 = (close - ma20) / ma20 * 100.0
        evidence.append(f"20일선 대비 {_fmt_pct(dist20)}")
        if -2.0 <= dist20 <= 8.0:
            score += 22
        elif 8.0 < dist20 <= 18.0:
            score += 8
        elif dist20 < -2.0:
            score -= 16
        else:
            score -= 10
    else:
        warnings.append("20일선 판단 데이터 부족")

    if close is not None and ma5 is not None and ma5 > 0:
        dist5 = (close - ma5) / ma5 * 100.0
        evidence.append(f"5일선 대비 {_fmt_pct(dist5)}")
        score += 14 if dist5 >= 0 else -8

    if close is not None and prior_high is not None and prior_high > 0:
        breakout_gap = (close - prior_high) / prior_high * 100.0
        evidence.append(f"전고점 대비 {_fmt_pct(breakout_gap)}")
        if breakout_gap >= 0:
            score += 14
        elif breakout_gap >= -3.0:
            score += 8
        else:
            score -= 6

    if volume_ratio is not None:
        evidence.append(f"거래량/20D x{volume_ratio:.2f}")
        if 1.2 <= volume_ratio <= 2.8:
            score += 14
        elif volume_ratio > 2.8:
            score += 4
        elif volume_ratio < 0.7:
            score -= 8

    if gap_up is not None and gap_up >= 3.0:
        score -= 12
        evidence.append(f"갭상승 {_fmt_pct(gap_up)}")
    if bool(price.get("gap_up_after_long_bullish")):
        score -= 18
        warnings.append("장대양봉 다음날 갭상승: 9:30 전 추격 금지")
    if close_location is not None:
        evidence.append(f"당일 종가 위치 {_fmt_num(close_location)}%")
        if close_location < 25:
            score -= 10
            warnings.append("종가가 당일 저점권")
        elif close_location > 65:
            score += 8

    score = round(_clip(score), 1)
    if score >= 75:
        timing_label = "양호"
    elif score >= 60:
        timing_label = "조건부 양호"
    elif score >= 45:
        timing_label = "확인 필요"
    else:
        timing_label = "불량"
    return {
        "score": score,
        "grade": _grade(score),
        "label": "진입 타이밍",
        "timing_label": timing_label,
        "evidence": evidence[:7],
        "warnings": warnings,
    }


def _final_judgment(
    quality: Dict[str, Any],
    upside: Dict[str, Any],
    timing: Dict[str, Any],
    loss_risk_score: Any,
) -> Dict[str, Any]:
    q = _num(quality.get("score")) or 0.0
    u = _num(upside.get("score")) or 0.0
    t = _num(timing.get("score")) or 0.0
    loss = _num(loss_risk_score)
    chase = str(upside.get("chase_risk_level") or "")

    if chase == "신규 진입 금지" or (loss is not None and loss >= 65.0):
        return {
            "action": "매수 금지",
            "tone": "danger",
            "summary": "과열 또는 손실위험 하드캡으로 신규 진입을 막습니다.",
        }
    if chase in {"매우 높음", "높음"}:
        return {
            "action": "눌림 대기",
            "tone": "risk",
            "summary": "종목은 볼 수 있지만 가격 부담이 커서 추격보다 눌림 확인이 필요합니다.",
        }
    if q >= 70 and u >= 65 and t >= 75 and (loss is None or loss < 45):
        return {
            "action": "즉시 매수 가능",
            "tone": "good",
            "summary": "품질, 상승 여력, 진입 타이밍이 동시에 양호합니다.",
        }
    if q >= 65 and u >= 55 and t >= 60:
        return {
            "action": "조건부 매수 가능",
            "tone": "focus",
            "summary": "조건은 대체로 맞지만 지정가/손절 기준을 지켜야 합니다.",
        }
    if q >= 65 and t < 60:
        return {
            "action": "돌파 확인",
            "tone": "caution",
            "summary": "종목 품질은 있으나 지금 자리는 방향 확인이 부족합니다.",
        }
    return {
        "action": "관망",
        "tone": "neutral",
        "summary": "품질, 상승 여력, 타이밍 중 하나 이상이 부족합니다.",
    }


def build_entry_readiness_analysis(
    *,
    candidate: Dict[str, Any],
    price: Dict[str, Any],
    prediction: Dict[str, Any],
    trade_plan: Dict[str, Any],
    news: Dict[str, Any] | None = None,
    loss_risk_score: Any = None,
) -> Dict[str, Any]:
    """Build a display-side entry-readiness analysis without changing ranking.

    The scanner/planner still owns candidate selection. This helper converts
    existing report evidence into a practical buyability view.
    """
    candidate = candidate if isinstance(candidate, dict) else {}
    price = price if isinstance(price, dict) else {}
    prediction = prediction if isinstance(prediction, dict) else {}
    trade_plan = trade_plan if isinstance(trade_plan, dict) else {}
    news = news if isinstance(news, dict) else {}

    merged_candidate = {**candidate, **price}
    quality = _build_quality_score(merged_candidate, prediction, news)
    upside = _build_upside_score(price)
    timing = _build_timing_score(price)
    judgment = _final_judgment(quality, upside, timing, loss_risk_score)
    warnings: List[str] = []
    for block in (quality, upside, timing):
        warnings.extend([str(item) for item in block.get("warnings", []) if str(item).strip()])

    return {
        "version": "entry_readiness_v1",
        "quality": quality,
        "upside": upside,
        "timing": timing,
        "chase_risk_level": upside.get("chase_risk_level"),
        "final_buy_judgment": judgment,
        "trade_plan_summary": {
            "entry_policy": trade_plan.get("entry_policy"),
            "entry_reference_price": trade_plan.get("entry_reference_price"),
            "target_tp_pct": trade_plan.get("target_tp_pct"),
            "stop_sl_pct": trade_plan.get("stop_sl_pct"),
            "hold_days": trade_plan.get("hold_days"),
        },
        "warnings": warnings[:8],
    }


__all__ = ["build_entry_readiness_analysis"]
