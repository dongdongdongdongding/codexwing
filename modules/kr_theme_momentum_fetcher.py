"""
KR Theme Momentum Fetcher

Scrapes Naver Finance theme group page to get real-time avg_change_pct per theme.
Writes momentum data into the theme_cache (KR.json) so the quant reranker can
apply momentum-weighted adjustments.

Classification (from FDR ThemeMomentum convention):
  EXPLODING   : avg_change >= +2.0%
  ACCELERATING: avg_change >= +0.5%
  STEADY      : -0.5% < avg_change < +0.5%
  FADING      : avg_change <= -0.5%

Usage:
    from modules.kr_theme_momentum_fetcher import fetch_and_write_theme_momentum
    result = fetch_and_write_theme_momentum()
    # result = {"fetched": 120, "matched": 8, "updated_at": "..."}
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

_NAVER_URL = "https://finance.naver.com/sise/sise_group.naver?type=theme"
_CACHE_PATH = Path("runtime_state") / "long_term" / "theme_cache" / "KR.json"
_TIMEOUT = 10
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SwingScanner/1.0)"}


def _momentum_class(pct: float) -> str:
    if pct >= 2.0:
        return "EXPLODING"
    if pct >= 0.5:
        return "ACCELERATING"
    if pct <= -0.5:
        return "FADING"
    return "STEADY"


def fetch_naver_theme_momentum() -> Dict[str, float]:
    """
    Fetches Naver Finance theme avg_change_pct for all themes.
    Returns dict: theme_name_kr -> avg_change_pct (float).
    Returns empty dict on network/parse failure.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {}

    try:
        r = requests.get(_NAVER_URL, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
    except Exception:
        return {}

    try:
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return {}

    result: Dict[str, float] = {}
    rows = soup.select("table.type_1 tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        name = str(cols[0].get_text(strip=True) or "").strip()
        raw_chg = str(cols[1].get_text(strip=True) or "").strip()
        if not name or not raw_chg:
            continue
        # Strip %, spaces, handle +/- signs
        clean = re.sub(r"[^\d.\-+]", "", raw_chg)
        try:
            pct = float(clean)
        except (ValueError, TypeError):
            continue
        result[name] = round(pct, 2)

    return result


def _build_match_keys(theme: Dict[str, Any]) -> List[str]:
    """Returns all strings to try when matching a theme_cache entry to Naver names."""
    keys: List[str] = []
    theme_name = str(theme.get("theme_name") or "").strip()
    theme_id = str(theme.get("theme_id") or "").strip()
    aliases = [str(a or "").strip() for a in (theme.get("beneficiary_keywords") or theme.get("victim_keywords") or []) if str(a or "").strip()]
    if theme_name:
        keys.append(theme_name)
    if theme_id and theme_id != theme_name:
        keys.append(theme_id)
    keys.extend(aliases[:4])
    return keys


def _match_theme_momentum(
    theme: Dict[str, Any],
    naver_lookup: Dict[str, float],
) -> Optional[float]:
    """
    Fuzzy-match a theme_cache entry to the Naver theme name.
    Returns avg_change_pct if a match is found, None otherwise.
    """
    for key in _build_match_keys(theme):
        # Exact match
        if key in naver_lookup:
            return naver_lookup[key]
        # Partial: any Naver theme that contains this key
        key_lower = key.lower()
        for naver_name, pct in naver_lookup.items():
            if key_lower and key_lower in naver_name.lower():
                return pct
    return None


def fetch_and_write_theme_momentum() -> Dict[str, Any]:
    """
    Fetches Naver theme momentum and writes avg_change_pct / momentum_class
    back into KR.json theme_cache.

    Returns summary: {"fetched": int, "matched": int, "updated_at": str}
    """
    naver_data = fetch_naver_theme_momentum()
    if not naver_data:
        return {"fetched": 0, "matched": 0, "updated_at": None, "error": "fetch_failed"}

    if not _CACHE_PATH.exists():
        return {"fetched": len(naver_data), "matched": 0, "updated_at": None, "error": "cache_not_found"}

    try:
        cache = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"fetched": len(naver_data), "matched": 0, "updated_at": None, "error": "cache_read_error"}

    states: List[Dict[str, Any]] = cache.get("theme_states", []) if isinstance(cache, dict) else []
    matched = 0
    for theme in states:
        if not isinstance(theme, dict):
            continue
        pct = _match_theme_momentum(theme, naver_data)
        if pct is not None:
            theme["momentum_avg_change_pct"] = pct
            theme["momentum_class"] = _momentum_class(pct)
            matched += 1
        else:
            theme["momentum_avg_change_pct"] = None
            theme["momentum_class"] = None

    now = datetime.now(timezone.utc).isoformat()
    cache["theme_momentum_updated_at"] = now

    try:
        _CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return {"fetched": len(naver_data), "matched": matched, "updated_at": now, "error": str(e)}

    return {"fetched": len(naver_data), "matched": matched, "updated_at": now}


if __name__ == "__main__":
    result = fetch_and_write_theme_momentum()
    print(json.dumps(result, ensure_ascii=False))
