from modules.kis_news_scope import (
    KIS_NEWS_SCOPE_AMBIGUOUS_BLOCK_REASON,
    KIS_NEWS_SCOPE_MARKET_WIDE_BLOCK_REASON,
    classify_kis_news_source_scope,
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
