# KIS Static Sidecar Master Augmentation

- version: `kis_static_sidecar_master_augmentation_v1`
- generated_at: `2026-06-13T16:04:34+00:00`
- dummy_data_used: `False`
- production_replacement_ready: `False`
- leakage_policy: `ticker_static_stock_info_only; no flow/news/vi/rank/financial values; fill missing only`

## Static Master
- master_rows: `2393`
- conflict_count: `42`
- columns: `['kis_stock_market_code', 'kis_stock_market_name', 'kis_stock_type', 'kis_stock_listed_date', 'kis_stock_status_code', 'kis_stock_sector_name', 'kis_stock_standard_industry_code', 'kis_stock_listed_shares', 'kis_stock_capital_amount', 'kis_stock_par_value', 'kis_stock_kospi200_item', 'kis_stock_trade_stop', 'kis_stock_admin_item', 'kis_theme_news_standard_industry_code']`

## Market Augmentation
- KOSPI: matched_rows=`85436` augmented_rows=`77565` augmented_pct=`77.187` output=`runtime_state/reports/learning/kis_historical_universe_fullrank_actual_augmented_prepared_kospi_20260101_20260610.pkl`
- KOSDAQ: matched_rows=`168646` augmented_rows=`155316` augmented_pct=`81.03` output=`runtime_state/reports/learning/kis_historical_universe_fullrank_actual_augmented_prepared_kosdaq_20260101_20260610.pkl`

## Top Coverage Deltas
### KOSPI
| family | improved_features | avg_positive_delta_pct | top_delta |
|---|---:|---:|---|
| sidecar_diagnostic | 0 | 0 | `kis_sidecar_present` 100.0 -> 100.0 (+0.0) |
| sidecar_price_daily_rank | 0 | 0 | `kis_current_price` 100.0 -> 100.0 (+0.0) |
| sidecar_flow | 0 | 0 | `kis_whale_score` 7.837 -> 7.837 (+0.0) |
| sidecar_stock_static | 8 | 57.79 | `kis_stock_par_value` 7.833 -> 85.019 (+77.186) |
| sidecar_financial | 0 | 0 | `kis_financial_revenue_growth_rate` 7.79 -> 7.79 (+0.0) |
| sidecar_news | 0 | 0 | `kis_news_title_count` 7.837 -> 7.837 (+0.0) |
| prefilter | 0 | 0 | `kis_prefilter_present` 100.0 -> 100.0 (+0.0) |
| theme_news | 1 | 77.19 | `kis_theme_news_standard_industry_code` 7.833 -> 85.019 (+77.186) |
### KOSDAQ
| family | improved_features | avg_positive_delta_pct | top_delta |
|---|---:|---:|---|
| sidecar_diagnostic | 0 | 0 | `kis_sidecar_present` 100.0 -> 100.0 (+0.0) |
| sidecar_price_daily_rank | 0 | 0 | `kis_current_price` 100.0 -> 100.0 (+0.0) |
| sidecar_flow | 0 | 0 | `kis_whale_score` 6.954 -> 6.954 (+0.0) |
| sidecar_stock_static | 6 | 80.81 | `kis_stock_par_value` 6.954 -> 87.984 (+81.03) |
| sidecar_financial | 0 | 0 | `kis_financial_revenue_growth_rate` 6.954 -> 6.954 (+0.0) |
| sidecar_news | 0 | 0 | `kis_news_title_count` 6.955 -> 6.955 (+0.0) |
| prefilter | 0 | 0 | `kis_prefilter_present` 100.0 -> 100.0 (+0.0) |
| theme_news | 1 | 81.03 | `kis_theme_news_standard_industry_code` 6.954 -> 87.984 (+81.03) |

## Decision
- static stock-info parity is an input-quality improvement only; promotion still requires walk-forward performance gates.
