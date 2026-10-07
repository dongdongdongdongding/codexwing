# Aerospace's omitted auction and numeric residual diagnostics

Issue `swing-main-7bar`, with remaining whole-source work in `swing-main-01n3`.
The fixed historical comparison isolated a large 012450 discrepancy before
September 27, 2024. Its source factor remained one across the resumption.

The [KRX method notice](https://kind.krx.co.kr/external/2024/09/26/000330/20240926000924/99332.htm)
specifies an opening auction within 145,000–580,000. The evaluated price is
290,000; the actual auction reference is **300,000**, independently given by
nominal open and 317,000 close minus 17,000 signed change, with positive volume.
The [final listing notice](https://kind.krx.co.kr/external/2024/09/24/000043/20240924000088/68155.htm)
identifies A012450 / KR7012450003 and the change from 50,630,000 to 45,581,161
surviving shares. The fixed August–October window contains 54 disclosures,
eight selected documents and 30 HTTP captures. Both method and final listing
receipts and bodies are pinned and checked.

V11 applies the missing **29/30** multiplier from September 27, preserving the
separate 2025 rights correction in v10. It changes 489 rows through four rules.
Independent 70-digit calculation and full comparison of all 5,360,785 rows
verify exact schema/raw fields and all-column equality for the other 5,360,296
rows. Only adjustment factor and adjusted OHLC change.

The same fixed 1,353-code / 872,671-date comparison was repeated. All four
tables are exact for the other 1,352 codes; entire nominal and provider-basis
tables remain exact. The Aerospace maximum comparable difference falls from
11,205.058824 to **1.046653 KRW**, with cells above one KRW falling from 706 to
20. The residual diagnostic is retained; it is not declared zero or waived.
The overall queue remains 213 codes above one KRW plus three unavailable
anchorless comparisons. Nontraded zero-OHL representations remain separately
recorded; nontraded close values are included in comparable diagnostics.

65 related tests passed. Actual capture/verifier/normalizer/rounding replay made
zero network calls and preserved 101 existing files' bytes, sizes and modification
times. This is a separate immutable source, with no live-consumer switch and no
strategy outcome calculation. The surviving-security adjustment does not
establish total wealth: new-company shares, fractional payments and actual account
availability remain outside this price correction.

## Testing the small residuals without changing tolerances

Three already corrected securities retain roughly one-KRW discrepancies.
The numeric audit fixes their complete comparable pre-event price scope and
validates the original receipt index, supporting hashes and adjusted responses.
It tests a six-decimal coefficient derived from the official reference ratio.

| Code | Six-decimal coefficient | Pre-event cells | Exact decimal truncation mismatches | Float32 multiplication mismatches | Post-event nominal matches |
| --- | ---: | ---: | ---: | ---: | ---: |
| 000880 | 1.200477 | 2,557 | 15 | 0 | 108 |
| 006400 | 0.979033 | 1,272 | 18 | 0 | 1,444 |
| 000500 | 0.555685 | 2,450 | 1 | 0 | 260 |

The successful candidate calculation is:
`int(float32(nominal_price) * float32(six_decimal_coefficient))`.
For example, 527,000 × 0.555685 is 292,845.995 in exact decimal arithmetic,
but the float32 product rounds to 292,846 before integer truncation, matching
the previously unresolved Gaon Cable example. A second implementation using
`struct` IEEE-754 single-precision packing, integer-derived coefficients and
the pinned original receipts independently reproduces **all 6,279 pre-event
cells**. All 1,812 post-event cells equal nominal prices exactly.

The exact-real-number truncation intervals are empty for Samsung SDI and Gaon
Cable, even though the float32 calculation matches every scoped cell. Hanwha's
real-number interval is nonempty. This is evidence compatible with a numeric
representation effect, not proof of the provider's undocumented implementation,
a universal rounding contract, an altered acceptance threshold, or whole-source
certification. No price was replaced with the provider's rounded values.
The initial exact-decimal-only result and its implementation remain preserved;
the extended hypothesis has its own v2 evidence directory. Aerospace's separate
20-cell residual is not included in this three-code hypothesis test.

Production evidence under `runtime_state/audit/`:

- `aerospace_split_documents_20261008/`
- `aerospace_split_evidence_20261008/`
- `kr_verified_events_v11_20261008/`
- `lowliq_history_indexed_comparison_v11_20261008/`
- `aerospace_split_replay_20261008.json`
- `reference_coefficient_rounding_20261008/` (preserved initial hypothesis)
- `reference_coefficient_rounding_v2_20261008/` (extended hypothesis and independent check)

Auction proof SHA: `31d8267d88203bdacfe424b8f23a8735c3d4e84778189a80636684dc08007c63`.
V11 panel SHA: `4d2c43d653140c39daed2f38f1f0c302f95ba16d84d75c9ad7f3162d56414256`.
Whole-source, point-in-time, portfolio-return and publication certificates remain
false; the requested H10/TP5 lane is not qualified by this work.
