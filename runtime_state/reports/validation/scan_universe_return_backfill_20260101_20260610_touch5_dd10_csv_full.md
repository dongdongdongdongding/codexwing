# Scan Universe Return Backfill

- generated_at: `2026-06-11T15:12:09.664325+00:00`
- source_rows: `166318`
- input_csv: `runtime_state/reports/archive/scan_universe_snapshots_kr_20260101_20260611.csv`
- candidate_rows: `166318`
- ticker_count: `2566`
- updates_built: `166314`
- rows_written: `0`
- updates_output_jsonl: `runtime_state/reports/validation/scan_universe_return_backfill_20260101_20260610_touch5_dd10_updates.jsonl`
- updates_input_jsonl: ``
- dry_run: `True`
- overwrite: `True`
- write_conflict_key: `id`
- write_start_offset: `0`
- no_history_rows: `4`
- no_payload_rows: `0`
- repaired_base_date_candidates: `0`
- run_date_index_size: `488`

## Distribution
- updates_by_market: `{'KOSPI': 77676, 'KOSDAQ': 88638}`
- updates_by_role: `{'rejected': 162358, 'emitted': 3956}`
- price_fetch_counts: `{'kis': 2564}`
- price_fetch_failures: `{'kis_empty': 2}`
- price_fetch_failure_examples: `{}`
