# Internal Retrain Candidate Sweep

- generated_at: `2026-05-27T13:54:04.758799+00:00`
- report_version: `internal_retrain_sweep_v1`
- input_rows: `4298`
- prepared_rows: `4298`
- completed_results: `1256`
- skipped_results: `0`

## Top Holdout Candidates

| Rank | Market | Cohort | Label | Feature Set | Model | TopN | Test N | Days | Label Win | 1D Win | 3D Win | 5D Win | Avg 5D | Min 5D | Max 5D | Bad Path | AUC |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | KOSPI | top5 | win_5d_pos | score_theme | logistic | 1 | 11 | 11 | 72.727 | 27.273 | 81.818 | 72.727 | 9.9188 | -18.7654 | 54.4834 | 63.636 | 0.655247 |
| 2 | KOSPI | top5 | win_5d_pos | wide_theme | logistic | 1 | 11 | 11 | 72.727 | 27.273 | 81.818 | 72.727 | 9.9188 | -18.7654 | 54.4834 | 63.636 | 0.655247 |
| 3 | KOSPI | top5_exception | win_5d_pos | score_theme | logistic | 1 | 11 | 11 | 72.727 | 27.273 | 81.818 | 72.727 | 9.9188 | -18.7654 | 54.4834 | 63.636 | 0.641778 |
| 4 | KOSPI | top5_exception | win_5d_pos | wide_theme | logistic | 1 | 11 | 11 | 72.727 | 27.273 | 81.818 | 72.727 | 9.9188 | -18.7654 | 54.4834 | 63.636 | 0.641778 |
| 5 | KOSPI | top5 | win_5d_pos | score_no_theme | logistic | 1 | 11 | 11 | 72.727 | 27.273 | 72.727 | 72.727 | 6.3027 | -18.7654 | 54.4834 | 63.636 | 0.641204 |
| 6 | KOSPI | top5 | win_5d_pos | score_flow_no_theme | logistic | 1 | 11 | 11 | 72.727 | 27.273 | 72.727 | 72.727 | 6.3027 | -18.7654 | 54.4834 | 63.636 | 0.641204 |
| 7 | KOSDAQ | core_trend | win_5d_pos | score_no_theme | hist_gb | 1 | 11 | 11 | 72.727 | 36.364 | 36.364 | 72.727 | 2.0963 | -29.2359 | 43.0878 | 54.546 | 0.540778 |
| 8 | KOSDAQ | core_trend | win_5d_pos | score_flow_no_theme | hist_gb | 1 | 11 | 11 | 72.727 | 36.364 | 36.364 | 72.727 | 2.0963 | -29.2359 | 43.0878 | 54.546 | 0.540778 |
| 9 | KOSDAQ | all | win_1d_pos | score_no_theme | lightgbm | 1 | 12 | 12 | 33.333 | 33.333 | 44.444 | 66.667 | 10.5377 | -5.0173 | 41.4424 | 58.333 | 0.502934 |
| 10 | KOSDAQ | all | win_1d_pos | score_flow_no_theme | lightgbm | 1 | 12 | 12 | 33.333 | 33.333 | 44.444 | 66.667 | 10.5377 | -5.0173 | 41.4424 | 58.333 | 0.502934 |
| 11 | KOSDAQ | all | win_3d_pos | score_theme | hist_gb | 1 | 11 | 11 | 45.454 | 54.546 | 45.454 | 66.667 | 6.3201 | -16.2319 | 46.2585 | 63.636 | 0.494561 |
| 12 | KOSDAQ | all | win_3d_pos | wide_theme | hist_gb | 1 | 11 | 11 | 45.454 | 54.546 | 45.454 | 66.667 | 6.3201 | -16.2319 | 46.2585 | 63.636 | 0.494561 |
| 13 | KOSDAQ | all | win_1d_pos | score_no_theme | extra_trees | 1 | 12 | 12 | 33.333 | 33.333 | 77.778 | 66.667 | 3.8735 | -19.7111 | 31.1475 | 50.0 | 0.521585 |
| 14 | KOSDAQ | all | win_1d_pos | score_flow_no_theme | extra_trees | 1 | 12 | 12 | 33.333 | 33.333 | 77.778 | 66.667 | 3.8735 | -19.7111 | 31.1475 | 50.0 | 0.521585 |
| 15 | KOSPI | top5_exception | win_5d_pos | score_no_theme | logistic | 1 | 11 | 11 | 63.636 | 27.273 | 63.636 | 63.636 | 4.6513 | -18.7654 | 54.4834 | 63.636 | 0.640741 |
| 16 | KOSPI | top5_exception | win_5d_pos | score_flow_no_theme | logistic | 1 | 11 | 11 | 63.636 | 27.273 | 63.636 | 63.636 | 4.6513 | -18.7654 | 54.4834 | 63.636 | 0.640741 |
| 17 | KOSDAQ | core_trend | win_5d_pos | score_theme | lightgbm | 1 | 11 | 11 | 63.636 | 54.546 | 72.727 | 63.636 | 2.6095 | -24.0506 | 22.1973 | 63.636 | 0.566899 |
| 18 | KOSDAQ | core_trend | win_5d_pos | wide_theme | lightgbm | 1 | 11 | 11 | 63.636 | 54.546 | 72.727 | 63.636 | 2.6095 | -24.0506 | 22.1973 | 63.636 | 0.566899 |
| 19 | KOSDAQ | core_trend | win_1d_pos | score_no_theme | logistic | 1 | 12 | 12 | 33.333 | 33.333 | 55.556 | 57.143 | 2.1638 | -33.0228 | 55.5862 | 75.0 | 0.51544 |
| 20 | KOSDAQ | core_trend | win_1d_pos | score_flow_no_theme | logistic | 1 | 12 | 12 | 33.333 | 33.333 | 55.556 | 57.143 | 2.1638 | -33.0228 | 55.5862 | 75.0 | 0.51544 |
| 21 | KOSDAQ | top5 | win_1d_pos | score_no_theme | extra_trees | 1 | 12 | 12 | 33.333 | 33.333 | 44.444 | 57.143 | -1.9399 | -46.3097 | 23.5005 | 58.333 | 0.652232 |
| 22 | KOSDAQ | top5 | win_1d_pos | score_flow_no_theme | extra_trees | 1 | 12 | 12 | 33.333 | 33.333 | 44.444 | 57.143 | -1.9399 | -46.3097 | 23.5005 | 58.333 | 0.652232 |
| 23 | KOSDAQ | core_trend | win_1d_pos | score_no_theme | lightgbm | 1 | 12 | 12 | 33.333 | 33.333 | 55.556 | 57.143 | -2.2126 | -27.3349 | 37.5748 | 83.333 | 0.592154 |
| 24 | KOSDAQ | core_trend | win_1d_pos | score_flow_no_theme | lightgbm | 1 | 12 | 12 | 33.333 | 33.333 | 55.556 | 57.143 | -2.2126 | -27.3349 | 37.5748 | 83.333 | 0.592154 |
| 25 | KOSDAQ | core_trend | win_1d_pos | score_no_theme | hist_gb | 1 | 12 | 12 | 41.667 | 41.667 | 44.444 | 57.143 | -6.5975 | -27.3349 | 6.7769 | 50.0 | 0.570124 |
| 26 | KOSDAQ | core_trend | win_1d_pos | score_flow_no_theme | hist_gb | 1 | 12 | 12 | 41.667 | 41.667 | 44.444 | 57.143 | -6.5975 | -27.3349 | 6.7769 | 50.0 | 0.570124 |
| 27 | KOSDAQ | core_trend | win_5d_pos | score_theme | hist_gb | 3 | 32 | 11 | 56.25 | 40.625 | 46.875 | 56.25 | 2.8624 | -29.5561 | 60.9508 | 68.75 | 0.57473 |
| 28 | KOSDAQ | core_trend | win_5d_pos | wide_theme | hist_gb | 3 | 32 | 11 | 56.25 | 40.625 | 46.875 | 56.25 | 2.8624 | -29.5561 | 60.9508 | 68.75 | 0.57473 |
| 29 | KOSPI | explosive_leader | target_5d_10v5 | score_no_theme | extra_trees | 3 | 18 | 6 | 38.889 | 22.222 | 44.444 | 55.556 | 2.8406 | -31.2057 | 56.4417 | 77.778 | 0.58493 |
| 30 | KOSPI | explosive_leader | target_5d_10v5 | score_flow_no_theme | extra_trees | 3 | 18 | 6 | 38.889 | 22.222 | 44.444 | 55.556 | 2.8406 | -31.2057 | 56.4417 | 77.778 | 0.58493 |
| 31 | KOSDAQ | all | win_3d_pos | score_theme | xgboost | 1 | 11 | 11 | 36.364 | 63.636 | 36.364 | 55.556 | 1.6394 | -17.6617 | 26.1128 | 72.727 | 0.497658 |
| 32 | KOSDAQ | all | win_3d_pos | wide_theme | xgboost | 1 | 11 | 11 | 36.364 | 63.636 | 36.364 | 55.556 | 1.6394 | -17.6617 | 26.1128 | 72.727 | 0.497658 |
| 33 | KOSPI | ranked_top20 | win_3d_pos | score_theme | hist_gb | 1 | 11 | 11 | 54.546 | 63.636 | 54.546 | 55.556 | 0.1487 | -9.9747 | 14.4687 | 63.636 | 0.549437 |
| 34 | KOSPI | ranked_top20 | win_3d_pos | wide_theme | hist_gb | 1 | 11 | 11 | 54.546 | 63.636 | 54.546 | 55.556 | 0.1487 | -9.9747 | 14.4687 | 63.636 | 0.549437 |
| 35 | KOSDAQ | all | win_3d_pos | score_theme | lightgbm | 1 | 11 | 11 | 36.364 | 45.454 | 36.364 | 55.556 | -0.4997 | -29.2359 | 26.1128 | 72.727 | 0.520466 |
| 36 | KOSDAQ | all | win_3d_pos | wide_theme | lightgbm | 1 | 11 | 11 | 36.364 | 45.454 | 36.364 | 55.556 | -0.4997 | -29.2359 | 26.1128 | 72.727 | 0.520466 |
| 37 | KOSPI | ranked_top20 | win_3d_pos | score_theme | xgboost | 1 | 11 | 11 | 54.546 | 63.636 | 54.546 | 55.556 | -1.6423 | -18.1818 | 14.4687 | 63.636 | 0.561478 |
| 38 | KOSPI | ranked_top20 | win_3d_pos | wide_theme | xgboost | 1 | 11 | 11 | 54.546 | 63.636 | 54.546 | 55.556 | -1.6423 | -18.1818 | 14.4687 | 63.636 | 0.561478 |
| 39 | KOSPI | ranked_top20 | win_5d_pos | score_no_theme | logistic | 1 | 11 | 11 | 54.546 | 63.636 | 54.546 | 54.546 | 17.4897 | -12.8527 | 97.0266 | 63.636 | 0.537054 |
| 40 | KOSPI | ranked_top20 | win_5d_pos | score_flow_no_theme | logistic | 1 | 11 | 11 | 54.546 | 63.636 | 54.546 | 54.546 | 17.4897 | -12.8527 | 97.0266 | 63.636 | 0.537054 |
| 41 | KOSPI | ranked_top20 | win_5d_pos | score_theme | logistic | 1 | 11 | 11 | 54.546 | 63.636 | 45.454 | 54.546 | 12.9744 | -12.8527 | 97.0266 | 72.727 | 0.537642 |
| 42 | KOSPI | ranked_top20 | win_5d_pos | wide_theme | logistic | 1 | 11 | 11 | 54.546 | 63.636 | 45.454 | 54.546 | 12.9744 | -12.8527 | 97.0266 | 72.727 | 0.537642 |
| 43 | KOSDAQ | top5 | win_5d_pos | score_theme | extra_trees | 1 | 11 | 11 | 54.546 | 27.273 | 54.546 | 54.546 | 5.8914 | -23.1707 | 37.5748 | 81.818 | 0.57285 |
| 44 | KOSDAQ | top5 | win_5d_pos | wide_theme | extra_trees | 1 | 11 | 11 | 54.546 | 27.273 | 54.546 | 54.546 | 5.8914 | -23.1707 | 37.5748 | 81.818 | 0.57285 |
| 45 | KOSDAQ | top5_exception | win_5d_pos | score_no_theme | catboost | 1 | 11 | 11 | 54.546 | 27.273 | 36.364 | 54.546 | 5.8547 | -19.5531 | 37.5748 | 90.909 | 0.437037 |
| 46 | KOSDAQ | top5_exception | win_5d_pos | score_flow_no_theme | catboost | 1 | 11 | 11 | 54.546 | 27.273 | 36.364 | 54.546 | 5.8547 | -19.5531 | 37.5748 | 90.909 | 0.437037 |
| 47 | KOSDAQ | core_trend | win_5d_pos | score_theme | random_forest | 1 | 11 | 11 | 54.546 | 36.364 | 54.546 | 54.546 | 2.6909 | -23.953 | 23.5084 | 81.818 | 0.579257 |
| 48 | KOSDAQ | core_trend | win_5d_pos | wide_theme | random_forest | 1 | 11 | 11 | 54.546 | 36.364 | 54.546 | 54.546 | 2.6909 | -23.953 | 23.5084 | 81.818 | 0.579257 |
| 49 | KOSDAQ | core_trend | win_5d_pos | score_theme | catboost | 1 | 11 | 11 | 54.546 | 45.454 | 45.454 | 54.546 | 2.0965 | -29.2359 | 23.5084 | 81.818 | 0.553757 |
| 50 | KOSDAQ | core_trend | win_5d_pos | wide_theme | catboost | 1 | 11 | 11 | 54.546 | 45.454 | 45.454 | 54.546 | 2.0965 | -29.2359 | 23.5084 | 81.818 | 0.553757 |
| 51 | KOSDAQ | core_trend | win_5d_pos | score_theme | xgboost | 1 | 11 | 11 | 54.546 | 45.454 | 54.546 | 54.546 | 0.3687 | -23.953 | 22.1973 | 63.636 | 0.561733 |
| 52 | KOSDAQ | core_trend | win_5d_pos | wide_theme | xgboost | 1 | 11 | 11 | 54.546 | 45.454 | 54.546 | 54.546 | 0.3687 | -23.953 | 22.1973 | 63.636 | 0.561733 |
| 53 | KOSPI | ranked_top20 | win_5d_pos | score_no_theme | lightgbm | 1 | 11 | 11 | 54.546 | 63.636 | 63.636 | 54.546 | -0.8226 | -17.8016 | 14.1925 | 72.727 | 0.454784 |
| 54 | KOSPI | ranked_top20 | win_5d_pos | score_flow_no_theme | lightgbm | 1 | 11 | 11 | 54.546 | 63.636 | 63.636 | 54.546 | -0.8226 | -17.8016 | 14.1925 | 72.727 | 0.454784 |
| 55 | KOSDAQ | core_trend | win_5d_pos | score_no_theme | random_forest | 1 | 11 | 11 | 54.546 | 27.273 | 27.273 | 54.546 | -1.3 | -29.2359 | 23.5084 | 72.727 | 0.557572 |
| 56 | KOSDAQ | core_trend | win_5d_pos | score_flow_no_theme | random_forest | 1 | 11 | 11 | 54.546 | 27.273 | 27.273 | 54.546 | -1.3 | -29.2359 | 23.5084 | 72.727 | 0.557572 |
| 57 | KOSDAQ | all | win_5d_pos | score_no_theme | lightgbm | 1 | 11 | 11 | 54.546 | 36.364 | 54.546 | 54.546 | -2.6456 | -29.2359 | 13.4415 | 81.818 | 0.530702 |
| 58 | KOSDAQ | all | win_5d_pos | score_flow_no_theme | lightgbm | 1 | 11 | 11 | 54.546 | 36.364 | 54.546 | 54.546 | -2.6456 | -29.2359 | 13.4415 | 81.818 | 0.530702 |
| 59 | KOSDAQ | core_trend | win_5d_pos | score_no_theme | lightgbm | 1 | 11 | 11 | 54.546 | 27.273 | 18.182 | 54.546 | -4.7253 | -29.2359 | 8.091 | 63.636 | 0.556951 |
| 60 | KOSDAQ | core_trend | win_5d_pos | score_flow_no_theme | lightgbm | 1 | 11 | 11 | 54.546 | 27.273 | 18.182 | 54.546 | -4.7253 | -29.2359 | 8.091 | 63.636 | 0.556951 |

## Baseline Reference

### KOSPI
- `top5` n=`390` 5D win=`52.051` avg=`1.9538` min=`-29.9776` max=`97.5155` bad_path=`59.41`
- `exception_leader` n=`63` 5D win=`73.016` avg=`7.5298` min=`-16.6118` max=`41.5809` bad_path=`40.298`
- `top5_exception` n=`453` 5D win=`54.967` avg=`2.7293` min=`-29.9776` max=`97.5155` bad_path=`56.89`
### KOSDAQ
- `top5` n=`281` 5D win=`46.619` avg=`1.0063` min=`-46.3097` max=`56.9153` bad_path=`67.213`
- `exception_leader` n=`184` 5D win=`54.348` avg=`2.3702` min=`-34.8118` max=`65.653` bad_path=`59.735`
- `top5_exception` n=`465` 5D win=`49.677` avg=`1.546` min=`-46.3097` max=`65.653` bad_path=`64.03`

## Notes
- Internal research only; production scanner and model artifacts are unchanged.
- Training uses chronological split by trade_date and scan-time features only.
- Stage 1 searches broad combinations with fast models; stage 2 refines the best base configurations with RF/XGBoost/LightGBM/CatBoost.
- Candidate ranking prioritizes adequate holdout sample, safer path, 5D win rate, 5D average return, bad-path rate, stop proxy, and only then label win.
- Theme-inclusive feature sets are reported separately because fixed theme effects can overfit rotating market themes.
