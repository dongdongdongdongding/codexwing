from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional


KIS_NEWS_SCOPE_VERSION = "kis_news_scope_v1"
KIS_NEWS_SCOPE_FILTER_POLICY = "strict_symbol_or_stock_name_row_filter_v1"
KIS_NEWS_SCOPE_AMBIGUOUS_BLOCK_REASON = "KIS_NEWS_SCOPE_AMBIGUOUS"
KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON = "KIS_NEWS_SCOPE_MARKET_WIDE"

_SYMBOL_FIELDS = (
    "pdno",
    "PDNO",
    "stck_shrn_iscd",
    "mksc_shrn_iscd",
    "isu_cd",
    "item_code",
    "stock_code",
    "symbol",
    "ticker",
    "code",
    *(f"iscd{idx}" for idx in range(1, 11)),
)
_NAME_FIELDS = (
    "hts_kor_isnm",
    "prdt_name",
    "prdt_abrv_name",
    "stock_name",
    "kor_isnm",
    "isu_nm",
    "name",
    *(f"kor_isnm{idx}" for idx in range(1, 11)),
)
_TITLE_FIELDS = (
    "title",
    "hts_pbnt_titl_cntt",
    "headline",
    "news_title",
    "pbnt_titl_cntt",
    "stck_ntby_titl",
)
_BODY_FIELDS = ("body", "content", "news_body", "article", "summary")


def normalize_kr_news_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    text = text.split(".")[0]
    if text.startswith("A") and len(text) >= 7:
        text = text[1:]
    digits = re.sub(r"\D", "", text)
    if not digits:
        return ""
    return digits[-6:].zfill(6)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", "", _text(value)).lower()


def _row_symbols(row: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for field in _SYMBOL_FIELDS:
        symbol = normalize_kr_news_symbol(row.get(field))
        if symbol and symbol not in out:
            out.append(symbol)
    return out


def _row_text(row: Mapping[str, Any], fields: Iterable[str]) -> str:
    return " ".join(_text(row.get(field)) for field in fields if _text(row.get(field)))


def _row_title(row: Mapping[str, Any]) -> str:
    return _row_text(row, _TITLE_FIELDS)


def _mentions_symbol(text: str, symbol: str) -> bool:
    if not symbol:
        return False
    normalized = normalize_kr_news_symbol(text)
    if normalized == symbol:
        return True
    return symbol in re.sub(r"\D", "", str(text or ""))


def _mentions_name(text: str, name: str) -> bool:
    needle = _compact_text(name)
    if len(needle) < 2:
        return False
    return needle in _compact_text(text)


def _rows(value: Optional[Iterable[Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in value or []:
        if isinstance(row, Mapping):
            out.append(dict(row))
    return out


def kis_news_row_matches_symbol(
    row: Mapping[str, Any],
    *,
    symbol: str = "",
    stock_name: str = "",
) -> bool:
    """Return whether one KIS news row proves relevance to the requested stock."""

    if not isinstance(row, Mapping):
        return False
    requested_symbol = normalize_kr_news_symbol(symbol)
    requested_name = _text(stock_name)
    row_symbols = _row_symbols(row)
    if row_symbols:
        return bool(requested_symbol and requested_symbol in row_symbols)

    title_body = " ".join(part for part in (_row_title(row), _row_text(row, _BODY_FIELDS)) if part)
    name_text = " ".join(part for part in (_row_text(row, _NAME_FIELDS), title_body) if part)
    if requested_symbol and _mentions_symbol(title_body, requested_symbol):
        return True
    if requested_name and _mentions_name(name_text, requested_name):
        return True
    return False


def filter_kis_news_rows_for_symbol(
    rows: Optional[Iterable[Mapping[str, Any]]],
    *,
    symbol: str = "",
    stock_name: str = "",
) -> Dict[str, Any]:
    """Filter mixed KIS news rows down to rows with explicit stock evidence."""

    row_list = _rows(rows)
    requested_symbol = normalize_kr_news_symbol(symbol)
    requested_name = _text(stock_name)
    if not requested_symbol and not requested_name:
        return {
            "version": KIS_NEWS_SCOPE_VERSION,
            "filter_policy": "not_applied_missing_symbol_and_name",
            "filter_applied": False,
            "requested_symbol": None,
            "requested_stock_name": None,
            "raw_news_count": len(row_list),
            "rows_filtered_out_count": 0,
            "matched_rows_count": len(row_list),
            "rows": row_list,
            "warnings": ["kis_news_scope_filter_missing_symbol_and_name"] if row_list else [],
        }

    matched: List[Dict[str, Any]] = []
    filtered_out = 0
    for row in row_list:
        if kis_news_row_matches_symbol(row, symbol=requested_symbol, stock_name=requested_name):
            matched.append(dict(row))
        else:
            filtered_out += 1

    warnings: List[str] = []
    if filtered_out:
        warnings.append("kis_news_scope_rows_filtered_out")
    if row_list and not matched:
        warnings.append("kis_news_scope_no_symbol_specific_rows_after_filter")

    return {
        "version": KIS_NEWS_SCOPE_VERSION,
        "filter_policy": KIS_NEWS_SCOPE_FILTER_POLICY,
        "filter_applied": True,
        "requested_symbol": requested_symbol or None,
        "requested_stock_name": requested_name or None,
        "raw_news_count": len(row_list),
        "rows_filtered_out_count": filtered_out,
        "matched_rows_count": len(matched),
        "rows": matched,
        "warnings": warnings,
    }


def classify_kis_news_source_scope(
    *,
    symbol: str = "",
    stock_name: str = "",
    rows: Optional[Iterable[Mapping[str, Any]]] = None,
    checked: bool = False,
    news_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Classify whether KIS news rows are safe to treat as symbol-specific.

    The classifier only uses fields present in the real KIS response or
    surrounding stock-info contract. It does not infer symbol specificity from
    the fact that a request included a symbol, because KIS can return rows whose
    displayed payload does not prove the same scope to downstream consumers.
    """

    row_list = _rows(rows)
    requested_symbol = normalize_kr_news_symbol(symbol)
    requested_name = _text(stock_name)
    count = int(news_count) if news_count is not None else len(row_list)
    warnings: List[str] = []
    evidence: Dict[str, Any] = {
        "requested_symbol": requested_symbol or None,
        "requested_stock_name": requested_name or None,
        "news_count": count,
        "rows_stored_count": len(row_list),
        "sample_titles": [_row_title(row) for row in row_list[:3] if _row_title(row)],
    }

    if not checked:
        return {
            "version": KIS_NEWS_SCOPE_VERSION,
            "checked": False,
            "source_scope": "not_checked",
            "source_scope_confidence": 0.0,
            "promotion_blocked": False,
            "promotion_block_reason": None,
            "promotion_blocking_reasons": [],
            "warnings": [],
            "evidence": evidence,
        }

    if count <= 0:
        return {
            "version": KIS_NEWS_SCOPE_VERSION,
            "checked": True,
            "source_scope": "empty",
            "source_scope_confidence": 1.0,
            "promotion_blocked": False,
            "promotion_block_reason": None,
            "promotion_blocking_reasons": [],
            "warnings": [],
            "evidence": evidence,
        }

    if not row_list:
        warnings.append("kis_news_scope_no_rows_stored")
    if not requested_symbol:
        warnings.append("kis_news_scope_missing_requested_symbol")

    coded_rows = 0
    matched_symbol_rows = 0
    conflicting_symbol_rows = 0
    matched_name_rows = 0
    title_symbol_rows = 0
    for row in row_list:
        row_symbols = _row_symbols(row)
        if row_symbols:
            coded_rows += 1
            if requested_symbol in row_symbols:
                matched_symbol_rows += 1
            else:
                conflicting_symbol_rows += 1
        title_body = " ".join(part for part in (_row_title(row), _row_text(row, _BODY_FIELDS)) if part)
        name_text = " ".join(part for part in (_row_text(row, _NAME_FIELDS), title_body) if part)
        if requested_name and _mentions_name(name_text, requested_name):
            matched_name_rows += 1
        if requested_symbol and _mentions_symbol(title_body, requested_symbol):
            title_symbol_rows += 1

    evidence.update(
        {
            "coded_rows": coded_rows,
            "matched_symbol_rows": matched_symbol_rows,
            "conflicting_symbol_rows": conflicting_symbol_rows,
            "matched_name_rows": matched_name_rows,
            "title_symbol_rows": title_symbol_rows,
        }
    )

    source_scope = "ambiguous"
    confidence = 0.25
    block_reason = KIS_NEWS_SCOPE_AMBIGUOUS_BLOCK_REASON
    if not requested_symbol:
        source_scope = "market_wide"
        confidence = 0.15
        block_reason = KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON
    elif conflicting_symbol_rows > 0:
        source_scope = "market_wide"
        confidence = 0.2
        block_reason = KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON
        warnings.append("kis_news_scope_conflicting_symbol_rows")
    elif matched_symbol_rows > 0:
        source_scope = "symbol_specific"
        confidence = 0.95 if coded_rows == len(row_list) else 0.85
        block_reason = None
    elif title_symbol_rows > 0:
        source_scope = "symbol_specific"
        confidence = 0.8
        block_reason = None
    elif matched_name_rows > 0:
        source_scope = "symbol_specific"
        confidence = 0.72
        block_reason = None
    else:
        warnings.append("kis_news_scope_ambiguous")

    promotion_blocked = block_reason is not None
    blocking_reasons = [block_reason] if block_reason else []
    if source_scope == "market_wide" and "kis_news_scope_market_wide" not in warnings:
        warnings.append("kis_news_scope_market_wide")

    return {
        "version": KIS_NEWS_SCOPE_VERSION,
        "checked": True,
        "source_scope": source_scope,
        "source_scope_confidence": round(confidence, 4),
        "promotion_blocked": promotion_blocked,
        "promotion_block_reason": block_reason,
        "promotion_blocking_reasons": blocking_reasons,
        "warnings": list(dict.fromkeys(warnings)),
        "evidence": evidence,
    }


__all__ = [
    "KIS_NEWS_SCOPE_AMBIGUOUS_BLOCK_REASON",
    "KIS_NEWS_SCOPE_FILTER_POLICY",
    "KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON",
    "KIS_NEWS_SCOPE_VERSION",
    "classify_kis_news_source_scope",
    "filter_kis_news_rows_for_symbol",
    "kis_news_row_matches_symbol",
    "normalize_kr_news_symbol",
]
