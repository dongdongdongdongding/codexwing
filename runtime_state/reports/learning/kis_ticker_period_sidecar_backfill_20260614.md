# KIS Ticker-Period Sidecar Backfill

- version: `kis_ticker_period_sidecar_backfill_v1`
- generated_at: `2026-06-14T05:58:12+00:00`
- dummy_data_used: `False`
- live_network_requested: `True`
- kis_live_network_allowed: `True`
- cache_dir: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/long_term/kis_ticker_period_sidecar`

## Target Scope
- rows: `292167`
- tickers: `2770`
- dates: `106`
- date_range: `20260102`..`20260610`

## Lookup Rows
- flow: `383848` financial: `275690` news: `292167`
- call_counts: `{'stock_investor_daily': 13838, 'financial_ratio': 2770, 'news_titles_by_date': 106}`
- failure_counts: `{'stock_investor_daily:KISOpenAPIError': 5, 'financial_ratio:KISOpenAPIError': 8}`

## Market Outputs
### KOSPI
- augmented_rows: `100485` (99.995%)
- flow_augmented_rows: `93536`
- financial_augmented_rows: `79869`
- news_augmented_rows: `99795`
- future_financial_rows_cleared: `0`
- output_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kospi_20260101_20260610.pkl`

| feature | filled_missing_values |
|---|---:|
| `kis_news_raw_title_count` | 99795 |
| `kis_news_rows_filtered_out_count` | 99795 |
| `kis_news_source_scope_confidence` | 99795 |
| `kis_news_source_scope_ambiguous` | 99795 |
| `kis_news_promotion_blocked` | 99795 |
| `kis_news_source_scope` | 99795 |
| `flow_source` | 93536 |
| `flow_unit` | 93536 |
| `flow_asof` | 93536 |
| `kis_news_title_count` | 92615 |
| `kis_whale_score` | 85699 |
| `kis_foreigner_1d` | 85699 |
| `kis_institution_1d` | 85699 |
| `kis_retail_1d` | 85699 |
| `kis_whale_flow_3d` | 85699 |
| `kis_whale_flow_10d` | 85699 |
| `kis_financial_statement_period` | 79869 |
| `kis_financial_revenue_growth_rate` | 79869 |
| `kis_financial_operating_profit_margin` | 79869 |
| `kis_financial_net_income_margin` | 79869 |

### KOSDAQ
- augmented_rows: `191676` (99.999%)
- flow_augmented_rows: `177959`
- financial_augmented_rows: `174764`
- news_augmented_rows: `191005`
- future_financial_rows_cleared: `0`
- output_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kosdaq_20260101_20260610.pkl`

| feature | filled_missing_values |
|---|---:|
| `kis_news_raw_title_count` | 191005 |
| `kis_news_rows_filtered_out_count` | 191005 |
| `kis_news_source_scope_confidence` | 191005 |
| `kis_news_source_scope_ambiguous` | 191005 |
| `kis_news_promotion_blocked` | 191005 |
| `kis_news_source_scope` | 191005 |
| `kis_news_title_count` | 178346 |
| `flow_source` | 177959 |
| `flow_unit` | 177959 |
| `flow_asof` | 177959 |
| `kis_financial_statement_period` | 174764 |
| `kis_financial_revenue_growth_rate` | 174764 |
| `kis_financial_operating_profit_margin` | 174764 |
| `kis_financial_net_income_margin` | 174764 |
| `kis_financial_roe` | 174764 |
| `kis_financial_eps` | 174764 |
| `kis_financial_bps` | 174764 |
| `kis_financial_debt_ratio` | 174764 |
| `kis_financial_reserve_ratio` | 174764 |
| `kis_whale_score` | 164722 |

## Decision
- backfilled_cache_ready_for_research: `True`
- production_replacement_ready: `False`
- reason: This regenerates research inputs only; promotion still requires walk-forward gates.
