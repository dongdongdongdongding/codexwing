# KOSPI Ordered Candidate Search

- market: `KOSPI`
- generated_at: `2026-05-16T16:19:18.267477+00:00`
- rows_labeled: `5121`
- ordered_label_ready_rows: `4585`
- unique_ticker_dates: `1707`
- split_day: `2026-04-24`

## Baseline

- `5D_ordered_8v4`: all n=1556 win=37.018%, test n=781 win=28.9373%, test_stop=67.7337%
- `5D_ordered_10v5`: all n=1521 win=34.1223%, test n=746 win=27.3458%, test_stop=66.3539%
- `5D_ordered_12v5`: all n=1508 win=28.2493%, test n=733 win=23.7381%, test_stop=68.2128%

## Practical Watch 75pct Non-Theme

- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'expected_edge_score>=-2.24']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'expected_edge_score>=-7.1315']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'decision_score>=49.4']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'decision_score>=65.4']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'expected_return_3d_pct>=-0.78']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'expected_return_3d_pct>=-1.21']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'selection_lane=3d']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'decision_score>=59.25']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'decision_score>=78.8']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob<=50', 'expected_edge_score>=-9.875']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8', 'expected_edge_score>=-2.24']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8', 'expected_edge_score>=-7.1315']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8', 'expected_return_3d_pct>=-0.78']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8', 'expected_return_3d_pct>=-1.21']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8', 'selection_lane=3d']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8', 'ml_prob=[18.8,50]']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=78.8', 'expected_edge_score>=-9.875']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]', 'expected_edge_score>=-2.24']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]', 'expected_edge_score>=-7.1315']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]', 'decision_score>=49.4']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]', 'decision_score>=65.4']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]', 'expected_return_3d_pct>=-0.78']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]', 'expected_return_3d_pct>=-1.21']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'ml_prob=[18.8,50]', 'selection_lane=3d']: all n=17 win=76.4706%, train n=8 win=75.0%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=73.3334%, min_fold=66.6667%, avg_mfe=9.3418%, avg_mae=-0.6102%, min_mae=-6.6761%

## Practical Candidates 75pct Non-Theme

- none

## Strong Practical 80pct Non-Theme

- none

## Recent-Regime 75pct Non-Theme Diagnostics

- none

## Promotion-Ready Non-Theme Candidates

- none

## Release-Like Non-Theme Candidates

- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_edge_score>=-2.24']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_edge_score>=-7.1315']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=49.4']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=65.4']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_return_3d_pct>=-0.78']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_return_3d_pct>=-1.21']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'selection_lane=3d']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'decision_score>=59.25']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_return_1d_pct>=0.1815', 'expected_edge_score>=-9.875']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-3.8855%, test_loss5=0.0%, fold_win=72.2223%, min_fold=66.6667%, avg_mfe=9.2534%, avg_mae=-0.8497%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_edge_score>=2.2315', 'ml_prob<=50']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-4.2373%, test_loss5=0.0%, fold_win=68.75%, min_fold=57.1429%, avg_mfe=8.8817%, avg_mae=-0.8235%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_edge_score>=2.2315', 'decision_score>=78.8']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-4.2373%, test_loss5=0.0%, fold_win=68.75%, min_fold=57.1429%, avg_mfe=8.8817%, avg_mae=-0.8235%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_edge_score>=2.2315', 'ml_prob=[18.8,50]']: all n=18 win=72.2222%, train n=8 win=75.0%, test n=10 win=70.0%, test_stop=20.0%, test_med_close=6.7669%, test_min_close=-4.2373%, test_loss5=0.0%, fold_win=68.75%, min_fold=57.1429%, avg_mfe=8.8817%, avg_mae=-0.8235%, min_mae=-6.6761%

## Current Cohort Baseline

### 5D_ordered_8v4
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 66 | 46.9697 | 40.9091 | 6.7669 | -9.5745 | 51.7067 | 5.8824 | 8.0511 | -13.0653 |
| Top3 | 185 | 42.7027 | 45.4054 | 4.8544 | -29.9776 | 97.5155 | 15.3846 | 7.4924 | -13.0653 |
| Top5 | 277 | 40.4332 | 48.3755 | 3.9171 | -29.9776 | 97.5155 | 17.5115 | 7.1909 | -15.0709 |
| Exception Leader | 69 | 47.8261 | 36.2319 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 7.1412 | -10.7627 |
| Top5+Exception | 346 | 41.9075 | 45.9538 | 4.9796 | -29.9776 | 97.5155 | 13.6201 | 7.1809 | -15.0709 |

### 5D_ordered_10v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 64 | 45.3125 | 32.8125 | 6.7669 | -9.5745 | 51.7067 | 5.8824 | 8.7868 | -13.0653 |
| Top3 | 180 | 40.0 | 37.7778 | 4.8544 | -29.9776 | 97.5155 | 15.3846 | 8.5016 | -13.0653 |
| Top5 | 272 | 38.9706 | 40.4412 | 3.9171 | -29.9776 | 97.5155 | 17.5115 | 8.2399 | -15.4812 |
| Exception Leader | 69 | 42.029 | 27.5362 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 8.1909 | -10.7627 |
| Top5+Exception | 341 | 39.5894 | 37.8299 | 4.9796 | -29.9776 | 97.5155 | 13.6201 | 8.23 | -15.4812 |

### 5D_ordered_12v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 61 | 40.9836 | 36.0656 | 6.7669 | -9.5745 | 51.7067 | 5.8824 | 8.9518 | -13.0653 |
| Top3 | 175 | 36.0 | 39.4286 | 4.8544 | -29.9776 | 97.5155 | 15.3846 | 8.9155 | -13.0653 |
| Top5 | 265 | 34.3396 | 41.8868 | 3.9171 | -29.9776 | 97.5155 | 17.5115 | 8.5843 | -15.4812 |
| Exception Leader | 68 | 32.3529 | 27.9412 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 8.2977 | -10.7627 |
| Top5+Exception | 333 | 33.9339 | 39.039 | 4.9796 | -29.9776 | 97.5155 | 13.6201 | 8.5258 | -15.4812 |


## Curated Ordered Candidates

- `ordered_prob_band_top3_edge_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'expected_return_3d_pct<=0.458']: all n=13 win=76.9231%, train n=5 win=60.0%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=11.8293%, test_min_close=9.1358%, test_loss5=0.0%, fold_win=72.7273%, min_fold=50.0%, avg_mfe=13.3015%, avg_mae=-2.3697%, min_mae=-5.7034%
- `ordered_prob_band_top3_core_route_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'theme_routing_path=core_only']: all n=13 win=76.9231%, train n=7 win=71.4286%, test n=6 win=83.3333%, test_stop=16.6667%, test_med_close=12.5475%, test_min_close=9.1358%, test_loss5=0.0%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=13.0334%, avg_mae=-1.8021%, min_mae=-5.7034%
- `ordered_prob_band_top3_ml_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'ml_prob<=38.6']: all n=15 win=73.3333%, train n=10 win=70.0%, test n=5 win=80.0%, test_stop=20.0%, test_med_close=10.6815%, test_min_close=9.1358%, test_loss5=0.0%, fold_win=72.7273%, min_fold=60.0%, avg_mfe=13.2389%, avg_mae=-1.494%, min_mae=-5.7034%
- `ordered_prob_band_top3_phase_low_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'phase25_prob<=40.6']: all n=10 win=80.0%, train n=5 win=80.0%, test n=5 win=80.0%, test_stop=20.0%, test_med_close=11.8293%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=66.6667%, min_fold=66.6667%, avg_mfe=14.6669%, avg_mae=-2.9033%, min_mae=-5.7034%
- `ordered_prob_band_top3_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0']: all n=19 win=73.6842%, train n=10 win=70.0%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=11.1111%, test_min_close=-13.2775%, test_loss5=14.2857%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=13.2918%, avg_mae=-1.5708%, min_mae=-8.7321%

## High-Win Small-N Non-Theme Candidates

- none

## Theme-Dependent Diagnostics

- `5D_ordered_10v5` ['prob_clean>=28.1', 'primary_theme=통신/네트워크', 'alpha_score<=99', 'expected_return_1d_pct>=-0.81']: all n=22 win=77.2727%, train n=12 win=66.6667%, test n=10 win=90.0%, test_stop=10.0%, test_med_close=29.4118%, test_min_close=1.644%, test_loss5=0.0%, fold_win=77.2728%, min_fold=55.5556%, avg_mfe=12.3524%, avg_mae=-1.9475%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean>=27.7', 'primary_theme=통신/네트워크', 'alpha_score<=99', 'expected_return_1d_pct>=-0.81']: all n=22 win=77.2727%, train n=12 win=66.6667%, test n=10 win=90.0%, test_stop=10.0%, test_med_close=29.4118%, test_min_close=1.644%, test_loss5=0.0%, fold_win=77.2728%, min_fold=55.5556%, avg_mfe=12.3524%, avg_mae=-1.9475%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean=[27.7,50]', 'primary_theme=통신/네트워크', 'alpha_score<=99', 'expected_return_1d_pct>=-0.81']: all n=22 win=77.2727%, train n=12 win=66.6667%, test n=10 win=90.0%, test_stop=10.0%, test_med_close=29.4118%, test_min_close=1.644%, test_loss5=0.0%, fold_win=77.2728%, min_fold=55.5556%, avg_mfe=12.3524%, avg_mae=-1.9475%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean>=28.1', 'primary_theme=통신/네트워크', 'alpha_score<=94', 'expected_return_1d_pct>=-0.81']: all n=18 win=77.7778%, train n=10 win=70.0%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=49.2681%, test_min_close=1.644%, test_loss5=0.0%, fold_win=81.25%, min_fold=57.1429%, avg_mfe=11.9227%, avg_mae=-2.1834%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean>=27.7', 'primary_theme=통신/네트워크', 'alpha_score<=94', 'expected_return_1d_pct>=-0.81']: all n=18 win=77.7778%, train n=10 win=70.0%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=49.2681%, test_min_close=1.644%, test_loss5=0.0%, fold_win=81.25%, min_fold=57.1429%, avg_mfe=11.9227%, avg_mae=-2.1834%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean=[27.7,50]', 'primary_theme=통신/네트워크', 'alpha_score<=94', 'expected_return_1d_pct>=-0.81']: all n=18 win=77.7778%, train n=10 win=70.0%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=49.2681%, test_min_close=1.644%, test_loss5=0.0%, fold_win=81.25%, min_fold=57.1429%, avg_mfe=11.9227%, avg_mae=-2.1834%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean>=28.1', 'primary_theme=통신/네트워크', 'alpha_score<=99', 'decision_score>=49.4']: all n=17 win=76.4706%, train n=9 win=66.6667%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=27.8127%, test_min_close=1.644%, test_loss5=0.0%, fold_win=80.0%, min_fold=57.1429%, avg_mfe=11.7395%, avg_mae=-2.3106%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean>=27.7', 'primary_theme=통신/네트워크', 'alpha_score<=99', 'decision_score>=49.4']: all n=17 win=76.4706%, train n=9 win=66.6667%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=27.8127%, test_min_close=1.644%, test_loss5=0.0%, fold_win=80.0%, min_fold=57.1429%, avg_mfe=11.7395%, avg_mae=-2.3106%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean=[27.7,50]', 'primary_theme=통신/네트워크', 'alpha_score<=99', 'decision_score>=49.4']: all n=17 win=76.4706%, train n=9 win=66.6667%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=27.8127%, test_min_close=1.644%, test_loss5=0.0%, fold_win=80.0%, min_fold=57.1429%, avg_mfe=11.7395%, avg_mae=-2.3106%, min_mae=-6.4198%
- `5D_ordered_10v5` ['prob_clean=[28.1,35.225]', 'primary_theme=통신/네트워크', 'ml_prob=[18,35]']: all n=21 win=71.4286%, train n=13 win=61.5385%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=29.4118%, test_min_close=5.7692%, test_loss5=0.0%, fold_win=77.7778%, min_fold=50.0%, avg_mfe=13.7553%, avg_mae=-2.6117%, min_mae=-15.0709%

## Notes

- Production scanner ranking is unchanged.
- Practical watch starts at ordered test win >=75%.
- Practical candidates require ordered test win >=75%, all win >=60%, train win >=55%, and stop/loss-tail/fold safeguards.
- Recent-regime candidates pass the latest test window but fail the all/train stability floor, so they are not promotion candidates.
- Strong practical candidates use ordered test win >=80%; promotion-ready remains stricter and requires larger samples.
- feature_quality is excluded from searched categorical conditions because it is a data completeness marker, not a trading signal.
- Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.
- Rows with immature no-touch labels are excluded from win-rate denominators.
- Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.
