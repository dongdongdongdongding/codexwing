# Feature Combo Watchlist

- generated_at: `2026-05-27T12:18:19.710084+00:00`
- production_scanner_changed: `False`
- review_candidate_count: `0`

| Rule | Issue | Status | Market | Scope | All | Train | Test | Conditions |
|---|---|---|---|---|---:|---:|---:|---|
| kospi_exact_path_low_alpha_low_ml_top5_exception | swing-main-n7og | watch_failed_current_gate | KOSPI | top5_exception / exact_path | n=32 days=14 win5=81.481% avg5=10.976% min5=-29.9776% bad=28.125% drop1d=15.625% loss5=15.625% stop=12.5% | n=22 days=7 win5=81.818% avg5=11.6746% min5=-29.9776% bad=22.727% drop1d=9.091% loss5=18.182% stop=18.182% | n=10 days=7 win5=80.0% avg5=7.9019% min5=-3.2595% bad=40.0% drop1d=30.0% loss5=10.0% stop=0.0% | alpha_score <= 67.0; ml_prob <= 30.45 |

## Gate Checks

### kospi_exact_path_low_alpha_low_ml_top5_exception
- train_n: `PASS` actual `22` expected `>=18`
- train_days: `PASS` actual `7` expected `>=6`
- train_win_5d: `PASS` actual `81.818` expected `>=70.0%`
- test_n: `PASS` actual `10` expected `>=8`
- test_days: `PASS` actual `7` expected `>=5`
- test_win_5d: `PASS` actual `80.0` expected `>=75.0%`
- test_avg_5d: `PASS` actual `7.9019` expected `>=5.0%`
- test_bad_path: `FAIL` actual `40.0` expected `<=25.0%`
- test_stop5: `PASS` actual `0.0` expected `<=10.0%`

## Notes

- Pinned candidate tracking only; this report does not search new rules.
- review_candidate still requires manual release review before scanner changes.
