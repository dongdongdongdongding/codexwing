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
Production application results will be recorded after full-panel verification.

Evidence: `runtime_state/audit/us_split_four_repair_20261007/`.
This certifies observed split units, not exact exchange prices, complete source
coverage, point-in-time listing metadata or H10 strategy qualification.
