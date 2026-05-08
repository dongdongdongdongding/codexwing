"""US instrument master sector-coverage enrichment.

FDR exchange listings (NASDAQ/NYSE/AMEX) supply ``Industry`` fields for ~99.7%
of US symbols but ``Sector`` only for ~7.3% (S&P500 overlay). This module maps
the Korean-translated GICS industry labels that FDR returns onto canonical GICS
sectors and downstream KR theme ids, lifting US coverage so the theme_transfer
graph and pre-open scoring have a usable foundation.

Source-of-truth: curated lookup covering the ~30 largest industry buckets and
a keyword fallback for the long tail. Provenance is recorded per record so the
coverage report can distinguish exchange-listed, S&P500-overlaid, and derived
classifications.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.theme_catalog import THEME_ID_MAP


ENRICHED_PATH_TEMPLATE = "runtime_state/long_term/instrument_master/US_enriched.json"
COVERAGE_REPORT_PATH = "runtime_state/reports/instrument_master/us_coverage_delta.json"


# Korean GICS-industry → (GICS sector name, KR theme id).
# Theme ids align with modules/theme_catalog.THEME_ID_MAP; new US-only ids
# (ai_datacenter, biotech, ev, oil_energy, nuclear, high_yield_risk_off) surface
# the macro/cross-market themes used by theme_transfer.
_INDUSTRY_MAP: Dict[str, Tuple[str, str]] = {
    "반도체": ("Information Technology", "semiconductor"),
    "반도체 장비 및 재료": ("Information Technology", "semiconductor"),
    "생명 공학 및 의학 연구": ("Health Care", "biotech"),
    "제약": ("Health Care", "bio"),
    "의료 장비, 물품 및 유통": ("Health Care", "bio"),
    "첨단 의료 장비 및 기술": ("Health Care", "bio"),
    "의료 시설 및 서비스": ("Health Care", "bio"),
    "의료 서비스": ("Health Care", "bio"),
    "소프트웨어": ("Information Technology", "it_platform"),
    "IT 서비스 및 컨설팅": ("Information Technology", "it_platform"),
    "온라인 서비스": ("Communication Services", "it_platform"),
    "통신 및 네트워킹": ("Communication Services", "telecom"),
    "무선 통신 서비스": ("Communication Services", "telecom"),
    "유선 통신 서비스": ("Communication Services", "telecom"),
    "은행": ("Financials", "finance"),
    "투자 지주 회사": ("Financials", "finance"),
    "투자 관리 및 펀드 운영": ("Financials", "finance"),
    "투자 은행 및 중개 서비스": ("Financials", "finance"),
    "소비자 대출": ("Financials", "finance"),
    "손해보험": ("Financials", "finance"),
    "생명 보험": ("Financials", "finance"),
    "재보험": ("Financials", "finance"),
    "폐쇄형 펀드": ("Financials", "finance"),
    "상업용 REITs": ("Real Estate", "construction_realestate"),
    "주거용 REITs": ("Real Estate", "construction_realestate"),
    "특수 REITs": ("Real Estate", "construction_realestate"),
    "부동산 운영": ("Real Estate", "construction_realestate"),
    "부동산 서비스": ("Real Estate", "construction_realestate"),
    "건설 및 엔지니어링": ("Industrials", "construction_realestate"),
    "건축 자재 및 용품": ("Industrials", "construction_realestate"),
    "항공우주 및 방위": ("Industrials", "defense"),
    "오일, 가스 탐사 및 생산": ("Energy", "oil_energy"),
    "오일 및 가스 수송 서비스": ("Energy", "oil_energy"),
    "오일 및 가스 정제 및 마케팅": ("Energy", "oil_energy"),
    "오일 관련 장비 및 서비스": ("Energy", "oil_energy"),
    "종합 오일 및 가스": ("Energy", "oil_energy"),
    "전력 유틸리티": ("Utilities", "eco_energy"),
    "복합 유틸리티": ("Utilities", "eco_energy"),
    "천연 가스 유틸리티": ("Utilities", "eco_energy"),
    "재생 에너지 장비 및 서비스": ("Utilities", "eco_energy"),
    "핵 에너지": ("Utilities", "nuclear"),
    "원자력": ("Utilities", "nuclear"),
    "전기 부품 및 장비": ("Industrials", "robotics"),
    "전자 장비 및 부품": ("Industrials", "robotics"),
    "산업용 기계 및 장비": ("Industrials", "robotics"),
    "중전기": ("Industrials", "robotics"),
    "철강": ("Materials", "steel_materials"),
    "금속 및 광업": ("Materials", "steel_materials"),
    "비철 금속 광업": ("Materials", "steel_materials"),
    "특수 화학 제품": ("Materials", "steel_materials"),
    "일반 화학": ("Materials", "steel_materials"),
    "비료 및 농업용 화학 제품": ("Materials", "steel_materials"),
    "건설 자재": ("Materials", "steel_materials"),
    "종이 및 제지 제품": ("Materials", "steel_materials"),
    "컨테이너 및 포장": ("Materials", "steel_materials"),
    "자동차 및 자동차 부품": ("Consumer Discretionary", "automobile"),
    "자동차 제조": ("Consumer Discretionary", "automobile"),
    "자동차 부품": ("Consumer Discretionary", "automobile"),
    "자동차 및 트럭 제조": ("Consumer Discretionary", "automobile"),
    "타이어 및 고무 제품": ("Consumer Discretionary", "automobile"),
    "조선": ("Industrials", "shipbuilding"),
    "해운": ("Industrials", "shipbuilding"),
    "항공화물 및 물류 서비스": ("Industrials", "shipbuilding"),
    "항공사": ("Industrials", "shipbuilding"),
    "소매": ("Consumer Discretionary", "consumer_retail"),
    "백화점": ("Consumer Discretionary", "consumer_retail"),
    "전문 소매": ("Consumer Discretionary", "consumer_retail"),
    "의류 및 신발 소매": ("Consumer Discretionary", "consumer_retail"),
    "식품 및 필수 식료품 소매": ("Consumer Staples", "consumer_retail"),
    "식품 가공": ("Consumer Staples", "consumer_retail"),
    "음료수": ("Consumer Staples", "consumer_retail"),
    "담배": ("Consumer Staples", "consumer_retail"),
    "가정용 제품": ("Consumer Staples", "consumer_retail"),
    "개인 용품": ("Consumer Staples", "consumer_retail"),
    "호텔, 모텔 및 크루즈": ("Consumer Discretionary", "consumer_retail"),
    "레스토랑 및 외식": ("Consumer Discretionary", "consumer_retail"),
    "카지노 및 게임": ("Consumer Discretionary", "game_content_ent"),
    "영화 및 엔터테인먼트": ("Communication Services", "game_content_ent"),
    "방송": ("Communication Services", "game_content_ent"),
    "출판": ("Communication Services", "game_content_ent"),
    "광고 및 마케팅": ("Communication Services", "game_content_ent"),
    "인터넷 및 카탈로그 소매": ("Consumer Discretionary", "it_platform"),
    "경영 지원 서비스": ("Industrials", "it_platform"),
    "블록 체인 및 암호화폐": ("Financials", "it_platform"),
    "핀테크": ("Financials", "finance"),
    "인터랙티브 미디어 및 서비스": ("Communication Services", "it_platform"),
}


# Keyword fallback table: any industry string containing these tokens inherits
# the mapping below if no exact match hit. Order matters — first match wins.
_KEYWORD_FALLBACK: List[Tuple[str, Tuple[str, str]]] = [
    ("반도체", ("Information Technology", "semiconductor")),
    ("바이오", ("Health Care", "biotech")),
    ("생명", ("Health Care", "biotech")),
    ("제약", ("Health Care", "bio")),
    ("의료", ("Health Care", "bio")),
    ("의약", ("Health Care", "bio")),
    ("소프트웨어", ("Information Technology", "it_platform")),
    ("플랫폼", ("Information Technology", "it_platform")),
    ("인터넷", ("Communication Services", "it_platform")),
    ("AI", ("Information Technology", "ai_datacenter")),
    ("통신", ("Communication Services", "telecom")),
    ("네트워크", ("Communication Services", "telecom")),
    ("은행", ("Financials", "finance")),
    ("투자", ("Financials", "finance")),
    ("보험", ("Financials", "finance")),
    ("금융", ("Financials", "finance")),
    ("핀테크", ("Financials", "finance")),
    ("REIT", ("Real Estate", "construction_realestate")),
    ("부동산", ("Real Estate", "construction_realestate")),
    ("건설", ("Industrials", "construction_realestate")),
    ("건축", ("Industrials", "construction_realestate")),
    ("방위", ("Industrials", "defense")),
    ("항공우주", ("Industrials", "defense")),
    ("오일", ("Energy", "oil_energy")),
    ("가스", ("Energy", "oil_energy")),
    ("석유", ("Energy", "oil_energy")),
    ("유틸리티", ("Utilities", "eco_energy")),
    ("태양광", ("Utilities", "eco_energy")),
    ("재생", ("Utilities", "eco_energy")),
    ("원자력", ("Utilities", "nuclear")),
    ("핵", ("Utilities", "nuclear")),
    ("로봇", ("Industrials", "robotics")),
    ("자동화", ("Industrials", "robotics")),
    ("기계", ("Industrials", "robotics")),
    ("산업용", ("Industrials", "robotics")),
    ("전자", ("Industrials", "robotics")),
    ("철강", ("Materials", "steel_materials")),
    ("금속", ("Materials", "steel_materials")),
    ("화학", ("Materials", "steel_materials")),
    ("소재", ("Materials", "steel_materials")),
    ("자동차", ("Consumer Discretionary", "automobile")),
    ("전기차", ("Consumer Discretionary", "ev")),
    ("EV", ("Consumer Discretionary", "ev")),
    ("조선", ("Industrials", "shipbuilding")),
    ("해운", ("Industrials", "shipbuilding")),
    ("항공", ("Industrials", "shipbuilding")),
    ("소매", ("Consumer Discretionary", "consumer_retail")),
    ("식품", ("Consumer Staples", "consumer_retail")),
    ("음료", ("Consumer Staples", "consumer_retail")),
    ("담배", ("Consumer Staples", "consumer_retail")),
    ("게임", ("Communication Services", "game_content_ent")),
    ("엔터", ("Communication Services", "game_content_ent")),
    ("방송", ("Communication Services", "game_content_ent")),
    ("미디어", ("Communication Services", "game_content_ent")),
    ("광고", ("Communication Services", "game_content_ent")),
    ("카지노", ("Consumer Discretionary", "game_content_ent")),
    ("도박", ("Consumer Discretionary", "game_content_ent")),
    ("여가", ("Consumer Discretionary", "game_content_ent")),
    ("오락", ("Consumer Discretionary", "game_content_ent")),
    ("금", ("Materials", "steel_materials")),
    ("철", ("Materials", "steel_materials")),
    ("강철", ("Materials", "steel_materials")),
    ("알루미늄", ("Materials", "steel_materials")),
    ("구리", ("Materials", "steel_materials")),
    ("니켈", ("Materials", "steel_materials")),
    ("아연", ("Materials", "steel_materials")),
    ("광산", ("Materials", "steel_materials")),
    ("광업", ("Materials", "steel_materials")),
    ("채굴", ("Materials", "steel_materials")),
    ("우라늄", ("Energy", "oil_energy")),
    ("농업", ("Consumer Staples", "consumer_retail")),
    ("어업", ("Consumer Staples", "consumer_retail")),
    ("양조", ("Consumer Staples", "consumer_retail")),
    ("양조업", ("Consumer Staples", "consumer_retail")),
    ("환경", ("Utilities", "eco_energy")),
    ("폐기물", ("Utilities", "eco_energy")),
    ("교육", ("Consumer Discretionary", "consumer_retail")),
    ("학", ("Consumer Discretionary", "consumer_retail")),
    ("중장비", ("Consumer Discretionary", "automobile")),
    ("차량", ("Consumer Discretionary", "automobile")),
    ("비즈니스", ("Industrials", "it_platform")),
    ("지원", ("Industrials", "it_platform")),
    ("용품", ("Consumer Discretionary", "consumer_retail")),
    ("컴퓨터", ("Information Technology", "it_platform")),
    ("하드웨어", ("Information Technology", "it_platform")),
    ("용기", ("Materials", "steel_materials")),
    ("포장", ("Materials", "steel_materials")),
    ("인쇄", ("Industrials", "it_platform")),
    ("물류", ("Industrials", "shipbuilding")),
    ("화물", ("Industrials", "shipbuilding")),
    ("공항", ("Industrials", "shipbuilding")),
    ("항만", ("Industrials", "shipbuilding")),
    ("레스토랑", ("Consumer Discretionary", "consumer_retail")),
    ("호텔", ("Consumer Discretionary", "consumer_retail")),
    ("석탄", ("Energy", "oil_energy")),
    ("목재", ("Materials", "steel_materials")),
    ("임업", ("Materials", "steel_materials")),
    ("고용", ("Industrials", "it_platform")),
    ("소비재", ("Consumer Staples", "consumer_retail")),
    ("중전기장비", ("Industrials", "robotics")),
    ("증류주", ("Consumer Staples", "consumer_retail")),
    ("포도주", ("Consumer Staples", "consumer_retail")),
    ("개인 서비스", ("Consumer Discretionary", "consumer_retail")),
    ("의류", ("Consumer Discretionary", "consumer_retail")),
    ("액세서리", ("Consumer Discretionary", "consumer_retail")),
    ("제화", ("Consumer Discretionary", "consumer_retail")),
    ("할인점", ("Consumer Discretionary", "consumer_retail")),
    ("가구", ("Consumer Discretionary", "consumer_retail")),
    ("정보 서비스", ("Information Technology", "it_platform")),
    ("여객", ("Industrials", "shipbuilding")),
    ("운송", ("Industrials", "shipbuilding")),
    ("민자", ("Utilities", "eco_energy")),
    ("발전", ("Utilities", "eco_energy")),
    ("종이", ("Materials", "steel_materials")),
    ("직물", ("Consumer Discretionary", "consumer_retail")),
    ("가죽", ("Consumer Discretionary", "consumer_retail")),
    ("장난감", ("Consumer Discretionary", "consumer_retail")),
    ("어린이", ("Consumer Discretionary", "consumer_retail")),
    ("출판", ("Communication Services", "game_content_ent")),
    ("뮤추얼 펀드", ("Financials", "finance")),
    ("사무기기", ("Information Technology", "it_platform")),
    ("소형 장치", ("Information Technology", "it_platform")),
    ("전화", ("Communication Services", "telecom")),
]


VALID_THEME_IDS = set(THEME_ID_MAP.values()) | {"biotech", "ai_datacenter", "ev", "oil_energy", "nuclear"}


def classify_industry(industry: Optional[str]) -> Tuple[Optional[str], Optional[str], str]:
    """Return (gics_sector, theme_id, match_type) for a FDR industry string."""
    if not industry:
        return (None, None, "empty")
    key = industry.strip()
    if not key:
        return (None, None, "empty")
    if key in _INDUSTRY_MAP:
        sector, theme = _INDUSTRY_MAP[key]
        return (sector, theme, "exact")
    for kw, (sector, theme) in _KEYWORD_FALLBACK:
        if kw in key:
            return (sector, theme, "keyword")
    return (None, None, "unmapped")


def enrich_records(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Enrich each record with derived sector/theme_id; returns (enriched, coverage_delta)."""
    enriched: List[Dict[str, Any]] = []
    stats = {
        "total": len(records),
        "official_sector_before": 0,
        "official_sector_after": 0,
        "derived_sector_exact": 0,
        "derived_sector_keyword": 0,
        "unmapped_industry_samples": [],
        "theme_counts": Counter(),
    }
    for row in records:
        new_row = dict(row)
        existing_sector = str(new_row.get("official_sector") or "").strip()
        if existing_sector:
            stats["official_sector_before"] += 1
        industry = str(new_row.get("official_industry") or "").strip()
        sector, theme, match_type = classify_industry(industry)

        # Preserve S&P500 (high-trust) sector; otherwise adopt derived.
        provenance = new_row.get("classification_source") or ""
        if existing_sector:
            derived_sector = existing_sector
            derived_source = provenance or "S&P500"
        elif sector:
            derived_sector = sector
            derived_source = f"DERIVED_FROM_INDUSTRY:{match_type}"
            if match_type == "exact":
                stats["derived_sector_exact"] += 1
            elif match_type == "keyword":
                stats["derived_sector_keyword"] += 1
        else:
            derived_sector = ""
            derived_source = provenance
            if industry and len(stats["unmapped_industry_samples"]) < 20:
                stats["unmapped_industry_samples"].append(industry)

        new_row["derived_sector"] = derived_sector
        new_row["derived_theme_id"] = theme or ""
        new_row["derived_source"] = derived_source
        new_row["derived_match_type"] = match_type
        if derived_sector:
            stats["official_sector_after"] += 1
        if theme:
            stats["theme_counts"][theme] += 1
        enriched.append(new_row)

    stats["coverage_before_pct"] = round(stats["official_sector_before"] / max(stats["total"], 1) * 100, 2)
    stats["coverage_after_pct"] = round(stats["official_sector_after"] / max(stats["total"], 1) * 100, 2)
    stats["uplift_pct"] = round(stats["coverage_after_pct"] - stats["coverage_before_pct"], 2)
    stats["theme_counts"] = dict(stats["theme_counts"])
    return enriched, stats


def build_enriched_payload(source_payload: Dict[str, Any]) -> Dict[str, Any]:
    records = source_payload.get("records", []) or []
    enriched, stats = enrich_records(records)
    payload = dict(source_payload)
    payload["records"] = enriched
    payload["coverage"] = dict(source_payload.get("coverage", {}) or {})
    payload["coverage"]["derived_sector"] = stats["official_sector_after"]
    payload["coverage"]["derived_theme_id"] = sum(1 for r in enriched if r.get("derived_theme_id"))
    payload["enrichment_stats"] = stats
    payload["enrichment_version"] = "us_sector_enrichment::v1"
    return payload


def write_enriched(source_path: Path, out_path: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
    out = out_path or Path(ENRICHED_PATH_TEMPLATE)
    src = json.loads(source_path.read_text(encoding="utf-8"))
    payload = build_enriched_payload(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out, payload["enrichment_stats"]


def write_coverage_report(stats: Dict[str, Any], out_path: Path = Path(COVERAGE_REPORT_PATH)) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "total_records": stats.get("total"),
        "official_sector_before": stats.get("official_sector_before"),
        "official_sector_after": stats.get("official_sector_after"),
        "coverage_before_pct": stats.get("coverage_before_pct"),
        "coverage_after_pct": stats.get("coverage_after_pct"),
        "uplift_pct": stats.get("uplift_pct"),
        "derived_by_match_type": {
            "exact": stats.get("derived_sector_exact"),
            "keyword": stats.get("derived_sector_keyword"),
        },
        "theme_counts": stats.get("theme_counts", {}),
        "unmapped_industry_samples": stats.get("unmapped_industry_samples", []),
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
