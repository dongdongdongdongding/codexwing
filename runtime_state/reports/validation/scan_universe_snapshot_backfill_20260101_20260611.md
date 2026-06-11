# Scan Universe Snapshot Backfill

- generated_at: `2026-06-11T11:56:29.749093+00:00`
- version: `scan_universe_snapshot_backfill_v2`
- runs_seen: `264`
- rows_built: `171808`
- emitted_rows: `4009`
- rejected_rows: `167799`
- outcome_available_rows: `6224`
- supabase_rows_upserted: `0`
- supabase_table: `scan_universe_snapshots`
- local_csv: `runtime_state/reports/archive/scan_universe_snapshots_kr_20260101_20260611.csv`

## Distribution
- by_market: `{'KOSPI': 79558, 'KOSDAQ': 92250}`
- by_scan_mode: `{'SWING': 171808}`
- by_role: `{'emitted': 4009, 'rejected': 167799}`

## Top Reject Reasons
- `LIQUIDITY_FILTER_FAIL`: `132833`
- `KR_HARD_FILTER_FAIL`: `8847`
- `KR_SIGNAL_WINDOW_FAIL`: `8713`
- `PRECISION_GATE_T3_LOW_ML_SUPPORT`: `8263`
- `KR_BASELINE_FILTER_FAIL`: `3868`
- `MARKET_POLICY_AVOID`: `2945`
- `PRECISION_GATE_RED_MARKET`: `1654`
- `PRECISION_GATE_TREND_MISMATCH`: `440`
- `PRECISION_GATE_LOW_MODEL_SUPPORT`: `236`
