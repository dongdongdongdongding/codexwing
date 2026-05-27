# KR INTRADAY Model Viability

- generated_at: `2026-05-27T05:54:52.981228+00:00`
- min_rows: `300` · min_positives: `60`

| Market | Horizon | Rows | Positives | Ready | Promotion | Best |
|---|---:|---:|---:|---:|---:|---|
| KOSPI | 1D | 2410 | 910 | True | FAIL auc_below_0.56,win_below_70.0,min_loss_below_-5.0 | rf th=0.95 picks=166 win=68.0723% avg=1.3381% min=-8.5559% max=17.3134% |
| KOSPI | 3D | 1621 | 634 | True | FAIL auc_below_0.56,win_below_70.0 | extratrees th=0.85 picks=15 win=66.6667% avg=4.0582% min=-4.9432% max=16.1702% |
| KOSPI | 5D | 1548 | 1146 | True | FAIL auc_below_0.56,win_below_70.0,min_loss_below_-5.0 | extratrees th=0.55 picks=110 win=69.0909% avg=6.2007% min=-6.3256% max=40.625% |
| KOSDAQ | 1D | 4760 | 1161 | True | FAIL auc_below_0.56,win_below_70.0,avg_below_1.0,min_loss_below_-5.0 | histgb th=0.8 picks=18 win=55.5556% avg=0.6203% min=-7.5676% max=14.5455% |
| KOSDAQ | 3D | 4434 | 1365 | True | FAIL auc_below_0.56,win_below_70.0,min_loss_below_-5.0 | logistic th=0.5 picks=990 win=58.3838% avg=3.7292% min=-36.4905% max=119.1844% |
| KOSDAQ | 5D | 4220 | 2077 | True | FAIL auc_below_0.56,min_loss_below_-5.0 | logistic th=0.85 picks=41 win=73.1707% avg=8.0807% min=-16.6121% max=53.913% |

## Notes

- No production model files are written by this report.
- Targets are simple positive close-return labels for viability only; promotion still requires forward observation and ordered path risk labels.
