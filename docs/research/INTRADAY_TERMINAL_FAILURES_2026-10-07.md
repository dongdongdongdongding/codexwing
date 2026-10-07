# Latest intraday terminal failures: evidence before repair

Issue `swing-main-dv7j`, parent `swing-main-5lj2`. Natural backfill
`20261007T205547317819` ended after its 7,200-second budget, with 20,772 requests,
84,798 added rows, seven request errors, three storage `ValueError`s and 610,735
unvisited pairs. The daily parent continued to its later steps. This is partial
collection, not overall pipeline success.

The terminal report is preserved in production
`runtime_state/audit/intraday_terminal_20261007_205547/original_report.json`,
SHA `99aef45f30c266c5828b4794d32aef8a4845284ce805057e7a05daf162b303bb`.
All three storage-error caches have unique valid datetime indices and restore
exactly from their current SHA-verified journal heads. Each has one existing
September 23 bar with open greater than high. Passing that cached session through
the existing validator reproduces `invalid_minute_OHLCV`. No new applied journal
record exists for these three codes in this run. The report does not retain the
original exception message/stack or request payload; this reproduction does not
prove every original exception site.

| Code / time | Existing O/H/L/C / volume | Fresh query-window evidence |
|---|---|---|
| 011230 / 09:00 | 2730/2725/2725/2725 / 385 | 10:00 query: high 2730; all other values unchanged |
| 013000 / 09:02 | 1199/1192/1190/1192 / 78 | 13:30 query: open 1192, volume 37; other three queries retain invalid original values |
| 014130 / 09:01 | 2635/2595/2595/2595 / 50 | 11:30 and 13:30 queries: open 2595, volume 10; 10:00 and 15:30 retain invalid original values |

For 013000 and 014130, cumulative amounts remain 93,225 and 131,350 respectively
across conflicting query variants. Valid OHLC shape alone cannot establish that
the lower-volume variant represents the entire minute. Neither cache is replaced
on this evidence, and no value is clamped to manufacture validity.

`capture_intraday_terminal_failures.py` captures the seven failed identities plus
all four standard query windows for the three invalid-cache dates: 17 distinct
requests. It pins the report and parser/client dependencies, bounds each call,
disables automatic retries, preserves payloads and only reuses immutable receipts.
Actual capture yielded 11 valid slices and six invalid OHLCV slices. Replay made
zero calls and preserved 19 JSON files' bytes, sizes and modification times.
Plan SHA `c0974ebf5ba6c175b68168b105c48dd0945f3cb131cd850f9256ddb5c58c36be`.
Twenty related tests passed, including receipt mutation and failed-call replay.

Independent raw Decimal inspection and cache comparison found:

- 011230: four valid query slices; the 10:00 slice matches 284 of 285 OHLCV
  cells, with only the independently received high changing to 2730. The other
  three slices match their existing rows exactly. No new timestamps.
- 220260 / September 28: recovered 15:30 slice contains 120 valid rows, 20 exact
  overlaps and 100 new timestamps.
- 012280 / September 23: 15:30 slice matches 101 cached rows exactly; the 13:30
  query still contains invalid 09:04 OHLC (open 3635 above high 3600).
- 393890 and 460850: recovered failed slices match all 61 and 75 cached rows.

Fresh receipts cannot prove the historical cause of the original unsaved
responses. Evidence includes `journal_diagnosis.json`,
`existing_cache_invalid_rows.json`, `query_window_comparison.json`,
`fresh_cache_comparison.json` and `fresh_capture/`. Price sources, checkpoint
state, models and live lane selection were not modified by this capture.

## Applied reviewed recovery

Issue `swing-main-wjdf`; implementation `abf0325`. After a coherent copy of all
five actual cache/state/journal-head sets passed rehearsal and independent
full-frame verification, `repair_intraday_terminal_cohort.py` created a fresh
live plan under the operational writer lock and applied it at approximately
23:13 KST. Live plan SHA:
`2f13d5b6a8f70071522f36802885fd44c1369fa622760c057b9cbf0c42e9b98f`.

The repair pins all eight accepted response hashes, preserves immutable before
and after files, checks all mutation targets before writing, repeats each
compare-and-set, validates both journal chains and resumes interrupted work.
Both price-file metadata and checkpoint identity are bound to the plan. A busy
writer, changed cache/state/backup, unexpected overlap, new timestamp count or
replacement value aborts. It does not change the collector or parser.

Actual changes were two price files, two journal heads and five checkpoints:

- 011230: one received high value changed 2725→2730; all other 73,692-row content
  stayed exact. Four accepted query windows restore its requested-slice state.
- 220260: 100 provider bars added, with all 83,001 previous rows unchanged.
  Independent Decimal verification matched all 500 newly added OHLCV cells.
- 012280, 393890 and 460850: price files unchanged; only validated request
  checkpoints recovered. 012280 stays partial because its 13:30 request is invalid.

All five journal reconstructions match the live frames exactly; checkpoint
identities match their files. Other dates' 36 checkpoint states are unchanged.
Of 2,627 price files, only the two planned files changed modification time/size;
the other 2,625 retained both. The excluded 013000/014130 caches and checkpoints
also retained their exact hashes. Their ambiguous source rows remain unresolved.

32 related tests passed in both checkouts, including mid-transaction interruption,
concurrent changes, whole-plan preflight, writer exclusion, strict replacement
scope and idempotency. Actual live replay wrote zero files and preserved all 29
audit/target files' bytes, sizes and mtimes. The producer, collector/client and
six frozen model pins remained unchanged. Four service API endpoints returned
HTTP 200; this confirms responsiveness, not complete data health or qualification.

Evidence is in `recovery/independent_live_verification.json`, immutable backups,
the applied plan and `shadow_rehearsal/independent_verification.json`. Four repaired
dates now have all requested slices; one remains partial. All retain unknown
whole-session completeness. No strategy was retrained, evaluated or promoted.

## Derived-panel consumer check

The already-running builder PID 34932 terminated and published a 92,096-row,
300-code `intraday_3d_panel.parquet` at 23:22 KST, SHA
`8e27d0862dad320cb80c0918baac98374086e2e829d4f4627c2efeecd1157429`.
The consumer's `_train()` reads that exact path. Both repaired price codes,
011230 and 220260, are absent from the builder's 300-code `ohlc_daily` source and
the resulting panel. No current training row requires regeneration for these two
repairs. A comparison over zero stored rows is explicitly **not** evidence that
their features were incorporated or that the entire panel is healthy.

Recomputing raw-cache features identifies two counterfactual changes for 011230
and sixteen for 220260, including later volume-history and next-session gap
effects; none is a row in this current training panel. The panel and source
universes match exactly at 300 codes. Evidence is in production
`runtime_state/audit/intraday_derived_repair_check_20261007/scope_resolution.json`.
This closes the scoped consumer check `swing-main-6bkk` without a rebuild.

Broader findings are tracked in `swing-main-g59e`: the builder does not validate
all input OHLCV rows, and its H3 label currently accepts fewer than three future
sessions. The intended 300-code scope and these source/target contracts need
review before a new training epoch. They are separate from the requested H10
replacement criterion; this check does not qualify the legacy H3 lane.
