# Eight additional KR issuance corrections — 2026-10-07

A separate v3 research source removes eight officially unsupported holder-price
adjustments. Exactly **338 of 5,360,785 rows** change, limited to `adj_factor` and
four adjusted OHLC fields. Full independent verification preserves every raw
field and all other 5,360,447 rows, including metadata. This is partial source
normalization, not source certification, model qualification or live promotion.
Tracking: `swing-main-bp1b`; broader source reconciliation: `swing-main-5pfa`.

## Official economics and exact scope

Seven events incorrectly treated non-pro-rata new shares as an entitlement of
existing shareholders. The heuristic even assigned the factors before the
actual listing dates. A mixed event multiplied by total outstanding-share growth
instead of the documented 5-for-1 split. The following primary KIND documents
were captured in the [fixed remaining-code corpus](KR_REMAINING_ACTION_CORPUS_2026-10-07.md).

| Code | Official event and listing date | Incorrect start | Corrected rows |
| --- | --- | --- | ---: |
| [002680](https://kind.krx.co.kr/external/2026/09/18/000390/20260918000902/70791.htm) | Third-party 1,292,671 shares; September 21 | August 18 | 32 |
| [069920](https://kind.krx.co.kr/external/2026/07/31/001241/20260731002370/70791.htm) | Third-party 5,004,170 shares; August 3 | July 22 | 50 |
| [123010](https://kind.krx.co.kr/external/2026/08/07/000830/20260807001698/70791.htm) | Third-party 2,816,900 shares; August 10 | July 29 | 45 |
| [138360](https://kind.krx.co.kr/external/2026/07/16/000945/20260716002150/70791.htm) | Third-party 13,513,514 shares; July 20 | July 14 | 55 |
| [225430](https://kind.krx.co.kr/external/2026/08/06/000605/20260806001468/70791.htm) | Third-party 908,265 shares; August 7 | July 8 | 59 |
| [314130](https://kind.krx.co.kr/external/2026/08/05/000500/20260805001385/70791.htm) | Preferred-to-common conversion, 6,900,732 shares; August 10 | July 29 | 45 |
| [900270](https://kind.krx.co.kr/external/2026/09/22/000424/20260922001080/70791.htm) | Third-party 1,749,353 shares; September 23 | August 31 | 23 |
| [276730](https://kind.krx.co.kr/external/2026/08/20/000557/20260820001314/70764.htm) | Par value KRW 500 → 100; August 21 | August 21 | 29 |

For 276730 the separately captured corrected CB/BW/third-party listing notices
explicitly state that their counts precede the split. The full reconciliation is:

`(2,371,816 + 252,657 + 680,734 + 3,626 + 1,206,647) × 5 = 22,577,400`.

The prior builder used `22,577,400 / 2,371,816 = 9.519035…` as holder entitlement.
The verified split factor is 5; CB/BW exercise and third-party allotment shares
belong to their recipients. The repair retains the pre-event constant basis and
multiplies it by 5. For the other seven, it retains the prior basis without the
non-pro-rata increase. Existing earlier split factors are preserved, including
small rounding differences; this patch does not silently certify or rewrite them.

All corrections run from the erroneous heuristic date through October 2. The
24 exact rules split on observed outstanding-share transitions and require exact
old factors, share counts and per-rule row counts. For 314130 and 900270, the
share count at the erroneous start predates another intermediate listing; the
rules guard those actual intermediate counts instead of assuming the eventual
trigger count was already in effect.

## Actual verification

Audit: `runtime_state/audit/kr_verified_events_v3_20261007/` in production.
`prepare.py` freezes 31 original body resources, economic evidence, source hashes
and exact rules before building. The wrapper verifies **all** supporting bodies,
including the split-day issuance revisions, not just each rule's primary body.
It reuses the hash-pinned v2 streaming builder and original correction helper.

- Independent full-panel comparison: all 5,360,785 rows checked; exactly 338 rows
  and five adjusted fields corrected; all raw fields and 5,360,447 unaffected
  rows exactly preserved; schema and metadata exact.
- All eight fixed June 30–October 2 histories: **520 dates**, **1,861 comparable
  OHLC cells**, plus **219 preserved nontrading zero-OHL cells**. KIS carries its
  adjusted close into adjusted OHL on those nontrading days; it must not be
  confused with the unadjusted close before a split.
- Within corrected periods, **1,316 comparable OHLC cells** agree with KIS after
  removing the retained constant basis; largest floating-point error is less
  than `6.2e-13` KRW. Independent nominal and adjusted KIS payloads also agree on
  every comparable cell in these corrected periods.
- Whole-window residuals remain visible: approximately 2 KRW for 123010 and
  276730 before their corrected periods, and smaller share-rounding differences
  for 002680 and 900270. These are not waived by a tolerance-based certificate.
- The original parent study source and code, six fitted model hashes and live KR
  producer hash remain unchanged. No H10 outcomes or test returns were computed.
- **16 tests passed** across v3 evidence tampering, the streaming issuance builder
  and original correction helper. Actual second execution returned `REUSED`;
  panel, manifest and receipt hashes, sizes and modification times were exact.

| Artifact | SHA-256 |
| --- | --- |
| Parent v2 panel | `1d92de63695c20af4170dd107493ff85e1cf50b331303b2580c767c3a26894da` |
| New v3 panel | `31db990498de17a29b626a7da52fadf6bae36b7434a092f457bdfc4058c6af70` |
| Independent verifier | `34d621d568b60c5855257ff6a19251761f3618d6b8d5d954fd6d0aab5727b518` |

The three separate source versions now contain **13 supported event corrections
and 457 cumulatively changed rows**. This does not mean 13 complete security
histories are certified. The other 52 original mismatch codes, residual split
and provider conventions on these eight, earlier feature lookbacks, final H10
labels and strategy qualification remain unresolved. `source_certified` and
`publication_allowed` remain false; live cache, parent models, scores, universe
and issued contracts are not replaced.
