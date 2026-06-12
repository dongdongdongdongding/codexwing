# KIS Sidecar Exact-Date Cache Augmentation

- version: `kis_sidecar_cache_exact_date_augmentation_v1`
- generated_at: `2026-06-12T18:32:12+00:00`
- dummy_data_used: `False`
- augmented_cache_ready_for_research: `True`
- production_replacement_ready: `False`
- leakage_policy: `exact_ticker_date_only_no_forward_fill`

## Scope
- sidecar: rows=`157551` days=`38` date=`2026-03-31`..`2026-06-10` tickers=`2496`

## Market Augmentation
- KOSPI: matched_rows=`16218` matched_pct=`16.176` days=`26` tickers=`842` output=`/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_universe_sidecar_cache_augmented_prepared_kospi_20260101_20260610.pkl`
  - matched_only: rows=`16218` days=`26` output=`runtime_state/reports/learning/kis_historical_universe_sidecar_cache_augmented_matched_only_kospi_20260101_20260610.pkl`
- KOSDAQ: matched_rows=`31850` matched_pct=`16.747` days=`27` tickers=`1643` output=`/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_universe_sidecar_cache_augmented_prepared_kosdaq_20260101_20260610.pkl`
  - matched_only: rows=`31850` days=`27` output=`runtime_state/reports/learning/kis_historical_universe_sidecar_cache_augmented_matched_only_kosdaq_20260101_20260610.pkl`

## Top Coverage Deltas
### KOSPI
| family | improved_features | avg_positive_delta_pct | top_delta |
|---|---:|---:|---|
| sidecar_diagnostic | 0 | 0 | `kis_sidecar_present` 100.0 -> 100.0 (+0.0) |
| sidecar_price_daily_rank | 5 | 1.581 | `kis_vi_triggered` 0.0 -> 7.854 (+7.854) |
| sidecar_flow | 6 | 7.855 | `kis_whale_score` 0.0 -> 7.855 (+7.855) |
| sidecar_stock_static | 8 | 5.891 | `kis_stock_listed_shares` 0.0 -> 7.851 (+7.851) |
| sidecar_financial | 9 | 7.808 | `kis_financial_revenue_growth_rate` 0.0 -> 7.808 (+7.808) |
| sidecar_news | 7 | 1.716 | `kis_news_title_count` 0.0 -> 7.855 (+7.855) |
| prefilter | 27 | 0.195 | `kis_prefilter_vi_triggered` 0.0 -> 0.334 (+0.334) |
| theme_news | 7 | 1.457 | `kis_theme_news_standard_industry_code` 0.0 -> 7.851 (+7.851) |
### KOSDAQ
| family | improved_features | avg_positive_delta_pct | top_delta |
|---|---:|---:|---|
| sidecar_diagnostic | 0 | 0 | `kis_sidecar_present` 100.0 -> 100.0 (+0.0) |
| sidecar_price_daily_rank | 5 | 1.409 | `kis_vi_triggered` 0.0 -> 7.01 (+7.01) |
| sidecar_flow | 6 | 7.009 | `kis_whale_score` 0.0 -> 7.009 (+7.009) |
| sidecar_stock_static | 6 | 7.009 | `kis_stock_listed_shares` 0.0 -> 7.009 (+7.009) |
| sidecar_financial | 9 | 7.009 | `kis_financial_revenue_growth_rate` 0.0 -> 7.009 (+7.009) |
| sidecar_news | 7 | 1.304 | `kis_news_title_count` 0.0 -> 7.01 (+7.01) |
| prefilter | 27 | 0.115 | `kis_prefilter_vi_triggered` 0.0 -> 0.181 (+0.181) |
| theme_news | 5 | 1.63 | `kis_theme_news_standard_industry_code` 0.0 -> 7.009 (+7.009) |

## Decision
- 이 도구는 학습 입력 보강까지만 수행한다. 운영 승격은 별도 walk-forward 성능 검증과 표본 gate 통과가 필요하다.
- 이 산출물은 성능 보고가 아니라, 다음 walk-forward 연구를 위한 실데이터 입력 보강 결과다.
