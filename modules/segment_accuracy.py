"""Segment historical OOS win rate lookup for card UI '정확성' display.

Why this exists
---------------
Card UI 'accuracy' was previously sourced from raw model probabilities
(phase25_prob, prob_clean, ml_prob) which are 0-100 model scores, not
calibrated probabilities. KOSPI SWING 평균 raw score 35.7%, KOSDAQ SWING
12% — 사용자가 카드 보고 "정확성 너무 낮다"고 지적한 원인.

진짜 정확도 = (decision × market × scan_mode) segment의 historical OOS
win rate. 이 값은 후보별 invariant이지만 등급/시장별로 다름. 사용자가
"이 등급/시장은 historical 75% 적중"을 시각적으로 확인 가능.

Source
------
2026-05-08 horizon_full_diagnosis (deduped 7,305 rows since 2026-04-01,
return_5d_pct/return_7d_pct measured). Updated when retrain or
ranking-validation report regenerates the win-rate matrix.

Note
----
- horizon_days=5 default (KOSPI SWING 정책 5d after 4lm). 7d도 lookup 가능.
- 표본 부족(n<8) segment는 None 반환 — UI는 fallback ("-") 표시.
"""
from __future__ import annotations

from typing import Optional, Tuple


# (market, scan_mode, decision) → {horizon_days: (n, win_pct)}
# 2026-05-08 dedup 측정값. 업데이트 시 horizon_full_diagnosis_*.md 재실행.
_SEGMENT_WIN_RATE: dict[Tuple[str, str, str], dict[int, Tuple[int, float]]] = {
    # KOSPI SWING
    ("KOSPI", "SWING", "EXCEPTION_LEADER"):    {5: (53, 81.1), 7: (53, 86.8)},
    ("KOSPI", "SWING", "PRIORITY_WATCHLIST"):  {5: (11, 63.6), 7: (11, 75.0)},
    ("KOSPI", "SWING", "WATCHLIST"):           {5: (14, 71.4), 7: (14, 71.4)},
    ("KOSPI", "SWING", "OBSERVE"):             {5: (468, 69.7), 7: (373, 76.4)},
    ("KOSPI", "SWING", "WATCHLIST_ONLY"):      {5: (44, 65.9), 7: (44, 65.9)},
    # KOSPI INTRADAY
    ("KOSPI", "INTRADAY", "EXCEPTION_LEADER"): {5: (1, 100.0), 7: (1, 100.0)},  # 표본 1
    ("KOSPI", "INTRADAY", "PRIORITY_WATCHLIST"): {5: (21, 90.5), 7: (12, 75.0)},
    ("KOSPI", "INTRADAY", "OBSERVE"):          {5: (360, 63.6), 7: (359, 70.5)},
    ("KOSPI", "INTRADAY", "WATCHLIST"):        {5: (59, 66.1), 7: (57, 68.4)},
    # KOSDAQ SWING
    ("KOSDAQ", "SWING", "EXCEPTION_LEADER"):   {5: (93, 64.5), 7: (82, 69.5)},
    ("KOSDAQ", "SWING", "PRIORITY_WATCHLIST"): {5: (8, 62.5),  7: (7, 28.6)},  # 표본 적음
    ("KOSDAQ", "SWING", "WATCHLIST"):          {5: (4, 50.0),  7: (4, 50.0)},
    ("KOSDAQ", "SWING", "OBSERVE"):            {5: (315, 50.2), 7: (248, 48.8)},
    ("KOSDAQ", "SWING", "WATCHLIST_ONLY"):     {5: (24, 75.0), 7: (24, 70.8)},
    # KOSDAQ INTRADAY
    ("KOSDAQ", "INTRADAY", "EXCEPTION_LEADER"): {5: (11, 63.6), 7: (6, 50.0)},  # 표본 적음
    ("KOSDAQ", "INTRADAY", "PRIORITY_WATCHLIST"): {5: (136, 70.6), 7: (91, 73.6)},
    ("KOSDAQ", "INTRADAY", "OBSERVE"):         {5: (139, 49.6), 7: (138, 52.9)},
    ("KOSDAQ", "INTRADAY", "WATCHLIST"):       {5: (126, 64.3), 7: (122, 74.6)},
}

# 표본이 너무 작으면 사용자에게 표시 안 하는 임계값
_MIN_SAMPLE_SIZE = 8


def _resolve_market(market: str | None, ticker: str | None) -> str | None:
    raw = str(market or "").upper().strip()
    if raw in {"KOSPI", "KOSDAQ"}:
        return raw
    t = str(ticker or "").upper()
    if t.endswith(".KS"):
        return "KOSPI"
    if t.endswith(".KQ"):
        return "KOSDAQ"
    return None


def lookup_segment_win_rate(
    decision: str | None,
    market: str | None,
    scan_mode: str | None,
    horizon_days: int = 5,
    ticker: str | None = None,
) -> Optional[float]:
    """Return historical OOS win rate (%) for the segment, or None when sample
    is too small or segment is not measured.

    Args:
        decision: PRIORITY_WATCHLIST / EXCEPTION_LEADER / WATCHLIST / OBSERVE / etc.
        market: KOSPI / KOSDAQ (또는 ticker로 추론).
        scan_mode: SWING / INTRADAY.
        horizon_days: 5 (default) or 7. 학습 horizon과 일치.
        ticker: market 추론 fallback.
    """
    decision_key = str(decision or "").upper().strip()
    if not decision_key:
        return None
    market_key = _resolve_market(market, ticker)
    if market_key is None:
        return None
    scan_key = str(scan_mode or "").upper().strip()
    if scan_key not in {"SWING", "INTRADAY"}:
        return None

    cell = _SEGMENT_WIN_RATE.get((market_key, scan_key, decision_key))
    if not cell:
        return None
    horizon_data = cell.get(int(horizon_days)) or cell.get(5) or cell.get(7)
    if not horizon_data:
        return None
    n, win_pct = horizon_data
    if n < _MIN_SAMPLE_SIZE:
        return None
    return float(win_pct)


def lookup_segment_avg_return(
    decision: str | None,
    market: str | None,
    scan_mode: str | None,
    horizon_days: int = 5,
    ticker: str | None = None,
) -> Optional[float]:
    """Placeholder for future avg_return lookup. Currently returns None;
    will be populated from horizon_full_diagnosis when card UI needs it."""
    return None
