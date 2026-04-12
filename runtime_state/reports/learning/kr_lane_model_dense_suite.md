# KR Dense Lane Model Suite

- generated_at: 2026-04-10T14:32:35.069741+00:00
- target_return_pct: 10.0
- target_win_rate_pct: 75.0

## Overall Champion
- segment: `kospi_core_3d`
- model: `catboost`
- avg_return_pct: `+9.94%`
- win_rate_pct: `75.00%`
- hit10_precision_pct: `40.00%`
- target_gap: `0.0058`
- auc: `0.360215`
- saved_model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/kr_lane_champions/kospi_core_3d__dense__catboost.pkl`

## kospi_core_1d
- rows: `1534` | days `8` | holdout days `2`
- champion: `hist_gb` | avg_return `+2.58%` | win `75.00%` | hit10 `5.00%` | target_gap `0.7415` | auc `0.550323`

## kospi_core_3d
- rows: `988` | days `6` | holdout days `2`
- champion: `catboost` | avg_return `+9.94%` | win `75.00%` | hit10 `40.00%` | target_gap `0.0058` | auc `0.360215`

## kospi_explosive_1d
- rows: `3236` | days `4` | holdout days `1`
- champion: `none`

## kosdaq_core_1d
- rows: `2794` | days `8` | holdout days `2`
- champion: `hist_gb` | avg_return `+0.19%` | win `50.00%` | hit10 `0.00%` | target_gap `1.0359` | auc `0.571356`

## kosdaq_core_3d
- rows: `1518` | days `6` | holdout days `2`
- champion: `hist_gb` | avg_return `+2.61%` | win `77.50%` | hit10 `12.50%` | target_gap `0.7388` | auc `0.555632`

## kosdaq_explosive_1d
- rows: `9197` | days `6` | holdout days `2`
- champion: `catboost` | avg_return `+0.47%` | win `67.50%` | hit10 `0.00%` | target_gap `0.9587` | auc `0.560359`
