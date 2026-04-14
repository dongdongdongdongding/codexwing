"""
KR Theme Momentum Fetcher

Scrapes Naver Finance theme group page to get real-time avg_change_pct per theme.
Writes momentum data into the theme_cache (KR.json) so the quant reranker can
apply momentum-weighted adjustments.

Strategy:
  - Fetch 263 Naver themes with avg_change_pct
  - Aggregate into swing-main's canonical theme groups via THEME_ALIAS_MAP
  - Write aggregated momentum into KR.json (creating/updating theme_states entries)
  - theme_states from news intel are preserved; momentum-only entries are added/updated

Classification:
  EXPLODING   : avg_change >= +2.0%
  ACCELERATING: avg_change >= +0.5%
  STEADY      : -0.5% < avg_change < +0.5%
  FADING      : avg_change <= -0.5%
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

# Canonical theme groups: theme_name -> list of Naver theme name fragments to match
# If a Naver theme name contains any of the fragments, it belongs to this group.
_CANONICAL_THEME_GROUPS: Dict[str, List[str]] = {
    "반도체": ["반도체", "HBM", "낸드", "DRAM", "파운드리", "웨이퍼", "패키징", "CXL", "SOCAMM", "뉴로모픽", "시스템반도체", "전력반도체", "SiC"],
    "2차전지": ["2차전지", "이차전지", "배터리", "양극재", "음극재", "전해액", "분리막", "리튬", "전고체", "나트륨"],
    "바이오/헬스케어": ["바이오", "헬스케어", "의약", "치료제", "백신", "진단", "제약", "의료", "ADC", "항체", "CMO", "CRO", "임플란트", "유전자", "mRNA"],
    "자동차": ["자동차", "전기차", "모빌리티", "자율주행", "ADAS", "차량"],
    "통신/네트워크": ["광통신", "통신장비", "5G", "6G", "NI(네트워크", "안테나", "위성통신", "해저케이블"],
    "로봇/자동화": ["로봇", "자동화", "스마트팩토리", "협동로봇", "물류로봇", "드론", "무인"],
    "친환경/에너지": ["태양광", "풍력", "수소", "연료전지", "ESS", "원자력", "전력", "SMR", "SOFC", "탄소"],
    "조선/해양": ["조선", "선박", "해양", "LNG선", "VLCC", "해운"],
    "방산": ["방산", "미사일", "탄약", "군수", "무기", "방위", "K2", "K9"],
    "AI/소프트웨어": ["AI", "인공지능", "온디바이스", "딥러닝", "LLM", "GPT", "생성AI", "뉴로모픽", "퓨리오사"],
    "양자컴퓨팅": ["양자암호", "양자컴퓨팅", "양자통신"],
    "게임/콘텐츠/엔터": ["게임", "콘텐츠", "엔터", "영화", "드라마", "음악", "웹툰", "K-pop", "메타버스"],
    "금융": ["금융", "은행", "보험", "증권", "캐피탈", "카드", "핀테크", "스테이블코인", "코인", "디지털화폐"],
    "철강/금속/소재": ["철강", "금속", "구리", "알루미늄", "화학", "소재", "희토류", "마그네슘", "텅스텐", "비철"],
    "건설/부동산": ["건설", "부동산", "레미콘", "시멘트", "모듈러", "주택"],
    "소비재/유통": ["화장품", "식품", "음료", "유통", "면세", "패션", "생활용품", "여행", "항공", "카지노"],
    "바이오시밀러": ["바이오시밀러"],
    "우주/항공": ["스페이스", "우주", "위성", "SpaceX", "발사체", "항공우주"],
    "보안": ["보안주(정보)", "사이버보안", "정보보안"],
    "해운": ["해운", "벌크", "컨테이너", "탱커"],
}


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
    Returns dict: naver_theme_name -> avg_change_pct (float).
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
        clean = re.sub(r"[^\d.\-+]", "", raw_chg)
        try:
            pct = float(clean)
        except (ValueError, TypeError):
            continue
        result[name] = round(pct, 2)

    return result


def aggregate_by_canonical(naver_data: Dict[str, float]) -> Dict[str, Tuple[float, int]]:
    """
    Aggregates raw Naver theme prices into canonical theme groups.
    Returns: canonical_name -> (avg_pct, num_matched_themes)
    """
    buckets: Dict[str, List[float]] = {k: [] for k in _CANONICAL_THEME_GROUPS}
    for naver_name, pct in naver_data.items():
        naver_lower = naver_name.lower()
        for canonical, fragments in _CANONICAL_THEME_GROUPS.items():
            for frag in fragments:
                if frag.lower() in naver_lower:
                    buckets[canonical].append(pct)
                    break
    result: Dict[str, Tuple[float, int]] = {}
    for canonical, values in buckets.items():
        if values:
            avg = round(sum(values) / len(values), 2)
            result[canonical] = (avg, len(values))
    return result


def fetch_and_write_theme_momentum() -> Dict[str, Any]:
    """
    Fetches Naver theme momentum, aggregates into canonical groups,
    and writes into KR.json theme_cache (merged with existing theme_states).
    """
    naver_data = fetch_naver_theme_momentum()
    if not naver_data:
        return {"fetched": 0, "matched": 0, "updated_at": None, "error": "fetch_failed"}

    aggregated = aggregate_by_canonical(naver_data)
    if not aggregated:
        return {"fetched": len(naver_data), "matched": 0, "updated_at": None, "error": "aggregate_empty"}

    # Load existing cache
    existing_cache: Dict[str, Any] = {}
    if _CACHE_PATH.exists():
        try:
            existing_cache = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Build lookup of existing theme_states by theme_name
    states: List[Dict[str, Any]] = list(existing_cache.get("theme_states") or [])
    state_by_name: Dict[str, Dict[str, Any]] = {}
    for s in states:
        name = str(s.get("theme_name") or "").strip()
        if name:
            state_by_name[name] = s

    now = datetime.now(timezone.utc).isoformat()
    matched = 0

    for canonical, (avg_pct, count) in aggregated.items():
        matched += 1
        mc = _momentum_class(avg_pct)
        if canonical in state_by_name:
            # Update existing state's momentum fields
            state_by_name[canonical]["momentum_avg_change_pct"] = avg_pct
            state_by_name[canonical]["momentum_class"] = mc
            state_by_name[canonical]["momentum_naver_count"] = count
        else:
            # Create a momentum-only placeholder (direction=NEUTRAL, no news evidence)
            new_entry: Dict[str, Any] = {
                "theme_id": canonical,
                "theme_name": canonical,
                "direction": "NEUTRAL",
                "strength_score": 0.0,
                "confidence": 0.0,
                "driver_categories": [],
                "evidence": [],
                "beneficiary_keywords": [],
                "victim_keywords": [],
                "momentum_avg_change_pct": avg_pct,
                "momentum_class": mc,
                "momentum_naver_count": count,
                "updated_at": now,
            }
            states.append(new_entry)
            state_by_name[canonical] = new_entry

    existing_cache["theme_states"] = states
    existing_cache["theme_momentum_updated_at"] = now

    try:
        _CACHE_PATH.write_text(json.dumps(existing_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return {"fetched": len(naver_data), "matched": matched, "updated_at": now, "error": str(e)}

    return {"fetched": len(naver_data), "matched": matched, "updated_at": now}


if __name__ == "__main__":
    result = fetch_and_write_theme_momentum()
    print(json.dumps(result, ensure_ascii=False))
