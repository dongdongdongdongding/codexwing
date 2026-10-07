# Captured flow conflicts normalized, 2026-10-07

`swing-main-px2s` resolves the 10,679 overlapping conflicts discovered by the
[flow refresh recovery](FLOW_REFRESH_RECOVERY_2026-10-07.md). Code `ffc359c`
implements pinned captures and offline replacement; `845efbb` distinguishes
adjusted auxiliary prices from nominal investor quantities.

This is a bounded KIS source normalization. It does not certify all historical
flow rows, point-in-time availability, amount units, or a replacement trading lane.
All corroborating endpoints belong to KIS, not independent data vendors.

## Controls and diagnosis

The original 600-symbol collection response was retained. For every symbol,
the normalizer captured a repeated daily-investor response, a current-investor
response and an explicitly unadjusted J-market daily chart. All **1,800** requests
succeeded. Replacements require identical dates, exact agreement on all six
stored fields, balanced net investor quantities, buy-minus-sell identities, and
agreement with chart turnover and auxiliary price/volume.

Initially **10,657** conflicting rows passed and **22** were deferred because
their auxiliary volume disagreed with the unadjusted chart. Those 22 were spread
across 207940 (17), 247540 (4), and 290650 (1).

Additional controlled requests established a price-basis distinction:

- On all **18,000** captured daily rows, the four investor groups' total purchases
  and total sales each equal the **unadjusted** chart's volume exactly.
- On the three deferred symbols, all **540** stored values across 90 daily rows
  are unchanged when the investor API's price flag is set explicitly to 1.
- Their auxiliary volume and close match the explicitly **adjusted** chart
  exactly, including the dates that disagreed with the unadjusted chart.
- Cash turnover still agrees with both chart bases. No stored flow quantity or
  amount is rescaled.

Version 2 consequently requires the same nominal turnover and investor-total
checks, while permitting auxiliary close/volume to match an explicit adjusted
chart when they do not match the unadjusted chart. This is an exact source-basis
check, not a numeric tolerance. Twelve fresh control requests for the three
symbols verified all 22 deferred rows before the second application.

The old updater's append-only/global-maximum logic could never revise an already
inserted row. This explains persistence of discrepancies, but the original cause
of every discrepancy is not established. For example, 012510 had eight shifted
turnover observations while its net quantities already matched. No blanket
date shift or scaling factor was applied; each replacement is keyed to its own
captured date and values.

## Applied result and preservation

| Stage | Corrected rows | Deferred rows | Result |
| --- | ---: | ---: | --- |
| Repeated/current flow + unadjusted chart | 10,657 | 22 | committed, degraded |
| Explicit adjusted auxiliary-price controls | 22 | 0 | committed, ok |
| Fresh operational updater, 600 requests | 0 | 0 | exit 0, no conflicts or gaps |

The final fresh read ran 11:12:14–11:13:48 KST. All 600 responses were valid;
error, empty, stale, overlap-conflict and additional-row counts were all zero.
The source checksum did not change during this read-only verification.

Independent checks verified **64,074** values on the **10,679** corrected rows.
The other **1,652,688** rows remain exactly equal. All `(code,date)` keys and the
total of **1,663,367** rows are preserved; duplicate keys are zero. The 934 missing
rows inserted in the previous recovery remain intact. Repeating the final apply
reports already_applied and zero changes.

Source SHA256 chain:

| State | SHA256 |
| --- | --- |
| Before normalization | `5c44ff9a79a3d73c84abddb1482ae9be98eee4ac51739f79a08256d503e80c4d` |
| After stage 1 | `5212a4ee51dcee0e26aa93020851475676e4d55687dba073125489151ac10b8f` |
| Final | `ba24a26df7b1abc220f39b51012d8ecade05d40327ba8597fdd7d55622f4c121` |

Both stages hold the shared flow writer lock, check the original source hash,
verify backups, preserve all unrelated rows, write a prepared journal containing
the intended output hash, and atomically replace the parquet. A post-rename crash
is recognized by exact output and evidence hashes and its journal is finalized.
Existing version-1 capture plans remain supported.

Validation: **49 tests passed** for normalization and refresh, including rejected
cross-endpoint disagreement, adjusted-price basis checks, nominal investor totals,
tampered captures, concurrent writes, bad backups, preserved rows, idempotence,
and interruption after the atomic rename.

## Evidence and remaining scope

Production audit directory: `runtime_state/audit/flow_normalization_20261007/`.
It contains `full_controls/` and `basis_repair/` manifests, replacement plans,
pre-mutation backups and application receipts; `basis_verification.json`;
`independent_stage1.json`; `independent_final.json`; `post_refresh_receipt.json`;
and `repeat_final.log`. All raw responses and earlier conflicting data are retained.

The six stored fields keep their provider units. `swing-main-g6ey` still audits
amount-unit labels and consumer scaling. Older dates and symbols outside the
captured scope are not certified. No model, pick, historical recommendation,
contract outcome, lane gate or publication policy was changed. This source repair
does not establish the user's H10/TP5/70% and 2–3 firing dates per five sessions.
