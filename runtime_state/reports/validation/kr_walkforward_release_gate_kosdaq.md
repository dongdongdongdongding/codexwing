# KR Walk-forward Release Gate (KOSDAQ)

- generated_at: 2026-05-12T15:17:11.331147+00:00
- confidence_level: 98.00%
- release_ready: **FAIL**

## Lane: EXPLOSIVE_LEADER [FAIL]

- topn: 10 | horizon: 1d
- active_days: 5 | total_rows: 42
- avg_1d_return: mean=-0.38%  CI [-1.35%, +0.57%]
- positive_1d: mean=56.00%  CI [42.00%, 80.00%]
- avoid_down_1d: mean=58.00%  CI [42.00%, 82.00%]
- precision_hit10: mean=0.00%  CI [0.00%, 0.00%]

### Checks
- [PASS] EXPLOSIVE_LEADER_MIN_ACTIVE_DAYS: active_days=5 (min=3)
- [FAIL] EXPLOSIVE_LEADER_AVG_1D_LOWER: avg_1d_lower=-1.3484%
- [FAIL] EXPLOSIVE_LEADER_POSITIVE_1D_LOWER: positive_1d_lower=42.00%
- [FAIL] EXPLOSIVE_LEADER_AVOID_DOWN_1D_LOWER: avoid_down_1d_lower=42.00%
- [PASS] EXPLOSIVE_LEADER_PRECISION_HIT10_LOWER: precision_hit10_lower=0.00%

## Lane: CORE_TREND [FAIL]

- topn: 5 | horizon: 3d
- active_days: 4 | total_rows: 20
- avg_3d_return: mean=-2.61%  CI [-11.74%, +6.83%]
- positive_3d: mean=50.00%  CI [0.00%, 100.00%]
- avoid_down_3d: mean=50.00%  CI [0.00%, 100.00%]
- precision_hit10: mean=5.00%  CI [0.00%, 15.00%]

### Checks
- [PASS] CORE_TREND_MIN_ACTIVE_DAYS: active_days=4 (min=3)
- [FAIL] CORE_TREND_AVG_3D_LOWER: avg_3d_lower=-11.7411%
- [FAIL] CORE_TREND_POSITIVE_3D_LOWER: positive_3d_lower=0.00%
- [FAIL] CORE_TREND_AVOID_DOWN_3D_LOWER: avoid_down_3d_lower=0.00%
- [PASS] CORE_TREND_PRECISION_HIT10_LOWER: precision_hit10_lower=0.00%
