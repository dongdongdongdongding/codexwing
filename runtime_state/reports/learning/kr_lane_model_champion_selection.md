# KR Lane Champion Selection

- generated_at: 2026-04-10T14:33:00Z
- source_reports:
  - `/Users/dongdong/Desktop/codex_swing/swing-main/runtime_state/reports/learning/kr_lane_model_suite.md`
  - `/Users/dongdong/Desktop/codex_swing/swing-main/runtime_state/reports/learning/kr_lane_model_dense_suite.md`

## Best-Known Lineup

- `KOSPI core 1D`: `xgboost`
  - model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/kr_lane_champions/kospi_core_1d__xgboost.pkl`
  - holdout avg_return: `+3.13%`
  - holdout win_rate: `80.00%`
  - target_gap: `0.6869`

- `KOSPI core 3D`: `catboost (dense engineered)`
  - model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/kr_lane_champions/kospi_core_3d__dense__catboost.pkl`
  - holdout avg_return: `+9.94%`
  - holdout win_rate: `75.00%`
  - target_gap: `0.0058`

- `KOSDAQ core 1D`: `logistic`
  - model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/kr_lane_champions/kosdaq_core_1d__logistic.pkl`
  - holdout avg_return: `+0.51%`
  - holdout win_rate: `57.50%`
  - target_gap: `0.9773`

- `KOSDAQ core 3D`: `hist_gb`
  - model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/kr_lane_champions/kosdaq_core_3d__hist_gb.pkl`
  - holdout avg_return: `+6.91%`
  - holdout win_rate: `95.00%`
  - target_gap: `0.3090`

- `KOSDAQ explosive 1D`: `catboost (dense engineered)`
  - model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/kr_lane_champions/kosdaq_explosive_1d__dense__catboost.pkl`
  - holdout avg_return: `+0.47%`
  - holdout win_rate: `67.50%`
  - target_gap: `0.9587`

## Not Ready

- `KOSPI explosive 1D`
  - best available result remains negative expectancy

- `KOSDAQ continuation 3D`
  - archive sample too thin for champion training

## Overall Best Model

- segment: `KOSPI core 3D`
- model: `catboost (dense engineered)`
- holdout avg_return: `+9.94%`
- holdout win_rate: `75.00%`
- hit10_precision: `40.00%`
- target_gap: `0.0058`
