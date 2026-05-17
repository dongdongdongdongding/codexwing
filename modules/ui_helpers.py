from __future__ import annotations

import math
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import uuid4

from modules.practical_entry_gate import evaluate_practical_entry_gate
from modules.segment_accuracy import lookup_segment_win_rate


def compute_progress_fraction(completed_count: int, total_count: int) -> float:
    total = max(int(total_count or 0), 0)
    completed = max(int(completed_count or 0), 0)
    if total <= 0:
        return 0.0
    return min(1.0, max(0.0, completed / total))


def _to_float(value) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return numeric


def resolve_display_price(realtime_price, last_close) -> float:
    realtime = _to_float(realtime_price)
    if realtime > 0:
        return realtime
    return max(_to_float(last_close), 0.0)


def format_volume_display(volume) -> str:
    numeric = max(_to_float(volume), 0.0)
    return f"{int(round(numeric)):,}"


def should_auto_refresh_scan_panel(status: str) -> bool:
    return str(status or "").lower() in {"queued", "running"}


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() != "none"
    return True


def _coalesce_value(*values: Any) -> Any:
    for value in values:
        if _is_present(value):
            return value
    return ""


def _coalesce_present(*values: Any) -> Any:
    return _coalesce_value(*values)


def _parse_percent_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _format_percent_label(value: Any) -> str:
    numeric = _parse_percent_value(value)
    if numeric is None:
        return "-"
    return f"{numeric:+.2f}%" if numeric < 0 else f"{numeric:.2f}%"


def _format_accuracy_label(value: Any) -> str:
    numeric = _parse_percent_value(value)
    if numeric is None:
        return "-"
    return f"{numeric:.1f}%"


def _format_score_label(value: Any) -> str:
    numeric = _parse_percent_value(value)
    if numeric is None:
        return "-"
    return f"{numeric:.1f}"


def _format_signed_percent_label(value: Any, fallback: str = "-") -> str:
    numeric = _parse_percent_value(value)
    if numeric is None:
        return fallback
    return f"{numeric:+.0f}%"


def _format_risk_score_label(value: Any) -> str:
    numeric = _parse_percent_value(value)
    if numeric is None:
        return "-"
    return f"{numeric:.1f}"


def _risk_level_label(value: Any) -> str:
    numeric = _parse_percent_value(value)
    if numeric is None:
        return ""
    if numeric >= 65:
        return "높음"
    if numeric >= 45:
        return "주의"
    return "낮음"


def _row_float(row: Dict[str, Any], *keys: str) -> float | None:
    value = _coalesce_present(*(row.get(key) for key in keys))
    numeric = _parse_percent_value(value)
    return numeric


def _row_text(row: Dict[str, Any], *keys: str) -> str:
    return str(_coalesce_present(*(row.get(key) for key in keys)) or "").strip()


def _row_market(row: Dict[str, Any]) -> str:
    market = _row_text(row, "market", "market2", "market_subtype", "Market").upper()
    ticker = _row_text(row, "ticker", "티커", "Ticker", "symbol").upper()
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return market


def _row_bool_false(row: Dict[str, Any], *keys: str) -> bool:
    value = _coalesce_present(*(row.get(key) for key in keys))
    if value in (None, ""):
        return False
    if isinstance(value, bool):
        return value is False
    text = str(value).strip().lower()
    return text in {"0", "false", "no", "off", "none"}


def _coerce_text_list(value: Any, limit: int = 3) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        source = value
    elif isinstance(value, tuple):
        source = list(value)
    else:
        text = str(value).strip()
        if not text or text.lower() == "none":
            return []
        source = re.split(r"[,/|]", text)
    out: List[str] = []
    for item in source:
        text = str(item).strip()
        if text and text.lower() != "none" and text not in out:
            out.append(text)
        if len(out) >= max(int(limit or 0), 0):
            break
    return out


def _action_trace_items(row: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    for key in ("theme_risk", "risk_flags", "rationale"):
        for item in _coerce_text_list(row.get(key), limit=8):
            if item not in items:
                items.append(item)
    return items


def build_action_display(row: Dict[str, Any]) -> Dict[str, Any]:
    """Render-only interpretation of existing planner/scanner trace.

    This does not change candidate selection, ranking, gates, or DB state. It
    maps already-produced decision/risk trace into an operator-facing action
    label so strong candidates are not visually mistaken for immediate buys
    when the planner already emitted wait/avoid risk markers.
    """
    if not isinstance(row, dict):
        return {"label": "-", "condition": "", "stop_condition": "", "reasons": []}

    decision = str(
        _coalesce_present(row.get("decision"), row.get("Decision"), row.get("decision_bucket"))
        or ""
    ).upper().strip()
    trace_items = _action_trace_items(row)
    explicit_action = str(_coalesce_present(row.get("final_action"), row.get("Final Action")) or "").strip()
    explicit_entry = str(
        _coalesce_present(row.get("entry_condition_text"), row.get("Entry Condition"))
        or ""
    ).strip()
    explicit_stop = str(
        _coalesce_present(row.get("stop_condition_text"), row.get("Stop Condition"))
        or ""
    ).strip()
    if explicit_action:
        return {
            "label": explicit_action,
            "condition": explicit_entry,
            "stop_condition": explicit_stop,
            "reasons": trace_items[:4],
        }

    trace_upper = {str(item).upper() for item in trace_items}
    risk_score = _parse_percent_value(_coalesce_present(row.get("loss_risk_score"), row.get("Loss Risk")))

    hard_markers = {
        "LOSS_RISK_HARD_CAP",
        "PHASE25_RAW_AUC_BELOW_RANDOM",
        "PHASE25_OOS_AUC_REGIME_BREAK",
        "ML_INFERENCE_FAILED",
    }
    wait_markers = {
        "ENTRY_TIMING_RISK_HIGH",
        "LOSS_RISK_SOFT_CAP",
        "EXPECTED_EDGE_PRIORITY_GUARD",
        "EXPECTED_EDGE_PRIORITY_GUARD_SOFT",
        "EXPECTED_EDGE_WATCH_GUARD",
        "EXPECTED_EDGE_WATCH_GUARD_SOFT",
        "KOSDAQ_SWING_TREND_GUARD",
        "KOSDAQ_SWING_CLEAN_PROB_GUARD",
        "KOSPI_SWING_MOMENTUM_GUARD",
        "KOSPI_SWING_PRIORITY_GUARD_SOFT",
        "KOSDAQ_SWING_LOW_VOL_GUARD",
    }
    special_risk_terms = {
        "유상증자",
        "신주배정",
        "신주 상장",
        "신주상장",
        "전환사채",
        "주식관련사채",
        "CB",
        "BW",
        "감사의견",
        "관리종목",
        "환기종목",
        "자본잠식",
    }
    trace_text_upper = "\n".join(trace_items).upper()
    day_change = _parse_percent_value(_coalesce_present(row.get("전일비"), row.get("day_return_pct"), row.get("day_change_pct")))

    if (
        decision in {"AVOID", "REJECT", "SELL", "NO_BUY", "NO_NEW_BUY"}
        or trace_upper.intersection(hard_markers)
        or any(term.upper() in trace_text_upper for term in special_risk_terms)
    ):
        label = "매수 금지"
        condition = "리스크 해소 전 신규 진입 금지"
    elif is_exception_leader_row(row):
        label = "급등 분리 관찰"
        condition = "Stream B 소액 운용, 손절 엄수"
    elif day_change is not None and day_change > 8.0:
        label = "눌림/확인 대기"
        condition = "당일 급등 추격 금지, 지지·재돌파 확인"
    elif trace_upper.intersection(wait_markers) or (risk_score is not None and risk_score >= 65):
        label = "눌림/확인 대기"
        condition = "지지·재돌파 확인 후 검토"
    elif decision in {"PRIORITY_WATCHLIST", "PICK", "BUY", "STRONG_BUY"}:
        label = "조건부 매수 가능"
        condition = "표시된 Entry/TP/SL 기준 준수"
    elif decision in {"WATCHLIST", "WATCHLIST_ONLY"}:
        label = "조건부 대기"
        condition = "가격 부담과 거래량 재유입 확인"
    elif decision == "OBSERVE":
        label = "관망"
        condition = "방향 확인 전 대기"
    else:
        label = "확인 필요"
        condition = "planner trace 기준 추가 확인"

    return {
        "label": label,
        "condition": condition,
        "stop_condition": explicit_stop,
        "reasons": trace_items[:4],
    }


def is_exception_leader_row(rec: Dict[str, Any]) -> bool:
    """8:2 자본 배분 정책의 Stream B (EXCEPTION_LEADER) 분류 규칙.

    Scanner / Archive / 기타 dataframe 출처 가 다 같은 기준으로 EL 을 판별하도록
    공용 헬퍼로 추출. ``decision`` / ``Decision`` / ``decision_bucket`` 어느 쪽이
    채워져 있어도 EL 을 정확히 잡고, decision 이 누락된 row 는 risk_label /
    reason / reject_reason 으로 보조 판별한다.
    """
    if not isinstance(rec, dict):
        return False
    decision_values = {
        str(rec.get("decision") or "").upper().strip(),
        str(rec.get("Decision") or "").upper().strip(),
        str(rec.get("decision_bucket") or "").upper().strip(),
    }
    if "EXCEPTION_LEADER" in decision_values:
        return True
    rl = str(rec.get("risk_label") or "").upper().strip()
    rs = str(rec.get("reason") or rec.get("reject_reason") or "").lower()
    return rl == "EXCEPTION_LEADER" or "exception_leader" in rs


def is_kospi_ordered_shadow_gate_row(rec: Dict[str, Any]) -> bool:
    """Current KOSPI ordered shadow gate.

    Display-only gate from the internal ordered OHLCV testbed:
    prob_clean>=35.5, alpha_score>=67, same-day theme avg alpha<=81,
    CORE_TREND role. This is a shadow-only display gate; it does not replace
    the production scanner ranking.
    """
    if not isinstance(rec, dict) or _row_market(rec) != "KOSPI" or is_exception_leader_row(rec):
        return False
    prob_clean = _row_float(rec, "prob_clean", "_prob_clean", "정밀확률", "Clean")
    alpha = _row_float(rec, "alpha_score", "Alpha", "종합점수")
    theme_avg_alpha = _row_float(
        rec,
        "theme_day_avg_alpha_score",
        "_theme_day_avg_alpha_score",
        "display_theme_day_avg_alpha_score",
    )
    role = _row_text(rec, "kr_universe_role", "KR Universe Role").upper()
    core_flag = _row_text(rec, "core_trend_flag", "Core Trend Flag").lower()
    is_core_trend = role == "CORE_TREND" or core_flag in {"1", "true", "yes", "on"}
    return (
        prob_clean is not None
        and prob_clean >= 35.5
        and alpha is not None
        and alpha >= 67.0
        and theme_avg_alpha is not None
        and theme_avg_alpha <= 81.0
        and is_core_trend
    )


def is_kosdaq_ordered_rebound_shadow_gate_row(rec: Dict[str, Any]) -> bool:
    """Current KOSDAQ low-loss rebound shadow gate.

    Display-only gate from the internal ordered OHLCV testbed:
    tech_score<=80, same-scan theme avg decision<=63.1,
    same-scan theme symbol count>=7, trend=UP.
    """
    if not isinstance(rec, dict) or _row_market(rec) != "KOSDAQ":
        return False
    tech = _row_float(rec, "tech_score", "Tech", "기술점수")
    theme_avg_decision = _row_float(
        rec,
        "theme_day_avg_decision_score",
        "_theme_day_avg_decision_score",
        "display_theme_day_avg_decision_score",
    )
    theme_count = _row_float(rec, "theme_day_symbol_count", "_theme_day_symbol_count", "display_theme_day_symbol_count")
    trend = _row_text(rec, "trend", "real_trend", "추세", "Trend").upper()
    return (
        tech is not None
        and tech <= 80.0
        and theme_avg_decision is not None
        and theme_avg_decision <= 63.1
        and theme_count is not None
        and theme_count >= 7.0
        and trend == "UP"
    )


def validated_winner_profile(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Display-side admission profile backed by current validation reports.

    This does not alter scanner scoring. It controls which candidates deserve
    the top actionable display slot after recent realized-outcome validation.
    """
    market = _row_market(rec)
    rank = _row_float(rec, "priority_rank", "Rank")
    edge = _row_float(rec, "expected_edge_score")
    prob_clean = _row_float(rec, "prob_clean", "_prob_clean", "정밀확률", "Clean")
    alpha = _row_float(rec, "alpha_score", "Alpha", "종합점수")
    is_exception = is_exception_leader_row(rec)

    if market == "KOSPI":
        if is_exception and alpha is not None and alpha >= 80:
            return {
                "level": "pass",
                "label": "KOSPI 검증 Exception Leader",
                "profile": "exception_leader__alpha_ge_80",
                "metrics": "n=45 · win5 86.7% · avg5 +8.88%",
            }
        if rank is not None and 1 <= rank <= 5 and edge is not None and edge >= 7:
            return {
                "level": "pass",
                "label": "KOSPI 검증 Top5",
                "profile": "rank_top5__edge_ge_7",
                "metrics": "n=55 · win5 80.0% · avg5 +8.99%",
            }
        if rank is not None and 1 <= rank <= 5 and prob_clean is not None and prob_clean >= 50:
            return {
                "level": "pass",
                "label": "KOSPI 검증 Top5",
                "profile": "rank_top5__prob_clean_ge_50",
                "metrics": "n=40 · win5 82.5% · avg5 +8.70%",
            }
    if market == "KOSDAQ":
        if is_exception and alpha is not None and alpha >= 85:
            return {
                "level": "near",
                "label": "KOSDAQ 관찰 Exception Leader",
                "profile": "exception_leader__alpha_ge_85",
                "metrics": "n=13 · win5 69.2% · avg5 +3.04%",
            }
        if rank is not None and 1 <= rank <= 5 and edge is not None and edge >= 7:
            return {
                "level": "near",
                "label": "KOSDAQ 관찰 Top5",
                "profile": "rank_top5__edge_ge_7",
                "metrics": "n=29 · win5 65.5% · avg5 +7.35%",
            }
    return {"level": "fail", "label": "검증 프로필 미달", "profile": "", "metrics": ""}


def build_kr_shadow_gate_records(
    records: List[Dict[str, Any]],
    planner_payload: Dict[str, Any] | None = None,
    *,
    limit: int = 5,
) -> Dict[str, List[Dict[str, Any]]]:
    """Build display-only KOSPI/KOSDAQ shadow-gate sections.

    These rows are not re-ranked into the production Top5. They are duplicated
    into an explicit upper section so operators can see the tested shadow gates
    without silently changing the scanner engine.
    """
    source_records = enrich_signal_rows_with_planner_trace(records or [], planner_payload) if planner_payload else (records or [])
    source_records = _attach_display_theme_day_metrics(source_records)
    sorted_rows = sort_signal_rows_by_planner_rank(source_records, planner_payload)
    limit_n = max(int(limit or 0), 0)

    def _mark(rows: List[Dict[str, Any]], *, section: str, order: int, gate: Dict[str, Any]) -> List[Dict[str, Any]]:
        marked: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows[:limit_n], start=1):
            copy = dict(row)
            copy["_analysis_section"] = section
            copy["_analysis_section_order"] = order
            copy["_analysis_section_rank"] = idx
            copy["_source_order"] = "shadow_gate_above_standard"
            copy["_shadow_gate"] = dict(gate)
            marked.append(copy)
        return marked

    kosdaq = _mark(
        [row for row in sorted_rows if is_kosdaq_ordered_rebound_shadow_gate_row(row)],
        section="KOSDAQ Shadow",
        order=-20,
        gate={
            "label": "KOSDAQ 최우선 관찰",
            "profile": "5D_ordered_5v5",
            "conditions": "tech<=80 · 테마평균 decision<=63.1 · 테마후보>=7 · trend=UP",
            "metrics": "n=21 · win 76.2% · test win 81.8% · test min -2.27% · loss5 0%",
            "note": "손실 꼬리 축소형 +5% shadow gate, 운영 랭킹 교체 아님",
        },
    )
    kospi = _mark(
        [row for row in sorted_rows if is_kospi_ordered_shadow_gate_row(row)],
        section="KOSPI Shadow",
        order=-10,
        gate={
            "label": "KOSPI ordered 관찰",
            "profile": "5D_ordered_10v5",
            "conditions": "prob_clean>=35.5 · alpha>=67 · CORE_TREND · 테마평균 alpha<=81",
            "metrics": "n=24 · win 70.8% · test win 87.5% · stop 12.5% · loss5 0%",
            "note": "최신 테마 보정 후 +10% shadow gate, 운영 랭킹 교체 아님",
        },
    )
    return {
        "kosdaq": kosdaq,
        "kospi": kospi,
        "combined": kosdaq + kospi,
    }


def attach_display_theme_day_metrics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _attach_display_theme_day_metrics(records)


def _attach_display_theme_day_metrics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach same-scan theme aggregates when storage rows do not have them.

    Ordered shadow gates were validated with dynamic same-day theme features.
    Live scan rows already carry primary_theme and row-level scores, but not
    always the precomputed theme aggregates, so compute display-only equivalents
    over the rows visible in the current scan/archive payload.
    """
    rows = [dict(row) for row in records or [] if isinstance(row, dict)]
    grouped: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        market = _row_market(row)
        if market not in {"KOSPI", "KOSDAQ"}:
            continue
        theme = _row_text(row, "primary_theme", "테마", "theme").strip()
        if not theme or theme.lower() in {"nan", "none", "null", "unclassified", "unknown"}:
            continue
        date_key = _row_theme_date_key(row)
        key = (market, date_key, theme)
        bucket = grouped.setdefault(key, {"tickers": set(), "alpha": [], "decision": []})
        ticker = _row_text(row, "ticker", "티커", "Ticker", "symbol").strip()
        if ticker:
            bucket["tickers"].add(ticker)
        alpha = _row_float(row, "alpha_score", "Alpha", "종합점수")
        decision = _row_float(row, "decision_score", "Decision Score", "score")
        if alpha is not None:
            bucket["alpha"].append(alpha)
        if decision is not None:
            bucket["decision"].append(decision)
    metrics = {
        key: {
            "symbol_count": float(len(value["tickers"])),
            "avg_alpha": (sum(value["alpha"]) / len(value["alpha"])) if value["alpha"] else None,
            "avg_decision": (sum(value["decision"]) / len(value["decision"])) if value["decision"] else None,
        }
        for key, value in grouped.items()
    }
    if not metrics:
        return rows
    for row in rows:
        market = _row_market(row)
        theme = _row_text(row, "primary_theme", "테마", "theme").strip()
        date_key = _row_theme_date_key(row)
        metric = metrics.get((market, date_key, theme))
        if not metric:
            continue
        if _row_float(row, "theme_day_symbol_count", "_theme_day_symbol_count") is None:
            row["_theme_day_symbol_count"] = metric["symbol_count"]
        if metric["avg_alpha"] is not None and _row_float(row, "theme_day_avg_alpha_score", "_theme_day_avg_alpha_score") is None:
            row["_theme_day_avg_alpha_score"] = round(metric["avg_alpha"], 2)
        if (
            metric["avg_decision"] is not None
            and _row_float(row, "theme_day_avg_decision_score", "_theme_day_avg_decision_score") is None
        ):
            row["_theme_day_avg_decision_score"] = round(metric["avg_decision"], 2)
    return rows


def _row_theme_date_key(row: Dict[str, Any]) -> str:
    text = _row_text(row, "base_trade_date", "trade_date", "recommended_at", "created_at", "generated_at").strip()
    return text[:10] if text else ""


def split_stream_records(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """raw 후보 리스트를 Stream A (안전, 자본 80%) / Stream B (EXCEPTION_LEADER, 20%)
    로 분리한다. 정렬 순서는 입력을 그대로 유지한다.
    """
    raw = list(records or [])
    return {
        "stream_a": [r for r in raw if isinstance(r, dict) and not is_exception_leader_row(r)],
        "stream_b": [r for r in raw if isinstance(r, dict) and is_exception_leader_row(r)],
    }


def _record_ticker_key(row: Dict[str, Any]) -> str:
    return str(
        _coalesce_present(row.get("ticker"), row.get("티커"), row.get("Ticker"), row.get("symbol"))
        or ""
    ).strip()


def _planner_exception_leader_records(
    planner_payload: Dict[str, Any] | None,
    existing_tickers: set[str],
) -> List[Dict[str, Any]]:
    """Lift planner-only Exception Leaders into display/report candidates.

    The scanner result rows are the Top5 source of truth, but Exception Leader
    candidates can be produced only in planner ``watchlist_meta`` after the raw
    scan rows have already been narrowed. Without this bridge, Discord/web deep
    reports silently show Top5 only even when the planner emitted Stream B.
    """
    payload = planner_payload if isinstance(planner_payload, dict) else {}
    seen = {str(ticker).strip() for ticker in existing_tickers if str(ticker).strip()}
    additions: List[Dict[str, Any]] = []
    for section in ("watchlist_meta", "decisions"):
        for item in payload.get(section, []) or []:
            if not isinstance(item, dict) or not is_exception_leader_row(item):
                continue
            ticker = _record_ticker_key(item)
            if not ticker or ticker in seen:
                continue
            copy = dict(item)
            copy.setdefault("ticker", ticker)
            copy.setdefault("decision", "EXCEPTION_LEADER")
            copy.setdefault("decision_bucket", "exception_leader")
            copy.setdefault("risk_label", "EXCEPTION_LEADER")
            copy.setdefault("reason", "exception_leader_planner_addon")
            additions.append(copy)
            seen.add(ticker)
    return additions


def merge_profile_exception_leaders_into_planner(
    planner_payload: Dict[str, Any] | None,
    profile_payload: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Return planner payload augmented with profile-only Exception Leaders.

    Some KOSPI runs emit Exception Leader rows only in
    ``profile_diagnostics.exception_leaders.watchlist_meta``. The lower
    diagnostics table reads that profile payload directly, while Top5 cards,
    Top Deep reports, archives, and Discord renderers consume planner payload.
    This bridge keeps all surfaces on the same candidate contract.
    """
    planner = dict(planner_payload) if isinstance(planner_payload, dict) else {}
    profile = profile_payload if isinstance(profile_payload, dict) else {}
    exception_block = profile.get("exception_leaders") if isinstance(profile.get("exception_leaders"), dict) else {}
    profile_rows = exception_block.get("watchlist_meta") if isinstance(exception_block.get("watchlist_meta"), list) else []
    if not profile_rows:
        return planner

    watchlist_meta = list(planner.get("watchlist_meta") or []) if isinstance(planner.get("watchlist_meta"), list) else []
    existing = {
        _record_ticker_key(row)
        for section in (planner.get("decisions") or [], watchlist_meta)
        for row in (section if isinstance(section, list) else [])
        if isinstance(row, dict)
    }
    for row in profile_rows:
        if not isinstance(row, dict):
            continue
        ticker = _record_ticker_key(row)
        if not ticker or ticker in existing:
            continue
        copy = dict(row)
        copy.setdefault("ticker", ticker)
        copy.setdefault("decision", "EXCEPTION_LEADER")
        copy.setdefault("decision_bucket", "exception_leader")
        copy.setdefault("risk_label", "EXCEPTION_LEADER")
        copy.setdefault("reason", "exception_leader_watchlist")
        watchlist_meta.append(copy)
        existing.add(ticker)
    planner["watchlist_meta"] = watchlist_meta
    return planner


def build_top5_plus_exception_records(
    records: List[Dict[str, Any]],
    planner_payload: Dict[str, Any] | None = None,
    *,
    top_limit: int = 5,
    exception_limit: int | None = 5,
) -> Dict[str, List[Dict[str, Any]]]:
    """Return the service display contract: Top5 main + Exception add-on.

    Top5 remains the primary service output. Exception Leaders are not merged
    into that ranking; they are appended as a separate, clearly labelled add-on
    for extra precision analysis and Discord output.
    """
    source_records = enrich_signal_rows_with_planner_trace(records or [], planner_payload) if planner_payload else (records or [])
    if planner_payload:
        source_records = list(source_records) + _planner_exception_leader_records(
            planner_payload,
            {_record_ticker_key(row) for row in source_records if isinstance(row, dict)},
        )
    sorted_rows = sort_signal_rows_by_planner_rank(source_records, planner_payload)
    streams = split_stream_records(sorted_rows)
    top_limit_n = max(int(top_limit or 0), 0)
    validated_top = []
    for row in streams["stream_a"]:
        profile = validated_winner_profile(row)
        if profile.get("level") in {"pass", "near"}:
            copy = dict(row)
            copy["_validated_winner_profile"] = profile
            validated_top.append(copy)
    top_records = validated_top[:top_limit_n] if validated_top else streams["stream_a"][:top_limit_n]

    exception_records = []
    for row in streams["stream_b"]:
        copy = dict(row)
        copy["_validated_winner_profile"] = validated_winner_profile(row)
        exception_records.append(copy)
    if exception_limit is not None:
        exception_records = exception_records[: max(int(exception_limit or 0), 0)]

    def _mark(rows: List[Dict[str, Any]], section: str, order: int) -> List[Dict[str, Any]]:
        marked: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            copy = dict(row)
            copy["_analysis_section"] = section
            copy["_analysis_section_order"] = order
            copy["_analysis_section_rank"] = idx
            copy["_source_order"] = "top5_main_plus_exception_addon"
            marked.append(copy)
        return marked

    top_marked = _mark(top_records, "Top5", 0)
    exception_marked = _mark(exception_records, "Exception Leader", 1)
    return {
        "top5": top_marked,
        "exception_leaders": exception_marked,
        "combined": top_marked + exception_marked,
    }


def build_live_cockpit_summary(
    stream_a_rows: List[Dict[str, Any]],
    stream_b_rows: List[Dict[str, Any]],
    *,
    market: str,
    strict_quality_gate: bool = True,
) -> Dict[str, Any]:
    """Summarize the live trading cockpit in operator-facing terms."""
    market_key = str(market or "").upper()
    policies = {
        "KOSPI": {
            "policy": "exception_leader OR edge>=5",
            "validated_win": "77.95%",
            "validated_return": "+8.80%",
            "sample": "n=254",
        },
        "KOSDAQ": {
            "policy": "exception_leader AND trend=UP",
            "validated_win": "80.00%",
            "validated_return": "+13.81% MFE",
            "sample": "n=65",
        },
    }
    policy = policies.get(
        market_key,
        {
            "policy": "segment policy",
            "validated_win": "-",
            "validated_return": "-",
            "sample": "-",
        },
    )
    stream_a_count = len(stream_a_rows or [])
    stream_b_count = len(stream_b_rows or [])
    return {
        "market": market_key or "-",
        "actionable_count": stream_a_count + stream_b_count,
        "stream_a_count": stream_a_count,
        "stream_b_count": stream_b_count,
        "quality_gate": "ON" if strict_quality_gate else "OFF",
        **policy,
    }


def enrich_signal_rows_with_planner_trace(
    rows: List[Dict[str, Any]],
    planner_payload: Dict[str, Any] | None,
) -> List[Dict[str, Any]]:
    """Attach planner risk trace to live scanner rows before UI normalization.

    Live scan cards are rendered from raw scanner worker results, while
    loss-risk is produced later by the planner handoff. Merge by ticker so the
    operator sees the same risk trace in live scan cards as in archived rows.
    """
    payload = planner_payload if isinstance(planner_payload, dict) else {}
    trace_by_ticker: Dict[str, Dict[str, Any]] = {}
    for section in ("decisions", "watchlist_meta"):
        for item in payload.get(section, []) or []:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker") or item.get("Ticker") or "").strip()
            if not ticker:
                continue
            trace = trace_by_ticker.setdefault(ticker, {})
            for key in (
                "stock_name",
                "decision",
                "decision_bucket",
                "priority_rank",
                "decision_score",
                "prob_clean",
                "prob_5",
                "_prob_clean",
                "_prob_5",
                "alpha_score",
                "expected_edge_score",
                "expected_return_1d_pct",
                "expected_return_3d_pct",
                "phase25_prob",
                "loss_risk_score",
                "theme_risk",
                "rationale",
                "real_trend",
                "trend",
                "selection_lane",
                "volume",
                "volume_ratio",
                "volume_confirmed",
                "relative_rank_score",
                "relative_rank_pct",
                "relative_rank_model",
                "final_action",
                "entry_condition_text",
                "stop_condition_text",
                "structured_conditions",
                "target_tp_pct",
                "stop_sl_pct",
                "hold_days",
                "entry_policy",
                "risk_label",
                "reason",
            ):
                if _is_present(item.get(key)):
                    trace[key] = item.get(key)

    enriched: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        merged = dict(row)
        ticker = str(
            _coalesce_present(
                merged.get("ticker"),
                merged.get("티커"),
                merged.get("Ticker"),
                merged.get("symbol"),
            )
            or ""
        ).strip()
        for key, value in trace_by_ticker.get(ticker, {}).items():
            if not _is_present(merged.get(key)):
                merged[key] = value
        enriched.append(merged)
    return enriched


def _display_rank_float(value: Any) -> float | None:
    numeric = _parse_percent_value(value)
    if numeric is None:
        return None
    return numeric


def sort_signal_rows_by_planner_rank(
    rows: List[Dict[str, Any]],
    planner_payload: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Sort signal rows by the final planner order used for trading.

    ``Decision Score`` is a useful scanner/raw model value, but the actionable
    top list must follow planner priority/relative-rank because that is where
    loss-risk, market regime, and admission gates are applied.
    """
    payload = planner_payload if isinstance(planner_payload, dict) else {}
    planner_order: Dict[str, int] = {}
    for section in ("decisions", "watchlist_meta"):
        for idx, item in enumerate(payload.get(section, []) or [], start=1):
            if not isinstance(item, dict):
                continue
            ticker = str(_coalesce_present(item.get("ticker"), item.get("Ticker")) or "").strip()
            if ticker and ticker not in planner_order:
                planner_order[ticker] = idx

    def _decision_priority(value: Any) -> int:
        d = str(value or "").upper()
        return {
            "STRONG_BUY": 0,
            "PICK": 0,
            "BUY": 0,
            "PRIORITY_WATCHLIST": 1,
            "WATCHLIST": 2,
            "WATCHLIST_ONLY": 3,
            "EXCEPTION_LEADER": 4,
        }.get(d, 9)

    def _key(row: Dict[str, Any]) -> tuple:
        ticker = str(
            _coalesce_present(row.get("ticker"), row.get("티커"), row.get("Ticker"), row.get("symbol"))
            or ""
        ).strip()
        priority = _display_rank_float(row.get("priority_rank"))
        planner_idx = planner_order.get(ticker)
        relative = _display_rank_float(row.get("relative_rank_score")) or 0.0
        score = _display_rank_float(row.get("decision_score") or row.get("Decision Score") or row.get("score")) or 0.0
        return (
            int(priority) if priority is not None else int(planner_idx) if planner_idx is not None else 9999,
            _decision_priority(row.get("decision") or row.get("Decision") or row.get("decision_bucket")),
            -relative,
            -score,
            ticker,
        )

    return sorted([dict(row) for row in rows or [] if isinstance(row, dict)], key=_key)


def build_signal_display_rows(rows: List[Dict[str, Any]], limit: int | None = None) -> List[Dict[str, Any]]:
    """Normalize scanner/archive rows into a compact decision list.

    Card '정확성' = (decision × market × scan_mode) segment의 historical OOS
    win rate. raw model score (phase25_prob, prob_clean, ml_prob)는
    calibrated probability가 아니라 정렬용 score이므로 정확도로 표시 금지.
    """
    normalized: List[Dict[str, Any]] = []
    source_rows = rows or []
    if limit is not None:
        source_rows = source_rows[: max(int(limit or 0), 0)]

    for rank, row in enumerate(source_rows, start=1):
        if not isinstance(row, dict):
            continue
        ticker = str(_coalesce_present(row.get("ticker"), row.get("티커"), row.get("Ticker"), row.get("symbol")) or "").strip()
        name = str(_coalesce_present(row.get("stock_name"), row.get("종목명"), row.get("Name"), row.get("name")) or "").strip()
        decision = str(_coalesce_present(row.get("decision"), row.get("Decision"), row.get("decision_bucket")) or "").strip()
        if is_exception_leader_row(row):
            decision = "EXCEPTION_LEADER"
        tier = str(_coalesce_present(row.get("tier"), row.get("Tier")) or "").strip()
        strategy = str(_coalesce_present(row.get("strategy"), row.get("전략"), row.get("strategy_family")) or "").strip()
        buy_signal = " · ".join(part for part in (decision, tier, strategy) if part) or "-"

        # 카드 UI '정확성' 일관화 (스캐너 ↔ 아카이브 같은 RUN/티커에 동일 값).
        #
        # coalesce 순서 — 양쪽 source 가 모두 보유한 키만 사용해서 결정성을 보장한다.
        #   1) segment_win  : (decision × market × scan_mode) 별 historical OOS
        #                     win rate. 표본 부족/미측정 segment 에선 None.
        #   2) phase25_oos_win_rate_pct : variant 별 학습 시 OOS win rate.
        #                     scanner res_data + archive DB 컬럼 양쪽 모두 같은 키로 보유.
        #   3) prob_clean / _prob_clean : 모델 raw clean-hit 확률 (numeric).
        #                     scanner 는 ``_prob_clean`` (UI dict), archive 는
        #                     ``prob_clean`` (DB) 키로 보유 — 둘 다 같은 numeric.
        #                     calibrated 확률은 아니지만 segment/variant OOS 가 모두
        #                     None 일 때 빈 카드를 피하기 위한 마지막 fallback.
        #
        # 'accuracy' 로 노출하지 말아야 하는 키 (정렬용 raw score, 다른 의미):
        #   - 정밀확률    : scanner-전용 문자열 포맷 (= prob_clean). DB numeric
        #                  키가 없는 legacy/UI row 에서만 마지막 fallback 으로 사용
        #                  해서 원천값을 비워 보이지 않게 한다.
        #   - phase25_prob, AI확률, ml_prob : prob_5(5pct breakout) 계열로 의미 다름
        segment_win = lookup_segment_win_rate(
            decision=decision,
            market=row.get("market") or row.get("market_subtype"),
            scan_mode=row.get("scan_mode") or row.get("Scan Mode"),
            ticker=ticker,
            horizon_days=5,
        )
        accuracy_source = _coalesce_present(
            segment_win,
            row.get("phase25_oos_win_rate_pct"),
            row.get("prob_clean"),
            row.get("_prob_clean"),
            row.get("정밀확률"),
        )
        day_change_source = _coalesce_present(
            row.get("전일비"),
            row.get("day_return_pct"),
            row.get("prev_pct_change"),
            row.get("1D Change"),
        )
        score_source = _coalesce_present(row.get("decision_score"), row.get("Decision Score"), row.get("score"))
        loss_risk_source = _coalesce_present(row.get("loss_risk_score"), row.get("Loss Risk"))
        risk_flags = _coerce_text_list(
            _coalesce_present(row.get("theme_risk"), row.get("risk_flags"), row.get("rationale")),
            limit=3,
        )
        theme = str(_coalesce_present(row.get("primary_theme"), row.get("테마"), row.get("Theme")) or "").strip()
        trend = str(_coalesce_present(row.get("trend"), row.get("추세"), row.get("Trend"), row.get("initial_trend")) or "").strip()
        entry = str(_coalesce_present(row.get("매수가(-2%)"), row.get("Entry"), row.get("entry_reference_price")) or "").strip()
        tp = str(_coalesce_present(row.get("TP"), row.get("target_tp_pct")) or "").strip()
        sl = str(_coalesce_present(row.get("SL"), row.get("stop_sl_pct")) or "").strip()
        latest_return = _coalesce_present(row.get("latest_return_pct"), row.get("return_1d_pct"), row.get("return_3d_pct"))
        action = build_action_display(row)
        practical_gate = evaluate_practical_entry_gate(row)
        gate_evidence = practical_gate.get("evidence") if isinstance(practical_gate.get("evidence"), dict) else {}
        shadow_gate = row.get("_shadow_gate") if isinstance(row.get("_shadow_gate"), dict) else {}

        day_change_numeric = _parse_percent_value(day_change_source)
        normalized.append(
            {
                "rank": rank,
                "ticker": ticker,
                "name": name,
                "analysis_section": str(row.get("_analysis_section") or "").strip(),
                "analysis_section_rank": row.get("_analysis_section_rank"),
                "buy_signal": buy_signal,
                "accuracy": _format_accuracy_label(accuracy_source),
                "day_change": _format_percent_label(day_change_source),
                "day_change_value": day_change_numeric,
                "score": _format_score_label(score_source),
                "loss_risk": _format_risk_score_label(loss_risk_source),
                "loss_risk_level": _risk_level_label(loss_risk_source),
                "risk_flags": risk_flags,
                "theme": theme or "-",
                "trend": trend or "-",
                "entry": entry or "-",
                "tp": tp or "-",
                "sl": sl or "-",
                "latest_return": _format_percent_label(latest_return),
                "action_label": action["label"],
                "action_condition": action["condition"],
                "stop_condition": action["stop_condition"],
                "action_reasons": action["reasons"],
                "practical_gate_level": practical_gate.get("level"),
                "practical_gate_pass": practical_gate.get("pass"),
                "practical_gate_promote": practical_gate.get("promote"),
                "practical_gate_label": practical_gate.get("label"),
                "practical_gate_reasons": practical_gate.get("reasons") or [],
                "practical_gate_evidence": gate_evidence,
                "shadow_gate_label": shadow_gate.get("label"),
                "shadow_gate_profile": shadow_gate.get("profile"),
                "shadow_gate_conditions": shadow_gate.get("conditions"),
                "shadow_gate_metrics": shadow_gate.get("metrics"),
                "shadow_gate_note": shadow_gate.get("note"),
            }
        )
    return normalized


def build_watchlist_display_rows(
    watchlist: List[str],
    watchlist_meta: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
    scanner_payload: Dict[str, Any] | None = None,
) -> tuple[List[Dict[str, Any]], List[str]]:
    meta_by_ticker = {
        str(row.get("ticker", "")): row
        for row in (watchlist_meta or [])
        if isinstance(row, dict) and str(row.get("ticker", "")).strip()
    }
    decision_by_ticker = {
        str(row.get("ticker", "")): row
        for row in (decisions or [])
        if isinstance(row, dict) and str(row.get("ticker", "")).strip()
    }
    candidate_by_ticker: Dict[str, Dict[str, Any]] = {}
    scanner_candidates = (
        (scanner_payload or {}).get("candidates", [])
        if isinstance(scanner_payload, dict)
        else []
    )
    for row in scanner_candidates or []:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker", "") or "").strip()
        if ticker:
            candidate_by_ticker[ticker] = row

    rows: List[Dict[str, Any]] = []
    # Keep legacy planner fields visible when present. Phase25 fields are added
    # after them, but not used as fabricated replacements for missing source data.
    exact_numeric_fields = [
        "Alpha",
        "Conviction",
        "Decision Score",
        "Prob5",
        "Clean",
        "Model Prob",
        "OOS Win %",
        "OOS Ret %",
    ]
    for rank, ticker in enumerate(watchlist or [], start=1):
        meta = meta_by_ticker.get(str(ticker), {})
        decision = decision_by_ticker.get(str(ticker), {})
        candidate = candidate_by_ticker.get(str(ticker), {})
        feature_snapshot = candidate.get("feature_snapshot", {}) if isinstance(candidate.get("feature_snapshot"), dict) else {}

        alpha_value = _coalesce_value(
            meta.get("alpha_score"),
            decision.get("alpha_score"),
            candidate.get("alpha_score"),
            feature_snapshot.get("alpha_score"),
        )
        decision_score_value = _coalesce_value(
            meta.get("decision_score"),
            decision.get("decision_score"),
            feature_snapshot.get("decision_score"),
            candidate.get("score"),
        )
        conviction_value = _coalesce_value(
            meta.get("conviction_score"),
            decision.get("conviction_score"),
            feature_snapshot.get("conviction_score"),
        )
        prob5_value = _coalesce_value(
            meta.get("prob_5"),
            decision.get("prob_5"),
            feature_snapshot.get("prob_5"),
        )
        clean_value = _coalesce_value(
            meta.get("prob_clean"),
            decision.get("prob_clean"),
            feature_snapshot.get("prob_clean"),
        )
        ph25_prob_value = _coalesce_value(
            meta.get("phase25_prob"),
            decision.get("phase25_prob"),
            feature_snapshot.get("phase25_prob"),
        )
        oos_win_value = _coalesce_value(
            decision.get("phase25_oos_win_rate_pct"),
            feature_snapshot.get("phase25_oos_win_rate_pct"),
        )
        oos_ret_value = _coalesce_value(
            decision.get("phase25_oos_avg_return_pct"),
            feature_snapshot.get("phase25_oos_avg_return_pct"),
        )
        sig_dir_value = _coalesce_value(
            decision.get("phase25_signal_direction"),
            feature_snapshot.get("phase25_signal_direction"),
        )
        primary_theme = _coalesce_value(
            decision.get("primary_theme"),
            feature_snapshot.get("primary_theme"),
        )
        decision_label = _coalesce_value(
            meta.get("decision"),
            decision.get("decision"),
        )

        rows.append(
            {
                "Rank": rank,
                "Ticker": ticker,
                "Name": _coalesce_value(meta.get("stock_name"), decision.get("stock_name"), candidate.get("stock_name")),
                "Decision": decision_label,
                "Theme": primary_theme,
                "Alpha": alpha_value,
                "Conviction": conviction_value,
                "Decision Score": decision_score_value,
                "Prob5": prob5_value,
                "Clean": clean_value,
                "Model Prob": ph25_prob_value,
                "OOS Win %": oos_win_value,
                "OOS Ret %": oos_ret_value,
                "SigDir": sig_dir_value,
            }
        )

    visible_numeric_fields = [
        field
        for field in exact_numeric_fields
        if any(_is_present(row.get(field)) for row in rows)
    ]
    return rows, visible_numeric_fields


def build_top_candidate_rows(planner_payload: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Return only real BUY-grade picks. OBSERVE/AVOID never appear in Top-N.

    Earlier this list ranked the entire decisions array by score, so OBSERVE
    rows with score=100 occupied Top 5 slots that the user could not act on,
    and the realized win/return metric was contaminated by hold-rated rows.
    Now we keep only PRIORITY_WATCHLIST/WATCHLIST/PICK/STRONG_BUY rows. If
    none qualify, we return [] and the UI shows a 'no live signal' state.

    Columns are reduced to what the user/analyst actually decides on:
    decision label, theme, trend, model conviction (phase25_prob vs gate),
    OOS proof (oos_win_rate / oos_avg_return), and the segment-specific
    entry / TP / SL the trader is supposed to use. Removed columns (Edge,
    1D/3D Exp, Decision Score, full Reason text) were either redundant,
    saturated, or computed from stale phase18 anchors.
    """
    payload = planner_payload if isinstance(planner_payload, dict) else {}
    decisions = payload.get("decisions", []) if isinstance(payload.get("decisions"), list) else []
    watchlist_meta = payload.get("watchlist_meta", []) if isinstance(payload.get("watchlist_meta"), list) else []

    BUY_GRADES = {"PICK", "BUY", "STRONG_BUY", "PRIORITY_WATCHLIST", "WATCHLIST", "WATCHLIST_ONLY", "EXCEPTION_LEADER"}

    def _is_buy(row: Dict[str, Any]) -> bool:
        dec = str(row.get("decision", "") or "").upper().strip()
        if not dec:
            return _is_present(row.get("priority_rank")) or _is_present(row.get("decision_score"))
        return dec in BUY_GRADES

    # 1) Pull EXCEPTION_LEADER from watchlist_meta. EL is attached as a
    #    watchlist_meta entry with reason='exception_leader_watchlist' but never
    #    appears in decisions[]. Production measurements (30d): EL win 75-100%,
    #    avg 5-10% — better than the picked baseline. Surface them as a
    #    first-class BUY signal in Top-N rather than only in a separate panel.
    el_rows: List[Dict[str, Any]] = []
    for meta in watchlist_meta:
        if not isinstance(meta, dict):
            continue
        reason = str(meta.get("reason", "") or "").lower()
        risk_label = str(meta.get("risk_label", "") or "").upper()
        if reason == "exception_leader_watchlist" or risk_label == "EXCEPTION_LEADER":
            row = dict(meta)
            row["decision"] = "EXCEPTION_LEADER"
            el_rows.append(row)

    candidates = [row for row in decisions if isinstance(row, dict) and _is_buy(row)]
    # If decisions list is empty (e.g. MARKET_POLICY_WATCHLIST_ONLY downgraded
    # everything), surface watchlist_meta entries as the user's actual picks.
    if not candidates and watchlist_meta and not el_rows:
        candidates = [row for row in watchlist_meta if isinstance(row, dict)]

    # 2026-05-09 정책: 8:2 자본 배분에 따라 Stream A(PRIORITY/WATCHLIST/OBSERVE,
    # 자본 80%)가 위, Stream B(EXCEPTION_LEADER, 자본 20%)가 아래.
    # build_top_candidate_compact_view가 decision 라벨로 두 그룹 분리하므로
    # 여기서는 EL을 candidates 끝에 합쳐 sorted 순서만 PRIORITY 우선으로 둠.
    seen_tickers = {str(r.get("ticker", "") or "") for r in el_rows}
    candidates = [r for r in candidates if str(r.get("ticker", "") or "") not in seen_tickers]
    # EL을 합쳐서 sorted_rows에 같이 노출 (compact_view에서 stream A/B로 분리됨)
    candidates = candidates + el_rows

    def _decision_priority(dec: str) -> int:
        """Lower number = higher. PRIORITY/WATCHLIST 위, EXCEPTION_LEADER 아래
        (8:2 배분 — Stream A 안전 매매가 본진)."""
        d = str(dec or "").upper()
        order = {
            "STRONG_BUY": 0,
            "PICK": 0,
            "BUY": 0,
            "PRIORITY_WATCHLIST": 1,
            "WATCHLIST": 2,
            "WATCHLIST_ONLY": 3,
            "EXCEPTION_LEADER": 5,  # Stream B — Stream A 다음
        }
        return order.get(d, 9)

    sorted_rows = sorted(
        candidates,
        key=lambda row: (
            _decision_priority(row.get("decision")),
            int(row.get("priority_rank", 9999) or 9999),
            -float(row.get("decision_score", 0.0) or 0.0),
            str(row.get("ticker", "") or ""),
        ),
    )

    def _exit_policy(ticker: str) -> Dict[str, Any]:
        """Mirror modules/scanner_services.evaluate_active_signal_candidate
        and modules/scanner_runtime.format_hourly_signal_message:
            KOSPI swing : open buy / TP +20% / SL -5% / hold 5d
            KOSDAQ swing: limit -2% / TP +10% / SL -10% / hold 5d
        Display as percent labels; absolute prices are shown elsewhere.
        """
        t = str(ticker or "").upper()
        if t.endswith(".KQ"):
            return {"Entry": "-2% (limit)", "TP": "+10%", "SL": "-10%", "Hold": "5d"}
        if t.endswith(".KS"):
            return {"Entry": "open", "TP": "+20%", "SL": "-5%", "Hold": "5d"}
        return {"Entry": "-", "TP": "-", "SL": "-", "Hold": "-"}

    top_rows: List[Dict[str, Any]] = []
    for rank, row in enumerate(sorted_rows[: max(int(limit or 0), 0)], start=1):
        sig_dir = str(row.get("phase25_signal_direction", "") or "").lower() or "-"
        oos_win = row.get("phase25_oos_win_rate_pct")
        oos_ret = row.get("phase25_oos_avg_return_pct")
        ph25 = row.get("phase25_prob")
        thr = row.get("phase25_recommended_threshold")
        ticker = str(row.get("ticker", "") or "")
        policy = _exit_policy(ticker)
        structured = row.get("structured_conditions") if isinstance(row.get("structured_conditions"), dict) else {}
        action = build_action_display(row)
        entry_label = str(_coalesce_present(row.get("entry_policy"), structured.get("entry_policy"), policy["Entry"]) or "")
        tp_value = _coalesce_present(row.get("target_tp_pct"), structured.get("target_tp_pct"))
        sl_value = _coalesce_present(row.get("stop_sl_pct"), structured.get("stop_sl_pct"))
        hold_value = _coalesce_present(row.get("hold_days"), structured.get("hold_days"))
        tp_label = _format_signed_percent_label(tp_value, policy["TP"])
        sl_label = _format_signed_percent_label(sl_value, policy["SL"])
        hold_numeric = _parse_percent_value(hold_value)
        hold_label = f"{int(hold_numeric)}d" if hold_numeric is not None else policy["Hold"]
        top_rows.append(
            {
                "Rank": rank,
                "Ticker": ticker,
                "Name": str(row.get("stock_name", "") or ""),
                "Decision": str(row.get("decision", "") or ""),
                "Theme": str(row.get("primary_theme", "") or ""),
                "Trend": str(row.get("real_trend", "") or ""),
                "Model Prob": (round(float(ph25), 1) if ph25 not in (None, "") else None),
                "Gate Thr": (round(float(thr), 1) if thr not in (None, "") else None),
                "OOS Win %": (round(float(oos_win), 1) if oos_win not in (None, "") else None),
                "OOS Ret %": (round(float(oos_ret), 2) if oos_ret not in (None, "") else None),
                "Loss Risk": (round(float(row.get("loss_risk_score")), 1) if row.get("loss_risk_score") not in (None, "") else None),
                "Risk Flags": ", ".join(_coerce_text_list(row.get("theme_risk"), limit=5)),
                "Action": action["label"],
                "Entry Condition": action["condition"],
                "Stop Condition": action["stop_condition"],
                "SigDir": sig_dir,
                "Entry": entry_label or policy["Entry"],
                "TP": tp_label,
                "SL": sl_label,
                "Hold": hold_label,
            }
        )
    return top_rows


# 2026-05-08 (swing-main-r39): UI 단순화. Top-N 표는 매수 결정에 직접 필요한
# 핵심 7컬럼만 노출하고, 11개 numeric 메타는 티커 선택 시 팝업에서 보게 한다.
TOP_N_COMPACT_COLUMNS = (
    "Rank", "Ticker", "Name", "Decision", "Entry", "TP", "SL",
)

# Card '정확성' = segment historical OOS win rate (5d). 카드에 별도 컬럼.
TOP_N_CARD_COLUMNS = (
    "Rank", "Ticker", "Name", "Decision", "Accuracy", "Entry", "TP", "SL",
)


def build_top_candidate_compact_view(planner_payload: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:
    """Stream A (Top-N 안전 매매) + Stream B (EXCEPTION_LEADER 급등 잡기)
    카드를 8:2 자본 배분 정책에 맞춰 분리 반환.

    Returns:
        {
            "stream_a_rows": [{Rank, Ticker, Name, Decision, Entry, TP, SL, Accuracy}, ...]  # PRIORITY/WATCHLIST 위주
            "stream_b_rows": [...]  # EXCEPTION_LEADER만
            "detail_by_ticker": {ticker: <full row>},
            "compact_rows": Stream A + B 합본 (legacy 호환)
        }

    카드 정확성('Accuracy') = segment historical OOS win rate (5d, dedup 측정).
    raw model score는 정확도로 노출 안 함.
    """
    from modules.segment_accuracy import lookup_segment_win_rate

    full = build_top_candidate_rows(planner_payload, limit=limit)

    def _augment(row: Dict[str, Any]) -> Dict[str, Any]:
        ticker = str(row.get("Ticker", "") or "")
        market_guess = "KOSPI" if ticker.endswith(".KS") else ("KOSDAQ" if ticker.endswith(".KQ") else None)
        scan_mode_guess = "SWING"  # Top-N 카드 default; 호출자가 명시하면 override 가능
        win = lookup_segment_win_rate(
            decision=row.get("Decision"),
            market=market_guess,
            scan_mode=scan_mode_guess,
            ticker=ticker,
            horizon_days=5,
        )
        compact = {col: row.get(col) for col in TOP_N_COMPACT_COLUMNS if col in row}
        compact["Accuracy"] = f"{win:.1f}%" if win is not None else "-"
        return compact

    stream_a_rows: List[Dict[str, Any]] = []
    stream_b_rows: List[Dict[str, Any]] = []
    detail_by_ticker: Dict[str, Dict[str, Any]] = {}
    for row in full:
        compact = _augment(row)
        ticker = str(row.get("Ticker", "") or "")
        if ticker:
            detail_by_ticker[ticker] = row
        decision = str(row.get("Decision", "") or "").upper()
        if decision == "EXCEPTION_LEADER":
            stream_b_rows.append(compact)
        else:
            stream_a_rows.append(compact)

    # legacy compat
    compact_rows = stream_a_rows + stream_b_rows
    return {
        "stream_a_rows": stream_a_rows,
        "stream_b_rows": stream_b_rows,
        "compact_rows": compact_rows,
        "detail_by_ticker": detail_by_ticker,
    }


@dataclass
class BackgroundScanState:
    market: str
    scan_mode: str
    engine_label: str
    max_scan: int
    run_id: str = field(default_factory=lambda: f"RUN-{uuid4().hex[:8].upper()}")
    job_id: str = field(default_factory=lambda: uuid4().hex[:10])
    status: str = "queued"
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    total_scans: int = 0
    completed_scans: int = 0
    progress: float = 0.0
    current_symbol: str = ""
    status_line: str = "스캔을 준비 중입니다."
    error: str = ""
    results: List[Dict[str, Any]] = field(default_factory=list)
    logs: List[Dict[str, str]] = field(default_factory=list)
    scan_diagnostics: Dict[str, Any] = field(
        default_factory=lambda: {
            "filtered_count": 0,
            "worker_error_count": 0,
            "executor_exception_count": 0,
            "filtered_symbols": [],
            "error_symbols": [],
            "exception_symbols": [],
            "reject_reason_counts": {},
            "reject_reasons_by_symbol": {},
            "reject_details_by_symbol": {},
        }
    )
    bridge_info: Dict[str, Any] = field(default_factory=dict)
    regime: Dict[str, Any] = field(default_factory=dict)
    intel_data: Dict[str, Any] = field(default_factory=dict)
    planner_warning: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def append_log(self, level: str, message: str, max_items: int = 120) -> None:
        with self._lock:
            self.logs.append({"level": str(level), "message": str(message)})
            if len(self.logs) > max_items:
                self.logs = self.logs[-max_items:]

    def append_result(self, row: Dict[str, Any]) -> None:
        with self._lock:
            self.results.append(dict(row))

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "job_id": self.job_id,
                "run_id": self.run_id,
                "market": self.market,
                "scan_mode": self.scan_mode,
                "engine_label": self.engine_label,
                "max_scan": self.max_scan,
                "status": self.status,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "total_scans": self.total_scans,
                "completed_scans": self.completed_scans,
                "progress": self.progress,
                "current_symbol": self.current_symbol,
                "status_line": self.status_line,
                "error": self.error,
                "results": list(self.results),
                "logs": list(self.logs),
                "scan_diagnostics": dict(self.scan_diagnostics),
                "bridge_info": dict(self.bridge_info),
                "regime": dict(self.regime),
                "intel_data": dict(self.intel_data),
                "planner_warning": self.planner_warning,
            }
