from __future__ import annotations

import json
import os
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER_PATH = Path("/Users/dongdong/Downloads/kospi_kosdaq_allstocks_structured.jsonl")
DEFAULT_THEME_RULES_PATH = Path("/Users/dongdong/Downloads/kospi_kosdaq_allstocks_structured.xlsx")
LOCAL_MASTER_PATH = PROJECT_ROOT / "models" / "kr_stock_theme_master.jsonl"
RUNTIME_THEME_MEMBERSHIP_PATH = PROJECT_ROOT / "runtime_state" / "long_term" / "theme_membership" / "KR.json"

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
    "정유/에너지": "정유/에너지",
    "정유": "정유/에너지",
    "석유": "정유/에너지",
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
    "우주항공/방산": "우주항공/방산",
    "항공우주": "우주항공/방산",
    "우주": "우주항공/방산",
    "it서비스/플랫폼": "IT서비스/플랫폼",
    "it 서비스/플랫폼": "IT서비스/플랫폼",
    "플랫폼": "IT서비스/플랫폼",
    "ai": "IT서비스/플랫폼",
    "ai/데이터센터": "IT서비스/플랫폼",
    "데이터센터": "IT서비스/플랫폼",
    "클라우드": "IT서비스/플랫폼",
    "핀테크": "IT서비스/플랫폼",
    "가상자산/블록체인": "가상자산/블록체인",
    "블록체인": "가상자산/블록체인",
    "전자부품/디스플레이": "전자부품/디스플레이",
    "디스플레이": "전자부품/디스플레이",
    "pcb": "전자부품/디스플레이",
    "산업재/기계": "산업재/기계",
    "기계": "산업재/기계",
    "지주/투자": "지주/투자",
    "창투": "지주/투자",
    "운송/물류": "운송/물류",
    "교육/출판": "교육/출판",
    "농업/사료": "농업/사료",
    "제지/포장": "제지/포장",
    "섬유/의류": "섬유/의류",
}

THEME_RULES_FALLBACK = {
    "2차전지": ["2차전지", "이차전지", "전고체", "양극재", "음극재", "전해액", "분리막", "배터리", "축전지", "전지", "리튬", "니켈", "코발트", "동박", "전기차용 배터리"],
    "반도체": ["반도체", "메모리", "HBM", "낸드", "DRAM", "파운드리", "웨이퍼", "패키징", "프로브카드", "프로브 카드", "테스트소켓", "테스트 소켓", "반도체 장비", "식각", "증착", "플라즈마", "세정장비", "세정", "Chemical 중앙공급", "C.C.S.S", "클린룸"],
    "바이오/헬스케어": ["의약", "치료제", "백신", "진단", "제약", "바이오", "의료", "헬스", "임플란트", "미용기기", "adc", "항체", "면역항암", "신약", "의료기기", "건강기능식품", "실험동물", "세포", "동물용 의약품", "생명과학", "시약", "DNA", "Sequencing", "Microarray", "Mouse", "아목사실린", "시메티딘", "아셀렉스", "안전성평가", "유효성평가", "시판후조사", "알파리퀴드", "유전체", "NGS", "암패널", "Genelix", "Genext", "Geneka"],
    "자동차": ["자동차", "차량", "전기차", "모빌리티", "타이어", "자율주행", "자동차 부품", "엔진부품", "와이어링 하네스", "연료저장장치", "내장품", "자전거"],
    "통신/네트워크": ["통신", "네트워크", "5G", "6G", "안테나", "광통신", "RF", "기지국", "스위치", "라우터", "커넥터", "케이블", "전화번호", "콜센터", "고객센터", "광트랜시버", "광다중화장치"],
    "로봇/자동화": ["로봇", "자동화", "스마트팩토리", "공작기계", "3d 프린터", "레이저", "감속기", "협동로봇", "물류로봇", "자동화 장비"],
    "친환경/에너지": ["태양광", "풍력", "수소", "연료전지", "ESS", "원자력", "전력", "에너지", "탄소", "폐기물", "전선", "케이블", "보일러", "난방", "히트펌프", "열교환기", "열교환", "모듈", "변압기", "송배전", "전력기기", "전동기", "발전기", "전자변성기", "변환장치"],
    "정유/에너지": ["정유", "석유", "석유류", "유류", "LPG", "윤활유"],
    "조선/해양": ["조선", "선박", "해양", "LNG선", "선박엔진", "선박용", "조선기자재"],
    "철강/금속/소재": ["철강", "금속", "구리", "알루미늄", "알미", "화학소재", "화학", "소재", "필름", "유리", "와이어", "합금", "강관", "스테인리스", "비철금속", "도금", "잉크리본", "인화지", "플라스틱", "합성수지", "파이프", "실란트", "열연박판", "후판", "무늬강판", "Magnet", "Shield Magnet", "필터", "내화", "요업", "세라믹", "페라이트", "벽돌", "몰탈", "화공약품", "안경렌즈"],
    "건설/부동산": ["건설", "부동산", "레미콘", "시멘트", "모듈러", "건자재", "토목", "수중공사", "준설", "시설물", "콘크리트", "플랜트", "아스팔트", "건축", "실내건축", "창호", "설계", "감리", "합판", "마루", "파티클보드", "우드칩", "목재", "MDF", "바닥재"],
    "소비재/유통": ["화장품", "식품", "음료", "유통", "면세", "패션", "생활용품", "의복", "어묵", "백화점", "리조트", "카지노", "홍삼", "인삼", "가구", "주방", "렌탈", "소파", "유제품", "숙박", "여행", "렌터카", "완구", "레인지후드", "의자", "양돈", "도축", "육계", "삼계", "육가공", "삼계탕", "오리", "와인", "정수기", "온수매트", "가방", "모자", "무점포 소매", "종합 소매", "상품 종합 도매", "도소매", "TV홈쇼핑", "홈쇼핑", "편의점", "프랜차이즈", "곡물가공", "소맥분", "밀가루", "아이스크림", "우유", "치즈", "스낵", "비스킷", "당과", "치킨", "신발", "모피", "조리기", "Jayjun", "Nerdy"],
    "게임/콘텐츠/엔터": ["게임", "콘텐츠", "엔터", "영화", "드라마", "음악", "광고", "웹툰", "영상", "음향", "전시관", "박물관", "엑스포", "반주기", "방송", "캐릭터", "미술품", "경매", "골프", "콘서트", "음반", "음원", "아티스트", "악기", "피아노", "기타", "현악기", "창작 및 예술"],
    "금융": ["금융", "은행", "보험", "증권", "캐피탈", "카드", "신탁", "신용조회", "채권추심", "신용조사", "기업신용", "ATM", "CD-VAN"],
    "IT서비스/플랫폼": ["소프트웨어", "SW", "S/W", "H/W", "클라우드", "플랫폼", "AI", "인공지능", "보안", "핀테크", "결제", "데이터", "시스템 통합", "온라인투자", "전자칠판", "전자교탁", "솔루션", "TeraStream", "전자상거래", "그룹웨어", "자료관리시스템", "POS", "금전등록기", "인터넷 인프라", "호스팅", "포털", "인터넷연동서비스", "미들웨어", "FXUI", "줌닷컴", "스토리지", "SPSS", "SI", "휴대폰부가서비스", "권리조사", "리서치"],
    "방산": ["방산", "미사일", "탄약", "군수", "무기", "방탄", "총포탄", "전투", "유도탄"],
    "우주항공/방산": ["우주", "항공", "위성", "발사체", "항공기", "항공우주", "넥스텍", "추진기관"],
    "가상자산/블록체인": ["블록체인", "가상자산", "암호화폐", "비트코인", "토큰증권", "STO"],
    "전자부품/디스플레이": ["전자부품", "전자부품 제조업", "디스플레이", "OLED", "LCD", "FPD", "LED", "터치패널", "PCB", "FPCB", "인쇄회로", "회로기판", "모듈", "전자칠판", "광학필름", "BLU", "전구", "형광등", "PC", "모니터", "컴퓨터", "플로터", "셋톱박스", "카메라 윈도우", "휴대폰액세서리", "코리아써", "HTL", "HIL", "RED HOST"],
    "산업재/기계": ["기계", "장비", "특수 목적용 기계", "산업용", "펌프", "압축기", "밸브", "기어", "베어링", "엘리베이터", "공조", "냉동", "자동판매기", "검사 장비", "아스팔트믹싱플랜트", "자동제어반", "모터", "MOTOR", "TIMER", "정밀기기", "측정", "시험", "줄자", "지게차", "인증서비스", "기술검사서비스", "전기전자규격", "계측제어", "고무벨트", "콘베이어벨트"],
    "지주/투자": ["지주", "투자", "창업투자", "벤처캐피탈", "신기술사업금융", "기업인수목적", "SPAC", "스팩", "회사 본부", "경영 컨설팅", "사업경영", "관리자문", "사모펀드", "PEF", "신탁업", "집합투자업"],
    "운송/물류": ["운송", "물류", "해운", "항공운송", "택배", "창고", "포워딩"],
    "교육/출판": ["교육", "출판", "학습", "교재", "이러닝", "도서", "학원", "어학원", "온라인강의", "만화단행본", "정기간행물"],
    "농업/사료": ["농업", "사료", "비료", "종자", "농약", "축산", "수산", "조경수", "작물", "고추", "수박", "참외", "오이", "호박", "배추", "살균제", "살충제", "제초제", "토마토"],
    "제지/포장": ["제지", "펄프", "종이", "판지", "골판지", "카톤팩", "포장", "포장재", "인쇄", "다이어리"],
    "섬유/의류": ["섬유", "의류", "의복", "봉제", "직물", "염색", "신사복", "패션"],
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
    allow_external_default = str(os.getenv("AG_ALLOW_EXTERNAL_KR_THEME_MASTER", "0")).strip().lower() in {"1", "true", "yes", "on"}
    paths: List[Path] = []
    if env_path:
        paths.append(Path(env_path).expanduser())
    paths.append(LOCAL_MASTER_PATH)
    if allow_external_default:
        paths.append(DEFAULT_MASTER_PATH)
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
            best_increment = 0.0
            best_matches: List[str] = []
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
                increment = weight + bonus
                if increment > best_increment:
                    best_increment = increment
                    best_matches = [kw]
                elif increment == best_increment:
                    best_matches.append(kw)
            if best_increment <= 0:
                continue
            scores[theme] = scores.get(theme, 0.0) + best_increment
            matched.setdefault(theme, [])
            for kw in best_matches:
                if kw not in matched[theme]:
                    matched[theme].append(kw)

    if not scores:
        return {"primary_theme": "unclassified", "secondary_themes": [], "theme_inference_status": "blank"}

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_theme, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    top_matches = matched.get(top_theme, [])

    single_official_signal = top_score >= 1.35 and second_score <= 0.0 and len(top_matches) >= 1
    clear_leader_signal = top_score >= 1.35 and top_score >= second_score + 0.85
    multi_evidence_leader_signal = top_score >= 1.55 and len(top_matches) >= 2 and top_score > second_score
    strong_enough = (
        top_score >= 1.7 and (top_score >= second_score + 0.6 or len(top_matches) >= 2)
    ) or single_official_signal or clear_leader_signal or multi_evidence_leader_signal
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


def _ticker_from_runtime_symbol(symbol: Any, market_scope: Any) -> str:
    text = str(symbol or "").strip().upper()
    if not text:
        return ""
    if "." in text:
        return text
    scope = str(market_scope or "").strip().upper()
    if scope == "KOSDAQ":
        return f"{text}.KQ"
    if scope == "KOSPI":
        return f"{text}.KS"
    return text


def _runtime_membership_to_raw(row: Dict[str, Any]) -> Dict[str, Any]:
    official = row.get("official_classification") if isinstance(row.get("official_classification"), dict) else {}
    memberships = row.get("memberships") if isinstance(row.get("memberships"), list) else []
    source_theme_reference = ""
    if memberships and isinstance(memberships[0], dict):
        source_theme_reference = str(memberships[0].get("theme_source") or memberships[0].get("theme_id") or "")
    return {
        "ticker": _ticker_from_runtime_symbol(row.get("symbol") or row.get("ticker"), row.get("market_scope")),
        "stock_name": str(row.get("name") or row.get("stock_name") or "").strip(),
        "market": str(row.get("market_scope") or row.get("market") or "").strip().upper(),
        "sector": str(official.get("official_sector") or row.get("sector") or "").strip(),
        "official_sector": str(official.get("official_sector") or "").strip(),
        "industry": str(official.get("official_industry") or row.get("industry") or "").strip(),
        "products": str(official.get("official_products") or row.get("products") or "").strip(),
        "listing_date": str(row.get("listing_date") or "").strip(),
        "region": str(row.get("region") or "").strip(),
        "primary_theme": str(row.get("primary_theme") or "").strip(),
        "secondary_themes": row.get("secondary_themes") if isinstance(row.get("secondary_themes"), list) else [],
        "theme_inference_status": str(
            (memberships[0].get("theme_inference_status") if memberships and isinstance(memberships[0], dict) else "")
            or row.get("theme_inference_status")
            or ""
        ).strip(),
        "source_official": str(official.get("classification_source") or "").strip(),
        "source_theme_reference": source_theme_reference,
    }


def _load_runtime_membership_records() -> tuple[List[Dict[str, Any]], str]:
    if not RUNTIME_THEME_MEMBERSHIP_PATH.exists():
        return [], ""
    try:
        payload = json.loads(RUNTIME_THEME_MEMBERSHIP_PATH.read_text(encoding="utf-8"))
    except Exception:
        return [], ""
    rows = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return [], ""
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        market_scope = str(row.get("market_scope") or row.get("market") or "").upper()
        if market_scope not in {"KOSPI", "KOSDAQ"}:
            continue
        raw = _runtime_membership_to_raw(row)
        if raw.get("ticker"):
            out.append(raw)
    version = str((payload or {}).get("version") or RUNTIME_THEME_MEMBERSHIP_PATH.stat().st_mtime_ns)
    return out, f"{RUNTIME_THEME_MEMBERSHIP_PATH}::{version}"


def _build_master_from_raw_records(raw_records: List[Dict[str, Any]], *, source_path: str, version_prefix: str) -> Dict[str, Any]:
    records_by_ticker: Dict[str, Dict[str, Any]] = {}
    market_counts: Counter[str] = Counter()
    theme_counts: Counter[str] = Counter()
    spac_count = 0

    for raw in raw_records:
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
        "version": f"{version_prefix}::{source_path}",
        "source_path": source_path,
        "records_by_ticker": records_by_ticker,
        "market_counts": dict(market_counts),
        "theme_counts": dict(theme_counts),
        "unclassified_count": int(theme_counts.get("unclassified", 0)),
        "spac_count": int(spac_count),
    }


@lru_cache(maxsize=1)
def load_kr_stock_theme_master() -> Dict[str, Any]:
    path = resolve_master_path()
    raw_records: List[Dict[str, Any]] = []
    if path is not None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    text = str(line or "").strip()
                    if not text:
                        continue
                    raw = json.loads(text)
                    if isinstance(raw, dict):
                        raw_records.append(raw)
            return _build_master_from_raw_records(
                raw_records,
                source_path=str(path),
                version_prefix=f"kr-stock-theme-master::{path.stat().st_mtime_ns}",
            )
        except Exception:
            raw_records = []

    raw_records, runtime_version = _load_runtime_membership_records()
    if raw_records:
        return _build_master_from_raw_records(
            raw_records,
            source_path=runtime_version,
            version_prefix="kr-stock-theme-master-runtime",
        )

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
    return {
        "version": "unreadable",
        "source_path": str(path),
        "records_by_ticker": {},
        "market_counts": {},
        "theme_counts": {},
        "unclassified_count": 0,
        "spac_count": 0,
    }


def get_stock_theme_record(ticker: str) -> Dict[str, Any]:
    master = load_kr_stock_theme_master()
    records = master.get("records_by_ticker", {})
    if not isinstance(records, dict):
        return {}
    return records.get(str(ticker or "").strip().upper(), {}) or {}
