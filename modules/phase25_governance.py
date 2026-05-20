from __future__ import annotations

import math
from typing import Any, List


OOS_VALIDATE_MIN_AUC = 0.55
OOS_VALIDATE_MIN_WIN_RATE_PCT = 70.0
OOS_VALIDATE_MIN_AVG_RETURN_PCT = 5.0

WEAK_OOS_MIN_AUC = 0.50
WEAK_OOS_MIN_WIN_RATE_PCT = 60.0
WEAK_OOS_MIN_AVG_RETURN_PCT = 0.0


def phase25_oos_validates(
    *,
    oos_auc: Any,
    oos_win_rate_pct: Any,
    oos_avg_return_pct: Any,
) -> bool:
    auc = _float_or_none(oos_auc)
    win = _float_or_none(oos_win_rate_pct)
    avg = _float_or_none(oos_avg_return_pct)
    return (
        auc is not None
        and auc >= OOS_VALIDATE_MIN_AUC
        and win is not None
        and win >= OOS_VALIDATE_MIN_WIN_RATE_PCT
        and avg is not None
        and avg >= OOS_VALIDATE_MIN_AVG_RETURN_PCT
    )


def phase25_weak_oos_reasons(
    *,
    oos_auc: Any,
    oos_win_rate_pct: Any,
    oos_avg_return_pct: Any,
) -> List[str]:
    reasons: List[str] = []
    auc = _float_or_none(oos_auc)
    win = _float_or_none(oos_win_rate_pct)
    avg = _float_or_none(oos_avg_return_pct)
    if auc is not None and auc < WEAK_OOS_MIN_AUC:
        reasons.append(f"oos_auc={auc:.3f}<{WEAK_OOS_MIN_AUC:.2f}")
    if win is not None and win < WEAK_OOS_MIN_WIN_RATE_PCT:
        reasons.append(f"oos_win={win:.1f}%<{WEAK_OOS_MIN_WIN_RATE_PCT:.1f}%")
    if avg is not None and avg < WEAK_OOS_MIN_AVG_RETURN_PCT:
        reasons.append(f"oos_avg={avg:.2f}%<{WEAK_OOS_MIN_AVG_RETURN_PCT:.1f}%")
    return reasons


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


__all__ = [
    "OOS_VALIDATE_MIN_AUC",
    "OOS_VALIDATE_MIN_AVG_RETURN_PCT",
    "OOS_VALIDATE_MIN_WIN_RATE_PCT",
    "WEAK_OOS_MIN_AUC",
    "WEAK_OOS_MIN_AVG_RETURN_PCT",
    "WEAK_OOS_MIN_WIN_RATE_PCT",
    "phase25_oos_validates",
    "phase25_weak_oos_reasons",
]
