# KOSPI Ordered Candidate Search

- market: `KOSPI`
- generated_at: `2026-05-15T18:38:09.116360+00:00`
- rows_labeled: `4881`
- ordered_label_ready_rows: `4577`
- unique_ticker_dates: `1627`
- split_day: `2026-04-24`

## Baseline

- `5D_ordered_8v4`: all n=1553 win=36.9607%, test n=778 win=28.7918%, test_stop=67.8663%
- `5D_ordered_10v5`: all n=1518 win=34.058%, test n=743 win=27.1871%, test_stop=66.4872%
- `5D_ordered_12v5`: all n=1506 win=28.2205%, test n=731 win=23.6662%, test_stop=68.2627%

## Release-Like Non-Theme Candidates

- none

## Promotion-Ready Non-Theme Candidates

- none

## Current Cohort Baseline

### 5D_ordered_8v4
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 64 | 45.3125 | 42.1875 | 6.7669 | -6.8182 | 51.7067 | 3.125 | 7.7965 | -13.0653 |
| Top3 | 181 | 41.989 | 45.8564 | 4.9796 | -29.9776 | 97.5155 | 9.9448 | 7.3705 | -13.0653 |
| Top5 | 273 | 39.9267 | 48.7179 | 4.299 | -29.9776 | 97.5155 | 11.7216 | 7.1453 | -15.0709 |
| Exception Leader | 69 | 47.8261 | 36.2319 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 7.1412 | -10.7627 |
| Top5+Exception | 342 | 41.5205 | 46.1988 | 5.1114 | -29.9776 | 97.5155 | 9.3567 | 7.1444 | -15.0709 |

### 5D_ordered_10v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 62 | 43.5484 | 33.871 | 6.7669 | -6.8182 | 51.7067 | 3.2258 | 8.5478 | -13.0653 |
| Top3 | 177 | 39.548 | 37.8531 | 4.9796 | -29.9776 | 97.5155 | 10.1695 | 8.4002 | -13.0653 |
| Top5 | 269 | 38.6617 | 40.5204 | 4.299 | -29.9776 | 97.5155 | 11.8959 | 8.2076 | -15.4812 |
| Exception Leader | 69 | 42.029 | 27.5362 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 8.1909 | -10.7627 |
| Top5+Exception | 338 | 39.3491 | 37.8698 | 5.1114 | -29.9776 | 97.5155 | 9.4675 | 8.2042 | -15.4812 |

### 5D_ordered_12v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 60 | 40.0 | 36.6667 | 6.7669 | -6.8182 | 51.7067 | 3.3333 | 8.7559 | -13.0653 |
| Top3 | 172 | 35.4651 | 39.5349 | 4.9796 | -29.9776 | 97.5155 | 10.4651 | 8.8184 | -13.0653 |
| Top5 | 262 | 33.9695 | 41.9847 | 4.299 | -29.9776 | 97.5155 | 12.2137 | 8.5376 | -15.4812 |
| Exception Leader | 68 | 32.3529 | 27.9412 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 8.2977 | -10.7627 |
| Top5+Exception | 330 | 33.6364 | 39.0909 | 5.1114 | -29.9776 | 97.5155 | 9.697 | 8.4882 | -15.4812 |


## Curated Ordered Candidates

- `ordered_prob_band_top3_edge_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'expected_return_3d_pct<=0.458']: all n=13 win=76.9231%, train n=5 win=60.0%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=12.5475%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=72.7273%, min_fold=50.0%, avg_mfe=13.3015%, avg_mae=-2.3697%, min_mae=-5.7034%
- `ordered_prob_band_top3_core_route_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'theme_routing_path=core_only']: all n=13 win=76.9231%, train n=7 win=71.4286%, test n=6 win=83.3333%, test_stop=16.6667%, test_med_close=12.7832%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=13.0334%, avg_mae=-1.8021%, min_mae=-5.7034%
- `ordered_prob_band_top3_ml_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'ml_prob<=38.6']: all n=16 win=75.0%, train n=10 win=70.0%, test n=6 win=83.3333%, test_stop=16.6667%, test_med_close=11.1111%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=72.7273%, min_fold=60.0%, avg_mfe=13.7087%, avg_mae=-1.3564%, min_mae=-5.7034%
- `ordered_prob_band_top3_phase_low_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'phase25_prob<=40.6']: all n=10 win=80.0%, train n=5 win=80.0%, test n=5 win=80.0%, test_stop=20.0%, test_med_close=11.8293%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=66.6667%, min_fold=66.6667%, avg_mfe=14.6669%, avg_mae=-2.9033%, min_mae=-5.7034%
- `ordered_prob_band_top3_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0']: all n=20 win=70.0%, train n=10 win=70.0%, test n=10 win=70.0%, test_stop=30.0%, test_med_close=11.8293%, test_min_close=-13.2775%, test_loss5=10.0%, fold_win=70.5883%, min_fold=66.6667%, avg_mfe=12.7733%, avg_mae=-1.7712%, min_mae=-8.7321%

## High-Win Small-N Non-Theme Candidates

- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'core_trend_flag=1']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'kr_universe_role=CORE_TREND']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'core_trend_flag=1', 'kr_universe_role=CORE_TREND']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'core_trend_flag=1', 'decision_score>=49.4']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'core_trend_flag=1', 'alpha_score>=67']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'core_trend_flag=1', 'selection_lane=3d']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'core_trend_flag=1', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'kr_universe_role=CORE_TREND', 'decision_score>=49.4']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'kr_universe_role=CORE_TREND', 'alpha_score>=67']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'kr_universe_role=CORE_TREND', 'selection_lane=3d']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'kr_universe_role=CORE_TREND', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=19 win=63.1579%, train n=8 win=37.5%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=66.6667%, avg_mfe=11.2914%, avg_mae=-2.6832%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'core_trend_flag=1', 'ml_prob<=50']: all n=18 win=61.1111%, train n=8 win=37.5%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=80.0%, min_fold=66.6667%, avg_mfe=11.35%, avg_mae=-2.596%, min_mae=-11.3793%
- `5D_ordered_10v5` ['cohort=Top3', 'whale_score>=73', 'kr_universe_role=CORE_TREND', 'ml_prob<=50']: all n=18 win=61.1111%, train n=8 win=37.5%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=80.0%, min_fold=66.6667%, avg_mfe=11.35%, avg_mae=-2.596%, min_mae=-11.3793%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_edge_score>=-2.24', 'feature_quality=incomplete', 'selection_lane=3d']: all n=20 win=70.0%, train n=10 win=60.0%, test n=10 win=80.0%, test_stop=10.0%, test_med_close=6.7669%, test_min_close=-4.2373%, test_loss5=0.0%, fold_win=70.0%, min_fold=57.1429%, avg_mfe=9.2533%, avg_mae=-0.6605%, min_mae=-6.6761%
- `5D_ordered_8v4` ['cohort=Top1', 'expected_edge_score>=-2.24', 'feature_quality=incomplete', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']: all n=20 win=70.0%, train n=10 win=60.0%, test n=10 win=80.0%, test_stop=10.0%, test_med_close=6.7669%, test_min_close=-4.2373%, test_loss5=0.0%, fold_win=70.0%, min_fold=57.1429%, avg_mfe=9.2533%, avg_mae=-0.6605%, min_mae=-6.6761%

## Theme-Dependent Diagnostics

- none

## Notes

- Production scanner ranking is unchanged.
- Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.
- Rows with immature no-touch labels are excluded from win-rate denominators.
- Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.
