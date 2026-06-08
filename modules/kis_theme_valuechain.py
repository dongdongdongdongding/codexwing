from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from modules.kis_openapi import normalize_kr_stock_code
from modules.kis_theme_news_evidence import build_kis_theme_news_evidence, extract_kis_sidecar
from modules.live_scan_context import normalize_market_key


KIS_THEME_VALUECHAIN_VERSION = "kis_theme_valuechain_v1"
VALUECHAIN_CONFIDENCE_FLOOR = 0.95
VALUECHAIN_DIR = Path("runtime_state/long_term/kis_theme_valuechain")
VALUECHAIN_REPORT_DIR = Path("runtime_state/reports/kis_theme_valuechain")

TRUSTED_VALUECHAIN_SOURCE_TYPES = {
    "regulatory_filing": 0.99,
    "exchange_disclosure": 0.99,
    "contract_disclosure": 0.99,
    "official_company": 0.97,
    "company_ir": 0.97,
    "government": 0.96,
}
UNVERIFIED_VALUECHAIN_SOURCE_TYPES = {
    "news": 0.88,
    "media": 0.86,
    "research": 0.9,
    "broker_report": 0.9,
    "web_search": 0.82,
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return round(numeric, 6)


def _safe_int(value: Any) -> int | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _date_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", text[:10]):
        return text[:10]
    if len(text) >= 8 and re.match(r"\d{8}", text[:8]):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text[:10]


def _ticker(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    code = normalize_kr_stock_code(text)
    if code:
        if ".KQ" in text:
            return f"{code}.KQ"
        if ".KS" in text:
            return f"{code}.KS"
        return code
    return text


def _market_scope(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip().upper()
        if not text:
            continue
        if text in {"KOSPI", "KS", "STK", "유가", "유가증권"}:
            return "KOSPI"
        if text in {"KOSDAQ", "KQ", "KSQ", "코스닥"}:
            return "KOSDAQ"
        if text.endswith(".KS"):
            return "KOSPI"
        if text.endswith(".KQ"):
            return "KOSDAQ"
        if text in {"KR", "KOREA"}:
            return "KR"
    return ""


def _valuechain_storage_key(market: str) -> str:
    scope = _market_scope(market)
    if scope in {"KOSPI", "KOSDAQ", "KR"}:
        return scope
    return normalize_market_key(market)


def _node_id(node_type: str, key: Any) -> str:
    text = re.sub(r"\s+", "_", str(key or "").strip())
    return f"{node_type}:{text}" if text else ""


def _text_list(value: Any, *, limit: int = 12) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        source = list(value)
    elif value is None:
        source = []
    else:
        source = re.split(r"[,/|]", str(value))
    out: List[str] = []
    for item in source:
        text = str(item or "").strip()
        if text and text.lower() not in {"none", "null", "nan", "-"} and text not in out:
            out.append(text)
        if len(out) >= max(0, int(limit or 0)):
            break
    return out


def _theme_evidence(row: Mapping[str, Any], sidecar: Mapping[str, Any]) -> Dict[str, Any]:
    source = _json_dict(row)
    snapshot = _json_dict(source.get("feature_snapshot"))
    evidence = _json_dict(source.get("kis_theme_news_evidence")) or _json_dict(snapshot.get("kis_theme_news_evidence"))
    if evidence:
        return evidence
    if sidecar:
        try:
            return build_kis_theme_news_evidence(source)
        except Exception:
            return {}
    return {}


def extract_kis_ticker_category_record(row: Mapping[str, Any]) -> Dict[str, Any]:
    source = _json_dict(row)
    snapshot = _json_dict(source.get("feature_snapshot"))
    sidecar = extract_kis_sidecar(source)
    stock = _json_dict(sidecar.get("stock_info_contract"))
    financial = _json_dict(sidecar.get("financial_ratio_contract"))
    model = _json_dict(sidecar.get("model_candidate_features"))
    news_contract = _json_dict(sidecar.get("news_contract"))
    evidence = _theme_evidence(source, sidecar)
    theme = _json_dict(evidence.get("theme"))
    news = _json_dict(evidence.get("news"))
    action = _json_dict(evidence.get("market_action"))

    ticker = _ticker(_first_present(source.get("ticker"), source.get("Ticker"), source.get("symbol"), stock.get("ticker")))
    market = _market_scope(
        source.get("market"),
        source.get("Market"),
        sidecar.get("market"),
        stock.get("market_name"),
        model.get("kis_stock_market_name"),
        ticker,
    ) or str(_first_present(source.get("market"), source.get("Market"), sidecar.get("market"), "") or "").upper()
    trade_date = _date_key(
        _first_present(
            source.get("base_trade_date"),
            source.get("recommended_at"),
            source.get("scanned_at"),
            source.get("created_at"),
            sidecar.get("generated_at"),
        )
    )
    primary_theme = str(
        _first_present(
            theme.get("primary_theme"),
            source.get("primary_theme"),
            snapshot.get("primary_theme"),
            source.get("테마"),
            "",
        )
        or ""
    )
    sector_name = str(
        _first_present(
            stock.get("sector_name"),
            stock.get("large_sector_name"),
            stock.get("mid_sector_name"),
            model.get("kis_stock_sector_name"),
            theme.get("kis_sector_name"),
            "",
        )
        or ""
    )
    news_count = _safe_int(_first_present(news.get("news_count"), news_contract.get("news_count"))) or 0
    raw_news_count = _safe_int(_first_present(news.get("raw_news_count"), news_contract.get("raw_news_count"))) or news_count

    return {
        "version": KIS_THEME_VALUECHAIN_VERSION,
        "ticker": ticker,
        "market": market,
        "market_scope": market,
        "market_key": normalize_market_key(market or ticker or "KR"),
        "trade_date": trade_date,
        "stock_name": str(_first_present(stock.get("product_name"), source.get("stock_name"), source.get("name"), ticker) or ""),
        "primary_theme": primary_theme,
        "secondary_themes": _text_list(theme.get("secondary_themes")),
        "theme_source": _first_present(theme.get("theme_source"), source.get("theme_source")),
        "theme_routing_path": _first_present(theme.get("theme_routing_path"), source.get("theme_routing_path")),
        "market_name": _first_present(stock.get("market_name"), model.get("kis_stock_market_name")),
        "market_code": _first_present(stock.get("market_code"), model.get("kis_stock_market_code")),
        "sector_name": sector_name,
        "standard_industry_code": _first_present(stock.get("standard_industry_code"), model.get("kis_stock_standard_industry_code")),
        "large_sector_name": stock.get("large_sector_name"),
        "mid_sector_name": stock.get("mid_sector_name"),
        "small_sector_name": stock.get("small_sector_name"),
        "stock_type": _first_present(stock.get("stock_type"), model.get("kis_stock_type")),
        "kospi200_item": _first_present(stock.get("kospi200_item"), model.get("kis_stock_kospi200_item")),
        "listed_date": _first_present(stock.get("listed_date"), model.get("kis_stock_listed_date")),
        "per": _safe_float(_first_present(financial.get("per"), model.get("kis_financial_per"), model.get("kis_per"))),
        "pbr": _safe_float(_first_present(financial.get("pbr"), model.get("kis_financial_pbr"), model.get("kis_pbr"))),
        "roe": _safe_float(_first_present(financial.get("roe"), model.get("kis_financial_roe"))),
        "debt_ratio": _safe_float(_first_present(financial.get("debt_ratio"), model.get("kis_financial_debt_ratio"))),
        "revenue_growth_rate": _safe_float(_first_present(financial.get("revenue_growth_rate"), model.get("kis_financial_revenue_growth_rate"))),
        "value_traded": _safe_float(_first_present(model.get("kis_value_traded"), source.get("value_traded"))),
        "day_return_pct": _safe_float(
            _first_present(source.get("day_return_pct"), source.get("day_change_pct"), model.get("kis_day_change_pct"))
        ),
        "volume_rank": _safe_float(_first_present(action.get("volume_rank"), model.get("kis_rank_volume"))),
        "fluctuation_rank": _safe_float(_first_present(action.get("fluctuation_rank"), model.get("kis_rank_fluctuation"))),
        "volume_power_rank": _safe_float(_first_present(action.get("volume_power_rank"), model.get("kis_rank_volume_power"))),
        "vi_triggered": bool(_first_present(action.get("vi_triggered"), model.get("kis_vi_triggered"))),
        "news_count": news_count,
        "raw_news_count": raw_news_count,
        "news_positive_tags": _text_list(news.get("positive_tags"), limit=16),
        "news_risk_tags": _text_list(news.get("risk_tags"), limit=16),
        "news_source_scope": _first_present(news.get("source_scope"), news_contract.get("source_scope")),
        "kis_evidence_strength_score": _safe_float(evidence.get("evidence_strength_score")),
        "kis_evidence_strength_level": evidence.get("evidence_strength_level"),
        "source_ref": _first_present(source.get("source_ref"), source.get("run_id"), sidecar.get("feature_origin")),
        "no_dummy_data": True,
    }


def extract_kis_ticker_category_records(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, str]] = set()
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        record = extract_kis_ticker_category_record(row)
        if not record.get("ticker"):
            continue
        key = (str(record.get("trade_date") or ""), str(record.get("market") or ""), str(record.get("ticker") or ""))
        if key in seen:
            continue
        seen.add(key)
        records.append(record)
    return records


def _record_matches_market(record: Mapping[str, Any], market: str) -> bool:
    scope = _market_scope(market)
    if not scope or scope == "KR":
        return normalize_market_key(str(record.get("market") or record.get("ticker") or "KR")) == "KR"
    if scope in {"KOSPI", "KOSDAQ"}:
        record_scope = _market_scope(record.get("market"), record.get("ticker"), record.get("market_scope"))
        return record_scope == scope
    return normalize_market_key(str(record.get("market") or record.get("ticker") or "")) == normalize_market_key(market)


def _style_bucket(record: Mapping[str, Any]) -> List[str]:
    tags: List[str] = []
    pbr = _safe_float(record.get("pbr"))
    per = _safe_float(record.get("per"))
    roe = _safe_float(record.get("roe"))
    debt = _safe_float(record.get("debt_ratio"))
    growth = _safe_float(record.get("revenue_growth_rate"))
    if pbr is not None and pbr <= 1.0:
        tags.append("value_low_pbr")
    if per is not None and 0 < per <= 12:
        tags.append("value_low_per")
    if roe is not None and roe >= 12:
        tags.append("quality_high_roe")
    if debt is not None and debt <= 60:
        tags.append("balance_low_debt")
    if growth is not None and growth >= 10:
        tags.append("growth_revenue")
    return tags


def _add_node(nodes: Dict[str, Dict[str, Any]], node_id: str, *, label: str, node_type: str, **extra: Any) -> None:
    if not node_id:
        return
    current = nodes.setdefault(node_id, {"id": node_id, "label": label, "type": node_type, "weight": 0.0})
    current["weight"] = round(float(current.get("weight") or 0.0) + float(extra.pop("weight", 1.0) or 1.0), 4)
    for key, value in extra.items():
        if value not in (None, "", []):
            current.setdefault(key, value)


def _edge_key(source: str, target: str, kind: str, relationship: str = "") -> Tuple[str, str, str, str]:
    return (source, target, kind, relationship)


def _add_edge(
    edges: Dict[Tuple[str, str, str, str], Dict[str, Any]],
    *,
    source: str,
    target: str,
    edge_kind: str,
    relationship: str,
    confidence: float,
    weight: float = 1.0,
    **extra: Any,
) -> None:
    if not source or not target or source == target:
        return
    key = _edge_key(source, target, edge_kind, relationship)
    current = edges.setdefault(
        key,
        {
            "source": source,
            "target": target,
            "edge_kind": edge_kind,
            "relationship": relationship,
            "confidence": round(float(confidence), 4),
            "weight": 0.0,
        },
    )
    current["weight"] = round(float(current.get("weight") or 0.0) + float(weight or 1.0), 4)
    current["confidence"] = round(max(float(current.get("confidence") or 0.0), float(confidence or 0.0)), 4)
    for key_name, value in extra.items():
        if value not in (None, "", []):
            if key_name == "evidence":
                merged = list(current.get("evidence") or [])
                for item in _text_list(value, limit=20):
                    if item not in merged:
                        merged.append(item)
                current["evidence"] = merged[:20]
            else:
                current.setdefault(key_name, value)


def _url_list(value: Any) -> List[str]:
    if isinstance(value, str):
        urls = [value.strip()]
    else:
        urls = _text_list(value, limit=10)
    return [url for url in urls if url.startswith("https://") or url.startswith("http://")]


def normalize_verified_valuechain_edge(edge: Mapping[str, Any], *, confidence_floor: float = VALUECHAIN_CONFIDENCE_FLOOR) -> Dict[str, Any]:
    source_type = str(edge.get("source_type") or edge.get("evidence_source_type") or "").strip().lower()
    source_urls = _url_list(edge.get("source_urls") or edge.get("source_url"))
    requested_confidence = _safe_float(edge.get("confidence"))
    default_confidence = TRUSTED_VALUECHAIN_SOURCE_TYPES.get(source_type, UNVERIFIED_VALUECHAIN_SOURCE_TYPES.get(source_type, 0.0))
    confidence = requested_confidence if requested_confidence is not None else default_confidence
    confidence = min(float(confidence or 0.0), float(default_confidence or 0.0))
    evidence_text = str(edge.get("evidence_text") or edge.get("evidence") or "").strip()
    blocked_reasons: List[str] = []
    if source_type not in TRUSTED_VALUECHAIN_SOURCE_TYPES:
        blocked_reasons.append("valuechain_source_type_not_95pct_trusted")
    if not source_urls:
        blocked_reasons.append("valuechain_source_url_missing")
    if len(evidence_text) < 12:
        blocked_reasons.append("valuechain_evidence_text_too_short")
    if confidence < float(confidence_floor):
        blocked_reasons.append("valuechain_confidence_below_95pct")

    from_symbol = _ticker(_first_present(edge.get("from_symbol"), edge.get("source_symbol"), edge.get("supplier_symbol")))
    to_symbol = _ticker(_first_present(edge.get("to_symbol"), edge.get("target_symbol"), edge.get("customer_symbol")))
    relationship = str(edge.get("relationship") or edge.get("relationship_type") or "valuechain").strip()
    theme_name = str(edge.get("theme") or edge.get("theme_name") or "").strip()
    normalized = {
        "edge_kind": "verified_valuechain",
        "source": _node_id("ticker", from_symbol),
        "target": _node_id("ticker", to_symbol),
        "from_symbol": from_symbol,
        "to_symbol": to_symbol,
        "relationship": relationship,
        "theme_name": theme_name or None,
        "confidence": round(float(confidence), 4),
        "source_type": source_type or None,
        "source_urls": source_urls,
        "source_title": edge.get("source_title"),
        "evidence_text": evidence_text,
        "evidence_collected_at": edge.get("evidence_collected_at") or _utcnow(),
        "production_valuechain": not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "no_dummy_data": True,
    }
    if not from_symbol or not to_symbol:
        normalized["production_valuechain"] = False
        normalized["blocked_reasons"] = list(dict.fromkeys([*blocked_reasons, "valuechain_endpoint_symbol_missing"]))
    return normalized


def build_theme_daily_state(records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for record in records or []:
        theme = str(record.get("primary_theme") or "").strip()
        if not theme:
            continue
        key = (str(record.get("trade_date") or ""), str(record.get("market") or ""), theme)
        grouped[key].append(record)

    rows: List[Dict[str, Any]] = []
    for (trade_date, market, theme), items in sorted(grouped.items()):
        returns = [_safe_float(row.get("day_return_pct")) for row in items]
        returns = [value for value in returns if value is not None]
        values = [_safe_float(row.get("value_traded")) or 0.0 for row in items]
        evidence_scores = [_safe_float(row.get("kis_evidence_strength_score")) for row in items]
        evidence_scores = [value for value in evidence_scores if value is not None]
        positive = sum(1 for value in returns if value > 0)
        rows.append(
            {
                "trade_date": trade_date,
                "market": market,
                "theme_name": theme,
                "symbol_count": len(items),
                "avg_day_return_pct": round(sum(returns) / len(returns), 4) if returns else None,
                "positive_return_ratio": round(positive / len(returns), 4) if returns else None,
                "total_value_traded": round(sum(values), 4),
                "news_count": sum(int(row.get("news_count") or 0) for row in items),
                "vi_triggered_count": sum(1 for row in items if row.get("vi_triggered")),
                "avg_kis_evidence_strength_score": round(sum(evidence_scores) / len(evidence_scores), 4) if evidence_scores else None,
                "top_symbols": sorted(
                    [
                        {
                            "ticker": row.get("ticker"),
                            "stock_name": row.get("stock_name"),
                            "day_return_pct": row.get("day_return_pct"),
                            "value_traded": row.get("value_traded"),
                        }
                        for row in items
                    ],
                    key=lambda row: float(row.get("value_traded") or 0.0),
                    reverse=True,
                )[:8],
                "no_dummy_data": True,
            }
        )
    return rows


def build_kis_theme_valuechain_payload(
    rows: Iterable[Mapping[str, Any]],
    *,
    verified_valuechain_sources: Optional[Iterable[Mapping[str, Any]]] = None,
    ticker_valuechain_master: Optional[Mapping[str, Any]] = None,
    market: str = "KR",
    confidence_floor: float = VALUECHAIN_CONFIDENCE_FLOOR,
) -> Dict[str, Any]:
    records = [record for record in extract_kis_ticker_category_records(rows) if _record_matches_market(record, market)]
    generated_at = _utcnow()
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    warnings: List[str] = []

    for record in records:
        ticker_id = _node_id("ticker", record.get("ticker"))
        _add_node(
            nodes,
            ticker_id,
            label=str(record.get("stock_name") or record.get("ticker")),
            node_type="ticker",
            ticker=record.get("ticker"),
            market=record.get("market"),
            theme=record.get("primary_theme"),
            sector=record.get("sector_name"),
            day_return_pct=record.get("day_return_pct"),
            weight=1.0 + max(0.0, min(4.0, float(record.get("news_count") or 0) * 0.25)),
        )
        theme = str(record.get("primary_theme") or "").strip()
        if theme:
            theme_id = _node_id("theme", theme)
            _add_node(nodes, theme_id, label=theme, node_type="theme", weight=2.0)
            _add_edge(
                edges,
                source=theme_id,
                target=ticker_id,
                edge_kind="theme_membership",
                relationship="theme_contains_ticker",
                confidence=min(0.94, 0.65 + float(record.get("kis_evidence_strength_score") or 0.0) / 300.0),
                weight=1.0 + float(record.get("news_count") or 0) * 0.2,
                evidence=[str(record.get("theme_source") or "kis_theme_news_evidence")],
            )
        sector = str(record.get("sector_name") or "").strip()
        if sector:
            sector_id = _node_id("sector", sector)
            _add_node(nodes, sector_id, label=sector, node_type="sector", weight=1.5)
            _add_edge(
                edges,
                source=sector_id,
                target=ticker_id,
                edge_kind="kis_category_membership",
                relationship="sector_contains_ticker",
                confidence=0.9,
                weight=1.0,
                evidence=["kis_stock_info.sector_name"],
            )
        for tag in _style_bucket(record):
            style_id = _node_id("style", tag)
            _add_node(nodes, style_id, label=tag, node_type="style", weight=0.8)
            _add_edge(
                edges,
                source=style_id,
                target=ticker_id,
                edge_kind="kis_style_membership",
                relationship="style_contains_ticker",
                confidence=0.86,
                weight=0.6,
                evidence=["kis_financial_ratio"],
            )
        for tag in _text_list(record.get("news_positive_tags"), limit=8):
            event_id = _node_id("event", tag)
            _add_node(nodes, event_id, label=tag, node_type="event", weight=0.7)
            _add_edge(
                edges,
                source=event_id,
                target=ticker_id,
                edge_kind="kis_news_event",
                relationship="news_event_mentions_ticker",
                confidence=0.82,
                weight=0.5,
                evidence=["kis_news_titles_strict_symbol_filter"],
            )

    verified_edges: List[Dict[str, Any]] = []
    blocked_edges: List[Dict[str, Any]] = []
    static_master = dict(ticker_valuechain_master or {})
    static_master_edges = static_master.get("edges") if isinstance(static_master.get("edges"), list) else []
    valuechain_sources = static_master_edges or list(verified_valuechain_sources or [])
    for raw_edge in valuechain_sources:
        if not isinstance(raw_edge, Mapping):
            continue
        normalized = normalize_verified_valuechain_edge(raw_edge, confidence_floor=confidence_floor)
        if normalized.get("production_valuechain"):
            verified_edges.append(normalized)
            for endpoint_key, symbol_key in (("source", "from_symbol"), ("target", "to_symbol")):
                node_id = str(normalized.get(endpoint_key) or "")
                if node_id and node_id not in nodes:
                    _add_node(nodes, node_id, label=str(normalized.get(symbol_key) or node_id), node_type="ticker")
            _add_edge(
                edges,
                source=str(normalized.get("source") or ""),
                target=str(normalized.get("target") or ""),
                edge_kind="verified_valuechain",
                relationship=str(normalized.get("relationship") or "valuechain"),
                confidence=float(normalized.get("confidence") or 0.0),
                weight=2.5,
                source_type=normalized.get("source_type"),
                source_urls=normalized.get("source_urls"),
                evidence=[normalized.get("evidence_text")],
                production_valuechain=True,
            )
        else:
            blocked_edges.append(normalized)

    if not verified_edges:
        warnings.append("verified_valuechain_edges_empty_requires_official_web_or_disclosure_evidence")
    source_distribution = Counter(str(row.get("source_type") or "unknown") for row in verified_edges)
    timeline = build_theme_daily_state(records)
    ticker_profiles = [
        dict(row)
        for row in (static_master.get("ticker_profiles") or [])
        if isinstance(row, Mapping)
    ]
    payload = {
        "version": KIS_THEME_VALUECHAIN_VERSION,
        "generated_at": generated_at,
        "market": _valuechain_storage_key(market),
        "market_region": normalize_market_key(market),
        "market_scope": _valuechain_storage_key(market),
        "confidence_floor": float(confidence_floor),
        "no_dummy_data": True,
        "source_policy": {
            "production_valuechain_requires_confidence_gte": float(confidence_floor),
            "trusted_source_types": TRUSTED_VALUECHAIN_SOURCE_TYPES,
            "unverified_source_type_caps": UNVERIFIED_VALUECHAIN_SOURCE_TYPES,
            "news_only_edges_blocked_from_production_valuechain": True,
        },
        "summary": {
            "ticker_category_records": len(records),
            "ticker_valuechain_profiles": len(ticker_profiles),
            "nodes": len(nodes),
            "edges": len(edges),
            "verified_valuechain_edges": len(verified_edges),
            "blocked_valuechain_edges": len(blocked_edges),
            "theme_daily_state_rows": len(timeline),
            "markets": dict(Counter(str(row.get("market") or "") for row in records)),
            "themes": dict(Counter(str(row.get("primary_theme") or "") for row in records if row.get("primary_theme"))),
            "verified_valuechain_source_distribution": dict(source_distribution),
            "ticker_valuechain_role_distribution": (
                dict(static_master.get("summary", {}).get("role_distribution") or {})
                if isinstance(static_master.get("summary"), Mapping)
                else {}
            ),
        },
        "ticker_valuechain_master": {
            "version": static_master.get("version"),
            "generated_at": static_master.get("generated_at"),
            "refresh_policy": static_master.get("refresh_policy") or {},
            "summary": static_master.get("summary") or {},
        },
        "ticker_valuechain_profiles": ticker_profiles,
        "ticker_category_records": records,
        "theme_daily_state": timeline,
        "nodes": sorted(nodes.values(), key=lambda row: (str(row.get("type") or ""), str(row.get("label") or ""))),
        "edges": sorted(edges.values(), key=lambda row: (str(row.get("edge_kind") or ""), str(row.get("source") or ""), str(row.get("target") or ""))),
        "verified_valuechain_edges": verified_edges,
        "blocked_valuechain_edges": blocked_edges,
        "warnings": warnings,
    }
    return payload


def kis_theme_valuechain_path(market: str = "KR") -> Path:
    market_key = _valuechain_storage_key(market)
    VALUECHAIN_DIR.mkdir(parents=True, exist_ok=True)
    return VALUECHAIN_DIR / f"{market_key}.json"


def write_kis_theme_valuechain_payload(payload: Mapping[str, Any], *, market: str = "KR") -> Path:
    path = kis_theme_valuechain_path(market or str(payload.get("market") or "KR"))
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_kis_theme_valuechain_payload(market: str = "KR") -> Dict[str, Any]:
    path = kis_theme_valuechain_path(market)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


__all__ = [
    "KIS_THEME_VALUECHAIN_VERSION",
    "TRUSTED_VALUECHAIN_SOURCE_TYPES",
    "UNVERIFIED_VALUECHAIN_SOURCE_TYPES",
    "VALUECHAIN_CONFIDENCE_FLOOR",
    "build_kis_theme_valuechain_payload",
    "build_theme_daily_state",
    "extract_kis_ticker_category_record",
    "extract_kis_ticker_category_records",
    "kis_theme_valuechain_path",
    "load_kis_theme_valuechain_payload",
    "normalize_verified_valuechain_edge",
    "write_kis_theme_valuechain_payload",
]
