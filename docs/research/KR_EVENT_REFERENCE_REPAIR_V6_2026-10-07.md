# Quote-reference event repair v6 — 2026-10-07

The separate v6 research panel corrects **10 events / 341 rows** using observed
reference prices. The independent full-panel verifier checks all **5,360,785
rows**, preserves every raw field and the other **5,360,444 rows**, and confirms
the exact schema. A second comparison directly against the original panel finds
the cumulative union: **63 securities / 2,040 distinct rows**. Epoch counts must
not be summed because earlier repairs overlap. Tracking: `swing-main-s4m7`;
broader source certification remains `swing-main-5pfa`.

## Evidence and scope

For each event, `nominal close − signed daily change` in the frozen KIS response
equals both KIS nominal open and the independent marcap nominal open. Volume is
positive and closes agree. Thus the reference is corroborated without assuming
the notice's evaluated price or the event day's closing price is the reference.

| Security | Event date | Previous nominal close | Observed reference | Evaluated price in method notice | Changed rows |
| --- | --- | ---: | ---: | ---: | ---: |
| 00088K | 2026-08-25 | 29,250 | 29,450 | 29,250 | 27 |
| 002630 | 2026-09-22 | 913 | 1,936 | 1,826 | 7 |
| 004870 | 2026-07-24 | 247 | 1,175 | 1,235 | 48 |
| 006490 | 2026-09-10 | 898 | 1,416 | 1,496 | 15 |
| 083660 | 2026-08-04 | 230 | 3,400 | — | 41 |
| 101000 | 2026-08-18 | 311 | 851 | — | 32 |
| 148780 | 2026-08-04 | 457 | 2,300 | — | 41 |
| 348080 | 2026-07-22 | 309 | 2,700 | — | 50 |
| 354200 | 2026-07-13 | 737 | 2,150 | — | 56 |
| 417310 | 2026-08-28 | 10,930 | 2,290 | 2,030 | 24 |

The five KOSPI method notices explicitly make the initial auction price the
reference, with observed references inside the published bounds. For example,
[417310's notice](https://kind.krx.co.kr/external/2026/08/27/000392/20260827000870/99345.htm)
specifies that method. Its old heuristic used the event close 2,335; the actual
quote reference is 2,290. For 00088K the issuer notice and separate listing
notice jointly identify the exact third preferred class, ISIN KR700088K015 and
short code A00088K. Common shares are not substituted.

The five KOSDAQ notices establish the exact security, capital reduction and
changed-listing date. They **do not themselves spell out the auction method**.
Their reference prices are inferred from the quote arithmetic and independently
corroborated raw open, not presented as fixed prices printed in those notices.
All 13 supporting body resources and their extracted text hashes are verified;
the audit also pins all 24 nominal/adjusted KIS responses for the 12-code scope.
The evidence preserves original URLs and captures.

## Later events remain outside the source

050110 and 131400 have official October 7 events, after the frozen October 2
source endpoint. Neither receives an overlay. Across all **260 provider OHLC
cells per security**, each full captured history is compatible with one constant
coefficient followed by integer truncation:

- 050110: `[5.00463392029657, 5.004638218923934)` approximately.
- 131400: `[11.09660842754368, 11.09661835748792)` approximately.

These intervals are diagnostic compatibility bounds, not inferred exact
corporate-action factors. They identify a later provider adjustment scale and
integer precision as a viable explanation of the observed residuals. Inserting
the October 7 event into an October 2 as-of panel would be incorrect. No complete
history or provider implementation certificate follows from interval overlap.

## Guarded application and verification

The overlay is `before_factor × prior_close / reference / old_event_factor`.
It multiplies each subsequent factor and therefore retains relative transitions
from other events, including 083660's later split and 354200's later rights event.
Fourteen rules guard exact old factors, share counts, dates and row counts.
The parent v5 panel is immutable. Entry checks pin the builder, correction helper,
quote verifier, overlay helper, evidence verifier, economics and all source inputs.

- **32 tests passed**, including signed price-change direction, rejection of
  evaluated-price substitution, no trading volume and cross-source disagreements.
- Independent verification reparses the primary notices and calculates factors
  with 60-digit Decimal arithmetic; it does not import the normalizer.
- Ten reference boundaries agree within `2.835e-12` in source price units.
- All post-event relative factors are retained within float storage precision.
- The 650 observed dates contain **2,123 comparable OHLC cells** and **477
  preserved nontrading zero-OHL cells**. After correction each history agrees
  with the provider within one KRW plus float precision. This bound is a
  diagnostic, not permission to call the source exact or certified.
- Actual repeat returns `REUSED`: all six audit/panel/manifest/receipt files keep
  identical hashes, sizes and modification times, with zero network requests.
- Original study code, six frozen model artifacts and the live KR producer keep
  their hashes. No strategy touch rates or returns were computed.

| Artifact | SHA-256 |
| --- | --- |
| Parent v5 panel | `85bf1a928bdf9a9dd356a97d6dae9df8235cde49fdea3ef9ecd030cd38dcc122` |
| New v6 panel | `1e39df38d4d21e5262f0513e4be8dd3f76133ae39004a59c63a5653a337de472` |
| Independent verifier | `29b181a08ba461edceec1750e0d456a6d7f953ee3f559bba93ea241f827a19aa` |

Audit directories: `runtime_state/audit/kr_event_reference_basis_20261007/` and
`runtime_state/audit/kr_verified_events_v6_20261007/` in the production checkout.
Code: `research/audit_kr_event_reference.py` and
`research/normalize_kr_event_reference.py`.

## Qualification remains open

All original 65 mismatch codes now have either scoped event corrections (63)
or an explicit later-event/constant-scale diagnosis (2). This does **not** prove
that all their earlier histories, all other symbols, or every integer adjusted
price is correct. The full fixed-universe comparison must be repeated against
v6, earlier feature lookbacks must be verified, and the execution/valuation
contract must handle actual cash and share entitlements. An auction-continuous
feature price is not shareholder wealth across a capital reduction or spin-off.
The source, portfolio-return and publication certificates remain false. A new
qualified study epoch and mature H10 outcomes are still required before replacing
the live lane.
