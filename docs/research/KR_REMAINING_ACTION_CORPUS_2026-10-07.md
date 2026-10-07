# Remaining KR corporate-action source corpus — 2026-10-07

The fixed remaining 60 mismatch codes now have a verified public-disclosure
capture and explicit evidence for two preferred-share issuer searches. This
completes source collection for the declared query and title scope; it does
**not** certify any additional adjustment factor or qualify an H10 strategy.
Tracking: `swing-main-uo0z`; economic reconciliation remains `swing-main-5pfa`.

## Frozen scope and actual collection

The cohort is the original 65-code trace, less the five independently corrected
codes 005440, 008830, 291810, 270520 and 071950. All 60 remain, including 13 with
no heuristic Q3 event. The other 47 contain 52 heuristic events. Names are pinned
to previously captured KIS response hashes. Queries cover June 1–October 7, 2026,
using KIND's current latest-report search (`lastReport=T`), not an as-of historical
information set. Viewer revisions exposed at capture time are retained.

| Evidence | Actual result |
| --- | ---: |
| Original security queries | 60/60, 1,842 disclosure rows |
| Original title-selected records | 417: 416 captured, one HTTP 403 |
| Original response receipts | 1,905: 1,904 HTTP 200, one HTTP 403 |
| Supplemental title matches (`액면`, `기준가격`) | 34 captured |
| Separate retry of failed public document | One captured, HTTP 200 |
| Additional issuer query: 000880 | 73 rows, 11 selected and captured |
| Supplemental response receipts | 165, all HTTP 200 |
| Combined unique `(query_code, acptno)` selected records | 462 |
| Combined HTML body resources | 884 |

Body resources include revision documents and tables of contents; 884 is not a
count of unique economic events. The base terminal receipt remains partial:
57 complete searches, two empty searches (00088K and 012205), and one partial
113810 document. Supplementary evidence is additive and preserves that history.
The 113810 retry is acceptance 20260727000425, a trading-halt release notice for
an ensuing stock consolidation listing; the same public request returned 200.

All actual searches fit one page (maximum 73 rows). The collector checks complete
pagination, stable reported totals and duplicate acceptance numbers; changing
and duplicate multi-page totals are also covered by tests. It records URL,
request, UTC capture time, status, byte length, raw SHA-256 and extracted-text
SHA-256 for every response. It never edits price data, models, issuance records
or live selection.

## Preferred-share evidence and limits

- **00088K / 한화3우B:** the issuer 000880's
  [August 20 changed-listing notice](https://kind.krx.co.kr/external/2026/08/20/000527/20260820001274/68155.htm)
  explicitly identifies `KR700088K015` and `A00088K`, with changed listing on
  August 25. This supports an issuer-search relationship, not substituting common
  shares for the preferred security. Acceptance 20260824000466 separately gives
  an evaluated price of KRW 29,250 for the third preferred class and states that
  the opening auction determines the reference price. Do not treat the evaluated
  price as the realized reference or derive a portfolio adjustment solely from
  the outstanding-share ratio.
- **012205 / 계양전기우:** the existing 012200 query contains the explicitly named
  [preferred-share ex-rights notice](https://kind.krx.co.kr/external/2026/07/24/000769/20260724001614/99301.htm),
  acceptance 20260724000769. It specifies first preferred shares, a KRW 6,710
  reference price and July 27 ex-rights date. The link rests on the exact security
  name and stock class; that body does not directly contain the short code or
  ISIN. Entitlement terms and the appropriate historical factor still require
  separate economic reconciliation.

## Verification and reproducibility

Production audit directory:
`runtime_state/audit/kr_remaining_action_documents_20261007/`.

- `verify.py` independently verified all 1,905 original raw/text hashes, request
  code/date scope, 1,842 parsed records and totals, selected/completed/failed
  partitions and body references. `first_result.json` preserves the first run.
- `verify_supplement.py` independently verified all 165 supplementary receipts,
  exact 35-document expansion/retry scope, issuer search rows, every viewer
  revision/routing/body relationship, preferred-share evidence and combined
  counts. The original failed receipt remains intact.
- Base replay: zero network requests and 5,777 captured/per-code files unchanged.
  Its execution summaries may update; these are not immutable source receipts.
- Supplement receipt-level replay: zero network requests; all 495 captured files
  retained exact hashes, sizes and modification times. The supplement driver is
  a one-shot immutable-result runner: do not rerun its `run()` as an idempotent
  orchestration command. Its receipt cache was tested separately.
- `tests/test_kr_action_documents.py`: **12 passed**, including malformed totals,
  duplicate pages, cache tampering, budget interruption, all document revisions,
  and unresolved supplementary bodies.

| Frozen artifact | SHA-256 |
| --- | --- |
| Base plan | `5c3548c3fa650ec277f89dc33938281bae9d18a35e5c7ea63668230301cede12` |
| First base result | `bef5ec9d76b90f7ee2b92fb5ca27c9c75756942b67e4f65df1642bee7df65c24` |
| Supplement plan | `b1df2491fe403500d54d2161d7780b635d1d476d3f9495576824a3bbd55c6c37` |
| Supplement result | `4e4c326506cd7ada3faf8629657d6b847b624d7e2cae4bd99cf0e1287ad3b679` |
| Supplement verifier | `6c7beabcc22c63aa6cf96f065961d509bc944086fa4a5313377ccdaaa4cf7ad1` |

Code fingerprints are pinned in the plans. This is current observed evidence,
with a fixed date window and title selection; it is not proof of exhaustive
historical actions, pre-June lookback correctness, historical availability or
terminal H10 labels. No touch rates, returns or model outcomes were computed.
The five supported corrections remain in the separate v2 research source;
remaining 60 security histories still require economic verdicts.
