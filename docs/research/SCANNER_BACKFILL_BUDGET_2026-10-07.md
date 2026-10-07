# Scanner return backfill execution audit — 2026-10-07

The daily worker was still executing `backfill_scanner_full_returns.py` after
70 minutes. A one-second native process sample showed curl network polling;
it did not establish a deadlock. The existing worker is preserved.

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

The new bounded **applying** path must still be observed after the old worker
terminates. Issue `swing-main-1y4w` remains in progress for that operational proof;
`swing-main-l64n` tracks the full daily pipeline. No model or issued contract is
changed by this execution repair, and no edge-lane qualification is implied.
