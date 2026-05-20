# Supabase Scan Data Quality

- generated_at: `2026-05-20T07:13:26.789321+00:00`
- table_rows: `18,177`
- column_count: `143`
- kr_swing_rows: `7,041`
- schema_missing_required_columns: `none`
- kr_swing_validation_excluded_rows: `4,014`
- kr_swing_dummy_rows: `0`
- kr_swing_computed_complete_rows: `79`
- kr_swing_computed_complete_with_return3d_rows: `0`

## KR SWING Counts

- by_submarket: `{'KOSPI': 4147, 'KOSDAQ': 2894}`
- by_bucket: `{'watchlist': 4103, 'unknown': 1180, 'ignored': 1033, 'exception_leader': 377, 'picked': 348}`

## Feature Missing Rates

- alpha_score: `8.01%`
- tech_score: `40.974%`
- ml_prob: `2.045%`
- prob_clean: `11.745%`
- whale_score: `40.974%`
- foreign_flow: `80.699%`
- institution_flow: `80.699%`
- retail_flow: `80.699%`
- foreigner_1d: `98.878%`
- institution_1d: `98.878%`
- retail_1d: `98.878%`
- foreigner_3d: `98.878%`
- institution_3d: `98.878%`
- retail_3d: `98.878%`
- foreigner_10d: `98.878%`
- institution_10d: `98.878%`
- retail_10d: `98.878%`
- flow_asof: `98.878%`
- decision_score: `1.875%`
- trend: `1.875%`
- tier: `42.593%`
- volume: `40.889%`
- volume_ratio: `46.868%`
- volume_confirmed: `46.868%`
- position: `42.593%`
- inference_failed: `56.327%`

## Origin Quality

- scanner_full: rows=2914, computed_complete=79 (2.711%), metadata_complete=2914, validation_excluded=0, excluded_reason_missing=0, metadata_false_missing=0 (0.0%)
- scanner_archive_outcome: rows=2589, computed_complete=0 (0.0%), metadata_complete=74, validation_excluded=2515, excluded_reason_missing=0, metadata_false_missing=0 (0.0%)
- outcome_sync_partial: rows=873, computed_complete=0 (0.0%), metadata_complete=30, validation_excluded=843, excluded_reason_missing=0, metadata_false_missing=0 (0.0%)
- scanner_partial_legacy: rows=665, computed_complete=0 (0.0%), metadata_complete=9, validation_excluded=656, excluded_reason_missing=0, metadata_false_missing=0 (0.0%)

## Return Summary

### return_1d_pct by bucket
- KOSDAQ / exception_leader: n=278, avg=-1.2255%, win=43.885%
- KOSDAQ / ignored: n=752, avg=-1.409%, win=34.043%
- KOSDAQ / picked: n=41, avg=-1.4986%, win=39.024%
- KOSDAQ / unknown: n=601, avg=-0.799%, win=37.438%
- KOSDAQ / watchlist: n=1200, avg=-0.3178%, win=38.917%
- KOSPI / exception_leader: n=93, avg=0.6028%, win=46.237%
- KOSPI / ignored: n=281, avg=0.0684%, win=50.178%
- KOSPI / picked: n=307, avg=-1.1597%, win=30.293%
- KOSPI / unknown: n=563, avg=0.5269%, win=48.135%
- KOSPI / watchlist: n=2866, avg=0.1676%, win=45.953%

### return_3d_pct by bucket
- KOSDAQ / exception_leader: n=249, avg=-0.9555%, win=48.594%
- KOSDAQ / ignored: n=683, avg=-3.7396%, win=31.772%
- KOSDAQ / picked: n=41, avg=-2.0504%, win=31.707%
- KOSDAQ / unknown: n=601, avg=-1.5439%, win=37.105%
- KOSDAQ / watchlist: n=1184, avg=-1.0417%, win=37.5%
- KOSPI / exception_leader: n=93, avg=4.5751%, win=79.57%
- KOSPI / ignored: n=234, avg=-0.2069%, win=48.718%
- KOSPI / picked: n=292, avg=0.4283%, win=41.438%
- KOSPI / unknown: n=523, avg=2.6611%, win=54.685%
- KOSPI / watchlist: n=2631, avg=-0.2607%, win=45.04%

### return_5d_pct by bucket
- KOSDAQ / exception_leader: n=215, avg=3.2022%, win=60.0%
- KOSDAQ / ignored: n=394, avg=-1.811%, win=41.117%
- KOSDAQ / picked: n=41, avg=1.0386%, win=48.78%
- KOSDAQ / unknown: n=470, avg=2.0762%, win=49.574%
- KOSDAQ / watchlist: n=1106, avg=0.6485%, win=43.852%
- KOSPI / exception_leader: n=93, avg=7.5761%, win=79.57%
- KOSPI / ignored: n=160, avg=2.1455%, win=55.625%
- KOSPI / picked: n=232, avg=-1.7142%, win=38.793%
- KOSPI / unknown: n=523, avg=2.9407%, win=52.772%
- KOSPI / watchlist: n=1834, avg=3.6603%, win=54.962%

### return_7d_pct by bucket
- KOSDAQ / exception_leader: n=195, avg=7.1186%, win=69.231%
- KOSDAQ / ignored: n=251, avg=1.4407%, win=47.41%
- KOSDAQ / picked: n=41, avg=8.8285%, win=39.024%
- KOSDAQ / unknown: n=459, avg=1.5829%, win=46.841%
- KOSDAQ / watchlist: n=1043, avg=-0.5879%, win=41.898%
- KOSPI / exception_leader: n=90, avg=11.7734%, win=85.556%
- KOSPI / ignored: n=146, avg=3.3094%, win=61.644%
- KOSPI / picked: n=107, avg=-0.5183%, win=47.664%
- KOSPI / unknown: n=439, avg=7.04%, win=63.098%
- KOSPI / watchlist: n=1619, avg=6.2464%, win=60.655%

### return_1d_pct by rank band
- KOSDAQ / rank_gt10: n=1004, avg=-0.1822%, win=39.442%
- KOSDAQ / top5: n=435, avg=-0.5497%, win=44.368%
- KOSDAQ / top6_10: n=274, avg=-0.8601%, win=40.876%
- KOSDAQ / unknown: n=1159, avg=-1.4371%, win=33.218%
- KOSPI / rank_gt10: n=1518, avg=0.9903%, win=50.725%
- KOSPI / top5: n=498, avg=0.3511%, win=45.984%
- KOSPI / top6_10: n=416, avg=0.1671%, win=46.394%
- KOSPI / unknown: n=1678, avg=-0.7458%, win=40.107%

### return_3d_pct by rank band
- KOSDAQ / rank_gt10: n=999, avg=-1.0514%, win=37.738%
- KOSDAQ / top5: n=410, avg=0.3073%, win=49.512%
- KOSDAQ / top6_10: n=265, avg=0.1488%, win=45.66%
- KOSDAQ / unknown: n=1084, avg=-3.8307%, win=29.244%
- KOSPI / rank_gt10: n=1513, avg=2.7948%, win=59.022%
- KOSPI / top5: n=447, avg=1.2553%, win=52.796%
- KOSPI / top6_10: n=383, avg=-0.3741%, win=43.342%
- KOSPI / unknown: n=1430, avg=-2.4044%, win=33.916%

### return_5d_pct by rank band
- KOSDAQ / rank_gt10: n=967, avg=0.6017%, win=44.881%
- KOSDAQ / top5: n=374, avg=2.2948%, win=54.011%
- KOSDAQ / top6_10: n=245, avg=1.9996%, win=49.796%
- KOSDAQ / unknown: n=640, avg=-0.3428%, win=42.344%
- KOSPI / rank_gt10: n=1482, avg=4.2859%, win=57.557%
- KOSPI / top5: n=350, avg=3.0482%, win=57.714%
- KOSPI / top6_10: n=290, avg=3.5759%, win=55.172%
- KOSPI / unknown: n=720, avg=0.6187%, win=44.722%

### return_7d_pct by rank band
- KOSDAQ / rank_gt10: n=915, avg=-0.5637%, win=41.421%
- KOSDAQ / top5: n=352, avg=4.8083%, win=59.375%
- KOSDAQ / top6_10: n=233, avg=2.397%, win=48.069%
- KOSDAQ / unknown: n=489, avg=1.0015%, win=45.399%
- KOSPI / rank_gt10: n=1416, avg=5.7475%, win=61.653%
- KOSPI / top5: n=284, avg=6.6647%, win=60.915%
- KOSPI / top6_10: n=262, avg=5.9891%, win=58.779%
- KOSPI / unknown: n=439, avg=7.04%, win=63.098%
