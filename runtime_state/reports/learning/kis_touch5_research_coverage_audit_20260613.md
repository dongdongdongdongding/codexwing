# KIS Touch5 Research Coverage Audit

- version: `kis_touch5_research_coverage_audit_v1`
- generated_at: `2026-06-13T08:57:04+00:00`
- dummy_data_used: `False`
- decision: `coverage_gap_blocks_production_replacement`
- production_replacement_ready: `False`
- recommended_action: `do not promote; run actual KIS monthly/2-month slices, feature-family ablations, and rolling-prior validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10` unique_days=`38`

## Current Best
- KOSPI: rule=`top2_prob_plus_tail_p0p8_tail0p85` validation=`tailfirst_realistic_coverage` n=`93` days=`14` runs=`54` hit5=`87.0968` avg5=`15.093948` min_low=`-8.919727` blockers=`['active_days_lt_15']`
- KOSDAQ: rule=`top3_ev_tail0p9` validation=`dayfold_realistic_coverage` n=`58` days=`10` runs=`20` hit5=`94.8276` avg5=`8.515405` min_low=`-7.8413` blockers=`['active_days_lt_20']`
- research_only_best: rule=`top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_46p6667` n=`54` days=`15` hit5=`98.1481` avg5=`24.676158` min_low=`-9.230497` holdout_gate_pass=`0`

## Month Matrix
| month | KOSPI rows | KOSDAQ rows | status |
|---|---:|---:|---|
| 2026-01 | 0 | 0 | missing_or_sparse |
| 2026-02 | 0 | 0 | missing_or_sparse |
| 2026-03 | 0 | 34 | missing_or_sparse |
| 2026-04 | 318 | 295 | missing_or_sparse |
| 2026-05 | 53792 | 53238 | usable |
| 2026-06 | 20278 | 29596 | usable |

## Feature Families
| family | columns | avg_present_pct | ablation_required |
|---|---:|---:|---|
| close_failure_prior | 45 | 94.32 | True |
| kis_financial | 12 | 38.2 | True |
| kis_flow | 5 | 44.949 | True |
| kis_price_rank_quote | 95 | 34.202 | True |
| kis_static_master | 13 | 87.296 | True |
| scanner_technical | 9 | 32.238 | True |
| theme_news | 30 | 75.148 | True |

## Required Research Axes
- period: Evaluate 2026-01..2026-06 monthly and rolling two-month windows separately; actual KIS sidecar can only claim months present in the cache. promotion_rule=`No production promotion from a rule that only works in one month or only in proxy data.`
- feature_family: Run all, all-minus-close_failure_prior, close_failure_prior-only, KIS price/rank/quote, KIS flow, static/financial, theme/news, and technical-only ablations. promotion_rule=`Promote only if performance survives removing a single dominant family or the dominance is intentionally documented as the model thesis.`
- selection_stability: Use rolling prior: choose thresholds from prior OOS folds only, then apply to the next fold. promotion_rule=`Post-hoc threshold sweep can seed research but cannot directly become production.`
- operational_economics: Keep the +2% buy-premium, cost model, +5% target touch, and -10% low guard in every metric. promotion_rule=`0.1% positive close is defense only, never a win.`
