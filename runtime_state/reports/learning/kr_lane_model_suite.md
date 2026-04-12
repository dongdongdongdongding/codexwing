# KR Lane Model Suite

- generated_at: 2026-04-10T13:55:36.539517+00:00
- target_return_pct: 10.0
- target_win_rate_pct: 75.0

## Overall Champion
- segment: `kospi_core_3d`
- model: `lightgbm`
- avg_return_pct: `+8.76%`
- win_rate_pct: `90.00%`
- hit10_precision_pct: `45.00%`
- target_gap: `0.1236`
- auc: `0.718414`
- saved_model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/kr_lane_champions/kospi_core_3d__lightgbm.pkl`

## kospi_core_1d
- description: `KOSPI core trend 1D`
- rows: `1534` | days `8` | holdout days `2`
- train `2026-03-31 -> 2026-04-07` | test `2026-04-08 -> 2026-04-09`
- positive_rate_train: `68.83%` | positive_rate_test: `50.34%`
- champion: `xgboost` | avg_return `+3.13%` | win `80.00%` | hit10 `0.00%` | target_gap `0.6869` | auc `0.589041`

## kospi_core_3d
- description: `KOSPI core trend 3D`
- rows: `988` | days `6` | holdout days `2`
- train `2026-03-31 -> 2026-04-03` | test `2026-04-06 -> 2026-04-07`
- positive_rate_train: `51.20%` | positive_rate_test: `83.78%`
- champion: `lightgbm` | avg_return `+8.76%` | win `90.00%` | hit10 `45.00%` | target_gap `0.1236` | auc `0.718414`

## kospi_explosive_1d
- description: `KOSPI explosive leader 1D`
- rows: `3236` | days `4` | holdout days `2`
- train `2026-04-01 -> 2026-04-07` | test `2026-04-08 -> 2026-04-09`
- positive_rate_train: `16.51%` | positive_rate_test: `41.94%`
- champion: `random_forest` | avg_return `-0.32%` | win `25.00%` | hit10 `2.50%` | target_gap `1.2283` | auc `0.495726`

## kosdaq_core_1d
- description: `KOSDAQ core trend 1D`
- rows: `2794` | days `8` | holdout days `2`
- train `2026-03-31 -> 2026-04-07` | test `2026-04-08 -> 2026-04-09`
- positive_rate_train: `39.94%` | positive_rate_test: `33.91%`
- champion: `logistic` | avg_return `+0.51%` | win `57.50%` | hit10 `0.00%` | target_gap `0.9773` | auc `0.412618`

## kosdaq_core_3d
- description: `KOSDAQ core trend 3D`
- rows: `1518` | days `6` | holdout days `2`
- train `2026-03-31 -> 2026-04-03` | test `2026-04-06 -> 2026-04-07`
- positive_rate_train: `41.35%` | positive_rate_test: `55.32%`
- champion: `hist_gb` | avg_return `+6.91%` | win `95.00%` | hit10 `20.00%` | target_gap `0.3090` | auc `0.872596`

## kosdaq_continuation_3d
- description: `KOSDAQ continuation 3D`
- rows: `88` | days `3` | holdout days `0`
- train ` -> ` | test ` -> `
- positive_rate_train: `0.00%` | positive_rate_test: `0.00%`
- champion: `none`

## kosdaq_explosive_1d
- description: `KOSDAQ explosive leader 1D`
- rows: `9197` | days `6` | holdout days `2`
- train `2026-04-01 -> 2026-04-07` | test `2026-04-08 -> 2026-04-09`
- positive_rate_train: `30.33%` | positive_rate_test: `33.78%`
- champion: `xgboost` | avg_return `-0.08%` | win `55.00%` | hit10 `0.00%` | target_gap `1.0430` | auc `0.486754`
