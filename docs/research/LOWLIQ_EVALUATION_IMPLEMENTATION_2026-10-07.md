# Fixed-window evaluator implementation choices, before outcomes

Issue `swing-main-47zr`, parent `swing-main-jm3e`. This records arithmetic choices
for implementing the existing original and cumulative-cadence preregistrations.
No source, feature, model, selection, test interval or target is changed. Neither
arm's Q3 outcomes have been opened. The original source is already rejected for
qualification; an evaluator cannot rehabilitate it.

For every real/noise seed, retain every selected record. An unfilled scheduled
entry contributes zero touch and zero return without cost; a filled record uses
gross policy return minus the registered round-trip percentage-point cost.
Report all-selected touch and filled-only touch separately. The minimum resolved
sample counts resolved filled trades, not unfilled orders. Frequency is firing
dates divided by **all** fixed test sessions, multiplied by five; also report the
maximum five-session firing count. Nothing is annualized from just firing dates.

Controls are all same-date, same-market eligible **nonselected** securities for
that variant. Their mean net return is assigned to each selected record in that
stratum. A market with no selected records gets zero weight. This preserves the
selected market composition. If a required selected/control result is missing
or unresolved, no performance verdict or partial success metrics are emitted.
Each market is reported as a diagnostic, never used to choose a winning subset.

Net EV and same-day excess are pick-weighted means. The 95% moving-block bootstrap
samples contiguous blocks of five test sessions, retaining zero-selection dates,
then truncates to the original calendar length. Each replicate divides sampled
return sums by sampled selected counts. Draw count and RNG seed are those already
registered (5,000 and 20261007). Zero-count replicates are discarded and counted;
no normal-approximation replacement is used.

Each real seed's noise comparison is its same-date daily mean net return minus
the average of the three frozen noise seeds' daily mean net returns, weighted by
that real seed's selected count. All six variants must have the same firing
calendar and daily number of picks, as their frozen eligible universe and
cadence construction require. The registered 0.3pp comparison uses real seed 0;
all real-seed comparisons are displayed. No seed is selected after evaluation.

Ticker placebo uses the same **within-date/market excess** statistic as the
observed candidate. In each draw and each selected date/market stratum, choose
exactly the observed number of securities without replacement from its entire
eligible universe, then use the remaining securities as that draw's control.
The one-sided p-value is `(1 + draws >= observed)/(draws + 1)`, with Bonferroni
family size 3 for the parent and 4 for the registered cadence amendment. This
family correction does not account for the entire historic research search.

Circular firing-date shifts are diagnostic only: rotate the fixed firing mask
through every nonzero offset and use each destination day's already frozen
uncapped top picks. A shifted sample with missing/unresolved records is reported
unavailable, never omitted from the diagnostic count or substituted into the
primary verdict. These diagnostics cannot qualify a candidate.

Cost sensitivities use the same selected/control rows and contract outcomes at
0.3 and 0.215pp, alongside the primary 1.0pp. The primary cost's gates determine
the screen; a sensitivity cannot rescue failure. Any primary target miss rejects
the retrospective screen. Passing is labeled retrospective-only, with
publication disabled; it does not establish per-pick calibrated probability or
live replacement eligibility.

Before invoking the outcome loader, require the entire fixed signal calendar
and H10 maturity, exact input bindings and explicitly accepted research-source,
contract, calendar, universe and score-replay evidence. The existing rejected
source must stop before outcomes are accessed. Hashes bind inputs, but the
statistical engine does not independently authenticate upstream evidence claims.
