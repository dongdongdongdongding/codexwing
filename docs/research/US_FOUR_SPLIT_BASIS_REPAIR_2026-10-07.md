# Four partial US split-basis repairs

Issue: `swing-main-ywuy`. Source audit: `swing-main-dr43`.

Full-history source comparisons explain all pre-event OHLC units for AIXI,
DLXY, SFWL and WCT using their official corporate-action chains. This selection
uses source evidence only, without model scores, returns or strategy outcomes.
The fixed comparison tolerances remain 0.5% plus 0.0001 for price and 5% plus one
adjusted share for volume. KIS volume remains nominal in both MODP modes and
must be divided by the entire official cumulative factor.

| Symbol | Latest factor | Pre-event rows | Exact supported rows | Corrected rows | Deferred |
|---|---:|---:|---:|---:|---:|
| AIXI | 7 | 877 | 874 | 870 | 3 |
| DLXY | 5 | 307 | 300 | 295 | 7 |
| SFWL | 15 | 861 | 836 | 832 | 25 |
| WCT | 5 | 483 | 478 | 474 | 5 |

Official latest Nasdaq notices are ECA2026-643, 679, 639 and 642 respectively.
AIXI's earlier 9 and 20 factors are documented in SEC accession
000121390026093890; WCT's earlier 50 factor is Nasdaq ECA2026-131.
Primary HTTP responses and hashes are retained with the full KIS response chain.

The four integrity-pinned JSON references contain the original raw hashes,
original and corrected nine numeric fields, and all forty unsupported rows.
Only exact original matches receive price multiplication and reciprocal volume
adjustment. Dollar volume is recomputed; unknown revisions remain quarantined.
Already corrected input is unchanged. No symbol-wide exemption exists.

The generic repair command retains its original VWAV filename and adds
`--symbol AIXI|DLXY|SFWL|WCT`. It validates all dates and deferred rows, rejects
unexpected source changes, stages a round-trip-verified parquet, and applies
under the US writer lock with complete backups and atomic compare-and-swap.

Independent Decimal comparison of the four staged sources passed 39,689 checks.
The split, lineage, daily quality, refresh, cache, source-audit and map suites
pass 131 tests. Deferred rows continue to separate feature and label runs.
Production application and full-panel verification are recorded below.

Evidence: `runtime_state/audit/us_split_four_repair_20261007/`.
This certifies observed split units, not exact exchange prices, complete source
coverage, point-in-time listing metadata or H10 strategy qualification.

## Production verification

Code `abe4346` was pushed to both branches before application. Under the US
writer lock, 3,976 protected path hashes and the actual current 14:18 panel were
recorded; all four raw files received complete verified backups. Exactly 2,471
rows changed, with 125 other raw rows unchanged, including all forty deferred
rows and every post-event date. All other raw, metadata and ledger hashes match.

The new panel is `daily_features_20180101_20261007_20261007_144228939420.parquet`,
SHA256 `9b00261fb815791ead264ee67a6b8db125afa273550ef4a030dfc68f1f7ef419`.
It retains 5,605,406 rows; all 5,602,810 rows outside the four symbols are exactly
unchanged across every column. Independent Decimal feature/label calculations
pass 56,392 checks, including null future labels across every invalid boundary.

| Symbol | Invalid before → after | Feature-ready before → after | Feature + H20 target available after |
|---|---:|---:|---:|
| AIXI | 877 → 3 | 0 → 706 | 586 |
| DLXY | 307 → 7 | 0 → 101 | 0 |
| SFWL | 861 → 25 | 0 → 344 | 224 |
| WCT | 483 → 5 | 0 → 167 | 47 |

These are source/feature availability counts, not actual model admission or
training. Current admission remains exactly 322 candidates, including admission
history and percentile values. No model was refitted and no issued contract
changed. H10 qualification is unaffected.

Fresh Yahoo full-history responses returned all 2,596 dates across the four
symbols. All 2,488 supported pre-event rows matched the exact reference after
extraction; the only unsupported pre-event dates were the original forty.
The fixed eleven-symbol classification is preserved, including unexplained
OHLC counts CPOP 4, IMMP 138, IZM 594, NFE 1,414, NRSN 910, UCAR 26 and WHLR
1,626. Those seven receive no new exception. Nine additional source histories
remain incomplete as documented in the preceding full-source audit.

The forty unresolved volume observations are tracked in `swing-main-kc3g`;
broader source completion remains `swing-main-d3f5`. Evidence includes
`complete_cohort_classification.json`, `fresh_yahoo_check.json`, `before.json`,
four source backup journals, `rebuild_result.json`, `verification.json` and
candidate pool CSVs. The separate daily collector continues its existing run.

Repeat application performs zero raw writes. Repeating the complete feature
build reuses the verified panel with zero new panel files. Health, picks,
overview and ops-status APIs all return HTTP 200. The application, independent
verification and replay jobs all terminated successfully. The daily collector's
parent 97991/97996 and child 10244 are still running; no overall daily success
is claimed before its terminal receipt.

Subsequent audit: CPOP now has a partial exact-reference repair documented in
`CPOP_SPLIT_BASIS_REPAIR_2026-10-07.md`; its four unexplained OHLC dates remain
quarantined. The seven-symbol statement above describes this earlier snapshot.
