# KR INTRADAY Model Viability

- generated_at: `2026-08-14T00:56:16.746388+00:00`
- min_rows: `300` · min_positives: `60`

| Market | Horizon | Rows | Positives | Ready | Promotion | Best |
|---|---:|---:|---:|---:|---:|---|
| KOSPI | 1D | 6942 | 2714 | True | FAIL auc_below_0.56,win_below_70.0,min_loss_below_-5.0 | logistic th=0.6 picks=54 win=61.1111% avg=3.2699% min=-18.6237% max=29.8795% |
| KOSPI | 3D | 6788 | 2460 | True | FAIL auc_below_0.56,win_below_70.0,avg_below_1.0,min_loss_below_-5.0 | histgb th=0.7 picks=39 win=56.4103% avg=-1.4389% min=-25.641% max=14.2002% |
| KOSPI | 5D | 6559 | 2310 | True | FAIL auc_below_0.56,min_loss_below_-5.0 | rf th=0.7 picks=17 win=70.5882% avg=4.9191% min=-31.7711% max=26.8692% |
| KOSDAQ | 1D | 6648 | 2674 | True | FAIL auc_below_0.56,win_below_70.0,min_loss_below_-5.0 | histgb th=0.8 picks=13 win=69.2308% avg=7.3886% min=-10.4154% max=29.9625% |
| KOSDAQ | 3D | 6355 | 2525 | True | FAIL auc_below_0.56,win_below_70.0,avg_below_1.0,min_loss_below_-5.0 | histgb th=0.55 picks=167 win=49.1018% avg=0.6202% min=-54.772% max=50.0% |
| KOSDAQ | 5D | 6063 | 2509 | True | FAIL auc_below_0.56,win_below_70.0,min_loss_below_-5.0 | logistic th=0.5 picks=23 win=69.5652% avg=6.5456% min=-15.9016% max=71.7647% |

## Notes

- No production model files are written by this report.
- Targets are simple positive close-return labels for viability only; promotion still requires forward observation and ordered path risk labels.
