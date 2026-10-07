# Three additional KR issuance-factor corrections

Official KRX additional-listing notices establish three more errors in the frozen
research price builder. It treated total outstanding-share growth as a
proportional entitlement of existing holders. These transactions issue shares
to subscribers, converting bondholders or a named third party instead.

| Code | Official transaction | Listing date | Added shares | Erroneous factor starts |
|---|---|---|---:|---|
| 291810 Pintel | General offering | 2026-09-22 | 2,657,218 | 2026-09-22 |
| 270520 Appteen | Convertible-bond conversion | 2026-09-28 | 16,868,000 | 2026-09-28 |
| 071950 Koas | Third-party placement | 2026-08-05 | 2,000,000 | 2026-07-21 |

Primary records: [Pintel](https://kind.krx.co.kr/external/2026/09/17/000472/20260917001223/70791.htm),
[Appteen](https://kind.krx.co.kr/external/2026/09/21/000413/20260921001172/70791.htm),
[Koas](https://kind.krx.co.kr/external/2026/08/04/000352/20260804000871/68154.htm).
The official document bodies, viewer routing and search responses are captured
with observation timestamps and hashes. The receipt hash is
`e19d43aed64cfcfc70334e86ea450402aa542838fec847903a458c761e89eb30`.
Pintel's earlier September 17 DART amendment independently identifies the
2,657,218-share general offering and revised September 22 listing date.

## Independent economics and price comparison

The issued quantities exactly account for each traced outstanding-share jump:
11,368,712 to 14,025,930; 23,158,914 to 40,026,914; and 12,459,195 to 14,459,195.
The frozen heuristic factors match those ratios. Koas additionally assigns its
August share-count change back to a July price decline.

The fixed June 30–October 2 window has 65 rows per company. Nominal and adjusted
KIS OHLC agree with each other on all 780 cells. Removing the unsupported
proportional entitlement matches all 772 positive-volume raw OHLC cells exactly.
Pintel has two nontrading dates: its six zero OHL cells remain zero in the panel;
KIS carries close into those OHL fields. These are preserved conventions, not
new executable prices. No selected-pick returns or touch outcomes were computed.

## Separate guarded source version

`normalize_verified_kr_issuance.py` reads the prior, separate two-event corrected
source (SHA `803fa406aa946f1a35ef0eb928f7a2f9ff3928f779cbedfe6f570e448bb7d862`).
It writes `runtime_state/audit/kr_verified_events_v2_20261007/panel.parquet`,
SHA `1d92de63695c20af4170dd107493ff85e1cf50b331303b2580c767c3a26894da`.
The specification pins the input, official receipts, economic verification and
unchanged chunk implementation. It guards old factors, share counts, date
ranges and individual rule counts. Output is created atomically and cannot
replace different existing bytes. Unknown source/evidence revisions fail.

The full source has 5,360,785 rows. Exactly 63 additional rows changed:
Pintel seven, Appteen five and Koas 51. Koas is split into two share-count ranges,
11 rows before and 40 from August 5. Only `adj_factor` and adjusted OHLC changed.
The preexisting constant price basis was preserved, including its original
floating-point representation. Nominal volume and amount were not adjusted.

Independent whole-panel verification establishes:

- Other 5,360,722 rows match the v1 source in every column.
- All raw columns match on all 5,360,785 rows; schema metadata is unchanged.
- The 774 comparable KIS price cells, including two nontrading closes, agree
  within floating-point error: maximum below 0.000000000001 KRW. Six nontrading
  OHL differences remain explicitly preserved.
- The original parent study source/code, six frozen model hashes and pinned
  live KR producer hash are unchanged.
- Repeating the builder returns `REUSED`; panel, manifest and receipt hashes,
  sizes and modification times are unchanged.

Twenty-one focused tests passed, including actual streaming construction,
individual-rule counts, source/evidence/output tampering, immutable outputs,
nontrading zeros, repeat behavior and prior adjustment/trace tests.

Audit evidence is in `lowliq_corporate_actions_20261007/followup_issuance/`
(`capture.py`, source responses, `verify_economics.py`, comparison and receipts)
and `kr_verified_events_v2_20261007/` (manifest, receipt, independent whole-panel
verification and repeat check). These paths are under production `runtime_state/audit/`.

Five event corrections are now represented across the separate v1/v2 chain.
This remains a partially corrected research source: the other 60 mismatch codes
and earlier feature history are not certified. No live price cache, frozen study,
model, score, universe, issuance contract or consumer path was replaced. A new
study requires explicit source provenance and source qualification. The H10
probability and weekly cadence objective remains unqualified.
