# Extended historical source comparison against a frozen receipt index

Issue `swing-main-6wsw`, within full historical capture `swing-main-d277`.
The comparison freezes the 23,776-receipt index produced at 14:18:33 UTC,
SHA `f2c4b3d6831ae9e370cc8b82e2619dd8c71f3520bc97383c00fd1beeb7c54c8d`.
It uses the unchanged v8 panel,
SHA `2a5cf80053751670294f253c68ad67c68219e84a26df9291c15d5882e720e02e`.
The continuing collector can add receipts without changing this cohort.

All **1,048 fully attempted, usable codes / 670,165 dates** were compared. The
overall scope still has 2,949 codes and 65,796 requests; 42,020 requests were
unvisited at the index snapshot. Partial codes remain explicitly listed. This is
an outcome-independent collection prefix, not a representative validation sample
or whole-source certificate. The reviewed 004310 supplement is explicitly
resolved; its original failed attempt and both provenance hashes remain visible.
The compared complete codes account for 23,756 receipts; the other 20 indexed
receipts belong to a still-partial code and do not enter this comparison.

The comparison rechecks the index/scope/capture-manifest bindings, original and
effective response hashes, request identities, payload inspections and supplement
validation. Missing source dates, overlapping windows, changed receipts, duplicate
identities and inconsistent index counts abort. A fully attempted unavailable
code remains unavailable; it is not silently compared on a smaller denominator.

### Observed results

- All **2,010,495 nominal close, volume and amount values match exactly**.
- Nominal open/high/low differ in 64,308 cells. Of these, 64,305 have zero volume
  and amount on both sides, with one side zero and the other equal to that side's
  close. These representation differences remain in the saved table.
- The other three cells are 001527 on March 28, 2024: panel O/H/L are zero,
  provider nominal O/H/L are 11,480; both have close 11,480, volume 2 and amount
  23,060. Provider adjusted OHLC are 22,960 with volume 1 and the same amount.
  This is not classified as a nontraded convention or automatically repaired.
- Adjusted comparison scales each code to its last common traded close. There
  are 381,425 difference cells above the existing 1e-6 arithmetic diagnostic;
  after separately marking 64,305 zero-OHL representations, 317,120 remain.
- **158 codes** have comparable differences strictly greater than 1 KRW; 154
  exceed 2 KRW. The maximum is approximately 129,187.626 KRW for 046070. These
  values are diagnostics for source review, not acceptance thresholds.
- Every code has a traded anchor. No nonfinite comparable differences occurred.
  Nontraded **close** differences are retained in the comparable set.

Independent Decimal comparison reproduced all **4,020,990 nominal comparisons**
and the entire 64,308-record difference table. The earlier 43-code / 972-response
v8 diagnostic reproduces exactly across all four saved tables: 2,148 nominal
differences, 9,256 adjusted differences, 2,509 basis differences and 43 summaries.

The initial development output retained the same numerical differences but
misclassified zero-OHL representations because it only recognized the opposite
direction. That output remains preserved at
`lowliq_history_indexed_comparison_20261007/`; its comparable summary is superseded
by `lowliq_history_indexed_comparison_20261007_v2/`. The corrected classifier
requires zero volume and amount on **both** sides and a zero-versus-close pair;
it does not excuse arbitrary nontraded values or positive-volume zero OHLC.

34 related tests passed, covering explicit partial/unavailable codes, reviewed
supplements, altered receipt/index/source evidence, actual value mismatches,
nontraded-close retention, both zero-OHL directions, missing-date rejection,
empty difference tables and immutable replay. Strategy outcomes remain unopened;
no model, source panel, live lane or qualification threshold was changed.
Actual full-snapshot replay made zero network calls and preserved all nine saved
comparison/evidence files' bytes, sizes and modification times.

Evidence is in production `runtime_state/audit/lowliq_history_indexed_comparison_20261007_v2/`.
Summary SHA: `237b7c6370d67032333e3551d3a93c862c1c18dfcfbedb3cff2821efc5f5926e`.
`source_review_queue.json` contains all 158 codes and concrete worst examples.
Corporate-action/reference-price reconciliation is tracked in `swing-main-01n3`;
broader capture, point-in-time evidence and settlement contracts remain required
before a corrected study can qualify.
