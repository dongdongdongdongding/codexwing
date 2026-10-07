# Intraday failed-slice diagnosis and guarded checkpoint recovery

The 17:15–19:15 KST backfill (`20261007T171511552855`) reported ten `ValueError` requests. A fresh, read-only capture of those exact code/date/hour identities found **eight now-valid responses and two reproducible OHLC violations**. The original failing payloads were not retained, so the fresh captures cannot prove all original error causes or provider revisions.

All **440 accepted rows** from the eight valid responses already match the existing cached OHLCV exactly, with **zero new timestamps and zero conflicting values**. No price-bar repair or invented fill is justified. The recoverable difference is stale acquisition checkpoint state.

| Code / date | Accepted failed hours | State after verified recovery |
|---|---|---|
| 025860 / 2026-09-28 | 10:00 | Four requested slices completed |
| 388610 / 2026-09-29 | 15:30 | Four requested slices completed |
| 417180 / 2026-09-29 | 15:30 | Four requested slices completed |
| 419120 / 2026-09-29 | 11:30, 10:00 | Four requested slices completed |
| 443250 / 2026-09-29 | 11:30 | Partial; 15:30 response remains invalid |
| 444530 / 2026-09-29 | 11:30 | Four requested slices completed |
| 446840 / 2026-09-29 | 15:30 | Partial; 11:30 response remains invalid |

`REQUESTED_ALL_SLICES` means the four acquisition requests were accepted, **not** that every trading minute is available. `session_complete` stays null, and session completeness remains `NOT_ESTABLISHED`.

The two malformed responses are query-dependent:

- 443250, 09:04: the 15:30 query returns O/H/L/C `4905/4945/4945/4945`, volume 150, while the 11:30 query returns `4945/4945/4945/4945`, volume 1. Both report cumulative traded amount 735,790. The cache matches the valid latter row exactly.
- 446840, 09:00: the 11:30 query returns `3200/3155/3155/3155`, volume 186, while the 15:30 query returns valid `3200/3200/3155/3155`, volume 186. Both report cumulative traded amount 594,435. The cache matches the valid latter row exactly.

These observations do not justify clamping high/low, discarding validation, certifying the rejected request or claiming the provider's internal cause. Both invalid payloads remain preserved.

`research/recover_intraday_slice_checkpoints.py` provides a guarded, resumable recovery. It requires the exact frozen failed-request identities, provider payload hashes, unchanged parser dependencies, valid OHLCV and complete equality against existing cache rows. It stores immutable before/after state files, verifies backups, preflights all targets, repeats compare-and-set before atomic replacement, and takes the existing operational writer lock. It never writes Parquet price files or changes the original run report. Unexpected cache differences, new timestamps or changed state abort the plan.

Validation: **42 tests passed**, including mismatched cache values, malformed bars, preserved partial status, concurrent changes, whole-plan preflight, interrupted multi-file resume, idempotent reuse active-writer rejection and rejection of a reused plan outside the locked cache. A coherent snapshot of all seven actual cache/state pairs was used for an isolated rehearsal: eight hours recovered, seven price files byte-identical, other dates preserved, five complete-request states and two partial states. Actual replay changed none of 23 audit/state files and made zero network calls.

**Live application completed at approximately 22:56 KST.** Natural backfill PID
11105 terminated after its 7,200-second budget and released the writer lock.
It was not restarted or interrupted. A fresh plan from current live state
revalidated all eight requests and 440 cached rows, then atomically updated seven
checkpoint files. The live plan SHA is
`8364a590d1c12e9c624ee8707672e59c9c4353befb99aa35b006f89704acd9b5`.

Independent verification confirmed all seven price files unchanged by hash and
file identity, all 50 other day states unchanged, eight hours recovered, five
`REQUESTED_ALL_SLICES` states and two preserved partial states. Actual live replay
returned `REUSED` with zero writes and preserved all 23 audit/state files' bytes,
sizes and modification times. Evidence is in
`checkpoint_recovery/independent_live_verification.json`. No network request was
made during planning, application or replay. This recovery is complete; session
completeness and the two malformed responses remain unresolved.

Commands from the deployed checkout:

```bash
python3 research/recover_intraday_slice_checkpoints.py --root /Users/dongdong/Projects/codex_swing/swing-main
python3 research/recover_intraday_slice_checkpoints.py --root /Users/dongdong/Projects/codex_swing/swing-main --apply
```

Evidence is under production `runtime_state/audit/intraday_failed_slices_20261007`: original report, frozen plan, ten provider responses, diagnosis, overlap comparison, isolated rehearsal and live recovery evidence. Recovery is tracked in `swing-main-x0iz`; broad daily coverage remains `swing-main-5lj2`. This does not resolve the unvisited pairs, the two invalid requests, US/scanner partials, or any strategy qualification.

The newer natural run `20261007T205547317819` ended `BUDGET_EXHAUSTED` after
20,772 requests, adding 84,798 rows. It reports seven request errors, three
storage errors and 610,735 unvisited pairs. Its original terminal report is
preserved separately at `runtime_state/audit/intraday_terminal_20261007_205547/`,
SHA `99aef45f30c266c5828b4794d32aef8a4845284ce805057e7a05daf162b303bb`.
Those new failures are separate from the recovered older checkpoint cohort;
neither this repair nor process termination establishes overall pipeline health.
