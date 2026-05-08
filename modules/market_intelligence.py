"""
Market Intelligence Module (Phase 40)
=====================================
Uses Gemini LLM to analyze real-time global news headlines and extract:
- Geopolitical themes (e.g., war, trade war, pandemic)
- Affected sectors (defense, energy, tech, etc.)
- Market sentiment bias
- Specific beneficiary/victim stock categories

Called ONCE per scan session (not per stock) to avoid API overuse.
The result is then used to adjust Alpha Scores for individual stocks.
"""

import os
import json
import time
import calendar
import re
import html
import socket
import feedparser
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dotenv import load_dotenv
from urllib.parse import quote
from datetime import datetime, timezone
from modules.live_scan_context import context_ttl_seconds, normalize_market_key, KR_TZ, US_TZ, live_mode_enabled
from modules.theme_signal_engine import build_theme_intelligence
from modules.us_overnight_theme_lead import enrich_kr_intel_with_us_overnight_theme_lead

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

load_dotenv()
load_dotenv(".env.local")

# Cache to avoid repeated API calls within same session
_intelligence_cache = {}
_invalid_key_warned = set()

POSITIVE_HINTS = [
    "상승", "강세", "랠리", "반등", "호조", "수혜", "개선", "확대", "rebound", "rally",
    "gain", "surge", "beat", "strong", "upgrade", "cooling inflation", "rate cut"
]
NEGATIVE_HINTS = [
    "하락", "급락", "약세", "리스크", "경고", "불안", "긴장", "충격", "매도", "전쟁",
    "plunge", "drop", "selloff", "risk", "fear", "war", "tariff", "downgrade", "hot inflation"
]

MACRO_CATEGORIES = [
    "GEOPOLITICS",
    "OIL",
    "FX",
    "RATES",
    "POLITICS",
    "ECONOMY",
    "LIQUIDITY",
    "EARNINGS",
    "REGULATION",
]

RULE_BASED_CATEGORY_HINTS = {
    "GEOPOLITICS": ["전쟁", "휴전", "긴장", "관세", "tariff", "war", "ceasefire", "middle east", "중동", "china", "대만"],
    "OIL": ["유가", "원유", "wti", "brent", "oil", "lng", "energy"],
    "FX": ["환율", "원달러", "달러", "dxy", "usd/krw", "yen", "엔화", "currency"],
    "RATES": ["금리", "국채", "채권", "10년물", "yield", "fed", "fomc", "rate cut", "rate hike"],
    "POLITICS": ["정치", "선거", "대선", "의회", "president", "election", "parliament", "정부"],
    "ECONOMY": ["경기", "침체", "고용", "cpi", "pce", "inflation", "recession", "growth", "gdp"],
    "LIQUIDITY": ["유동성", "부양", "qt", "qe", "stimulus", "funding", "credit"],
    "EARNINGS": ["실적", "earnings", "guidance", "매출", "영업이익"],
    "REGULATION": ["규제", "승인", "fda", "공시", "contract", "계약", "임상", "license"],
}

DRIVER_LABELS = {
    "GEOPOLITICS": "지정학",
    "OIL": "유가",
    "FX": "환율",
    "RATES": "금리",
    "POLITICS": "정책/정치",
    "ECONOMY": "경기",
    "LIQUIDITY": "수급/유동성",
    "EARNINGS": "실적/수주",
    "REGULATION": "규제/공시",
}

DART_KEY_DISCLOSURE_HINTS = [
    "공급계약", "단일판매", "수주", "계약", "임상", "허가", "승인", "특허",
    "기술이전", "전환사채", "유상증자", "무상증자", "합병", "분할",
    "자기주식", "조회공시", "관리종목", "투자판단", "소송", "영업정지",
]

DART_POSITIVE_EVENT_RULES = [
    ("단일판매", 4, "EARNINGS", "수주/판매계약"),
    ("공급계약체결", 4, "EARNINGS", "공급계약"),
    ("기술이전", 5, "REGULATION", "기술이전"),
    ("품목허가", 5, "REGULATION", "허가"),
    ("승인", 4, "REGULATION", "승인"),
    ("특허", 3, "REGULATION", "특허"),
    ("자기주식취득", 3, "LIQUIDITY", "자사주"),
    ("무상증자", 2, "LIQUIDITY", "무상증자"),
    ("합병", 2, "EARNINGS", "합병"),
]

DART_NEGATIVE_EVENT_RULES = [
    ("공급계약해지", -5, "EARNINGS", "계약해지"),
    ("단일판매ㆍ공급계약해지", -5, "EARNINGS", "계약해지"),
    ("유상증자", -6, "LIQUIDITY", "유상증자"),
    ("전환사채", -5, "LIQUIDITY", "전환사채"),
    ("신주인수권부사채", -5, "LIQUIDITY", "BW"),
    ("교환사채", -4, "LIQUIDITY", "교환사채"),
    ("관리종목", -6, "REGULATION", "관리종목"),
    ("조회공시", -2, "REGULATION", "조회공시"),
    ("소송", -4, "REGULATION", "소송"),
    ("영업정지", -6, "REGULATION", "영업정지"),
    ("담보제공", -2, "LIQUIDITY", "담보제공"),
    ("최대주주변경", -2, "POLITICS", "최대주주변경"),
]


def _coerce_json_text(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    if not text:
        return ""
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1].strip()
    return text


def _build_rule_fallback_result(headlines, market, source: str, insight_suffix: str):
    result = _build_rule_based_intelligence(headlines, market)
    disclosure_meta = _extract_disclosure_signals(headlines)
    if disclosure_meta.get("disclosure_events"):
        result["disclosure_events"] = disclosure_meta["disclosure_events"]
        result["company_event_bias"] = disclosure_meta["company_event_bias"]
        for category, bump in disclosure_meta.get("driver_bump", {}).items():
            current = int(result.get("driver_scores", {}).get(category, 0) or 0)
            result["driver_scores"][category] = int(max(-5, min(5, current + int(bump))))
    result.update(build_theme_intelligence(market, result))
    result["source"] = source
    result["headline_count"] = len(headlines or [])
    if insight_suffix:
        base = str(result.get("key_insight", "") or "").strip()
        result["key_insight"] = f"{base} | {insight_suffix}".strip(" |")
    result = _finalize_intelligence_payload(result, headlines, market)
    result = enrich_kr_intel_with_us_overnight_theme_lead(result, market=market)
    return result

def _build_rule_based_intelligence(headlines, market):
    score = 0
    positives = []
    negatives = []
    driver_scores = {category: 0 for category in MACRO_CATEGORIES}
    macro_drivers = []
    risk_flags = []
    cross_asset_signals = []
    for line in headlines:
        text = str(line or "").lower()
        for kw in POSITIVE_HINTS:
            if kw.lower() in text:
                score += 8
                positives.append(kw)
                break
        for kw in NEGATIVE_HINTS:
            if kw.lower() in text:
                score -= 8
                negatives.append(kw)
                break
        for category, hints in RULE_BASED_CATEGORY_HINTS.items():
            if any(h in text for h in hints):
                if any(kw.lower() in text for kw in POSITIVE_HINTS):
                    driver_scores[category] += 2
                elif any(kw.lower() in text for kw in NEGATIVE_HINTS):
                    driver_scores[category] -= 2
                else:
                    driver_scores[category] += 1 if category in {"EARNINGS", "LIQUIDITY"} else 0

    for category, driver_score in driver_scores.items():
        if driver_score == 0:
            continue
        signal = "BULLISH" if driver_score > 0 else "BEARISH"
        description = f"{category} 관련 헤드라인이 최근 시장에 {'우호적' if driver_score > 0 else '부정적'}으로 작용 중입니다."
        macro_drivers.append(
            {
                "category": category,
                "signal": signal,
                "market_impact": int(max(-5, min(5, driver_score))),
                "description": description,
            }
        )
        if driver_score < 0:
            risk_flags.append(category)

    joined = " ".join(str(x) for x in headlines).lower()
    if any(kw in joined for kw in ["usd/krw", "원달러", "달러 강세", "dxy", "strong dollar"]):
        cross_asset_signals.append(
            {"asset": "FX", "direction": "UP", "market_impact": -2, "description": "달러 강세/환율 부담"}
        )
    if any(kw in joined for kw in ["wti", "brent", "유가", "원유"]):
        cross_asset_signals.append(
            {"asset": "OIL", "direction": "UP", "market_impact": -1, "description": "유가 상승 압력"}
        )
    if any(kw in joined for kw in ["yield", "10년물", "국채금리", "treasury"]):
        cross_asset_signals.append(
            {"asset": "RATES", "direction": "UP", "market_impact": -2, "description": "금리 상승 압력"}
        )

    score = max(-100, min(100, score))
    if score >= 20:
        sentiment = "BULLISH"
    elif score <= -20:
        sentiment = "BEARISH"
    elif score != 0:
        sentiment = "MIXED"
    else:
        sentiment = "NEUTRAL"

    beneficiary = []
    victim = []
    joined = " ".join(str(x) for x in headlines).lower()
    if any(kw in joined for kw in ["반도체", "semiconductor", "ai", "chip"]):
        beneficiary.append("반도체")
    if any(kw in joined for kw in ["방산", "defense", "missile", "war"]):
        beneficiary.append("방산")
    if any(kw in joined for kw in ["oil", "원유", "에너지", "lng"]):
        beneficiary.append("에너지")
    if any(kw in joined for kw in ["관세", "tariff", "war", "긴장"]):
        victim.append("소비재")
        victim.append("수출민감주")
    if any(kw in joined for kw in ["yield", "금리", "inflation", "hot inflation"]):
        victim.append("성장주")

    market_name = str(market or "시장")
    positive_drivers = [DRIVER_LABELS.get(category, category) for category, value in driver_scores.items() if value > 0]
    negative_drivers = [DRIVER_LABELS.get(category, category) for category, value in driver_scores.items() if value < 0]
    tailwind = ", ".join(positive_drivers[:2]) if positive_drivers else "선별적 수급"
    headwind = ", ".join(negative_drivers[:2]) if negative_drivers else "뚜렷한 시스템 리스크 제한"
    if sentiment == "BULLISH":
        insight = f"{market_name}는 {tailwind}이 버팀목으로 작동하며 상방 우위가 유지되는 흐름입니다."
    elif sentiment == "BEARISH":
        insight = f"{market_name}는 {headwind} 부담이 커지며 방어적 대응이 필요한 구간입니다."
    elif sentiment == "MIXED":
        insight = f"{market_name}는 {tailwind}과 {headwind}이 엇갈려 추격보다 선별 대응이 중요한 장세입니다."
    else:
        insight = f"{market_name}는 뚜렷한 한 방향보다 개별 재료 소화에 가까운 흐름입니다."

    return {
        "market_sentiment": sentiment,
        "sentiment_score": int(score),
        "themes": [],
        "macro_drivers": macro_drivers[:6],
        "driver_scores": {k: int(max(-5, min(5, v))) for k, v in driver_scores.items()},
        "cross_asset_signals": cross_asset_signals[:4],
        "risk_flags": sorted(set(risk_flags))[:6],
        "news_quality": "LOW" if len(headlines) < 2 else ("MEDIUM" if len(headlines) < 5 else "HIGH"),
        "beneficiary_sectors": sorted(set(beneficiary)),
        "victim_sectors": sorted(set(victim)),
        "beneficiary_keywords": sorted(set(positives))[:8],
        "victim_keywords": sorted(set(negatives))[:8],
        "key_insight": insight,
        "evidence_headlines": headlines[:4],
        "raw_headlines": headlines,
        "source": "rss_rule_based",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _headline_bucket(text: str, market: str) -> str:
    body = str(text or "").strip()
    lower = body.lower()
    if body.startswith("[DART"):
        return "disclosure"
    if body.startswith("[주달"):
        return "theme_feed"
    macro_keywords = [
        "코스피", "코스닥", "한국 증시", "증시", "외국인", "기관", "수급", "환율", "금리", "유가",
        "나스닥", "nasdaq", "s&p", "dow", "treasury", "yield", "fed", "fomc", "inflation", "macro",
    ]
    company_keywords = ["특징주", "수주", "계약", "실적", "목표가", "upgrade", "downgrade", "guidance", "earnings"]
    if any(token in lower for token in macro_keywords):
        return "macro"
    if any(token in lower for token in company_keywords):
        return "company"
    market_key = str(market or "").upper()
    if market_key in {"KOSPI", "KOSDAQ", "KR"}:
        if any(source in lower for source in ["sbs biz", "한국경제", "매일경제", "연합뉴스", "머니투데이", "이데일리"]):
            return "macro"
    return "general"


def _select_balanced_headlines(collected, market: str, max_items: int):
    ranked = []
    seen = set()
    for ts, text in collected or []:
        line = str(text or "").strip()
        if not line:
            continue
        dedup_key = line.lower()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        relevance = _headline_relevance_score(line, market)
        bucket = _headline_bucket(line, market)
        if relevance <= 0 and bucket not in {"disclosure", "theme_feed"}:
            continue
        ranked.append((int(ts or 0), line, relevance, bucket))
    ranked.sort(key=lambda item: (item[2], item[0]), reverse=True)

    buckets = {"macro": [], "company": [], "disclosure": [], "theme_feed": [], "general": []}
    for ts, line, relevance, bucket in ranked:
        buckets.setdefault(bucket, []).append((ts, line, relevance))

    market_key = str(market or "KOSPI").upper()
    if market_key in {"KOSPI", "KOSDAQ", "KR"}:
        quotas = [("macro", 6), ("company", 3), ("theme_feed", 2), ("disclosure", 2), ("general", 2)]
        hard_caps = {"disclosure": 2, "theme_feed": 2}
    else:
        quotas = [("macro", 7), ("company", 4), ("general", 4), ("disclosure", 0), ("theme_feed", 0)]
        hard_caps = {}

    selected = []
    selected_keys = set()
    picked_by_bucket = {name: 0 for name in buckets}

    def _take(line: str, bucket: str):
        dedup_key = line.lower()
        if dedup_key in selected_keys or len(selected) >= max_items:
            return
        selected.append(line)
        selected_keys.add(dedup_key)
        picked_by_bucket[bucket] = picked_by_bucket.get(bucket, 0) + 1

    for bucket, quota in quotas:
        for _, line, _ in buckets.get(bucket, [])[:quota]:
            _take(line, bucket)
            if len(selected) >= max_items:
                break
        if len(selected) >= max_items:
            break

    if len(selected) < max_items:
        for _, line, _, bucket in ranked:
            cap = hard_caps.get(bucket)
            if cap is not None and picked_by_bucket.get(bucket, 0) >= cap:
                continue
            _take(line, bucket)
            if len(selected) >= max_items:
                break

    return selected[:max_items]


def _normalize_text_list(rows, limit: int = 6):
    seen = set()
    normalized = []
    for row in rows or []:
        text = str(row or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def _ensure_market_lists(result):
    beneficiary = _normalize_text_list(result.get("beneficiary_sectors"), limit=6)
    victim = _normalize_text_list(result.get("victim_sectors"), limit=6)
    driver_scores = result.get("driver_scores") if isinstance(result.get("driver_scores"), dict) else {}
    if not beneficiary:
        beneficiary = [
            DRIVER_LABELS.get(category, category)
            for category, value in driver_scores.items()
            if int(value or 0) > 0
        ][:4]
    if not victim:
        victim = [
            DRIVER_LABELS.get(category, category)
            for category, value in driver_scores.items()
            if int(value or 0) < 0
        ][:4]
    result["beneficiary_sectors"] = beneficiary
    result["victim_sectors"] = victim
    result["beneficiary_keywords"] = _normalize_text_list(result.get("beneficiary_keywords"), limit=8)
    result["victim_keywords"] = _normalize_text_list(result.get("victim_keywords"), limit=8)
    result["risk_flags"] = _normalize_text_list(result.get("risk_flags"), limit=6)
    evidence = _normalize_text_list(result.get("evidence_headlines"), limit=4)
    if not evidence:
        evidence = _normalize_text_list(result.get("raw_headlines"), limit=4)
    result["evidence_headlines"] = evidence
    return result


def _finalize_intelligence_payload(result, headlines, market):
    if not isinstance(result, dict):
        return result
    payload = dict(result)
    payload["raw_headlines"] = _normalize_text_list(headlines or payload.get("raw_headlines"), limit=15)
    payload["headline_count"] = int(payload.get("headline_count", len(payload["raw_headlines"])) or len(payload["raw_headlines"]))
    payload = _ensure_market_lists(payload)
    return payload


def _extract_disclosure_signals(headlines):
    disclosure_events = []
    company_event_bias = {}
    driver_bump = {category: 0 for category in MACRO_CATEGORIES}

    for line in headlines or []:
        text = str(line or "").strip()
        if not text.startswith("[DART"):
            continue
        body = text.split("] ", 1)[1] if "] " in text else text
        body = body.split(" | ", 1)[0]
        if " - " not in body:
            continue
        corp_name, report_nm = [part.strip() for part in body.split(" - ", 1)]
        report_lower = report_nm.lower()

        matched = None
        for pattern, score, category, label in DART_NEGATIVE_EVENT_RULES:
            if pattern.lower() in report_lower:
                matched = (score, category, label)
                break
        if matched is None:
            for pattern, score, category, label in DART_POSITIVE_EVENT_RULES:
                if pattern.lower() in report_lower:
                    matched = (score, category, label)
                    break
        if matched is None:
            continue

        score, category, label = matched
        disclosure_events.append(
            {
                "company": corp_name,
                "report_name": report_nm,
                "event_score": int(score),
                "category": category,
                "label": label,
                "polarity": "POSITIVE" if score > 0 else "NEGATIVE",
            }
        )
        company_event_bias[corp_name] = int(max(-8, min(8, company_event_bias.get(corp_name, 0) + score)))
        driver_bump[category] = int(max(-5, min(5, driver_bump.get(category, 0) + (1 if score > 0 else -1))))

    return {
        "disclosure_events": disclosure_events[:8],
        "company_event_bias": company_event_bias,
        "driver_bump": driver_bump,
    }

MARKET_INTEL_PROMPT = """당신은 시장별 뉴스를 근거로 요약하는 글로벌 매크로 전략가입니다.
선택 시장은 {market} 입니다. 아래 헤드라인에서 실제로 보이는 정보만 사용해 JSON으로 정리하세요.
반복적이고 추상적인 문구를 피하고, 선택 시장에 직접 연결되는 설명을 우선하세요.
시장 전체를 움직이는 흐름을 우선하고, 개별 종목 공시(DART)는 보조 근거로만 사용하세요.
핵심 인사이트는 반드시 "현재 버티는 축"과 "경계할 리스크"를 함께 담은 한 문장으로 작성하세요.
수혜/피해 섹터와 키워드는 비워두지 말고, 명확한 섹터명이 없으면 거시/스타일 축(예: 반도체, 바이오, 성장주, 경기민감주, 방어주, 수급/유동성, 환율 민감주)으로라도 채우세요.

[뉴스 헤드라인]
{headlines}

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
  "market_sentiment": "BULLISH" | "BEARISH" | "MIXED" | "NEUTRAL",
  "sentiment_score": -100 ~ 100 (정수, 시장 전체 분위기),
  "themes": [
    {{
      "theme": "테마명 (예: 중동 지정학 리스크, AI 혁명, 금리 인하 기대 등)",
      "impact": "POSITIVE" | "NEGATIVE" | "MIXED",
      "description": "한 줄 설명"
    }}
  ],
  "macro_drivers": [
    {{
      "category": "GEOPOLITICS" | "OIL" | "FX" | "RATES" | "POLITICS" | "ECONOMY" | "LIQUIDITY" | "EARNINGS" | "REGULATION",
      "signal": "BULLISH" | "BEARISH" | "MIXED" | "NEUTRAL",
      "market_impact": -5 ~ 5 (정수, 선택 시장에 미치는 영향),
      "description": "왜 이 요인이 현재 시장에 중요했는지 한 줄",
      "evidence": "근거가 된 짧은 헤드라인 또는 요약"
    }}
  ],
  "driver_scores": {{
    "GEOPOLITICS": -5 ~ 5,
    "OIL": -5 ~ 5,
    "FX": -5 ~ 5,
    "RATES": -5 ~ 5,
    "POLITICS": -5 ~ 5,
    "ECONOMY": -5 ~ 5,
    "LIQUIDITY": -5 ~ 5,
    "EARNINGS": -5 ~ 5,
    "REGULATION": -5 ~ 5
  }},
  "cross_asset_signals": [
    {{
      "asset": "USD/KRW" | "DXY" | "US10Y" | "WTI" | "BRENT" | "GOLD" | "BTC" | "VIX",
      "direction": "UP" | "DOWN" | "MIXED" | "NEUTRAL",
      "market_impact": -5 ~ 5,
      "description": "선택 시장에 주는 영향 한 줄"
    }}
  ],
  "risk_flags": ["현재 시장을 누르는 핵심 리스크 태그 1~6개"],
  "news_quality": "HIGH" | "MEDIUM" | "LOW",
  "beneficiary_sectors": ["방산", "에너지", "반도체" 등 수혜 섹터 목록],
  "victim_sectors": ["여행", "항공", "소비재" 등 피해 섹터 목록],
  "beneficiary_keywords": ["방위산업", "미사일", "원유", "LNG" 등 수혜 종목 키워드],
  "victim_keywords": ["여행사", "항공사", "면세점" 등 피해 종목 키워드],
  "key_insight": "현재 시장에서 가장 중요한 투자 인사이트 한 줄",
  "evidence_headlines": ["가장 중요한 근거 헤드라인 2~4개"]
}}
"""


def _headline_queries(market: str):
    key = str(market or "KOSPI").upper()
    query_map = {
        "KOSPI": [
            ("코스피 외국인 기관 수급", "ko", "KR"),
            ("한국 증시 반도체 자동차 은행", "ko", "KR"),
            ("원달러 금리 한국 증시", "ko", "KR"),
            ("국제유가 환율 금리 지정학 한국 증시", "ko", "KR"),
            ("한국 정치 선거 정책 증시", "ko", "KR"),
        ],
        "KOSDAQ": [
            ("코스닥 급등 공시 수주 임상 계약", "ko", "KR"),
            ("오전장 특징주 코스닥", "ko", "KR"),
            ("증시요약 특징 종목 코스닥", "ko", "KR"),
            ("코스닥 바이오 로봇 2차전지 AI 수급", "ko", "KR"),
            ("코스닥 외국인 기관 수급", "ko", "KR"),
            ("원달러 유가 금리 지정학 코스닥", "ko", "KR"),
            ("한국 정치 정책 규제 코스닥", "ko", "KR"),
        ],
        "NASDAQ": [
            ("nasdaq tech earnings ai semiconductors", "en-US", "US"),
            ("nasdaq market movers guidance upgrades", "en-US", "US"),
            ("fed yields inflation tech stocks", "en-US", "US"),
            ("oil dollar yields geopolitics nasdaq", "en-US", "US"),
            ("us election politics regulation tech stocks", "en-US", "US"),
        ],
        "S&P500": [
            ("s&p 500 market breadth earnings macro", "en-US", "US"),
            ("dow s&p sector rotation rates inflation", "en-US", "US"),
            ("us stock market today recession treasury", "en-US", "US"),
            ("oil dollar yields geopolitics s&p 500", "en-US", "US"),
            ("us election fiscal policy regulation stocks", "en-US", "US"),
        ],
        "AMEX": [
            ("nyse american stocks today small cap surge", "en-US", "US"),
            ("small cap stock news today offering contract fda", "en-US", "US"),
            ("microcap momentum stock halt dilution today", "en-US", "US"),
            ("small cap oil dollar yields geopolitics today", "en-US", "US"),
            ("small cap regulation offering dilution politics", "en-US", "US"),
        ],
        "US": [
            ("stock market today nasdaq s&p 500", "en-US", "US"),
            ("fed inflation yields us stocks", "en-US", "US"),
            ("market movers earnings geopolitics", "en-US", "US"),
        ],
        "KR": [
            ("한국 증시 코스피 코스닥", "ko", "KR"),
            ("원달러 금리 외국인 수급", "ko", "KR"),
            ("반도체 바이오 2차전지 증시", "ko", "KR"),
        ],
    }
    return query_map.get(key, query_map["KOSPI"])


def _fallback_headline_queries(market: str):
    key = str(market or "KOSPI").upper()
    if key in {"KOSPI", "KOSDAQ", "KR"}:
        return [
            ("한국 증시 오늘", "ko", "KR"),
            ("코스피 코스닥 오늘 뉴스", "ko", "KR"),
            ("오전장 특징주 코스닥", "ko", "KR"),
        ]
    return [
        ("stock market today", "en-US", "US"),
        ("nasdaq today", "en-US", "US"),
        ("small cap stocks today", "en-US", "US"),
    ]


def _direct_feed_urls(market: str):
    key = str(market or "KOSPI").upper()
    kr_common = [
        "https://www.yna.co.kr/rss/market.xml",
        "https://www.yna.co.kr/rss/economy.xml",
        "https://www.hankyung.com/feed/finance",
        "https://www.hankyung.com/feed/economy",
        "https://www.mk.co.kr/rss/30000001/",
        "https://www.mk.co.kr/rss/30100041/",
    ]
    us_common = [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://feeds.marketwatch.com/marketwatch/marketpulse/",
        "https://finance.yahoo.com/news/rssindex",
    ]
    feed_map = {
        "KOSPI": kr_common,
        "KOSDAQ": kr_common,
        "KR": kr_common,
        "NASDAQ": us_common + [
            "https://www.cnbc.com/id/15839135/device/rss/rss.html",
        ],
        "S&P500": us_common,
        "AMEX": us_common + [
            "https://www.investing.com/rss/news_25.rss",
        ],
        "US": us_common,
    }
    return feed_map.get(key, kr_common)


def _fetch_judal_theme_updates(market: str, max_items: int = 8):
    if normalize_market_key(market) != "KR":
        return []
    urls = [
        ("상승테마", "https://www.judal.co.kr/?view=themeList&type=changeRateDesc"),
        ("핫테마", "https://www.judal.co.kr/?view=themeList&type=neglectRateHot"),
        ("기대수익률", "https://www.judal.co.kr/?view=themeList&type=expectRateDesc"),
    ]
    banned = {"ETF", "ETN", "테마없음", "스팩"}
    seen = set()
    collected = []
    now_ts = int(time.time())
    timeout_sec = _network_timeout("AG_MARKET_INTEL_THEME_FEED_TIMEOUT_SEC", 4.0)

    def _parse_theme_text(text: str) -> str:
        clean = " ".join(str(text or "").split())
        clean = re.sub(r"\(\d+\)$", "", clean).strip()
        return clean

    for bucket, url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    "Referer": "https://www.judal.co.kr/",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"Judal fetch error ({bucket}): {e}")
            continue

        theme_names = []
        if BeautifulSoup is not None:
            try:
                soup = BeautifulSoup(html, "html.parser")
                for anchor in soup.find_all("a", href=True):
                    href = str(anchor.get("href") or "")
                    if "themeIdx=" not in href:
                        continue
                    label = _parse_theme_text(anchor.get_text(" ", strip=True))
                    if not label or label in banned:
                        continue
                    theme_names.append(label)
            except Exception as e:
                print(f"Judal parse error ({bucket}): {e}")
        else:
            for href, label in re.findall(r'href="([^"]*themeIdx=\d+[^"]*)".*?>([^<]+)</a>', html, flags=re.IGNORECASE | re.DOTALL):
                label = _parse_theme_text(label)
                if not label or label in banned:
                    continue
                theme_names.append(label)

        deduped = []
        for label in theme_names:
            if label in seen:
                continue
            seen.add(label)
            deduped.append(label)
            if len(deduped) >= max_items // max(1, len(urls)) + 2:
                break

        for rank, label in enumerate(deduped[: max(2, max_items // len(urls))], start=1):
            collected.append((now_ts, f"[주달 {bucket}] {label} | 주달"))

    return collected[:max_items]


def _headline_relevance_score(text: str, market: str) -> int:
    body = str(text or "").lower()
    market_key = str(market or "KOSPI").upper()
    common_kr = {
        "외국인": 2,
        "기관": 2,
        "수급": 2,
        "환율": 2,
        "금리": 2,
        "유가": 2,
        "공시": 2,
        "전자공시": 2,
    }
    market_rules = {
        "KOSPI": {"코스피": 5, "반도체": 3, "자동차": 3, "은행": 2, "대형주": 2},
        "KOSDAQ": {"코스닥": 5, "바이오": 3, "로봇": 3, "ai": 2, "임상": 3, "수주": 2, "특징주": 2},
        "KR": {"코스피": 3, "코스닥": 3, "한국 증시": 4},
        "NASDAQ": {"nasdaq": 5, "tech": 3, "ai": 3, "semiconductor": 3, "earnings": 2},
        "S&P500": {"s&p": 5, "dow": 3, "macro": 2, "treasury": 2},
        "AMEX": {"small cap": 4, "microcap": 4, "offering": 3, "fda": 3, "dilution": 3},
    }
    score = 0
    for kw, weight in common_kr.items():
        if kw.lower() in body:
            score += weight
    for kw, weight in market_rules.get(market_key, {}).items():
        if kw.lower() in body:
            score += weight
    return score


def _normalize_headline_title(title: str, source: str = "") -> str:
    text = html.unescape(str(title or "")).strip()
    text = re.sub(r"\s+", " ", text)
    src = str(source or "").strip()
    if src:
        escaped = re.escape(src)
        text = re.sub(rf"\s*[-|]\s*{escaped}\s*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def _network_timeout(name: str, default: float) -> float:
    try:
        return max(1.0, float(os.environ.get(name, str(default)) or default))
    except Exception:
        return float(default)


def _parse_feed_url(url: str, timeout: float):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read()
    return feedparser.parse(payload)


def _fetch_dart_disclosures(market: str, max_items: int = 10):
    if normalize_market_key(market) != "KR":
        return []
    api_key = os.environ.get("OPENDART_API_KEY", "").strip()
    if not api_key:
        return []

    allowed_dates, _ = _allowed_trade_dates(market)
    date_values = sorted(d.strftime("%Y%m%d") for d in allowed_dates)
    bgn_de = date_values[0]
    end_de = date_values[-1]
    market_key = str(market or "KR").upper()
    corp_cls = {"KOSPI": "Y", "KOSDAQ": "K"}.get(market_key, "")

    params = {
        "crtfc_key": api_key,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_count": "100",
    }
    if corp_cls:
        params["corp_cls"] = corp_cls
    url = "https://opendart.fss.or.kr/api/list.json?" + urllib.parse.urlencode(params)

    timeout_sec = _network_timeout("AG_MARKET_INTEL_DART_TIMEOUT_SEC", 5.0)
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"DART fetch error ({market_key}): {e}")
        return []

    if str(payload.get("status", "")) != "000":
        print(f"DART API status ({market_key}): {payload.get('status')} {payload.get('message')}")
        return []

    items = payload.get("list", []) or []
    if not isinstance(items, list):
        return []

    prioritized = []
    others = []
    for item in items:
        corp_name = str(item.get("corp_name", "")).strip()
        report_nm = str(item.get("report_nm", "")).strip()
        rcept_dt = str(item.get("rcept_dt", "")).strip()
        if not corp_name or not report_nm or not rcept_dt:
            continue
        headline = f"[DART {rcept_dt}] {corp_name} - {report_nm} | 전자공시"
        lower = report_nm.lower()
        if any(hint.lower() in lower for hint in DART_KEY_DISCLOSURE_HINTS):
            prioritized.append(headline)
        else:
            others.append(headline)

    combined = prioritized[:max_items]
    if len(combined) < max_items:
        combined.extend(others[: max_items - len(combined)])
    now_ts = int(time.time())
    return [(now_ts, text) for text in combined]


def _dynamic_kr_market_leaders(market: str):
    market_key = str(market or "KR").upper()
    try:
        from modules.quant_analysis import QuantStrategy
    except Exception as e:
        print(f"KR market leader import error: {e}")
        return []

    try:
        base_default = {
            "KOSPI": int(os.getenv("AG_MARKET_INTEL_LEADER_COUNT_KOSPI", "6")),
            "KOSDAQ": int(os.getenv("AG_MARKET_INTEL_LEADER_COUNT_KOSDAQ", "8")),
            "KR": int(os.getenv("AG_MARKET_INTEL_LEADER_COUNT_KR", "8")),
        }.get(market_key, int(os.getenv("AG_MARKET_INTEL_LEADER_COUNT", "6")))
    except Exception:
        base_default = 8 if market_key in {"KOSDAQ", "KR"} else 6

    try:
        open_bonus = int(os.getenv("AG_MARKET_INTEL_LEADER_COUNT_OPEN_BONUS", "2"))
    except Exception:
        open_bonus = 2

    leader_count = base_default + (open_bonus if live_mode_enabled(market_key) else 0)
    leader_count = max(4, min(12, leader_count))

    try:
        if market_key in {"KOSPI", "KOSDAQ"}:
            tickers = QuantStrategy.get_market_tickers(market_key)
            return list((tickers or {}).keys())[:leader_count]
        if market_key == "KR":
            kospi_target = max(2, leader_count // 2)
            kosdaq_target = max(2, leader_count - kospi_target)
            kospi = list((QuantStrategy.get_market_tickers("KOSPI") or {}).keys())[:kospi_target]
            kosdaq = list((QuantStrategy.get_market_tickers("KOSDAQ") or {}).keys())[:kosdaq_target]
            merged = []
            for ticker in kospi + kosdaq:
                if ticker not in merged:
                    merged.append(ticker)
            return merged[:leader_count]
    except Exception as e:
        print(f"KR market leader fetch error ({market_key}): {e}")
    return []


def _collect_kr_stock_headlines(market: str):
    market_key = str(market or "KR").upper()
    tickers = _dynamic_kr_market_leaders(market_key)
    if not tickers:
        return []
    try:
        from modules.naver_news_scraper import NaverNewsScraper
    except Exception as e:
        print(f"Naver stock news import error: {e}")
        return []

    scraper = NaverNewsScraper()
    now_ts = int(time.time())
    collected = []
    seen_headlines: set = set()
    for ticker in tickers:
        try:
            payload = scraper.get_news_sentiment(ticker, days=2)
        except Exception as e:
            print(f"Naver stock news fetch error ({ticker}): {e}")
            continue
        items = list(payload.get("headline_items", []) or [])
        ticker_added = 0
        for item in items[:5]:
            title = _normalize_headline_title(item.get("title"), item.get("source"))
            if not title:
                continue
            dedup_key = title.lower()
            if dedup_key in seen_headlines:
                continue
            seen_headlines.add(dedup_key)
            source = str(item.get("source", "") or "네이버증권").strip()
            date_str = str(item.get("datetime", "") or "").strip()
            ts = now_ts
            if date_str:
                try:
                    ts = int(datetime.strptime(date_str[:12], "%Y%m%d%H%M").timestamp())
                except Exception:
                    ts = now_ts
            pub = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}" if len(date_str) >= 12 else ""
            text = f"[{pub}] {title}" if pub else title
            if source:
                text = f"{text} | {source}"
            collected.append((ts, text))
            ticker_added += 1
            if ticker_added >= 2:
                break
    return collected


def _entry_timestamp(entry) -> int:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    try:
        return int(calendar.timegm(parsed))
    except Exception:
        return 0


def _allowed_trade_dates(market: str):
    region = normalize_market_key(market)
    tz = KR_TZ if region == "KR" else US_TZ
    today_local = datetime.now(tz).date()
    allowed = {today_local}
    prev = today_local
    while True:
        prev = prev.fromordinal(prev.toordinal() - 1)
        if prev.weekday() < 5:
            allowed.add(prev)
            break
    return allowed, tz


def _fetch_global_headlines(market="KR", max_items=15):
    """Fetch latest market-specific headlines from Google RSS + direct feeds."""
    allowed_dates, tz = _allowed_trade_dates(market)
    seen_titles = set()
    query_timeout = _network_timeout("AG_MARKET_INTEL_QUERY_TIMEOUT_SEC", 4.0)
    feed_timeout = _network_timeout("AG_MARKET_INTEL_FEED_TIMEOUT_SEC", 4.0)

    def _collect(queries):
        collected = []
        per_query = max(3, max_items // max(1, len(queries)))
        for query, lang, region in queries:
            try:
                encoded = quote(query)
                url = f"https://news.google.com/rss/search?q={encoded}&hl={lang}&gl={region}&ceid={region}:{lang.split('-')[0]}"
                feed = _parse_feed_url(url, timeout=query_timeout)

                for entry in feed.entries[:per_query]:
                    source = ""
                    source_meta = entry.get("source")
                    if isinstance(source_meta, dict):
                        source = str(source_meta.get("title", "")).strip()
                    title = _normalize_headline_title(entry.get('title', ''), source)
                    if not title:
                        continue
                    dedup_key = title.lower()
                    if dedup_key in seen_titles:
                        continue
                    seen_titles.add(dedup_key)
                    pub = str(entry.get('published', '')).strip()
                    ts = _entry_timestamp(entry)
                    if ts <= 0:
                        continue
                    pub_dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(tz)
                    if pub_dt.date() not in allowed_dates:
                        continue
                    text = f"[{pub}] {title}" if pub else title
                    if source:
                        text = f"{text} | {source}"
                    collected.append((ts, text))
            except Exception as e:
                print(f"RSS Fetch Error ({query}): {e}")
        return collected

    def _collect_feed_urls(urls):
        collected = []
        per_feed = max(4, max_items // max(1, len(urls)))
        for url in urls:
            try:
                feed = _parse_feed_url(url, timeout=feed_timeout)
                for entry in feed.entries[:per_feed]:
                    title = _normalize_headline_title(entry.get("title", ""))
                    if not title:
                        continue
                    dedup_key = title.lower()
                    if dedup_key in seen_titles:
                        continue
                    ts = _entry_timestamp(entry)
                    if ts <= 0:
                        continue
                    pub_dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(tz)
                    if pub_dt.date() not in allowed_dates:
                        continue
                    seen_titles.add(dedup_key)
                    pub = str(entry.get("published", "") or entry.get("updated", "")).strip()
                    source = ""
                    source_meta = entry.get("source")
                    if isinstance(source_meta, dict):
                        source = str(source_meta.get("title", "")).strip()
                    if not source:
                        link = str(entry.get("link", "")).strip()
                        if "cnbc.com" in link:
                            source = "CNBC"
                        elif "marketwatch.com" in link:
                            source = "MarketWatch"
                        elif "yahoo.com" in link:
                            source = "Yahoo Finance"
                        elif "yna.co.kr" in link:
                            source = "연합뉴스"
                        elif "hankyung.com" in link:
                            source = "한국경제"
                        elif "mk.co.kr" in link:
                            source = "매일경제"
                        elif "judal.co.kr" in link:
                            source = "주달"
                        elif "investing.com" in link:
                            source = "Investing.com"
                    text = f"[{pub}] {title}" if pub else title
                    if source:
                        text = f"{text} | {source}"
                    collected.append((ts, text))
            except Exception as e:
                print(f"RSS Feed Error ({url}): {e}")
        return collected

    collected = _collect(_headline_queries(market))
    collected.extend(_collect_feed_urls(_direct_feed_urls(market)))
    collected.extend(_fetch_dart_disclosures(market, max_items=max(4, max_items // 2)))
    if normalize_market_key(market) == "KR":
        collected.extend(_fetch_judal_theme_updates(market, max_items=max(4, max_items // 2)))
        # Always include Naver stock-linked headlines — these have the highest relevance scores
        # and contain actual market direction signals (시장 상황, 코스피 방향 등)
        collected.extend(_collect_kr_stock_headlines(market))
    if not collected:
        collected = _collect(_fallback_headline_queries(market))
        collected.extend(_collect_feed_urls(_direct_feed_urls(market)))
        collected.extend(_fetch_dart_disclosures(market, max_items=max(4, max_items // 2)))
        if normalize_market_key(market) == "KR":
            collected.extend(_fetch_judal_theme_updates(market, max_items=max(4, max_items // 2)))
        if normalize_market_key(market) == "KR":
            collected.extend(_collect_kr_stock_headlines(market))

    headlines = _select_balanced_headlines(collected, market, max_items=max_items)
    return headlines


def get_market_intelligence(market="KOSPI", api_key=None, force_refresh=False):
    """
    Main entry point: Fetch news → Send to Gemini → Return structured intelligence.
    Results are cached for 30 minutes to avoid excessive API calls.
    
    Returns:
        dict with keys: market_sentiment, sentiment_score, themes, 
              beneficiary_sectors, victim_sectors, beneficiary_keywords, 
              victim_keywords, key_insight, raw_headlines
    """
    global _intelligence_cache
    market_key = normalize_market_key(market)
    ttl = context_ttl_seconds(market_key, open_seconds=300, closed_seconds=1800)
    cache = _intelligence_cache.get(market_key, {'data': None, 'timestamp': 0, 'ttl': ttl})
    cache['ttl'] = ttl

    def _attach_display_origin(result, origin: str):
        if not isinstance(result, dict):
            return result
        payload = dict(result)
        payload["_display_origin"] = str(origin or "live")
        return payload
    
    # Check cache first
    now = time.time()
    if not force_refresh and cache['data'] and (now - cache['timestamp']) < cache['ttl']:
        print("📡 Market Intelligence: Using cached data")
        return _attach_display_origin(cache['data'], "cache")
    
    # Default fallback
    default_result = {
        'market_sentiment': 'NEUTRAL',
        'sentiment_score': 0,
        'themes': [],
        'theme_states': [],
        'beneficiary_themes': [],
        'headwind_themes': [],
        'theme_evidence': {},
        'macro_drivers': [],
        'driver_scores': {category: 0 for category in MACRO_CATEGORIES},
        'cross_asset_signals': [],
        'risk_flags': [],
        'news_quality': 'LOW',
        'disclosure_events': [],
        'company_event_bias': {},
        'beneficiary_sectors': [],
        'victim_sectors': [],
        'beneficiary_keywords': [],
        'victim_keywords': [],
        'evidence_headlines': [],
        'key_insight': 'No intelligence available',
        'raw_headlines': [],
        'headline_count': 0,
        'model': '',
        'source': 'fallback'
    }
    default_result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if not api_key:
        api_key = os.environ.get('GEMINI_API_KEY', '')
    
    # 1. Fetch Headlines
    headlines = _fetch_global_headlines(market)
    
    if not headlines:
        print("⚠️ Market Intelligence: No headlines fetched")
        default_result['key_insight'] = f"No intelligence available ({market} headlines unavailable)"
        default_result = enrich_kr_intel_with_us_overnight_theme_lead(default_result, market=market)
        return _attach_display_origin(default_result, "live")

    disclosure_meta = _extract_disclosure_signals(headlines)
    if disclosure_meta.get("disclosure_events"):
        default_result["disclosure_events"] = disclosure_meta["disclosure_events"]
        default_result["company_event_bias"] = disclosure_meta["company_event_bias"]
        for category, bump in disclosure_meta.get("driver_bump", {}).items():
            default_result["driver_scores"][category] = int(max(-5, min(5, default_result["driver_scores"].get(category, 0) + bump)))

    if not api_key:
        print("⚠️ Market Intelligence: No Gemini API Key, using RSS rule-based mode")
        result = _build_rule_fallback_result(
            headlines,
            market,
            source="rss_rule_based",
            insight_suffix="Gemini key unavailable, fallback mode active",
        )
        cache['data'] = result
        cache['timestamp'] = now
        _intelligence_cache[market_key] = cache
        return _attach_display_origin(result, "live")
    
    # 2. Ask Gemini for Analysis
    try:
        prompt_headlines = headlines[:12]
        headlines_text = "\n".join(prompt_headlines)
        prompt = MARKET_INTEL_PROMPT.format(market=market, headlines=headlines_text)

        timeout_sec = 25.0
        try:
            timeout_sec = float(os.environ.get("AG_MARKET_INTEL_GEMINI_TIMEOUT_SEC", "25"))
        except Exception:
            timeout_sec = 25.0

        primary_model = (
            os.environ.get("AG_MARKET_INTEL_GEMINI_PRIMARY_MODEL")
            or os.environ.get("GEMINI_MARKET_INTEL_MODEL")
            or "gemini-2.5-flash"
        )
        secondary_model = os.environ.get("AG_MARKET_INTEL_GEMINI_SECONDARY_MODEL", "gemini-2.5-pro")
        model_candidates = []
        for model_name in [primary_model, secondary_model]:
            model_name = str(model_name or "").strip()
            if model_name and model_name not in model_candidates:
                model_candidates.append(model_name)

        response_payload = None
        last_exc = None
        used_model = None

        def _run_gemini_http(model_name: str):
            endpoint = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{urllib.parse.quote(model_name, safe='')}:generateContent?key={quote(api_key)}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                },
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=max(1.0, timeout_sec)) as resp:
                return json.loads(resp.read().decode("utf-8"))

        for model_name in model_candidates:
            try:
                response_payload = _run_gemini_http(model_name)
                used_model = model_name
                break
            except urllib.error.HTTPError as e:
                last_exc = e
                if e.code == 429:
                    break
                if e.code in {400, 404}:
                    continue
                if e.code in {401, 403}:
                    break
                continue
            except TimeoutError as e:
                last_exc = FuturesTimeoutError(str(e))
                break
            except socket.timeout as e:
                last_exc = FuturesTimeoutError(str(e))
                break
            except urllib.error.URLError as e:
                if isinstance(getattr(e, "reason", None), (TimeoutError, socket.timeout)):
                    last_exc = FuturesTimeoutError(str(e))
                    break
                last_exc = e
                continue
            except Exception as e:
                if "timed out" in str(e).lower():
                    last_exc = FuturesTimeoutError(str(e))
                    break
                last_exc = e
                continue

        if response_payload is None:
            raise last_exc or FuturesTimeoutError()

        raw_text = ""
        try:
            candidates = response_payload.get("candidates", []) if isinstance(response_payload, dict) else []
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                content = candidate.get("content", {})
                if not isinstance(content, dict):
                    continue
                parts = content.get("parts", [])
                if not isinstance(parts, list):
                    continue
                text_parts = [str(part.get("text") or "").strip() for part in parts if isinstance(part, dict) and str(part.get("text") or "").strip()]
                if text_parts:
                    raw_text = "\n".join(text_parts).strip()
                    break
        except Exception:
            raw_text = ""
        if not raw_text:
            raise json.JSONDecodeError("Empty Gemini response text", doc="", pos=0)
        
        json_text = _coerce_json_text(raw_text)
        result = json.loads(json_text)
        result['raw_headlines'] = headlines
        result['headline_count'] = len(headlines)
        disclosure_meta = _extract_disclosure_signals(headlines)
        evidence = result.get('evidence_headlines')
        if not isinstance(evidence, list):
            result['evidence_headlines'] = headlines[:4]
        result['source'] = 'gemini'
        result['model'] = used_model
        result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Validate required keys
        for key in ['market_sentiment', 'sentiment_score', 'beneficiary_sectors',
                     'victim_sectors', 'beneficiary_keywords', 'victim_keywords', 'evidence_headlines',
                     'macro_drivers', 'driver_scores', 'cross_asset_signals', 'risk_flags', 'news_quality',
                     'disclosure_events', 'company_event_bias']:
            if key not in result:
                result[key] = default_result.get(key, [])
        
        # Ensure sentiment_score is int
        result['sentiment_score'] = int(result.get('sentiment_score', 0))
        if not isinstance(result.get('driver_scores'), dict):
            result['driver_scores'] = default_result['driver_scores']
        else:
            normalized = {}
            for category in MACRO_CATEGORIES:
                try:
                    normalized[category] = int(float(result['driver_scores'].get(category, 0)))
                except Exception:
                    normalized[category] = 0
            for category, bump in disclosure_meta.get("driver_bump", {}).items():
                normalized[category] = int(max(-5, min(5, normalized.get(category, 0) + bump)))
            result['driver_scores'] = normalized
        if not isinstance(result.get("company_event_bias"), dict):
            result["company_event_bias"] = {}
        for corp_name, score in disclosure_meta.get("company_event_bias", {}).items():
            existing = result["company_event_bias"].get(corp_name, 0)
            try:
                result["company_event_bias"][corp_name] = int(max(-8, min(8, int(existing) + int(score))))
            except Exception:
                result["company_event_bias"][corp_name] = int(score)
        if not isinstance(result.get("disclosure_events"), list):
            result["disclosure_events"] = []
        result["disclosure_events"] = (disclosure_meta.get("disclosure_events", []) + result["disclosure_events"])[:8]
        result.update(build_theme_intelligence(market, result))
        result = _finalize_intelligence_payload(result, headlines, market)
        result = enrich_kr_intel_with_us_overnight_theme_lead(result, market=market)

        # Cache it
        cache['data'] = result
        cache['timestamp'] = now
        _intelligence_cache[market_key] = cache
        
        print(f"🧠 Market Intelligence[{used_model}]: {result.get('market_sentiment')} (Score: {result.get('sentiment_score')})")
        print(f"   Key Insight: {result.get('key_insight', 'N/A')}")
        
        return _attach_display_origin(result, "live")
    except FuturesTimeoutError:
        print("⚠️ Market Intelligence: Gemini request timed out, falling back to RSS rule-based mode")
        result = _build_rule_fallback_result(
            headlines,
            market,
            source="rss_rule_based_timeout",
            insight_suffix="Gemini timeout, fallback mode active",
        )
        cache['data'] = result
        cache['timestamp'] = now
        _intelligence_cache[market_key] = cache
        return _attach_display_origin(result, "live")
    except json.JSONDecodeError as e:
        print(f"⚠️ Market Intelligence JSON Parse Error: {e}")
        print(f"   Raw response: {raw_text[:200]}")
        result = _build_rule_fallback_result(
            headlines,
            market,
            source="rss_rule_based_parse_fallback",
            insight_suffix=f"JSON parse failed; fallback used for {market}",
        )
        cache['data'] = result
        cache['timestamp'] = now
        _intelligence_cache[market_key] = cache
        return _attach_display_origin(result, "live")
    except Exception as e:
        err_text = str(e)
        if isinstance(e, urllib.error.HTTPError) and getattr(e, "code", None) == 429:
            print("⚠️ Market Intelligence: Gemini rate limit hit, falling back to headline-based rule mode")
            result = _build_rule_fallback_result(
                headlines,
                market,
                source="rss_rule_based_rate_limited",
                insight_suffix="Gemini rate-limited; headline-based fallback active",
            )
            cache['data'] = result
            cache['timestamp'] = now
            _intelligence_cache[market_key] = cache
            return _attach_display_origin(result, "live")
        if "API_KEY_INVALID" in err_text or "API key not valid" in err_text:
            warn_key = f"{market_key}:invalid_api_key"
            if warn_key not in _invalid_key_warned:
                print("⚠️ Market Intelligence: Gemini API key is invalid, falling back to RSS rule-based mode")
                _invalid_key_warned.add(warn_key)
            result = _build_rule_fallback_result(
                headlines,
                market,
                source="rss_rule_based_invalid_key",
                insight_suffix="Gemini key invalid, fallback mode active",
            )
            cache['data'] = result
            cache['timestamp'] = now
            _intelligence_cache[market_key] = cache
            return _attach_display_origin(result, "live")
        print(f"⚠️ Market Intelligence Error: {e}")
        result = _build_rule_fallback_result(
            headlines,
            market,
            source="rss_rule_based_error",
            insight_suffix=f"Market intelligence error; fallback used for {market}",
        )
        cache['data'] = result
        cache['timestamp'] = now
        _intelligence_cache[market_key] = cache
        return _attach_display_origin(result, "live")


def calculate_news_adjustment(stock_name, ticker, sector_hint, intel_data):
    """
    Calculate how much to adjust a stock's Alpha Score based on market intelligence.
    
    Args:
        stock_name: Korean name of the stock (e.g., "한화에어로스페이스")
        ticker: Stock ticker (e.g., "012450.KS")
        sector_hint: Any sector info from the stock
        intel_data: Result from get_market_intelligence()
    
    Returns:
        dict with:
            - score_adjustment: int (-15 to +15)
            - reason: str (why adjusted)
            - is_beneficiary: bool
            - is_victim: bool
    """
    if not intel_data:
        return {'score_adjustment': 0, 'reason': 'No intelligence', 
                'is_beneficiary': False, 'is_victim': False}
    
    adjustment = 0
    reasons = []
    is_beneficiary = False
    is_victim = False
    
    name_lower = stock_name.lower() if stock_name else ""
    
    # 1. Check Beneficiary Keywords
    for kw in intel_data.get('beneficiary_keywords', []):
        if kw.lower() in name_lower:
            adjustment += 10
            reasons.append(f"🔥 수혜 키워드 '{kw}' 매칭")
            is_beneficiary = True
            break
    
    # 2. Check Victim Keywords
    for kw in intel_data.get('victim_keywords', []):
        if kw.lower() in name_lower:
            adjustment -= 10
            reasons.append(f"⚠️ 피해 키워드 '{kw}' 매칭")
            is_victim = True
            break
    
    # 3. Global Sentiment Bias (smaller effect)
    sentiment_score = intel_data.get('sentiment_score', 0)
    if abs(sentiment_score) > 30:
        global_adj = int(sentiment_score / 20)  # Max ±5
        adjustment += global_adj
        if abs(global_adj) > 2:
            reasons.append(f"📊 시장 분위기 {'긍정' if global_adj > 0 else '부정'}")

    # 4. Structured macro drivers
    driver_scores = intel_data.get('driver_scores') or {}
    if isinstance(driver_scores, dict) and driver_scores:
        try:
            macro_bias = sum(int(float(v)) for v in driver_scores.values())
        except Exception:
            macro_bias = 0
        macro_adj = max(-4, min(4, int(round(macro_bias / 10.0))))
        if macro_adj != 0:
            adjustment += macro_adj
            reasons.append(f"🧭 거시 드라이버 {'우호' if macro_adj > 0 else '부담'}")

    # 5. Low-quality news dampening
    if str(intel_data.get("news_quality", "MEDIUM")).upper() == "LOW" and adjustment != 0:
        adjustment = int(adjustment * 0.7)
        reasons.append("📰 뉴스 밀도 낮음")

    # 6. Company-specific disclosure bias
    company_event_bias = intel_data.get("company_event_bias") or {}
    if stock_name and isinstance(company_event_bias, dict):
        stock_name_lower = str(stock_name).lower().strip()
        for company, score in company_event_bias.items():
            company_lower = str(company).lower().strip()
            if not company_lower:
                continue
            if stock_name_lower == company_lower or stock_name_lower in company_lower or company_lower in stock_name_lower:
                disclosure_adj = max(-8, min(8, int(score)))
                adjustment += disclosure_adj
                reasons.append(f"📄 공시 이벤트 {'긍정' if disclosure_adj > 0 else '부정'}")
                if disclosure_adj > 0:
                    is_beneficiary = True
                elif disclosure_adj < 0:
                    is_victim = True
                break

    # 7. Theme-state overlay
    theme_states = intel_data.get("theme_states") or []
    if stock_name and isinstance(theme_states, list):
        stock_name_lower = str(stock_name).lower().strip()
        best_theme_score = 0.0
        best_theme_reason = ""
        for state in theme_states:
            if not isinstance(state, dict):
                continue
            theme_name = str(state.get("theme_name") or state.get("theme_id") or "").lower().strip()
            keywords = list(state.get("beneficiary_keywords", []) or []) + list(state.get("victim_keywords", []) or [])
            matched = False
            if theme_name and theme_name in stock_name_lower:
                matched = True
            elif any(str(kw).lower() in stock_name_lower for kw in keywords if str(kw).strip()):
                matched = True
            if not matched:
                continue
            direction = str(state.get("direction") or "NEUTRAL").upper()
            strength = float(state.get("strength_score", 0.0) or 0.0)
            theme_adj = min(6.0, max(0.0, (strength - 35.0) * 0.08))
            if direction == "BENEFICIARY":
                if theme_adj > best_theme_score:
                    best_theme_score = theme_adj
                    best_theme_reason = "🧩 테마 수혜"
                    is_beneficiary = True
            elif direction == "HEADWIND":
                if theme_adj > best_theme_score:
                    best_theme_score = -theme_adj
                    best_theme_reason = "🧩 테마 역풍"
                    is_victim = True
        if best_theme_score != 0:
            adjustment += best_theme_score
            reasons.append(best_theme_reason)

    # Cap adjustment
    adjustment = max(-15, min(15, adjustment))
    
    return {
        'score_adjustment': adjustment,
        'reason': ' | '.join(reasons) if reasons else '시장 이벤트 영향 없음',
        'is_beneficiary': is_beneficiary,
        'is_victim': is_victim
    }
