# KIS News Scope and Industry Regime Validation

- generated_at: `2026-06-08T17:41:39.985778+09:00`
- verdict: `promotion_block_required_for_ambiguous_news`
- no_dummy_data: `True`
- live_network_enabled_for_run: `True`
- symbols_checked: `4`
- news_scope_counts: `{'market_wide': 4}`
- news_promotion_blocked_count: `4`
- industry_overlay_ready_count: `2/2`
- mapping_note: KIS industry_price/industry_daily_bars validate market/industry-index regime, but stock_info standard_industry_code is not an official one-to-one index_code mapping.

## News Scope Rows

- 005930 삼성전자보통주: scope=`market_wide`, confidence=`0.2`, news_count=`40`, blocked=`True`, reason=`KIS_NEWS_SCOPE_MARKET_WIDE`
- 000660 에스케이하이닉스보통주: scope=`market_wide`, confidence=`0.2`, news_count=`40`, blocked=`True`, reason=`KIS_NEWS_SCOPE_MARKET_WIDE`
- 091990 셀트리온헬스케어: scope=`market_wide`, confidence=`0.2`, news_count=`40`, blocked=`True`, reason=`KIS_NEWS_SCOPE_MARKET_WIDE`
- 196170 알테오젠: scope=`market_wide`, confidence=`0.2`, news_count=`40`, blocked=`True`, reason=`KIS_NEWS_SCOPE_MARKET_WIDE`

## Industry Regime Rows

- 0001 KOSPI: trend=`strong_negative`, score=`-36.3658`, change_pct=`-8.29`, return_5d_pct=`-11.700359`, return_20d_pct=`-0.0753`, bar_count=`28`, source_ok=`True`
- 1001 KOSDAQ: trend=`strong_negative`, score=`-50.16`, change_pct=`-9.08`, return_5d_pct=`-15.203759`, return_20d_pct=`-23.998899`, bar_count=`28`, source_ok=`True`
