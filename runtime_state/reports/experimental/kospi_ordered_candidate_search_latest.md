# KOSPI Ordered Candidate Search

- market: `KOSPI`
- generated_at: `2026-05-16T10:04:29.178289+00:00`
- rows_labeled: `4881`
- ordered_label_ready_rows: `4577`
- unique_ticker_dates: `1627`
- split_day: `2026-04-24`

## Baseline

- `5D_ordered_8v4`: all n=1553 win=36.9607%, test n=778 win=28.7918%, test_stop=67.8663%
- `5D_ordered_10v5`: all n=1518 win=34.058%, test n=743 win=27.1871%, test_stop=66.4872%
- `5D_ordered_12v5`: all n=1506 win=28.2205%, test n=731 win=23.6662%, test_stop=68.2627%

## Practical Watch 75pct Non-Theme

- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob<=27.35']: all n=24 win=45.8333%, train n=15 win=26.6667%, test n=9 win=77.7778%, test_stop=11.1111%, test_med_close=9.6313%, test_min_close=-6.8182%, test_loss5=20.0%, fold_win=70.0%, min_fold=50.0%, avg_mfe=9.186%, avg_mae=-1.9682%, min_mae=-7.3025%
- `5D_ordered_10v5` ['cohort=Top5', 'whale_score>=73', 'alpha_score<=99', 'decision_score>=89.35']: all n=17 win=47.0588%, train n=8 win=12.5%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=10.2518%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=66.6667%, min_fold=33.3333%, avg_mfe=9.6839%, avg_mae=-4.2462%, min_mae=-11.4481%
- `5D_ordered_8v4` ['ml_prob<=18.8', 'prob_clean<=30.2', 'alpha_score<=99']: all n=42 win=52.381%, train n=33 win=45.4545%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=3.2847%, test_min_close=-14.7848%, test_loss5=25.0%, fold_win=44.1176%, min_fold=33.3333%, avg_mfe=7.2458%, avg_mae=-3.3456%, min_mae=-13.5079%
- `5D_ordered_8v4` ['prob_clean<=31.8', 'ml_prob<=18.8', 'alpha_score<=99']: all n=44 win=50.0%, train n=35 win=42.8571%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=3.2847%, test_min_close=-14.7848%, test_loss5=25.0%, fold_win=41.6667%, min_fold=30.7692%, avg_mfe=7.0682%, avg_mae=-3.2894%, min_mae=-13.5079%
- `5D_ordered_8v4` ['prob_clean<=35.225', 'ml_prob<=18.8', 'alpha_score<=99']: all n=48 win=47.9167%, train n=39 win=41.0256%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=3.2847%, test_min_close=-14.7848%, test_loss5=25.0%, fold_win=41.0256%, min_fold=33.3333%, avg_mfe=6.7014%, avg_mae=-3.4754%, min_mae=-13.5079%
- `5D_ordered_8v4` ['ml_prob<=18.8', 'prob_clean<=35.5', 'alpha_score<=99']: all n=48 win=47.9167%, train n=39 win=41.0256%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=3.2847%, test_min_close=-14.7848%, test_loss5=25.0%, fold_win=41.0256%, min_fold=33.3333%, avg_mfe=6.7014%, avg_mae=-3.4754%, min_mae=-13.5079%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob=[20.5,27.35]']: all n=17 win=47.0588%, train n=9 win=22.2222%, test n=8 win=75.0%, test_stop=12.5%, test_med_close=9.6313%, test_min_close=-6.8182%, test_loss5=20.0%, fold_win=83.3334%, min_fold=66.6667%, avg_mfe=9.5483%, avg_mae=-1.9593%, min_mae=-7.3025%
- `5D_ordered_10v5` ['cohort=Top3', 'decision_score<=98.05', 'ml_prob=[18.8,27.35]']: all n=19 win=47.3684%, train n=11 win=27.2727%, test n=8 win=75.0%, test_stop=12.5%, test_med_close=9.6313%, test_min_close=-6.8182%, test_loss5=20.0%, fold_win=83.3334%, min_fold=66.6667%, avg_mfe=9.486%, avg_mae=-2.0092%, min_mae=-7.3025%
- `5D_ordered_8v4` ['ml_prob<=18.8', 'prob_clean<=27.7', 'alpha_score<=99']: all n=40 win=52.5%, train n=32 win=46.875%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=4.0128%, test_min_close=-14.7848%, test_loss5=28.5714%, fold_win=43.75%, min_fold=36.3636%, avg_mfe=7.289%, avg_mae=-3.2145%, min_mae=-13.5079%

## Practical Candidates 75pct Non-Theme

- none

## Strong Practical 80pct Non-Theme

- none

## Promotion-Ready Non-Theme Candidates

- none

## Release-Like Non-Theme Candidates

- none

## Current Cohort Baseline

### 5D_ordered_8v4
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 64 | 45.3125 | 42.1875 | 6.7669 | -6.8182 | 51.7067 | 4.0816 | 7.7965 | -13.0653 |
| Top3 | 181 | 41.989 | 45.8564 | 4.9796 | -29.9776 | 97.5155 | 13.1387 | 7.3705 | -13.0653 |
| Top5 | 273 | 39.9267 | 48.7179 | 4.299 | -29.9776 | 97.5155 | 15.3846 | 7.1453 | -15.0709 |
| Exception Leader | 69 | 47.8261 | 36.2319 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 7.1412 | -10.7627 |
| Top5+Exception | 342 | 41.5205 | 46.1988 | 5.1114 | -29.9776 | 97.5155 | 11.8519 | 7.1444 | -15.0709 |

### 5D_ordered_10v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 62 | 43.5484 | 33.871 | 6.7669 | -6.8182 | 51.7067 | 4.0816 | 8.5478 | -13.0653 |
| Top3 | 177 | 39.548 | 37.8531 | 4.9796 | -29.9776 | 97.5155 | 13.1387 | 8.4002 | -13.0653 |
| Top5 | 269 | 38.6617 | 40.5204 | 4.299 | -29.9776 | 97.5155 | 15.3846 | 8.2076 | -15.4812 |
| Exception Leader | 69 | 42.029 | 27.5362 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 8.1909 | -10.7627 |
| Top5+Exception | 338 | 39.3491 | 37.8698 | 5.1114 | -29.9776 | 97.5155 | 11.8519 | 8.2042 | -15.4812 |

### 5D_ordered_12v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 60 | 40.0 | 36.6667 | 6.7669 | -6.8182 | 51.7067 | 4.0816 | 8.7559 | -13.0653 |
| Top3 | 172 | 35.4651 | 39.5349 | 4.9796 | -29.9776 | 97.5155 | 13.1387 | 8.8184 | -13.0653 |
| Top5 | 262 | 33.9695 | 41.9847 | 4.299 | -29.9776 | 97.5155 | 15.3846 | 8.5376 | -15.4812 |
| Exception Leader | 68 | 32.3529 | 27.9412 | 6.0606 | -3.8658 | 31.6614 | 0.0 | 8.2977 | -10.7627 |
| Top5+Exception | 330 | 33.6364 | 39.0909 | 5.1114 | -29.9776 | 97.5155 | 11.8519 | 8.4882 | -15.4812 |


## Curated Ordered Candidates

- `ordered_prob_band_top3_edge_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'expected_return_3d_pct<=0.458']: all n=13 win=76.9231%, train n=5 win=60.0%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=12.5475%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=72.7273%, min_fold=50.0%, avg_mfe=13.3015%, avg_mae=-2.3697%, min_mae=-5.7034%
- `ordered_prob_band_top3_core_route_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'theme_routing_path=core_only']: all n=13 win=76.9231%, train n=7 win=71.4286%, test n=6 win=83.3333%, test_stop=16.6667%, test_med_close=12.7832%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=77.7778%, min_fold=66.6667%, avg_mfe=13.0334%, avg_mae=-1.8021%, min_mae=-5.7034%
- `ordered_prob_band_top3_ml_cap_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'ml_prob<=38.6']: all n=16 win=75.0%, train n=10 win=70.0%, test n=6 win=83.3333%, test_stop=16.6667%, test_med_close=11.1111%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=72.7273%, min_fold=60.0%, avg_mfe=13.7087%, avg_mae=-1.3564%, min_mae=-5.7034%
- `ordered_prob_band_top3_phase_low_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0', 'phase25_prob<=40.6']: all n=10 win=80.0%, train n=5 win=80.0%, test n=5 win=80.0%, test_stop=20.0%, test_med_close=11.8293%, test_min_close=10.2518%, test_loss5=0.0%, fold_win=66.6667%, min_fold=66.6667%, avg_mfe=14.6669%, avg_mae=-2.9033%, min_mae=-5.7034%
- `ordered_prob_band_top3_10v5` `5D_ordered_10v5` ['cohort=Top3', 'prob_clean=[28.1,31.8]', 'decision_score>=100', 'explosive_leader_flag=0']: all n=20 win=70.0%, train n=10 win=70.0%, test n=10 win=70.0%, test_stop=30.0%, test_med_close=11.8293%, test_min_close=-13.2775%, test_loss5=16.6667%, fold_win=70.5883%, min_fold=66.6667%, avg_mfe=12.7733%, avg_mae=-1.7712%, min_mae=-8.7321%

## High-Win Small-N Non-Theme Candidates

- none

## Theme-Dependent Diagnostics

- none

## Notes

- Production scanner ranking is unchanged.
- Practical watch starts at ordered test win >=75%; practical candidates also require stop/loss-tail/fold safeguards.
- Strong practical candidates use ordered test win >=80%; promotion-ready remains stricter and requires larger samples.
- Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.
- Rows with immature no-touch labels are excluded from win-rate denominators.
- Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.
