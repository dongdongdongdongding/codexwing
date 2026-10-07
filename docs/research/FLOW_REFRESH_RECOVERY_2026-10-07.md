# Flow refresh recovery, 2026-10-07

Issue `swing-main-sie4`; code `905a7e2`, corrected request date `e02d448`.
The updater now reports failed requests, empty responses, coverage gaps and
historical conflicts separately. This fixes false success reporting, **not** the
entire flow dataset. Historical conflicts remain under `swing-main-px2s`.

Later on October 7, these 10,679 conflicts were verified and corrected in two
stages; the fresh 600-symbol read then reported zero conflicts. See
[source normalization](FLOW_SOURCE_NORMALIZATION_2026-10-07.md). The initial
observations and source hashes below remain the historical recovery record.

## Actual source diagnosis

At 10:49 KST, the same Samsung 005930 endpoint returned:

| Requested date | ETC parameter | Result |
| --- | --- | --- |
| 2026-10-07 | blank | OPSQ2001, TIME LIMIT 00:00 ~ 15:40 |
| 2026-10-06 | 1 | rt_cd=0, 30 rows |
| 2026-10-06 | blank | rt_cd=0, 30 rows, identical output2 |

Thus the old ticket/session rationale claiming a global API availability window
was unsupported. A completed date works at the same time that the current date
fails. The updater requests each symbol's latest observed completed `px_long`
date and excludes current/future dates from insertion. This does not establish
that every historical value is final or that every market session is represented.
The [official KIS example](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/investor_trade_by_stock_daily/investor_trade_by_stock_daily.py)
documents this endpoint and its input date; the availability result above is from
our captured paired requests, not an inferred official schedule.

## Deployed behavior

- Repository updater `multi_agent/tools/update_flow_cache.py` replaces the external
  script; the original external file is backed up and now execs the repository entry point.
- Preserves the existing top-600 median-liquidity collection scope. It is not a
  point-in-time research universe and does not certify all 2,695 cached symbols.
- Matches normalized `(code, date)` keys, filling returned holes even when another
  symbol has a later global maximum. No malformed numeric values become zero.
- Preserves every existing row. Captures raw responses, detects conflicts, uses
  a writer flock, detects legacy writers, backs up before writes, checks source
  hashes, and atomically replaces only after validation.
- Each run keeps a complete receipt with per-symbol expected/cached dates,
  response hashes and counts. The session runner assigns a unique batch receipt
  and embeds its summary/path/hash independently of truncated stdout.
- Flow is a research/PEAD shadow cache in the inspected consumers. Operational
  investor features call KIS directly. It remains an optional batch step, but
  failure/partial results return 2 and make the enclosing batch nonzero through
  its existing optional-failure aggregation. It is not a required scan dependency.

## Production evidence

Audit root: `runtime_state/audit/flow_update_20261007/` in the production checkout.

| Run | Requests | Valid | Errors | Added rows | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| Initial current-date run | 600 | 0 | 600 | 0 | exit 2, source unchanged |
| Completed-date run | 600 | 600 | 0 | 934 | exit 2: historical conflicts |
| Captured-response replay | 600 | 600 | 0 | 0 | no write, same conflicts |

The completed-date run ended at 10:52:38 KST. All 600 symbol-specific expected
latest keys are now present; this is not a claim that all have an October 6 row.
The 934 additions cover 76 symbols, June 29 through October 2. Independent Decimal
parsing verified all 5,604 numeric values against captures; all 1,662,433 original
rows remain exactly equal, with no duplicate keys. New total: 1,663,367 rows.

Before SHA256: `c3c6c25169805b43fcf700c921a1ba2190b0110b2751f0c9bb717d9d5b9e49f1`.
After SHA256: `5c44ff9a79a3d73c84abddb1482ae9be98eee4ac51739f79a08256d503e80c4d`.
Raw captures and backup:
`/Users/dongdong/research_cache/.flow_updates/20261007T014958865937`.

There are **10,679 conflicting overlapping rows**, preserved without revision.
Field counts: foreign quantity 8,585; institutional quantity 5,074; retail quantity
9,820; foreign amount 7,674; institutional amount 4,349; cumulative amount 9,132.
Examples include apparent adjacent-date displacement for 012510 and changed
October 6 quantities/turnover for 005930. Cause is not established. These need
source-finality, date alignment and market-basis verification before replacement.
`overlap_conflicts.json` records every difference; `independent_verification.json`
records preservation and insertion checks. Amount units also remain a separate
unresolved audit, `swing-main-g6ey`; no rescaling was performed.

Validation: **87 tests passed**, covering API failure, empty/malformed response,
strict numeric parsing, signed quantities, per-symbol holes, provisional dates,
source-change rejection, backup, repeat behavior and session receipt attachment,
plus existing session/dispatch/shell checks.
An actual one-symbol read-only execution through `_run_command` also attached
its unique receipt (25 conflicts, exit 2, no source change), recorded in
`one_symbol_artifact_attachment.json`. It was a scoped attachment check, not an
additional full daily batch.

## Concurrent operational state

KR worker finished 10:33:14 KST, rc0. US worker finished 10:46:32, rc0, with an
actual report containing 14/14 batches and 3,972/3,972 scanned symbols, 182 results.
One US batch records error_count=1 and worker_error_count=1; their sum is reported
as 2 and may double count. `swing-main-cpb8` tracks the misleading success exit and
counting semantics. These 182 results are not qualified replacement-lane picks.

Original primary process 54858 and batch 75970 remain active; their registration
has not been retired and no duplicate batch was launched. API health/picks/ops
endpoints returned HTTP 200. The overall user goal is still active: no replacement
has demonstrated the required 2–3 firing dates per five observed sessions plus
H10/TP5 touch probability of at least 70% with the preregistered validation gates.
