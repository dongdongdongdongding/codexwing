# Feature Combo Watchlist

- generated_at: `2026-06-29T07:07:07.705183+00:00`
- production_scanner_changed: `False`
- review_candidate_count: `0`

| Rule | Issue | Status | Market | Scope | All | Train | Test | Conditions |
|---|---|---|---|---|---:|---:|---:|---|
| kospi_exact_path_low_alpha_low_ml_top5_exception | swing-main-n7og | watch_failed_current_gate | KOSPI | top5_exception / exact_path | n=44 days=23 win5=66.667% avg5=7.7321% min5=-29.9776% bad=43.182% drop1d=22.727% loss5=29.545% stop=20.454% | n=30 days=12 win5=76.667% avg5=10.1639% min5=-29.9776% bad=26.667% drop1d=13.333% loss5=23.333% stop=13.333% | n=14 days=11 win5=33.333% avg5=-0.3741% min5=-15.493% bad=78.571% drop1d=42.857% loss5=42.857% stop=35.714% | alpha_score <= 67.0; ml_prob <= 30.45 |

## Gate Checks

### kospi_exact_path_low_alpha_low_ml_top5_exception
- train_n: `PASS` actual `30` expected `>=18`
- train_days: `PASS` actual `12` expected `>=6`
- train_win_5d: `PASS` actual `76.667` expected `>=70.0%`
- test_n: `PASS` actual `14` expected `>=8`
- test_days: `PASS` actual `11` expected `>=5`
- test_win_5d: `FAIL` actual `33.333` expected `>=75.0%`
- test_avg_5d: `FAIL` actual `-0.3741` expected `>=5.0%`
- test_bad_path: `FAIL` actual `78.571` expected `<=25.0%`
- test_stop5: `FAIL` actual `35.714` expected `<=10.0%`

## Refinement Candidates

### kospi_exact_path_low_alpha_low_ml_top5_exception
- 추가 refinement 후보 없음

## Notes

- Pinned candidate tracking only; this report does not search new rules.
- review_candidate still requires manual release review before scanner changes.
