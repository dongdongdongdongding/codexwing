# Scan Universe Touch5 DD10 Training Decision

- generated_at: `2026-06-11T17:15:10.721669+00:00`
- no_dummy_data: `True`
- requested_min_base_date: `2026-01-01`
- warning: No dummy data was used. The 2026-01-01 CSV-label cache actually starts at 2026-03-31, and the KIS feature cache starts at 2026-04-02.

| market | best scope | feature/model/rule | n/days/runs | +5 dd10 | +10 touch | avg 5D | min low 5D | gate | decision |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| KOSPI | CSV label best | failure_risk_augmented/lightgbm/top2_p0.70 | 133/20/61 | 81.203 | 78.1955 | 12.797801 | -27.855505 | no_kis_gate | do_not_promote_to_production |
| KOSPI | KIS feature best | kis_sidecar_failure_risk_numeric/lightgbm/top1_p0.50 | 63/16/60 | 73.0159 | 92.0635 | 23.990244 | -16.211437 | shadow_risk_review | do_not_promote_to_production |
| KOSDAQ | CSV label best | failure_risk_augmented/lightgbm/top1_p0.70 | 36/20/34 | 80.5556 | 80.5556 | 6.947286 | -20.898989 | no_kis_gate | do_not_promote_to_production |
| KOSDAQ | KIS feature best | kis_sidecar_failure_risk_augmented/xgboost/top1_p0.65 | 25/14/23 | 84.0 | 92.0 | 11.961235 | -15.670754 | shadow_risk_review | do_not_promote_to_production |

## Decision

- Production replacement: `false`
- Shadow update allowed only with risk-review labeling: `true`
- Main blockers: missing real Jan-Mar training snapshots, insufficient production-ready KIS sample, repeated -10% low-guard violations.
