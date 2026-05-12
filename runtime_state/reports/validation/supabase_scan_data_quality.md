# Supabase Scan Data Quality

- generated_at: `2026-05-12T17:34:48.018021+00:00`
- table_rows: `15,502`
- column_count: `107`
- kr_swing_rows: `5,060`
- schema_missing_required_columns: `none`
- kr_swing_validation_excluded_rows: `3,943`
- kr_swing_dummy_rows: `0`
- kr_swing_computed_complete_rows: `2,132`
- kr_swing_computed_complete_with_return3d_rows: `1,392`

## KR SWING Counts

- by_submarket: `{'KOSPI': 2832, 'KOSDAQ': 2228}`
- by_bucket: `{'watchlist': 2934, 'unknown': 994, 'ignored': 550, 'exception_leader': 308, 'picked': 274}`

## Feature Missing Rates

- alpha_score: `11.146%`
- tech_score: `56.917%`
- ml_prob: `2.846%`
- prob_clean: `16.344%`
- whale_score: `56.917%`
- decision_score: `2.609%`
- trend: `2.609%`
- tier: `57.866%`
- volume: `56.897%`
- volume_ratio: `65.119%`
- volume_confirmed: `65.119%`
- position: `57.866%`
- inference_failed: `76.976%`

## Origin Quality

- scanner_archive_outcome: rows=2518, computed_complete=159 (6.315%), metadata_complete=74, validation_excluded=2444, excluded_reason_missing=0, metadata_false_missing=85 (3.376%)
- scanner_full: rows=1004, computed_complete=1004 (100.0%), metadata_complete=1004, validation_excluded=0, excluded_reason_missing=0, metadata_false_missing=0 (0.0%)
- outcome_sync_partial: rows=873, computed_complete=305 (34.937%), metadata_complete=30, validation_excluded=843, excluded_reason_missing=0, metadata_false_missing=275 (31.501%)
- scanner_partial_legacy: rows=665, computed_complete=664 (99.85%), metadata_complete=9, validation_excluded=656, excluded_reason_missing=0, metadata_false_missing=655 (98.496%)

## Return Summary

### return_1d_pct by bucket
- KOSDAQ / exception_leader: n=208, avg=-0.2162%, win=51.442%
- KOSDAQ / ignored: n=349, avg=-0.4777%, win=40.401%
- KOSDAQ / picked: n=41, avg=-1.4986%, win=39.024%
- KOSDAQ / unknown: n=471, avg=-0.2151%, win=39.703%
- KOSDAQ / watchlist: n=1086, avg=-0.1827%, win=39.871%
- KOSPI / exception_leader: n=93, avg=0.6028%, win=46.237%
- KOSPI / ignored: n=155, avg=1.2337%, win=54.194%
- KOSPI / picked: n=226, avg=-1.04%, win=28.319%
- KOSPI / unknown: n=523, avg=0.6521%, win=48.948%
- KOSPI / watchlist: n=1746, avg=1.0513%, win=50.63%

### return_3d_pct by bucket
- KOSDAQ / exception_leader: n=195, avg=1.7215%, win=60.0%
- KOSDAQ / ignored: n=245, avg=1.5062%, win=53.469%
- KOSDAQ / picked: n=41, avg=-2.0504%, win=31.707%
- KOSDAQ / unknown: n=453, avg=0.234%, win=43.488%
- KOSDAQ / watchlist: n=1001, avg=-0.1367%, win=40.959%
- KOSPI / exception_leader: n=84, avg=4.8978%, win=80.952%
- KOSPI / ignored: n=144, avg=2.3847%, win=58.333%
- KOSPI / picked: n=45, avg=2.4345%, win=51.111%
- KOSPI / unknown: n=439, avg=2.8341%, win=55.353%
- KOSPI / watchlist: n=1554, avg=3.2138%, win=61.583%

### return_5d_pct by bucket
- KOSDAQ / exception_leader: n=195, avg=4.9967%, win=65.641%
- KOSDAQ / ignored: n=204, avg=3.4792%, win=58.824%
- KOSDAQ / picked: n=41, avg=1.0386%, win=48.78%
- KOSDAQ / unknown: n=426, avg=3.3023%, win=53.756%
- KOSDAQ / watchlist: n=776, avg=2.4951%, win=50.0%
- KOSPI / exception_leader: n=84, avg=8.9851%, win=85.714%
- KOSPI / ignored: n=138, avg=3.0034%, win=59.42%
- KOSPI / picked: n=45, avg=4.586%, win=66.667%
- KOSPI / unknown: n=430, avg=4.6435%, win=58.837%
- KOSPI / watchlist: n=1309, avg=6.6175%, win=66.845%

### return_7d_pct by bucket
- KOSDAQ / exception_leader: n=195, avg=7.1186%, win=69.231%
- KOSDAQ / ignored: n=184, avg=5.2456%, win=58.696%
- KOSDAQ / picked: n=41, avg=8.8285%, win=39.024%
- KOSDAQ / unknown: n=416, avg=3.0322%, win=50.481%
- KOSDAQ / watchlist: n=658, avg=2.8634%, win=50.152%
- KOSPI / exception_leader: n=84, avg=13.1273%, win=89.286%
- KOSPI / ignored: n=134, avg=4.2925%, win=64.925%
- KOSPI / picked: n=45, avg=7.2089%, win=77.778%
- KOSPI / unknown: n=425, avg=7.3585%, win=63.765%
- KOSPI / watchlist: n=1270, avg=8.8233%, win=68.425%

### return_1d_pct by rank band
- KOSDAQ / rank_gt10: n=964, avg=-0.0241%, win=40.353%
- KOSDAQ / top5: n=365, avg=-0.3021%, win=47.671%
- KOSDAQ / top6_10: n=235, avg=-0.5025%, win=42.979%
- KOSDAQ / unknown: n=591, avg=-0.5436%, win=37.225%
- KOSPI / rank_gt10: n=1484, avg=1.0375%, win=50.876%
- KOSPI / top5: n=312, avg=1.2118%, win=50.962%
- KOSPI / top6_10: n=280, avg=0.4257%, win=45.357%
- KOSPI / unknown: n=667, avg=0.2279%, win=43.478%

### return_3d_pct by rank band
- KOSDAQ / rank_gt10: n=909, avg=-0.5856%, win=39.384%
- KOSDAQ / top5: n=341, avg=1.8417%, win=57.185%
- KOSDAQ / top6_10: n=227, avg=1.7451%, win=51.101%
- KOSDAQ / unknown: n=458, avg=0.2139%, win=43.45%
- KOSPI / rank_gt10: n=1322, avg=3.2099%, win=61.876%
- KOSPI / top5: n=264, avg=3.7638%, win=66.288%
- KOSPI / top6_10: n=241, avg=2.5789%, win=57.676%
- KOSPI / unknown: n=439, avg=2.8341%, win=55.353%

### return_5d_pct by rank band
- KOSDAQ / rank_gt10: n=690, avg=2.2832%, win=50.435%
- KOSDAQ / top5: n=320, avg=4.4842%, win=60.625%
- KOSDAQ / top6_10: n=206, avg=3.1678%, win=55.34%
- KOSDAQ / unknown: n=426, avg=3.3023%, win=53.756%
- KOSPI / rank_gt10: n=1127, avg=6.3329%, win=66.46%
- KOSPI / top5: n=235, avg=6.5522%, win=71.489%
- KOSPI / top6_10: n=214, avg=6.3599%, win=66.355%
- KOSPI / unknown: n=430, avg=4.6435%, win=58.837%

### return_7d_pct by rank band
- KOSDAQ / rank_gt10: n=572, avg=2.8236%, win=50.524%
- KOSDAQ / top5: n=310, avg=6.6875%, win=63.226%
- KOSDAQ / top6_10: n=196, avg=4.6488%, win=53.061%
- KOSDAQ / unknown: n=416, avg=3.0322%, win=50.481%
- KOSPI / rank_gt10: n=1097, avg=8.5518%, win=70.283%
- KOSPI / top5: n=227, avg=8.9597%, win=68.722%
- KOSPI / top6_10: n=209, avg=8.5775%, win=66.507%
- KOSPI / unknown: n=425, avg=7.3585%, win=63.765%
