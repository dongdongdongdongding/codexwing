# VWAV price and volume basis repair

Beads: `swing-main-ym5x`; independent full-source audit: `swing-main-dr43`.

VWAV's September 15–16 Yahoo rows retain nominal prices and volume amid an
otherwise adjusted series. The [official Nasdaq notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-667)
establishes a 1-for-20 reverse split effective September 22, 2026. On all 299
pre-event dates, every KIS MODP1 OHLC field is exactly 20 times MODP0; on ten
subsequent dates it is unchanged. KIS volume stays nominal in both modes.

## Repair and scope

`us_split_basis.py` normalizes only the two exactly matched, preserved nominal
rows: OHLC/raw-close/adjusted-close ×20 and volume ÷20, with dollar volume
recomputed. Date, identity, source and every other row remain unchanged. All
nine numeric fields must match the known original row before correction, so an
already corrected provider row is never multiplied again.

The checked-in reference contains the 299 independently compared adjusted rows,
the two original rows, original raw SHA256 and eight KIS response hashes/times.
After the two corrections, the largest observed cross-provider OHLC difference
is 0.1095% and adjusted-share-volume difference is 1.5738%. Those differences
are preserved vendor observations, not fabricated exact agreement. The reference
certifies the audited split **basis**, not exact exchange prices or tradability.

Quarantine release requires exact equality of date, provider, symbol and all nine
numeric fields to a reference row. No symbol-wide exemption is introduced;
unfamiliar vendor revisions or later corporate actions require a new audit.
Structural errors continue to take priority. The other 20 quarantined series
remain restricted. Both normalization code and reference bytes participate in
feature-panel cache fingerprints; the reference also has an explicit integrity
hash. There is no new raw schema or model parameter.

The shared Yahoo extraction function applies the same guarded correction on
future batch and single-symbol refreshes. Unknown historical changes fail the
existing merged-bar checks instead of silently reviving a mixed series.

## Verification before application

The stage command is:

```bash
python3 research/repair_vwav_split_basis_20261007.py \
  --audit /Users/dongdong/Projects/codex_swing/swing-main/runtime_state/audit/vwav_basis_repair_20261007
```

Actual staging preserves 310 rows and changes exactly September 15 and 16.
The original raw SHA is
`a98e30cb9429bec83778c2e7aea5342f01dec105f599d9d164f9f265c0d6ec9d`;
the staged SHA is
`c95073d3d010963bb49958ae681993b3fb84eca8182883a70bafd2a95aefc680`.
Applying adds `--apply`; the command takes the US writer lock, revalidates the
baseline, saves a full hash-verified backup and uses the existing audited atomic
store. Repeating an applied repair performs no additional source write.

At 14:15 KST a fresh full Yahoo request returned all 310 dates; extraction
normalized the known rows and all 299 pre-split rows passed the exact reference.
The latest October 6 low/volume also differed from the earlier saved source.
That separate mutable latest-bar difference is preserved in the fresh audit;
this basis repair retains the existing post-event rows.

The focused split-basis, lineage, daily-quality, refresh, cache, history-audit
and lane-map suites pass **127 tests**. Tests cover all nine unknown-field
revisions, missing fields/identity/date scope, reference corruption, unchanged
already-fixed provider values, duplicate indices and refresh rejection of an
uncertified revision. Production application and full-panel evidence follow
below when verified. No H10 strategy improvement is inferred from data repair.
