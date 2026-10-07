# Removing a third-party issuance misclassified as a bonus event

Issue `swing-main-3pog`; wider source reconciliation remains `swing-main-01n3`.

V13 correctly uses the December 20, 2023 opening reference for 002880's actual
capital consolidation. Eleven comparable price cells on December 15–21 still
differed by up to 1,455.681180 KRW. The remaining cause is a second, false event
on December 22, rather than a revision of the verified December 20 auction.

Replaying the pinned original builder on all **2,147 original 002880 rows**
reproduces all five adjusted fields exactly. The trace identifies a `lag` rule:

| Field | Verified value |
| --- | --- |
| Incorrect adjustment date | 2023-12-22 |
| Later share-count trigger | 2024-01-19 |
| Distance | 17 observed sessions |
| Trigger shares before/after | 38,730,299 → 46,739,450 |
| New shares | 8,009,151 |
| Incorrect bonus multiplier | 46,739,450 / 38,730,299 |

The December 19 issuance decision, December 26 payment completion and January
18 final listing notice all describe **third-party placement**, not a
distribution to existing holders. The five named recipients' allocations are
2,288,329, 1,716,247, 1,716,247, 1,144,164 and 1,144,164 shares, totaling exactly
8,009,151. The final notice identifies A002880 / KR7002880003 and January 19
listing with a one-year holding restriction. Its increase exactly matches the
algorithm's later trigger.

On the false event date, the independently captured nominal response gives
1,360 close, -258 change and therefore the unchanged **1,618 reference**. Open
is 1,578, volume 7,009,766 and the provider adjustment marker is zero. Source
shares remain 38,730,299 on both December 21 and 22. Thus the genuine market
price decline was incorrectly interpreted as a bonus ex-date when the later
third-party share increase arrived.

`audit_dayou_third_party_lag.py` verifies the original trace, all three primary
documents, actual source boundaries and nominal response provenance. It rejects
holder placements, other trigger dates/counts/rules, changed source factors,
listing counts, codes, and a quote indicating a real reference change. The
1e-15 relative check links two floating representations of the same traced
multiplier; it does not change the one-KRW provider diagnostic threshold.

V14 removes only the false December 22 factor using five nonoverlapping rules
across 674 rows. The verified December 20 auction/consolidation and all actual
outstanding-share counts remain intact, including the January issuance and later
capital changes. Independent 75-digit arithmetic checks all corrected factors
and 2,696 adjusted prices. Full comparison of **5,360,785 rows** confirms exact
schema/metadata and every raw field; every field of the other 5,360,111 rows is
identical. Maximum relative decimal representation error is 2.11e-16.

The same fixed 1,353-code / 872,671-date comparison is repeated. All four tables
are exact for the other 1,352 codes, and the entire nominal/provider-basis tables
are exact. For 002880, maximum comparable difference falls from 1,455.681180 to
**0.999999999999227 KRW**, with zero cells above one. The diagnostic queue falls
193 to 192 codes; three unavailable anchorless comparisons remain unresolved.
This is the scoped price-reference result, not whole-source certification.

85 related tests pass. Actual verifier/normalizer replay makes zero network
calls, reuses v14, and preserves 2,252 existing files' bytes, sizes and modification
times. The original builder, earlier panels and primary evidence remain intact.

Production evidence under `runtime_state/audit/`:

- `dayou_third_party_lag_evidence_20261008/verification.json`
- `kr_verified_events_v14_20261008/` and its independent verification
- `lowliq_history_indexed_comparison_v14_20261008/`
- `dayou_third_party_lag_replay_20261008.json`

Evidence SHA: `06829f53b09b5a277626243869160678240040734a4cc5e5e3e5f839b2ee4c6d`.
V14 panel SHA: `700903bde57d828f77a0a01df4d1d62e620c2cf0bd6df8fc050c36fc6910d069`.

Source, point-in-time, portfolio-return and publication certificates remain
false. No Q3 outcomes, refit or live lane replacement occurs in this correction.
