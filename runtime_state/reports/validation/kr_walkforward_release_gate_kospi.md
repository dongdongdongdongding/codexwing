# KR Walk-forward Release Gate (KOSPI)

- generated_at: 2026-05-12T15:17:02.052664+00:00
- confidence_level: 98.00%
- release_ready: **FAIL**

## Lane: EXPLOSIVE_LEADER [FAIL]

- topn: 10 | horizon: 1d
- active_days: 3 | total_rows: 23
- avg_1d_return: mean=+1.13%  CI [-2.14%, +3.31%]
- positive_1d: mean=40.00%  CI [0.00%, 70.00%]
- avoid_down_1d: mean=40.00%  CI [0.00%, 70.00%]
- precision_hit10: mean=6.67%  CI [0.00%, 10.00%]

### Checks
- [PASS] EXPLOSIVE_LEADER_MIN_ACTIVE_DAYS: active_days=3 (min=3)
- [FAIL] EXPLOSIVE_LEADER_AVG_1D_LOWER: avg_1d_lower=-2.1378%
- [FAIL] EXPLOSIVE_LEADER_POSITIVE_1D_LOWER: positive_1d_lower=0.00%
- [FAIL] EXPLOSIVE_LEADER_AVOID_DOWN_1D_LOWER: avoid_down_1d_lower=0.00%
- [PASS] EXPLOSIVE_LEADER_PRECISION_HIT10_LOWER: precision_hit10_lower=0.00%

## Lane: CORE_TREND [PASS]

- topn: 5 | horizon: 3d
- active_days: 3 | total_rows: 15
- avg_3d_return: mean=+15.01%  CI [+4.46%, +22.64%]
- positive_3d: mean=93.33%  CI [80.00%, 100.00%]
- avoid_down_3d: mean=93.33%  CI [80.00%, 100.00%]
- precision_hit10: mean=53.33%  CI [0.00%, 100.00%]

### Checks
- [PASS] CORE_TREND_MIN_ACTIVE_DAYS: active_days=3 (min=3)
- [PASS] CORE_TREND_AVG_3D_LOWER: avg_3d_lower=+4.4635%
- [PASS] CORE_TREND_POSITIVE_3D_LOWER: positive_3d_lower=80.00%
- [PASS] CORE_TREND_AVOID_DOWN_3D_LOWER: avoid_down_3d_lower=80.00%
- [PASS] CORE_TREND_PRECISION_HIT10_LOWER: precision_hit10_lower=0.00%
