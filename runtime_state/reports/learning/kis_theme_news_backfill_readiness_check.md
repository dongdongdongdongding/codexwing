# KIS sidecar scan_universe backfill

- generated_at: `2026-06-08T05:02:01.590719+00:00`
- dry_run: `True`
- fetched_rows: `101786`
- candidate_rows: `None`
- unique_keys: `None`
- sidecar_keys_built: `None`
- updates_built: `None`
- rows_written: `0`
- kis_theme_news_evidence_rows: `0`
- kis_theme_news_news_checked_rows: `0`
- no_dummy_data: `True`

## Limitations

- Historical quote fields are reconstructed from KIS historical daily bars, not from a live quote endpoint.
- Historical rank membership is not backfilled unless `--include-current-rank` is explicitly used.
- Rows with unavailable KIS daily bars are skipped instead of receiving placeholder values.
