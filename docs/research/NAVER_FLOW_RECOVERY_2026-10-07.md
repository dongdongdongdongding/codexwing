# Naver investor-flow recovery — 2026-10-07

The default production KR flow lookup failed for 005930 and 035420: pykrx returned
empty flow, and the old `finance.naver.com/item/frgn.naver` URL returned HTTP 200
with the new app shell and no legacy tables. Three captured HTML responses,
including 091990, establish this failure independently of HTTP status.

The public Naver page's own JavaScript identifies
`/front-api/stock/domestic/trend`, `code`, `exchangeType=KRX`, and the preview/list
sizes. The adapter now uses that response, explicitly in shares and KRX venue.
It requires ten ordered, unique, non-future observations with measured quantities,
checks net = buy minus sell for each of three investor groups, and rejects an
empty latest KRX observation or zero latest trading volume. Missing values never
become measured zero. A measured zero net with nonzero gross trading is valid.

The newest source date must not precede the latest known prior market session.
This uses the observed price calendar, not a weekday guess. An unavailable or
stale calendar cannot certify full freshness; the evidence records its reference
and availability. This is not a historical PIT calendar reconstruction or a
general freshness fix for every provider.

## Actual verification

Production audit directory:
`runtime_state/audit/flow_freshness_20261007/naver_current/`.

- `captures.json`, saved HTML and public JavaScript preserve the old endpoint
  failure and the new endpoint/venue/unit evidence.
- `actual_before_flow.json`: both normal symbols returned `valid=False`.
- `trend_capture_manifest.json`: three full API responses and SHA256 identities.
- `independent_kis_quantity_check.json`: two symbols × ten observed dates ×
  three net-volume fields = 60 exact matches to previously captured KIS data.
  This verifies quantities; it does not assert that the providers' prices match.
- `actual_fixed_flow.json`: fresh real lookups return valid October 6 data for
  005930 and 035420. 091990 remains invalid: its latest January 11, 2024 row has
  no KRX observation. No rescan, DB mutation or external message was performed.
- `independent_aggregate_check.json`: all nine 1/3/10-observation quantity sums
  for both valid symbols match independent integer calculations.

## Personal-investor values and provenance

The old HTML path inferred personal net buying as minus foreign plus institutional
net buying. That residual also includes other participant categories. The new
contract uses the provider's actual individual net volume, independently matched
to KIS. For 005930's latest ten observations the inferred value would have been
+1,051,439 shares; the reported individual net is -17,404,752 shares. Neither is
relabelled as the other.

`naver_krx_shares_v1` carries `retail_basis=reported_individual_net_volume`, venue,
observation count, source hash, retrieval time and calendar reference. Scanner
raw rows and the existing DB `leader_metrics` JSON preserve this evidence.
Direct and live-fetch deep reports preserve the same contract. No database
column is added. Historical rows keep their original values; old model training
and new source semantics require the separate `swing-main-x0fq` input audit.

The combined suite passes 81 tests. The regression cases cover the three real fixtures, missing/non-numeric fields,
net/gross disagreement, insufficient windows, duplicate/future/stale dates,
holiday-aware reference handling, observed zero net and HTTP failure. The real
response also passes through QuantStrategy, scanner/DB payload construction and
both deep-report paths while retaining quantities and contract evidence.

`swing-main-2kmm` owns this source repair. `swing-main-lk6b` retains broader source
freshness and historical impact work. KR issuing swing lanes do not consume
these investor values; this is not evidence of an improved H10 edge or calibrated
probability.
