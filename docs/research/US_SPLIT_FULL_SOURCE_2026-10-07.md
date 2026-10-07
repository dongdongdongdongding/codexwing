# Full independent history for quarantined US split series

Beads: `swing-main-dr43`, following `swing-main-thec` / `swing-main-d3f5`.

The earlier independent audit established mixed split units in 21 Yahoo series
using the latest 100 KIS bars. It could not support replacement of their full
history. This extension freezes the same 21 symbols plus the existing ADBE
control and requests both KIS price bases back to each stored history's start
(no earlier than 2018). No performance outcomes enter selection.

## Measured result

On October 7, the collector reused 44 verified seed responses and captured
**428 additional pages**, completing all **44 symbol/basis paths in 96.49s**.
Twenty-six reached the requested start and 18 exhausted the provider history.
The latter is a terminal collection result, not proof of complete history.
Each response retains request parameters, observation time and SHA256. Identity,
record count, descending unique dates, upper date bounds and pagination overlap
are checked before pages contribute to coverage. The requested end is October 5,
so neither the latest October 6 bar nor a future bar is certified here.

Across both bases, the scoped output contains **42,378 rows**. Independent
reconstruction from all 472 JSON responses exactly reproduced **211,890 numeric
fields** using Decimal, the missing-date sets and positive/ordered OHLC checks.
The current 22 raw files, whole feature panel, listing snapshots and issued
ledger remain byte-identical. Replaying the full collector with network calls
forbidden completed with **zero calls** and unchanged 856 response/receipt files.

| Group | Symbols | Finding |
|---|---|---|
| Complete existing dates, structurally valid | AIXI, CPOP, DLXY, IMMP, IZM, NFE, NRSN, SFWL, UCAR, VWAV, WCT, WHLR | 12 quarantined symbols pass these prerequisites |
| Unchanged control | ADBE | 2,201 scoped dates, no missing or extra dates |
| Incomplete independent history | ALP, BRTX, BTLN, GMEX, GTBP, HUBC, LRHC, NXXT, TNMG | Existing dates still missing; no full replacement |

Missing counts per basis are ALP 2,085; BRTX 969; BTLN 1,289; GMEX 650;
GTBP 725; HUBC 290; LRHC 1; NXXT 858; TNMG 702. Extra provider dates are
reported separately and are not substituted for missing dates. IMMP has 13
zero-volume dates and NFE has one; structural positivity is not tradability.

## Adjustment constraints and a concrete repair target

KIS reports the same volume for MODP0 and MODP1 throughout the common history.
Consequently an adjusted-price replacement cannot simply copy volume and assume
it matches Yahoo's split-adjusted share units. Many price-factor histories also
vary beyond the latest declared split. Full date coverage does not resolve
dividend methodology, earlier corporate actions or venue/session differences.
No production quarantine is released by this audit.

VWAV provides a specific next repair, tracked by `swing-main-ym5x`:
[Nasdaq ECA2026-667](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-667)
and the [SEC filing](https://www.sec.gov/Archives/edgar/data/2038439/000173112226001258/e7956_8-k.htm)
confirm a 1-for-20 reverse split effective September 22, 2026. All four KIS OHLC
fields are exactly 20 times nominal on all 299 pre-event dates and equal nominal
on the ten subsequent dates. Yahoo's September 15 and 16 OHLC instead match
nominal units, while all other 297 pre-event OHLC rows match adjusted units at a
0.5% **unit-classification** tolerance. This tolerance is not exact price
certification. Those two Yahoo volumes also remain in nominal share units.

Example September 15: Yahoo close 0.532 versus KIS nominal 0.532 and adjusted
10.64; Yahoo volume 4,536,500 versus KIS nominal 4,536,511. Correcting price alone
would leave turnover and volume features inconsistent. A repair must preserve
originals, verify all fields, survive refresh without double adjustment, and
recheck derived features, labels and consumers before releasing the quarantine.

## Reproduction and artifacts

From the development checkout:

```bash
python3 research/audit_us_split_history_20261007.py \
  --root /Users/dongdong/Projects/codex_swing/swing-main \
  --audit /Users/dongdong/Projects/codex_swing/swing-main/runtime_state/audit/us_split_full_kis_20261007 \
  --budget-seconds 600
python3 research/compare_us_split_history_20261007.py \
  --audit /Users/dongdong/Projects/codex_swing/swing-main/runtime_state/audit/us_split_full_kis_20261007
python3 -m pytest tests/test_us_split_history_audit.py -q
```

Nine tests pass, including wrong identities, future/duplicate/overlapping dates,
saved-response tampering, network-free reuse and inconsistent field/volume
adjustments. The artifact directory preserves `plan.json`, baseline copies,
immutable pages and receipts, `capture_initial_summary.json`, `comparison.json`,
`independent_verification.json`, `reuse_verification.json`,
`protected_before.json` and `vwav_basis_detail.json`.

This completes the fixed full-source audit, not price normalization, a qualified
H10 strategy, or a production lane replacement. The main normalization and
research issues remain open.
