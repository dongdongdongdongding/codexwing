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


def _fmt_price(value: Any) -> str:
    numeric = _num(value)
    if numeric is None:
        return "-"
    if numeric >= 1000:
        return f"{numeric:,.0f}원"
    return f"{numeric:.2f}"


def _nearest_support(price: Dict[str, Any], reference: float) -> tuple[str, float] | None:
    candidates: List[tuple[str, float]] = []
    for label, key in (("5일선", "ma5"), ("20일선", "ma20"), ("20일 저점", "range_20d_low")):
        level = _num(price.get(key))
        if level is not None and 0 < level <= reference:
            candidates.append((label, level))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])


def _resistance_level(price: Dict[str, Any], reference: float) -> tuple[str, float] | None:
    candidates: List[tuple[str, float]] = []
    for label, key in (("전고점", "prior_20d_high"), ("20일 고점", "range_20d_high"), ("52주 고점", "high_52w")):
        level = _num(price.get(key))
        if level is not None and level > 0:
            candidates.append((label, level))
    if not candidates:
        return None
    above = [item for item in candidates if item[1] >= reference]
    if above:
        return min(above, key=lambda item: item[1])
    return max(candidates, key=lambda item: item[1])


def _build_data_backed_action_plan(
    *,
    price: Dict[str, Any],
    trade_plan: Dict[str, Any],
    judgment: Dict[str, Any],
    loss_risk_score: Any,
) -> Dict[str, Any]:
    action = str(judgment.get("action") or "관망")
    current = _num(price.get("current_price")) or _num(trade_plan.get("entry_reference_price"))
    entry_high = _num(trade_plan.get("entry_zone_high")) or current
    entry_low = _num(trade_plan.get("entry_zone_low"))
    stop_price = _num(trade_plan.get("stop_price"))
    target_price = _num(trade_plan.get("target_price"))
    reference = entry_high or current
    support = _nearest_support(price, reference) if reference is not None else None
    resistance = _resistance_level(price, reference) if reference is not None else None

    warnings: List[str] = []
    if current is None:
        warnings.append("현재가 기반 액션 플랜 산출 불가")
    if support is None:
        warnings.append("지지선 데이터 부족: 손절 기준은 기본 손절가만 사용")
    if resistance is None:
        warnings.append("저항선 데이터 부족: 돌파 조건은 진입 상단 기준")

    support_label, support_price = support if support is not None else ("기준가", reference or 0.0)
    resistance_label, resistance_price = resistance if resistance is not None else ("진입 상단", entry_high or reference or 0.0)
    breakout_price = resistance_price * 1.005 if resistance_price else entry_high
    pullback_price = support_price if support_price else entry_low
    invalidation_price = stop_price
    if invalidation_price is None and support_price:
        invalidation_price = support_price * 0.985

    if action == "매수 금지":
        mode = "blocked"
        primary_condition = "신규 매수 금지"
        secondary_condition = (
            f"{support_label} {_fmt_price(support_price)} 지지 확인 후 "
            f"{resistance_label} {_fmt_price(breakout_price)} 재돌파 시 재검토"
        )
        blocked_reason = str(judgment.get("summary") or "과열 또는 손실위험")
    elif action == "눌림 대기":
        mode = "pullback_wait"
        primary_condition = f"{support_label} {_fmt_price(support_price)} 부근 눌림 지지 확인"
        secondary_condition = f"{resistance_label} {_fmt_price(breakout_price)} 재돌파 + 거래량 재유입"
        blocked_reason = ""
    elif action == "돌파 확인":
        mode = "breakout_confirm"
        primary_condition = f"{resistance_label} {_fmt_price(breakout_price)} 돌파 확인"
        secondary_condition = f"돌파 실패 시 {support_label} {_fmt_price(support_price)} 지지까지 대기"
        blocked_reason = ""
    elif action in {"즉시 매수 가능", "조건부 매수 가능"}:
        mode = "entry_allowed"
        primary_condition = (
            f"{_fmt_price(entry_low)}~{_fmt_price(entry_high)} 구간에서 "
            f"{support_label} 지지 유지"
        )
        secondary_condition = f"{resistance_label} {_fmt_price(breakout_price)} 돌파 시 추가 확인"
        blocked_reason = ""
    else:
        mode = "watch"
        primary_condition = f"{support_label} {_fmt_price(support_price)} 지지 또는 {resistance_label} 돌파 확인 전 관망"
        secondary_condition = f"방향 확인 후 {_fmt_price(entry_low)}~{_fmt_price(entry_high)} 재산정"
        blocked_reason = ""

    stop_condition = (
        f"{_fmt_price(invalidation_price)} 이탈"
        if invalidation_price is not None
        else f"{support_label} 이탈"
    )
    if support is not None and invalidation_price is not None:
        stop_condition = f"{support_label} {_fmt_price(support_price)} 지지 실패 또는 {_fmt_price(invalidation_price)} 이탈"

    data_points = {
        "current_price": current,
        "ma5": _num(price.get("ma5")),
        "ma20": _num(price.get("ma20")),
        "prior_20d_high": _num(price.get("prior_20d_high")),
        "range_20d_low": _num(price.get("range_20d_low")),
        "range_20d_high": _num(price.get("range_20d_high")),
        "high_52w": _num(price.get("high_52w")),
        "volume_ratio_20d": _num(price.get("volume_ratio_20d")),
        "return_5d_pct": _num(price.get("return_5d_pct")),
        "return_20d_pct": _num(price.get("return_20d_pct")),
        "return_60d_pct": _num(price.get("return_60d_pct")),
        "loss_risk_score": _num(loss_risk_score),
    }
    available = [key for key, value in data_points.items() if value is not None]

    entry_strategy = {
        "mode": mode,
        "primary_condition": primary_condition,
        "secondary_condition": secondary_condition,
        "blocked_reason": blocked_reason,
        "entry_zone_low": entry_low,
        "entry_zone_high": entry_high,
        "pullback_support_label": support_label,
        "pullback_support_price": round(support_price, 4) if support_price else None,
        "breakout_label": resistance_label,
        "breakout_price": round(breakout_price, 4) if breakout_price else None,
        "data_source": "price_snapshot_ma_volume_return",
        "evidence": [
            f"현재가 {_fmt_price(current)}",
            f"{support_label} {_fmt_price(support_price)}",
            f"{resistance_label} {_fmt_price(resistance_price)}",
            f"거래량/20D x{_fmt_num(price.get('volume_ratio_20d'), 2)}",
        ],
    }
    risk_management = {
        "stop_condition": stop_condition,
        "stop_price": round(invalidation_price, 4) if invalidation_price is not None else None,
        "target_price": target_price,
        "risk_reward": trade_plan.get("risk_reward"),
        "loss_risk_score": _num(loss_risk_score),
        "invalidation": "지지선 이탈 또는 돌파 실패 후 장대음봉 발생",
        "data_source": "support_resistance_stop_from_price_snapshot",
        "warnings": warnings,
    }
    return {
        "entry_strategy": entry_strategy,
        "risk_management": risk_management,
        "data_coverage": {
            "available_fields": available,
            "available_count": len(available),
            "required_fields": list(data_points.keys()),
            "coverage_pct": round(len(available) / len(data_points) * 100.0, 1),
        },
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
    action_plan = _build_data_backed_action_plan(
        price=price,
        trade_plan=trade_plan,
        judgment=judgment,
        loss_risk_score=loss_risk_score,
    )
    warnings: List[str] = []
    for block in (quality, upside, timing):
        warnings.extend([str(item) for item in block.get("warnings", []) if str(item).strip()])
    warnings.extend(action_plan.get("risk_management", {}).get("warnings", []))

    return {
        "version": "entry_readiness_v1",
        "quality": quality,
        "upside": upside,
        "timing": timing,
        "chase_risk_level": upside.get("chase_risk_level"),
        "final_buy_judgment": judgment,
        "entry_strategy": action_plan["entry_strategy"],
        "risk_management": action_plan["risk_management"],
        "data_coverage": action_plan["data_coverage"],
        "trade_plan_summary": {
            "entry_policy": trade_plan.get("entry_policy"),
            "entry_reference_price": trade_plan.get("entry_reference_price"),
            "entry_zone_low": trade_plan.get("entry_zone_low"),
            "entry_zone_high": trade_plan.get("entry_zone_high"),
            "target_price": trade_plan.get("target_price"),
            "stop_price": trade_plan.get("stop_price"),
            "target_tp_pct": trade_plan.get("target_tp_pct"),
            "stop_sl_pct": trade_plan.get("stop_sl_pct"),
            "hold_days": trade_plan.get("hold_days"),
            "risk_reward": trade_plan.get("risk_reward"),
        },
        "warnings": warnings[:8],
    }


__all__ = ["build_entry_readiness_analysis"]
