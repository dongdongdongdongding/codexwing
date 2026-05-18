from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

from modules.entry_readiness import build_entry_readiness_analysis
from modules.practical_entry_gate import evaluate_practical_entry_gate
from modules.ui_helpers import build_kr_shadow_gate_records, build_top5_plus_exception_records, enrich_signal_rows_with_planner_trace


REPORT_VERSION = "top_deep_report_v1"
LOCAL_REPORT_DIR = Path("runtime_state/reports/top_deep")

SCAN_DEEP_REPORT_COLUMNS = {
    "report_id",
    "report_version",
    "run_id",
    "market",
    "scan_mode",
    "rank",
    "ticker",
    "stock_name",
    "generated_at",
    "signal_label",
    "decision",
    "decision_bucket",
    "buy_score",
    "accuracy",
    "day_change_pct",
    "loss_risk_score",
    "selection_alignment",
    "risk_flags",
    "rationale",
    "prediction",
    "selection_thesis",
    "risk_overrides",
    "entry_action",
    "practical_entry_gate",
    "trade_plan",
    "flow",
    "theme",
    "price",
    "news",
    "data_warnings",
}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() != "none"
    if isinstance(value, float):
        return not (math.isnan(value) or math.isinf(value))
    return True


def _safe_float(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return round(numeric, 4)


def _safe_int(value: Any) -> int | None:
    try:
        numeric = int(float(value))
    except (TypeError, ValueError):
        return None
    return numeric


def _ticker(row: Dict[str, Any]) -> str:
    return str(row.get("ticker") or row.get("Ticker") or row.get("티커") or "").strip()


def _first_present(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if _present(value):
            return value
    return None


def _coerce_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _coerce_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_coerce_jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    return value


def _planner_trace_by_ticker(planner_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    traces: Dict[str, Dict[str, Any]] = {}
    payload = planner_payload if isinstance(planner_payload, dict) else {}
    for section in ("decisions", "watchlist_meta"):
        for row in payload.get(section, []) or []:
            if not isinstance(row, dict):
                continue
            ticker = _ticker(row)
            if ticker and ticker not in traces:
                traces[ticker] = dict(row)
    return traces


def _select_top_candidates(
    scan_rows: List[Dict[str, Any]],
    planner_payload: Dict[str, Any],
    limit: int,
) -> List[Dict[str, Any]]:
    ranked_rows = []
    for idx, row in enumerate(scan_rows or [], start=1):
        if not isinstance(row, dict):
            continue
        copy = dict(row)
        copy.setdefault("_raw_scan_rank", idx)
        ranked_rows.append(copy)
    enriched = enrich_signal_rows_with_planner_trace(ranked_rows, planner_payload)
    rows = [row for row in enriched if _ticker(row)]
    groups = build_top5_plus_exception_records(
        rows,
        planner_payload,
        top_limit=max(int(limit or 0), 0),
        exception_limit=5,
    )
    shadow_groups = build_kr_shadow_gate_records(rows, planner_payload, limit=5)
    shadow_rows = shadow_groups["combined"]
    seen_shadow = {str(row.get("ticker") or "") for row in shadow_rows}
    standard_rows = [row for row in groups["combined"] if str(row.get("ticker") or "") not in seen_shadow]
    return shadow_rows + standard_rows


def _fetch_price_snapshot(ticker: str) -> Dict[str, Any]:
    warnings: List[str] = []
    try:
        hist = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
    except Exception as exc:
        return {"warnings": [f"price_fetch_failed:{exc}"], "ohlcv_tail": []}

    if hist is None or hist.empty:
        return {"warnings": ["price_history_empty"], "ohlcv_tail": []}

    hist = hist.dropna(subset=["Close"]).copy()
    latest = hist.iloc[-1]
    close = _safe_float(latest.get("Close"))
    prev_close = _safe_float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
    open_price = _safe_float(latest.get("Open"))
    high = _safe_float(latest.get("High"))
    low = _safe_float(latest.get("Low"))
    day_change_pct = None
    if close is not None and prev_close not in (None, 0):
        day_change_pct = round((close - prev_close) / prev_close * 100.0, 4)
    gap_up_pct = None
    if open_price is not None and prev_close not in (None, 0):
        gap_up_pct = round((open_price - prev_close) / prev_close * 100.0, 4)
    candle_return_pct = None
    if close is not None and open_price not in (None, 0):
        candle_return_pct = round((close - open_price) / open_price * 100.0, 4)
    close_location_pct = None
    if close is not None and high is not None and low is not None and high > low:
        close_location_pct = round((close - low) / (high - low) * 100.0, 4)
    volume = _safe_int(latest.get("Volume"))
    vol20 = _safe_float(hist["Volume"].tail(20).mean()) if "Volume" in hist else None
    volume_ratio = None
    if volume is not None and vol20 not in (None, 0):
        volume_ratio = round(float(volume) / float(vol20), 4)
    ma5 = _safe_float(hist["Close"].tail(5).mean()) if len(hist) >= 5 else None
    ma20 = _safe_float(hist["Close"].tail(20).mean()) if len(hist) >= 20 else None
    ma60 = _safe_float(hist["Close"].tail(60).mean()) if len(hist) >= 60 else None
    prior_20d_high = _safe_float(hist["High"].iloc[:-1].tail(20).max()) if "High" in hist and len(hist) >= 21 else None
    high_52w = _safe_float(hist["High"].tail(252).max()) if "High" in hist else None
    pct_from_52w_high = None
    if close is not None and high_52w not in (None, 0):
        pct_from_52w_high = round((close - high_52w) / high_52w * 100.0, 4)

    def _lookback_return(days: int) -> float | None:
        if close is None or len(hist) <= days:
            return None
        base = _safe_float(hist["Close"].iloc[-days - 1])
        if base in (None, 0):
            return None
        return round((close - base) / base * 100.0, 4)

    prev_candle_return_pct = None
    if len(hist) >= 2:
        prev = hist.iloc[-2]
        prev_open = _safe_float(prev.get("Open"))
        prev_close_for_candle = _safe_float(prev.get("Close"))
        if prev_open not in (None, 0) and prev_close_for_candle is not None:
            prev_candle_return_pct = round((prev_close_for_candle - prev_open) / prev_open * 100.0, 4)
    gap_up_after_long_bullish = bool(
        prev_candle_return_pct is not None
        and prev_candle_return_pct >= 8.0
        and gap_up_pct is not None
        and gap_up_pct >= 3.0
    )
    trend = "UNKNOWN"
    if close is not None and ma20 is not None and ma60 is not None:
        if close >= ma20 >= ma60:
            trend = "UP"
        elif close <= ma20 <= ma60:
            trend = "DOWN"
        else:
            trend = "MIXED"
    if len(hist) < 60:
        warnings.append("price_history_lt_60d")

    ohlcv_tail = []
    for idx, row in hist.tail(30).iterrows():
        ohlcv_tail.append(
            {
                "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                "open": _safe_float(row.get("Open")),
                "high": _safe_float(row.get("High")),
                "low": _safe_float(row.get("Low")),
                "close": _safe_float(row.get("Close")),
                "volume": _safe_int(row.get("Volume")),
            }
        )

    return {
        "warnings": warnings,
        "current_price": close,
        "prev_close": prev_close,
        "day_change_pct": day_change_pct,
        "gap_up_pct": gap_up_pct,
        "candle_return_pct": candle_return_pct,
        "prev_candle_return_pct": prev_candle_return_pct,
        "gap_up_after_long_bullish": gap_up_after_long_bullish,
        "close_location_pct": close_location_pct,
        "volume": volume,
        "volume_ratio_20d": volume_ratio,
        "ma5": ma5,
        "ma20": ma20,
        "ma60": ma60,
        "trend": trend,
        "return_5d_pct": _lookback_return(5),
        "return_20d_pct": _lookback_return(20),
        "return_60d_pct": _lookback_return(60),
        "high_52w": high_52w,
        "pct_from_52w_high": pct_from_52w_high,
        "prior_20d_high": prior_20d_high,
        "range_20d_high": _safe_float(hist["High"].tail(20).max()) if "High" in hist else None,
        "range_20d_low": _safe_float(hist["Low"].tail(20).min()) if "Low" in hist else None,
        "ohlcv_tail": ohlcv_tail,
    }


def _fetch_news_snapshot(ticker: str, stock_name: str) -> Dict[str, Any]:
    try:
        from modules.news_analysis import NewsAnalyzer

        payload = NewsAnalyzer(ticker, stock_name=stock_name, max_results=5).get_news_sentiment()
        return {
            "status": payload.get("status"),
            "sentiment_score": _safe_float(payload.get("score")),
            "headlines": [
                {
                    "title": str(item.get("title") or ""),
                    "score": _safe_float(item.get("score")),
                    "source": str(item.get("source") or ""),
                    "date": item.get("date"),
                    "url": item.get("url"),
                }
                for item in (payload.get("headlines") or [])
                if isinstance(item, dict)
            ],
            "warnings": [],
        }
    except Exception as exc:
        return {"status": "ERROR", "sentiment_score": None, "headlines": [], "warnings": [f"news_fetch_failed:{exc}"]}


def _fetch_investor_flow_snapshot(ticker: str, row: Dict[str, Any], trace: Dict[str, Any]) -> Dict[str, Any]:
    base = {**(row if isinstance(row, dict) else {}), **(trace if isinstance(trace, dict) else {})}
    direct = {
        "whale_score": _safe_float(_first_present(base, "whale_score", "Whale", "kr_flow_leader_score")),
        "foreigner": _safe_float(
            _first_present(base, "foreigner", "foreign_flow", "foreign_net", "foreign_net_buy", "kr_foreign_flow")
        ),
        "institution": _safe_float(
            _first_present(
                base,
                "institution",
                "institution_flow",
                "institution_net",
                "institution_net_buy",
                "kr_institution_flow",
            )
        ),
        "retail": _safe_float(
            _first_present(base, "retail", "retail_flow", "individual", "individual_net", "retail_net_buy", "kr_retail_flow")
        ),
    }
    has_flow_breakdown = any(direct.get(key) is not None for key in ("foreigner", "institution", "retail"))
    if has_flow_breakdown:
        whale = direct.get("whale_score")
        return {
            "valid": True,
            "type": "KR" if str(ticker).upper().endswith((".KS", ".KQ")) else "UNKNOWN",
            "source": "scan_row",
            "whale_score": whale,
            "foreigner": direct.get("foreigner"),
            "institution": direct.get("institution"),
            "retail": direct.get("retail"),
            "dominant": base.get("dominant"),
            "whale_trend": base.get("whale_trend"),
            "warnings": [] if whale is not None else ["investor_flow_score_missing_scan_row"],
        }

    if not str(ticker).upper().endswith((".KS", ".KQ")):
        return {
            "valid": False,
            "type": "UNSUPPORTED",
            "source": "none",
            "whale_score": None,
            "foreigner": None,
            "institution": None,
            "retail": None,
            "warnings": ["investor_flow_supported_for_kr_only"],
        }

    try:
        from modules.quant_analysis import QuantStrategy

        payload = QuantStrategy(ticker).get_investor_flows()
        fetched_whale = _safe_float(payload.get("whale_score"))
        return {
            "valid": bool(payload.get("valid")),
            "type": payload.get("type") or "KR",
            "source": payload.get("flow_source") or "quant_strategy",
            "whale_score": fetched_whale if fetched_whale is not None else direct.get("whale_score"),
            "foreigner": _safe_float(payload.get("foreigner")),
            "institution": _safe_float(payload.get("institution")),
            "retail": _safe_float(payload.get("retail")),
            "dominant": payload.get("dominant"),
            "whale_trend": payload.get("whale_trend"),
            "warnings": [] if payload.get("valid") else [str(payload.get("reason") or "investor_flow_unavailable")],
        }
    except Exception as exc:
        return {
            "valid": False,
            "type": "KR",
            "source": "quant_strategy",
            "whale_score": direct.get("whale_score"),
            "foreigner": None,
            "institution": None,
            "retail": None,
            "warnings": [f"investor_flow_failed:{exc}"],
        }


def _practical_gate_blocks(gate: Dict[str, Any] | None) -> bool:
    if not isinstance(gate, dict):
        return False
    return gate.get("level") == "fail" and bool(gate.get("evidence"))


def _apply_practical_gate_override(readiness: Dict[str, Any], gate: Dict[str, Any]) -> Dict[str, Any]:
    if not _practical_gate_blocks(gate):
        return readiness
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness.get("final_buy_judgment"), dict) else {}
    if judgment.get("action") not in {"즉시 매수 가능", "조건부 매수 가능"}:
        return readiness
    updated = dict(readiness)
    updated["final_buy_judgment"] = {
        "action": "관망",
        "tone": "neutral",
        "summary": "실전 80% 필터 미달 후보라 매수 액션에서 제외합니다.",
    }
    overrides = list(updated.get("safety_overrides") or [])
    overrides.append("실전 80% 필터 미달")
    updated["safety_overrides"] = overrides[:8]
    return updated


def _signal_label(
    row: Dict[str, Any],
    loss_risk: float | None,
    *,
    readiness: Dict[str, Any] | None = None,
    practical_gate: Dict[str, Any] | None = None,
) -> str:
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness, dict) else {}
    action = str(judgment.get("action") or "")
    if action == "매수 금지":
        return "NO_BUY"
    if action in {"눌림 대기", "돌파 확인", "관망"}:
        return "WAIT_CONFIRM"
    if _practical_gate_blocks(practical_gate):
        return "WAIT_CONFIRM"
    decision = str(row.get("decision") or row.get("Decision") or "").upper()
    if decision == "EXCEPTION_LEADER":
        return "SURGE_CAPTURE"
    if loss_risk is not None and loss_risk >= 65:
        return "RISK_REVIEW"
    if decision in {"PRIORITY_WATCHLIST", "PICK", "BUY", "STRONG_BUY"}:
        return "PRIMARY_BUY"
    if decision in {"WATCHLIST", "WATCHLIST_ONLY"}:
        return "WATCH_BUY"
    return decision or "OBSERVE"


def _segment_accuracy(row: Dict[str, Any], trace: Dict[str, Any], ticker: str, market: str, scan_mode: str) -> float | None:
    direct = _safe_float(
        _first_present(row, "phase25_oos_win_rate_pct")
        or trace.get("phase25_oos_win_rate_pct")
        or row.get("prob_clean")
        or trace.get("prob_clean")
    )
    if direct is not None:
        return direct
    try:
        from modules.segment_accuracy import lookup_segment_win_rate

        return _safe_float(
            lookup_segment_win_rate(
                decision=_first_present(row, "decision", "Decision") or trace.get("decision"),
                market=market or trace.get("market") or row.get("market"),
                scan_mode=scan_mode or trace.get("scan_mode") or row.get("scan_mode"),
                ticker=ticker,
                horizon_days=5,
            )
        )
    except Exception:
        return None


def _derive_trade_price_levels(policy: Dict[str, Any], price: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    policy = dict(policy if isinstance(policy, dict) else {})
    price = price if isinstance(price, dict) else {}
    warnings: List[str] = [str(item) for item in policy.get("warnings", []) if str(item).strip()]
    current = _safe_float(price.get("current_price"))
    entry = _safe_float(policy.get("entry_reference_price")) or current
    if entry is None:
        policy.update(
            {
                "entry_zone_low": None,
                "entry_zone_high": None,
                "target_price": None,
                "stop_price": None,
                "risk_reward": None,
                "price_level_source": "unavailable",
                "warnings": ["trade_price_level_unavailable"],
            }
        )
        return policy

    if policy.get("entry_reference_price") is None:
        policy["entry_reference_price"] = entry
        warnings.append("entry_reference_price_fallback_current_price")

    is_kq = str(ticker).upper().endswith(".KQ")
    ma20 = _safe_float(price.get("ma20"))
    ma5 = _safe_float(price.get("ma5"))
    range_low = _safe_float(price.get("range_20d_low"))
    prior_high = _safe_float(price.get("prior_20d_high"))
    tp_pct = _safe_float(policy.get("target_tp_pct")) or 0.0
    sl_pct = _safe_float(policy.get("stop_sl_pct")) or (-7.0 if is_kq else -5.0)

    pullback = 0.025 if is_kq else 0.018
    entry_zone_low = entry * (1.0 - pullback)
    support_candidates = []
    for support in (ma5, ma20, range_low):
        if support is not None and 0 < support < entry and ((entry - support) / entry) <= 0.15:
            support_candidates.append(support)
    if support_candidates:
        entry_zone_low = min(entry_zone_low, max(support_candidates))
    entry_zone_high = entry

    fallback_stop = entry * (1.0 + sl_pct / 100.0)
    stop_candidates = [fallback_stop]
    for support in (ma20, range_low):
        if support is not None and 0 < support < entry:
            stop_candidates.append(support * 0.985)
    stop_price = max([candidate for candidate in stop_candidates if candidate < entry], default=fallback_stop)
    if (entry - stop_price) / entry < 0.015:
        stop_price = entry * 0.985
    if (entry - stop_price) / entry > 0.15:
        stop_price = fallback_stop
        warnings.append("stop_price_default_pct_used_due_far_support")

    target_price = entry * (1.0 + tp_pct / 100.0) if tp_pct else None
    if target_price is not None and prior_high is not None and prior_high > entry:
        target_price = max(target_price, prior_high * 1.01)

    reward = (target_price - entry) if target_price is not None else None
    risk = entry - stop_price if stop_price is not None else None
    risk_reward = round(reward / risk, 4) if reward is not None and risk and risk > 0 else None

    policy.update(
        {
            "entry_zone_low": _safe_float(entry_zone_low),
            "entry_zone_high": _safe_float(entry_zone_high),
            "target_price": _safe_float(target_price),
            "stop_price": _safe_float(stop_price),
            "risk_reward": risk_reward,
            "stop_sl_pct": _safe_float((stop_price / entry - 1.0) * 100.0) if stop_price is not None else policy.get("stop_sl_pct"),
            "target_tp_pct": _safe_float((target_price / entry - 1.0) * 100.0) if target_price is not None else policy.get("target_tp_pct"),
            "price_level_source": "per_stock_price_snapshot",
            "warnings": warnings,
        }
    )
    return policy


def _trade_policy(row: Dict[str, Any], trace: Dict[str, Any], ticker: str, price: Dict[str, Any]) -> Dict[str, Any]:
    tp = _safe_float(trace.get("target_tp_pct") or row.get("target_tp_pct"))
    sl = _safe_float(trace.get("stop_sl_pct") or row.get("stop_sl_pct"))
    hold = _safe_int(trace.get("hold_days") or row.get("hold_days"))
    entry_policy = str(row.get("entry_policy") or trace.get("entry_policy") or "").strip()
    if tp is None or sl is None or hold is None or not entry_policy:
        try:
            from modules.scanner_services import DEFAULT_EXIT_HOLD_DAYS, DEFAULT_EXIT_SL_PCT, DEFAULT_EXIT_TP_PCT

            tp = DEFAULT_EXIT_TP_PCT if tp is None else tp
            sl = DEFAULT_EXIT_SL_PCT if sl is None else sl
            hold = DEFAULT_EXIT_HOLD_DAYS if hold is None else hold
        except Exception:
            tp = 15.0 if tp is None else tp
            sl = -10.0 if sl is None else sl
            hold = 5 if hold is None else hold
        if not entry_policy:
            entry_policy = "-2% limit" if str(ticker).upper().endswith(".KQ") else "open/reference"
    if not _present(_first_present(trace, "target_tp_pct") or row.get("target_tp_pct")):
        # Exit percent defaults are an explicit fallback; concrete price levels below remain per-stock.
        trace = {**trace, "trade_policy_warning": "default_target_pct_used"}
    policy = {
        "entry_policy": entry_policy,
        "entry_reference_price": _safe_float(
            _first_present(
                trace,
                "entry_reference_price",
                "entry_price",
                "Entry Price",
                "Entry(-2%)",
                "매수가(-2%)",
                "Current Price",
                "현재가",
                "curr_price",
                "price",
            )
            or _first_present(
                row,
                "entry_reference_price",
                "entry_price",
                "Entry Price",
                "Entry(-2%)",
                "매수가(-2%)",
                "Current Price",
                "현재가",
                "curr_price",
                "price",
            )
        ),
        "target_tp_pct": tp,
        "stop_sl_pct": sl,
        "hold_days": hold,
    }
    if trace.get("trade_policy_warning"):
        policy["warnings"] = [trace.get("trade_policy_warning")]
    return _derive_trade_price_levels(policy, price, ticker)


def _build_selection_thesis(
    *,
    row: Dict[str, Any],
    trace: Dict[str, Any],
    prediction: Dict[str, Any],
    readiness: Dict[str, Any],
) -> Dict[str, Any]:
    merged = {**(row if isinstance(row, dict) else {}), **(trace if isinstance(trace, dict) else {})}
    decision = str(merged.get("decision") or "").upper()
    raw_score = _safe_float(_first_present(row, "Decision Score", "decision_score", "score"))
    relative_score = _safe_float(merged.get("relative_rank_score"))
    expected_edge = _safe_float(prediction.get("expected_edge_score"))
    loss = _safe_float(merged.get("loss_risk_score"))
    selection_reasons = []
    for item in merged.get("rationale") or []:
        text = str(item).strip()
        if text and text not in selection_reasons:
            selection_reasons.append(text)
        if len(selection_reasons) >= 8:
            break

    if decision in {"PRIORITY_WATCHLIST", "PICK", "BUY", "STRONG_BUY"}:
        status = "planner_priority"
        summary = "플래너가 실행 후보군으로 유지한 종목입니다."
    elif decision in {"WATCHLIST", "WATCHLIST_ONLY"}:
        status = "planner_watchlist"
        summary = "스캔 강도는 있으나 플래너가 감시 후보로 낮춘 종목입니다."
    elif decision in {"OBSERVE", "AVOID"}:
        status = "planner_demoted"
        summary = "스캔에는 포착됐지만 플래너가 관망/회피로 강등한 종목입니다."
    else:
        status = "scanner_candidate"
        summary = "스캔 후보로 포착된 종목입니다."

    if raw_score is not None and raw_score >= 80 and decision in {"OBSERVE", "AVOID"}:
        summary += " 원본 점수는 높지만 손실위험/기대수익/상대순위에서 차단 신호가 있습니다."
    elif expected_edge is not None and expected_edge < 0:
        summary += " 다만 기대 엣지는 음수라 즉시 매수 논리는 약합니다."
    elif loss is not None and loss >= 65:
        summary += " 손실위험 하드캡에 가까워 진입 판단은 보수적으로 봅니다."

    quality = readiness.get("quality") if isinstance(readiness.get("quality"), dict) else {}
    timing = readiness.get("timing") if isinstance(readiness.get("timing"), dict) else {}
    upside = readiness.get("upside") if isinstance(readiness.get("upside"), dict) else {}
    return {
        "status": status,
        "summary": summary,
        "scanner_basis": {
            "raw_decision_score": raw_score,
            "quant_priority_score": _safe_float(merged.get("quant_priority_score")),
            "relative_rank_score": relative_score,
            "relative_rank_pct": _safe_float(merged.get("relative_rank_pct")),
            "expected_edge_score": expected_edge,
            "expected_return_1d_pct": _safe_float(prediction.get("expected_return_1d_pct")),
            "expected_return_3d_pct": _safe_float(prediction.get("expected_return_3d_pct")),
            "loss_risk_score": loss,
        },
        "readiness_snapshot": {
            "quality_score": quality.get("score"),
            "upside_score": upside.get("score"),
            "timing_score": timing.get("score"),
            "chase_risk_level": readiness.get("chase_risk_level"),
        },
        "selection_reasons": selection_reasons,
    }


def _build_risk_overrides(
    *,
    row: Dict[str, Any],
    trace: Dict[str, Any],
    readiness: Dict[str, Any],
    loss_risk_score: float | None,
) -> Dict[str, Any]:
    merged = {**(row if isinstance(row, dict) else {}), **(trace if isinstance(trace, dict) else {})}
    flags = []
    for source in (merged.get("theme_risk"), merged.get("risk_flags"), merged.get("rationale")):
        for item in source or []:
            text = str(item).strip()
            if text and text not in flags:
                flags.append(text)
    upside = readiness.get("upside") if isinstance(readiness.get("upside"), dict) else {}
    filters = upside.get("filters") if isinstance(upside.get("filters"), list) else []
    triggered_filters = [item for item in filters if isinstance(item, dict) and item.get("triggered")]
    warnings = [str(item) for item in readiness.get("warnings") or [] if str(item).strip()]
    severity = "none"
    if loss_risk_score is not None and loss_risk_score >= 65:
        severity = "hard"
    elif any(str(item.get("severity")) == "block" for item in triggered_filters):
        severity = "hard"
    elif loss_risk_score is not None and loss_risk_score >= 45:
        severity = "soft"
    elif triggered_filters:
        severity = "soft"

    return {
        "severity": severity,
        "loss_risk_score": loss_risk_score,
        "triggered_chase_filters": triggered_filters,
        "planner_risk_flags": flags[:10],
        "data_warnings": warnings[:8],
    }


def build_top_deep_reports(
    *,
    scan_rows: List[Dict[str, Any]],
    planner_payload: Dict[str, Any],
    run_id: str,
    market: str,
    scan_mode: str,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    traces = _planner_trace_by_ticker(planner_payload)
    reports: List[Dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc).isoformat()
    for rank, row in enumerate(_select_top_candidates(scan_rows, planner_payload, top_n), start=1):
        ticker = _ticker(row)
        trace = traces.get(ticker, {})
        stock_name = str(_first_present(row, "stock_name", "종목명", "Name", "name") or trace.get("stock_name") or ticker)
        price = _fetch_price_snapshot(ticker)
        news = _fetch_news_snapshot(ticker, stock_name)
        loss_risk = _safe_float(_first_present(row, "loss_risk_score") or trace.get("loss_risk_score"))
        day_change = _safe_float(_first_present(row, "day_return_pct", "전일비") or price.get("day_change_pct"))
        buy_score = _safe_float(_first_present(row, "relative_rank_score", "decision_score", "Decision Score", "score"))
        trade_policy = _trade_policy(row, trace, ticker, price)
        flow = _fetch_investor_flow_snapshot(ticker, row, trace)
        prediction = {
            "phase25_prob": _safe_float(trace.get("phase25_prob") or row.get("phase25_prob")),
            "expected_return_1d_pct": _safe_float(trace.get("expected_return_1d_pct") or row.get("expected_return_1d_pct")),
            "expected_return_3d_pct": _safe_float(trace.get("expected_return_3d_pct") or row.get("expected_return_3d_pct")),
            "expected_edge_score": _safe_float(trace.get("expected_edge_score") or row.get("expected_edge_score")),
            "relative_rank_score": _safe_float(trace.get("relative_rank_score") or row.get("relative_rank_score")),
            "relative_rank_pct": _safe_float(trace.get("relative_rank_pct") or row.get("relative_rank_pct")),
            "relative_rank_model": trace.get("relative_rank_model") or row.get("relative_rank_model"),
        }
        readiness_analysis = build_entry_readiness_analysis(
            candidate={**row, **trace},
            price=price,
            prediction=prediction,
            trade_plan=trade_policy,
            news=news,
            loss_risk_score=loss_risk,
        )
        practical_gate = evaluate_practical_entry_gate({**row, **trace})
        readiness_analysis = _apply_practical_gate_override(readiness_analysis, practical_gate)
        selection_thesis = _build_selection_thesis(
            row=row,
            trace=trace,
            prediction=prediction,
            readiness=readiness_analysis,
        )
        risk_overrides = _build_risk_overrides(
            row=row,
            trace=trace,
            readiness=readiness_analysis,
            loss_risk_score=loss_risk,
        )
        entry_action = {
            "judgment": readiness_analysis.get("final_buy_judgment"),
            "entry_strategy": readiness_analysis.get("entry_strategy"),
            "risk_management": readiness_analysis.get("risk_management"),
        }
        trade_policy["readiness_analysis"] = readiness_analysis
        if isinstance(readiness_analysis.get("entry_strategy"), dict):
            trade_policy["entry_strategy"] = readiness_analysis["entry_strategy"]
        if isinstance(readiness_analysis.get("risk_management"), dict):
            trade_policy["risk_management"] = readiness_analysis["risk_management"]
        if isinstance(readiness_analysis.get("data_coverage"), dict):
            trade_policy["data_coverage"] = readiness_analysis["data_coverage"]
        trade_policy["selection_thesis"] = selection_thesis
        trade_policy["risk_overrides"] = risk_overrides
        trade_policy["entry_action"] = entry_action
        trade_policy["practical_entry_gate"] = practical_gate
        report = {
            "report_id": f"{run_id}:{ticker}:{REPORT_VERSION}",
            "report_version": REPORT_VERSION,
            "run_id": str(run_id),
            "market": str(market or ""),
            "scan_mode": str(scan_mode or ""),
            "rank": rank,
            "ticker": ticker,
            "stock_name": stock_name,
            "generated_at": generated_at,
            "signal_label": _signal_label(
                {**row, **trace},
                loss_risk,
                readiness=readiness_analysis,
                practical_gate=practical_gate,
            ),
            "decision": str(_first_present(row, "decision", "Decision") or trace.get("decision") or ""),
            "decision_bucket": str(_first_present(row, "decision_bucket") or trace.get("decision_bucket") or ""),
            "selection_alignment": {
                "raw_scan_rank": _safe_int(row.get("_raw_scan_rank")),
                "planner_priority_rank": _safe_int(trace.get("priority_rank") or row.get("priority_rank")),
                "raw_decision_score": _safe_float(_first_present(row, "Decision Score", "decision_score", "score")),
                "planner_decision": str(trace.get("decision") or row.get("decision") or ""),
                "relative_rank_score": _safe_float(trace.get("relative_rank_score") or row.get("relative_rank_score")),
                "relative_rank_pct": _safe_float(trace.get("relative_rank_pct") or row.get("relative_rank_pct")),
                "analysis_section": str(row.get("_analysis_section") or "Top5"),
                "analysis_section_rank": _safe_int(row.get("_analysis_section_rank")),
                "source_order": str(row.get("_source_order") or "top5_main_plus_exception_addon"),
                "validated_winner_profile": row.get("_validated_winner_profile"),
            },
            "buy_score": buy_score,
            "accuracy": _segment_accuracy(row, trace, ticker, market, scan_mode),
            "day_change_pct": day_change,
            "loss_risk_score": loss_risk,
            "practical_entry_gate": practical_gate,
            "risk_flags": trace.get("theme_risk") or row.get("theme_risk") or [],
            "rationale": trace.get("rationale") or row.get("rationale") or [],
            "prediction": prediction,
            "selection_thesis": selection_thesis,
            "risk_overrides": risk_overrides,
            "entry_action": entry_action,
            "trade_plan": trade_policy,
            "flow": flow,
            "theme": {
                "primary_theme": _first_present(trace, "primary_theme", "테마", "Theme")
                or _first_present(row, "primary_theme", "테마", "Theme"),
                "theme_routing_path": _first_present(trace, "theme_routing_path", "theme_routing_path")
                or _first_present(row, "theme_routing_path", "theme_routing_path"),
            },
            "price": price,
            "news": news,
            "data_warnings": (
                list(price.get("warnings") or [])
                + list(news.get("warnings") or [])
                + list(flow.get("warnings") or [])
                + list(trade_policy.get("warnings") or [])
            ),
        }
        reports.append(_coerce_jsonable(report))
    return reports


def save_reports_local(reports: List[Dict[str, Any]], run_id: str) -> str:
    LOCAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = LOCAL_REPORT_DIR / f"{run_id}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)
    return str(path)


def upsert_reports_to_supabase(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not reports:
        return {"rows_seen": 0, "rows_upserted": 0, "warning": ""}
    try:
        from modules.db_manager import DBManager

        db = DBManager()
        if not db.client:
            return {"rows_seen": len(reports), "rows_upserted": 0, "warning": "db_client_unavailable"}
        filtered_reports = []
        for row in reports:
            if not isinstance(row, dict):
                continue
            filtered = db._filter_payload_to_existing_columns("scan_deep_reports", row)
            if set(filtered.keys()) == set(row.keys()):
                filtered = {key: value for key, value in row.items() if key in SCAN_DEEP_REPORT_COLUMNS}
            filtered_reports.append(filtered)
        run_ids = sorted({str(row.get("run_id") or "") for row in reports if row.get("run_id")})
        for run_id in run_ids:
            db.client.table("scan_deep_reports").delete().eq("run_id", run_id).execute()
        db.client.table("scan_deep_reports").upsert(filtered_reports, on_conflict="report_id").execute()
        return {"rows_seen": len(reports), "rows_upserted": len(filtered_reports), "warning": ""}
    except Exception as exc:
        return {"rows_seen": len(reports), "rows_upserted": 0, "warning": str(exc)}


def generate_and_store_top_deep_reports(
    *,
    scan_rows: List[Dict[str, Any]],
    planner_payload: Dict[str, Any],
    run_id: str,
    market: str,
    scan_mode: str,
    top_n: int = 5,
    write_db: bool = True,
) -> Dict[str, Any]:
    reports = build_top_deep_reports(
        scan_rows=scan_rows,
        planner_payload=planner_payload,
        run_id=run_id,
        market=market,
        scan_mode=scan_mode,
        top_n=top_n,
    )
    local_path = save_reports_local(reports, run_id)
    db_result = upsert_reports_to_supabase(reports) if write_db else {"rows_seen": len(reports), "rows_upserted": 0, "warning": "write_db_disabled"}
    return {"count": len(reports), "local_path": local_path, "db_result": db_result}
