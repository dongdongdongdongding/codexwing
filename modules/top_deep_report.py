from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

from modules.ui_helpers import enrich_signal_rows_with_planner_trace, sort_signal_rows_by_planner_rank


REPORT_VERSION = "top_deep_report_v1"
LOCAL_REPORT_DIR = Path("runtime_state/reports/top_deep")


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
    enriched = enrich_signal_rows_with_planner_trace(scan_rows, planner_payload)
    rows = [row for row in enriched if _ticker(row)]
    return sort_signal_rows_by_planner_rank(rows, planner_payload)[: max(int(limit or 0), 0)]


def _fetch_price_snapshot(ticker: str) -> Dict[str, Any]:
    warnings: List[str] = []
    try:
        hist = yf.Ticker(ticker).history(period="6mo", interval="1d", auto_adjust=False)
    except Exception as exc:
        return {"warnings": [f"price_fetch_failed:{exc}"], "ohlcv_tail": []}

    if hist is None or hist.empty:
        return {"warnings": ["price_history_empty"], "ohlcv_tail": []}

    hist = hist.dropna(subset=["Close"]).copy()
    latest = hist.iloc[-1]
    close = _safe_float(latest.get("Close"))
    prev_close = _safe_float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
    day_change_pct = None
    if close is not None and prev_close not in (None, 0):
        day_change_pct = round((close - prev_close) / prev_close * 100.0, 4)
    volume = _safe_int(latest.get("Volume"))
    vol20 = _safe_float(hist["Volume"].tail(20).mean()) if "Volume" in hist else None
    volume_ratio = None
    if volume is not None and vol20 not in (None, 0):
        volume_ratio = round(float(volume) / float(vol20), 4)
    ma20 = _safe_float(hist["Close"].tail(20).mean()) if len(hist) >= 20 else None
    ma60 = _safe_float(hist["Close"].tail(60).mean()) if len(hist) >= 60 else None
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
        "volume": volume,
        "volume_ratio_20d": volume_ratio,
        "ma20": ma20,
        "ma60": ma60,
        "trend": trend,
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


def _signal_label(row: Dict[str, Any], loss_risk: float | None) -> str:
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


def _trade_policy(row: Dict[str, Any], trace: Dict[str, Any], ticker: str) -> Dict[str, Any]:
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
    return {
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
        trade_policy = _trade_policy(row, trace, ticker)
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
            "signal_label": _signal_label({**row, **trace}, loss_risk),
            "decision": str(_first_present(row, "decision", "Decision") or trace.get("decision") or ""),
            "decision_bucket": str(_first_present(row, "decision_bucket") or trace.get("decision_bucket") or ""),
            "buy_score": buy_score,
            "accuracy": _segment_accuracy(row, trace, ticker, market, scan_mode),
            "day_change_pct": day_change,
            "loss_risk_score": loss_risk,
            "risk_flags": trace.get("theme_risk") or row.get("theme_risk") or [],
            "rationale": trace.get("rationale") or row.get("rationale") or [],
            "prediction": {
                "phase25_prob": _safe_float(trace.get("phase25_prob") or row.get("phase25_prob")),
                "expected_return_1d_pct": _safe_float(trace.get("expected_return_1d_pct") or row.get("expected_return_1d_pct")),
                "expected_return_3d_pct": _safe_float(trace.get("expected_return_3d_pct") or row.get("expected_return_3d_pct")),
                "expected_edge_score": _safe_float(trace.get("expected_edge_score") or row.get("expected_edge_score")),
                "relative_rank_score": _safe_float(trace.get("relative_rank_score") or row.get("relative_rank_score")),
                "relative_rank_pct": _safe_float(trace.get("relative_rank_pct") or row.get("relative_rank_pct")),
                "relative_rank_model": trace.get("relative_rank_model") or row.get("relative_rank_model"),
            },
            "trade_plan": trade_policy,
            "theme": {
                "primary_theme": trace.get("primary_theme") or row.get("primary_theme"),
                "theme_routing_path": trace.get("theme_routing_path") or row.get("theme_routing_path"),
            },
            "price": price,
            "news": news,
            "data_warnings": list(price.get("warnings") or []) + list(news.get("warnings") or []),
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
        run_ids = sorted({str(row.get("run_id") or "") for row in reports if row.get("run_id")})
        for run_id in run_ids:
            db.client.table("scan_deep_reports").delete().eq("run_id", run_id).execute()
        db.client.table("scan_deep_reports").upsert(reports, on_conflict="report_id").execute()
        return {"rows_seen": len(reports), "rows_upserted": len(reports), "warning": ""}
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
