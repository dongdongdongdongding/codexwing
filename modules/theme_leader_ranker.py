from __future__ import annotations

from typing import Any, Dict, List


def _safe_last(series: Any, default: float = 0.0) -> float:
    try:
        if series is None or len(series) == 0:
            return float(default)
        return float(series.iloc[-1])
    except Exception:
        return float(default)


def compute_theme_leader_metrics(
    *,
    df: Any,
    current_price: float,
    volume_ratio: float,
    decision_score: float,
    primary_theme: str,
    scan_mode: str,
) -> Dict[str, Any]:
    high = getattr(df, "__getitem__", lambda *_: None)("High") if df is not None is not False else None
    low = getattr(df, "__getitem__", lambda *_: None)("Low") if df is not None is not False else None
    close = getattr(df, "__getitem__", lambda *_: None)("Close") if df is not None is not False else None
    volume = getattr(df, "__getitem__", lambda *_: None)("Volume") if df is not None is not False else None

    current_turnover = max(0.0, current_price * _safe_last(volume, 0.0))
    avg_turnover_20 = 0.0
    try:
        avg_turnover_20 = float(((close * volume).rolling(20, min_periods=5).mean()).iloc[-1])
    except Exception:
        avg_turnover_20 = current_turnover
    turnover_growth_5d = 1.0
    try:
        recent = (close * volume).tail(5).mean()
        base = (close * volume).tail(20).mean()
        if float(base or 0.0) > 0:
            turnover_growth_5d = float(recent) / float(base)
    except Exception:
        pass

    high_20 = _safe_last(high.rolling(20, min_periods=5).max(), current_price) if hasattr(high, "rolling") else current_price
    low_20 = _safe_last(low.rolling(20, min_periods=5).min(), current_price) if hasattr(low, "rolling") else current_price
    breakout_quality = 50.0
    if high_20 > 0:
        breakout_quality += min(25.0, max(-10.0, ((current_price / high_20) - 0.985) * 150.0))
    close_location = 50.0
    if high_20 > low_20:
        close_location = max(0.0, min(100.0, ((current_price - low_20) / (high_20 - low_20)) * 100.0))
    expansion_potential = max(0.0, min(100.0, 35.0 + volume_ratio * 12.0 + turnover_growth_5d * 8.0))
    leader_score = max(
        0.0,
        min(
            100.0,
            0.28 * min(100.0, current_turnover / 100_000_000.0)
            + 0.20 * min(100.0, volume_ratio * 25.0)
            + 0.20 * breakout_quality
            + 0.18 * close_location
            + 0.14 * expansion_potential
            + 0.12 * float(decision_score),
        ),
    )
    return {
        "theme_name": primary_theme,
        "theme_rank": None,
        "turnover_rank_in_theme": None,
        "turnover_ratio_vs_float_cap": round(min(1.0, current_turnover / max(avg_turnover_20, 1.0)), 4),
        "turnover_growth_5d": round(float(turnover_growth_5d), 3),
        "breakout_quality_score": round(float(breakout_quality), 1),
        "close_location_score": round(float(close_location), 1),
        "expansion_potential_score": round(float(expansion_potential), 1),
        "leader_score": round(float(leader_score), 1),
        "scan_mode": str(scan_mode or "SWING").upper(),
    }


def assign_theme_ranks(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for candidate in candidates:
        theme_context = candidate.get("theme_context", {}) if isinstance(candidate.get("theme_context"), dict) else {}
        primary_theme = str(theme_context.get("primary_theme") or "").strip()
        if not primary_theme:
            continue
        grouped.setdefault(primary_theme, []).append(candidate)

    for _, rows in grouped.items():
        rows.sort(key=lambda row: float((row.get("leader_metrics") or {}).get("leader_score", 0.0) or 0.0), reverse=True)
        turnover_sorted = sorted(
            rows,
            key=lambda row: float((row.get("leader_metrics") or {}).get("turnover_ratio_vs_float_cap", 0.0) or 0.0),
            reverse=True,
        )
        turnover_index = {id(row): idx for idx, row in enumerate(turnover_sorted, start=1)}
        for idx, row in enumerate(rows, start=1):
            leader_metrics = row.get("leader_metrics", {}) if isinstance(row.get("leader_metrics"), dict) else {}
            leader_metrics["theme_rank"] = idx
            leader_metrics["turnover_rank_in_theme"] = int(turnover_index.get(id(row), idx))
            row["leader_metrics"] = leader_metrics
    return candidates
