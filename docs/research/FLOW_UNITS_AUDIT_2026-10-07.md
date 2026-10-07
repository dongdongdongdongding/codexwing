# KIS investor amount units — 2026-10-07

Issue: `swing-main-g6ey`. KIS investor amounts retained in this repository are
million KRW, whereas cached total turnover (`acml_val`) is KRW. The old `KRW`
investor label and amount/turnover research ratios were incorrect. This repair
does not rescale the source parquet, replace a model, or establish an edge.

## Source evidence and an official documentation discrepancy

The [official daily investor API guide](https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily)
states that amounts are million KRW and quantities are shares. Public guide
JSON was retrieved from the portal's detail/property endpoints and retained in
the audit directory. The daily field description also labels `acml_tr_pbmn` as
million KRW, but captured responses contradict that particular description:
total turnover matches the daily chart's nominal KRW turnover exactly. Do not
apply the investor amount multiplier to total turnover.

For 600 symbols and 30 rows per symbol from the earlier source-normalization
capture, sum foreign/institution/individual/other gross purchases, and separately
gross sales. Across 35,964 positive-turnover side checks, multiplying each sum
by 1,000,000 agrees with total turnover to within 1,842,550 KRW. This is within
the rounding allowance for four million-KRW amounts. Of tested factors 1,
1,000, 10,000, 1,000,000 and 100,000,000, only 1,000,000 satisfies every check.
Values are rounded, not demonstrated to be truncated.

The earlier source-normalization audit also compared 18,000 daily/current
investor rows and nominal chart turnover. These are controls from the same
provider, not independent-vendor or point-in-time history verification. See
[source normalization](FLOW_SOURCE_NORMALIZATION_2026-10-07.md).

Across the full cache (1,663,367 rows, 2,695 symbols), no row has negative
turnover, nonzero net amount with zero turnover, or absolute net amount after
unit conversion exceeding turnover plus a four-million-KRW rounding allowance.
These bounds establish dimensional plausibility, not historical correctness.

## Repair and compatibility

- Shared `investor_flow_units` declares net values in `KRW_million`, turnover in
  `KRW`, and quantities in shares. Refresh receipts now expose field units.
- Live and historical KIS parsers retain every raw number and label the unit
  correctly. Known legacy KIS metadata is canonicalized in persistence, deep
  reports, adapters and flattened features. Unknown providers, pykrx KRW values
  and quantity fallback values retain their units.
- PEAD shadow and the flow research harness convert only net amounts before
  dividing by turnover/ADV. The existing one-won denominator guard remains.
  Future artifacts identify `net_million_krw_over_turnover_krw_v1`.
- Existing research outputs and ledgers are not rewritten. The PEAD lane remains
  a NON-EDGE falsification shadow; its June 23 retraction is not reopened.

Before/after comparisons cover 600 parser snapshots and 600 normalized whale
contracts: only the unit label changes; all other fields, including scores, are
exactly equal. Legacy/new flattened KIS inputs also agree after canonicalization.
Four selected KOSPI/KOSDAQ admission/shadow bundles have no unit feature in their
feature columns. Their input numbers and model files remain unchanged. This is
not a claim about every model or a resolution of historical provider mixing:
pykrx amounts are KRW while preserved KIS numbers are million KRW. A separate
follow-up tracks training/inference provider provenance before any new contract.

## Verification and artifacts

84 relevant tests passed: source-specific units, signed ratios/null/index
preservation, historical/live consistency, legacy cached readers, actual
research feature causal shifting, PEAD panel calculation, adapters, prefilter,
deep reports and flow refresh. No scoring rerun or forward-ledger append was
needed for this unit repair.

Audit root on the production machine:
`runtime_state/audit/flow_units_20261007/`:

- `daily_*`, `investor_*`, `chart_*`: official public guide JSON.
- `unit_evidence.json`: captured-response checks and manifest hash.
- `full_cache_dimensional_bounds.json`: whole-cache sanity checks.
- `before_contracts.json`, `contract_invariance.json`: numeric compatibility.
- `model_input_audit.json`: four selected bundles, hashes and feature counts.

Source cache SHA-256 remains
`ba24a26df7b1abc220f39b51012d8ecade05d40327ba8597fdd7d55622f4c121`.
The user's H10/+5%/70%/2–3 firing-date target remains unqualified; this repair
does not change that verdict.
