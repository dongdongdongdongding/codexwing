# KIS sidecar scan_universe backfill

- generated_at: `2026-06-12T13:16:07.339417+00:00`
- dry_run: `False`
- fetched_rows: `1515`
- candidate_rows: `1515`
- unique_keys: `823`
- sidecar_keys_built: `823`
- updates_built: `1515`
- rows_written: `1515`
- kis_theme_news_evidence_rows: `None`
- kis_theme_news_news_checked_rows: `None`
- no_dummy_data: `True`

## Limitations

- Historical quote fields are reconstructed from KIS historical daily bars, not from a live quote endpoint.
- Historical rank membership is not backfilled unless `--include-current-rank` is explicitly used.
- Rows with unavailable KIS daily bars are skipped instead of receiving placeholder values.
