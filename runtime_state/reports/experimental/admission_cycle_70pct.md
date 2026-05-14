# Admission Cycle 70pct Shadow Search

- generated_at: `2026-05-14T05:39:13.991035+00:00`
- mode: `shadow_only_not_production`
- input_rows: `4335`
- config: `{'max_depth': 3, 'beam_width': 150, 'min_train': 20, 'min_test': 8, 'max_conditions': 180, 'train_ratio': 0.7, 'run_ml': True}`

## Holdout Champions

| rank | market | cohort | profile | test_n | test_win | test_avg_5d | test_stop5 | train_n | train_win | conditions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | KOSPI | All | 5D_clean_10v5 | 11 | 90.909 | 9.836 | 0.0 | 55 | 38.182 | ml_prob<=24.9<br>prob_clean>=32.4 |
| 2 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 88.889 | 10.7048 | 0.0 | 21 | 66.667 | prob_clean<=31.8<br>decision_score>=100<br>explosive_leader_flag=0 |
| 3 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 88.889 | 10.7048 | 0.0 | 24 | 62.5 | prob_clean<=31.8<br>decision_score>=93.26<br>explosive_leader_flag=0 |
| 4 | KOSPI | Top3 | 5D_clean_10v5 | 8 | 87.5 | 8.4654 | 0.0 | 23 | 52.174 | ml_prob<=34.65<br>decision_score>=100<br>kr_universe_role=CORE_TREND |
| 5 | KOSPI | Top3 | 5D_clean_10v5 | 8 | 87.5 | 8.4654 | 0.0 | 27 | 55.556 | ml_prob<=34.65<br>decision_score>=100<br>explosive_leader_flag=0 |
| 6 | KOSPI | Top3 | 5D_clean_10v5 | 8 | 87.5 | 8.4654 | 0.0 | 23 | 52.174 | ml_prob<=34.65<br>decision_score>=100<br>core_trend_flag=1 |
| 7 | KOSPI | All | 5D_clean_10v5 | 12 | 83.333 | 7.8882 | 16.667 | 35 | 40.0 | expected_edge_score<=-8.34<br>phase25_prob<=6.1 |
| 8 | KOSPI | All | 5D_clean_10v5 | 12 | 83.333 | 7.8882 | 16.667 | 34 | 38.235 | expected_return_3d_pct<=-1.01<br>phase25_prob<=6.1 |
| 9 | KOSDAQ | Top3 | 5D_clean_10v5 | 11 | 81.818 | 10.1843 | 0.0 | 21 | 42.857 | ml_prob<=50<br>prob_clean<=31.3<br>trend=UP |
| 10 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | prob_clean<=31.8<br>explosive_leader_flag=0 |
| 11 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | prob_clean<=31.8<br>prob_clean<=35.385<br>explosive_leader_flag=0 |
| 12 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | prob_clean<=31.8<br>prob_clean<=50<br>explosive_leader_flag=0 |
| 13 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | prob_clean<=31.8<br>priority_rank>=1<br>explosive_leader_flag=0 |
| 14 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | prob_clean<=31.8<br>priority_rank<=3<br>explosive_leader_flag=0 |
| 15 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | prob_clean<=31.8<br>selection_lane=3d<br>explosive_leader_flag=0 |
| 16 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | prob_clean<=31.8<br>scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH<br>explosive_leader_flag=0 |
| 17 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | ml_prob<=50<br>prob_clean<=31.8<br>explosive_leader_flag=0 |
| 18 | KOSPI | Top3 | 5D_clean_10v5 | 10 | 80.0 | 8.9525 | 10.0 | 33 | 54.545 | prob_clean<=31.8<br>explosive_leader_flag=0<br>explosive_eligible=1 |
| 19 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>kr_universe_role=CORE_TREND |
| 20 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>core_trend_flag=1 |
| 21 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>prob_clean<=35.385<br>kr_universe_role=CORE_TREND |
| 22 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>prob_clean<=35.385<br>core_trend_flag=1 |
| 23 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>prob_clean<=50<br>kr_universe_role=CORE_TREND |
| 24 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>prob_clean<=50<br>core_trend_flag=1 |
| 25 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>priority_rank>=1<br>kr_universe_role=CORE_TREND |
| 26 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>priority_rank>=1<br>core_trend_flag=1 |
| 27 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>priority_rank<=3<br>kr_universe_role=CORE_TREND |
| 28 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>priority_rank<=3<br>core_trend_flag=1 |
| 29 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>selection_lane=3d<br>kr_universe_role=CORE_TREND |
| 30 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>selection_lane=3d<br>core_trend_flag=1 |

## 70pct+ Holdout Candidates

- `KOSPI` / `All` / `5D_clean_10v5`: test win `90.909`% n=`11`, train win `38.182`% n=`55`; conditions=['ml_prob<=24.9', 'prob_clean>=32.4']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `88.889`% n=`9`, train win `66.667`% n=`21`; conditions=['prob_clean<=31.8', 'decision_score>=100', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `88.889`% n=`9`, train win `62.5`% n=`24`; conditions=['prob_clean<=31.8', 'decision_score>=93.26', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `87.5`% n=`8`, train win `52.174`% n=`23`; conditions=['ml_prob<=34.65', 'decision_score>=100', 'kr_universe_role=CORE_TREND']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `87.5`% n=`8`, train win `55.556`% n=`27`; conditions=['ml_prob<=34.65', 'decision_score>=100', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `87.5`% n=`8`, train win `52.174`% n=`23`; conditions=['ml_prob<=34.65', 'decision_score>=100', 'core_trend_flag=1']
- `KOSPI` / `All` / `5D_clean_10v5`: test win `83.333`% n=`12`, train win `40.0`% n=`35`; conditions=['expected_edge_score<=-8.34', 'phase25_prob<=6.1']
- `KOSPI` / `All` / `5D_clean_10v5`: test win `83.333`% n=`12`, train win `38.235`% n=`34`; conditions=['expected_return_3d_pct<=-1.01', 'phase25_prob<=6.1']
- `KOSDAQ` / `Top3` / `5D_clean_10v5`: test win `81.818`% n=`11`, train win `42.857`% n=`21`; conditions=['ml_prob<=50', 'prob_clean<=31.3', 'trend=UP']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['prob_clean<=31.8', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['prob_clean<=31.8', 'prob_clean<=35.385', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['prob_clean<=31.8', 'prob_clean<=50', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['prob_clean<=31.8', 'priority_rank>=1', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['prob_clean<=31.8', 'priority_rank<=3', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['prob_clean<=31.8', 'selection_lane=3d', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['prob_clean<=31.8', 'scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['ml_prob<=50', 'prob_clean<=31.8', 'explosive_leader_flag=0']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `80.0`% n=`10`, train win `54.545`% n=`33`; conditions=['prob_clean<=31.8', 'explosive_leader_flag=0', 'explosive_eligible=1']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `77.778`% n=`9`, train win `50.0`% n=`28`; conditions=['prob_clean<=31.8', 'kr_universe_role=CORE_TREND']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `77.778`% n=`9`, train win `50.0`% n=`28`; conditions=['prob_clean<=31.8', 'core_trend_flag=1']

## Stable Candidates

- `train>=60/test>=70`: `KOSPI` / `Top3` / `5D_clean_10v5` test `88.889`% n=`9`, train `66.667`% n=`21`, stop5 `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=100', 'explosive_leader_flag=0']
- `train>=60/test>=70`: `KOSPI` / `Top3` / `5D_clean_10v5` test `88.889`% n=`9`, train `62.5`% n=`24`, stop5 `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=93.26', 'explosive_leader_flag=0']
- `train>=60/test>=70`: `KOSDAQ` / `Exception Leader` / `5D_clean_10v5` test `75.0`% n=`8`, train `60.0`% n=`35`, stop5 `25.0`%, conditions=['alpha_score>=34', 'ml_prob>=21.3', 'priority_rank>=4']
- `train>=60/test>=70`: `KOSPI` / `Top3` / `5D_clean_10v5` test `75.0`% n=`12`, train `60.0`% n=`25`, stop5 `0.0`%, conditions=['prob_clean<=35.385', 'decision_score>=100', 'explosive_leader_flag=0']
- `train>=60/test>=70`: `KOSPI` / `Top3` / `3D_close_5v3_no_5d_stop` test `75.0`% n=`8`, train `65.0`% n=`20`, stop5 `12.5`%, conditions=['ml_prob<=35.6', 'prob_clean<=28.575', 'kr_universe_role=CORE_TREND']
- `train>=60/test>=70`: `KOSPI` / `Top3` / `3D_close_5v3_no_5d_stop` test `75.0`% n=`8`, train `61.905`% n=`21`, stop5 `12.5`%, conditions=['ml_prob<=35.6', 'prob_clean<=28.575', 'explosive_leader_flag=0']
- `train>=60/test>=70`: `KOSPI` / `Top3` / `3D_close_5v3_no_5d_stop` test `75.0`% n=`8`, train `65.0`% n=`20`, stop5 `12.5`%, conditions=['ml_prob<=35.6', 'prob_clean<=28.575', 'core_trend_flag=1']

## Strict 70/70 Candidates

- None.

## Notes
- This is an internal admission cycle only; production scanner logic is unchanged.
- 5D clean labels use archive high/low proxy: target MFE reached and stop MAE not breached.
- 1D/3D labels use close-return target plus no 5D stop breach, so they are conservative but not exact intraday order labels.
- Primary theme values are intentionally excluded from rule features because themes rotate and fixed-theme rules overfit.
