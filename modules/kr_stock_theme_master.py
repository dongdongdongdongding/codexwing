from __future__ import annotations

import json
import os
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


DEFAULT_MASTER_PATH = Path("/Users/dongdong/Downloads/kospi_kosdaq_allstocks_structured.jsonl")
DEFAULT_THEME_RULES_PATH = Path("/Users/dongdong/Downloads/kospi_kosdaq_allstocks_structured.xlsx")
LOCAL_MASTER_PATH = Path(__file__).resolve().parents[1] / "models" / "kr_stock_theme_master.jsonl"

CANONICAL_THEME_MAP = {
    "2차전지": "2차전지",
    "이차전지": "2차전지",
    "반도체": "반도체",
    "바이오": "바이오/헬스케어",
    "헬스케어": "바이오/헬스케어",
    "바이오/헬스케어": "바이오/헬스케어",
    "자동차": "자동차",
    "통신": "통신/네트워크",
    "통신/네트워크": "통신/네트워크",
    "네트워크": "통신/네트워크",
    "로봇": "로봇/자동화",
    "로봇/자동화": "로봇/자동화",
    "친환경/에너지": "친환경/에너지",
    "에너지": "친환경/에너지",
    "원전": "친환경/에너지",
    "전력": "친환경/에너지",
    "수소": "친환경/에너지",
    "태양광": "친환경/에너지",
    "풍력": "친환경/에너지",
    "조선": "조선/해양",
    "조선/해양": "조선/해양",
    "해양": "조선/해양",
    "철강": "철강/금속/소재",
    "금속": "철강/금속/소재",
    "소재": "철강/금속/소재",
    "철강/금속/소재": "철강/금속/소재",
    "건설": "건설/부동산",
    "부동산": "건설/부동산",
    "건설/부동산": "건설/부동산",
    "소비재": "소비재/유통",
    "유통": "소비재/유통",
    "소비재/유통": "소비재/유통",
    "게임": "게임/콘텐츠/엔터",
    "콘텐츠": "게임/콘텐츠/엔터",
    "엔터": "게임/콘텐츠/엔터",
    "게임/콘텐츠/엔터": "게임/콘텐츠/엔터",
    "금융": "금융",
    "방산": "방산",
    "defense": "방산",
    "it서비스/플랫폼": "IT서비스/플랫폼",
    "it 서비스/플랫폼": "IT서비스/플랫폼",
    "플랫폼": "IT서비스/플랫폼",
    "ai": "IT서비스/플랫폼",
    "ai/데이터센터": "IT서비스/플랫폼",
    "데이터센터": "IT서비스/플랫폼",
    "클라우드": "IT서비스/플랫폼",
    "핀테크": "IT서비스/플랫폼",
}

THEME_RULES_FALLBACK = {
    "2차전지": ["2차전지", "이차전지", "전고체", "양극재", "음극재", "전해액", "분리막", "배터리", "리튬", "니켈", "코발트"],
    "반도체": ["반도체", "메모리", "HBM", "낸드", "DRAM", "파운드리", "웨이퍼", "패키징"],
    "바이오/헬스케어": ["의약", "치료제", "백신", "진단", "제약", "바이오", "의료", "헬스", "임플란트", "미용기기", "adc", "항체", "면역항암", "신약", "의료기기"],
    "자동차": ["자동차", "차량", "전기차", "모빌리티", "타이어", "자율주행"],
    "통신/네트워크": ["통신", "네트워크", "5G", "6G", "안테나", "광통신"],
    "로봇/자동화": ["로봇", "자동화", "스마트팩토리", "공작기계", "3d 프린터", "레이저"],
    "친환경/에너지": ["태양광", "풍력", "수소", "연료전지", "ESS", "원자력", "전력", "에너지", "탄소", "폐기물", "전선", "케이블"],
    "조선/해양": ["조선", "선박", "해양", "열교환기"],
    "철강/금속/소재": ["철강", "금속", "구리", "알루미늄", "화학소재", "화학", "소재", "필름", "유리", "와이어"],
    "건설/부동산": ["건설", "부동산", "레미콘", "시멘트", "모듈러"],
    "소비재/유통": ["화장품", "식품", "음료", "유통", "면세", "패션", "생활용품", "의복", "어묵", "백화점", "리조트", "카지노"],
    "게임/콘텐츠/엔터": ["게임", "콘텐츠", "엔터", "영화", "드라마", "음악", "광고", "웹툰"],
    "금융": ["금융", "은행", "보험", "증권", "캐피탈", "카드", "신탁"],
    "IT서비스/플랫폼": ["소프트웨어", "SW", "클라우드", "플랫폼", "AI", "인공지능", "보안", "핀테크", "결제", "데이터", "시스템 통합"],
    "방산": ["방산", "미사일", "탄약", "군수", "무기", "방탄", "총포탄", "전투", "유도탄"],
}

FIELD_WEIGHTS = {
    "stock_name": 0.5,
    "sector": 0.8,
    "official_sector": 0.8,
    "industry": 1.3,
    "products": 1.6,
}


def _candidate_paths() -> List[Path]:
    env_path = str(os.getenv("AG_KR_STOCK_THEME_MASTER_PATH") or "").strip()
    paths: List[Path] = []
    if env_path:
        paths.append(Path(env_path).expanduser())
    paths.extend([LOCAL_MASTER_PATH, DEFAULT_MASTER_PATH])
    deduped: List[Path] = []
    seen = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def resolve_master_path() -> Path | None:
    for path in _candidate_paths():
        if path.exists():
            return path
    return None


def normalize_theme_name(name: Any) -> str:
    raw = str(name or "").strip()
    if not raw:
        return "unclassified"
    lower = raw.lower()
    if lower in CANONICAL_THEME_MAP:
        return CANONICAL_THEME_MAP[lower]
    if raw in CANONICAL_THEME_MAP:
        return CANONICAL_THEME_MAP[raw]
    return raw


@lru_cache(maxsize=1)
def _load_theme_rules() -> Dict[str, List[str]]:
    rules: Dict[str, List[str]] = {normalize_theme_name(k): list(v) for k, v in THEME_RULES_FALLBACK.items()}
    if DEFAULT_THEME_RULES_PATH.exists():
        try:
            df = pd.read_excel(DEFAULT_THEME_RULES_PATH, sheet_name="theme_rules")
            for row in df.to_dict(orient="records"):
                theme = normalize_theme_name(row.get("theme"))
                text = str(row.get("keyword_rules") or "").strip()
                if not theme or theme == "unclassified" or not text:
                    continue
                keywords = [item.strip() for item in text.split(",") if item.strip()]
                merged = list(dict.fromkeys([*(rules.get(theme, [])), *keywords]))
                rules[theme] = merged
        except Exception:
            pass
    normalized: Dict[str, List[str]] = {}
    for theme, keywords in rules.items():
        deduped: List[str] = []
        for keyword in keywords:
            k = str(keyword or "").strip()
            if not k:
                continue
            if k not in deduped:
                deduped.append(k)
        normalized[theme] = deduped
    return normalized


def _parse_secondary_themes(value: Any) -> List[str]:
    if isinstance(value, list):
        rows = value
    else:
        text = str(value or "").strip()
        if not text or text in {"[]", "nan", "None"}:
            rows = []
        else:
            try:
                parsed = json.loads(text)
                rows = parsed if isinstance(parsed, list) else [text]
            except Exception:
                rows = [item.strip() for item in text.split(",") if item.strip()]
    normalized: List[str] = []
    for row in rows:
        theme = normalize_theme_name(row)
        if theme and theme != "unclassified" and theme not in normalized:
            normalized.append(theme)
    return normalized


def is_spac_record(stock_name: Any, industry: Any, products: Any = None) -> bool:
    joined = " ".join(
        [
            str(stock_name or "").strip(),
            str(industry or "").strip(),
            str(products or "").strip(),
        ]
    ).lower()
    return "스팩" in joined or "기업 인수" in joined or "기업인수" in joined or "합병 목적" in joined


def _infer_themes_from_text(raw: Dict[str, Any]) -> Dict[str, Any]:
    rules = _load_theme_rules()
    scores: Dict[str, float] = {}
    matched: Dict[str, List[str]] = {}
    for field, weight in FIELD_WEIGHTS.items():
        text = str(raw.get(field) or "").strip()
        if not text:
            continue
        lowered = text.lower()
        for theme, keywords in rules.items():
            for keyword in keywords:
                kw = str(keyword or "").strip()
                if not kw:
                    continue
                kw_lower = kw.lower()
                if kw_lower not in lowered:
                    continue
                bonus = 0.0
                if len(kw) >= 4 or any(ch.isdigit() for ch in kw):
                    bonus += 0.2
                if field in {"industry", "products"}:
                    bonus += 0.1
                scores[theme] = scores.get(theme, 0.0) + weight + bonus
                matched.setdefault(theme, [])
                if kw not in matched[theme]:
                    matched[theme].append(kw)

    if not scores:
        return {"primary_theme": "unclassified", "secondary_themes": [], "theme_inference_status": "blank"}

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_theme, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    top_matches = matched.get(top_theme, [])

    strong_enough = top_score >= 1.7 and (top_score >= second_score + 0.6 or len(top_matches) >= 2)
    if not strong_enough:
        return {"primary_theme": "unclassified", "secondary_themes": [], "theme_inference_status": "blank"}

    secondary: List[str] = []
    for theme, score in ranked[1:]:
        if len(secondary) >= 2:
            break
        if score < 1.4:
            continue
        if top_score - score > 1.2:
            continue
        if theme == top_theme:
            continue
        secondary.append(theme)

    return {
        "primary_theme": top_theme,
        "secondary_themes": secondary,
        "theme_inference_status": "rule_inferred",
    }


def _normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    ticker = str(raw.get("ticker") or "").strip().upper()
    primary_theme_raw = str(raw.get("primary_theme") or "").strip()
    inference_status = str(raw.get("theme_inference_status") or "").strip().lower() or "blank"
    primary_theme = normalize_theme_name(primary_theme_raw)
    if not primary_theme_raw or inference_status == "blank":
        primary_theme = "unclassified"

    secondary_themes = _parse_secondary_themes(raw.get("secondary_themes"))
    normalized_raw = {
        "stock_name": str(raw.get("stock_name") or "").strip(),
        "sector": str(raw.get("sector") or "").strip(),
        "industry": str(raw.get("industry") or "").strip(),
        "official_sector": str(raw.get("official_sector") or "").strip(),
        "products": str(raw.get("products") or "").strip(),
    }

    if primary_theme == "unclassified":
        inferred = _infer_themes_from_text(normalized_raw)
        primary_theme = str(inferred.get("primary_theme") or "unclassified")
        secondary_themes = list(inferred.get("secondary_themes") or [])
        inference_status = str(inferred.get("theme_inference_status") or "blank")

    record = {
        "ticker": ticker,
        "stock_name": normalized_raw["stock_name"],
        "market": str(raw.get("market") or "").strip().upper(),
        "sector": normalized_raw["sector"],
        "industry": normalized_raw["industry"],
        "official_sector": normalized_raw["official_sector"],
        "products": normalized_raw["products"],
        "listing_date": str(raw.get("listing_date") or "").strip(),
        "region": str(raw.get("region") or "").strip(),
        "primary_theme": primary_theme,
        "secondary_themes": secondary_themes,
        "theme_inference_status": "blank" if primary_theme == "unclassified" else inference_status,
        "source_official": str(raw.get("source_official") or "").strip(),
        "source_theme_reference": str(raw.get("source_theme_reference") or "").strip(),
    }
    record["is_spac"] = is_spac_record(record["stock_name"], record["industry"], record["products"])
    return record


@lru_cache(maxsize=1)
def load_kr_stock_theme_master() -> Dict[str, Any]:
    path = resolve_master_path()
    if path is None:
        return {
            "version": "missing",
            "source_path": "",
            "records_by_ticker": {},
            "market_counts": {},
            "theme_counts": {},
            "unclassified_count": 0,
            "spac_count": 0,
        }

    records_by_ticker: Dict[str, Dict[str, Any]] = {}
    market_counts: Counter[str] = Counter()
    theme_counts: Counter[str] = Counter()
    spac_count = 0

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = str(line or "").strip()
            if not text:
                continue
            raw = json.loads(text)
            if not isinstance(raw, dict):
                continue
            record = _normalize_record(raw)
            ticker = record["ticker"]
            if not ticker:
                continue
            records_by_ticker[ticker] = record
            market_counts[record["market"] or "UNKNOWN"] += 1
            theme_counts[record["primary_theme"]] += 1
            if record["is_spac"]:
                spac_count += 1

    return {
        "version": f"kr-stock-theme-master::{path.stat().st_mtime_ns}",
        "source_path": str(path),
        "records_by_ticker": records_by_ticker,
        "market_counts": dict(market_counts),
        "theme_counts": dict(theme_counts),
        "unclassified_count": int(theme_counts.get("unclassified", 0)),
        "spac_count": int(spac_count),
    }


def get_stock_theme_record(ticker: str) -> Dict[str, Any]:
    master = load_kr_stock_theme_master()
    records = master.get("records_by_ticker", {})
    if not isinstance(records, dict):
        return {}
    return records.get(str(ticker or "").strip().upper(), {}) or {}
