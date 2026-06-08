from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional

from modules.kis_news_scope import (
    KIS_NEWS_SCOPE_AMBIGUOUS_BLOCK_REASON,
    KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON,
    classify_kis_news_source_scope,
)


KIS_THEME_NEWS_EVIDENCE_VERSION = "kis_theme_news_evidence_v1"

POSITIVE_NEWS_KEYWORDS = {
    "수주": "contract_order",
    "계약": "contract_order",
    "공급": "supply",
    "납품": "supply",
    "실적": "earnings",
    "매출": "earnings",
    "영업익": "earnings",
    "흑자": "earnings_positive",
    "증가": "growth",
    "성장": "growth",
    "승인": "approval",
    "허가": "approval",
    "fda": "approval",
    "임상": "clinical",
    "특허": "ip",
    "강세": "market_interest",
    "급등": "market_interest",
    "신고가": "market_interest",
    "정부": "policy",
    "정책": "policy",
    "지원": "policy",
    "예산": "policy",
    "ai": "theme_ai",
    "반도체": "theme_semiconductor",
    "2차전지": "theme_battery",
    "배터리": "theme_battery",
    "로봇": "theme_robot",
    "방산": "theme_defense",
    "원전": "theme_nuclear",
    "바이오": "theme_bio",
    "조선": "theme_shipbuilding",
    "전력": "theme_power",
    "전기차": "theme_ev",
    "ess": "theme_ess",
}

RISK_NEWS_KEYWORDS = {
    "소송": "legal_risk",
    "압수수색": "legal_risk",
    "횡령": "governance_risk",
    "배임": "governance_risk",
    "거래정지": "trading_halt",
    "관리종목": "market_warning",
    "상장폐지": "delisting_risk",
    "불성실": "disclosure_risk",
    "감자": "capital_action_risk",
    "유상증자": "dilution_risk",
    "전환사채": "dilution_risk",
    "cb": "dilution_risk",
    "적자": "earnings_risk",
    "하락": "price_risk",
    "급락": "price_risk",
    "매도": "sell_pressure",
    "규제": "policy_risk",
}


def _json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    return {}


def _nested_dict(source: Any, *keys: str) -> Dict[str, Any]:
    current: Any = source
    for key in keys:
        current = _json_dict(current)
        if not current:
            return {}
        current = current.get(key)
    return _json_dict(current)


def _first_dict(*values: Any) -> Dict[str, Any]:
    for value in values:
        parsed = _json_dict(value)
        if parsed:
            return parsed
    return {}


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            continue
        if isinstance(value, str):
            text = value.strip()
            if text and text.lower() not in {"none", "null", "nan", "-", "unclassified"}:
                return text
            continue
        if value != "":
            return value
    return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
    except Exception:
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return round(numeric, 4)


def _text_list(value: Any, *, limit: int = 8) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        source = list(value)
    else:
        text = str(value).strip()
        if not text or text.lower() in {"none", "null", "nan", "-"}:
            return []
        source = re.split(r"[,/|]", text)
    out: List[str] = []
    for item in source:
        text = str(item).strip()
        if text and text.lower() not in {"none", "null", "nan", "-"} and text not in out:
            out.append(text)
        if len(out) >= max(int(limit or 0), 0):
            break
    return out


def extract_kis_sidecar(row: Mapping[str, Any], trace: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    source = _json_dict(row)
    trace_source = _json_dict(trace)
    snapshot = _json_dict(source.get("feature_snapshot"))
    trace_snapshot = _json_dict(trace_source.get("feature_snapshot"))
    return _first_dict(
        source.get("_kis_sidecar"),
        source.get("kis_sidecar"),
        _nested_dict(source, "_leader_metrics", "kis_sidecar"),
        _nested_dict(source, "leader_metrics", "kis_sidecar"),
        snapshot.get("kis_sidecar"),
        snapshot.get("_kis_sidecar"),
        _nested_dict(snapshot, "_leader_metrics", "kis_sidecar"),
        _nested_dict(snapshot, "leader_metrics", "kis_sidecar"),
        trace_source.get("_kis_sidecar"),
        trace_source.get("kis_sidecar"),
        _nested_dict(trace_source, "_leader_metrics", "kis_sidecar"),
        _nested_dict(trace_source, "leader_metrics", "kis_sidecar"),
        trace_snapshot.get("kis_sidecar"),
        trace_snapshot.get("_kis_sidecar"),
        _nested_dict(trace_snapshot, "_leader_metrics", "kis_sidecar"),
        _nested_dict(trace_snapshot, "leader_metrics", "kis_sidecar"),
    )


def extract_kis_prefilter(row: Mapping[str, Any], trace: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    source = _json_dict(row)
    trace_source = _json_dict(trace)
    snapshot = _json_dict(source.get("feature_snapshot"))
    trace_snapshot = _json_dict(trace_source.get("feature_snapshot"))
    return _first_dict(
        source.get("kis_operational_prefilter"),
        snapshot.get("kis_operational_prefilter"),
        trace_source.get("kis_operational_prefilter"),
        trace_snapshot.get("kis_operational_prefilter"),
    )


def _extract_theme_context(row: Mapping[str, Any], trace: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    source = _json_dict(row)
    trace_source = _json_dict(trace)
    snapshot = _json_dict(source.get("feature_snapshot"))
    trace_snapshot = _json_dict(trace_source.get("feature_snapshot"))
    theme = _first_dict(
        source.get("theme_context"),
        source.get("_theme_context"),
        source.get("theme"),
        snapshot.get("theme_context"),
        trace_source.get("theme_context"),
        trace_source.get("_theme_context"),
        trace_source.get("theme"),
        trace_snapshot.get("theme_context"),
    )
    primary = _first_present(
        theme.get("primary_theme"),
        source.get("primary_theme"),
        source.get("테마"),
        source.get("Theme"),
        trace_source.get("primary_theme"),
        trace_source.get("테마"),
        trace_source.get("Theme"),
    )
    if primary:
        theme.setdefault("primary_theme", primary)
    source_name = _first_present(
        theme.get("theme_source"),
        source.get("theme_source"),
        trace_source.get("theme_source"),
        snapshot.get("theme_source"),
        trace_snapshot.get("theme_source"),
    )
    if source_name:
        theme.setdefault("theme_source", source_name)
    routing_path = _first_present(
        theme.get("routing_path"),
        theme.get("theme_routing_path"),
        source.get("routing_path"),
        source.get("theme_routing_path"),
        trace_source.get("routing_path"),
        trace_source.get("theme_routing_path"),
    )
    if routing_path:
        theme.setdefault("theme_routing_path", routing_path)
    return theme


def _extract_news_rows(news_contract: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = news_contract.get("rows") if isinstance(news_contract.get("rows"), list) else []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        title = _first_present(
            row.get("title"),
            row.get("hts_pbnt_titl_cntt"),
            row.get("headline"),
            row.get("news_title"),
            row.get("pbnt_titl_cntt"),
            row.get("stck_ntby_titl"),
        )
        if not title:
            continue
        date_value = _first_present(row.get("date"), row.get("data_dt"), row.get("pbnt_dt"))
        time_value = _first_present(row.get("time"), row.get("data_tm"), row.get("pbnt_tm"))
        out.append(
            {
                "title": str(title),
                "source": str(_first_present(row.get("source"), row.get("dorg"), row.get("news_ofer_entp_code"), "KIS")),
                "date": str(date_value) if date_value else None,
                "time": str(time_value) if time_value else None,
                "url": row.get("url"),
                "symbol": _first_present(
                    row.get("symbol"),
                    row.get("ticker"),
                    row.get("pdno"),
                    row.get("stck_shrn_iscd"),
                    row.get("mksc_shrn_iscd"),
                    row.get("stock_code"),
                    row.get("iscd1"),
                ),
                "stock_name": _first_present(
                    row.get("stock_name"),
                    row.get("hts_kor_isnm"),
                    row.get("prdt_name"),
                    row.get("name"),
                    row.get("kor_isnm1"),
                ),
            }
        )
    return out


def _news_scope_from_contract(
    *,
    ticker: str,
    stock_name: str = "",
    news_contract: Mapping[str, Any],
    news_rows: Iterable[Mapping[str, Any]],
    news_checked: bool,
    news_count: int,
) -> Dict[str, Any]:
    existing = _json_dict(news_contract.get("source_scope_metadata"))
    if existing and existing.get("source_scope"):
        return existing
    raw_rows = news_contract.get("rows") if isinstance(news_contract.get("rows"), list) else list(news_rows)
    return classify_kis_news_source_scope(
        symbol=ticker,
        stock_name=stock_name,
        rows=raw_rows,
        checked=news_checked,
        news_count=news_count,
    )


def _classify_news_titles(titles: Iterable[str]) -> Dict[str, Any]:
    positive: List[str] = []
    risk: List[str] = []
    matched_keywords: List[str] = []
    for title in titles:
        lower = str(title or "").lower()
        for keyword, tag in POSITIVE_NEWS_KEYWORDS.items():
            if keyword.lower() in lower and tag not in positive:
                positive.append(tag)
                matched_keywords.append(keyword)
        for keyword, tag in RISK_NEWS_KEYWORDS.items():
            if keyword.lower() in lower and tag not in risk:
                risk.append(tag)
                matched_keywords.append(keyword)
    return {
        "positive_tags": positive[:12],
        "risk_tags": risk[:12],
        "matched_keywords": list(dict.fromkeys(matched_keywords))[:20],
    }


def _rank_snapshot(prefilter: Mapping[str, Any], sidecar: Mapping[str, Any]) -> Dict[str, Any]:
    rank = _json_dict(prefilter.get("rank"))
    rank_contract = _json_dict(sidecar.get("rank_contract"))
    model_features = _json_dict(sidecar.get("model_candidate_features"))
    sources = _text_list(prefilter.get("sources"), limit=8)
    return {
        "prefilter_sources": sources,
        "selection_score": _safe_float(prefilter.get("selection_score")),
        "volume_rank": _safe_float(_first_present(rank.get("volume_rank"), rank_contract.get("volume_rank"), model_features.get("kis_rank_volume"))),
        "fluctuation_rank": _safe_float(
            _first_present(rank.get("fluctuation_rank"), rank_contract.get("fluctuation_rank"), model_features.get("kis_rank_fluctuation"))
        ),
        "volume_power_rank": _safe_float(
            _first_present(rank.get("volume_power_rank"), rank_contract.get("volume_power_rank"), model_features.get("kis_rank_volume_power"))
        ),
        "vi_triggered": bool(_first_present(prefilter.get("vi_triggered"), _nested_dict(sidecar, "vi_contract").get("triggered"))),
        "quote_ok": bool(prefilter.get("quote_ok")) if "quote_ok" in prefilter else None,
        "flow_ok": bool(prefilter.get("flow_ok")) if "flow_ok" in prefilter else None,
    }


def build_kis_theme_news_evidence(
    row: Mapping[str, Any],
    *,
    trace: Optional[Mapping[str, Any]] = None,
    market: str = "",
    theme_master: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic KIS-backed theme/news evidence contract.

    The function only reads real payloads already present in scanner rows,
    feature snapshots, top-deep reports, or planner traces. It does not call KIS
    or synthesize missing API data.
    """

    source = _json_dict(row)
    trace_source = _json_dict(trace)
    sidecar = extract_kis_sidecar(source, trace_source)
    prefilter = extract_kis_prefilter(source, trace_source)
    theme_context = _extract_theme_context(source, trace_source)
    theme_master_dict = _json_dict(theme_master)
    stock_info = _json_dict(sidecar.get("stock_info_contract"))
    model_features = _json_dict(sidecar.get("model_candidate_features"))
    coverage = _json_dict(sidecar.get("coverage"))
    news_contract = _json_dict(sidecar.get("news_contract"))
    news_rows = _extract_news_rows(news_contract)
    news_classification = _classify_news_titles(row.get("title") for row in news_rows)

    primary_theme = _first_present(
        theme_context.get("primary_theme"),
        source.get("primary_theme"),
        trace_source.get("primary_theme"),
        theme_master_dict.get("primary_theme"),
    )
    secondary_themes = _text_list(
        _first_present(
            theme_context.get("secondary_themes"),
            source.get("secondary_themes"),
            trace_source.get("secondary_themes"),
            theme_master_dict.get("secondary_themes"),
        ),
        limit=6,
    )
    kis_sector = _first_present(
        stock_info.get("sector_name"),
        stock_info.get("large_sector_name"),
        stock_info.get("mid_sector_name"),
        model_features.get("kis_stock_sector_name"),
    )
    standard_industry_code = _first_present(
        stock_info.get("standard_industry_code"),
        model_features.get("kis_stock_standard_industry_code"),
    )
    rank = _rank_snapshot(prefilter, sidecar)

    source_names: List[str] = []
    if sidecar:
        source_names.append("kis_sidecar")
    if prefilter:
        source_names.append("kis_operational_prefilter")
    if news_contract.get("checked"):
        source_names.append("kis_news_title")
    if stock_info.get("checked") or stock_info:
        source_names.append("kis_stock_info")
    if theme_context:
        source_names.append("theme_context")
    if theme_master_dict:
        source_names.append("kr_stock_theme_master")
    source_names = list(dict.fromkeys(source_names))

    kis_backed = bool(
        sidecar
        or prefilter
        or news_contract.get("checked")
        or stock_info.get("checked")
        or str(source.get("feature_origin") or "").startswith("kis_openapi")
    )
    news_checked = bool(news_contract.get("checked"))
    news_count = int(_safe_float(news_contract.get("news_count")) or len(news_rows) or 0)
    ticker = str(_first_present(source.get("ticker"), source.get("Ticker"), source.get("티커"), trace_source.get("ticker"), ""))
    stock_name = str(
        _first_present(
            stock_info.get("product_name"),
            source.get("stock_name"),
            source.get("name"),
            source.get("종목명"),
            trace_source.get("stock_name"),
            trace_source.get("name"),
            "",
        )
    )
    news_scope = _news_scope_from_contract(
        ticker=ticker,
        stock_name=stock_name,
        news_contract=news_contract,
        news_rows=news_rows,
        news_checked=news_checked,
        news_count=news_count,
    )
    news_promotion_blocked = bool(news_scope.get("promotion_blocked")) and news_checked and news_count > 0

    score = 0.0
    if kis_backed:
        score += 15.0
    if news_checked:
        score += 15.0
    score += min(20.0, float(news_count) * 4.0)
    if kis_sector:
        score += 15.0
    if standard_industry_code:
        score += 5.0
    if primary_theme:
        score += 10.0
    if rank.get("prefilter_sources"):
        score += 10.0
    if rank.get("vi_triggered"):
        score += 5.0
    if rank.get("selection_score") is not None:
        score += 5.0
    if news_classification["risk_tags"]:
        score = max(0.0, score - min(20.0, 5.0 * len(news_classification["risk_tags"])))
    if news_promotion_blocked:
        score = min(score, 60.0)
    score = round(min(100.0, score), 2)
    if score >= 70:
        strength = "strong"
    elif score >= 45:
        strength = "medium"
    elif score > 0:
        strength = "weak"
    else:
        strength = "missing"

    drivers: List[str] = []
    if news_checked:
        drivers.append(f"KIS 뉴스 {news_count}건")
    if kis_sector:
        drivers.append(f"KIS 업종 {kis_sector}")
    if primary_theme:
        drivers.append(f"테마 {primary_theme}")
    if rank.get("prefilter_sources"):
        drivers.append("KIS 랭킹 " + ",".join(rank["prefilter_sources"][:3]))
    if rank.get("vi_triggered"):
        drivers.append("KIS VI 포착")
    if news_classification["positive_tags"] and not news_promotion_blocked:
        drivers.append("뉴스 긍정태그 " + ",".join(news_classification["positive_tags"][:3]))

    warnings: List[str] = []
    if sidecar and not coverage.get("news_titles"):
        warnings.append("kis_news_titles_not_checked")
    if sidecar and not coverage.get("stock_info"):
        warnings.append("kis_stock_info_missing")
    if not kis_backed and primary_theme:
        warnings.append("theme_context_not_kis_backed")
    if news_classification["risk_tags"]:
        warnings.append("kis_news_risk_tags:" + ",".join(news_classification["risk_tags"][:4]))
    if news_contract.get("rows_truncated"):
        warnings.append("kis_news_rows_truncated")
    warnings.extend(news_scope.get("warnings") or [])
    promotion_blocking_reasons = list(news_scope.get("promotion_blocking_reasons") or [])
    if news_promotion_blocked:
        if not promotion_blocking_reasons:
            promotion_blocking_reasons.append(KIS_NEWS_SCOPE_AMBIGUOUS_BLOCK_REASON)
        if promotion_blocking_reasons[0] == KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON:
            warnings.append("kis_news_scope_market_wide")
        else:
            warnings.append("kis_news_scope_ambiguous")

    return {
        "contract_version": KIS_THEME_NEWS_EVIDENCE_VERSION,
        "available": bool(kis_backed or primary_theme or news_checked or kis_sector),
        "kis_backed": kis_backed,
        "ticker": ticker,
        "market": str(_first_present(market, source.get("market"), source.get("Market"), trace_source.get("market"), "")),
        "sources_present": source_names,
        "evidence_strength_score": score,
        "evidence_strength_level": strength,
        "promotion_blocked": news_promotion_blocked,
        "promotion_block_reason": promotion_blocking_reasons[0] if promotion_blocking_reasons else None,
        "promotion_blocking_reasons": promotion_blocking_reasons,
        "theme": {
            "primary_theme": primary_theme,
            "secondary_themes": secondary_themes,
            "theme_source": _first_present(theme_context.get("theme_source"), theme_master_dict.get("source_theme_reference")),
            "theme_routing_path": _first_present(theme_context.get("theme_routing_path"), theme_context.get("routing_path")),
            "kis_sector_name": kis_sector,
            "kis_standard_industry_code": standard_industry_code,
            "kis_market_name": _first_present(stock_info.get("market_name"), model_features.get("kis_stock_market_name")),
            "kis_stock_type": _first_present(stock_info.get("stock_type"), model_features.get("kis_stock_type")),
        },
        "news": {
            "checked": news_checked,
            "source_status": news_contract.get("source_status") or ("not_requested" if not news_checked else "ok"),
            "news_count": news_count,
            "raw_news_count": _safe_float(news_contract.get("raw_news_count")),
            "rows_filtered_out_count": _safe_float(news_contract.get("rows_filtered_out_count")),
            "rows_stored_count": len(news_rows),
            "headlines": news_rows[:5],
            "source_scope_filter_applied": bool(news_contract.get("source_scope_filter_applied")),
            "source_scope_filter_policy": news_contract.get("source_scope_filter_policy"),
            "source_scope": news_scope.get("source_scope"),
            "source_scope_confidence": news_scope.get("source_scope_confidence"),
            "source_scope_metadata": news_scope,
            "promotion_blocked": news_promotion_blocked,
            "promotion_block_reason": promotion_blocking_reasons[0] if promotion_blocking_reasons else None,
            **news_classification,
        },
        "market_action": rank,
        "drivers": drivers[:10],
        "warnings": list(dict.fromkeys(warnings))[:10],
        "no_dummy_data": True,
    }


def format_kis_theme_news_summary(evidence: Mapping[str, Any], *, max_headlines: int = 1) -> str:
    payload = _json_dict(evidence)
    if not payload or not payload.get("available") or not payload.get("kis_backed"):
        return ""
    theme = _json_dict(payload.get("theme"))
    news = _json_dict(payload.get("news"))
    action = _json_dict(payload.get("market_action"))
    parts = [
        f"{payload.get('evidence_strength_level') or '-'} {_safe_float(payload.get('evidence_strength_score')) or 0:.0f}점",
    ]
    theme_label = _first_present(theme.get("primary_theme"), theme.get("kis_sector_name"))
    if theme_label:
        sector = f"/{theme.get('kis_sector_name')}" if theme.get("kis_sector_name") and theme.get("kis_sector_name") != theme_label else ""
        parts.append(f"테마 {theme_label}{sector}")
    if news.get("checked"):
        parts.append(f"뉴스 {news.get('news_count') or 0}건")
        if news.get("source_scope") and news.get("source_scope") not in {"symbol_specific", "empty"}:
            parts.append(f"뉴스범위 {news.get('source_scope')}")
    if action.get("vi_triggered"):
        parts.append("VI")
    if action.get("prefilter_sources"):
        parts.append("랭킹 " + ",".join(action["prefilter_sources"][:2]))
    headlines = []
    for row in news.get("headlines") or []:
        if isinstance(row, Mapping) and row.get("title"):
            headlines.append(str(row["title"]))
        if len(headlines) >= max(0, int(max_headlines or 0)):
            break
    if headlines:
        parts.append("뉴스: " + " / ".join(headlines))
    warnings = _text_list(payload.get("warnings"), limit=2)
    if warnings:
        parts.append("경고 " + ",".join(warnings))
    return " · ".join(str(part) for part in parts if str(part).strip())


__all__ = [
    "KIS_THEME_NEWS_EVIDENCE_VERSION",
    "build_kis_theme_news_evidence",
    "extract_kis_prefilter",
    "extract_kis_sidecar",
    "format_kis_theme_news_summary",
]
