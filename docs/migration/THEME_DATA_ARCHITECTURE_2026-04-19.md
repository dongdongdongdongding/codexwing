# Theme Data Architecture 2026-04-19

## Objective
- Build a traceable theme-data foundation accurate enough for:
- previous US session to current KR pre-open theme priors
- daily strong/weak theme monitoring
- scanner score features with explicit provenance

## Why The Previous Structure Was Not Enough
- `stock_master`, `seed_catalog`, and `keyword_fallback` were mixed in one resolution path.
- official classification and theme inference were not clearly separated.
- `FDR` can provide useful official descriptors, but not a complete theme truth table by itself.
- US full-universe listings have weak sector coverage outside the `S&P500` overlay.

## New Layered Model
1. `instrument_master`
- one record per symbol
- only official or near-official classification fields
- keeps `classification_source`, `source_listings`, `market_scope`, and timestamp

2. `theme_membership`
- one record per symbol with multiple memberships
- each membership keeps `theme_source`, `theme_inference_status`, `confidence`, `reasons`, and `evidence`
- downstream scanners consume this layer instead of directly turning `industry` into `theme`

3. `theme_transfer`
- source-market theme to target-market theme edges
- designed for future US-close to KR-open transfer priors
- not hardcoded into scanner logic yet

## Storage Mapping
- long-term memory
  - `runtime_state/long_term/instrument_master/KR.json`
  - `runtime_state/long_term/instrument_master/US.json`
  - `runtime_state/long_term/theme_membership/KR.json`
  - `runtime_state/long_term/theme_membership/US.json`
- artifact/report layer
  - `runtime_state/reports/theme_validation/theme_data_pipeline_kr.json|md`
  - `runtime_state/reports/theme_validation/theme_data_pipeline_us.json|md`

## Source Policy
- KR official base:
  - `FDR KRX-DESC`
  - strongest fields: `Industry`, `Products`
  - weaker field: `Sector` because sparsity is materially higher
- US official base:
  - `FDR NASDAQ`, `NYSE`, `AMEX`
  - `S&P500` overlay for `Sector`
  - treat non-`S&P500` sector availability as limited

## Membership Priority
1. `stock_master`
- highest trust for KR where curated mapping already exists

2. `seed_catalog`
- explicit ticker-theme seed links

3. `official_text_match`
- conservative fallback from official classification text
- useful for bootstrapping US and for filling KR gaps

## Scanner Integration Rule
- scanner should read theme memberships, not raw industry strings
- `theme_source=stock_master` remains the only source eligible for the strictest exception path
- lower-confidence sources can influence ranking but should not bypass hard filters alone

## Validation Rule
- every artifact must expose:
  - version
  - coverage
  - warnings
  - source distribution
  - sample rows

## Next Step
- build `theme_transfer` edges from realized co-movement and event studies
- use those priors in KR pre-open scoring as a separate explicit feature
