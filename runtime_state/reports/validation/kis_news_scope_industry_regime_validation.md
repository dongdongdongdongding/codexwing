# KIS News Scope and Industry Regime Validation

- generated_at: `2026-06-08T18:01:49.686560+09:00`
- verdict: `ready_with_symbol_specific_news`
- no_dummy_data: `True`
- live_network_enabled_for_run: `True`
- symbols_checked: `4`
- news_scope_counts: `{'symbol_specific': 4}`
- news_raw_count_total: `160`
- news_rows_filtered_out_total: `83`
- news_promotion_blocked_count: `0`
- industry_overlay_ready_count: `2/2`
- stock_industry_index_mapping_verified_count: `0`
- stock_industry_index_mapping_unverified_count: `4`
- mapping_note: KIS industry_price/industry_daily_bars are used only with verified market index codes. stock_info standard_industry_code is recorded but blocked from stock-specific index boosts until an official one-to-one KIS index_code mapping is verified.

## News Scope Rows

- 005930 삼성전자보통주: scope=`symbol_specific`, confidence=`0.95`, news_count=`27`, raw_news_count=`40`, rows_filtered_out=`13`, blocked=`False`, reason=`None`, stock_industry_mapping=`unmapped_unverified`, market_index_code=`0001`
- 000660 에스케이하이닉스보통주: scope=`symbol_specific`, confidence=`0.95`, news_count=`11`, raw_news_count=`40`, rows_filtered_out=`29`, blocked=`False`, reason=`None`, stock_industry_mapping=`unmapped_unverified`, market_index_code=`0001`
- 091990 셀트리온헬스케어: scope=`symbol_specific`, confidence=`0.95`, news_count=`32`, raw_news_count=`40`, rows_filtered_out=`8`, blocked=`False`, reason=`None`, stock_industry_mapping=`unmapped_unverified`, market_index_code=`1001`
- 196170 알테오젠: scope=`symbol_specific`, confidence=`0.95`, news_count=`7`, raw_news_count=`40`, rows_filtered_out=`33`, blocked=`False`, reason=`None`, stock_industry_mapping=`unmapped_unverified`, market_index_code=`1001`

## Industry Regime Rows

- 0001 KOSPI: trend=`strong_negative`, score=`-36.3658`, change_pct=`-8.29`, return_5d_pct=`-11.700359`, return_20d_pct=`-0.0753`, bar_count=`28`, source_ok=`True`
- 1001 KOSDAQ: trend=`strong_negative`, score=`-50.16`, change_pct=`-9.08`, return_5d_pct=`-15.203759`, return_20d_pct=`-23.998899`, bar_count=`28`, source_ok=`True`
