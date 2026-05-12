# KR Lane Model Suite

- generated_at: 2026-05-08T05:27:54.749590+00:00
- target_return_pct: 5.0
- target_win_rate_pct: 60.0

## Overall Champion
- segment: `kospi_core_3d`
- model: `hist_gb`
- avg_return_pct: `+6.08%`
- win_rate_pct: `65.00%`
- hit10_precision_pct: `0.00%`
- target_gap: `0.0000`
- auc: `0.629427`
- saved_model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/kr_lane_champions/kospi_core_3d__hist_gb.pkl`

## kospi_core_1d
- description: `KOSPI core trend 1D`
- rows: `335` | days `7` | holdout days `2`
- train `2026-04-23 -> 2026-04-30` | test `2026-05-04 -> 2026-05-06`
- positive_rate_train: `41.45%` | positive_rate_test: `41.53%`
- champion: `xgboost` | avg_return `+2.61%` | win `40.00%` | hit10 `0.00%` | target_gap `0.5835` | auc `0.438023`

## kospi_core_3d
- description: `KOSPI core trend 3D`
- rows: `151` | days `5` | holdout days `2`
- train `2026-04-23 -> 2026-04-28` | test `2026-04-29 -> 2026-04-30`
- positive_rate_train: `69.84%` | positive_rate_test: `45.45%`
- champion: `hist_gb` | avg_return `+6.08%` | win `65.00%` | hit10 `0.00%` | target_gap `0.0000` | auc `0.629427`

## kospi_explosive_1d
- description: `KOSPI explosive leader 1D`
- rows: `29` | days `4` | holdout days `0`
- train ` -> ` | test ` -> `
- positive_rate_train: `0.00%` | positive_rate_test: `0.00%`
- champion: `none`

## kosdaq_core_1d
- description: `KOSDAQ core trend 1D`
- rows: `266` | days `5` | holdout days `2`
- train `2026-04-24 -> 2026-04-30` | test `2026-05-04 -> 2026-05-06`
- positive_rate_train: `67.57%` | positive_rate_test: `35.42%`
- champion: `extra_trees` | avg_return `+0.38%` | win `45.00%` | hit10 `0.00%` | target_gap `0.9576` | auc `0.475925`

## kosdaq_core_3d
- description: `KOSDAQ core trend 3D`
- rows: `74` | days `3` | holdout days `0`
- train ` -> ` | test ` -> `
- positive_rate_train: `0.00%` | positive_rate_test: `0.00%`
- champion: `none`

## kosdaq_continuation_3d
- description: `KOSDAQ continuation 3D`
- rows: `21` | days `2` | holdout days `0`
- train ` -> ` | test ` -> `
- positive_rate_train: `0.00%` | positive_rate_test: `0.00%`
- champion: `none`

## kosdaq_explosive_1d
- description: `KOSDAQ explosive leader 1D`
- rows: `2` | days `1` | holdout days `0`
- train ` -> ` | test ` -> `
- positive_rate_train: `0.00%` | positive_rate_test: `0.00%`
- champion: `none`
