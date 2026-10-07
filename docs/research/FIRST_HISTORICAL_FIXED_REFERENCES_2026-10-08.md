# First historical fixed-reference batch

Issues `swing-main-1sug` and `swing-main-45fi`; broader source work remains
in `swing-main-01n3` and primary collection in `swing-main-qzrd`.

The pinned historical inventory contains 287 traded reference candidates in
187 securities. The first primary collection stopped after 45 of 256 windows:
38 complete, six empty direct searches and one partial. Its last request,
007070's `searchDetailsSub` POST, returned HTTP 403. The preceding main-page
GET returned 200. A separate viewer request in the partial 001510 window also
returned 403. The reason for either denial is unverified. Both original error
receipts remain preserved; this batch made no retries against those failures.

`audit_first_historical_fixed_references.py` revalidates the 38 complete cached
searches and their selected documents without network access. It accepts only
explicit fixed-reference templates, matches the effective date, issuer and
share class, and checks the official price against the independently captured
nominal close minus signed change. Original source boundary factors, prices,
positive volume and nominal receipt provenance must agree.

The verified scope is **27 events in 22 securities**:

| Code | Effective dates | Official reference prices, KRW |
| --- | --- | --- |
| 000640 | 2025-03-13; 2026-03-11 | 98,600; 104,600 |
| 000670 | 2024-12-27; 2025-04-25; 2025-12-29 | 401,000; 36,750; 48,400 |
| 000860 | 2025-04-30 | 11,930 |
| 001060 | 2023-12-27 | 35,800 |
| 001065 | 2023-12-27 | 32,750 |
| 001067 | 2023-12-27 | 61,000 |
| 001360 | 2024-01-04 | 2,060 |
| 001380 | 2026-05-11 | 2,200 |
| 001440 | 2024-01-30 | 9,720 |
| 001500 | 2025-01-14 | 6,600 |
| 001530 | 2023-12-27; 2024-12-27; 2025-12-29 | 28,650; 49,000; 19,810 |
| 002240 | 2024-12-27 | 18,060 |
| 003000 | 2025-05-30 | 3,935 |
| 003060 | 2024-05-13 | 1,281 |
| 003690 | 2024-11-06 | 8,080 |
| 004270 | 2026-07-21 | 6,400 |
| 004710 | 2026-06-08 | 11,630 |
| 005810 | 2024-03-04 | 29,050 |
| 006040 | 2024-12-30 | 36,100 |
| 006800 | 2026-03-16 | 69,200 |
| 006805 | 2026-03-16 | 23,900 |
| 00680K | 2026-03-16 | 21,500 |

Four preferred securities use explicit class-specific notices returned in the
common issuer's complete search. An empty preferred-code query is not evidence
that no notice exists. The 001530 identity check initially stopped on
`디아이동일` versus `DI동일`. A captured official listing links that company,
`DI동일보통주`, and `KR7001530005 (단축코드:A001530)`. The exact three-part binding
is required to accept this alias; it is an identity check, not a historical
availability certificate. Auction templates and the partial 001510 window are
excluded from this batch.

## Immutable normalization and verification

V12 applies these references cumulatively to v11 using 91 nonoverlapping rules
across 9,080 rows. The full 5,360,785-row comparison verifies identical schema
and metadata, all raw fields, and every field of the other 5,351,705 rows.
An independent 75-digit decimal calculation checks all corrected factors and
36,320 adjusted prices. Factors are exact after float conversion; the maximum
relative decimal representation error in prices is 2.54e-16.

The fixed 1,353-code / 872,671-date historical comparison is repeated using the
same 30,936-request snapshot. All four tables are exact for the other 1,331
codes. Entire nominal and provider-basis tables are unchanged. Thirteen of the
22 corrected codes now have no comparable cell above one KRW. The overall
diagnostic queue falls **213 to 200 codes**, with the same three anchorless
securities still unresolved.

Residuals are not waived. Large remaining differences include 001065 (55.88),
001067 (3,388.20), 003060 (1,666.00), and 004710 (309.05 KRW). Five other corrected
codes retain maxima between 1.001 and 1.202 KRW. The existing 27 reference events
are verified independently of those remaining differences; no rounded provider
prices are copied into the source, and no whole-code certification is issued.

83 related tests pass. The initial test expectation used an unreduced rational
pair and was corrected to 1600/1441. Actual verifier/normalizer replay made zero
network calls, reused v12, and preserved the bytes, sizes and modification times
of 2,191 existing files. The initial evidence version is preserved with its
exact implementation; v2 adds explicit security-name/class and alias provenance.
An attempted overwrite was correctly rejected by immutable publication.

## Honest capture exit status

The original primary collector returned shell status zero despite its structured
`CAPTURE_FAILED` result. Its frozen code and evidence are preserved.
`run_historical_reference_capture.py` is the new CLI entry point: it returns zero
only when every target window is complete, and two for failure, partial, empty,
or budget-limited collection. Its read-only `--receipt` mode requires a trusted
matching SHA256. On the actual terminal receipt, it returns **2**, reports
`capture_complete=false`, and leaves the original receipt unchanged.

Production evidence under `runtime_state/audit/`:

- `first_historical_fixed_evidence_20261008/` — preserved initial proof.
- `first_historical_fixed_evidence_v2_20261008/` — final proof and independent
  reconstruction of the original plan and all 45 terminal window counts.
- `kr_verified_events_v12_20261008/` — normalized panel and full independent audit.
- `lowliq_history_indexed_comparison_v12_20261008/` — fixed comparison and queue.
- `first_historical_fixed_replay_20261008.json` — replay and actual CLI exit proof.

Final evidence SHA: `f4614a90458804f7beffb235be31da7616661580863f7b4cf6042d39c140d49b`.
V12 panel SHA: `508f84d6b43c2e6a7d19d4057ef613d8791fcbe1435d87e6405fa648bf88265b`.

The separate historical quote collector completed 40,772 of 65,796 request
receipts before its time budget expired: 40,770 original captures and two
original errors. The known 004310 supplement remains separate; new 102460
recovery is tracked in `swing-main-gz0u`. Unvisited collection continues without
overwriting or automatically retrying those errors. These newer receipts are
not silently substituted into the fixed comparison snapshot.

Source, point-in-time, portfolio-return and publication certificates remain
false. No Q3 strategy outcomes, model fitting, or live lane replacement occurs
in this batch. H10/TP5 at 70% and two to three firing dates per five observed
sessions remains the qualification requirement, not a result of this audit.
