# KOSPI Admission Robust Search

- generated_at: `2026-05-14T12:16:40.521852+00:00`
- mode: `shadow_only_not_production`
- kospi_rows: `2462`
- raw_candidate_count: `7596`
- evaluated_candidate_count: `7596`
- config: `{'train_ratios': [0.55, 0.6, 0.65, 0.7, 0.75], 'max_depth': 3, 'beam_width': 180, 'min_train': 20, 'min_test': 8, 'max_conditions': 180, 'top_per_split': 120, 'rolling_folds': 4, 'min_train_days': 8, 'min_fold_test': 2}`

## Strict 70pct Candidates

- `Top5` / `5D_clean_8v4`: weighted `78.947`%, min_fold `71.429`%, n=`19`, stop_max `14.286`%, conditions=['prob_clean<=31.3', 'decision_score>=100', 'kr_universe_role=CORE_TREND']
- `Top5` / `5D_clean_8v4`: weighted `78.947`%, min_fold `71.429`%, n=`19`, stop_max `14.286`%, conditions=['prob_clean<=31.3', 'decision_score>=100', 'core_trend_flag=1']
- `Top5+Exception` / `5D_clean_8v4`: weighted `76.0`%, min_fold `71.429`%, n=`25`, stop_max `14.286`%, conditions=['prob_clean<=30.8', 'decision_score>=100', 'kr_universe_role=CORE_TREND']
- `Top5+Exception` / `5D_clean_8v4`: weighted `76.0`%, min_fold `71.429`%, n=`25`, stop_max `14.286`%, conditions=['prob_clean<=30.8', 'decision_score>=100', 'core_trend_flag=1']
- `Top5` / `5D_clean_8v4`: weighted `73.684`%, min_fold `71.429`%, n=`19`, stop_max `14.286`%, conditions=['ml_prob<=20.84', 'prob_clean<=35.225', 'decision_score>=92']
- `Top5` / `5D_clean_10v5`: weighted `73.684`%, min_fold `71.429`%, n=`19`, stop_max `14.286`%, conditions=['ml_prob<=20.84', 'prob_clean<=35.225', 'decision_score>=92']
- `Top5` / `5D_clean_8v4`: weighted `72.727`%, min_fold `70.0`%, n=`22`, stop_max `14.286`%, conditions=['prob_clean<=31.3', 'decision_score>=92', 'kr_universe_role=CORE_TREND']
- `Top5` / `5D_clean_8v4`: weighted `72.727`%, min_fold `70.0`%, n=`22`, stop_max `14.286`%, conditions=['prob_clean<=31.3', 'decision_score>=92', 'core_trend_flag=1']

## Stable 70pct Candidates

- `Top5` / `5D_clean_8v4`: weighted `78.947`%, min_fold `71.429`%, median `80.0`%, n=`19`, avg5 `8.5147`%, stop_max `14.286`%, conditions=['prob_clean<=31.3', 'decision_score>=100', 'kr_universe_role=CORE_TREND']
- `Top5` / `5D_clean_8v4`: weighted `78.947`%, min_fold `71.429`%, median `80.0`%, n=`19`, avg5 `8.5147`%, stop_max `14.286`%, conditions=['prob_clean<=31.3', 'decision_score>=100', 'core_trend_flag=1']
- `Top3` / `5D_clean_10v5`: weighted `78.947`%, min_fold `62.5`%, median `80.0`%, n=`19`, avg5 `10.303`%, stop_max `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=100', 'explosive_leader_flag=0']
- `Top3` / `5D_clean_12v5`: weighted `78.947`%, min_fold `62.5`%, median `80.0`%, n=`19`, avg5 `10.303`%, stop_max `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=100', 'explosive_leader_flag=0']
- `Top3` / `5D_clean_10v5`: weighted `76.191`%, min_fold `55.556`%, median `83.333`%, n=`21`, avg5 `10.5854`%, stop_max `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=93.26', 'explosive_leader_flag=0']
- `Top3` / `5D_clean_12v5`: weighted `76.191`%, min_fold `55.556`%, median `83.333`%, n=`21`, avg5 `10.5854`%, stop_max `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=93.26', 'explosive_leader_flag=0']
- `Top5+Exception` / `5D_clean_8v4`: weighted `76.0`%, min_fold `71.429`%, median `76.923`%, n=`25`, avg5 `8.581`%, stop_max `14.286`%, conditions=['prob_clean<=30.8', 'decision_score>=100', 'kr_universe_role=CORE_TREND']
- `Top5+Exception` / `5D_clean_8v4`: weighted `76.0`%, min_fold `71.429`%, median `76.923`%, n=`25`, avg5 `8.581`%, stop_max `14.286`%, conditions=['prob_clean<=30.8', 'decision_score>=100', 'core_trend_flag=1']
- `Top5` / `5D_clean_8v4`: weighted `73.684`%, min_fold `71.429`%, median `73.215`%, n=`19`, avg5 `6.2038`%, stop_max `14.286`%, conditions=['ml_prob<=20.84', 'prob_clean<=35.225', 'decision_score>=92']
- `Top5` / `5D_clean_10v5`: weighted `73.684`%, min_fold `71.429`%, median `73.215`%, n=`19`, avg5 `6.2038`%, stop_max `14.286`%, conditions=['ml_prob<=20.84', 'prob_clean<=35.225', 'decision_score>=92']
- `Top3` / `5D_clean_8v4`: weighted `73.684`%, min_fold `62.5`%, median `80.0`%, n=`19`, avg5 `10.303`%, stop_max `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=100', 'explosive_leader_flag=0']
- `Top5` / `5D_clean_8v4`: weighted `72.727`%, min_fold `70.0`%, median `71.429`%, n=`22`, avg5 `7.9306`%, stop_max `14.286`%, conditions=['prob_clean<=31.3', 'decision_score>=92', 'kr_universe_role=CORE_TREND']
- `Top5` / `5D_clean_8v4`: weighted `72.727`%, min_fold `70.0`%, median `71.429`%, n=`22`, avg5 `7.9306`%, stop_max `14.286`%, conditions=['prob_clean<=31.3', 'decision_score>=92', 'core_trend_flag=1']
- `Top5` / `5D_clean_8v4`: weighted `72.0`%, min_fold `62.5`%, median `70.0`%, n=`25`, avg5 `8.7801`%, stop_max `12.5`%, conditions=['prob_clean<=31.3', 'decision_score>=100', 'explosive_leader_flag=0']
- `Top5+Exception` / `5D_clean_8v4`: weighted `71.429`%, min_fold `68.75`%, median `71.429`%, n=`28`, avg5 `8.2035`%, stop_max `14.286`%, conditions=['prob_clean<=30.8', 'decision_score>=97.2', 'kr_universe_role=CORE_TREND']
- `Top5+Exception` / `5D_clean_8v4`: weighted `71.429`%, min_fold `68.75`%, median `71.429`%, n=`28`, avg5 `8.2035`%, stop_max `14.286`%, conditions=['prob_clean<=30.8', 'decision_score>=97.2', 'core_trend_flag=1']
- `Top3` / `3D_close_5v3_no_5d_stop`: weighted `71.429`%, min_fold `66.667`%, median `75.0`%, n=`14`, avg5 `5.6229`%, stop_max `25.0`%, conditions=['ml_prob<=35.6', 'prob_clean<=28.575', 'kr_universe_role=CORE_TREND']
- `Top3` / `3D_close_5v3_no_5d_stop`: weighted `71.429`%, min_fold `66.667`%, median `75.0`%, n=`14`, avg5 `5.6229`%, stop_max `25.0`%, conditions=['ml_prob<=35.6', 'prob_clean<=28.575', 'core_trend_flag=1']
- `Top3` / `5D_clean_8v4`: weighted `71.429`%, min_fold `55.556`%, median `83.333`%, n=`21`, avg5 `10.5854`%, stop_max `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=93.26', 'explosive_leader_flag=0']
- `Top5+Exception` / `5D_clean_8v4`: weighted `70.968`%, min_fold `62.5`%, median `68.75`%, n=`31`, avg5 `9.0427`%, stop_max `12.5`%, conditions=['prob_clean<=30.8', 'decision_score>=100', 'explosive_leader_flag=0']
- `Top3` / `5D_clean_10v5`: weighted `70.833`%, min_fold `60.0`%, median `75.0`%, n=`24`, avg5 `8.8428`%, stop_max `10.0`%, conditions=['prob_clean<=35.385', 'decision_score>=100', 'explosive_leader_flag=0']
- `Top3` / `5D_clean_12v5`: weighted `70.833`%, min_fold `60.0`%, median `75.0`%, n=`24`, avg5 `8.8428`%, stop_max `10.0`%, conditions=['prob_clean<=35.385', 'decision_score>=100', 'explosive_leader_flag=0']
- `Top5+Exception` / `5D_clean_8v4`: weighted `70.37`%, min_fold `62.5`%, median `68.092`%, n=`27`, avg5 `5.3529`%, stop_max `25.0`%, conditions=['ml_prob<=20.5', 'prob_clean<=34.475', 'priority_rank>=2']
- `Top5+Exception` / `5D_clean_10v5`: weighted `70.37`%, min_fold `62.5`%, median `68.092`%, n=`27`, avg5 `5.3529`%, stop_max `25.0`%, conditions=['ml_prob<=20.5', 'prob_clean<=34.475', 'priority_rank>=2']
- `Top3` / `5D_clean_10v5`: weighted `70.37`%, min_fold `54.545`%, median `77.778`%, n=`27`, avg5 `9.147`%, stop_max `9.091`%, conditions=['prob_clean<=35.385', 'decision_score>=93.26', 'explosive_leader_flag=0']
- `Top3` / `5D_clean_12v5`: weighted `70.37`%, min_fold `54.545`%, median `77.778`%, n=`27`, avg5 `9.147`%, stop_max `9.091`%, conditions=['prob_clean<=35.385', 'decision_score>=93.26', 'explosive_leader_flag=0']
- `Top5` / `5D_clean_8v4`: weighted `70.0`%, min_fold `62.5`%, median `68.75`%, n=`20`, avg5 `6.1779`%, stop_max `12.5`%, conditions=['ml_prob<=20.84', 'decision_score>=92']
- `Top5` / `5D_clean_8v4`: weighted `70.0`%, min_fold `62.5`%, median `68.75`%, n=`20`, avg5 `6.1779`%, stop_max `12.5`%, conditions=['ml_prob<=20.84', 'decision_score>=92', 'priority_rank>=1']
- `Top5` / `5D_clean_8v4`: weighted `70.0`%, min_fold `62.5`%, median `68.75`%, n=`20`, avg5 `6.1779`%, stop_max `12.5`%, conditions=['ml_prob<=20.84', 'decision_score>=92', 'selection_lane=3d']
- `Top5` / `5D_clean_8v4`: weighted `70.0`%, min_fold `62.5`%, median `68.75`%, n=`20`, avg5 `6.1779`%, stop_max `12.5`%, conditions=['ml_prob<=20.84', 'decision_score>=92', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH']

## Top Champions

| rank | cohort | profile | folds | n | weighted_win | min_win | median_win | avg5 | max_stop | conditions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Exception Leader | 5D_clean_8v4 | 1 | 8 | 100.0 | 100.0 | 100.0 | 10.4593 | 0.0 | priority_rank>=5<br>priority_rank<=11 |
| 2 | Exception Leader | 5D_clean_8v4 | 1 | 8 | 100.0 | 100.0 | 100.0 | 10.4593 | 0.0 | priority_rank>=5<br>priority_rank<=9 |
| 3 | Exception Leader | 5D_clean_8v4 | 1 | 5 | 100.0 | 100.0 | 100.0 | 8.4133 | 0.0 | alpha_score<=95.25<br>prob_clean<=33.925<br>priority_rank>=5 |
| 4 | Exception Leader | 5D_clean_8v4 | 1 | 5 | 100.0 | 100.0 | 100.0 | 8.4133 | 0.0 | alpha_score<=95.25<br>priority_rank>=5<br>priority_rank<=14.8 |
| 5 | Exception Leader | 5D_clean_8v4 | 1 | 5 | 100.0 | 100.0 | 100.0 | 8.4133 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>priority_rank<=14.8 |
| 6 | Exception Leader | 5D_clean_10v5 | 1 | 5 | 100.0 | 100.0 | 100.0 | 8.4133 | 0.0 | alpha_score<=95.25<br>priority_rank>=5<br>priority_rank<=14.8 |
| 7 | Exception Leader | 5D_clean_10v5 | 1 | 5 | 100.0 | 100.0 | 100.0 | 8.4133 | 0.0 | alpha_score<=95.25<br>prob_clean<=33.925<br>priority_rank>=5 |
| 8 | Exception Leader | 5D_clean_10v5 | 1 | 5 | 100.0 | 100.0 | 100.0 | 8.4133 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>priority_rank<=14.8 |
| 9 | Exception Leader | 5D_clean_10v5 | 1 | 2 | 100.0 | 100.0 | 100.0 | 7.8496 | 0.0 | alpha_score<=95.25<br>ml_prob>=20.2<br>prob_clean<=35.3 |
| 10 | Exception Leader | 5D_clean_10v5 | 1 | 2 | 100.0 | 100.0 | 100.0 | 7.8496 | 0.0 | alpha_score<=95.25<br>ml_prob>=20.2<br>priority_rank<=14.8 |
| 11 | Exception Leader | 5D_clean_8v4 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>selection_lane=3d |
| 12 | Exception Leader | 5D_clean_8v4 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>kr_universe_role=CORE_TREND |
| 13 | Exception Leader | 5D_clean_8v4 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH |
| 14 | Exception Leader | 5D_clean_8v4 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>explosive_leader_flag=0 |
| 15 | Exception Leader | 5D_clean_8v4 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>core_trend_flag=1 |
| 16 | Exception Leader | 5D_clean_10v5 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>selection_lane=3d |
| 17 | Exception Leader | 5D_clean_10v5 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>kr_universe_role=CORE_TREND |
| 18 | Exception Leader | 5D_clean_10v5 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH |
| 19 | Exception Leader | 5D_clean_10v5 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>explosive_leader_flag=0 |
| 20 | Exception Leader | 5D_clean_10v5 | 1 | 9 | 88.889 | 88.889 | 88.889 | 10.792 | 0.0 | prob_clean<=33.925<br>priority_rank>=5<br>core_trend_flag=1 |
| 21 | Exception Leader | 5D_clean_10v5 | 1 | 8 | 87.5 | 87.5 | 87.5 | 10.4593 | 0.0 | priority_rank>=5<br>priority_rank<=11 |
| 22 | Exception Leader | 5D_clean_10v5 | 1 | 8 | 87.5 | 87.5 | 87.5 | 10.4593 | 0.0 | priority_rank>=5<br>priority_rank<=9 |
| 23 | Exception Leader | 5D_clean_10v5 | 1 | 8 | 87.5 | 87.5 | 87.5 | 10.4593 | 0.0 | alpha_score<=100<br>priority_rank>=5<br>priority_rank<=11 |
| 24 | Exception Leader | 5D_clean_8v4 | 1 | 7 | 85.714 | 85.714 | 85.714 | 9.5702 | 0.0 | prob_clean<=35.3<br>priority_rank>=5<br>priority_rank<=14.8 |
| 25 | Exception Leader | 5D_clean_10v5 | 1 | 7 | 85.714 | 85.714 | 85.714 | 9.5702 | 0.0 | prob_clean<=35.3<br>priority_rank>=5<br>priority_rank<=14.8 |
| 26 | Exception Leader | 5D_clean_8v4 | 1 | 7 | 85.714 | 85.714 | 85.714 | 8.1079 | 0.0 | alpha_score<=95.25<br>priority_rank<=11 |
| 27 | Exception Leader | 5D_clean_8v4 | 1 | 7 | 85.714 | 85.714 | 85.714 | 8.1079 | 0.0 | alpha_score<=95.25<br>priority_rank<=14.8 |
| 28 | Exception Leader | 5D_clean_8v4 | 1 | 7 | 85.714 | 85.714 | 85.714 | 8.1079 | 0.0 | alpha_score<=95.25<br>alpha_score<=100<br>priority_rank<=11 |
| 29 | Exception Leader | 5D_clean_8v4 | 1 | 7 | 85.714 | 85.714 | 85.714 | 8.1079 | 0.0 | alpha_score<=95.25<br>alpha_score<=100<br>priority_rank<=14.8 |
| 30 | Exception Leader | 5D_clean_8v4 | 1 | 7 | 85.714 | 85.714 | 85.714 | 8.1079 | 0.0 | alpha_score<=95.25<br>priority_rank<=14.8<br>selection_lane=3d |

## Fold Ranges
- fold `1`: train `2026-03-30` to `2026-04-09`, test `2026-04-10` to `2026-04-17`
- fold `2`: train `2026-03-30` to `2026-04-17`, test `2026-04-19` to `2026-04-26`
- fold `3`: train `2026-03-30` to `2026-04-26`, test `2026-04-27` to `2026-05-06`
- fold `4`: train `2026-03-30` to `2026-05-06`, test `2026-05-07` to `2026-05-13`

## Notes
- KOSPI-only shadow search. Production scanner logic is unchanged.
- Rules are searched on multiple simple train/test ratios, then rechecked on rolling time folds.
- Primary theme is not used as a condition because fixed themes rotate and overfit.
- Archive labels are still proxy labels; any production candidate must be revalidated with ordered OHLCV path labels.
