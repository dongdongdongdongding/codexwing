# Expanded historical source comparison: 2,024 securities

Issue `swing-main-13qa`; wider normalization remains in `swing-main-01n3`.

A new immutable coverage index freezes **46,520 response paths** while the
historical collector continues independently. It retains 46,518 original
captures and two original errors. The explicitly reviewed 004310 and 102460
supplements resolve those errors for this index, with the original failures,
trusted recovery plans and effective responses all retained in provenance.
All 30,936 entries of the preceding index are exactly unchanged; 15,584 entries
are added. Files published after the initial path enumeration are outside this
snapshot, even though collection remains active.

| Scope | Fixed index |
| --- | ---: |
| Target requests | 65,796 |
| Indexed responses, including two reviewed supplements | 46,520 |
| Requests not yet visited at the snapshot | 19,276 |
| Target securities | 2,949 |
| Fully captured, usable securities | 2,024 |
| Securities with unvisited requests | 925 |
| Compared source dates | 1,313,188 |
| Nominal numeric cells compared | 7,879,128 |

The source remains immutable v14. All four comparison tables are exact for
the previous **1,353 securities / 872,671 dates**. This preserves the previous
192-code diagnostic queue. The added scope contains 671 securities and 440,517
dates. Independent Decimal comparisons revalidate 7,792 nominal requests and
all **2,643,102 new numeric cells**; all 58,371 new nominal difference records
exactly match the comparator, including their representation classifications.

Across the full expanded scope, nominal close, volume and amount match exactly.
The 149,859 nominal differences concern open/high/low. Of these, 149,853 are
recorded nontraded zero-versus-close representations. Six cells on two dates
have positive volume and therefore remain unexplained by that convention:

| Code | Date | Source O/H/L | Provider nominal O/H/L | Close | Volume | Amount |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 001527 | 2024-03-28 | 0 | 11,480 | 11,480 | 2 | 23,060 |
| 145210 | 2025-03-21 | 0 | 1,126 | 1,126 | 1,015 | 1,142,890 |

145210 is newly observed. Issue `swing-main-r7rt` requires authoritative session
and intraday evidence to distinguish regular trading, after-hours activity and
suspension semantics before changing any raw value. Neither provider is copied
over the other, and a positive aggregate volume does not by itself prove an
executable regular-session open.

The expanded comparable-adjusted queue contains **316 codes above one KRW**:
the previous 192 plus 124 newly inspected securities. This larger queue reflects
the expanded cohort; the preceding cohort and repairs are unchanged. Five codes
lack a traded anchor: 058530, 066410, 068940, 099520 and 121800. The latter two
each have 679 scoped dates from December 15, 2023 through October 2, 2026, all
with zero volume and amount. Their unavailable comparisons are retained, not
classified clean. Nontraded close values remain included in diagnostics.

Four existing index tests pass, in addition to the 85 v14-related tests. The
actual expanded index independently preserves all old entries and both error
provenance chains. Source comparison and independent checks use only captured
evidence; no new quote request is made for this comparison.

Production artifacts under `runtime_state/audit/`:

- `lowliq_history_coverage_indices/index_20261007T164015205007.json`
- `expanded_history_snapshot_20261008/` — recorded snapshot driver and receipt,
  independent index verification and all new nominal checks/differences.
- `lowliq_history_indexed_comparison_v14_expanded_20261008/` — complete expanded
  comparison, unvisited scope, source-review queue and prior-cohort verification.

Index SHA: `3573f9cf558c9c733e0fa4b1c63127a080bf6b89554ca78696150d2980cbefd7`.
Source SHA: `700903bde57d828f77a0a01df4d1d62e620c2cf0bd6df8fc050c36fc6910d069`.
Both preceding fixed indices/comparisons and all source versions remain intact.
Source, point-in-time, portfolio-return and publication certificates remain
false; Q3 outcomes and live lane replacement are still deferred.
