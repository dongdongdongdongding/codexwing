# DS Dansuk historical price-reference corrections

Issue `swing-main-iykk`, within `swing-main-01n3`. The fixed historical
comparison identified 017860 independently of strategy outcomes. Two official
reference-price events explain its large adjusted-price discrepancy.

| Ex-date | Previous nominal close | Official reference | Correction |
| --- | ---: | ---: | --- |
| 2024-11-25 | 128,800 | 42,950 | Replace the erroneous close-based factor 128800/55800 with 128800/42950 |
| 2025-12-29 | 18,600 | 18,420 | Add the missing factor 18600/18420 |

The first reference is explicitly fixed in the [KRX bonus-ex notice](https://kind.krx.co.kr/external/2024/11/22/000304/20241122000873/99301.htm).
The second is explicitly fixed in the [KRX stock-dividend-ex notice](https://kind.krx.co.kr/external/2025/12/26/000708/20251226002084/99311.htm).
Captured nominal quotes independently imply the same references from close minus
signed price change. The bonus share ratio is three total shares per old share,
but the official rounded reference does not imply an exact price factor of three.

The capture fixes two full disclosure windows, October–December 2024 and
November 2025–January 2026. It preserves 29 HTTP receipts, including decisions,
reference notices and the final December 24, 2024 bonus additional-listing notice.
The verifier pins six document receipts and their bodies, nominal quote receipts,
the existing comparison index, source and implementation dependencies. Changed
identities, dates, classes, references or existing source factors abort.

The v9 panel changes 451 rows through five interval rules. An independent full
comparison of all 5,360,785 rows confirms identical schema and raw fields, and
all-column equality for the other 5,360,334 rows. Only adjusted OHLC and adjustment
factor change. Independent 70-digit arithmetic gives factors
2.9988358556461003 after the bonus event and 3.028140440554694 after the dividend.

The same frozen 1,048-code / 670,165-date historical cohort was rerun against v9.
DS Dansuk's maximum difference falls from 50,982.7577639752 to
0.967741935486 KRW. Its 1,952 cells previously above one KRW become zero;
1,904 smaller differences remain. All four comparison tables are exactly unchanged
for the other 1,047 codes, and the entire nominal and provider-basis tables are
unchanged. There remain **157 codes** with comparable differences above one KRW.
The existing one-KRW diagnostic is unchanged and is not a source certificate.

39 related tests passed. Actual capture, verifier and normalizer replay made zero
network requests and preserved the bytes, sizes and modification times of all
96 existing evidence/source files. Full-source independent verification and
fixed-cohort parity evidence are retained alongside the outputs.

The bonus listing occurs 29 calendar days after ex-date; instrument trading does
not establish unrestricted account credit. The later stock-dividend and cash
dividend decisions remain proposals subject to shareholder approval and
fractional-share terms. No payment or actual account availability is certified.
Consequently these are price-reference corrections only: portfolio-return,
point-in-time, whole-source and publication certification remain false. Live
consumers and the original frozen study inputs are unchanged; no strategy
outcomes were calculated. These corrections cannot by themselves qualify or
replace the requested H10/TP5 lane.

Production audit directories:

- `runtime_state/audit/ds_reference_documents_20261007/`
- `runtime_state/audit/ds_price_reference_evidence_20261007/`
- `runtime_state/audit/kr_verified_events_v9_20261007/`
- `runtime_state/audit/lowliq_history_indexed_comparison_v9_20261007/`

Verification SHA: `aca28caf35691a58dd2149c24abcefae3fad887b058e8416359e0ac94f14b347`.
V9 panel SHA: `f9360da33359799941f906f68a2aba172e9d456c7494edec687ec173a1ba0979`.
The v8 parent and original 158-code review queue remain preserved; the v9 queue
records the remaining 157 codes without changing the research universe.
