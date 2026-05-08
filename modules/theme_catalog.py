from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from modules.kr_stock_theme_master import (
    get_stock_theme_record,
    load_kr_stock_theme_master,
    normalize_theme_name,
)
from modules.theme_data_pipeline import build_catalog_from_membership_payload, get_theme_membership_record


CATALOG_PATH = Path(__file__).resolve().parents[1] / "models" / "theme_catalog_kr.json"

THEME_CANONICAL_MAP = {
    "semiconductor": "반도체",
    "secondary_battery": "2차전지",
    "bio": "바이오/헬스케어",
    "robotics": "로봇/자동화",
    "quantum": "양자",
    "ai_datacenter": "IT서비스/플랫폼",
    "oil_energy": "친환경/에너지",
    "power_grid": "친환경/에너지",
    "nuclear": "친환경/에너지",
    "shipbuilding": "조선/해양",
    "defense": "방산",
    "automobile": "자동차",
    "finance": "금융",
    "telecom": "통신/네트워크",
    "network": "통신/네트워크",
    "steel_materials": "철강/금속/소재",
    "construction_realestate": "건설/부동산",
    "consumer_retail": "소비재/유통",
    "game_content_ent": "게임/콘텐츠/엔터",
    "crypto": "가상자산/블록체인",
}

THEME_ID_MAP = {
    "2차전지": "secondary_battery",
    "반도체": "semiconductor",
    "바이오/헬스케어": "bio",
    "자동차": "automobile",
    "통신/네트워크": "telecom",
    "로봇/자동화": "robotics",
    "양자": "quantum",
    "친환경/에너지": "eco_energy",
    "조선/해양": "shipbuilding",
    "철강/금속/소재": "steel_materials",
    "건설/부동산": "construction_realestate",
    "소비재/유통": "consumer_retail",
    "게임/콘텐츠/엔터": "game_content_ent",
    "금융": "finance",
    "IT서비스/플랫폼": "it_platform",
    "방산": "defense",
    "가상자산/블록체인": "crypto",
    "unclassified": "unclassified",
}

THEME_ALIAS_MAP = {
    "2차전지": ["2차전지", "이차전지", "배터리", "양극재", "음극재", "전해액", "분리막", "리튬"],
    "반도체": ["반도체", "메모리", "HBM", "낸드", "DRAM", "파운드리", "웨이퍼", "패키징"],
    "바이오/헬스케어": ["바이오", "헬스케어", "의약", "치료제", "백신", "진단", "제약", "의료", "ADC"],
    "자동차": ["자동차", "차량", "전기차", "모빌리티", "자율주행"],
    "통신/네트워크": ["통신", "네트워크", "5G", "6G", "안테나", "광통신"],
    "로봇/자동화": ["로봇", "자동화", "스마트팩토리", "협동로봇", "물류로봇"],
    "양자": ["양자", "양자컴퓨팅", "양자암호", "양자센서", "quantum"],
    "친환경/에너지": ["친환경", "에너지", "태양광", "풍력", "수소", "연료전지", "ESS", "원자력", "전력"],
    "조선/해양": ["조선", "선박", "해양", "LNG선"],
    "철강/금속/소재": ["철강", "금속", "구리", "알루미늄", "화학", "소재", "필름"],
    "건설/부동산": ["건설", "부동산", "레미콘", "시멘트", "모듈러"],
    "소비재/유통": ["화장품", "식품", "음료", "유통", "면세", "패션", "생활용품"],
    "게임/콘텐츠/엔터": ["게임", "콘텐츠", "엔터", "영화", "드라마", "음악", "광고", "웹툰"],
    "금융": ["금융", "은행", "보험", "증권", "캐피탈", "카드"],
    "IT서비스/플랫폼": ["IT서비스", "플랫폼", "소프트웨어", "SW", "클라우드", "AI", "인공지능", "보안", "핀테크", "결제"],
    "방산": ["방산", "미사일", "탄약", "군수", "무기"],
    "가상자산/블록체인": ["가상자산", "블록체인", "암호화폐", "비트코인", "토큰증권", "STO"],
}


@lru_cache(maxsize=1)
def _load_seed_catalog() -> Dict[str, Any]:
    if not CATALOG_PATH.exists():
        return {"version": "missing", "market": "KR", "themes": []}
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"version": "invalid", "market": "KR", "themes": []}
    except Exception:
        return {"version": "invalid", "market": "KR", "themes": []}


def _seed_theme_metadata() -> Dict[str, Dict[str, Any]]:
    payload = _load_seed_catalog()
    master = load_kr_stock_theme_master()
    records = master.get("records_by_ticker", {}) if isinstance(master, dict) else {}
    meta: Dict[str, Dict[str, Any]] = {}
    for theme in payload.get("themes", []) or []:
        if not isinstance(theme, dict):
            continue
        seed_id = str(theme.get("theme_id") or "").strip()
        seed_name = str(theme.get("theme_name") or seed_id).strip()
        canonical = normalize_theme_name(THEME_CANONICAL_MAP.get(seed_id, seed_name))
        info = meta.setdefault(
            canonical,
            {
                "aliases": set(),
                "driver_categories": set(),
                "news_keywords": set(),
                "disclosure_keywords": set(),
                "seed_theme_ids": set(),
                "ticker_memberships": {},
            },
        )
        info["aliases"].update([canonical, seed_name])
        info["aliases"].update(str(x or "").strip() for x in theme.get("aliases", []) or [] if str(x or "").strip())
        info["driver_categories"].update(str(x or "").strip() for x in theme.get("driver_categories", []) or [] if str(x or "").strip())
        info["news_keywords"].update(str(x or "").strip() for x in theme.get("news_keywords", []) or [] if str(x or "").strip())
        info["disclosure_keywords"].update(str(x or "").strip() for x in theme.get("disclosure_keywords", []) or [] if str(x or "").strip())
        if seed_id:
            info["seed_theme_ids"].add(seed_id)
        memberships = theme.get("ticker_memberships", {})
        if isinstance(memberships, dict):
            for ticker, score in memberships.items():
                ticker_key = str(ticker).upper()
                master_row = records.get(ticker_key, {}) if isinstance(records, dict) else {}
                master_primary = normalize_theme_name(master_row.get("primary_theme"))
                master_secondary = [normalize_theme_name(x) for x in (master_row.get("secondary_themes", []) or [])]
                if master_primary != "unclassified" and canonical not in {master_primary, *master_secondary}:
                    continue
                try:
                    info["ticker_memberships"][ticker_key] = max(
                        float(score), float(info["ticker_memberships"].get(ticker_key, 0.0) or 0.0)
                    )
                except Exception:
                    continue
    return meta


def _default_metadata(canonical: str) -> Dict[str, Any]:
    aliases = list(dict.fromkeys([canonical] + THEME_ALIAS_MAP.get(canonical, [])))
    return {
        "aliases": aliases,
        "driver_categories": [],
        "news_keywords": aliases[:],
        "disclosure_keywords": [],
        "seed_theme_ids": [],
        "ticker_memberships": {},
    }


def _merge_theme_metadata(canonical: str, seed_meta: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    base = _default_metadata(canonical)
    extra = seed_meta.get(canonical, {})
    aliases = list(dict.fromkeys(base["aliases"] + sorted(extra.get("aliases", []))))
    news_keywords = list(dict.fromkeys(base["news_keywords"] + sorted(extra.get("news_keywords", []))))
    disclosure_keywords = list(dict.fromkeys(base["disclosure_keywords"] + sorted(extra.get("disclosure_keywords", []))))
    driver_categories = sorted(extra.get("driver_categories", []))
    seed_theme_ids = sorted(extra.get("seed_theme_ids", []))
    ticker_memberships = dict(extra.get("ticker_memberships", {}))
    return {
        "aliases": aliases,
        "driver_categories": driver_categories,
        "news_keywords": news_keywords,
        "disclosure_keywords": disclosure_keywords,
        "seed_theme_ids": seed_theme_ids,
        "ticker_memberships": ticker_memberships,
    }


@lru_cache(maxsize=2)
def load_theme_catalog(market: str = "KR") -> Dict[str, Any]:
    market_key = str(market or "KR").upper()
    artifact_catalog = build_catalog_from_membership_payload(market_key)
    if artifact_catalog.get("themes"):
        return artifact_catalog
    if market_key not in {"KR", "KOSPI", "KOSDAQ"}:
        return {"version": "empty", "market": market_key, "themes": []}

    master = load_kr_stock_theme_master()
    records_by_ticker = master.get("records_by_ticker", {}) if isinstance(master, dict) else {}
    seed_meta = _seed_theme_metadata()

    theme_rows: Dict[str, Dict[str, Any]] = {}
    for record in records_by_ticker.values():
        if not isinstance(record, dict):
            continue
        record_market = str(record.get("market") or "").upper()
        if market_key != "KR" and record_market != market_key:
            continue
        ticker = str(record.get("ticker") or "").upper()
        if not ticker:
            continue

        primary = normalize_theme_name(record.get("primary_theme"))
        secondary = [normalize_theme_name(row) for row in record.get("secondary_themes", []) or []]

        memberships: List[tuple[str, float]] = []
        if primary and primary != "unclassified":
            memberships.append((primary, 0.90))
        for theme_name in secondary:
            if theme_name and theme_name != "unclassified":
                memberships.append((theme_name, 0.70))

        for canonical, score in memberships:
            row = theme_rows.setdefault(
                canonical,
                {
                    "theme_id": THEME_ID_MAP.get(canonical, canonical.lower().replace("/", "_").replace(" ", "_")),
                    "theme_name": canonical,
                    "aliases": [],
                    "driver_categories": [],
                    "news_keywords": [],
                    "disclosure_keywords": [],
                    "ticker_memberships": {},
                    "seed_theme_ids": [],
                    "source": "stock_master",
                },
            )
            previous = float(row["ticker_memberships"].get(ticker, 0.0) or 0.0)
            row["ticker_memberships"][ticker] = round(max(previous, float(score)), 3)

    for canonical, row in theme_rows.items():
        merged = _merge_theme_metadata(canonical, seed_meta)
        row["aliases"] = merged["aliases"]
        row["driver_categories"] = merged["driver_categories"]
        row["news_keywords"] = merged["news_keywords"]
        row["disclosure_keywords"] = merged["disclosure_keywords"]
        row["seed_theme_ids"] = merged["seed_theme_ids"]
        for ticker, score in merged["ticker_memberships"].items():
            if ticker not in row["ticker_memberships"]:
                row["ticker_memberships"][ticker] = score

    for canonical, merged in seed_meta.items():
        if canonical in theme_rows:
            continue
        theme_rows[canonical] = {
            "theme_id": THEME_ID_MAP.get(canonical, canonical.lower().replace("/", "_").replace(" ", "_")),
            "theme_name": canonical,
            "aliases": merged["aliases"],
            "driver_categories": sorted(merged["driver_categories"]),
            "news_keywords": sorted(merged["news_keywords"]),
            "disclosure_keywords": sorted(merged["disclosure_keywords"]),
            "ticker_memberships": merged["ticker_memberships"],
            "seed_theme_ids": sorted(merged["seed_theme_ids"]),
            "source": "seed_catalog",
        }

    themes = sorted(theme_rows.values(), key=lambda row: (len(row.get("ticker_memberships", {})), row.get("theme_name", "")), reverse=True)
    return {
        "version": f"stock-master::{master.get('version', 'missing')}::{_load_seed_catalog().get('version', 'seed')}",
        "market": market_key,
        "themes": themes,
        "source_path": master.get("source_path", ""),
        "master_stats": {
            "market_counts": master.get("market_counts", {}),
            "theme_counts": master.get("theme_counts", {}),
            "unclassified_count": master.get("unclassified_count", 0),
            "spac_count": master.get("spac_count", 0),
        },
    }


def _theme_name(theme: Dict[str, Any]) -> str:
    return normalize_theme_name(theme.get("theme_name") or theme.get("theme_id") or "")


def resolve_theme_memberships(
    ticker: str,
    stock_name: str,
    market: str = "KR",
    extra_texts: List[str] | None = None,
) -> List[Dict[str, Any]]:
    market_key = str(market or "KR").upper()
    catalog = load_theme_catalog(market)
    themes = catalog.get("themes", []) if isinstance(catalog, dict) else []
    ticker_key = str(ticker or "").upper().strip()
    stock_name_lower = str(stock_name or "").strip().lower()
    texts = [stock_name_lower]
    for item in extra_texts or []:
        text = str(item or "").strip().lower()
        if text:
            texts.append(text)
    joined = " ".join(texts)

    best: Dict[str, Dict[str, Any]] = {}

    artifact_record = get_theme_membership_record(ticker_key, market_key)
    if artifact_record:
        artifact_memberships: List[Dict[str, Any]] = []
        official = artifact_record.get("official_classification", {}) if isinstance(artifact_record.get("official_classification"), dict) else {}
        for row in artifact_record.get("memberships", []) or []:
            if not isinstance(row, dict):
                continue
            artifact_memberships.append(
                {
                    "theme_id": str(row.get("theme_id") or "").strip() or THEME_ID_MAP.get(str(row.get("theme_name") or "").strip(), "unclassified"),
                    "theme_name": normalize_theme_name(row.get("theme_name")),
                    "confidence": round(float(row.get("confidence", 0.0) or 0.0), 3),
                    "reasons": list(row.get("reasons", []) or [])[:8],
                    "driver_categories": list(row.get("driver_categories", []) or []),
                    "theme_source": str(row.get("theme_source") or "theme_membership"),
                    "theme_inference_status": str(row.get("theme_inference_status") or "artifact"),
                    "secondary_themes": list(artifact_record.get("secondary_themes", []) or []),
                    "is_spac": False,
                    "official_sector": str(official.get("official_sector") or "").strip(),
                    "official_industry": str(official.get("official_industry") or "").strip(),
                    "official_products": str(official.get("official_products") or "").strip(),
                    "classification_source": str(official.get("classification_source") or "").strip(),
                }
            )
        artifact_memberships = [row for row in artifact_memberships if row.get("theme_name") and row.get("theme_name") != "unclassified"]
        if artifact_memberships:
            return artifact_memberships

    if market_key in {"KR", "KOSPI", "KOSDAQ"}:
        record = get_stock_theme_record(ticker_key)
        if record:
            primary = normalize_theme_name(record.get("primary_theme"))
            secondary = [normalize_theme_name(row) for row in record.get("secondary_themes", []) or []]
            inference_status = str(record.get("theme_inference_status") or "blank")
            common_payload = {
                "theme_inference_status": inference_status,
                "secondary_themes": secondary,
                "is_spac": bool(record.get("is_spac", False)),
            }
            if primary == "unclassified":
                best["unclassified"] = {
                    "theme_id": THEME_ID_MAP.get("unclassified", "unclassified"),
                    "theme_name": "unclassified",
                    "confidence": 0.0,
                    "reasons": ["stock_master_blank"],
                    "driver_categories": [],
                    "theme_source": "stock_master",
                    **common_payload,
                }
            else:
                best[primary] = {
                    "theme_id": THEME_ID_MAP.get(primary, primary.lower().replace("/", "_").replace(" ", "_")),
                    "theme_name": primary,
                    "confidence": 0.90,
                    "reasons": ["stock_master_primary"],
                    "driver_categories": [],
                    "theme_source": "stock_master",
                    **common_payload,
                }
                for theme_name in secondary:
                    if theme_name == "unclassified":
                        continue
                    best.setdefault(
                        theme_name,
                        {
                            "theme_id": THEME_ID_MAP.get(theme_name, theme_name.lower().replace("/", "_").replace(" ", "_")),
                            "theme_name": theme_name,
                            "confidence": 0.70,
                            "reasons": ["stock_master_secondary"],
                            "driver_categories": [],
                            "theme_source": "stock_master",
                            **common_payload,
                        },
                    )

    if "unclassified" not in best:
        for theme in themes:
            if not isinstance(theme, dict):
                continue
            confidence = 0.0
            reasons: List[str] = []
            theme_name = _theme_name(theme)
            theme_id = str(theme.get("theme_id") or "").strip()

            ticker_memberships = theme.get("ticker_memberships", {})
            if isinstance(ticker_memberships, dict) and ticker_key in ticker_memberships:
                try:
                    confidence = max(confidence, float(ticker_memberships[ticker_key]))
                    reasons.append("seed_ticker_mapping")
                except Exception:
                    pass

            for alias in theme.get("aliases", []) or []:
                alias_text = str(alias or "").strip().lower()
                if alias_text and alias_text in joined:
                    confidence = max(confidence, 0.72)
                    reasons.append(f"alias:{alias}")

            for keyword in theme.get("news_keywords", []) or []:
                kw_text = str(keyword or "").strip().lower()
                if kw_text and kw_text in joined:
                    confidence = max(confidence, 0.64)
                    reasons.append(f"keyword:{keyword}")

            if confidence <= 0.0:
                continue

            existing = best.get(theme_name)
            if existing and float(existing.get("confidence", 0.0) or 0.0) >= confidence:
                existing["reasons"] = sorted(set(existing.get("reasons", []) + reasons))[:6]
                continue

            best[theme_name] = {
                "theme_id": theme_id or THEME_ID_MAP.get(theme_name, theme_name.lower().replace("/", "_").replace(" ", "_")),
                "theme_name": theme_name,
                "confidence": round(min(0.99, max(0.0, confidence)), 3),
                "reasons": sorted(set(reasons))[:6],
                "driver_categories": list(theme.get("driver_categories", []) or []),
                "theme_source": "seed_catalog" if "seed_ticker_mapping" in reasons else "keyword_fallback",
                "theme_inference_status": "fallback",
                "secondary_themes": [],
                "is_spac": False,
            }

    source_priority = {"stock_master": 3, "seed_catalog": 2, "keyword_fallback": 1}
    memberships = list(best.values())
    memberships.sort(
        key=lambda row: (
            int(source_priority.get(str(row.get("theme_source") or ""), 0)),
            float(row.get("confidence", 0.0)),
            row.get("theme_name", ""),
        ),
        reverse=True,
    )
    return memberships


def primary_theme(memberships: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not memberships:
        return {}
    first = memberships[0]
    return first if isinstance(first, dict) else {}


def build_stock_master_validation_report(market: str = "KR") -> Dict[str, Any]:
    master = load_kr_stock_theme_master()
    seed = _load_seed_catalog()
    records = master.get("records_by_ticker", {}) if isinstance(master, dict) else {}
    seed_themes = seed.get("themes", []) if isinstance(seed, dict) else []
    conflict_rows: List[Dict[str, Any]] = []
    seed_by_ticker: Dict[str, str] = {}
    for theme in seed_themes:
        if not isinstance(theme, dict):
            continue
        canonical = normalize_theme_name(THEME_CANONICAL_MAP.get(str(theme.get("theme_id") or "").strip(), theme.get("theme_name")))
        memberships = theme.get("ticker_memberships", {})
        if not isinstance(memberships, dict):
            continue
        for ticker in memberships:
            ticker_key = str(ticker or "").upper().strip()
            if ticker_key and ticker_key not in seed_by_ticker:
                seed_by_ticker[ticker_key] = canonical

    selected_market = str(market or "KR").upper()
    primary_counter: defaultdict[str, int] = defaultdict(int)
    market_counts: defaultdict[str, int] = defaultdict(int)
    inference_status_counts: defaultdict[str, int] = defaultdict(int)
    spac_excluded = 0
    unclassified = 0
    for ticker, record in records.items():
        if not isinstance(record, dict):
            continue
        record_market = str(record.get("market") or "").upper()
        if selected_market != "KR" and record_market != selected_market:
            continue
        market_counts[record_market] += 1
        primary = str(record.get("primary_theme") or "unclassified")
        inference_status = str(record.get("theme_inference_status") or "blank")
        primary_counter[primary] += 1
        inference_status_counts[inference_status] += 1
        if primary == "unclassified":
            unclassified += 1
        if bool(record.get("is_spac", False)):
            spac_excluded += 1
        seed_theme = seed_by_ticker.get(ticker, "")
        if seed_theme and primary != "unclassified" and seed_theme != primary:
            conflict_rows.append(
                {
                    "ticker": ticker,
                    "stock_name": str(record.get("stock_name") or ""),
                    "master_primary_theme": primary,
                    "seed_theme": seed_theme,
                }
            )

    return {
        "market": selected_market,
        "source_path": master.get("source_path", ""),
        "records_loaded": sum(market_counts.values()) if selected_market == "KR" else market_counts.get(selected_market, 0),
        "market_counts": dict(market_counts),
        "primary_theme_distribution": dict(sorted(primary_counter.items(), key=lambda item: item[1], reverse=True)),
        "inference_status_distribution": dict(sorted(inference_status_counts.items(), key=lambda item: item[1], reverse=True)),
        "rule_inferred_count": int(inference_status_counts.get("rule_inferred", 0)),
        "unclassified_count": unclassified,
        "spac_excluded_count": spac_excluded,
        "seed_conflict_count": len(conflict_rows),
        "seed_conflict_examples": conflict_rows[:20],
    }
