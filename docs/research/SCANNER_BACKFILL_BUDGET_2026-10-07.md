# Scanner return backfill execution audit — 2026-10-07

The daily worker was still executing `backfill_scanner_full_returns.py` after
70 minutes. A one-second native process sample showed curl network polling;
it did not establish a deadlock. That worker was allowed to finish and was
confirmed terminal around 13:00 KST, with ten committed patches. The parent
daily pipeline continued into admission optimization.

A read-only current DB census found 30,190 eligible missing-return rows but
22,148 distinct ticker/local-signal-date combinations. Another 211 rows belong
to the dedicated `SWING-CAND-` refresh and cannot be patched by this tool.
These counts describe the query time, not the running worker's captured inputs.

## Execution changes

- Cache each ticker/date price response, including unavailable responses, within
  one invocation. Later invocations fetch fresh responses as labels mature.
- Skip dedicated-refresh rows before external IO. Keep existing price-basis,
  exact-run identity, missing-cell and audited CAS/readback guards.
- Daily defaults: at most 500 rows, 100 unique historical-price requests and
  300 seconds of planning. Each limit has an explicit environment override;
  the standalone CLI remains unlimited unless bounds are supplied.
- Bounded calls use a market/scope-checked ID cursor. Advance it only after the
  selected update plan passes audited writes. Rotate through current eligible
  rows so older immature/failed rows are revisited. Dry runs never advance it.
- Write atomic progress receipts during DB pages, historical requests, planning,
  application and termination. The CLI uses a global file lock across markets.
- Partial coverage, unavailable history and conflicting daily bases return
  exit code 2. The daily wrapper records the failure and continues its other
  steps. Attempted coverage does not mean all horizons were filled.
- An empty local outcome index can still use an enabled historical fallback.

The planning budget does not interrupt an in-flight request, initial DB scan or
the final audited writes. Row/request limits also bound the selected work. This
is not a hard wall-clock timeout, nor a claim that historical coverage is complete.

## Verification

95 tests cover source reuse, cursor rotation, request/row/time limits, immutable
dry-run cursors, crash/CAS failure, CLI failure receipts and locking, existing
normalization guards, shell portability and session dispatch.

Production audit directory: `runtime_state/audit/scanner_backfill_budget_20261007/`.

- Four real duplicate DB rows and two captured price responses: four external
  lookups become two; both versions reject the same conflicting patches.
- Eight captured historical before-rows/source outcomes: all planned patch values
  exactly match the original audited application. This is a planner replay,
  without new DB writes or claims that old source data is still current.
- Actual CLI dry run over production KOSPI: 8,468 eligible rows, two requests and
  two attempted rows, 8,466 unvisited. It terminates in 19.797 seconds with
  `partial`, exit 2, zero writes and no cursor advance. DB-page and final receipts
  are in `actual_dry_progress.json`; stdout is `actual_dry_cli.log`.

## Applied production pilot and resume

After the old writer terminated, the bounded KOSPI applying call attempted two
rows using two history requests in 19.361 seconds. Both missing H30 returns were
committed and independently read through the Management API: ID 2161 received
41.176471%, and ID 2162 received 8.163265%. Full before/after rows differ only in
`return_30d_pct` and the update timestamp. The cursor advanced to 2162 only after
successful audited application. The CLI correctly returned partial/exit 2 with
8,466 rows unvisited.

A second call resumed from that cursor, attempted one row with one request in
8.904 seconds, and advanced to 2168 after applying -35.202864% to that row's H30.
Independent API readback and fresh-history Decimal calculation agree; all captured
unpatched fields are exact. It returned partial/exit 2 with 8,465 rows unvisited.
These pilots use a separate audit cursor, not the daily ALL-market cursor.

Receipts: `old_worker_terminal.json`, `apply_pilot_before.json`,
`apply_pilot_independent_readback.json`, `apply_resume_independent_readback.json`,
`apply_pilot_progress.json`, `apply_resume_progress.json`, and
`apply_pilot_cursor.json`. The global apply journals retain immutable plans and
before/after checks.

This completes the applying/resume proof for `swing-main-1y4w`.
`swing-main-l64n` still tracks the unfinished daily pipeline. Historical coverage
remains partial; no model, issued contract or edge-lane qualification is changed.

## Historical request window correction

The actual dry run exposed a second cause of repeated missing labels. IDs 2161
and 2162 (032830.KS / 267250.KS, signal 2026-04-03) lacked H30 even though the
signals were old. The former 40-day request plus its five-day buffer returned
31 rows, of which two preceded the signal: only 29 observations from the base.

The default request window is now 90 calendar days plus the existing buffer.
Both real responses contain 65 rows. All 31 overlapping prices and earlier
horizons are exactly equal; independent Decimal arithmetic identifies H30 at
2026-05-19 with returns 41.176471% and 8.163265%. Existing-field consistency
checks admit only the missing H30 field for these rows. A fresh call using the
fixed default reproduces both values. No DB writes were performed by these probes.

Regression tests verify holiday headroom and that an immature response still
leaves H30 missing. The combined suite now has 97 passing tests. This does not
invent missing sessions or guarantee a horizon for long suspensions.

Evidence: `history_horizon_window_probe.json`, `horizon_independent_check.json`,
`horizon_fixed_default_probe.json`, and `dry_first_rows.json` in the same audit
directory. `swing-main-axmi` tracks this request-window bug; the applying pilots
above subsequently verified the actual database updates.
