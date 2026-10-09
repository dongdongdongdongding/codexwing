# Complete historical source coverage

Issues `swing-main-5ki2` and `swing-main-e4sk`.

The fixed historical quote collection has finished all **65,796 requests** for
2,949 securities. Its terminal receipt reports 65,793 captured responses and
three preserved request errors. A new immutable index explicitly adopts the
three reviewed supplements for 004310, 102460 and 361570. It contains 65,796
usable effective responses and **zero unvisited requests**. The original
errors remain in place; the index records both original and replacement
provenance. Complete collection does not certify the source's economic meaning.

The terminal collector run is
`lowliq_history_capture_20261007/runs/20261009T061926924490.json`, SHA
`0ca6355c75bc7196399b3c97de78c1cfc1bad6ee23b9f65e48bd20eed2e91658`.
It reused 60,313 receipts, made 5,483 new calls, and terminated normally with
`ATTEMPTS_COMPLETE`. No historical collector remains necessary for this scope.

361570 recovery used a separate, single-attempt capture with automatic retries
disabled. The original adjusted request for 2023-12-15 through 2024-03-13
failed with `KISOpenAPIError` and no saved payload; its root cause is unknown.
The paired nominal receipt and v14 source have exactly matching data for the
58 expected dates. The reviewed source's adjustment factor remains 3.0 from
the start of that segment through the source cutoff. The new adjusted
response matches all **348 OHLC/volume/amount cells** of both references
exactly. This supports adoption of this particular response; it is not a
general rule equating nominal and adjusted prices.

Independent Decimal comparison confirms every recovered cell. A network-blocked
replay makes zero calls and preserves all six recovery/original evidence files
byte-for-byte with their size and modification time unchanged. Source values,
the original failure, and the frozen collector are not edited.

Recovery evidence: `lowliq_history_361570_recovery_20261009/` under production
`runtime_state/audit/`.

- Original failure SHA: `41055f8b872dc576045005c55f54bd5396509ae959111270439e9932dba6dafb`.
- Trusted recovery plan SHA: `bd8e9dfa45eb9268ea8fd0b29c24888f6cbe07dfd782eecd958a6470bb55ce13`.
- Accepted response SHA: `f2f3bdd206d1e274e6ce65f4210564c17a3b889f01934d4bf229537ce02842d5`.

The complete index is
`lowliq_history_coverage_indices/index_20261009T095010842741.json`, SHA
`6e0a453ca58d881551536f191f09bd6991e7264084c7854760d398a3b1b1cacc`.
All 46,520 entries of the preceding index are exactly unchanged; 19,276 entries
are added. Independent scope verification confirms unique request membership,
all three original-error provenance chains, and the absence of unvisited scope.

The full v14 comparison completes **2,949 securities / 1,857,109 scoped dates /
11,142,654 nominal numeric cells**. All four preceding comparison tables remain
exact for the earlier 2,024 securities. Across the full scope, nominal close,
volume and amount match exactly. Of 213,348 O/H/L differences, 213,342 meet the
nontraded representation convention. The same six nonconventional cells remain
on 001527 (2024-03-28) and 145210 (2025-03-21); neither is filled or certified.

The additional 925 securities contain 543,921 scoped dates. An independent
Decimal comparison revalidates 9,647 nominal requests and **3,263,526 numeric
cells**. Every new nominal close, volume and amount matches the source. The
63,489 new O/H/L differences all satisfy the recorded nontraded zero-versus-close
representation convention. No new positive-volume nominal discrepancy is
introduced by this additional scope.

All 63,489 independently computed new nominal difference records exactly match
the main comparator, including their convention classifications. No request
contains additional provider dates outside the fixed expected scope.

The complete comparable-adjusted review queue contains **531 securities**:
the prior 316 plus 215 from the added scope. This is expansion of coverage;
the earlier cohort's four tables and review membership are unchanged. Queue
SHA: `ae2e2c21702e907ff4fc87b757bf67466cf06bbb6cd0393d4a1c84b4f234a675`.
The earlier 419-event inventory belongs to the preceding 316-code queue and
does not yet describe these 215 additional securities.

Eight securities have no traded anchor in the fixed scope: 058530, 066410,
068940, 099520, 121800, 217480, 377460 and 405640. The three additions have
zero volume and amount on all their scoped dates: 217480 and 377460 each have
679 dates from 2023-12-15 through 2026-10-02; 405640 has eight dates from
2024-05-29 through 2024-06-10. **405640 has traded dates outside this scope.**
An initial verification assertion using its entire post-December source history
was rejected; the corrected check binds the exact frozen request dates.
Unavailable anchored comparisons are not classified clean.

The complete index uses the same immutable v14 panel, SHA
`700903bde57d828f77a0a01df4d1d62e620c2cf0bd6df8fc050c36fc6910d069`.
Snapshot, terminal, and independent nominal evidence is preserved in
`complete_history_snapshot_20261009/`. The full comparison has a separate
output directory, `lowliq_history_indexed_comparison_v14_complete_20261009/`;
preceding indices, comparisons and event inventories remain intact.

The recovery protocol, index, expanded reconciliation, original inventory and
document-window tests pass: **38 tests**. This change does not refit models,
compute Q3 strategy outcomes or replace a live lane. Source, point-in-time,
portfolio-return and publication certificates remain false.
