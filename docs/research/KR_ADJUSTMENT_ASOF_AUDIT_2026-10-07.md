# KR adjusted-price as-of audit and reconstruction primitive

Issue: `swing-main-xi1c`; corrected candidate work: `swing-main-jm3e`.

The current delisted-inclusive price panel cannot be reused unchanged as
historical signal-time input. Its adjustment algorithm uses later observations
when assigning some past factors. An independent full reconstruction exactly
matches all five adjusted fields on 5,360,785 rows, and fixed date-prefix
reconstructions demonstrate changed historical prices and market-context inputs.
This establishes an availability problem, not the correct corporate-action
factor or the magnitude of any strategy performance distortion.

## Reproducible scope

Inputs were copied completely and checked against their live sources before
and after the audit. Original prices and the original builder remain unchanged.
The final evidence is production
`runtime_state/audit/kr_adjustment_asof_20261007/final/`.

| Input | SHA256 |
|---|---|
| `px_delisted.parquet`, through 2026-10-02 | `8c6fba2daf8d995be66441d873094928f347618c3a41f208c9286509f4fb1981` |
| Existing `build_px_delisted.py` | `a44b3733a59886d75de676a466fb90d0c9aa5480f3f8cca3e2d9cb044db113da` |

The reviewed builder is also frozen in
`research/data/build_px_delisted_20261007.py.txt`. The auditor validates its
complete hash and executes only the numerical adjustment block, excluding all
file reads, delisting joins, validation reads and source writes.

Cutoffs were fixed as March/June quarter ends and July/August/September month
ends before comparison. Every observed code is included. No model score,
selection return, or newly tested candidate outcome chooses a cutoff.

## Findings

Two rules explain the availability risk. Later stock-count changes may assign
a factor to an earlier price-drop date, looking back up to 60 observations.
Separately, a large traded-price move is normalized unless it is in the last
15 observations of a code; appending later rows can change that classification.
Neither rule uses an official corporate-action timestamp.

| Cutoff | Changed adjusted rows / codes | Changed event-factor rows | Eligible cutoff rows with changed shared market context |
|---|---:|---:|---:|
| 2026-03-31 | 41 / 5 | 5 | 501 |
| 2026-06-30 | 70 / 13 | 13 | 741 |
| 2026-07-31 | 140 / 20 | 20 | 691 |
| 2026-08-31 | 39 / 6 | 6 | 644 |
| 2026-09-30 | 0 / 0 | 0 | 0 |

Changed rows are measured separately for each prefix and must not be summed as
unique observations. The last column counts each candidate once, even when
both index features change. Its scope is 5–30억 rolling traded value, positive
signal-day volume, and six available return inputs at that cutoff. It is not a
count of actual model selections. September's zero comparison only covers the
available full panel ending October 2; it does not establish general stability.

For June 30, KOSDAQ index momentum is -14.12826971 using full history versus
-14.24837715 using the prefix; KOSPI is -0.95716832 versus -0.96339389. These
market inputs are shared by 491 and 250 eligible rows respectively. Thus even
unchanged individual stock prices do not isolate a candidate from the effect.
All changed event factors and affected individual-return examples are saved in
per-cutoff CSV files; exact market-context values are in `audit.json`.

## Implemented date restriction

`asof_adjustment(raw, cutoff, block)` removes later rows before every adjustment
decision. Tests prove invariance when every numeric field after the cutoff is
changed, reproduce the later-stock-count and future-row-count counterexamples,
and cover shared market context and invalid source rejection. Together with
the preceding selection audit, 14 tests pass.

A June 30 reconstruction was built and parquet-round-trip verified:
5,183,869 rows, maximum input date 2026-06-30, SHA256
`7c408afb5d91892af813d5d1c162636333812139963969c8f327dd2a572344e4`.
Its file and `snapshot_receipt.json` are in the final audit directory. This is a
research data artifact, not a production source replacement or fitted model.

The date restriction fixes the demonstrated use of later rows. It does not
certify historical provider publication times, absence of later raw revisions,
or the economic correctness of heuristic corporate-action factors. Corrected
H10 research must distinguish these limits and independently verify executable
price/contract evidence before promotion. No threshold or outcome was inspected
to choose a replacement strategy.

## Consumer boundary

The inherited low-liquidity harness computes historical features directly from
this panel, so its full-history inputs are affected. The live KR swing producer
uses separate `px_long` features and `p2_label`; it was not modified here.
`refresh_issued_outcomes.py` and `observe_kr_touch10_prospective.py` use this panel
for settlement. No issued result was changed and no effect on particular issued
returns is asserted by this feature audit. Existing prospective studies remain
unchanged and unpublished. Source/contract verification remains required before
the user goal can be declared met.
