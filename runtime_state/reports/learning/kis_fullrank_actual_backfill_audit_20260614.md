# KIS Fullrank Actual Backfill Audit

- generated_at: `2026-06-13T16:14:43+00:00`
- dummy_data_used: `False`
- period: `2026-01-02`..`2026-06-10`
- total_prepared_rows: `292167`

## Completed Actual Data

- KOSPI: tickers=`949/949` raw_rows=`100501` prepared_rows=`100490` failed=`0` prefilter_selected=`97282`
- KOSDAQ: tickers=`1821/1821` raw_rows=`191712` prepared_rows=`191677` failed=`0` prefilter_selected=`182562`

## Exact Sidecar Merge
- KOSPI: matched_rows=`16225` matched_pct=`16.146` days=`26` tickers=`843`
- KOSDAQ: matched_rows=`31851` matched_pct=`16.617` days=`27` tickers=`1644`

## Static Stock Master
- KOSPI: master_matched_rows=`85436` augmented_rows=`77565` augmented_pct=`77.187`
- KOSDAQ: master_matched_rows=`168646` augmented_rows=`155316` augmented_pct=`81.03`

## Remaining Real-Data Boundary
- Flow/financial/news values were not fabricated. Only exact-date sidecar observations exist in the final cache.
- Full live sidecar overwrite target is `292,167` ticker-date rows across `106` base dates; this needs a ticker-period cache/joiner before production-scale execution.
- Financial ratio fill still needs statement-period gating to avoid as-of leakage.

## Artifacts
- final_kospi_cache: `runtime_state/reports/learning/kis_historical_universe_fullrank_actual_augmented_prepared_kospi_20260101_20260610.pkl`
- final_kosdaq_cache: `runtime_state/reports/learning/kis_historical_universe_fullrank_actual_augmented_prepared_kosdaq_20260101_20260610.pkl`
- gap_report: `runtime_state/reports/learning/kis_fullrank_actual_sidecar_proxy_feature_gap_20260614.json`
- plan_report: `runtime_state/reports/learning/kis_fullrank_actual_sidecar_backfill_overwrite_plan_20260614.json`
