# Full fixed-cohort recheck after v6 — 2026-10-07

Rechecking **all 1,310 original securities / 85,104 dates** finds six additional
adjustment contradictions in suspended-period closes. These were outside the
original 65-code **traded-row** mismatch cohort. They must be reconciled before
the source is accepted; nontrading rows can still affect historical features.
The v6 panel remains unchanged and uncertified. Tracking: `swing-main-iti8`;
official evidence collection: `swing-main-5yeb`.

## Full comparison

The audit reuses the exact original June 30–October 2 calendar and all **2,620
hash-pinned KIS responses**. It compares 510,624 raw OHLCV/amount cells. The only
raw differences remain the same 4,182 OHL cells across 1,394 nontrading dates:
the panel keeps zero OHL, while the provider repeats a nonzero value. Every
nominal close, volume and traded amount agrees. These rows are not treated as
fills. Original nominal-difference and provider-basis tables remain exactly equal.

After separating those zero-OHL conventions, **336,234 adjusted price cells**
remain comparable. Anchoring each history to its last traded adjusted close gives:

| Scope | Differences above 0.000001 KRW | Securities |
| --- | ---: | ---: |
| Positive-volume dates | 2,842 | 30 |
| Nontrading closes | 244 | 12 |
| Combined | 3,086 | 36 |

Of 204 differences strictly above one KRW, **141 exceed `1.00000001` KRW**.
All 141 are nontrading closes in the six codes below; the remaining near-boundary
differences are kept in the diagnostics. The numerical cutoffs are for reporting,
not certification or removal of data. The maximum remaining difference is about
KRW 2,080.

## Independent coefficient intervals

For each comparable cell with v6 adjusted price `p` and integer provider price
`a`, intersect the constraints `a/p <= coefficient < (a+1)/p`. This tests whether
one constant scale followed by truncation could reconcile the whole captured
history. It does not prove a provider implementation or corporate-action truth.

- **1,292** securities have a nonempty half-open interval.
- One additional security, 199800, has coincident closed bounds but an empty
  half-open interval; it is not silently counted as compatible.
- Eleven have strictly empty intervals with relative gaps between roughly
  `4.4e-17` and `3.5e-16`. These floating-storage boundary discrepancies remain
  explicit rather than being waived by tolerance.
- Six have much larger interval contradictions, about **3.50%–24.37%**.

| Code | First traded date in window | Observed nominal open | Event evidence now captured |
| --- | --- | ---: | --- |
| 002210 | 2026-07-30 | 1,946 | Trading resumption and auction-reference method |
| 051360 | 2026-07-27 | 10,010 | Spin-off capital reduction / changed listing |
| 079190 | 2026-07-23 | 1,102 | Capital reduction / changed listing |
| 175250 | 2026-09-03 | 2,870 | Trading resumption after listing-maintenance decision |
| 210120 | 2026-08-20 | 1,991 | Par-value consolidation / trading resumption |
| 214330 | 2026-07-08 | 6,950 | Capital reduction and auction-reference method |

The opens are observations to corroborate against signed quote changes and the
official event terms before generating corrections. For example, several old
heuristics connect the pre-suspension price to the resumption **close**, absorbing
that day's movement. No correction is applied by this audit.

## Primary evidence collection

The six-code scope was fixed from the full-cohort contradictions before any
strategy outcomes. The collector searches all June 1–October 7 disclosures,
including reference-price/par-value titles. It records **183 search results**,
selects **30 corporate/reference documents**, and separately captures both
remaining trading-status documents. The combined evidence has **32 documents,
229 successful HTTP receipts and 115 body resources including revisions**.

The independent verifier checks every receipt hash and byte count, reconstructs
text directly from HTML without newline conversion, reparses the complete search
scope, and verifies viewer document numbers and routed body URLs. Capturing the
current evidence does not establish historical availability.

## Validation and limits

- **38 tests passed**, including interval boundary rejection and existing source
  and document capture tests.
- Independent rational-number verification covers all 1,310 histories and
  336,234 comparable adjusted cells. Saved Decimal residuals agree with the
  rational calculation within `1.873e-23` from numeric representation.
- The actual repeat performs zero network requests and leaves **683 files**
  unchanged in hash, size and mtime; the two-document supplement is separately
  replayed with zero requests and unchanged artifacts.
- Original study code, six model artifacts and the live KR producer retain their
  hashes. No model fitting, strategy outcomes, live data changes or lane promotion
  are performed.

Audit directories in the production checkout:
`runtime_state/audit/kr_v6_full_cohort_20261007/` and
`runtime_state/audit/kr_suspended_references_20261007/`.
The full-cohort verifier SHA is
`4bc733597ae335caccf90af9e744da69c4fa58011e8c07e7c2a02259e6d1d62b`;
the primary-document verifier SHA is
`57a14cb1b86068ce7e52bfd54733bb3a0ef9829918a995400cc31e7a8ab583fc`.

The next source repair must cover these six boundaries, then repeat this whole
cohort. Earlier feature lookbacks, cash/share entitlements and mature H10 strategy
validation remain separate requirements. Neither this audit nor the prior 63-code
repair establishes the requested weekly cadence or 70% touch rate.

## Separate daily-pipeline observation

The October 7 19:40 US refresh reported 129 failed symbols. A read-only comparison
with the captured 18:30 official Nasdaq directory and the existing session-tape
instrument filter separates 56 absent symbols, 70 listed instruments excluded by
that filter, and three current tape instrument types: ATTT and MMEDV with incomplete
adjustment histories, SVA without the requested session. This is instrument
classification, not proof of trading eligibility or a successful refresh.

The daily feature collector uses its own FDR universe. The earlier scanner-only
membership repair explicitly did not alter that path. The report does not delete
historical sources or narrow coverage to make the batch green. Evidence is saved
in `runtime_state/audit/daily_partial_scope_20261007/`; recovery remains
`swing-main-5lj2`. Newly scheduled daily and KR scan workers were confirmed live
around 20:21 KST and were not restarted.
