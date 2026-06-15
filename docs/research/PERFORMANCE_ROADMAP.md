# Performance Roadmap — 75% accuracy / 15%+ return / 8:2 safe trading

Author: Claude (with operator). Date: 2026-06-15. Status: design + roadmap.

Every workstream below is filtered through the Quant + Dev + Validator mental model and is
gated by **forward validation (walk-forward CI), not eyeball judgment**. No candidate is ever
excluded by chart aesthetics; differentiation is only added when forward data backs it at the
same rigor as the cohort release gate.

---

## 0. The decomposition (why this is multi-dimensional)

The goal is realized profit, not any single metric. Per-trade and portfolio return decompose as:

```
per_trade_EV = P(win) · E[gain | win]  −  P(loss) · E[loss | loss]
portfolio_return ≈ (trades / period) · per_trade_EV · (capital_fraction_per_trade)
```

These terms **multiply** — optimizing one while ignoring the others never reaches the goal.
Mapping our validated facts onto the four engines:

| Engine | Drives | Current (validated 2026-H1) | Gap | Primary lever |
|---|---|---|---|---|
| **Accuracy** | P(win) | Exception Leader 77.7% / Practical-80 94% (KOSPI) | mostly there | cohort selection (DONE: 95% EV+tail gate, promoted) |
| **Win-size** | E[gain\|win] | ~+5% realized vs **+12–15% MFE** available | **largest gap** | let-winners-run exit (capture the right tail) |
| **Loss-control** | E[loss\|loss] | tail −7% (leaders) … −17.6% (rebounds) | medium | loss-exclusion guards + tail-aware sizing |
| **Coverage** | trades/period | ~5 KOSPI signals/day | medium | flow signal + practical-80 profile breadth |

Key implication: **accuracy is largely solved for the cohorts; 15% return is blocked by the
+5% exit cap (win-size) and by tail leakage (loss-control), and is throughput-limited by
coverage.** The ML entry model (AUC ~0.56) is plateaued — more variant search is overfitting.
Progress comes from the OTHER three engines, not from re-tuning the entry classifier.

---

## A. Tail-aware sizing (design — the immediate, data-backed refinement)

**Evidence (Exception Leader cohort, n=139, forward 5D, bootstrap 95% CI):** the rebound/pulled-
back slice is *still profitable* (+6.8% avg, 68% win — above the promotion bar), so it is **not
excluded**. The one clean, monotone signal is **tail risk by entry-time distance-from-high**:

| Entry zone (20D-high dist) | tail (worst 5D) | avg MFE | → treatment |
|---|---|---|---|
| near high (≥ −4%) | −7.0% | 12.2% | TIER_A |
| shallow pullback (−8…−4%) | −15.8% | 10.5% | TIER_B |
| deep pullback / rebound (< −8%) | −17.6% | 12.4% | TIER_C |

**Design — equal-risk-budget sizing (not exclusion):** scale position so that
`size × expected_tail` is roughly constant across tiers (equal dollar-at-risk), and set the
stop just outside each tier's empirical tail. Keep every candidate; manage the tail.

| Tier | dist_from_high | position_factor | suggested_stop | rationale |
|---|---|---|---|---|
| A (leader) | ≥ −4% | **1.0×** | −8% | tail only −7%, full conviction |
| B (shallow) | −8…−4% | **0.45×** | −9% | tail ~−16%, halve dollar-risk |
| C (deep/rebound) | < −8% | **0.40×** | −10% (or −6% tight) | tail ~−18%, capture MFE on runners, cap downside |

- **Output, not gate:** emit `tail_risk_tier`, `position_factor`, `suggested_stop_pct` as
  advisory fields on the trade plan (UI/Discord). Never removes a candidate. Directly serves the
  8:2 (80% safety) objective without sacrificing the rebound EV/MFE (the 20% upside capture).
- **Compute:** `dist_from_high_20d` is reconstructable at scan time (scanner already has price
  history); add it as a scan feature, attach the tier in the planner trade-policy layer.
- **Validator caveat:** single regime (2026-H1), rebound direct-slice n=10. Therefore ship as a
  **forward-tracked hypothesis** (measure realized portfolio drawdown vs flat sizing), not a
  locked rule. Self-limiting like the cohort gate.

---

## B. Research roadmap (sequenced, with gates)

Sequencing logic: do the data-ready/low-risk safety work now; attack the biggest return gap
(exit) next with existing infra; then the orthogonal-signal work (flow) that needs data
plumbing; regime-robustness runs continuously underneath all of it.

### Phase 0 — Foundation & honest measurement (now → 1 week)
Goal: make the promoted cohorts real and *observable* before building on them.
- Ship **tail-aware sizing** (Section A) as advisory + forward-track.
- Wire the **Exception Leader buy-surfacing consumer** (selection_lane → buy list) — remaining
  piece from the promotion work; decision_bucket preserved (no feedback loop).
- **Fix measurement gaps found this session:** drift monitor stale since 2026-05-06; reconcile
  walk-forward gate vs live shadow numbers. *Without honest measurement everything downstream is
  blind.*
- Run a live **shadow-compare** of the promoted cohorts (Practical-80 + Exception Leader) for N
  sessions before trusting them with size.
- Quant: no return change yet — this de-risks. Dev: additive, flag-gated, reversible. Validator:
  restores the feedback loop that lets every later phase be judged.
- **Gate to Phase 1:** cohort gate still PASS on fresh data + shadow-compare shows no drift vs
  backtest.

### Phase 1 — Win-size: let winners run (1 → 3 weeks) — **biggest lever for 15%**
The +5% exit cap is the single largest constraint: avg MFE is 12–15% but realized close ~5–8%.
- Design an **asymmetric exit**: cut losers at the tail-tier stop (Section A); let winners run via
  trailing stop / partial-take-and-runner to capture MFE instead of a fixed +5% cap.
- Reuse existing infra: `optimize_exit_policy_per_segment`, `exit_policy_watch`,
  `target_touch_kr_asymmetric_ordered` (MFE/MAE already measured per cohort/profile).
- Quant: this is where the return engine lives — converts the proven MFE into realized gain.
  Dev: `dynamic_exit` already exists and already turns avg positive; extend, don't rebuild.
  Validator: walk-forward exit-policy backtest on cohort rows; gate on **realized net exit EV +
  tail floor**, not on hit-rate.
- **Gate to Phase 2:** asymmetric exit beats fixed +5% on realized net 5D EV at 95% CI on the
  cohorts, without worsening the tail floor.

### Phase 2 — Coverage & orthogonal signal: flow into SELECTION (2 → 4 weeks)
Two jobs at once: break the AUC-0.56 plateau with a *new orthogonal input*, and raise
trades/period.
- **Flow features** (foreigner/institution/retail) are already proven in the loss-exclusion guard
  (+31.9% test win-delta) but are only used to *exclude*. Wire flow into *selection/admission
  scoring* and into the cohort definition.
- **Precondition (Validator):** fix flow coverage first — it was 0% in the ordered-candidate
  dataset though present in the ranked_top20 guard set; the KIS sidecar carries it. This is a
  plumbing/backfill fix, the original justification for the KIS migration.
- Quant: orthogonal signal can lift P(win) AND surface more high-quality candidates/day (coverage).
  Dev: read KIS sidecar flow into the admission scorer; additive feature group. Validator: flow-
  augmented cohort must beat the current cohort forward at 95% CI before it changes selection.
- **Gate to scale:** flow-augmented selection raises coverage and/or EV without lowering the
  release gate.

### Phase 3 — Throughput, KOSDAQ, and the regime thread (ongoing)
- **Coverage math:** 15% annual needs enough independent trades; ~5 KOSPI signals/day must be
  validated as sufficient or widened (flow + practical-80 profile breadth). Model the
  trades×EV×size budget explicitly.
- **KOSDAQ:** no edge in any stream today → accumulate data only (operator decision). Re-run the
  cohort gate monthly; promote only if/when it passes. Never force.
- **Regime thread (the silent killer):** every edge here is validated on one regime (2026-H1
  KOSPI bull). The cohort edge may be partly beta. Build **regime-conditional validation** — does
  the edge survive chop/down-trend? This runs *continuously under every phase*, not as a step. It
  is the largest unmeasured risk to the 15% target.

---

## C. Cross-cutting discipline (the meta-layer)

1. **Forward-validate everything** at cohort-gate rigor (walk-forward bootstrap CI). No eyeball /
   single-metric / aesthetic filters — applies to Claude's own judgment first.
2. **Gate on EV + tail, report hit-rate.** Win-rate is a vanity axis; the goal is realized profit
   with bounded drawdown (8:2).
3. **Self-limiting promotions.** Every promotion reads its gate verdict and auto-stops on
   degradation (already true for the cohort promotion).
4. **One regime is not validation.** Treat all current numbers as provisional until they survive a
   regime change; keep shadow-compare and drift monitoring live.
5. **No feedback loops in measurement.** Promotion must never change the labels the gate measures
   (the Exception Leader decision_bucket lesson).

---

## D. Definition of done (what "goal achieved" looks like)

- A live KOSPI buy stream (Exception Leader + Practical-80, tail-aware sized) whose **forward**
  realized record over ≥2 regimes shows: win-rate ≥ 75%, average realized return consistent with
  ≥15% annualized after costs, and worst-case per-trade loss bounded by the 8:2 risk budget.
- Every signal carries a full trace (cohort, gate verdict, tail tier, size, stop) and a realized
  outcome that feeds the next gate refresh.
- KOSDAQ either earns promotion through the same gate or stays research-only — never forced.
