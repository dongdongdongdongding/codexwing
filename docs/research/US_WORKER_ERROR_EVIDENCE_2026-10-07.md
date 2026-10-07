# US worker error evidence — 2026-10-07

The historical NASDAQ batch `RUN-65DAEE5F` identifies one failed symbol, IOND.
Its raw scan artifact and scanner input both retain the count and symbol, but
neither retains an exception type, message or traceback. The session result's
truncated output does not contain IOND. The original failure cause remains
unknown; no new full-universe scan was run to reinterpret that historical event.

Evidence inventory and source hashes are in
`runtime_state/audit/us_worker_error_20261007/historical_evidence.json`.

The worker now returns structured error evidence: exception type, bounded
message, attempt count and up to eight file/function/line frames. Source-code
lines and absolute traceback paths are omitted. Configured credential values,
request URLs and common authorization/secret forms are redacted before logging
or persistence. Rate-limit exhaustion retains its existing error code and retry
behavior. Successful picks and error counts are unchanged.

The non-UI collector previously discarded every worker error payload. It now
preserves per-symbol worker and executor details in diagnostics, which already
flow into scanner input and `raw_scan_results.json`. Error-bearing scans retain
the partial/failure status established by the earlier US status repair.

Twenty-one tests pass across diagnostics, scanner runtime, non-UI pipeline,
artifact persistence and US batch status. A fault injected at the real worker's
price-fetch boundary passes through the actual parallel collector and disk
artifact writer; its exception and frame survive, credentials do not, and the
scan remains one error with no pick. Separate tests retain successful symbols
alongside executor errors and cover rate-limit exhaustion and legacy payloads.

`swing-main-ssvo` remains open for the actual IOND cause: the instrumentation
fix cannot reconstruct discarded historical evidence. The next naturally
occurring failure will have usable detail. No historical outcome, model or
published probability was changed.
