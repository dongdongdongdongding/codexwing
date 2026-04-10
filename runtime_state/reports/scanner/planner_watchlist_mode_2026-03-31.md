# Planner Watchlist Mode Validation

- Date: 2026-03-31
- Goal: confirm that learned market policy suppresses active recommendations only in avoid buckets, while KR markets remain differentiated.

## Validation Results
- `RUN-08CDC5E4` (`NASDAQ`)
  - planner decisions were cleared
  - watchlist kept `AAPL`
  - warnings included `MARKET_POLICY_WATCHLIST_ONLY`
  - realized outcome placeholder is recorded as `WATCHLIST_ONLY`
- `RUN-61E3B6D4` (`KOSPI`)
  - scanner returned 0 results
  - top reject reasons included `MARKET_POLICY_AVOID`
  - interpretation: current KOSPI bucket is still too hostile for active recommendations
- `RUN-C95E8EF1` (`KOSDAQ`)
  - scanner returned 0 results
  - rejects were `LIQUIDITY_FILTER_FAIL`, `KR_HARD_FILTER_FAIL`, `PRECISION_GATE_RED_MARKET`
  - interpretation: KOSDAQ was not blanket-rejected by learned market policy; quality/risk gates blocked the sample instead

## Conclusion
- US avoid buckets are now downgraded to watchlist-only at the planner stage.
- KOSPI and KOSDAQ are no longer behaving as one shared KR policy surface.
- This is safer for win-rate improvement because it avoids forced recommendations in buckets that the external labeled dataset rated as structurally weak.
