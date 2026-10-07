# Fixed historical reference-event inventory and primary capture

Inventory issue `swing-main-sr2t`; primary capture `swing-main-qzrd`; full
reconciliation remains `swing-main-01n3`. This inventories all 213 codes from
the pinned v11 discrepancy queue, using the fixed 30,936-receipt index and v11
panel. It does not select candidates using strategy outcomes or change prices.

Every captured nominal date is checked against source close, volume and amount.
On a traded date with a captured preceding source observation, signed quote
change establishes a candidate reference price. The expected factor change
`previous_close / reference` is compared with `current_factor / previous_factor`
using exact fractions. The resulting candidates require primary verification;
a provider quote alone is not an accepted corporate-action correction.

The inventory covers **142,762 dates** across all 213 codes:

- 213 first-scope boundaries are explicitly unpaired.
- 15,403 paired dates are nontraded; 107 changes in close, factor or share count
  remain separately recorded for review.
- 127,146 paired traded dates have usable signed references.
- 126,842 have exact factor agreement.
- 17 have nonzero arithmetic-sized disagreements, retained separately.
- **287 events across 187 codes require primary review**. Of these, 132 have no
  source factor change. Provider flags are 169 `00`, 76 `01`, 32 `02`, 10 `04`;
  these flags are observations, not independent event classifications.

Relative disagreement of 1e-12 separates arithmetic-sized diagnostics only; it
does not waive small errors or define source qualification. Some review
candidates remain much smaller than one economic tick. Unsupported quote signs,
uncaptured preceding dates and nontraded events are never counted as clean.
All 213 codes have complete captured nominal request scope in the frozen index.

An independent 75-digit Decimal implementation verified **428,286 nominal
cells**, every event date/reference/classification, all per-code counts and every
unpaired/nontraded boundary. It uses the pinned original receipt contents and
does not call the inventory function. This confirms the inventory computation,
not a primary source or portfolio-return certificate.

## Bounded official-document collection

The 287-event list is frozen with SHA
`a080aa9cf180216445580658c9df2c23af28d14c10244123061554d5112be3c9`.
Each event receives a ±45-calendar-day window; overlapping windows merge only
within the same code. Every event remains in exactly one of **256 windows**.
The manifest pins the inventory, windows, selection keywords and implementation
dependencies. Four events with absent provider names retain ticker-only queries.
This is collection scope; it does not establish issuer or historical identity.

The collector uses a global time budget and a new-window limit. Completed
windows replay from immutable HTTP/body receipts; a budget interruption keeps
partial captures for the same window. Runs have separate receipts. Empty and
partial results remain explicit, and no price correction follows automatically.

The first bounded run completed **8 windows / 178 requests**, with seven complete
searches and one empty search, leaving 248 windows unvisited. The seven searches
contain 220 disclosure records and 49 selected documents. The empty result is
001065 queried as a preferred-stock code. Its common issuer's 001060 window
already contains class-specific notices for both JW preferred issues: December
27, 2023 references of 32,750 for the first preferred class and 61,000 for the
second preferred B class. These bodies are retained, but quote/class identity
linkage and correction still require explicit verification. The empty direct
query is not evidence of no corporate action or no available issuer disclosure.

44 related tests passed. Actual inventory and eight-window capture replay made
zero network calls and preserved all **549 existing evidence files' bytes,
sizes and modification times**. The tests cover normal returns, missing and
already-corrected factors, retained arithmetic residuals, nontraded boundaries,
unsupported signs, missing/duplicate dates, nominal disagreement, deterministic
window merging, ticker-only searches and ambiguous names. Capture remains
incomplete; the observed prefix is not a representative validation sample.

Production evidence under `runtime_state/audit/`:

- `historical_reference_inventory_20261008/`: manifest, by-code results,
  287-event queue, summary and independent verification.
- `historical_reference_documents_20261008/`: fixed 256-window plan, HTTP/body
  receipts, window results and separate bounded-run receipts.
- `historical_inventory_replay_20261008.json`: actual replay verification.

The separate 107 nontraded boundaries and three anchorless codes from the full
1,353-code comparison remain unresolved. Whole-source, point-in-time,
portfolio-return and publication certification remain false. No strategy
outcome, model, live source consumer or lane qualification was changed.
