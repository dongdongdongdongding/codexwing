from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from modules.kr_stock_theme_master import get_stock_theme_record, load_kr_stock_theme_master, normalize_theme_name
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
    "정유/에너지": "oil_energy",
    "조선/해양": "shipbuilding",
    "철강/금속/소재": "steel_materials",
    "건설/부동산": "construction_realestate",
    "소비재/유통": "consumer_retail",
    "게임/콘텐츠/엔터": "game_content_ent",
    "금융": "finance",
    "IT서비스/플랫폼": "it_platform",
    "방산": "defense",
    "우주항공/방산": "aerospace_defense",
    "가상자산/블록체인": "crypto_blockchain",
    "전자부품/디스플레이": "electronic_components_display",
    "산업재/기계": "industrial_machinery",
    "지주/투자": "holding_investment",
    "운송/물류": "transport_logistics",
    "교육/출판": "education_publishing",
    "농업/사료": "agriculture_feed",
    "제지/포장": "paper_packaging",
    "섬유/의류": "textile_apparel",
    "unclassified": "unclassified",
}

THEME_ALIAS_FALLBACK = {
    "2차전지": ["2차전지", "이차전지", "배터리", "축전지", "전지", "양극재", "양극활물질", "음극재", "전해액", "분리막", "리튬", "니켈", "코발트", "동박", "battery", "lithium", "cathode"],
    "반도체": ["반도체", "메모리", "HBM", "낸드", "DRAM", "파운드리", "웨이퍼", "패키징", "프로브카드", "프로브 카드", "Probe Card", "테스트소켓", "테스트 소켓", "Test Socket", "Probe Station", "식각", "증착", "CVD", "LP CVD", "플라즈마", "세정장비", "세정", "Chemical 중앙공급", "C.C.S.S", "클린룸", "semiconductor", "chip", "memory", "foundry"],
    "바이오/헬스케어": ["바이오", "헬스케어", "의약", "치료제", "백신", "진단", "제약", "의료", "의료기기", "건강기능식품", "실험동물", "세포", "동물용 의약품", "생명과학", "시약", "DNA", "Sequencing", "Microarray", "Mouse", "아목사실린", "시메티딘", "아셀렉스", "안전성평가", "유효성평가", "시판후조사", "알파리퀴드", "유전체", "NGS", "암패널", "Genelix", "Genext", "Geneka", "보툴리눔", "필러", "인사돌", "마데카솔", "메디컬 에스테틱", "CRO", "생물종", "유전적 질병", "방사성동위원소", "척추임플란트", "척추용 임플란트", "전자약", "M-CHECK", "biotech", "pharma", "therapeutics", "medical"],
    "자동차": ["자동차", "차량", "전기차", "모빌리티", "자율주행", "자동차 부품", "엔진부품", "와이어링 하네스", "연료저장장치", "내장품", "자전거", "automobile", "vehicle", "ev", "mobility", "autonomous"],
    "통신/네트워크": ["통신", "네트워크", "5G", "6G", "안테나", "광통신", "RF", "기지국", "스위치", "라우터", "Router", "커넥터", "케이블", "전화번호", "콜센터", "고객센터", "광트랜시버", "광다중화장치", "PLC모뎀", "DCU", "내비게이션", "블랙박스", "telecom", "network", "wireless", "broadband"],
    "로봇/자동화": ["로봇", "자동화", "스마트팩토리", "공작기계", "3D 프린터", "레이저", "감속기", "협동로봇", "물류로봇", "자동화 장비", "robot", "automation", "factory automation"],
    "친환경/에너지": ["친환경", "에너지", "태양광", "풍력", "수소", "연료전지", "ESS", "원자력", "전력", "전선", "케이블", "보일러", "난방", "히트펌프", "열교환기", "열교환", "변압기", "송배전", "전력기기", "전동기", "발전기", "전자변성기", "변환장치", "clean energy", "solar", "wind", "hydrogen", "nuclear", "power grid"],
    "정유/에너지": ["정유", "석유", "석유류", "유류", "LPG", "윤활유", "oil refining", "petroleum"],
    "조선/해양": ["조선", "선박", "해양", "LNG선", "선박엔진", "선박용", "조선기자재", "shipbuilding", "marine", "offshore", "lng carrier"],
    "철강/금속/소재": ["철강", "금속", "구리", "알루미늄", "알미", "화학", "소재", "합금", "강관", "스테인리스", "비철금속", "도금", "필름", "잉크리본", "인화지", "플라스틱", "합성수지", "파이프", "실란트", "열연박판", "후판", "무늬강판", "Magnet", "Shield Magnet", "필터", "내화", "요업", "세라믹", "페라이트", "벽돌", "몰탈", "화공약품", "안경렌즈", "폴리프로필렌", "수처리응집제", "하이드로겔", "steel", "metal", "materials", "copper", "aluminum"],
    "건설/부동산": ["건설", "부동산", "레미콘", "시멘트", "건자재", "토목", "수중공사", "준설", "시설물", "콘크리트", "플랜트", "아스팔트", "건축", "실내건축", "창호", "설계", "감리", "합판", "마루", "파티클보드", "우드칩", "목재", "MDF", "바닥재", "construction", "real estate", "cement", "building products"],
    "소비재/유통": ["화장품", "식품", "음료", "유통", "면세", "패션", "생활용품", "의복", "어묵", "백화점", "리조트", "카지노", "홍삼", "인삼", "가구", "주방", "렌탈", "소파", "유제품", "숙박", "여행", "렌터카", "완구", "레인지후드", "의자", "양돈", "도축", "육계", "삼계", "육가공", "삼계탕", "오리", "와인", "정수기", "온수매트", "가방", "모자", "무점포 소매", "종합 소매", "상품 종합 도매", "도소매", "TV홈쇼핑", "홈쇼핑", "편의점", "프랜차이즈", "곡물가공", "소맥분", "밀가루", "아이스크림", "우유", "치즈", "스낵", "비스킷", "당과", "치킨", "신발", "모피", "조리기", "Jayjun", "Nerdy", "시리얼", "시리얼바", "마스크팩", "면생리대", "은나노스텝", "닥터오렌지", "consumer", "retail", "cosmetics", "beverage", "food"],
    "게임/콘텐츠/엔터": ["게임", "콘텐츠", "엔터", "영화", "드라마", "웹툰", "영상", "음향", "전시관", "박물관", "엑스포", "반주기", "방송", "캐릭터", "미술품", "경매", "골프", "콘서트", "음반", "음원", "아티스트", "악기", "피아노", "기타", "현악기", "창작 및 예술", "game", "gaming", "content", "entertainment", "media"],
    "금융": ["금융", "은행", "보험", "증권", "캐피탈", "카드", "신용조회", "채권추심", "신용조사", "기업신용", "ATM", "CD-VAN", "financial", "bank", "insurance", "brokerage", "capital markets"],
    "IT서비스/플랫폼": ["IT서비스", "플랫폼", "소프트웨어", "SW", "S/W", "H/W", "클라우드", "AI", "인공지능", "보안", "핀테크", "결제", "데이터", "시스템 통합", "온라인투자", "전자칠판", "전자교탁", "솔루션", "TeraStream", "전자상거래", "그룹웨어", "자료관리시스템", "POS", "금전등록기", "인터넷 인프라", "호스팅", "포털", "인터넷연동서비스", "미들웨어", "FXUI", "줌닷컴", "스토리지", "SPSS", "SI", "휴대폰부가서비스", "권리조사", "리서치", "판도라TV", "KM 플레이어", "디지털 사이니지", "키오스크", "software", "platform", "cloud", "security", "fintech", "data center"],
    "방산": ["방산", "미사일", "탄약", "군수", "무기", "defense", "aerospace", "missile", "munition", "weapons"],
    "우주항공/방산": ["우주", "항공", "위성", "발사체", "항공기", "항공우주", "넥스텍", "추진기관", "aerospace", "satellite", "launch vehicle"],
    "가상자산/블록체인": ["가상자산", "블록체인", "암호화폐", "비트코인", "토큰증권", "STO", "crypto", "blockchain"],
    "전자부품/디스플레이": ["전자부품", "전자부품 제조업", "디스플레이", "OLED", "LCD", "FPD", "LED", "터치패널", "PCB", "FPCB", "인쇄회로", "회로기판", "모듈", "광학필름", "BLU", "전구", "형광등", "PC", "모니터", "컴퓨터", "플로터", "셋톱박스", "카메라 윈도우", "휴대폰액세서리", "코리아써", "HTL", "HIL", "RED HOST", "display", "printed circuit board"],
    "산업재/기계": ["기계", "장비", "특수 목적용 기계", "산업용", "펌프", "압축기", "밸브", "기어", "베어링", "엘리베이터", "공조", "냉동", "자동판매기", "검사 장비", "아스팔트믹싱플랜트", "자동제어반", "모터", "MOTOR", "TIMER", "정밀기기", "측정", "시험", "줄자", "지게차", "인증서비스", "기술검사서비스", "전기전자규격", "계측제어", "고무벨트", "콘베이어벨트", "전자가속기", "정밀금형", "사출품", "industrial machinery"],
    "지주/투자": ["지주", "투자", "창업투자", "벤처캐피탈", "신기술사업금융", "기업인수목적", "SPAC", "스팩", "회사 본부", "경영 컨설팅", "사업경영", "관리자문", "사모펀드", "PEF", "신탁업", "집합투자업", "venture capital", "holding"],
    "운송/물류": ["운송", "물류", "해운", "항공운송", "택배", "창고", "포워딩", "logistics", "shipping"],
    "교육/출판": ["교육", "출판", "학습", "교재", "이러닝", "도서", "학원", "어학원", "온라인강의", "만화단행본", "정기간행물", "education", "publishing"],
    "농업/사료": ["농업", "사료", "비료", "종자", "농약", "축산", "수산", "조경수", "작물", "고추", "수박", "참외", "오이", "호박", "배추", "살균제", "살충제", "제초제", "토마토", "feed", "fertilizer"],
    "제지/포장": ["제지", "펄프", "종이", "판지", "골판지", "카톤팩", "포장", "포장재", "인쇄", "다이어리", "paper", "packaging"],
    "섬유/의류": ["섬유", "의류", "의복", "봉제", "직물", "염색", "신사복", "패션", "textile", "apparel"],
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


def _kr_name_theme_key(name: Any) -> str:
    text = re.sub(r"\s+", "", _safe_text(name))
    if not text:
        return ""
    text = re.sub(r"(?:\d+)?우(?:B|C)?(?:\(전환\))?$", "", text)
    text = re.sub(r"(?:\d+)?우선주$", "", text)
    return text


def _build_kr_name_theme_fallback() -> Dict[str, Dict[str, Any]]:
    master = load_kr_stock_theme_master()
    records = master.get("records_by_ticker", {}) if isinstance(master, dict) else {}
    fallback: Dict[str, Dict[str, Any]] = {}
    for record in records.values():
        if not isinstance(record, dict):
            continue
        primary = normalize_theme_name(record.get("primary_theme"))
        if not primary or primary == "unclassified":
            continue
        key = _kr_name_theme_key(record.get("stock_name"))
        if not key:
            continue
        current = fallback.get(key)
        if current and str(current.get("theme_inference_status") or "") == "inferred":
            continue
        fallback[key] = record
    return fallback


def _lookup_kr_name_theme_fallback(fallback: Dict[str, Dict[str, Any]], name: Any) -> Dict[str, Any] | None:
    key = _kr_name_theme_key(name)
    if not key:
        return None
    direct = fallback.get(key)
    if direct:
        return direct
    if len(key) < 4:
        return None
    candidates = [(base, record) for base, record in fallback.items() if base.startswith(key) or key.startswith(base)]
    if len(candidates) != 1:
        return None
    return candidates[0][1]


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
        tokens = list(_iter_tokens(theme_row))
        for field_name, text in field_texts.items():
            if not text:
                continue
            best_increment = 0.0
            best_tokens: List[str] = []
            for token in tokens:
                token_lower = token.lower()
                if len(token_lower) < 2 or token_lower not in text:
                    continue
                increment = FIELD_WEIGHTS[field_name] + _best_match_specificity(token, field_name)
                if increment > best_increment:
                    best_increment = increment
                    best_tokens = [token]
                elif increment == best_increment:
                    best_tokens.append(token)
            if best_increment <= 0:
                continue
            score += best_increment
            fields_hit.add(field_name)
            evidence.extend(f"{field_name}:{token}" for token in best_tokens)
        if (
            score < 0.92
            and not ("official_products" in fields_hit and score >= 0.70)
            and not ("official_industry" in fields_hit and score >= 0.62)
        ):
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
    kr_name_theme_fallback = _build_kr_name_theme_fallback() if market_key == "KR" else {}
    membership_records: List[Dict[str, Any]] = []
    primary_source_distribution: Counter[str] = Counter()
    warnings: List[str] = []

    for instrument in records:
        if not isinstance(instrument, dict):
            continue
        symbol = _safe_text(instrument.get("symbol")).upper()
        market_scope = _safe_text(instrument.get("market_scope")).upper()
        best: Dict[str, Dict[str, Any]] = {}
        source_priority = {"stock_master": 3, "seed_catalog": 2, "stock_master_name_fallback": 2, "official_text_match": 1}

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

            if not best:
                name_fallback = _lookup_kr_name_theme_fallback(kr_name_theme_fallback, instrument.get("name"))
                if name_fallback:
                    fallback_primary = normalize_theme_name(name_fallback.get("primary_theme"))
                    fallback_secondary = [
                        normalize_theme_name(item)
                        for item in (name_fallback.get("secondary_themes", []) or [])
                    ]
                    if fallback_primary != "unclassified":
                        upsert(
                            {
                                "theme_name": fallback_primary,
                                "confidence": 0.78,
                                "theme_source": "stock_master_name_fallback",
                                "theme_inference_status": "name_fallback",
                                "reasons": ["preferred_or_variant_name_fallback"],
                                "evidence": [
                                    f"name_fallback:{_safe_text(instrument.get('name'))}->{_safe_text(name_fallback.get('stock_name'))}"
                                ],
                            }
                        )
                    for secondary_theme in fallback_secondary:
                        if secondary_theme == "unclassified":
                            continue
                        upsert(
                            {
                                "theme_name": secondary_theme,
                                "confidence": 0.70,
                                "theme_source": "stock_master_name_fallback",
                                "theme_inference_status": "name_fallback",
                                "reasons": ["preferred_or_variant_name_fallback_secondary"],
                                "evidence": [f"name_fallback_secondary:{secondary_theme}"],
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
