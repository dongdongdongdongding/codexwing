# KR Walk-forward Release Gate (KOSPI)

- generated_at: 2026-06-08T16:29:28.038679+00:00
- confidence_level: 98.00%
- release_ready: **FAIL**

## Lane: EXPLOSIVE_LEADER [FAIL]

- topn: 10 | horizon: 1d
- active_days: 10 | total_rows: 54
- avg_1d_return: mean=+1.69%  CI [-0.37%, +3.92%]
- positive_1d: mean=51.67%  CI [26.66%, 76.34%]
- avoid_down_1d: mean=55.00%  CI [29.00%, 81.00%]
- precision_hit10: mean=12.33%  CI [0.00%, 27.34%]

### Checks
- [PASS] EXPLOSIVE_LEADER_MIN_ACTIVE_DAYS: active_days=10 (min=3)
- [FAIL] EXPLOSIVE_LEADER_AVG_1D_LOWER: avg_1d_lower=-0.3703%
- [FAIL] EXPLOSIVE_LEADER_POSITIVE_1D_LOWER: positive_1d_lower=26.66%
- [FAIL] EXPLOSIVE_LEADER_AVOID_DOWN_1D_LOWER: avoid_down_1d_lower=29.00%
- [PASS] EXPLOSIVE_LEADER_PRECISION_HIT10_LOWER: precision_hit10_lower=0.00%

## Lane: CORE_TREND [FAIL]

- topn: 5 | horizon: 3d
- active_days: 12 | total_rows: 45
- avg_3d_return: mean=+2.42%  CI [-1.78%, +6.59%]
- positive_3d: mean=58.19%  CI [40.56%, 76.11%]
- avoid_down_3d: mean=62.64%  CI [41.80%, 84.17%]
- precision_hit10: mean=8.61%  CI [0.00%, 20.83%]

### Checks
- [PASS] CORE_TREND_MIN_ACTIVE_DAYS: active_days=12 (min=3)
- [FAIL] CORE_TREND_AVG_3D_LOWER: avg_3d_lower=-1.7807%
- [FAIL] CORE_TREND_POSITIVE_3D_LOWER: positive_3d_lower=40.56%
- [FAIL] CORE_TREND_AVOID_DOWN_3D_LOWER: avoid_down_3d_lower=41.80%
- [PASS] CORE_TREND_PRECISION_HIT10_LOWER: precision_hit10_lower=0.00%
