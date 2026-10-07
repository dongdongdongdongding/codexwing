# Six historical rights and auction reference corrections

Issue `swing-main-7bar`, within `swing-main-01n3`. Six securities from the fixed
v9 historical discrepancy queue were investigated using official exchange
documents and previously captured nominal quotes, without strategy outcomes.

| Code | Event date | Previous close | Verified reference | Event close | Method |
| --- | --- | ---: | ---: | ---: | --- |
| 000880 Hanwha | 2026-08-25 | 83,800 | 100,600 | 118,100 | Resumption auction |
| 012450 Hanwha Aerospace | 2025-05-22 | 850,000 | 837,000 | 833,000 | Fixed ex-rights |
| 011790 SKC | 2026-04-06 | 94,900 | 89,200 | 89,900 | Fixed ex-rights |
| 003670 POSCO Future M | 2025-06-16 | 127,100 | 123,200 | 118,500 | Fixed ex-rights |
| 006400 Samsung SDI | 2025-04-10 | 171,700 | 168,100 | 177,200 | Fixed ex-rights |
| 006405 Samsung SDI preferred | 2025-04-10 | 99,400 | 95,800 | 103,600 | Fixed ex-rights |

Hanwha's [official method notice](https://kind.krx.co.kr/external/2026/08/24/000446/20260824001208/99332.htm)
specifies an auction within 41,900–167,600. Its 83,800 evaluated price is not the
actual auction reference. Nominal open and signed close-change independently
give 100,600, with positive volume. The source had used 83,800/118,100, incorrectly
absorbing the day's return; the corrected factor is 83,800/100,600. The final
split-listing notice independently identifies 000880 and its share-count change
from 70,507,919 to 53,328,897.

The other five events have explicit fixed references and missing source factors.
Each official class-specific reference matches close minus signed price change.
Samsung SDI common and preferred notices are checked separately. The verifier
rejects changed receipt hashes, wrong identities/classes/dates, changed source
factors, quote disagreement, zero-volume auction evidence and substituted
evaluated prices.

The fixed five-company disclosure windows contain 718 records, 79 selected
documents and 146 body resources, captured in 351 HTTP requests. All five
windows completed. The immutable corpus includes decisions, amendments, rights
and additional-listing disclosures; capturing a document does not certify every
economic entitlement described in it.

V10 corrects **1,524 rows through ten rules**: Hanwha 27, POSCO Future M 319,
Samsung SDI 361, Samsung SDI preferred 361, SKC 122 and Hanwha Aerospace 334.
Independent full comparison of 5,360,785 rows confirms exact schema and raw
fields, and exact all-column equality for the other 5,359,261 rows. Independent
70-digit calculations verify all six adjusted factors and OHLC values.

56 related tests passed. Actual capture/verifier/normalizer replay made zero
network requests and preserved bytes, sizes and modification times of 1,067
evidence and source files. The output is a separate immutable panel; original
study inputs and live consumers remain unchanged.

The expanded historical snapshot fixes 30,936 receipts, explicitly resolving the
previously reviewed 004310 supplement while preserving its failed original.
It covers 1,353 complete usable codes / 872,671 dates, with 34,860 requests still
unvisited. All four tables retain exactly the previous 1,048 codes' values.
The new anchorless codes 058530, 066410 and 068940 have respectively 18, 679 and
679 scoped dates, all with zero volume and amount. Their adjusted comparisons
are unavailable, not clean. Null adjusted-cell counts widen the summary column
from integer to float without changing earlier values. V9 has 216 codes above
the unchanged one-KRW diagnostic, including 59 newly captured codes; this
expanded count does not imply regression in the earlier cohort.

The full fixed 1,353-code comparison against v10 preserves all four comparison
tables exactly for the other 1,347 codes. Entire nominal and provider-basis
tables are unchanged. Comparable maximum differences are:

| Code | V9 maximum, KRW | V10 maximum, KRW | Remaining comparable cells above 1 KRW |
| --- | ---: | ---: | ---: |
| 000880 | 34,749.831 | 1.028640 | 45 |
| 003670 | 11,722.000 | 0.933910 | 0 |
| 006400 | 10,369.000 | 1.071637 | 64 |
| 006405 | 10,105.000 | 0.947686 | 0 |
| 011790 | 12,013.000 | 0.973656 | 0 |
| 012450 | 13,750.000 | 11,205.059 | 706 |

The 012450 residual is confined to December 2023–September 2024 in the captured
scope and requires separate earlier-event investigation. The small 000880 and
006400 residuals also remain unresolved; no rounding assumption or relaxed
tolerance certifies them. There are **213 codes** still above the one-KRW
diagnostic, plus the three unavailable anchorless comparisons. Zero-OHL
representation differences remain separately recorded and are excluded from the
comparable maxima above, while nontraded close differences remain included.
Issue 7bar remains open for these residual investigations.

Paid-right subscription cash, rights sales and actual availability are not
modeled. Hanwha's surviving-security price also omits assets transferred to the
new security. These corrections establish price-reference continuity only.
Whole-source, portfolio-return, point-in-time and publication certification
remain false. No strategy outcomes were computed and no H10/TP5 replacement was
qualified by this work.

Production evidence is under `runtime_state/audit/`:

- `large_gap_reference_documents_20261008/`
- `large_gap_reference_evidence_20261008/`
- `kr_verified_events_v10_20261008/`
- `large_gap_reference_replay_20261008.json`
- `lowliq_history_indexed_comparison_v9_20261008/`
- `lowliq_history_indexed_comparison_v10_20261008/`

Verification SHA: `c42df087f24548cdf3e8be0601a25d6d1f89c17a0036dbac886b09ec157f8397`.
V10 panel SHA: `86c7f56e91261f3d8c8c770aaa6b8a5e9079bfa221ef80525e7f490d73b6dd53`.
