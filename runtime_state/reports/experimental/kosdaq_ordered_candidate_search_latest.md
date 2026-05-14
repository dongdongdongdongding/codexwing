# KOSDAQ Ordered Candidate Search

- market: `KOSDAQ`
- generated_at: `2026-05-14T14:18:19.483864+00:00`
- rows_labeled: `6272`
- ordered_label_ready_rows: `5838`
- unique_ticker_dates: `1568`
- split_day: `2026-04-22`

## Baseline

- `5D_ordered_5v5`: all n=1480 win=41.9595%, test n=806 win=35.1117%, test_stop=63.5236%
- `5D_ordered_8v5`: all n=1460 win=31.9178%, test n=786 win=27.0992%, test_stop=69.8473%
- `5D_ordered_10v5`: all n=1451 win=26.6023%, test n=777 win=21.6216%, test_stop=73.7452%
- `5D_ordered_12v5`: all n=1447 win=22.322%, test n=773 win=18.37%, test_stop=75.5498%

## Release-Like Non-Theme Candidates

- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'explosive_eligible=1']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'prob_clean<=50']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'decision_score<=97.5']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'core_trend_flag=0']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'ml_prob>=19.285']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.2699%, avg_mae=-2.816%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_edge_score<=2.92']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_1d_pct<=0.9']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_3d_pct<=1.34']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_3d_pct<=1.64']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_1d_pct<=0.71']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_3d_pct<=1.84']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_1d_pct<=0.46']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_1d_pct<=0.25']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%

## Curated Ordered Candidates

- `kosdaq_validated_touch_exception_5v5` `5D_ordered_5v5` ['cohort=Top5', 'trend=UP', 'alpha_score>=90', 'volume_ratio>=2']: all n=5 win=40.0%, train n=1 win=0.0%, test n=4 win=50.0%, test_stop=50.0%, fold_win=50.0%, min_fold=0.0%, avg_mfe=11.8694%, avg_mae=-5.7941%

## High-Win Small-N Non-Theme Candidates

- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_edge_score<=0.21']: all n=17 win=88.2353%, train n=8 win=87.5%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=93.75%, min_fold=87.5%, avg_mfe=10.1961%, avg_mae=-2.6669%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_3d_pct<=0.49']: all n=17 win=88.2353%, train n=8 win=87.5%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=93.75%, min_fold=87.5%, avg_mfe=10.1961%, avg_mae=-2.6669%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_1d_pct<=0.02']: all n=17 win=88.2353%, train n=8 win=87.5%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=93.75%, min_fold=87.5%, avg_mfe=10.1961%, avg_mae=-2.6669%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'explosive_eligible=1']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'prob_clean<=50']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'decision_score<=97.5']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'core_trend_flag=0']: all n=20 win=85.0%, train n=11 win=81.8182%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=89.4737%, min_fold=80.0%, avg_mfe=10.0859%, avg_mae=-2.8729%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'ml_prob>=19.285']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.2699%, avg_mae=-2.816%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_edge_score<=2.92']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_1d_pct<=0.9']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_3d_pct<=1.34']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_3d_pct<=1.64']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%
- `5D_ordered_5v5` ['volume_ratio<=1.23', 'trend=DOWN', 'selection_lane=1d', 'expected_return_1d_pct<=0.71']: all n=19 win=84.2105%, train n=10 win=80.0%, test n=9 win=88.8889%, test_stop=11.1111%, fold_win=88.8889%, min_fold=80.0%, avg_mfe=10.1719%, avg_mae=-3.0455%

## Theme-Dependent Diagnostics

- none

## Notes

- Production scanner ranking is unchanged.
- Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.
- Rows with immature no-touch labels are excluded from win-rate denominators.
- Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.
