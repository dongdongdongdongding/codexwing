# Admission Cycle 70pct Shadow Search

- generated_at: `2026-05-20T09:07:32.936002+00:00`
- mode: `shadow_only_not_production`
- input_rows: `5914`
- config: `{'max_depth': 3, 'beam_width': 180, 'min_train': 20, 'min_test': 8, 'max_conditions': 240, 'train_ratio': 0.7, 'run_ml': True}`

## Holdout Champions

| rank | market | cohort | profile | test_n | test_win | test_avg_5d | test_stop5 | train_n | train_win | conditions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | KOSPI | All | 3D_close_5v3_no_5d_stop | 10 | 70.0 | 7.4092 | 10.0 | 29 | 41.379 | tech_score>=85<br>tech_score<=85<br>prob_clean>=29.4 |
| 2 | KOSDAQ | All | 5D_clean_10v5 | 9 | 66.667 | 4.3325 | 33.333 | 20 | 20.0 | tech_score<=70<br>priority_rank>=57 |
| 3 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 2.1142 | 11.111 | 20 | 25.0 | tech_score>=85<br>feature_quality=incomplete |
| 4 | KOSPI | Top5+Exception | 5D_clean_10v5 | 9 | 66.667 | 2.1142 | 11.111 | 20 | 45.0 | tech_score>=85<br>feature_quality=incomplete |
| 5 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 42 | 40.476 | alpha_score>=71<br>decision_score>=111.912 |
| 6 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 42 | 40.476 | alpha_score>=71<br>decision_score>=111.912<br>trend=UP |
| 7 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 39 | 41.026 | alpha_score>=71<br>decision_score>=111.912<br>selection_lane=3d |
| 8 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 39 | 41.026 | alpha_score>=71<br>decision_score>=111.912<br>kr_universe_role=CORE_TREND |
| 9 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 39 | 41.026 | alpha_score>=71<br>decision_score>=111.912<br>scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH |
| 10 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 42 | 40.476 | alpha_score>=71<br>decision_score>=111.912<br>feature_quality=incomplete |
| 11 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 39 | 38.462 | alpha_score>=71<br>decision_score>=111.912<br>feature_origin=scanner_archive_outcome |
| 12 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 39 | 41.026 | alpha_score>=71<br>decision_score>=111.912<br>explosive_leader_flag=0 |
| 13 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 39 | 41.026 | alpha_score>=71<br>decision_score>=111.912<br>core_trend_flag=1 |
| 14 | KOSPI | Top5+Exception | 3D_close_5v3_no_5d_stop | 9 | 66.667 | 1.2463 | 0.0 | 42 | 40.476 | alpha_score>=71<br>decision_score>=111.912<br>explosive_eligible=1 |
| 15 | KOSPI | Top5+Exception | 5D_clean_10v5 | 9 | 66.667 | 1.2463 | 0.0 | 42 | 50.0 | alpha_score>=71<br>decision_score>=112.008 |
| 16 | KOSPI | Top5 | 3D_close_5v3_no_5d_stop | 12 | 66.667 | 0.3781 | 25.0 | 26 | 26.923 | ml_prob>=22.34<br>ml_prob<=27 |
| 17 | KOSPI | All | 5D_clean_10v5 | 15 | 66.667 | -1.1173 | 33.333 | 20 | 60.0 | whale_score>=80<br>whale_score<=80<br>priority_rank>=7 |
| 18 | KOSPI | All | 5D_clean_10v5 | 11 | 63.636 | 5.0727 | 36.364 | 250 | 63.6 | extra_trees_shadow_prob>=train_q0.8:0.5480 |
| 19 | KOSPI | All | 5D_clean_10v5 | 11 | 63.636 | 4.6641 | 36.364 | 21 | 57.143 | tech_score>=65<br>expected_edge_score>=-1.45<br>position=🌋 고점 (Peak) |
| 20 | KOSPI | All | 5D_clean_10v5 | 11 | 63.636 | 4.6641 | 36.364 | 21 | 57.143 | tech_score>=65<br>expected_return_1d_pct>=-0.11<br>position=🌋 고점 (Peak) |
| 21 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 28 | 35.714 | decision_score>=90.68<br>feature_quality=incomplete |
| 22 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 22 | 40.909 | alpha_score<=100<br>decision_score>=90.68<br>feature_quality=incomplete |
| 23 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 21 | 38.095 | ml_prob>=22.56<br>decision_score>=90.68<br>feature_quality=incomplete |
| 24 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 27 | 37.037 | decision_score>=90.68<br>trend=UP<br>feature_quality=incomplete |
| 25 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 28 | 35.714 | decision_score>=90.68<br>priority_rank>=1<br>feature_quality=incomplete |
| 26 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 28 | 35.714 | decision_score>=90.68<br>priority_rank<=1<br>feature_quality=incomplete |
| 27 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 28 | 35.714 | decision_score>=90.68<br>selection_lane=3d<br>feature_quality=incomplete |
| 28 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 28 | 35.714 | decision_score>=90.68<br>scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH<br>feature_quality=incomplete |
| 29 | KOSPI | Top1 | 3D_close_5v3_no_5d_stop | 11 | 63.636 | 2.5358 | 27.273 | 28 | 35.714 | decision_score>=90.68<br>feature_quality=incomplete<br>explosive_eligible=1 |
| 30 | KOSPI | Top3 | 5D_clean_10v5 | 11 | 63.636 | 0.251 | 36.364 | 42 | 76.19 | hist_gb_shadow_prob>=train_q0.6:0.4849 |

## 70pct+ Holdout Candidates

- `KOSPI` / `All` / `3D_close_5v3_no_5d_stop`: test win `70.0`% n=`10`, train win `41.379`% n=`29`; conditions=['tech_score>=85', 'tech_score<=85', 'prob_clean>=29.4']

## Stable Candidates

- No candidate met train>=60% and test>=70%.

## Strict 70/70 Candidates

- None.

## Notes
- This is an internal admission cycle only; production scanner logic is unchanged.
- 5D clean labels use archive high/low proxy: target MFE reached and stop MAE not breached.
- 1D/3D labels use close-return target plus no 5D stop breach, so they are conservative but not exact intraday order labels.
- Primary theme values are intentionally excluded from rule features because themes rotate and fixed-theme rules overfit.
