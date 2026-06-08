from modules.kis_news_scope import (
    KIS_NEWS_SCOPE_AMBIGUOUS_BLOCK_REASON,
    KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON,
    classify_kis_news_source_scope,
    filter_kis_news_rows_for_symbol,
    kis_news_row_matches_symbol,
)


def test_kis_news_scope_accepts_explicit_symbol_rows():
    scope = classify_kis_news_source_scope(
        symbol="005930.KS",
        stock_name="삼성전자",
        checked=True,
        news_count=1,
        rows=[{"mksc_shrn_iscd": "005930", "hts_pbnt_titl_cntt": "삼성전자 AI 반도체 공급 계약"}],
    )

    assert scope["source_scope"] == "symbol_specific"
    assert scope["source_scope_confidence"] >= 0.9
    assert scope["promotion_blocked"] is False


def test_kis_news_scope_blocks_title_only_rows_as_ambiguous():
    scope = classify_kis_news_source_scope(
        symbol="005930",
        checked=True,
        news_count=1,
        rows=[{"hts_pbnt_titl_cntt": "AI 반도체 공급 계약"}],
    )

    assert scope["source_scope"] == "ambiguous"
    assert scope["promotion_blocked"] is True
    assert scope["promotion_block_reason"] == KIS_NEWS_SCOPE_AMBIGUOUS_BLOCK_REASON


def test_kis_news_scope_blocks_conflicting_symbol_rows_as_market_wide():
    scope = classify_kis_news_source_scope(
        symbol="005930",
        checked=True,
        news_count=1,
        rows=[{"iscd1": "000660", "kor_isnm1": "SK하이닉스", "hts_pbnt_titl_cntt": "SK하이닉스 공급 계약"}],
    )

    assert scope["source_scope"] == "market_wide"
    assert scope["promotion_blocked"] is True
    assert scope["promotion_block_reason"] == KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON


def test_kis_news_strict_filter_keeps_only_matching_symbol_rows():
    rows = [
        {
            "iscd1": "005930",
            "kor_isnm1": "삼성전자",
            "hts_pbnt_titl_cntt": "삼성전자 AI 반도체 공급 계약",
        },
        {
            "iscd1": "000660",
            "kor_isnm1": "SK하이닉스",
            "hts_pbnt_titl_cntt": "SK하이닉스 HBM 공급",
        },
    ]

    filtered = filter_kis_news_rows_for_symbol(rows, symbol="005930", stock_name="삼성전자")

    assert filtered["raw_news_count"] == 2
    assert filtered["matched_rows_count"] == 1
    assert filtered["rows_filtered_out_count"] == 1
    assert filtered["rows"][0]["iscd1"] == "005930"
    assert kis_news_row_matches_symbol(rows[0], symbol="005930", stock_name="삼성전자") is True
    assert kis_news_row_matches_symbol(rows[1], symbol="005930", stock_name="삼성전자") is False
