# KOSPI Admission Robust Search

- generated_at: `2026-05-14T11:59:00.827830+00:00`
- mode: `shadow_only_not_production`
- kospi_rows: `2462`
- raw_candidate_count: `2`
- evaluated_candidate_count: `2`
- config: `{'train_ratios': [], 'max_depth': 0, 'beam_width': 150, 'min_train': 20, 'min_test': 8, 'max_conditions': 180, 'top_per_split': 1, 'rolling_folds': 4, 'min_train_days': 8, 'min_fold_test': 2}`

## Strict 70pct Candidates

- None.

## Stable 70pct Candidates

- `Top3` / `5D_clean_10v5`: weighted `78.947`%, min_fold `62.5`%, median `80.0`%, n=`19`, avg5 `10.303`%, stop_max `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=100', 'explosive_leader_flag=0']
- `Top3` / `5D_clean_10v5`: weighted `76.191`%, min_fold `55.556`%, median `83.333`%, n=`21`, avg5 `10.5854`%, stop_max `0.0`%, conditions=['prob_clean<=31.8', 'decision_score>=93.26', 'explosive_leader_flag=0']

## Top Champions

| rank | cohort | profile | folds | n | weighted_win | min_win | median_win | avg5 | max_stop | conditions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Top3 | 5D_clean_10v5 | 3 | 19 | 78.947 | 62.5 | 80.0 | 10.303 | 0.0 | prob_clean<=31.8<br>decision_score>=100<br>explosive_leader_flag=0 |
| 2 | Top3 | 5D_clean_10v5 | 3 | 21 | 76.191 | 55.556 | 83.333 | 10.5854 | 0.0 | prob_clean<=31.8<br>decision_score>=93.26<br>explosive_leader_flag=0 |

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
