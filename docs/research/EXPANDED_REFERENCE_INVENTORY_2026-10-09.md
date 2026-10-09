# Expanded historical reference inventory

Issue `swing-main-euuu`. The v14 source and the fixed 46,520-receipt index
now have an event-level inventory for all 316 securities in the expanded
adjusted-price review queue. The audit also rechecks the 21 securities present
in the original v11 inventory but absent from the current queue. Removal from
the queue does not serve as evidence of a repaired event.

The resulting union contains 337 securities and 225,916 scoped dates. All
3,993 nominal requests are read from preserved receipts, with the original
error and reviewed-supplement provenance checked where applicable. The
original v11 inventory, its 287 events, and its 256 document-search windows
remain unchanged.

| Scope | Securities | Scoped dates | Primary-review events | Nontraded boundaries |
| --- | ---: | ---: | ---: | ---: |
| Current expanded queue | 316 | 211,657 | 419 | 144 |
| Entire original v11 cohort rechecked on v14 | 213 | 142,762 | 245 | 107 |
| Newly added securities | 124 | 83,154 | 174 | 40 |
| Union, without double counting | 337 | 225,916 | 419 | 147 |

Every original primary-review event is re-evaluated at its actual source and
provider date pair. Of the original 287 events, 245 remain primary-review
events, 39 now have arithmetic-sized residuals, and three agree exactly.
Thus the 42 events corrected in v12–v14 no longer have large factor
disagreements. There are no new primary-review events within the old cohort.
The added 174 events come from 118 newly inspected securities. Neither the
arithmetic category nor the absence of a large discrepancy is a source or
portfolio-return certificate.

Across the union, 202,293 paired rows have positive volume: 201,807 factor
ratios agree exactly, 66 have arithmetic-sized residuals, 419 require primary
review, and one has an unsupported provider quote. The remaining scoped rows
are 23,286 paired nontraded rows and 337 first-scope boundaries. All 147
nontraded factor/share-count/close boundaries remain explicit, including
three from securities no longer in the current adjusted-price queue.

The unsupported quote is **145210 on 2025-03-21**. The provider reports
positive volume 1,015, amount 1,142,890, close 1,126, zero price change, and
`prdy_vrss_sign="0"`. It is also the newly observed nominal zero-O/H/L
disagreement described in the expanded history report. The unknown sign is
not silently converted to an unchanged-reference quote. Issue `swing-main-r7rt`
retains the session-semantics investigation; no raw field or execution
assumption is changed.

Validation performed:

- `python3 research/inventory_expanded_historical_references.py --root <PROD>`
  completed using only the pinned source and captured provider receipts.
- An independent verifier using Decimal precision 80 and cross-products
  checked all **677,748 nominal numeric cells**, all paired classifications,
  every first-scope/unsupported/nontraded boundary, and all 287 old-event
  transitions. It imports none of the production inventory, signed-reference,
  or reconciliation functions.
- The expanded reconciliation, original inventory, document-window, and
  index test suites pass: **26 tests**. Cases prevent a missing date, changed
  raw value, unsupported sign, or duplicate event from becoming a resolved
  diagnostic.

Production evidence is in
`runtime_state/audit/expanded_historical_reference_inventory_20261009/`:
`manifest.json`, `by_code.json`, `primary_review_events.json`,
`old_event_reconciliation.json`, `summary.json`, the independent verifier and
result, and the network-blocked replay verification. Inputs are pinned:

- Source v14: `700903bde57d828f77a0a01df4d1d62e620c2cf0bd6df8fc050c36fc6910d069`.
- Index: `3573f9cf558c9c733e0fa4b1c63127a080bf6b89554ca78696150d2980cbefd7`.
- Expanded queue: `e5583edcf124d94bd1b4584222518ea6d450db4c64ec92c281d35f073cbebcb3`.

The live history collector is independent of this frozen snapshot. Its prior
run ended with 60,313 original receipts, including three preserved request
errors, and collection of unvisited scope resumed. The newly observed 361570
adjusted-history error is tracked in `swing-main-5ki2`; it is outside the
snapshot used here. The two previously reviewed supplements do not authorize
substitution for this third error.

Actual daily-operation receipts separately show terminal return code 9 for
the October 7 and October 8 Nasdaq regular-open batches. Their failed steps
are preserved in `runtime_state/audit/operations_terminal_20261009_1448/`
and tracked in `swing-main-5lj2`. This inventory does not imply that the
service pipeline is fully healthy.

Source, point-in-time, portfolio-return and publication certificates remain
false. No Q3 strategy outcome is computed, no model is refit by this audit,
and no live lane is replaced. The requested cadence and H10 +5% touch rate
remain unproved.
