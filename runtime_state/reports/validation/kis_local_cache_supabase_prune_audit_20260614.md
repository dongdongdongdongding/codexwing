# KIS Local Cache Supabase Prune Audit

- generated_at: `2026-06-14T19:12:00+09:00`
- status: `prune_local_caches_after_supabase_check`
- preserved: result reports under `runtime_state/reports/learning/*.md` and `*.json`

## Supabase Check

Supabase table checked: `scan_universe_snapshots`

Query method: id pagination without `count=exact`, because exact count timed out with Postgres `57014`.

Observed table state:

- total rows scanned: `187844`
- table date range: `2026-03-31`..`2026-06-14`
- target audit range: `2026-01-01`..`2026-06-10`

KOSPI in target range:

- rows: `85579`
- unique dates: `36`
- outcome label rows: `66253`
- KIS sidecar rows: `40448`
- KIS sidecar + outcome label rows: `40448`
- sidecar origin: `kis_openapi_backfill`
- roles: emitted=`4885`, rejected=`80694`

KOSDAQ in target range:

- rows: `94931`
- unique dates: `37`
- outcome label rows: `62442`
- KIS sidecar rows: `34857`
- KIS sidecar + outcome label rows: `34857`
- sidecar origin: `kis_openapi_backfill`
- roles: emitted=`2726`, rejected=`92205`

Interpretation:

- Supabase does contain real KIS sidecar rows and outcome labels for the research window.
- The large local `.pkl` files are prepared/raw training caches, not the durable source of truth.
- Some local historical-universe caches are broader derived datasets than the current Supabase sidecar subset, so future work should regenerate them from Supabase/KIS sources instead of keeping bulky local copies.

## Local Prune Target

Delete only local cache/data files:

- `runtime_state/reports/learning/*.pkl`
- `runtime_state/long_term/kis_historical_prices`
- `runtime_state/long_term/kis_ticker_period_sidecar`
- `runtime_state/reports/archive/scan_archive_learning_dataset_all.csv`
- `runtime_state/reports/archive/scan_archive_learning_dataset_all.json`
- `runtime_state/reports/archive/scan_universe_snapshots_kr_20260101_20260611.csv`
- `runtime_state/reports/validation/scan_universe_return_backfill_20260101_20260610_touch5_dd10_updates.jsonl`
- `runtime_state/pycache`
- `runtime_state/tmp/pycache`
- `runtime_state/streamlit_8501.err`
- `runtime_state/streamlit_8501.log`

Additional note:

- `runtime_state/long_term/kis_ticker_period_sidecar` was a local KIS flow/financial/news raw lookup cache for `292167` historical-universe rows.
- Supabase raw-table persistence for this entire lookup cache was not found.
- Supabase `scan_universe_snapshots` does contain extracted real KIS sidecar features for `40448` KOSPI rows and `34857` KOSDAQ rows in the audit range.
- The local raw lookup cache is pruned because the durable source path should be Supabase/KIS services, not local bulk files.
- Large archive/update payload files were also pruned after Supabase outcome and sidecar rows were verified.
- Python bytecode cache and stale Streamlit logs were pruned as non-data runtime waste.

Do not delete result reports:

- `runtime_state/reports/learning/*.md`
- `runtime_state/reports/learning/*.json`
- committed compound guard decision reports

## Final Local State

- `runtime_state/reports/learning/*.pkl`: `0`
- `runtime_state/reports/learning/*.pkl.meta.json`: `0`
- `runtime_state/long_term/kis_historical_prices`: absent
- `runtime_state/long_term/kis_ticker_period_sidecar`: absent
- runtime files larger than 50MB after prune: `0`
- `runtime_state` total size after prune: `2.5G`
- `runtime_state/reports/learning` size after prune: `204M`
- `runtime_state/long_term` size after prune: `31M`
