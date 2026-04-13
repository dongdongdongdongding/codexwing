"""
Theme momentum loader for quant reranker.

Reads theme_cache to extract momentum_avg_change_pct per theme.
The field is set to None by default in theme_signal_engine.py and can be
populated by an external process (e.g. FDR Naver theme rankings) before
the reranker runs. When not populated, the momentum block in the reranker
is a no-op.

Momentum class thresholds (from FDR ThemeMomentum convention):
  EXPLODING   : avg_change >= 2.0%
  ACCELERATING: avg_change >= 0.5%
  STEADY      : -0.5% < avg_change < 0.5%
  FADING      : avg_change <= -0.5%
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


_CACHE_DIR = Path("runtime_state") / "long_term" / "theme_cache"


def _momentum_class(avg_change_pct: float) -> str:
    if avg_change_pct >= 2.0:
        return "EXPLODING"
    if avg_change_pct >= 0.5:
        return "ACCELERATING"
    if avg_change_pct <= -0.5:
        return "FADING"
    return "STEADY"


def load_theme_momentum_lookup(market: str) -> Dict[str, Tuple[Optional[float], str]]:
    """
    Returns dict keyed by theme_id and theme_name (both), mapping to
    (avg_change_pct, momentum_class).

    Returns empty dict when cache file missing or has no momentum data.
    """
    market_key = str(market or "").upper()
    # KR.json serves both KOSPI and KOSDAQ
    if market_key in {"KOSPI", "KOSDAQ"}:
        path = _CACHE_DIR / "KR.json"
    else:
        path = _CACHE_DIR / f"{market_key}.json"

    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    states = data.get("theme_states", []) if isinstance(data, dict) else []
    lookup: Dict[str, Tuple[Optional[float], str]] = {}
    for row in states:
        if not isinstance(row, dict):
            continue
        raw_pct = row.get("momentum_avg_change_pct")
        if raw_pct is None:
            continue
        try:
            pct = float(raw_pct)
        except Exception:
            continue
        mc = str(row.get("momentum_class") or _momentum_class(pct))
        theme_id = str(row.get("theme_id") or "").strip()
        theme_name = str(row.get("theme_name") or "").strip()
        entry = (pct, mc)
        if theme_id:
            lookup[theme_id] = entry
        if theme_name and theme_name != theme_id:
            lookup[theme_name] = entry
    return lookup


def get_theme_momentum(
    lookup: Dict[str, Tuple[Optional[float], str]],
    primary_theme: Optional[str],
) -> Tuple[Optional[float], str]:
    """
    Looks up momentum for a candidate's primary_theme.
    Returns (avg_change_pct, momentum_class) or (None, "UNKNOWN") if not found.
    """
    if not primary_theme or not lookup:
        return (None, "UNKNOWN")
    key = str(primary_theme).strip()
    if key in lookup:
        return lookup[key]
    key_lower = key.lower()
    for k, v in lookup.items():
        if k.lower() == key_lower:
            return v
    return (None, "UNKNOWN")
