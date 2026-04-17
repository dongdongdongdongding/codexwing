# Segment Top5 Validation

- generated_at: 2026-04-16T17:31:01.631605+00:00
- source: supabase.market_scan_results
- target_top5_accuracy_pct: 75.00
- target_high_conviction_avg_return_pct: 15.00
- recent_days: 20
- measurement_horizon_by_mode: {'SWING': 'return_3d_pct', 'INTRADAY': 'return_1d_pct'}
- fetch_stats: {'raw_rows_by_mode': {'SWING': 8949, 'INTRADAY': 22385}, 'deduped_mature_rows': 1916}

## Segment Baselines
### NASDAQ:SWING
- recent days: 1 | history days: 1
- recent top5 positive-rate: 100.00% (gap +25.00%)
- recent top5 avg return: +6.07% (gap -8.93%)
- recent hit5 / hit10: 40.00% / 20.00%
- history top5 positive-rate: 100.00%
- history top5 avg return: +6.07%
- warnings: ['VERY_LOW_SAMPLE', 'US_VALIDATION_PARITY_INCOMPLETE']

### KOSPI:SWING
- recent days: 7 | history days: 7
- recent top5 positive-rate: 80.00% (gap +5.00%)
- recent top5 avg return: +6.82% (gap -8.18%)
- recent hit5 / hit10: 51.43% / 31.43%
- history top5 positive-rate: 80.00%
- history top5 avg return: +6.82%
- warnings: []

### KOSDAQ:INTRADAY
- recent days: 7 | history days: 7
- recent top5 positive-rate: 62.86% (gap -12.14%)
- recent top5 avg return: +2.05% (gap -12.95%)
- recent hit5 / hit10: 28.57% / 14.29%
- history top5 positive-rate: 62.86%
- history top5 avg return: +2.05%
- warnings: ['INTRADAY_MATURITY_THIN']

### KOSDAQ:SWING
- recent days: 8 | history days: 8
- recent top5 positive-rate: 57.50% (gap -17.50%)
- recent top5 avg return: +3.43% (gap -11.57%)
- recent hit5 / hit10: 28.75% / 18.75%
- history top5 positive-rate: 57.50%
- history top5 avg return: +3.43%
- warnings: []

### KOSPI:INTRADAY
- recent days: 4 | history days: 4
- recent top5 positive-rate: 45.00% (gap -30.00%)
- recent top5 avg return: +2.13% (gap -12.87%)
- recent hit5 / hit10: 30.00% / 5.00%
- history top5 positive-rate: 45.00%
- history top5 avg return: +2.13%
- warnings: ['LOW_SAMPLE', 'INTRADAY_MATURITY_THIN']

### NASDAQ:INTRADAY
- recent days: 0 | history days: 0
- recent top5 positive-rate: 0.00% (gap -75.00%)
- recent top5 avg return: +0.00% (gap -15.00%)
- recent hit5 / hit10: 0.00% / 0.00%
- history top5 positive-rate: 0.00%
- history top5 avg return: +0.00%
- warnings: ['NO_MATURE_OUTCOMES', 'US_VALIDATION_PARITY_INCOMPLETE', 'INTRADAY_MATURITY_THIN']

### AMEX:SWING
- recent days: 0 | history days: 0
- recent top5 positive-rate: 0.00% (gap -75.00%)
- recent top5 avg return: +0.00% (gap -15.00%)
- recent hit5 / hit10: 0.00% / 0.00%
- history top5 positive-rate: 0.00%
- history top5 avg return: +0.00%
- warnings: ['NO_MATURE_OUTCOMES', 'US_VALIDATION_PARITY_INCOMPLETE']

### AMEX:INTRADAY
- recent days: 0 | history days: 0
- recent top5 positive-rate: 0.00% (gap -75.00%)
- recent top5 avg return: +0.00% (gap -15.00%)
- recent hit5 / hit10: 0.00% / 0.00%
- history top5 positive-rate: 0.00%
- history top5 avg return: +0.00%
- warnings: ['NO_MATURE_OUTCOMES', 'US_VALIDATION_PARITY_INCOMPLETE', 'INTRADAY_MATURITY_THIN']

