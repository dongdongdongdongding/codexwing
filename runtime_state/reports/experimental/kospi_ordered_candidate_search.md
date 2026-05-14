# KOSPI Ordered Candidate Search

- generated_at: `2026-05-14T13:27:53.475595+00:00`
- rows_labeled: `4881`
- ordered_label_ready_rows: `4577`
- unique_ticker_dates: `1627`
- split_day: `2026-04-24`

## Baseline

- `5D_ordered_8v4`: all n=1553 win=36.9607%, test n=778 win=28.7918%, test_stop=67.8663%
- `5D_ordered_10v5`: all n=1518 win=34.058%, test n=743 win=27.1871%, test_stop=66.4872%
- `5D_ordered_12v5`: all n=1506 win=28.2205%, test n=731 win=23.6662%, test_stop=68.2627%

## Release-Like Non-Theme Candidates

- `5D_ordered_10v5` ['cohort=Top3', 'ml_prob=[20.5,27.35]', 'theme_routing_path=core_only', 'prob_clean<=35.225']: all n=22 win=72.7273%, train n=14 win=71.4286%, test n=8 win=75.0%, test_stop=25.0%, fold_win=70.5883%, min_fold=50.0%, avg_mfe=11.4049%, avg_mae=-2.3999%
- `5D_ordered_8v4` ['cohort=Top3', 'ml_prob=[20.5,27.35]', 'theme_routing_path=core_only', 'prob_clean<=35.225']: all n=22 win=72.7273%, train n=14 win=71.4286%, test n=8 win=75.0%, test_stop=25.0%, fold_win=70.5883%, min_fold=50.0%, avg_mfe=9.5818%, avg_mae=-2.1285%

## Curated Ordered Candidates

- `ordered_prob_band_top3_edge_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'expected_return_3d_pct<=0.458']: all n=13 win=76.9231%, train n=5 win=60.0%, test n=8 win=87.5%, test_stop=12.5%, fold_win=72.7273%, min_fold=50.0%, avg_mfe=13.3015%, avg_mae=-2.3697%
- `ordered_prob_band_top3_core_route_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'theme_routing_path=core_only']: all n=13 win=76.9231%, train n=7 win=71.4286%, test n=6 win=83.3333%, test_stop=16.6667%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=13.0334%, avg_mae=-1.8021%
- `ordered_prob_band_top3_ml_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'ml_prob<=38.6']: all n=16 win=75.0%, train n=10 win=70.0%, test n=6 win=83.3333%, test_stop=16.6667%, fold_win=72.7273%, min_fold=60.0%, avg_mfe=13.7087%, avg_mae=-1.3564%
- `ordered_prob_band_top3_phase_low_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'phase25_prob<=40.6']: all n=10 win=80.0%, train n=5 win=80.0%, test n=5 win=80.0%, test_stop=20.0%, fold_win=66.6667%, min_fold=66.6667%, avg_mfe=14.6669%, avg_mae=-2.9033%
- `ordered_prob_band_top3_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0']: all n=20 win=70.0%, train n=10 win=70.0%, test n=10 win=70.0%, test_stop=30.0%, fold_win=70.5883%, min_fold=66.6667%, avg_mfe=12.7733%, avg_mae=-1.7712%

## High-Win Small-N Non-Theme Candidates

- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=30.2']: all n=16 win=56.25%, train n=8 win=25.0%, test n=8 win=87.5%, test_stop=12.5%, fold_win=83.3334%, min_fold=66.6667%, avg_mfe=10.778%, avg_mae=-1.1638%
- `5D_ordered_8v4` ['cohort=Top3', 'ml_prob<=27.35', 'decision_score<=98.05', 'prob_clean<=30.2']: all n=16 win=62.5%, train n=8 win=37.5%, test n=8 win=87.5%, test_stop=12.5%, fold_win=83.3334%, min_fold=66.6667%, avg_mfe=10.5081%, avg_mae=-1.0874%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=31.8']: all n=17 win=52.9412%, train n=9 win=22.2222%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=10.0933%, avg_mae=-1.4333%
- `5D_ordered_8v4` ['cohort=Top3', 'ml_prob<=27.35', 'decision_score<=98.05', 'prob_clean<=31.8']: all n=17 win=58.8235%, train n=9 win=33.3333%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.8393%, avg_mae=-1.287%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=35.5']: all n=21 win=52.381%, train n=13 win=30.7692%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.613%, avg_mae=-1.7241%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=35.225']: all n=21 win=52.381%, train n=13 win=30.7692%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.613%, avg_mae=-1.7241%
- `5D_ordered_8v4` ['cohort=Top3', 'ml_prob<=27.35', 'decision_score<=98.05', 'prob_clean<=35.5']: all n=21 win=57.1429%, train n=13 win=38.4615%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.4074%, avg_mae=-1.6057%
- `5D_ordered_8v4` ['cohort=Top3', 'ml_prob<=27.35', 'decision_score<=98.05', 'prob_clean<=35.225']: all n=21 win=57.1429%, train n=13 win=38.4615%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.4074%, avg_mae=-1.6057%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=50']: all n=23 win=47.8261%, train n=15 win=26.6667%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.2642%, avg_mae=-1.8658%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'trend=UP']: all n=22 win=45.4545%, train n=14 win=21.4286%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.1571%, avg_mae=-1.9915%
- `5D_ordered_8v4` ['cohort=Top3', 'ml_prob<=27.35', 'decision_score<=98.05', 'prob_clean<=50']: all n=23 win=52.1739%, train n=15 win=33.3333%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.0764%, avg_mae=-1.7577%
- `5D_ordered_8v4` ['cohort=Top3', 'ml_prob<=27.35', 'decision_score<=98.05', 'trend=UP']: all n=22 win=50.0%, train n=14 win=28.5714%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=8.9608%, avg_mae=-1.8785%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'whale_score>=73']: all n=20 win=65.0%, train n=8 win=37.5%, test n=12 win=83.3333%, test_stop=16.6667%, fold_win=83.3333%, min_fold=75.0%, avg_mfe=11.5452%, avg_mae=-2.7738%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'whale_score>=73', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=20 win=65.0%, train n=8 win=37.5%, test n=12 win=83.3333%, test_stop=16.6667%, fold_win=83.3333%, min_fold=75.0%, avg_mfe=11.5452%, avg_mae=-2.7738%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'whale_score>=73', 'selection_lane=3d']: all n=20 win=65.0%, train n=8 win=37.5%, test n=12 win=83.3333%, test_stop=16.6667%, fold_win=83.3333%, min_fold=75.0%, avg_mfe=11.5452%, avg_mae=-2.7738%

## Theme-Dependent Diagnostics

- none

## Notes

- Production scanner ranking is unchanged.
- Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.
- Rows with immature no-touch labels are excluded from win-rate denominators.
- Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.
