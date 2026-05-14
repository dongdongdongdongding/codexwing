# KOSPI Admission Robust Search

- generated_at: `2026-05-14T11:23:13.364983+00:00`
- mode: `shadow_only_not_production`
- kospi_rows: `2462`
- raw_candidate_count: `1202`
- evaluated_candidate_count: `105`
- config: `{'train_ratios': [0.6, 0.7], 'max_depth': 2, 'beam_width': 60, 'min_train': 20, 'min_test': 8, 'max_conditions': 100, 'top_per_split': 30, 'rolling_folds': 4, 'min_train_days': 8, 'min_fold_test': 4}`

## Strict 70pct Candidates

- None.

## Stable 70pct Candidates

- None.

## Top Champions

| rank | cohort | profile | folds | n | weighted_win | min_win | median_win | avg5 | max_stop | conditions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Exception Leader | 5D_clean_8v4 | 1 | 8 | 100.0 | 100.0 | 100.0 | 10.4593 | 0.0 | priority_rank>=5<br>priority_rank<=9 |
| 2 | Exception Leader | 5D_clean_10v5 | 1 | 8 | 87.5 | 87.5 | 87.5 | 10.4593 | 0.0 | priority_rank>=5<br>priority_rank<=9 |
| 3 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9 |
| 4 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | alpha_score<=100<br>priority_rank<=9 |
| 5 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9<br>selection_lane=3d |
| 6 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9<br>kr_universe_role=CORE_TREND |
| 7 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9<br>scanner_timeframe_profile=DAILY_PRIMARY_WITH_1H_REFRESH |
| 8 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9<br>feature_quality=incomplete |
| 9 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9<br>feature_origin=scanner_archive_outcome |
| 10 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9<br>explosive_leader_flag=0 |
| 11 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9<br>core_trend_flag=1 |
| 12 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | priority_rank<=9<br>explosive_eligible=1 |
| 13 | Exception Leader | 5D_clean_8v4 | 1 | 15 | 80.0 | 80.0 | 80.0 | 9.8541 | 0.0 | decision_score<=119<br>priority_rank<=9 |
| 14 | Exception Leader | 5D_clean_10v5 | 1 | 15 | 73.333 | 73.333 | 73.333 | 9.8541 | 0.0 | priority_rank<=9 |
| 15 | Exception Leader | 5D_clean_10v5 | 1 | 15 | 73.333 | 73.333 | 73.333 | 9.8541 | 0.0 | alpha_score<=100<br>priority_rank<=9 |
| 16 | Exception Leader | 5D_clean_10v5 | 1 | 15 | 73.333 | 73.333 | 73.333 | 9.8541 | 0.0 | decision_score<=119<br>priority_rank<=9 |
| 17 | Exception Leader | 5D_clean_8v4 | 1 | 23 | 65.217 | 65.217 | 65.217 | 8.0501 | 8.696 | priority_rank>=5 |
| 18 | Exception Leader | 5D_clean_8v4 | 1 | 30 | 63.333 | 63.333 | 63.333 | 8.3096 | 6.667 | BASE |
| 19 | Exception Leader | 5D_clean_8v4 | 1 | 30 | 63.333 | 63.333 | 63.333 | 8.3096 | 6.667 | alpha_score<=100 |
| 20 | Exception Leader | 5D_clean_8v4 | 1 | 30 | 63.333 | 63.333 | 63.333 | 8.3096 | 6.667 | decision_score<=119 |
| 21 | Exception Leader | 5D_clean_8v4 | 1 | 30 | 63.333 | 63.333 | 63.333 | 8.3096 | 6.667 | feature_quality=incomplete |
| 22 | Exception Leader | 5D_clean_8v4 | 1 | 30 | 63.333 | 63.333 | 63.333 | 8.3096 | 6.667 | feature_origin=scanner_archive_outcome |
| 23 | Exception Leader | 5D_clean_8v4 | 1 | 30 | 63.333 | 63.333 | 63.333 | 8.3096 | 6.667 | explosive_eligible=1 |
| 24 | Exception Leader | 5D_clean_8v4 | 1 | 26 | 57.692 | 57.692 | 57.692 | 7.282 | 7.692 | trend=UP |
| 25 | Exception Leader | 5D_clean_8v4 | 1 | 23 | 56.522 | 56.522 | 56.522 | 7.4056 | 8.696 | decision_score>=119 |
| 26 | Exception Leader | 5D_clean_10v5 | 1 | 30 | 53.333 | 53.333 | 53.333 | 8.3096 | 6.667 | BASE |
| 27 | Exception Leader | 5D_clean_10v5 | 1 | 30 | 53.333 | 53.333 | 53.333 | 8.3096 | 6.667 | alpha_score<=100 |
| 28 | Exception Leader | 5D_clean_10v5 | 1 | 30 | 53.333 | 53.333 | 53.333 | 8.3096 | 6.667 | decision_score<=119 |
| 29 | Exception Leader | 5D_clean_10v5 | 1 | 30 | 53.333 | 53.333 | 53.333 | 8.3096 | 6.667 | feature_quality=incomplete |
| 30 | Exception Leader | 5D_clean_10v5 | 1 | 30 | 53.333 | 53.333 | 53.333 | 8.3096 | 6.667 | feature_origin=scanner_archive_outcome |

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
