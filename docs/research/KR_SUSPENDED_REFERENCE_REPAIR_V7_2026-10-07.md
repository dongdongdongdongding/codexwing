# Suspended-history reference repair v7 — 2026-10-07

The v7 research source corrects the six boundaries found by the full v6 cohort
audit. **249 rows** change in adjusted OHLC and `adj_factor`; every raw field
and the other **5,360,536 rows** remain exact. Direct comparison against the
original source gives a cumulative **69 codes / 2,289 distinct changed rows**.
Tracking: `swing-main-6hsa`; source qualification: `swing-main-5pfa`.

## Actual reference prices

Each official event date is corroborated by the frozen nominal KIS response and
independent marcap prices. `KIS close − signed daily change` equals both sources'
opening price, with positive volume and identical closes. The two KOSPI notices
explicitly specify the first-auction-price method; the other four establish the
changed-listing or trading-resumption date. Their reference prices are inferred
from the corroborated quotes, not claimed as fixed prices printed in the notice.

| Code | Effective date | Prior nominal close | Reference | Event close | Changed rows |
| --- | --- | ---: | ---: | ---: | ---: |
| 002210 | 2026-07-30 | 973 | 1,946 | 1,800 | 44 |
| 051360 | 2026-07-27 | 16,090 | 10,010 | 9,010 | 47 |
| 079190 | 2026-07-23 | 571 | 1,102 | 1,100 | 49 |
| 175250 | 2026-09-03 | 2,170 | 2,870 | 2,110 | 20 |
| 210120 | 2026-08-20 | 930 | 1,991 | 1,992 | 30 |
| 214330 | 2026-07-08 | 2,555 | 6,950 | 9,030 | 59 |

For all six, every preceding date inside the captured June 30–October 2 window
has zero volume. Those rows remain intact. The repair changes the factor from
the event date forward, restoring the relationship between preceding suspended
prices and resumed trading. This also prevents the first trading day's close
from absorbing that day's genuine movement into an adjustment. For 175250 the
previous source had no factor transition at resumption.

The overlay is `before_factor × prior_close / reference / old_event_factor`.
Nine rules guard exact old factors, share counts, dates and row counts. Later
relative factor transitions remain unchanged. Six primary bodies and twelve
provider responses are hash-pinned; the wider 32-document corpus remains
available in `kr_suspended_references_20261007`.

## Verification

- Independent 60-digit Decimal verification covers all **5,360,785 rows** and
  the exact schema. Reference boundaries agree within `1.075e-12` in source
  price units. All raw and unaffected fields are exact.
- The six histories cover **390 dates**, **1,137 comparable OHLC cells** and
  **423 preserved nontrading zero-OHL cells**.
- **50 tests passed**, including source-hash rejection, quote arithmetic,
  cross-source disagreement and empty integer-precision interval handling.
- Actual repeated normalization returns `REUSED`. Eleven panel, receipt and
  full-cohort artifacts keep identical hashes, byte sizes and modification times;
  no network calls are made.
- Original study code, six frozen model files and the live KR producer remain
  unchanged. No strategy touch rates or returns were calculated.

| Artifact | SHA-256 |
| --- | --- |
| Parent v6 panel | `1e39df38d4d21e5262f0513e4be8dd3f76133ae39004a59c63a5653a337de472` |
| New v7 panel | `2dca1f0b55a5614a8e6faa076e881d435955775061df6ed8d098622bba36c73a` |
| Full-panel verifier | `c75f8b816705763d3e130f0145973bf53a4b8f64da2db4dd593222f97ded8f74` |
| Full-cohort verifier | `70515d6bd915b90f8d87475ac901dbf90158bcfbafa74b1f69df6666a5888250` |

## Entire fixed cohort after correction

The reusable comparator first reproduces the old v6 results exactly: all five
Parquet tables, interval results and summary match the fixed 1,310-code audit.
It then compares v7 with the same **2,620 provider responses / 85,104 dates**.
The independent verifier uses rational arithmetic rather than importing the
comparison implementation.

- All **510,624 raw cells** preserve the prior result: close, volume and amount
  agree exactly; the same 4,182 nontrading zero-OHL conventions remain explicit.
- Across **336,234 comparable adjusted cells**, the largest residual falls from
  about **2,080 KRW to 1.000000000000552 KRW**. No former large contradiction
  remains. This numerical bound is not a certification threshold.
- **2,996 cells / 32 codes** still differ above `0.000001` KRW: 2,842 on traded
  dates and 154 nontrading closes. Integer precision and floating storage remain
  visible instead of being silently rounded away.
- A common coefficient followed by truncation is compatible with all cells for
  **1,296 codes**. Code 199800 has coincident closed bounds but an empty half-open
  interval. Thirteen others have empty intervals with relative gaps no larger
  than `3.479e-16`. None is promoted to an exact provider-match claim.

Audit directories in the production checkout:
`runtime_state/audit/kr_verified_events_v7_20261007/`,
`runtime_state/audit/kr_v7_full_cohort_20261007/`, and
`runtime_state/audit/kr_corrected_cohort_v6_parity_20261007/`.

## Remaining requirements

This completes the six scoped repairs and removes the observed large Q3 basis
contradictions. It does **not** certify earlier training/feature histories,
historical publication times, share and cash entitlements, or strategy returns.
The source and publication flags remain false. Before a new study epoch uses the
panel, earlier lookbacks and corporate-action execution/valuation must be audited.
The parent study and live lane are not replaced; weekly cadence and H10 +5% touch
qualification still require their own valid evidence.
