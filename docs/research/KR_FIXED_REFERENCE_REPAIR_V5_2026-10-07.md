# Fixed-reference event overlays v5 — 2026-10-07

The separate v5 research source reconciles 30 in-window fixed-price par-change
notices: **29 require updates, one already matches**. Exactly **737 rows** change
in `adj_factor` and adjusted OHLC. Independent full-panel comparison preserves
all raw fields and the other **5,360,048 of 5,360,785 rows**, with exact schema.
Tracking: `swing-main-mvmh`; broader source review: `swing-main-5pfa`.

## Fixed published references, not auction estimates

The frozen scope comprises 34 captured fixed-price notices: the 30 below, two
outside the June 30–October 2 source window (002630 June 9, 050110 October 7),
and two other preferred classes of 002780 that are not the audited common share.
All four out-of-scope records remain explicit in the evidence. Separate notices
whose evaluated prices precede an auction are not treated as fixed references.

| Code / official notice | Effective date | Prior close KRW | Fixed reference KRW | Changed rows |
| --- | --- | ---: | ---: | ---: |
| [002680](https://kind.krx.co.kr/external/2026/07/09/000503/20260709001274/70795.htm) | 2026-07-10 | 374 | 1870 | 57 |
| [002780](https://kind.krx.co.kr/external/2026/09/04/000385/20260904001093/99321.htm) | 2026-09-07 | 782 | 7820 | 18 |
| [006490](https://kind.krx.co.kr/external/2026/07/15/000522/20260715001469/99321.htm) | 2026-07-16 | 310 | 1550 | 53 |
| [009620](https://kind.krx.co.kr/external/2026/09/16/000562/20260916001306/70795.htm) | 2026-09-17 | 870 | 4350 | 10 |
| [012170](https://kind.krx.co.kr/external/2026/08/27/000395/20260827001198/99321.htm) | 2026-08-28 | 748 | 3740 | 24 |
| [018470](https://kind.krx.co.kr/external/2026/09/10/000357/20260910000995/99321.htm) | 2026-09-11 | 973 | 4865 | 14 |
| [033170](https://kind.krx.co.kr/external/2026/08/25/000598/20260825001414/70795.htm) | 2026-08-26 | 340 | 1700 | 26 |
| [034940](https://kind.krx.co.kr/external/2026/08/26/000573/20260826001464/70795.htm) | 2026-08-27 | 550 | 2750 | 25 |
| [043200](https://kind.krx.co.kr/external/2026/08/26/000572/20260826001467/70795.htm) | 2026-08-27 | 512 | 1024 | 25 |
| [051980](https://kind.krx.co.kr/external/2026/10/01/000574/20261001001356/70795.htm) | 2026-10-02 | 1035 | 10350 | 1 |
| [054940](https://kind.krx.co.kr/external/2026/08/11/000756/20260811001296/70795.htm) | 2026-08-12 | 760 | 3800 | 35 |
| [062970](https://kind.krx.co.kr/external/2026/08/06/000649/20260806001411/70795.htm) | 2026-08-07 | 1162 | 2325 | 38 |
| [067390](https://kind.krx.co.kr/external/2026/08/27/000542/20260827001325/70795.htm) | 2026-08-28 | 506 | 5060 | 24 |
| [082850](https://kind.krx.co.kr/external/2026/09/04/000702/20260904001724/70795.htm) | 2026-09-07 | 897 | 4485 | 18 |
| [083660](https://kind.krx.co.kr/external/2026/08/25/000555/20260825001125/70795.htm) | 2026-08-26 | 2860 | 1430 | 0 |
| [084680](https://kind.krx.co.kr/external/2026/10/01/000399/20261001001038/99321.htm) | 2026-10-02 | 532 | 2660 | 1 |
| [091810](https://kind.krx.co.kr/external/2026/08/28/000484/20260828001188/99321.htm) | 2026-08-31 | 626 | 3130 | 23 |
| [105550](https://kind.krx.co.kr/external/2026/08/11/000752/20260811001298/70795.htm) | 2026-08-12 | 397 | 1985 | 35 |
| [113810](https://kind.krx.co.kr/external/2026/07/27/000715/20260727001284/70795.htm) | 2026-07-28 | 465 | 2325 | 46 |
| [123010](https://kind.krx.co.kr/external/2026/07/24/000827/20260724001573/70795.htm) | 2026-07-27 | 1554 | 3110 | 47 |
| [204840](https://kind.krx.co.kr/external/2026/08/10/000821/20260810001572/70795.htm) | 2026-08-11 | 814 | 4070 | 36 |
| [207760](https://kind.krx.co.kr/external/2026/09/01/000607/20260901001340/70795.htm) | 2026-09-02 | 384 | 1920 | 21 |
| [214680](https://kind.krx.co.kr/external/2026/09/09/000583/20260909001496/70795.htm) | 2026-09-10 | 960 | 4800 | 15 |
| [239340](https://kind.krx.co.kr/external/2026/09/18/000643/20260918000899/70795.htm) | 2026-09-21 | 504 | 2520 | 8 |
| [276730](https://kind.krx.co.kr/external/2026/08/20/000637/20260820001226/70795.htm) | 2026-08-21 | 11470 | 2295 | 29 |
| [285800](https://kind.krx.co.kr/external/2026/09/10/000536/20260910001209/70795.htm) | 2026-09-11 | 733 | 3665 | 14 |
| [291230](https://kind.krx.co.kr/external/2026/08/13/001091/20260813002862/70795.htm) | 2026-08-14 | 588 | 2940 | 33 |
| [300120](https://kind.krx.co.kr/external/2026/08/19/000470/20260819001130/70795.htm) | 2026-08-20 | 491 | 2455 | 30 |
| [378800](https://kind.krx.co.kr/external/2026/09/28/000617/20260928001315/70795.htm) | 2026-09-29 | 510 | 2550 | 4 |
| [900270](https://kind.krx.co.kr/external/2026/08/24/000606/20260824001463/70795.htm) | 2026-08-25 | 420 | 2100 | 27 |

083660's August 26 event already has the required factor 2 and gets no write.
This does not certify its preceding capital reduction. Other changes include
rounded total-share fractions and tick-adjusted references. For example:

- 123010: prior close 1,554 and reference 3,110 give a forward price factor
  `1554/3110`, rather than exactly 0.5.
- 062970: prior close 1,162 and reference 2,325 similarly differ from 0.5.
- 276730: the previously verified shareholder split is 5-for-1; its official
  price reference 2,295 against prior close 11,470 gives `11470/2295`. The v3
  non-pro-rata issuance correction is retained, with the price convention now
  refined separately from shareholder quantities.
- 291230: the published fixed reference 2,940 against prior close 588 gives 0.2;
  the heuristic had used approximately 0.21459854. The fixed price is supported
  by the official notice even though that date also has merger/capital changes.

## Preserve unrelated later changes

The overlay is `before_factor × prior_close / reference / old_event_factor`.
Each affected source factor is multiplied by that exact rational overlay, with
conversion to float only at the final step. This replaces the covered event
multiplier without flattening subsequent unrelated changes. The 37 rules guard
exact old factor, share count, dates and per-rule row count.

For 006490 the July 16 fixed-price consolidation is corrected; the September 10
capital-reduction multiplier remains proportional to the original. Independent
comparison bounds the relative-factor difference at about `5.01e-17` from float
storage. The later capital reduction remains **uncertified**.

## Verification and remaining differences

Audit: `runtime_state/audit/kr_verified_events_v5_20261007/`.

- All 34 primary body resources and their extracted text hashes are verified.
  Independent verification reparses the references, dates and security classes
  directly from those bodies and obtains before/after factors from the parent.
- Every panel row is checked against a separate Decimal implementation. Exactly
  737 rows change, with all raw and unaffected fields preserved. All 30 official
  reference boundaries connect to the prior adjusted close; maximum numerical
  discrepancy is `2.052e-13` in source price units.
- Across all 30 histories: **1,950 dates, 6,339 comparable OHLC cells and 1,461
  preserved nontrading zero-OHL cells**. Full-window provider differences remain
  explicit. The large residuals are 006490's separate capital reduction (about
  KRW 139.33) and 083660's earlier reduction (about KRW 36.00). Other histories
  are within one KRW plus floating-point precision in this captured window;
  this is not an exact provider or complete-history certificate.
- A second full-panel comparison directly against the original frozen source
  verifies the cumulative union: **55 codes / 1,765 distinct rows** differ,
  with every original raw field still exact. Epoch row totals were not added
  blindly because four codes overlap earlier repairs.
- Original study code, six frozen model files and the live KR producer retain
  their hashes. No test touch rates, returns or H10 outcomes were computed.
- **22 tests passed**. Actual repeated build returned `REUSED`, preserving panel,
  manifest and receipt hashes, byte lengths and modification times.

| Artifact | SHA-256 |
| --- | --- |
| Parent v4 panel | `78a8d8c296d90484da62fd3dd4cff20079e07e794dad863dcd1f35d9f7848482` |
| New v5 panel | `85bf1a928bdf9a9dd356a97d6dae9df8235cde49fdea3ef9ecd030cd38dcc122` |
| Independent verifier | `6a0fe51005d672ff30bedff2ee5f0a4d2aba062f96763afa02bae66ae634e0dd` |

The original mismatch codes with no normalization yet are 00088K, 002630,
004870, 050110, 083660, 101000, 131400, 148780, 348080 and 417310. Residual actions
on previously corrected codes (including 006490 and 354200), earlier histories
and event-spanning execution/valuation also remain unresolved. This is a partial
research source; source, portfolio-return and publication certificates remain
false. Live cache, parent study, models, universe and issued picks are preserved.
