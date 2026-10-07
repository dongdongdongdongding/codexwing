# Official ex-right reference and provider-basis audit — 2026-10-07

The fixed public corpus contains **18 ex-right notices for 17 securities**.
Six are bonus issues; twelve are paid rights issues. All 16 events inside the
captured provider window have the same adjustment percentage as the official
reference-price ratio rounded to two decimal places. This establishes a usable
price-reference mapping; it does not prove that a rounded percentage is an exact
historical-price factor, nor that price adjustments equal shareholder returns.
Tracking: `swing-main-o4bf`; guarded source construction: `swing-main-l02t`.

## Three distinct quantities

The exchange applies a special reference price when rights or par value change;
ordinary prior-close reference rules do not suffice. See the
[KRX explanation of reference prices](https://regulation.krx.co.kr/contents/RGL/03/03020201/RGL03020201.jsp).
Our price-continuity diagnostic uses `reference / prior nominal close` backward,
or its reciprocal forward. This is a declared price-basis convention, not a
claim about cash, subscription payments or the tradability of distributed shares.

The six captured board decisions separately specify new shares per existing
share: 002070=1, 220100=0.2, 240600=0.2, 340570=1, 475460=2, 494120=1.
For example, [340570's board decision](https://kind.krx.co.kr/external/2026/07/28/000376/20260728000888/11307.htm)
gives one new share per eligible share and excludes 185,880 treasury shares.
Its July/August price reference implies a 1.975903614… forward price factor,
while the shareholder quantity multiplier is 2. These must not be substituted
for each other. Likewise [240600's decision](https://kind.krx.co.kr/external/2026/07/13/000226/20260713000555/11307.htm)
specifies 0.2 new shares per eligible share, but the official reference implies
1.195704057… rather than a 1.2 price factor.

## Fixed event reconciliation

Provider source: the previously hash-pinned June 30–October 2 KIS nominal and
adjusted captures. Every security has 65 dates. Preferred 012205 retains its own
price history; the 012200 issuer notice is linked by explicit preferred name and
class, not by replacing preferred prices with common prices.

| Security / official notice | Ex-date | Kind | Reference KRW | Prior close KRW | KIS percentage |
| --- | --- | --- | ---: | ---: | ---: |
| [002070](https://kind.krx.co.kr/external/2026/07/30/000571/20260730001327/99301.htm) | 2026-07-31 | bonus | 3905 | 7800 | -49.94 |
| [012200](https://kind.krx.co.kr/external/2026/07/24/000771/20260724001612/99301.htm) | 2026-07-27 | rights | 4000 | 4230 | -5.44 |
| [012205](https://kind.krx.co.kr/external/2026/07/24/000769/20260724001614/99301.htm) | 2026-07-27 | rights | 6710 | 6940 | -3.31 |
| [042940](https://kind.krx.co.kr/external/2026/09/21/000481/20260921001112/70766.htm) | 2026-09-22 | rights | 5680 | 5900 | -3.73 |
| [047920](https://kind.krx.co.kr/external/2026/08/03/001008/20260803001597/70766.htm) | 2026-08-04 | rights | 7630 | 8280 | -7.85 |
| [061970](https://kind.krx.co.kr/external/2026/06/17/000525/20260617001478/70766.htm) | 2026-06-18 | rights | 5310 | outside window | unverified |
| [187660](https://kind.krx.co.kr/external/2026/06/26/001006/20260626001693/70766.htm) | 2026-06-29 | rights | 5090 | outside window | unverified |
| [199800](https://kind.krx.co.kr/external/2026/08/06/000650/20260806001531/70766.htm) | 2026-08-07 | rights | 38400 | 39000 | -1.54 |
| [210980](https://kind.krx.co.kr/external/2026/08/31/000534/20260831001279/99301.htm) | 2026-09-01 | rights | 2810 | 4130 | -31.96 |
| [220100](https://kind.krx.co.kr/external/2026/07/14/000770/20260714001642/70766.htm) | 2026-07-15 | rights | 8470 | 8750 | -3.20 |
| [220100](https://kind.krx.co.kr/external/2026/09/16/000563/20260916001356/70766.htm) | 2026-09-17 | bonus | 6750 | 8100 | -16.67 |
| [240600](https://kind.krx.co.kr/external/2026/07/28/000734/20260728001376/70766.htm) | 2026-07-29 | bonus | 2095 | 2505 | -16.37 |
| [255220](https://kind.krx.co.kr/external/2026/07/20/000747/20260720001283/70766.htm) | 2026-07-21 | rights | 1299 | 1388 | -6.41 |
| [321370](https://kind.krx.co.kr/external/2026/07/06/000837/20260706001760/70766.htm) | 2026-07-07 | rights | 1851 | 2040 | -9.26 |
| [340570](https://kind.krx.co.kr/external/2026/08/05/000756/20260805001709/70766.htm) | 2026-08-06 | bonus | 33200 | 65600 | -49.39 |
| [354200](https://kind.krx.co.kr/external/2026/07/20/000748/20260720001531/70766.htm) | 2026-07-21 | rights | 1404 | 1669 | -15.88 |
| [475460](https://kind.krx.co.kr/external/2026/09/15/000714/20260915001295/70766.htm) | 2026-09-16 | bonus | 2765 | 8290 | -66.65 |
| [494120](https://kind.krx.co.kr/external/2026/07/14/000771/20260714001244/70766.htm) | 2026-07-15 | bonus | 12780 | 25550 | -49.98 |

For each of the 16 comparable events, `(reference/prior_close − 1) × 100`,
rounded half-up to two decimals, equals KIS `prtt_rate`. Both June events remain
outside the captured provider window: their pre-event prices were not verified
by this audit. Their actual dates do show why a July price drop cannot itself
establish a new rights event. Future corrections require the corresponding
subscription/listing evidence and exact source guards.

## Whole-window checks and limits

The audit checks **1,105 security-dates and 4,420 OHLC values**, including provider
carried-close values on nontrading days; these are not executable fills. Two
explicit diagnostic hypotheses were evaluated using Decimal arithmetic:

- Multiply all later reported percentage coefficients, then truncate once:
  **4,142/4,420 exact**, 278 differences.
- Truncate after every later event: **4,130/4,420 exact**, 290 differences.

Neither reproduces the provider exactly. A separately implemented verifier uses
exact rational arithmetic, checks all saved cells against the original 34 source
payloads, and reproduces both counts without importing the audit implementation.

For each event-delimited segment it intersects the coefficient intervals implied
by `adjusted <= nominal × coefficient < adjusted + 1`. All **34 segments** have
nonempty intersections. For **4,384 values**, the product of official reference
ratios lies in the **closed** interval. Seven segments place it exactly at the
excluded upper boundary: integer truncation then differs by one won at boundary
prices. This is evidence of precision/convention differences, not an exact
reproduction or permission to silently waive discrepancies.

The other **36 values** are 354200's nine dates before a separate July 13 capital
reduction. The original [changed-listing notice](https://kind.krx.co.kr/external/2026/07/08/000562/20260708001349/70763.htm)
was hash-verified and establishes that boundary. Its factor was deliberately not
inferred from an ex-right percentage. The appropriate reference for that event
still requires separate reconciliation. All 36 remain in the audit.

## Reproducibility and downstream consequence

Audit directory: `runtime_state/audit/kr_exrights_basis_20261007/`.
`plan.json` pins 24 official body resources (18 notices and six board decisions),
34 provider payloads and implementation hash. `comparison_cells.json` retains
all 4,420 identities, source values and both projections. `result.json` retains
all 18 events, including both missing pre-event comparisons.
`independent_intervals.json` retains exact numerator/denominator bounds and
verifier/source hashes. No network, database, price, model or outcome writes occur.

Three parser/identity/rounding tests passed. Actual replay of both programs made
zero network calls and preserved hashes, sizes and modification times of all
four evidence outputs. Plan SHA-256:
`2a9d222a219ba3c764e27352bb77e01c73239cf4a56d654cb32926acc101258f`;
result SHA-256:
`106d32b87c030583a01bde64bc605f99f55d12e8811abfc47dcba7c13b1612ea`.

The next source epoch must explicitly name the official ex-reference price
convention and retain separate shareholder-entitlement evidence. H10 paths that
span a rights or bonus event need a validated execution/valuation contract;
price continuity alone does not prove realizable portfolio returns. No strategy
outcomes were inspected, no prices normalized in this audit, and no source or
replacement lane is certified.
