# KR INTRADAY Model Viability

- generated_at: `2026-06-29T07:07:21.298742+00:00`
- min_rows: `300` · min_positives: `60`

| Market | Horizon | Rows | Positives | Ready | Promotion | Best |
|---|---:|---:|---:|---:|---:|---|
| KOSPI | 1D | 4574 | 1659 | True | FAIL auc_below_0.56,win_below_70.0,avg_below_1.0,min_loss_below_-5.0 | histgb th=0.75 picks=10 win=40.0% avg=-1.6361% min=-14.4279% max=7.5171% |
| KOSPI | 3D | 4407 | 1397 | True | FAIL auc_below_0.56,win_below_70.0,avg_below_1.0,min_loss_below_-5.0 | logistic th=0.65 picks=61 win=42.623% avg=-2.0502% min=-42.6339% max=11.2817% |
| KOSPI | 5D | 4238 | 1402 | True | FAIL auc_below_0.56,avg_below_1.0,min_loss_below_-5.0 | logistic th=0.65 picks=21 win=71.4286% avg=-0.5889% min=-40.0868% max=20.2532% |
| KOSDAQ | 1D | 4316 | 1599 | True | FAIL auc_below_0.56,win_below_70.0,min_loss_below_-5.0 | logistic th=0.65 picks=10 win=60.0% avg=3.8639% min=-10.6047% max=24.6772% |
| KOSDAQ | 3D | 4019 | 1522 | True | FAIL auc_below_0.56,win_below_70.0,min_loss_below_-5.0 | logistic th=0.6 picks=81 win=50.6173% avg=2.1534% min=-32.2321% max=72.5629% |
| KOSDAQ | 5D | 3758 | 1581 | True | FAIL auc_below_0.56,win_below_70.0,avg_below_1.0,min_loss_below_-5.0 | histgb th=0.65 picks=11 win=45.4545% avg=-0.5663% min=-23.6351% max=12.5243% |

## Notes

- No production model files are written by this report.
- Targets are simple positive close-return labels for viability only; promotion still requires forward observation and ordered path risk labels.
