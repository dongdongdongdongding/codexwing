# KOSPI Ordered Candidate Search

- generated_at: `2026-05-14T14:00:09.015629+00:00`
- rows_labeled: `5121`
- ordered_label_ready_rows: `4585`
- unique_ticker_dates: `1707`
- split_day: `2026-04-24`

## Baseline

- `5D_ordered_8v4`: all n=1556 win=37.018%, test n=781 win=28.9373%, test_stop=67.7337%
- `5D_ordered_10v5`: all n=1521 win=34.1223%, test n=746 win=27.3458%, test_stop=66.3539%
- `5D_ordered_12v5`: all n=1508 win=28.2493%, test n=733 win=23.7381%, test_stop=68.2128%

## Release-Like Non-Theme Candidates

- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'prob_clean=[28.1,31.8]', 'decision_score>=100']: all n=19 win=73.6842%, train n=10 win=70.0%, test n=9 win=77.7778%, test_stop=22.2222%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=13.2918%, avg_mae=-1.5708%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'prob_clean=[28.1,31.8]', 'ml_prob=[20.5,50]']: all n=21 win=71.4286%, train n=9 win=66.6667%, test n=12 win=75.0%, test_stop=25.0%, fold_win=82.3529%, min_fold=60.0%, avg_mfe=13.9006%, avg_mae=-2.2991%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'prob_clean=[28.1,31.8]', 'ml_prob>=20.5']: all n=21 win=71.4286%, train n=9 win=66.6667%, test n=12 win=75.0%, test_stop=25.0%, fold_win=82.3529%, min_fold=60.0%, avg_mfe=13.9006%, avg_mae=-2.2991%
- `5D_ordered_10v5` ['ml_prob=[18,35]', 'expected_return_1d_pct>=0.1815', 'decision_score>=98.05', 'alpha_score<=100']: all n=18 win=72.2222%, train n=10 win=70.0%, test n=8 win=75.0%, test_stop=25.0%, fold_win=66.6667%, min_fold=50.0%, avg_mfe=11.1783%, avg_mae=-2.8634%
- `5D_ordered_10v5` ['ml_prob=[18,35]', 'expected_return_1d_pct>=0.1815', 'decision_score>=98.05', 'alpha_score>=67']: all n=18 win=72.2222%, train n=10 win=70.0%, test n=8 win=75.0%, test_stop=25.0%, fold_win=66.6667%, min_fold=50.0%, avg_mfe=11.1783%, avg_mae=-2.8634%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'prob_clean=[28.1,31.8]', 'expected_edge_score>=-14.377']: all n=19 win=73.6842%, train n=8 win=75.0%, test n=11 win=72.7273%, test_stop=27.2727%, fold_win=73.6842%, min_fold=50.0%, avg_mfe=12.7759%, avg_mae=-3.2452%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'prob_clean=[28.1,31.8]', 'expected_return_3d_pct>=-1.9335']: all n=19 win=73.6842%, train n=8 win=75.0%, test n=11 win=72.7273%, test_stop=27.2727%, fold_win=73.6842%, min_fold=50.0%, avg_mfe=12.7759%, avg_mae=-3.2452%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'prob_clean=[28.1,31.8]', 'expected_return_1d_pct>=-1.207']: all n=19 win=73.6842%, train n=8 win=75.0%, test n=11 win=72.7273%, test_stop=27.2727%, fold_win=73.6842%, min_fold=50.0%, avg_mfe=12.7759%, avg_mae=-3.2452%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_edge_score>=-7.1315']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'prob_clean<=50']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_edge_score>=-14.377']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_return_3d_pct>=-1.9335']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_return_3d_pct>=-0.78']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_edge_score>=-9.875']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%

## Curated Ordered Candidates

- `ordered_prob_band_top3_edge_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'expected_return_3d_pct<=0.458']: all n=13 win=76.9231%, train n=5 win=60.0%, test n=8 win=87.5%, test_stop=12.5%, fold_win=72.7273%, min_fold=50.0%, avg_mfe=13.3015%, avg_mae=-2.3697%
- `ordered_prob_band_top3_core_route_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'theme_routing_path=core_only']: all n=13 win=76.9231%, train n=7 win=71.4286%, test n=6 win=83.3333%, test_stop=16.6667%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=13.0334%, avg_mae=-1.8021%
- `ordered_prob_band_top3_ml_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'ml_prob<=38.6']: all n=15 win=73.3333%, train n=10 win=70.0%, test n=5 win=80.0%, test_stop=20.0%, fold_win=72.7273%, min_fold=60.0%, avg_mfe=13.2389%, avg_mae=-1.494%
- `ordered_prob_band_top3_phase_low_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'phase25_prob<=40.6']: all n=10 win=80.0%, train n=5 win=80.0%, test n=5 win=80.0%, test_stop=20.0%, fold_win=66.6667%, min_fold=66.6667%, avg_mfe=14.6669%, avg_mae=-2.9033%
- `ordered_prob_band_top3_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0']: all n=19 win=73.6842%, train n=10 win=70.0%, test n=9 win=77.7778%, test_stop=22.2222%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=13.2918%, avg_mae=-1.5708%

## High-Win Small-N Non-Theme Candidates

- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=30.2']: all n=16 win=56.25%, train n=8 win=25.0%, test n=8 win=87.5%, test_stop=12.5%, fold_win=83.3334%, min_fold=66.6667%, avg_mfe=10.778%, avg_mae=-1.1638%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=31.8']: all n=17 win=52.9412%, train n=9 win=22.2222%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=10.0933%, avg_mae=-1.4333%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=35.225']: all n=21 win=52.381%, train n=13 win=30.7692%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.613%, avg_mae=-1.7241%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=35.5']: all n=21 win=52.381%, train n=13 win=30.7692%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.613%, avg_mae=-1.7241%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'prob_clean<=50']: all n=23 win=47.8261%, train n=15 win=26.6667%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.2642%, avg_mae=-1.8658%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35', 'trend=UP']: all n=22 win=45.4545%, train n=14 win=21.4286%, test n=8 win=87.5%, test_stop=12.5%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=9.1571%, avg_mae=-1.9915%
- `5D_ordered_10v5` ['expected_return_3d_pct>=-0.02', 'position=🌋 고점 (Peak)', 'theme_routing_path=core_only', 'decision_score>=49.4']: all n=17 win=76.4706%, train n=9 win=66.6667%, test n=8 win=87.5%, test_stop=12.5%, fold_win=76.4706%, min_fold=66.6667%, avg_mfe=13.9048%, avg_mae=-2.4063%
- `5D_ordered_10v5` ['expected_return_3d_pct>=-0.02', 'position=🌋 고점 (Peak)', 'theme_routing_path=core_only', 'alpha_score>=76']: all n=18 win=72.2222%, train n=10 win=60.0%, test n=8 win=87.5%, test_stop=12.5%, fold_win=72.2222%, min_fold=60.0%, avg_mfe=13.669%, avg_mae=-2.4363%
- `5D_ordered_10v5` ['expected_return_3d_pct>=-0.02', 'position=🌋 고점 (Peak)', 'theme_routing_path=core_only', 'expected_edge_score>=-2.24']: all n=18 win=72.2222%, train n=10 win=60.0%, test n=8 win=87.5%, test_stop=12.5%, fold_win=72.2222%, min_fold=60.0%, avg_mfe=13.545%, avg_mae=-2.3891%
- `5D_ordered_10v5` ['expected_return_3d_pct>=-0.02', 'position=🌋 고점 (Peak)', 'theme_routing_path=core_only', 'expected_return_1d_pct>=-0.18']: all n=18 win=72.2222%, train n=10 win=60.0%, test n=8 win=87.5%, test_stop=12.5%, fold_win=72.2222%, min_fold=60.0%, avg_mfe=13.545%, avg_mae=-2.3891%
- `5D_ordered_10v5` ['cohort=Top3', 'explosive_leader_flag=0', 'prob_clean=[28.1,31.8]', 'theme_routing_path=core_only']: all n=17 win=76.4706%, train n=9 win=66.6667%, test n=8 win=87.5%, test_stop=12.5%, fold_win=71.4286%, min_fold=57.1429%, avg_mfe=13.7366%, avg_mae=-1.9875%
- `5D_ordered_10v5` ['expected_return_3d_pct>=-0.02', 'position=🌋 고점 (Peak)', 'theme_routing_path=core_only', 'expected_edge_score<=9.1225']: all n=17 win=70.5882%, train n=9 win=55.5556%, test n=8 win=87.5%, test_stop=12.5%, fold_win=70.5883%, min_fold=55.5556%, avg_mfe=13.1199%, avg_mae=-2.3879%
- `5D_ordered_10v5` ['expected_return_3d_pct>=-0.02', 'position=🌋 고점 (Peak)', 'theme_routing_path=core_only', 'expected_return_1d_pct<=0.7735']: all n=17 win=70.5882%, train n=9 win=55.5556%, test n=8 win=87.5%, test_stop=12.5%, fold_win=70.5883%, min_fold=55.5556%, avg_mfe=13.1199%, avg_mae=-2.3879%
- `5D_ordered_10v5` ['expected_return_3d_pct>=-0.02', 'position=🌋 고점 (Peak)', 'theme_routing_path=core_only']: all n=19 win=68.4211%, train n=11 win=54.5455%, test n=8 win=87.5%, test_stop=12.5%, fold_win=68.4211%, min_fold=54.5455%, avg_mfe=13.2588%, avg_mae=-2.3748%
- `5D_ordered_10v5` ['expected_return_3d_pct>=-0.02', 'position=🌋 고점 (Peak)', 'theme_routing_path=core_only', 'expected_edge_score>=-7.1315']: all n=19 win=68.4211%, train n=11 win=54.5455%, test n=8 win=87.5%, test_stop=12.5%, fold_win=68.4211%, min_fold=54.5455%, avg_mfe=13.2588%, avg_mae=-2.3748%

## Theme-Dependent Diagnostics

- none

## Notes

- Production scanner ranking is unchanged.
- Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.
- Rows with immature no-touch labels are excluded from win-rate denominators.
- Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.
