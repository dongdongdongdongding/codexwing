# KIS Sidecar vs Historical Proxy Feature Gap

- version: `kis_sidecar_proxy_feature_gap_v1`
- generated_at: `2026-06-12T18:12:01+00:00`
- dummy_data_used: `False`
- production_replacement_ready: `False`
- shadow_signal_confirmed: `True`
- proxy_model_promotable: `False`
- next_best_action: Backfill actual KIS sidecar-equivalent flow, financial, stock static, rank/VI, and news fields for more historical days before retraining.

## Scope
- sidecar_cache: rows=`157551` days=`38` date=`2026-03-31`..`2026-06-10`
- proxy_cache: rows=`100260` days=`106` date=`2026-01-02`..`2026-06-10` markets=`{'KOSPI': 100260}`
- proxy_cache: rows=`190182` days=`106` date=`2026-01-02`..`2026-06-10` markets=`{'KOSDAQ': 190182}`

## Sidecar Shadow Evidence
- KOSPI: rule=`top1_p0p3_tail0p9` n=`50` days=`11` hit5_dd10=`82.0` avg5=`26.115197` min_low=`-8.919727` blockers=`['active_days_lt_15']`
- KOSDAQ: rule=`top1_p0p75_tail0p85` n=`19` days=`9` hit5_dd10=`100.0` avg5=`15.458772` min_low=`-7.006077` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']`

## Proxy Research Evidence
- KOSPI: n=`18` days=`18` hit5_dd10=`55.5556` tail=`27.7778` avg_exit=`-0.53572` min_low=`-27.443637`
- KOSDAQ: n=`17` days=`17` hit5_dd10=`58.8235` tail=`35.2941` avg_exit=`-0.971936` min_low=`-28.390711`

## Backfill Priorities
| priority | family | missing_features | avg_gap_pct | path |
|---:|---|---:|---:|---|
| 1 | sidecar_flow | 6 | 44.95 | KIS investor flow endpoint 또는 저장된 KIS sidecar backfill |
| 2 | sidecar_financial | 9 | 44.8 | KIS financial ratio/style + static daily cache |
| 3 | sidecar_stock_static | 6 | 44.95 | KIS stock info/listing/industry master |
| 7 | theme_news | 1 | 44.95 | KIS stock sector + news evidence contract |
| 99 | sidecar_diagnostic | 5 | 44.88 | review |

## Top Feature Gaps
### sidecar_diagnostic
- `kis_sidecar_coverage_quote_snapshot` sidecar=`44.964` proxy=`0.0` gap=`44.964`
- `kis_sidecar_coverage_vi_status` sidecar=`44.963` proxy=`0.0` gap=`44.963`
- `kis_sidecar_coverage_financial_ratio` sidecar=`44.95` proxy=`0.0` gap=`44.95`
- `kis_sidecar_coverage_financial_style` sidecar=`44.802` proxy=`0.0` gap=`44.802`
- `kis_sidecar_coverage_investor_flow` sidecar=`44.715` proxy=`0.0` gap=`44.715`
### sidecar_price_daily_rank
- `kis_vi_triggered` sidecar=`0.64` proxy=`0.0` gap=`0.64`
- `kis_high_250d_gap_pct` sidecar=`0.036` proxy=`0.0` gap=`0.036`
- `kis_low_250d_gap_pct` sidecar=`0.036` proxy=`0.0` gap=`0.036`
- `kis_rank_fluctuation` sidecar=`0.022` proxy=`0.0` gap=`0.022`
- `kis_rank_volume` sidecar=`0.021` proxy=`0.0` gap=`0.021`
### sidecar_flow
- `kis_whale_score` sidecar=`44.949` proxy=`0.0` gap=`44.949`
- `kis_foreigner_1d` sidecar=`44.949` proxy=`0.0` gap=`44.949`
- `kis_institution_1d` sidecar=`44.949` proxy=`0.0` gap=`44.949`
- `kis_retail_1d` sidecar=`44.949` proxy=`0.0` gap=`44.949`
- `kis_whale_flow_3d` sidecar=`44.949` proxy=`0.0` gap=`44.949`
### sidecar_stock_static
- `kis_stock_listed_shares` sidecar=`44.947` proxy=`0.0` gap=`44.947`
- `kis_stock_capital_amount` sidecar=`44.947` proxy=`0.0` gap=`44.947`
- `kis_stock_par_value` sidecar=`44.947` proxy=`0.0` gap=`44.947`
- `kis_stock_type` sidecar=`44.947` proxy=`0.0` gap=`44.947`
- `kis_stock_standard_industry_code` sidecar=`44.947` proxy=`0.0` gap=`44.947`
### sidecar_financial
- `kis_financial_revenue_growth_rate` sidecar=`44.8` proxy=`0.0` gap=`44.8`
- `kis_financial_operating_profit_margin` sidecar=`44.8` proxy=`0.0` gap=`44.8`
- `kis_financial_net_income_margin` sidecar=`44.8` proxy=`0.0` gap=`44.8`
- `kis_financial_roe` sidecar=`44.8` proxy=`0.0` gap=`44.8`
- `kis_financial_eps` sidecar=`44.8` proxy=`0.0` gap=`44.8`
### sidecar_news
- `kis_news_source_scope_confidence` sidecar=`1.355` proxy=`0.0` gap=`1.355`
- `kis_news_source_scope_ambiguous` sidecar=`1.355` proxy=`0.0` gap=`1.355`
- `kis_news_source_scope` sidecar=`1.355` proxy=`0.0` gap=`1.355`
- `kis_news_title_count` sidecar=`1.349` proxy=`0.0` gap=`1.349`
- `kis_news_raw_title_count` sidecar=`0.033` proxy=`0.0` gap=`0.033`
### prefilter
- `kis_prefilter_quote_market_cap` sidecar=`1.013` proxy=`0.0` gap=`1.013`
- `kis_prefilter_quote_per` sidecar=`1.013` proxy=`0.0` gap=`1.013`
- `kis_prefilter_quote_pbr` sidecar=`1.013` proxy=`0.0` gap=`1.013`
- `kis_prefilter_score_market_cap` sidecar=`1.013` proxy=`0.0` gap=`1.013`
- `kis_prefilter_vi_triggered` sidecar=`0.1` proxy=`0.0` gap=`0.1`
### theme_news
- `kis_theme_news_standard_industry_code` sidecar=`44.947` proxy=`0.0` gap=`44.947`
- `kis_theme_news_news_count` sidecar=`1.349` proxy=`0.0` gap=`1.349`
- `kis_theme_news_headline_count` sidecar=`1.349` proxy=`0.0` gap=`1.349`
- `kis_theme_news_positive_tag_count` sidecar=`1.344` proxy=`0.0` gap=`1.344`
- `kis_theme_news_top_positive_tag` sidecar=`1.344` proxy=`0.0` gap=`1.344`

## Model Structure To Keep
- Stage 1: real KIS sidecar/prefilter wide recall pool, not dummy or missing-only proxy rows.
- Stage 2: separate touch5 success model and dd10/tail-safe model with hard tail gate.
- Stage 3: expected-value ranker plus no-trade threshold, then production evidence gate by n/active_days/active_runs.
