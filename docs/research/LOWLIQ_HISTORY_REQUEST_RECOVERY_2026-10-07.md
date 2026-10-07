# Reviewed historical request recovery and coverage index

Issue `swing-main-sz9t`, within the full historical capture `swing-main-d277`.
The original nominal 004310 request for June 2–August 30 returned
`KISOpenAPIError` without a saved provider payload. Its root cause remains
unknown. The failed receipt is preserved unchanged, SHA
`454e5d0a9b7a5cc26cade0059e0ed5e581ea37184ff5adde3a2e839affbe03e4`.

A separately recorded, one-attempt retry received all 61 expected trading dates
at 2026-10-07 13:45:58 UTC. Each of 366 OHLC, volume and amount values exactly
matches both the pinned v8 raw panel and the existing paired adjusted response.
This is a fixed-cohort comparison, not a general equivalence between nominal
and adjusted prices. Independent Decimal comparison confirmed both matches.

`recover_lowliq_history_request.py` pins the original failure, paired response,
full source panel, scope and collector dependencies before capture. Failed and
successful retry receipts are immutable; replay makes no network requests.
Consumers must explicitly supply the trusted supplement plan digest to resolve
this particular failed original. Altered identity, payload, inspection,
validation, original receipt or plan is rejected. No running collector or its
frozen dependencies were changed.

The production recovery directory is
`runtime_state/audit/lowliq_history_request_recovery_20261007/`:

- Plan SHA: `488cf55e6b1edfda943648482ad6a5aa5ca408692407579e777e25c211a46661`.
- Response SHA: `892c87d3716421d543a5a5cc17bb9170c4a2b301c2e99700a203929023036984`.
- Validation, resolved provenance and independent verification are retained.
- Actual replay made zero network calls and preserved all five original
  evidence files' bytes, sizes and modification times.

`index_lowliq_history_capture.py` freezes receipt path membership before reading,
validates each request/payload/inspection against the frozen scope, and retains
both original and effective statuses, paths and digests. Supplemental evidence
is opt-in and cannot conceal the original failed attempt. A running collector
may add files after enumeration; they remain outside that index snapshot.

The first verified snapshot contains 19,242 of 65,796 requests: 19,241 original
CAPTURED and one original REQUEST_ERROR; all 19,242 are effectively CAPTURED
after the reviewed supplement. The remaining 46,554 are explicitly unvisited
at that snapshot. Index SHA
`134237cf9bea1cc79311310ceee080f0414c99161ce7951688cc8392bf9829cd`
is stored at
`runtime_state/audit/lowliq_history_coverage_indices/index_20261007T134942906787.json`.

27 related tests passed, covering original and supplemented coverage, immutable
failure/replay, exact large Decimal values, incomplete or changed responses,
provenance tampering, duplicate/unknown receipts and stale scope. Availability
does not certify the full source, corporate actions, point-in-time inputs or
tradability. Source certification and publication remain false. No strategy
outcomes were computed, models refitted or live lane replaced.
