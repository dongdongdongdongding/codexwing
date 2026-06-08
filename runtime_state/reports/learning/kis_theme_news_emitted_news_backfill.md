# KIS sidecar scan_universe backfill

- generated_at: `2026-06-08T05:14:16.155052+00:00`
- dry_run: `False`
- fetched_rows: `3029`
- candidate_rows: `3029`
- unique_keys: `1425`
- sidecar_keys_built: `1425`
- updates_built: `3029`
- rows_written: `3029`
- kis_theme_news_evidence_rows: `None`
- kis_theme_news_news_checked_rows: `None`
- no_dummy_data: `True`

## Limitations

- Historical quote fields are reconstructed from KIS historical daily bars, not from a live quote endpoint.
- Historical rank membership is not backfilled unless `--include-current-rank` is explicitly used.
- Rows with unavailable KIS daily bars are skipped instead of receiving placeholder values.
