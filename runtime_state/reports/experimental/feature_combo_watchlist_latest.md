# Feature Combo Watchlist

- generated_at: `2026-08-14T00:55:57.800819+00:00`
- production_scanner_changed: `False`
- review_candidate_count: `0`

| Rule | Issue | Status | Market | Scope | All | Train | Test | Conditions |
|---|---|---|---|---|---:|---:|---:|---|
| kospi_exact_path_low_alpha_low_ml_top5_exception | swing-main-n7og | watch_failed_current_gate | KOSPI | top5_exception / exact_path | n=53 days=28 win5=52.83% avg5=2.6763% min5=-29.9776% bad=50.943% drop1d=26.415% loss5=47.17% stop=24.528% | n=37 days=17 win5=70.27% avg5=8.6598% min5=-29.9776% bad=35.135% drop1d=18.919% loss5=29.73% stop=16.216% | n=16 days=11 win5=12.5% avg5=-11.1607% min5=-24.94% bad=87.5% drop1d=43.75% loss5=87.5% stop=43.75% | alpha_score <= 67.0; ml_prob <= 30.45 |

## Gate Checks

### kospi_exact_path_low_alpha_low_ml_top5_exception
- train_n: `PASS` actual `37` expected `>=18`
- train_days: `PASS` actual `17` expected `>=6`
- train_win_5d: `PASS` actual `70.27` expected `>=70.0%`
- test_n: `PASS` actual `16` expected `>=8`
- test_days: `PASS` actual `11` expected `>=5`
- test_win_5d: `FAIL` actual `12.5` expected `>=75.0%`
- test_avg_5d: `FAIL` actual `-11.1607` expected `>=5.0%`
- test_bad_path: `FAIL` actual `87.5` expected `<=25.0%`
- test_stop5: `FAIL` actual `43.75` expected `<=10.0%`

## Refinement Candidates

### kospi_exact_path_low_alpha_low_ml_top5_exception
- 추가 refinement 후보 없음

## Notes

- Pinned candidate tracking only; this report does not search new rules.
- review_candidate still requires manual release review before scanner changes.
