from __future__ import annotations

import math
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import uuid4


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


def build_signal_display_rows(rows: List[Dict[str, Any]], limit: int | None = None) -> List[Dict[str, Any]]:
    """Normalize scanner/archive rows into a compact decision list.

    Card '정확성' = (decision × market × scan_mode) segment의 historical OOS
    win rate. raw model score (phase25_prob, prob_clean, ml_prob)는
    calibrated probability가 아니라 정렬용 score이므로 정확도로 표시 금지.
    """
    from modules.segment_accuracy import lookup_segment_win_rate
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
        tier = str(_coalesce_present(row.get("tier"), row.get("Tier")) or "").strip()
        strategy = str(_coalesce_present(row.get("strategy"), row.get("전략"), row.get("strategy_family")) or "").strip()
        buy_signal = " · ".join(part for part in (decision, tier, strategy) if part) or "-"

        # 카드 UI '정확성' 1순위: segment historical OOS win rate
        # (decision × market × scan_mode 별 invariant, dedup 측정값).
        # 2순위 phase25_oos_win_rate_pct (variant별 OOS win, segment lookup 부재 시).
        # raw model scores (phase25_prob, prob_clean raw, ml_prob)는 calibrated
        # probability가 아니므로 정확도 fallback에서 제외.
        segment_win = lookup_segment_win_rate(
            decision=row.get("decision") or row.get("Decision") or row.get("decision_bucket"),
            market=row.get("market") or row.get("market_subtype"),
            scan_mode=row.get("scan_mode") or row.get("Scan Mode"),
            ticker=ticker,
            horizon_days=5,
        )
        accuracy_source = _coalesce_present(
            row.get("정밀확률"),
            segment_win,
            row.get("phase25_oos_win_rate_pct"),
            row.get("prob_clean"),
            row.get("_prob_clean"),
            row.get("AI확률"),
            row.get("ml_prob"),
        )
        day_change_source = _coalesce_present(
            row.get("전일비"),
            row.get("day_return_pct"),
            row.get("prev_pct_change"),
            row.get("1D Change"),
        )
        score_source = _coalesce_present(row.get("decision_score"), row.get("Decision Score"), row.get("score"))
        theme = str(_coalesce_present(row.get("primary_theme"), row.get("테마"), row.get("Theme")) or "").strip()
        trend = str(_coalesce_present(row.get("trend"), row.get("추세"), row.get("Trend"), row.get("initial_trend")) or "").strip()
        entry = str(_coalesce_present(row.get("매수가(-2%)"), row.get("Entry"), row.get("entry_reference_price")) or "").strip()
        tp = str(_coalesce_present(row.get("TP"), row.get("target_tp_pct")) or "").strip()
        sl = str(_coalesce_present(row.get("SL"), row.get("stop_sl_pct")) or "").strip()
        latest_return = _coalesce_present(row.get("latest_return_pct"), row.get("return_1d_pct"), row.get("return_3d_pct"))

        day_change_numeric = _parse_percent_value(day_change_source)
        normalized.append(
            {
                "rank": rank,
                "ticker": ticker,
                "name": name,
                "buy_signal": buy_signal,
                "accuracy": _format_accuracy_label(accuracy_source),
                "day_change": _format_percent_label(day_change_source),
                "day_change_value": day_change_numeric,
                "score": _format_score_label(score_source),
                "theme": theme or "-",
                "trend": trend or "-",
                "entry": entry or "-",
                "tp": tp or "-",
                "sl": sl or "-",
                "latest_return": _format_percent_label(latest_return),
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
                "SigDir": sig_dir,
                "Entry": policy["Entry"],
                "TP": policy["TP"],
                "SL": policy["SL"],
                "Hold": policy["Hold"],
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
