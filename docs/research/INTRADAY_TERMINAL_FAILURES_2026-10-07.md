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

These observations identify a bounded repair opportunity; this document does not
claim it has been applied. Fresh receipts cannot prove the historical cause of
the original unsaved responses. Evidence includes `journal_diagnosis.json`,
`existing_cache_invalid_rows.json`, `query_window_comparison.json`,
`fresh_cache_comparison.json` and `fresh_capture/`. Price sources, checkpoint
state, models and live lane selection were not modified by this capture.
