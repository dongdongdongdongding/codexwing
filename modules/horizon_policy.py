"""Explicit label horizon policy for scanner and Phase25 model artifacts."""

from __future__ import annotations

from typing import Dict, Tuple


HORIZON_POLICY: Dict[Tuple[str, str], Dict[str, object]] = {
    ("KOSPI", "SWING"): {
        "horizon_days": 5,
        "return_col": "return_5d_pct",
        "reason": "2026-05-08 (swing-main-4lm): horizon 진단에서 KOSPI SWING은 5d hold "
                  "에서 자연 분포가 가장 강하다 (PRIORITY win_5d 80.6% / OBSERVE win_7d "
                  "75.6% / EXCEPTION_LEADER avg_5d 8.67%). 학습 OOS auc 0.485(랜덤 미만)는 "
                  "3d target이 노이즈로 학습 가능 신호를 못 만들기 때문. 5d로 변경하면 "
                  "운영 실제 분포(70-90% win)와 학습 target이 일치.",
    },
    ("KOSDAQ", "SWING"): {
        "horizon_days": 5,
        "return_col": "return_5d_pct",
        "reason": "KOSDAQ SWING surge signals materialize better at 5d than 3d.",
    },
    ("KOSPI", "INTRADAY"): {
        "horizon_days": 1,
        "return_col": "return_1d_pct",
        "reason": "Intraday candidates use next-session realized outcome.",
    },
    ("KOSDAQ", "INTRADAY"): {
        "horizon_days": 1,
        "return_col": "return_1d_pct",
        "reason": "Intraday candidates use next-session realized outcome.",
    },
}


def resolve_horizon_policy(market: str, scan_mode: str) -> Dict[str, object]:
    market_key = str(market or "").upper()
    mode_key = str(scan_mode or "SWING").upper()
    policy = HORIZON_POLICY.get((market_key, mode_key))
    if policy:
        return dict(policy)
    if mode_key == "INTRADAY":
        return {
            "horizon_days": 1,
            "return_col": "return_1d_pct",
            "reason": "Default intraday horizon.",
        }
    return {
        "horizon_days": 3,
        "return_col": "return_3d_pct",
        "reason": "Default swing horizon.",
    }


def horizon_days_from_return_col(return_col: str) -> int:
    value = str(return_col or "")
    if "return_5d" in value:
        return 5
    if "return_3d" in value:
        return 3
    if "return_1d" in value:
        return 1
    return 3
