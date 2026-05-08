from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from modules.kr_stock_theme_master import get_stock_theme_record, normalize_theme_name
from modules.live_scan_context import normalize_market_key

try:
    import FinanceDataReader as fdr
except Exception:  # pragma: no cover - import failure is surfaced through builder warnings
    fdr = None


THEME_ID_MAP = {
    "2차전지": "secondary_battery",
    "반도체": "semiconductor",
    "바이오/헬스케어": "bio",
    "자동차": "automobile",
    "통신/네트워크": "telecom",
    "로봇/자동화": "robotics",
    "친환경/에너지": "eco_energy",
    "조선/해양": "shipbuilding",
    "철강/금속/소재": "steel_materials",
    "건설/부동산": "construction_realestate",
    "소비재/유통": "consumer_retail",
    "게임/콘텐츠/엔터": "game_content_ent",
    "금융": "finance",
    "IT서비스/플랫폼": "it_platform",
    "방산": "defense",
    "unclassified": "unclassified",
}

THEME_ALIAS_FALLBACK = {
    "2차전지": ["2차전지", "이차전지", "배터리", "양극재", "음극재", "전해액", "분리막", "리튬", "battery", "lithium", "cathode"],
    "반도체": ["반도체", "메모리", "HBM", "낸드", "DRAM", "파운드리", "웨이퍼", "패키징", "semiconductor", "chip", "memory", "foundry"],
    "바이오/헬스케어": ["바이오", "헬스케어", "의약", "치료제", "백신", "진단", "제약", "의료", "biotech", "pharma", "therapeutics", "medical"],
    "자동차": ["자동차", "차량", "전기차", "모빌리티", "자율주행", "automobile", "vehicle", "ev", "mobility", "autonomous"],
    "통신/네트워크": ["통신", "네트워크", "5G", "6G", "안테나", "광통신", "telecom", "network", "wireless", "broadband"],
    "로봇/자동화": ["로봇", "자동화", "스마트팩토리", "협동로봇", "robot", "automation", "factory automation"],
    "친환경/에너지": ["친환경", "에너지", "태양광", "풍력", "수소", "연료전지", "ESS", "원자력", "전력", "clean energy", "solar", "wind", "hydrogen", "nuclear", "power grid"],
    "조선/해양": ["조선", "선박", "해양", "LNG선", "shipbuilding", "marine", "offshore", "lng carrier"],
    "철강/금속/소재": ["철강", "금속", "구리", "알루미늄", "화학", "소재", "steel", "metal", "materials", "copper", "aluminum"],
    "건설/부동산": ["건설", "부동산", "레미콘", "시멘트", "건자재", "construction", "real estate", "cement", "building products"],
    "소비재/유통": ["화장품", "식품", "음료", "유통", "면세", "패션", "consumer", "retail", "cosmetics", "beverage", "food"],
    "게임/콘텐츠/엔터": ["게임", "콘텐츠", "엔터", "영화", "드라마", "웹툰", "game", "gaming", "content", "entertainment", "media"],
    "금융": ["금융", "은행", "보험", "증권", "캐피탈", "카드", "financial", "bank", "insurance", "brokerage", "capital markets"],
    "IT서비스/플랫폼": ["IT서비스", "플랫폼", "소프트웨어", "SW", "클라우드", "AI", "인공지능", "보안", "핀테크", "software", "platform", "cloud", "security", "fintech", "data center"],
    "방산": ["방산", "미사일", "탄약", "군수", "무기", "defense", "aerospace", "missile", "munition", "weapons"],
}

FIELD_WEIGHTS = {
    "name": 0.15,
    "official_sector": 0.18,
    "official_industry": 0.42,
    "official_products": 0.62,
}

RUNTIME_ROOT = Path("runtime_state")
INSTRUMENT_MASTER_DIR = RUNTIME_ROOT / "long_term" / "instrument_master"
THEME_MEMBERSHIP_DIR = RUNTIME_ROOT / "long_term" / "theme_membership"
VALIDATION_DIR = RUNTIME_ROOT / "reports" / "theme_validation"
SEED_CATALOG_PATH = Path("models") / "theme_catalog_kr.json"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _safe_date(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            return _safe_text(value)
    return _safe_text(value)


def _theme_id(theme_name: str) -> str:
    canonical = normalize_theme_name(theme_name)
    return THEME_ID_MAP.get(canonical, canonical.lower().replace("/", "_").replace(" ", "_"))


def _kr_symbol(code: str, market_scope: str) -> str:
    scope = str(market_scope or "").upper()
    suffix = ".KS" if scope == "KOSPI" else ".KQ" if scope == "KOSDAQ" else ""
    return f"{code}{suffix}" if code and suffix else code


def _load_seed_catalog() -> Dict[str, Any]:
    if not SEED_CATALOG_PATH.exists():
        return {}
    try:
        payload = json.loads(SEED_CATALOG_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _theme_taxonomy() -> Dict[str, Dict[str, Any]]:
    taxonomy: Dict[str, Dict[str, Any]] = {}
    payload = _load_seed_catalog()
    for row in payload.get("themes", []) or []:
        if not isinstance(row, dict):
            continue
        canonical = normalize_theme_name(row.get("theme_name") or row.get("theme_id") or "")
        if not canonical or canonical == "unclassified":
            continue
        aliases = [
            _safe_text(item)
            for item in [canonical, *(row.get("aliases", []) or []), *(THEME_ALIAS_FALLBACK.get(canonical, []) or [])]
            if _safe_text(item)
        ]
        taxonomy[canonical] = {
            "theme_id": _theme_id(canonical),
            "theme_name": canonical,
            "aliases": list(dict.fromkeys(aliases)),
            "news_keywords": list(dict.fromkeys([_safe_text(x) for x in (row.get("news_keywords", []) or []) if _safe_text(x)] + THEME_ALIAS_FALLBACK.get(canonical, []))),
            "disclosure_keywords": list(dict.fromkeys([_safe_text(x) for x in (row.get("disclosure_keywords", []) or []) if _safe_text(x)])),
            "driver_categories": list(dict.fromkeys([_safe_text(x) for x in (row.get("driver_categories", []) or []) if _safe_text(x)])),
            "ticker_memberships": dict(row.get("ticker_memberships", {}) or {}),
        }
    for canonical, aliases in THEME_ALIAS_FALLBACK.items():
        taxonomy.setdefault(
            canonical,
            {
                "theme_id": _theme_id(canonical),
                "theme_name": canonical,
                "aliases": list(dict.fromkeys([canonical, *aliases])),
                "news_keywords": list(dict.fromkeys(aliases)),
                "disclosure_keywords": [],
                "driver_categories": [],
                "ticker_memberships": {},
            },
        )
    return taxonomy


def _fetch_listing(name: str) -> pd.DataFrame:
    if fdr is None:
        raise RuntimeError("FinanceDataReader is not available")
    return fdr.StockListing(name)


def _extract_day_return_pct(raw: Dict[str, Any]) -> float | None:
    candidates = [
        raw.get("ChagesRatio"),
        raw.get("ChangesRatio"),
        raw.get("ChangeRate"),
        raw.get("change_rate"),
    ]
    for value in candidates:
        try:
            if value is None or pd.isna(value):
                continue
            return float(value)
        except Exception:
            continue
    close_val = raw.get("Close")
    prev_close = raw.get("PrevClose")
    try:
        if close_val is not None and prev_close not in (None, 0) and not pd.isna(close_val) and not pd.isna(prev_close):
            return (float(close_val) / float(prev_close) - 1.0) * 100.0
    except Exception:
        pass
    return None


def build_market_day_return_map(market: str) -> Dict[str, float]:
    market_input = str(market or "KR").upper()
    canonical_market = normalize_market_key(market_input)
    return_map: Dict[str, float] = {}
    if fdr is None:
        return return_map
    listing_names: List[str]
    if market_input in {"KOSPI", "KOSDAQ", "KONEX"}:
        listing_names = [market_input]
    elif canonical_market == "KR":
        listing_names = ["KRX"]
    else:
        return return_map

    for listing_name in listing_names:
        try:
            frame = _fetch_listing(listing_name)
        except Exception:
            continue
        for raw in frame.to_dict(orient="records"):
            code = _safe_text(raw.get("Code"))
            if not code:
                continue
            scope = _safe_text(raw.get("Market")).upper()
            symbol = _kr_symbol(code, scope)
            day_return = _extract_day_return_pct(raw)
            if symbol and day_return is not None:
                return_map[symbol] = round(float(day_return), 4)
    return return_map


def _normalize_kr_record(raw: Dict[str, Any], source_listing: str) -> Dict[str, Any]:
    code = _safe_text(raw.get("Code"))
    market_scope = _safe_text(raw.get("Market")).upper()
    return {
        "symbol": _kr_symbol(code, market_scope),
        "local_symbol": code,
        "name": _safe_text(raw.get("Name")),
        "country": "KR",
        "market": "KR",
        "market_scope": market_scope or "KRX",
        "exchange": "KRX",
        "instrument_type": "equity",
        "official_sector": _safe_text(raw.get("Sector")),
        "official_industry": _safe_text(raw.get("Industry")),
        "official_products": _safe_text(raw.get("Products")),
        "industry_code": "",
        "region": _safe_text(raw.get("Region")),
        "listing_date": _safe_date(raw.get("ListingDate")),
        "company_homepage": _safe_text(raw.get("HomePage")),
        "classification_source": "FDR_KRX_DESC",
        "source_listings": [source_listing],
        "generated_at": _utcnow(),
    }


def _normalize_us_record(raw: Dict[str, Any], source_listing: str) -> Dict[str, Any]:
    symbol = _safe_text(raw.get("Symbol")).upper()
    official_sector = _safe_text(raw.get("Sector"))
    return {
        "symbol": symbol,
        "local_symbol": symbol,
        "name": _safe_text(raw.get("Name")),
        "country": "US",
        "market": "US",
        "market_scope": source_listing,
        "exchange": source_listing,
        "instrument_type": "equity",
        "official_sector": official_sector,
        "official_industry": _safe_text(raw.get("Industry")),
        "official_products": "",
        "industry_code": _safe_text(raw.get("IndustryCode")),
        "region": "",
        "listing_date": "",
        "company_homepage": "",
        "classification_source": "FDR_US_LISTING",
        "source_listings": [source_listing],
        "generated_at": _utcnow(),
    }


def build_instrument_master_payload(
    market: str,
    *,
    listing_frames: Dict[str, pd.DataFrame] | None = None,
) -> Dict[str, Any]:
    market_key = normalize_market_key(market)
    generated_at = _utcnow()
    warnings: List[str] = []

    if market_key == "KR":
        frames = listing_frames or {"KRX-DESC": _fetch_listing("KRX-DESC")}
        records = []
        for source_listing, frame in frames.items():
            for raw in frame.to_dict(orient="records"):
                record = _normalize_kr_record(raw, source_listing)
                if record["symbol"]:
                    records.append(record)
        records.sort(key=lambda row: (row["market_scope"], row["symbol"]))
        sector_coverage = sum(1 for row in records if row.get("official_sector"))
        if sector_coverage / max(len(records), 1) < 0.5:
            warnings.append("KRX-DESC sector coverage is sparse; industry/products should be treated as the stronger official basis.")
    else:
        frames = listing_frames or {
            "NASDAQ": _fetch_listing("NASDAQ"),
            "NYSE": _fetch_listing("NYSE"),
            "AMEX": _fetch_listing("AMEX"),
            "S&P500": _fetch_listing("S&P500"),
        }
        merged: Dict[str, Dict[str, Any]] = {}
        for source_listing in ("NASDAQ", "NYSE", "AMEX"):
            frame = frames.get(source_listing)
            if frame is None:
                continue
            for raw in frame.to_dict(orient="records"):
                record = _normalize_us_record(raw, source_listing)
                if not record["symbol"]:
                    continue
                merged[record["symbol"]] = record
        sp500 = frames.get("S&P500")
        if sp500 is not None:
            for raw in sp500.to_dict(orient="records"):
                symbol = _safe_text(raw.get("Symbol")).upper()
                if not symbol:
                    continue
                base = merged.setdefault(symbol, _normalize_us_record(raw, "S&P500"))
                sector = _safe_text(raw.get("Sector"))
                industry = _safe_text(raw.get("Industry"))
                if sector:
                    base["official_sector"] = sector
                if industry:
                    base["official_industry"] = industry
                if "S&P500" not in base["source_listings"]:
                    base["source_listings"].append("S&P500")
        records = sorted(merged.values(), key=lambda row: row["symbol"])
        sector_coverage = sum(1 for row in records if row.get("official_sector"))
        if sector_coverage / max(len(records), 1) < 0.25:
            warnings.append("US exchange listings are missing official sector for most symbols; only the S&P500 overlay supplies sector reliably.")

    return {
        "version": f"instrument-master::{market_key}::{generated_at[:10]}",
        "market": market_key,
        "generated_at": generated_at,
        "record_count": len(records),
        "records": records,
        "source_provider": "FinanceDataReader",
        "warnings": warnings,
        "coverage": {
            "official_sector": sum(1 for row in records if row.get("official_sector")),
            "official_industry": sum(1 for row in records if row.get("official_industry")),
            "official_products": sum(1 for row in records if row.get("official_products")),
        },
        "market_scope_counts": dict(Counter(str(row.get("market_scope") or "") for row in records)),
    }


def instrument_master_path(market: str) -> Path:
    market_key = normalize_market_key(market)
    path = INSTRUMENT_MASTER_DIR / f"{market_key}.json"
    _ensure_parent(path)
    return path


def write_instrument_master_payload(payload: Dict[str, Any]) -> Path:
    path = instrument_master_path(payload.get("market", "KR"))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_instrument_master_payload(market: str) -> Dict[str, Any]:
    path = instrument_master_path(market)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _best_match_specificity(keyword: str, field_name: str) -> float:
    bonus = 0.0
    if len(keyword) >= 4 or any(char.isdigit() for char in keyword):
        bonus += 0.12
    if field_name in {"official_industry", "official_products"}:
        bonus += 0.08
    return bonus


def _iter_tokens(theme_row: Dict[str, Any]) -> Iterable[str]:
    seen = set()
    for field_name in ("aliases", "news_keywords"):
        for token in theme_row.get(field_name, []) or []:
            text = _safe_text(token)
            lower = text.lower()
            if not lower or lower in seen:
                continue
            seen.add(lower)
            yield text


def _infer_from_official_text(instrument: Dict[str, Any], taxonomy: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    field_texts = {
        "name": _safe_text(instrument.get("name")).lower(),
        "official_sector": _safe_text(instrument.get("official_sector")).lower(),
        "official_industry": _safe_text(instrument.get("official_industry")).lower(),
        "official_products": _safe_text(instrument.get("official_products")).lower(),
    }
    matches: List[Dict[str, Any]] = []
    for theme_name, theme_row in taxonomy.items():
        score = 0.0
        evidence: List[str] = []
        fields_hit = set()
        for token in _iter_tokens(theme_row):
            token_lower = token.lower()
            if len(token_lower) < 2:
                continue
            for field_name, text in field_texts.items():
                if not text or token_lower not in text:
                    continue
                score += FIELD_WEIGHTS[field_name] + _best_match_specificity(token, field_name)
                evidence.append(f"{field_name}:{token}")
                fields_hit.add(field_name)
                break
        if score < 0.92 and not ("official_products" in fields_hit and score >= 0.72):
            continue
        confidence = min(0.79, 0.38 + (score * 0.22) + (0.06 if len(fields_hit) >= 2 else 0.0))
        matches.append(
            {
                "theme_id": theme_row["theme_id"],
                "theme_name": theme_name,
                "confidence": round(confidence, 3),
                "theme_source": "official_text_match",
                "theme_inference_status": "official_text_match",
                "reasons": sorted(dict.fromkeys(evidence))[:8],
                "evidence": sorted(dict.fromkeys(evidence))[:8],
                "driver_categories": list(theme_row.get("driver_categories", []) or []),
            }
        )
    matches.sort(key=lambda row: float(row.get("confidence", 0.0) or 0.0), reverse=True)
    return matches[:3]


def build_theme_membership_payload(
    market: str,
    *,
    instrument_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    market_key = normalize_market_key(market)
    generated_at = _utcnow()
    instrument_payload = instrument_payload or load_instrument_master_payload(market_key)
    records = instrument_payload.get("records", []) if isinstance(instrument_payload, dict) else []
    taxonomy = _theme_taxonomy()
    membership_records: List[Dict[str, Any]] = []
    primary_source_distribution: Counter[str] = Counter()
    warnings: List[str] = []

    for instrument in records:
        if not isinstance(instrument, dict):
            continue
        symbol = _safe_text(instrument.get("symbol")).upper()
        market_scope = _safe_text(instrument.get("market_scope")).upper()
        best: Dict[str, Dict[str, Any]] = {}
        source_priority = {"stock_master": 3, "seed_catalog": 2, "official_text_match": 1}

        def upsert(row: Dict[str, Any]) -> None:
            theme_name = normalize_theme_name(row.get("theme_name"))
            if not theme_name or theme_name == "unclassified":
                return
            confidence = round(float(row.get("confidence", 0.0) or 0.0), 3)
            existing = best.get(theme_name)
            payload = {
                "theme_id": _safe_text(row.get("theme_id")) or _theme_id(theme_name),
                "theme_name": theme_name,
                "confidence": confidence,
                "theme_source": _safe_text(row.get("theme_source")) or "unknown",
                "theme_inference_status": _safe_text(row.get("theme_inference_status")) or "unknown",
                "reasons": sorted(dict.fromkeys([_safe_text(item) for item in (row.get("reasons", []) or []) if _safe_text(item)]))[:8],
                "evidence": sorted(dict.fromkeys([_safe_text(item) for item in (row.get("evidence", []) or []) if _safe_text(item)]))[:8],
                "driver_categories": list(dict.fromkeys([_safe_text(item) for item in (row.get("driver_categories", []) or []) if _safe_text(item)])),
            }
            if existing and float(existing.get("confidence", 0.0) or 0.0) >= confidence:
                existing["reasons"] = sorted(dict.fromkeys(existing.get("reasons", []) + payload["reasons"]))[:8]
                existing["evidence"] = sorted(dict.fromkeys(existing.get("evidence", []) + payload["evidence"]))[:8]
                return
            if existing:
                existing_priority = source_priority.get(str(existing.get("theme_source") or ""), 0)
                incoming_priority = source_priority.get(payload["theme_source"], 0)
                if existing_priority > incoming_priority:
                    existing["reasons"] = sorted(dict.fromkeys(existing.get("reasons", []) + payload["reasons"]))[:8]
                    existing["evidence"] = sorted(dict.fromkeys(existing.get("evidence", []) + payload["evidence"]))[:8]
                    return
                if existing_priority == incoming_priority and float(existing.get("confidence", 0.0) or 0.0) >= confidence:
                    existing["reasons"] = sorted(dict.fromkeys(existing.get("reasons", []) + payload["reasons"]))[:8]
                    existing["evidence"] = sorted(dict.fromkeys(existing.get("evidence", []) + payload["evidence"]))[:8]
                    return
            best[theme_name] = payload

        if market_key == "KR":
            stock_record = get_stock_theme_record(symbol)
            if stock_record:
                inference_status = _safe_text(stock_record.get("theme_inference_status")) or "blank"
                primary_theme = normalize_theme_name(stock_record.get("primary_theme"))
                secondary_themes = [normalize_theme_name(item) for item in (stock_record.get("secondary_themes", []) or [])]
                if primary_theme != "unclassified":
                    upsert(
                        {
                            "theme_name": primary_theme,
                            "confidence": 0.96 if inference_status == "inferred" else 0.88,
                            "theme_source": "stock_master",
                            "theme_inference_status": inference_status,
                            "reasons": [f"stock_master:{inference_status}"],
                            "evidence": [f"stock_master_primary:{primary_theme}"],
                        }
                    )
                for secondary_theme in secondary_themes:
                    if secondary_theme == "unclassified":
                        continue
                    upsert(
                        {
                            "theme_name": secondary_theme,
                            "confidence": 0.82,
                            "theme_source": "stock_master",
                            "theme_inference_status": inference_status,
                            "reasons": ["stock_master:secondary"],
                            "evidence": [f"stock_master_secondary:{secondary_theme}"],
                        }
                    )

        for theme_name, theme_row in taxonomy.items():
            ticker_memberships = theme_row.get("ticker_memberships", {})
            if symbol in ticker_memberships:
                upsert(
                    {
                        "theme_id": theme_row["theme_id"],
                        "theme_name": theme_name,
                        "confidence": max(0.84, float(ticker_memberships[symbol])),
                        "theme_source": "seed_catalog",
                        "theme_inference_status": "seed_membership",
                        "reasons": ["seed_ticker_mapping"],
                        "evidence": [f"seed_ticker_mapping:{symbol}"],
                        "driver_categories": theme_row.get("driver_categories", []),
                    }
                )

        for inferred in _infer_from_official_text(instrument, taxonomy):
            upsert(inferred)

        memberships = list(best.values())
        memberships.sort(
            key=lambda row: (
                source_priority.get(str(row.get("theme_source") or ""), 0),
                float(row.get("confidence", 0.0) or 0.0),
                row.get("theme_name", ""),
            ),
            reverse=True,
        )
        primary_theme = memberships[0]["theme_name"] if memberships else "unclassified"
        primary_source = memberships[0]["theme_source"] if memberships else "unclassified"
        primary_source_distribution[primary_source] += 1
        membership_records.append(
            {
                "symbol": symbol,
                "market": market_key,
                "market_scope": market_scope,
                "name": _safe_text(instrument.get("name")),
                "primary_theme": primary_theme,
                "secondary_themes": [row["theme_name"] for row in memberships[1:3]],
                "memberships": memberships,
                "official_classification": {
                    "official_sector": _safe_text(instrument.get("official_sector")),
                    "official_industry": _safe_text(instrument.get("official_industry")),
                    "official_products": _safe_text(instrument.get("official_products")),
                    "industry_code": _safe_text(instrument.get("industry_code")),
                    "classification_source": _safe_text(instrument.get("classification_source")),
                },
                "generated_at": generated_at,
            }
        )

    if market_key == "US":
        high_conf = sum(1 for row in membership_records if row.get("primary_theme") != "unclassified" and any(float(m.get("confidence", 0.0) or 0.0) >= 0.7 for m in row.get("memberships", [])[:1]))
        if high_conf / max(len(membership_records), 1) < 0.15:
            warnings.append("US theme memberships are still mostly tentative because full-market sector coverage is weak outside the S&P500 overlay.")

    return {
        "version": f"theme-membership::{market_key}::{generated_at[:10]}",
        "market": market_key,
        "generated_at": generated_at,
        "record_count": len(membership_records),
        "records": membership_records,
        "primary_source_distribution": dict(primary_source_distribution),
        "warnings": warnings,
        "instrument_master_version": instrument_payload.get("version", ""),
    }


def theme_membership_path(market: str) -> Path:
    market_key = normalize_market_key(market)
    path = THEME_MEMBERSHIP_DIR / f"{market_key}.json"
    _ensure_parent(path)
    return path


def write_theme_membership_payload(payload: Dict[str, Any]) -> Path:
    path = theme_membership_path(payload.get("market", "KR"))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_theme_membership_payload(market: str) -> Dict[str, Any]:
    path = theme_membership_path(market)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def get_theme_membership_record(symbol: str, market: str) -> Dict[str, Any] | None:
    payload = load_theme_membership_payload(market)
    if not payload:
        return None
    symbol_key = _safe_text(symbol).upper()
    for row in payload.get("records", []) or []:
        if _safe_text(row.get("symbol")).upper() == symbol_key:
            return row
    return None


def build_catalog_from_membership_payload(market: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    market_input = str(market or "KR").upper()
    canonical_market = normalize_market_key(market_input)
    payload = payload or load_theme_membership_payload(canonical_market)
    if not payload:
        return {"version": "missing", "market": market_input, "themes": []}
    taxonomy = _theme_taxonomy()
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in payload.get("records", []) or []:
        if not isinstance(row, dict):
            continue
        if market_input in {"KOSPI", "KOSDAQ"} and _safe_text(row.get("market_scope")).upper() != market_input:
            continue
        symbol = _safe_text(row.get("symbol")).upper()
        for membership in row.get("memberships", []) or []:
            if not isinstance(membership, dict):
                continue
            theme_name = normalize_theme_name(membership.get("theme_name"))
            if not theme_name or theme_name == "unclassified":
                continue
            theme_tax = taxonomy.get(theme_name, {})
            block = grouped.setdefault(
                theme_name,
                {
                    "theme_id": _safe_text(membership.get("theme_id")) or _theme_id(theme_name),
                    "theme_name": theme_name,
                    "aliases": list(theme_tax.get("aliases", [theme_name])),
                    "driver_categories": list(theme_tax.get("driver_categories", [])),
                    "news_keywords": list(theme_tax.get("news_keywords", [])),
                    "disclosure_keywords": list(theme_tax.get("disclosure_keywords", [])),
                    "ticker_memberships": {},
                    "source": "theme_membership_artifact",
                },
            )
            block["ticker_memberships"][symbol] = round(float(membership.get("confidence", 0.0) or 0.0), 3)
    themes = sorted(grouped.values(), key=lambda row: (len(row.get("ticker_memberships", {})), row.get("theme_name", "")), reverse=True)
    return {
        "version": f"theme-catalog::{payload.get('version', 'missing')}",
        "market": market_input,
        "themes": themes,
        "source_path": str(theme_membership_path(canonical_market)),
        "master_stats": {
            "record_count": payload.get("record_count", 0),
            "primary_source_distribution": payload.get("primary_source_distribution", {}),
        },
    }


def build_theme_data_validation_report(
    market: str,
    *,
    instrument_payload: Dict[str, Any] | None = None,
    membership_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    market_key = normalize_market_key(market)
    instrument_payload = instrument_payload or load_instrument_master_payload(market_key)
    membership_payload = membership_payload or load_theme_membership_payload(market_key)
    instrument_records = instrument_payload.get("records", []) if isinstance(instrument_payload, dict) else []
    membership_records = membership_payload.get("records", []) if isinstance(membership_payload, dict) else []
    primary_theme_distribution = Counter(str(row.get("primary_theme") or "unclassified") for row in membership_records)
    high_conf_primary = sum(
        1
        for row in membership_records
        if row.get("primary_theme") != "unclassified"
        and any(float(m.get("confidence", 0.0) or 0.0) >= 0.8 for m in (row.get("memberships", []) or [])[:1])
    )
    official_sector_coverage = sum(1 for row in instrument_records if _safe_text(row.get("official_sector")))
    official_industry_coverage = sum(1 for row in instrument_records if _safe_text(row.get("official_industry")))
    official_products_coverage = sum(1 for row in instrument_records if _safe_text(row.get("official_products")))
    warnings = list(dict.fromkeys([*(instrument_payload.get("warnings", []) or []), *(membership_payload.get("warnings", []) or [])]))
    samples = []
    for row in membership_records[:10]:
        samples.append(
            {
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "primary_theme": row.get("primary_theme"),
                "top_membership": (row.get("memberships") or [{}])[0],
            }
        )
    return {
        "market": market_key,
        "generated_at": _utcnow(),
        "instrument_master_version": instrument_payload.get("version", ""),
        "theme_membership_version": membership_payload.get("version", ""),
        "instrument_record_count": len(instrument_records),
        "membership_record_count": len(membership_records),
        "official_coverage": {
            "official_sector": official_sector_coverage,
            "official_industry": official_industry_coverage,
            "official_products": official_products_coverage,
        },
        "primary_source_distribution": membership_payload.get("primary_source_distribution", {}),
        "primary_theme_distribution": dict(primary_theme_distribution.most_common(15)),
        "high_conf_primary_ratio": round(high_conf_primary / max(len(membership_records), 1), 4),
        "warnings": warnings,
        "samples": samples,
    }


def write_theme_data_validation_report(report: Dict[str, Any]) -> Dict[str, Path]:
    market_key = normalize_market_key(report.get("market", "KR"))
    json_path = VALIDATION_DIR / f"theme_data_pipeline_{market_key.lower()}.json"
    md_path = VALIDATION_DIR / f"theme_data_pipeline_{market_key.lower()}.md"
    _ensure_parent(json_path)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# Theme Data Pipeline ({market_key})",
        "",
        f"- instrument_master_version: {report.get('instrument_master_version', '')}",
        f"- theme_membership_version: {report.get('theme_membership_version', '')}",
        f"- instrument_record_count: {report.get('instrument_record_count', 0)}",
        f"- membership_record_count: {report.get('membership_record_count', 0)}",
        f"- official_coverage: {report.get('official_coverage', {})}",
        f"- primary_source_distribution: {report.get('primary_source_distribution', {})}",
        f"- high_conf_primary_ratio: {report.get('high_conf_primary_ratio', 0.0)}",
        "",
        "## Primary Theme Distribution",
    ]
    for theme_name, count in (report.get("primary_theme_distribution", {}) or {}).items():
        lines.append(f"- {theme_name}: {count}")
    if report.get("warnings"):
        lines.extend(["", "## Warnings"])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    if report.get("samples"):
        lines.extend(["", "## Sample Rows"])
        for row in report["samples"][:10]:
            top_membership = row.get("top_membership", {}) if isinstance(row.get("top_membership"), dict) else {}
            lines.append(
                f"- {row.get('symbol')} {row.get('name')}: {row.get('primary_theme')} | "
                f"source={top_membership.get('theme_source')} | confidence={top_membership.get('confidence')}"
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "md": md_path}


def build_theme_distribution_summary(
    market: str,
    *,
    membership_payload: Dict[str, Any] | None = None,
    intel_data: Dict[str, Any] | None = None,
    day_return_map: Dict[str, float] | None = None,
    top_n: int = 12,
) -> Dict[str, Any]:
    market_input = str(market or "KR").upper()
    canonical_market = normalize_market_key(market_input)
    membership_payload = membership_payload or load_theme_membership_payload(canonical_market)
    records = membership_payload.get("records", []) if isinstance(membership_payload, dict) else []
    theme_state_lookup: Dict[str, Dict[str, Any]] = {}
    if isinstance(intel_data, dict):
        for row in intel_data.get("theme_states", []) or []:
            if not isinstance(row, dict):
                continue
            theme_name = _safe_text(row.get("theme_name"))
            theme_id = _safe_text(row.get("theme_id"))
            if theme_name:
                theme_state_lookup[theme_name] = row
            if theme_id and theme_name and theme_id not in theme_state_lookup:
                theme_state_lookup[theme_id] = row

    filtered_records: List[Dict[str, Any]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        scope = _safe_text(row.get("market_scope")).upper()
        if market_input in {"KOSPI", "KOSDAQ", "KONEX", "NASDAQ", "NYSE", "AMEX"} and scope != market_input:
            continue
        filtered_records.append(row)

    grouped: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "theme_name": "",
            "symbol_count": 0,
            "confidence_sum": 0.0,
            "return_sum": 0.0,
            "return_count": 0,
            "positive_return_count": 0,
            "negative_return_count": 0,
            "symbols": [],
            "sources": Counter(),
            "industry_samples": [],
            "product_samples": [],
        }
    )
    day_return_map = day_return_map or build_market_day_return_map(market_input)
    classified_symbols = 0
    for row in filtered_records:
        primary_theme = normalize_theme_name(row.get("primary_theme"))
        if not primary_theme or primary_theme == "unclassified":
            continue
        symbol = _safe_text(row.get("symbol")).upper()
        memberships = row.get("memberships", []) if isinstance(row.get("memberships"), list) else []
        primary_membership = memberships[0] if memberships else {}
        group = grouped[primary_theme]
        group["theme_name"] = primary_theme
        group["symbol_count"] += 1
        group["confidence_sum"] += float(primary_membership.get("confidence", 0.0) or 0.0)
        group["symbols"].append(
            {
                "symbol": symbol,
                "name": _safe_text(row.get("name")),
                "confidence": round(float(primary_membership.get("confidence", 0.0) or 0.0), 3),
                "theme_source": _safe_text(primary_membership.get("theme_source")),
                "official_industry": _safe_text((row.get("official_classification") or {}).get("official_industry")),
                "official_products": _safe_text((row.get("official_classification") or {}).get("official_products")),
                "day_return_pct": day_return_map.get(symbol),
            }
        )
        group["sources"][_safe_text(primary_membership.get("theme_source")) or "unknown"] += 1
        official = row.get("official_classification") if isinstance(row.get("official_classification"), dict) else {}
        industry = _safe_text(official.get("official_industry"))
        products = _safe_text(official.get("official_products"))
        if industry and industry not in group["industry_samples"]:
            group["industry_samples"].append(industry)
        if products and products not in group["product_samples"]:
            group["product_samples"].append(products)
        day_return = day_return_map.get(symbol)
        if day_return is not None:
            group["return_sum"] += float(day_return)
            group["return_count"] += 1
            if float(day_return) > 0:
                group["positive_return_count"] += 1
            elif float(day_return) < 0:
                group["negative_return_count"] += 1
        classified_symbols += 1

    distribution_rows: List[Dict[str, Any]] = []
    for theme_name, group in grouped.items():
        state = theme_state_lookup.get(theme_name, {})
        avg_confidence = group["confidence_sum"] / max(group["symbol_count"], 1)
        avg_day_return = group["return_sum"] / max(group["return_count"], 1) if group["return_count"] else None
        symbols = sorted(group["symbols"], key=lambda row: (float(row.get("confidence", 0.0) or 0.0), row.get("symbol", "")), reverse=True)
        distribution_rows.append(
            {
                "theme_name": theme_name,
                "theme_id": _theme_id(theme_name),
                "symbol_count": int(group["symbol_count"]),
                "avg_confidence": round(avg_confidence, 3),
                "avg_day_return_pct": round(float(avg_day_return), 4) if avg_day_return is not None else None,
                "return_coverage": int(group["return_count"]),
                "positive_ratio": round(group["positive_return_count"] / max(group["return_count"], 1), 4) if group["return_count"] else None,
                "negative_ratio": round(group["negative_return_count"] / max(group["return_count"], 1), 4) if group["return_count"] else None,
                "direction": _safe_text(state.get("direction")) or "NEUTRAL",
                "strength_score": round(float(state.get("strength_score", 0.0) or 0.0), 1),
                "momentum_class": _safe_text(state.get("momentum_class")),
                "source_mix": dict(group["sources"]),
                "industry_samples": group["industry_samples"][:3],
                "product_samples": group["product_samples"][:3],
                "symbols": symbols[:25],
            }
        )

    distribution_rows.sort(
        key=lambda row: (
            -9999.0 if row.get("avg_day_return_pct") is None else float(row.get("avg_day_return_pct", 0.0) or 0.0),
            float(row.get("strength_score", 0.0) or 0.0),
            int(row.get("symbol_count", 0)),
            row.get("theme_name", ""),
        ),
        reverse=True,
    )
    total_symbols = len(filtered_records)
    unclassified_symbols = max(total_symbols - classified_symbols, 0)
    top_theme = distribution_rows[0]["theme_name"] if distribution_rows else "unclassified"
    return {
        "market": market_input,
        "canonical_market": canonical_market,
        "total_symbols": total_symbols,
        "classified_symbols": classified_symbols,
        "unclassified_symbols": unclassified_symbols,
        "classified_ratio": round(classified_symbols / max(total_symbols, 1), 4),
        "top_theme": top_theme,
        "rows": distribution_rows[:top_n],
        "all_rows": distribution_rows,
    }


def refresh_theme_data_pipeline(market: str) -> Dict[str, Any]:
    instrument_payload = build_instrument_master_payload(market)
    write_instrument_master_payload(instrument_payload)
    membership_payload = build_theme_membership_payload(market, instrument_payload=instrument_payload)
    write_theme_membership_payload(membership_payload)
    try:
        from modules.theme_catalog import load_theme_catalog

        load_theme_catalog.cache_clear()
    except Exception:
        pass
    report = build_theme_data_validation_report(
        market,
        instrument_payload=instrument_payload,
        membership_payload=membership_payload,
    )
    report_paths = write_theme_data_validation_report(report)
    return {
        "instrument_master": instrument_payload,
        "theme_membership": membership_payload,
        "validation_report": report,
        "report_paths": {key: str(path) for key, path in report_paths.items()},
    }
