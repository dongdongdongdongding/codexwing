# Retrain V2 Report

- generated_at: `2026-05-13T02:50:02.076780`
- execution_status: `trained`
- rows_loaded: `11464`
- backend: `lgb`
- last_successful_model_train_at: `2026-05-13T02:50:02.076780`

## Segment Results
- `phase25_global`: `trained`
  rows=2820 positives=804 auc=0.6230 acc=0.6431
  best_th=0.60 picks=147 avg_return=+5.62% win_rate=65.3% hit_rate=44.2%
- `phase25_kospi_swing`: `trained`
  rows=1069 positives=508 auc=0.6434 acc=0.5751
  best_th=0.45 picks=182 avg_return=+7.65% win_rate=67.0% hit_rate=52.7%
- `phase25_kosdaq_swing`: `trained`
  rows=931 positives=328 auc=0.5920 acc=0.6008
  best_th=0.50 picks=102 avg_return=+5.71% win_rate=61.8% hit_rate=43.1%
- `phase25_kospi_intraday`: `skipped`
  reason: `insufficient_rows`
- `phase25_kosdaq_intraday`: `trained`
  rows=387 positives=116 auc=0.6236 acc=0.5657
  best_th=0.60 picks=61 avg_return=+0.73% win_rate=59.0% hit_rate=59.0%
