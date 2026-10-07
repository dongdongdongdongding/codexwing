# US scan partial-error reporting — 2026-10-07

Issue `swing-main-cpb8`. The completed 10:46:32 KST NASDAQ scan visited 3,972
symbols in 14 batches and returned 182 results. `RUN-65DAEE5F` records one IOND
worker error. `run_parallel_scan.error_count` already includes worker-returned
errors and executor exceptions; adding its diagnostic subtotals counted the
same error twice. The old command nevertheless returned zero.

The command now counts the aggregate once, retains diagnostic disagreement as
a degraded condition, and returns exit 2 for partial errors or incomplete
coverage. A batch exception writes a failed report preserving completed batch
IDs and stops without retrying. Clean complete scans return zero. Reports are
written atomically. A per-invocation receipt links the durable report into the
primary session command result independently of truncated stdout; the existing
session classifier then reports an optional scan failure as degraded.

48 relevant tests passed, including the real parallel-scan counter contract,
partial error, incomplete coverage, batch exception without retries, clean
completion, session receipt attachment, dispatch and existing flow receipts.

Read-only reclassification of the actual historical report gives one error,
14 completed batches, complete scan coverage, status `degraded`, expected exit
2. This does not change the historical exit code or rescan any symbol. Original
report and session evidence are preserved. Audit:
`runtime_state/audit/us_scan_status_20261007/historical_reclassification.json`.
Original report SHA-256:
`ba0de5ed4847b0d66b78a0b35b62d8416c60621d410fa5bb799831dcd7546ddf`.

The IOND error message was not retained in the original structured artifacts;
its cause remains unproven. `swing-main-ssvo` tracks that investigation and
structured error-detail retention. The 182 results are not 182 qualified H10
picks. No model, threshold, or edge qualification changed.
