# KIS Sidecar vs Historical Proxy Feature Gap

- version: `kis_sidecar_proxy_feature_gap_v1`
- generated_at: `2026-06-14T08:44:27+00:00`
- dummy_data_used: `False`
- production_replacement_ready: `False`
- shadow_signal_confirmed: `True`
- proxy_model_promotable: `False`
- next_best_action: Backfill actual KIS sidecar-equivalent flow, financial, stock static, rank/VI, and news fields for more historical days before retraining.

## Scope
- sidecar_cache: rows=`157551` days=`38` date=`2026-03-31`..`2026-06-10`
- proxy_cache: rows=`100490` days=`106` date=`2026-01-02`..`2026-06-10` markets=`{'KOSPI': 100490}`
- proxy_cache: rows=`191677` days=`106` date=`2026-01-02`..`2026-06-10` markets=`{'KOSDAQ': 191677}`

## Sidecar Shadow Evidence
- KOSPI: rule=`top1_p0p3_tail0p9` n=`50` days=`11` hit5_dd10=`82.0` avg5=`26.115197` min_low=`-8.919727` blockers=`['active_days_lt_15']`
- KOSDAQ: rule=`top1_p0p75_tail0p85` n=`19` days=`9` hit5_dd10=`100.0` avg5=`15.458772` min_low=`-7.006077` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']`

## Proxy Research Evidence
- KOSPI: n=`23` days=`23` hit5_dd10=`69.5652` tail=`13.0435` avg_exit=`1.373243` min_low=`-15.847695`
- KOSDAQ: n=`20` days=`20` hit5_dd10=`60.0` tail=`15.0` avg_exit=`1.201685` min_low=`-14.301385`

## Backfill Priorities
| priority | family | missing_features | avg_gap_pct | path |
|---:|---|---:|---:|---|

## Top Feature Gaps
### sidecar_diagnostic
- `kis_sidecar_coverage_quote_snapshot` sidecar=`44.964` proxy=`7.258` gap=`37.706`
- `kis_sidecar_coverage_vi_status` sidecar=`44.963` proxy=`7.258` gap=`37.705`
- `kis_sidecar_coverage_financial_ratio` sidecar=`44.95` proxy=`7.257` gap=`37.693`
- `kis_sidecar_coverage_financial_style` sidecar=`44.802` proxy=`7.242` gap=`37.56`
- `kis_sidecar_coverage_investor_flow` sidecar=`44.715` proxy=`7.211` gap=`37.504`
### sidecar_price_daily_rank
- `kis_vi_triggered` sidecar=`0.64` proxy=`0.109` gap=`0.531`
- `kis_high_250d_gap_pct` sidecar=`0.036` proxy=`0.013` gap=`0.023`
- `kis_low_250d_gap_pct` sidecar=`0.036` proxy=`0.013` gap=`0.023`
- `kis_rank_fluctuation` sidecar=`0.022` proxy=`0.008` gap=`0.014`
- `kis_rank_volume` sidecar=`0.021` proxy=`0.008` gap=`0.013`
### sidecar_flow
- `kis_whale_score` sidecar=`44.949` proxy=`92.969` gap=`-48.02`
- `kis_foreigner_1d` sidecar=`44.949` proxy=`92.969` gap=`-48.02`
- `kis_institution_1d` sidecar=`44.949` proxy=`92.969` gap=`-48.02`
- `kis_retail_1d` sidecar=`44.949` proxy=`92.969` gap=`-48.02`
- `kis_whale_flow_3d` sidecar=`44.949` proxy=`92.969` gap=`-48.02`
### sidecar_stock_static
- `kis_stock_status_code` sidecar=`0.0` proxy=`0.0` gap=`0.0`
- `kis_stock_listed_shares` sidecar=`44.947` proxy=`86.307` gap=`-41.36`
- `kis_stock_capital_amount` sidecar=`44.947` proxy=`86.502` gap=`-41.555`
- `kis_stock_kospi200_item` sidecar=`44.947` proxy=`86.802` gap=`-41.855`
- `kis_stock_par_value` sidecar=`44.947` proxy=`86.965` gap=`-42.018`
### sidecar_financial
- `kis_financial_per` sidecar=`0.0` proxy=`0.0` gap=`0.0`
- `kis_financial_pbr` sidecar=`0.0` proxy=`0.0` gap=`0.0`
- `kis_financial_current_ratio` sidecar=`0.0` proxy=`0.0` gap=`0.0`
- `kis_financial_revenue_growth_rate` sidecar=`44.8` proxy=`94.395` gap=`-49.595`
- `kis_financial_operating_profit_margin` sidecar=`44.8` proxy=`94.395` gap=`-49.595`
### sidecar_news
- `kis_news_title_count` sidecar=`1.349` proxy=`0.602` gap=`0.747`
- `kis_news_promotion_blocked` sidecar=`0.0` proxy=`0.0` gap=`0.0`
- `kis_news_source_scope_confidence` sidecar=`1.355` proxy=`100.0` gap=`-98.645`
- `kis_news_source_scope_ambiguous` sidecar=`1.355` proxy=`100.0` gap=`-98.645`
- `kis_news_source_scope` sidecar=`1.355` proxy=`100.0` gap=`-98.645`
### prefilter
- `kis_prefilter_quote_market_cap` sidecar=`1.013` proxy=`0.233` gap=`0.78`
- `kis_prefilter_quote_per` sidecar=`1.013` proxy=`0.233` gap=`0.78`
- `kis_prefilter_quote_pbr` sidecar=`1.013` proxy=`0.233` gap=`0.78`
- `kis_prefilter_score_market_cap` sidecar=`1.013` proxy=`0.233` gap=`0.78`
- `kis_prefilter_vi_triggered` sidecar=`0.1` proxy=`0.045` gap=`0.055`
### theme_news
- `kis_theme_news_news_count` sidecar=`1.349` proxy=`0.33` gap=`1.019`
- `kis_theme_news_headline_count` sidecar=`1.349` proxy=`0.33` gap=`1.019`
- `kis_theme_news_positive_tag_count` sidecar=`1.344` proxy=`0.328` gap=`1.016`
- `kis_theme_news_top_positive_tag` sidecar=`1.344` proxy=`0.328` gap=`1.016`
- `kis_theme_news_promotion_blocked` sidecar=`1.315` proxy=`0.318` gap=`0.997`

## Model Structure To Keep
- Stage 1: real KIS sidecar/prefilter wide recall pool, not dummy or missing-only proxy rows.
- Stage 2: separate touch5 success model and dd10/tail-safe model with hard tail gate.
- Stage 3: expected-value ranker plus no-trade threshold, then production evidence gate by n/active_days/active_runs.
