# Official ex-reference price epoch v4 — 2026-10-07

A separate v4 research source applies **16 official ex-reference price events**
and removes **two mistimed paid-issue adjustments** across 17 securities. Exactly
**700 of 5,360,785 rows** change in the adjustment factor and adjusted OHLC only.
Independent full-panel verification preserves every raw field, all other
5,360,085 rows, schema and metadata. Tracking: `swing-main-l02t`.

## Explicit convention and official evidence

For each covered ex-date, the forward factor multiplies by
`prior nominal close / official KRX reference price`. The exact numerator and
denominator are preserved in the contract; rational arithmetic produces the
stored float only at the final step. Repeated events compound chronologically.
This is `KRX_OFFICIAL_EX_REFERENCE_PRICE_CONTINUITY_V1` for these covered events.
Earlier source bases and other actions remain unchanged and uncertified.

The [18-notice reconciliation](KR_EXRIGHTS_PRICE_BASIS_2026-10-07.md) supplies all
16 in-window official dates/reference prices and independently captured prior
nominal closes. All provider-reported percentages match the rounded official
ratios; the two-decimal percentages themselves are not used as precise factors.
The six separate bonus-share entitlement records remain evidence, but do not
replace exchange reference prices. Preferred 012205 keeps its own source and
its own reference, distinct from common 012200.

The two removed July adjustments concern paid subscriptions, not new July
ex-right events:

- **061970:** official ex-date June 18; 12,000,000 paid shares listed August 26 at
  KRW 2,855 per share. The heuristic applied total-share growth on July 30.
- **187660:** official ex-date June 29; 8,500,000 paid shares listed August 28 at
  KRW 3,085 per share. The heuristic applied total-share growth on July 28.

Their additional-listing bodies expressly identify paid shareholder allocation
followed by a public offering of unsubscribed shares. Both full captured Q3 KIS
nominal and adjusted OHLC paths are identical: **520 cells across 130 dates**.
The unsupported July increase is removed while the preexisting constant basis
is preserved. June pre-event prices are outside this provider capture; the June
factors themselves are not repaired or certified here.

## Guarded scope

| Code | First corrected date | Treatment | Rows |
| --- | --- | --- | ---: |
| 002070 | 2026-07-31 | official ex-reference | 43 |
| 012200 | 2026-07-27 | official ex-reference | 47 |
| 012205 | 2026-07-27 | official ex-reference | 47 |
| 042940 | 2026-09-22 | official ex-reference | 7 |
| 047920 | 2026-08-04 | official ex-reference | 41 |
| 061970 | 2026-07-30 | remove mistimed paid-issue factor | 44 |
| 187660 | 2026-07-28 | remove mistimed paid-issue factor | 46 |
| 199800 | 2026-08-07 | official ex-reference | 38 |
| 210980 | 2026-09-01 | official ex-reference | 22 |
| 220100 | 2026-07-15 | official ex-reference | 54 |
| 240600 | 2026-07-29 | official ex-reference | 45 |
| 255220 | 2026-07-21 | official ex-reference | 51 |
| 321370 | 2026-07-07 | official ex-reference | 60 |
| 340570 | 2026-08-06 | official ex-reference | 39 |
| 354200 | 2026-07-21 | official ex-reference | 51 |
| 475460 | 2026-09-16 | official ex-reference | 11 |
| 494120 | 2026-07-15 | official ex-reference | 54 |

The 29 rules split on dates, existing factors, share-count transitions and new
reference factors. Exact old factor, share count, per-rule row count and source
hash guards reject revisions. The wrapper additionally verifies each rule's
factor against its named contract and both date endpoints. All 26 supporting
body resources are hash-verified, including six entitlement decisions and both
paid-listing documents. Existing immutable builders remain hash-pinned.

## Independent checks

Audit directory: `runtime_state/audit/kr_verified_events_v4_20261007/`.

- `prepare.py` freezes source/evidence, exact rules and convention before build.
  `evidence/economics_verification.json` retains original official reference
  evidence, all prior-provider hashes, paid-issue evidence and limitations.
- `verify.py` independently checks the entire panel using a separately specified
  event schedule and 60-digit Decimal arithmetic rather than importing the
  normalizer. All 700 changed rows have the required factor and adjusted OHLC;
  all raw fields and 5,360,085 unaffected rows remain exact.
- **16/16 reference boundaries** satisfy adjusted prior close = adjusted official
  ex-reference price; the largest stored-float discrepancy is `5e-12` in source
  price units. This is price continuity, not an observed zero-return condition.
- All **1,105 dates / 4,390 comparable OHLC cells** were checked against KIS;
  **30 nontrading zero-OHL cells** remain unchanged. The two removed July events
  agree to floating-point precision across their entire captured Q3 histories.
- Other canonical/reference and KIS integer-price differences remain visible,
  generally up to one won; no provider exactness certificate is issued. The
  earlier, separately unresolved 354200 capital-reduction basis leaves a maximum
  full-window residual of about **KRW 51.94** after removing the final constant
  basis. Its raw prices and earlier adjusted factor are preserved.
- Original parent study source/code, all six fitted model hashes and the live
  KR producer hash remain unchanged. No H10 outcomes, returns or new models were
  computed. No live cache, universe, picks or issued contracts were replaced.
- **22 tests passed** across reference schedules, compounding, tamper guards and
  the streaming normalizer. Actual second execution returned `REUSED`; panel,
  manifest and receipt hashes, sizes and modification times were identical.

| Artifact | SHA-256 |
| --- | --- |
| Parent v3 panel | `31db990498de17a29b626a7da52fadf6bae36b7434a092f457bdfc4058c6af70` |
| New v4 panel | `78a8d8c296d90484da62fd3dd4cff20079e07e794dad863dcd1f35d9f7848482` |
| Independent verifier | `cc8b77768369b635400504611b3a9ca3bf5574ab6d4499a53a2725096ddda69f` |

Across the four partial epochs, **31 event corrections on 30 codes** affect
**1,157 distinct rows**. These counts are not complete-history certifications.
The remaining 35 original mismatch codes, earlier actions and residuals on the
corrected codes, pre-June feature history and final H10 data still need review.

Price continuity does not value cash subscriptions, sold rights, delayed bonus
share availability or portfolio wealth. Event-spanning H10 execution/valuation
needs separate evidence before claiming realizable returns or qualifying a lane.
`source_certified`, `publication_allowed` and `portfolio_return_certified` remain
false. This partial source cannot replace the frozen parent study silently.
