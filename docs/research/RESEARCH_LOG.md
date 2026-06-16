# Research Log — performance roadmap execution

## Consumer-parity verification + unification adapter (2026-06-16)
- **Verified** (today's KOSPI run, web/Discord/Top-deep/archive): web ↔ Discord are consistent
  (both render `scan_deep_reports`, section-labeled). But the **learning archive exports only
  `market_scan_results`** (export L337), while the user-facing deep reports are built from
  scan_universe_admission + KIS shadow + exception. 14/23 deep tickers are NOT in
  market_scan_results -> the models/cohort-gate learn from a DIFFERENT set than the user sees, and
  the production buy stream is empty (picked=0) so the Top is dominated by KIS_SHADOW_BLOCKED.
- **Fix (unification adapter):** `report_regime_signal_shadow.down_buy_scan_rows` converts the
  DOWN/chop-regime picks (the OOS-validated 75%+ reversal leg) into `market_scan_results` rows
  (decision=`REGIME_DOWN_BUY`, lane=`REGIME_DOWN`). Routing through market_scan_results makes them
  outcome-tracked AND learned, so surface=archive=learning hold for this stream. Flag-gated
  `AG_REGIME_DOWN_PRODUCTION` (default OFF) — stays off until the shadow ledger confirms the live
  edge; deployment is then one flag flip. Tested (network-free conversion).
- **Remaining follow-on:** surface the DOWN production rows on the web/Discord deep reports as a
  distinct production section (so the user *sees* them, not just tracking) — the deep-report
  generation change. Then re-run the same parity check to confirm web=Discord=archive=learning show
  identical DOWN tickers/order.



Living, sequential log. One step at a time, fit the existing framework (see
[PERFORMANCE_ROADMAP.md](PERFORMANCE_ROADMAP.md) + bd). Every step is recorded through the loop:
**데이터(Data) → 용도(Use) → 회고(Retrospective) → 테스트(Test) → 운영(Operation)**, then
updated and iterated. The test (forward validation) decides whether to build — not judgment.

Status legend: 🔬 testing · 🛠 building · 🚦 shadow · ✅ live · ⏸ parked

---

## Step 1 — Overextension (peak-chase) guard for the Exception Leader stream
Status: ✅ built + verified (flag-gated, shadow until live confirm)
Phase: 0 (foundation). Updated: 2026-06-15.

### 데이터 (Data needed / current fill / how to fill)
- Needed at entry time: **RSI14** and **distance-from-20D-high** per candidate.
- Current fill: Exception Leaders are FEATURE_MISSING — `position` populated only **1.4%**,
  `chase_risk_level` = "불명", `is_peak` uncomputable. So the system has **no overextension read**
  on this stream.
- How to fill (fits existing schema): **reconstruct RSI14 + dist_from_high from price history**
  (scanner already fetches it). Demonstrated offline on the full cohort (n=139). No ML features
  required — works precisely because price is always available.

### 용도 (Use)
- A **peak-chase guard** on Exception Leader promotion: demote/observe candidates that are
  at-high AND overheated.
- Same reconstructed `dist_from_high` already feeds the **tail-aware sizing tier** (Section A of
  the roadmap) — one feature, two consumers.

### 회고 (Retrospective — where it failed)
- **System:** peak guards (`is_peak`, `EDGE_PEAK_ENTRY_RISK`, `KOSDAQ_QUANT_T1_PEAK_FADE`) all
  key off `position`, which Exception Leaders lack → the promoted stream bypassed the peak guard
  entirely. A future RSI-80-at-high exception leader would be promoted unchecked.
- **My reasoning (recorded so I don't repeat):** I twice eyeballed today's picks as "parabolic /
  at new highs" using an 8-day lookback. With a proper 20/60D high + RSI14 they are RSI 39–60 and
  −10…−30% BELOW their highs — pulled back, not peaked. Wrong because of short lookback + no
  feature computation. (See memory: research-discipline-ev-not-eyeball, working-loop-discipline.)

### 테스트 (Forward validation — done, decides the build)
Cohort = Exception Leader KOSPI SWING, n=139, forward 5D, bootstrap 95% CI.

| Slice | n | win | avg5d | MFE | tail |
|---|---|---|---|---|---|
| RSI≥70 alone | 25 | 68.0% | +9.94% | 10.8% | −16.6% |
| at-high alone (dist≥−3%) | 34 | 73.5% | +5.82% | 10.0% | −7.0% |
| **at-high AND RSI≥65 (true peak-chase)** | **18** | **55.6%** | **+2.65%** [CI +0.5,+4.8] | 6.9% | −7.0% |
| everything else | 121 | 81.0% | +8.74% | 12.5% | −17.6% |
| ALL (baseline) | 139 | 77.7% | +7.95% | 11.8% | −17.6% |

**Verdict:** overextension *alone* (RSI or at-high) is NOT a clean signal — do not guard on it.
The **combination** at-high AND overheated (the genuine peak-chase) IS a real, large degradation:
win 56% vs 81%, avg +2.65% (barely clears friction) vs +8.74%, MFE collapses 6.9% vs 12.5%. It is
an **upside collapse, not a tail blowup**. A guard is warranted — but only on the combination.

### 운영 (Operation — design, not yet built)
- Add `dist_from_high_20d` + `rsi14` as reconstructed scan features (additive).
- Exception Leader promotion: if `dist_from_high_20d ≥ −3 AND rsi14 ≥ 65` → demote to OBSERVE
  (or shadow), keep decision_bucket=exception_leader (no feedback loop). Else promote as before.
- Flag-gated (`AG_KR_PEAKCHASE_GUARD`), self-limiting (re-validate on the daily cohort refresh),
  reversible. Shadow-compare before it can demote live.
- Today's 5 picks: all outside the danger zone (RSI<65, dist≤−10%) → none would be demoted.

### 기록·갱신 (Updates)
- 2026-06-15: test complete; guard justified on the *combination* only.
- 2026-06-15: **built** — `modules/overextension.py` (rolling RSI14 matching the validation +
  dist-from-20D-high, fail-open) + `legacy_orchestration` withholds gate-promotion for the
  peak-chase combination (decision_bucket preserved). Flags: `AG_KR_PEAKCHASE_GUARD`,
  `AG_PEAKCHASE_RSI_MIN`/`AG_PEAKCHASE_DIST_MAX`. Tests: `tests/test_overextension.py` (network-
  free) + suite green. Live check on today's 5 picks: rsi 39–60 / dist −10…−30% → peak_chase=False
  for all (none suppressed), ok=True. Matches the offline RSI/dist read.
- Next: Step 2 — full 140-column × per-cohort fill-rate + guard-coverage matrix (find any other
  guard silently blind like the peak guard was).

---

## Loop iteration 5 — multi-regime price-primitive model (FDR backfill breaks the data limit)
Status: ✅ verified OOS → direction CONFIRMED, proceed to build. Updated: 2026-06-15.

- **문제:** the rich sidecar is only ~1 month (May 2026) = one regime; no model could be validated.
  Operator point: backfill from FDR/yfinance instead of waiting for KIS.
- **가설:** reconstruct price-primitive features + 5D labels over a long multi-regime history from
  FDR; a regime-conditional factor model has stable OOS edge (momentum in up-trends, reversal in
  down/chop) — the sign-flip that broke the single-regime models.
- **검증:** built a 2.5yr panel (2024-03..2026-06, 300 liquid KR names, 153K rows). (1) sign-
  stability now shows `ma60_dist` stable (mean-reversion). (2) GBM multi-regime OOS AUC 0.513
  (POSITIVE — the 1-month inversion was a single-regime artifact). (3) walk-forward (train→test)
  regime-conditional rule: top-decile OOS win 54.7% / net +2.54% vs base 52.5%/+1.27%;
  **DOWN/chop reversal picks 62.6% win / net +3.05%**; MFE avg +12.9%.
- **결과:** thin but real, OOS-verified positive edge; structure = regime-conditional factor sign
  (UP=momentum/above-MA, DOWN-chop=oversold reversal). DOWN/chop reversal is the strongest piece.
- **회고:** my "no edge" (iters 1-2/4) was a single-regime (1-month sidecar) artifact, and my first
  "breakthrough" read had survivorship + in-sample-regime flaws — caught on self-review and
  re-verified walk-forward. Edge clears costs but is thin (+2.2pp) with severe single-name tails
  (−48%) → mandatory risk sizing. Survivorship inflates absolute returns; the relative/regime edge
  is robust (base stable across test halves).
- **빌드 완료:** `modules/regime_conditional_scorer.py` (validated spec, tested) +
  `multi_agent/tools/report_regime_signal_shadow.py` (scores a liquid universe daily, ranks within
  regime, applies tail-aware sizing, records picks to a JSONL ledger, and auto-resolves the realized
  5D outcome of elapsed picks so the live edge is measured before any production role). Registered
  in run_daily_ops.sh (AG_REGIME_SIGNAL_SHADOW_ENABLE). Observation-only; never touches the live
  scanner/planner. Tests: test_regime_conditional_scorer + test_regime_signal_shadow (network-free).
- **다음:** accumulate the shadow ledger forward; once the live forward record confirms the OOS
  edge, combine with the structural edges (theme/watch) and graduate from shadow. Keep collecting
  sidecar so rich features eventually add to the price base.

---

## Loop iteration 1 — does ANY populated feature separate winners OOS? (the coin-flip mission)
Status: ✅ done — refuted; reframes the model question. Updated: 2026-06-15.

- **문제 (Problem):** production/base win is a coin-flip (Top5 48%, base 46.6%); mission is to raise
  P(win) robustly, anti-overfit.
- **가설 (Hypothesis):** some populated entry feature separates 5D-winners from losers OOS.
- **검증 (Verify):** KOSPI SWING archive, date split 70/30 (cut 2026-05-14), top vs bottom tercile
  win, TRAIN vs TEST. Also the theme-gate levels.
- **결과 (Result):** REFUTED. Every score feature collapses or *reverses* OOS:
  decision_score 51/47→32/44, prob_clean 71/35→38/37, expected_edge 62/41→32/39,
  phase25_prob 24/57→41/34, alpha/conviction/tech/whale/volume all flip/weak. Base win itself
  shifts 50%→37% (regime). The ONLY OOS survivor is the **theme gate**: in the hard 37%-base test
  period, pass/near/small_sample have ~0 candidates, but **watch holds (n=13, 69.2% win, +24.2%
  avg)**. So the headline "Practical-80 94%" was train-concentrated; the durable piece is `watch`.
- **회고 (Retrospect):** the edge is **structural/thematic, not score-based**. This is exactly why
  AUC sits at 0.56 and why Codex's score-reranking variants overfit — there is no OOS signal in the
  raw scores to learn from. Training another model on these features is futile. The regime shift
  (50→37) is the dominant breaker. **Model comes AFTER robust features exist**; priority is
  orthogonal signal (flow) + understanding/encoding the theme mechanism, all OOS-gated.
- **다음 (iteration 2):** test the orthogonal flow signal (foreigner/institution) as an OOS
  separator — the one untested input and the KIS migration's original justification.
- **적용:** `watch` added to Practical-80 (cohort gate mask + planner promotion), flag
  `AG_PRACTICAL80_INCLUDE_WATCH` (default on, reversible). Gate still PASS. Thin (n=13 OOS) →
  forward-tracked.

## Loop iteration 2 — does the orthogonal flow signal separate winners OOS?
Status: ✅ done — refuted (1d); multi-day untestable (coverage). Updated: 2026-06-15.

- **문제:** scores have no OOS edge (iter 1); flow is the one untested orthogonal input.
- **가설:** foreigner/institution/retail flow separates 5D-winners OOS.
- **검증:** same date-split tercile test on archive flow columns (33% coverage for 1d, 17% for 3d/10d).
- **결과:** REFUTED at 1d — foreigner_1d 19/29→41/38 (flip), institution_1d flat, retail_1d
  24/18→30/43 (reverse), whale_flow_1d sign-inconsistent, flow_consensus_buying 22/22→18/61
  (strong reverse). The theory-favored **multi-day flow (3d/10d accumulation) is UNTESTABLE** —
  only 17% coverage, test n insufficient.
- **회고:** no robust univariate OOS edge in either scores (iter 1) or 1d flow (iter 2). The only
  OOS edge is structural (theme `watch`). **Conclusion: results require NEW robust signal, not more
  model training on existing features (that is the overfitting Codex already hit).** The single
  most-promising untested lever is multi-day institutional/foreigner accumulation flow, blocked by
  17% coverage (and flow_fetch_count=0 in live ops).
- **다음 (iteration 3):** close the multi-day flow coverage gap (fetch/backfill foreigner_3d/10d,
  institution_10d), THEN re-test as an OOS separator. Data work, not modeling.

---

## Step 4 — ROOT CAUSE: the production yield collapse is upstream (KIS operational prefilter)
Status: ✅ diagnosed — this reframes the whole problem. Wrong track corrected.
Phase: 0→ becomes the top priority. Updated: 2026-06-15.

### The finding (evidence)
Same KOSPI SWING, today, by execution path:
| Run | scanned | **picked (production)** | liq-rejects | path |
|---|---:|---:|---:|---|
| 01:33 | **833** | **27** | 0 | full-universe scan (nightly) |
| 09:45 | 80 | **0** | 43 | KIS operational prefilter |
| 15:47 | 80 | **0** | 41 | KIS operational prefilter |

The operational path produces **zero production picks**; the full-universe path produces 27.
The difference is entirely the candidate generator.

### Root cause (code-confirmed)
- `kis_operational_prefilter.build_*` selects the top-80 by `selection_score` = momentum ranks
  (volume_rank w1.0 + **fluctuation_rank w0.75** + volume_power w0.85 + **VI +8**) with only a
  weak log-scaled `value_traded` bonus and **no hard liquidity floor**. `_has_quote_activity`
  only checks volume/value > 0 (traded at all), not "liquid enough".
- Result: high-등락률 / VI-triggered **illiquid small-caps** fill the 80 slots; the scanner's real
  liquidity gate (AG_KOSPI_UNIVERSE_MIN_AMOUNT = 12B KRW) then rejects ~54% of them
  (sampled rejects traded 9M–131M KRW, <1% of the floor). Effective pool ≈ 37 → ML cuts 19 →
  ~0 production → forced onto the exception-leader fallback.
- The full-universe scan applies the 12B liquidity floor at universe construction, so it has 0
  liquidity waste and yields real picks.

### Implication for ALL prior work (re-read of existing test results)
- **Codex's KIS model research kept returning "no_improvement / 0 promotable"** — plausibly because
  it trains/ranks on prefilter candidates that are ~half illiquid junk. The model isn't necessarily
  bad; the candidate generator feeding it is polluted. (Re-validate models on a liquidity-clean pool.)
- The validated cohort edge (Exception Leader 77.7%, Practical-80 94%, archive-based) sits
  *downstream* of this broken generator → operationally it is starved.
- `flow_fetch_count = 0`: the orthogonal flow signal (the KIS migration's main justification) is
  not even fetched in the operational prefilter.

### 회고 (my wrong track)
- I spent steps adding SAFETY (peak guard) and proposed restoring the drift monitor — the opposite
  of what was needed. The disease is candidate YIELD/QUALITY at the prefilter, not insufficient
  safety. (User flagged this directly; corrected here.)

### Research hypotheses (ranked) + influencing factors → Step 5
- **H1 (primary):** add a hard liquidity floor to the prefilter seed (drop value_traded below a KR
  market floor BEFORE the 80-cap) → the 80 slots fill with liquid momentum names → production picks
  recover toward the full-scan level. Highest leverage, smallest change.
- **H2:** re-weight selection_score toward liquidity/quality vs raw fluctuation/VI.
- **H3:** widen the prefilter pool or use the full-universe scan for operational SWING (yield vs
  speed trade-off; the full scan already yields 27).
- **H4:** fix flow fetching (flow_fetch_count=0) so the orthogonal signal is live.
- Influencing factors: pool cap (80), selection metric (momentum vs liquidity), VI weighting,
  absence of a liquidity floor, value_traded weight, scan-speed budget, flow availability,
  prefilter→scanner liquidity contract mismatch.
- **Validate-first:** estimate H1 impact (how many liquid momentum names are displaced by junk),
  then A/B the prefilter (liquidity-floored vs current) on production-pick yield AND on whether the
  recovered picks perform forward (don't just add volume — add *good* volume).

---

## Step 3 — Architecture review: WHY Exception Leaders are feature-blind (intentional vs omission)
Status: ✅ judged — mostly intentional/correct; one omission already fixed in Step 1. No rip-out.
Phase: 0. Updated: 2026-06-15.

### Evidence (why designed this way)
- Exception Leaders are re-admitted from candidates the strict path REJECTED, specifically
  `KR_HARD_FILTER_FAIL` (failed the mechanical backtest filter) or
  `PRECISION_GATE_T3_LOW_ML_SUPPORT` (rejected for LOW ML support), gated by alpha≥45 / conviction≥58.
- The reject-detail snapshot (`reject_details_by_symbol`) is **stage-dependent**: early rejects
  carry almost nothing; late rejects carry scoring features (alpha/tech/whale/prob) but never
  `position`. So the detail captures *scoring* features, not price-derived *safety* context.

### Judgment (intentional vs error)
- **Bypass = intentional and validated.** It is the 주도주 하이패스 (PROJECT_HISTORY Phase 13):
  catch momentum leaders the mechanical/ML path wrongly rejects. The cohort gate (77.7%/+7.95%)
  proves it works. Do NOT redesign it away — that re-breaks a validated stream.
- **ML-feature gaps (expected_edge / phase25 / model_prob) = correct-by-design, NOT errors.**
  These candidates were admitted *because* they have low/no ML support; their ML scores are
  legitimately absent. Recomputing them is circular (the model already said no).
- **The one genuine legacy omission = price-derived SAFETY context (`position`)** dropped from the
  reject-detail snapshot. `position` is computable from price, so its absence disabled the peak
  guard for this stream. → **already fixed in Step 1** (reconstruct RSI/dist; guard the validated
  peak-chase combination).

### Redesign decision (best way for the goal, given the above)
- Do NOT rip out the bypass or try to re-inject ML scores. Preserve working, validated core.
- Formalize Step 1's reconstruction as **the designed Exception-Leader safety layer** (price-derived
  safety features reconstructed at collection, since ML features are absent by design).
- Optional, **validate-first** extensions (not bolted on): (a) restore `position`→loss_risk so its
  peak component fires for EL [marginal — Step 1's direct guard already covers the sharp risk];
  (b) volume-confirmation of the EL move (thin-volume fakeout filter). Each forward-validated before
  building. Alternative "fix at source" (add `position` to reject_details in scanner_services) is
  viable but higher blast-radius than reconstruction; reconstruction preferred.

---

## Step 2 — Full feature & guard-coverage audit
Status: ✅ audit done (map recorded; no new guard built — audits map, they don't change behavior)
Phase: 0. Updated: 2026-06-15.

### 데이터 (per-cohort fill-rate, KOSPI SWING: Exception Leader n=205 vs rest n=5908)
| Feature (guard it powers) | EL fill | rest fill | blind? |
|---|---:|---:|---|
| expected_edge_score / expected_return_1d,3d | 2.9% | 96% | ⛔ edge gate + edge promotion |
| phase25_prob / threshold | 3.4% | 74% | ⛔ ML/phase25 gates |
| position / tier | 2.0% | 53% | ⛔ peak guard (fixed in Step 1) |
| model_prob_mean / low_prob_high_score | 2.0% | 51% | ⛔ inverted-signal gate |
| relative_rank_pct / regime_adjusted_grade | 0% | 42% | ⛔ ranking/regime gate |
| **loss_risk_score** | **36.6%** | 43% | ⚠️ ~63% lack it; and it's degraded (below) |
| populated for EL | decision_score 97%, prob_clean 97%, alpha_score 97% | | |

### 용도 / 가드-coverage map
- **Exception Leaders bypass the planner gate stack entirely** — they are collected in a separate
  path (`_collect_exception_leaders_from_scanner_payload`), not the planner main loop, so
  `_apply_kr_market_mode_quality_gate` / `_apply_expected_edge_gate` / peak / inverted demotes
  never run on them.
- ML-feature gates are structurally inapplicable (features 2–4% populated).
- `compute_loss_risk_features` depends on `position/tech/whale/ml_prob` → for EL these are missing,
  so loss_risk is computed with **degraded inputs (is_peak/is_rising dead)** and only ~37% persisted.
- Net: EL per-candidate safety rests on **exception-admission thresholds (alpha/conviction/prob)
  + degraded loss_risk + (now) the reconstructed peak guard + the forward COHORT gate**. The
  cohort gate is the primary validator; most per-candidate ML guards don't apply by design.
- **Practical-80** is NOT a bypass stream — those candidates flow through the normal planner loop
  with full features, so they get the full gate stack + the practical gate. No blind spot there.

### 회고 (wrong assumptions corrected)
- Assumed the loss-risk hard cap protects Exception Leaders — it only partially does (37% + degraded).
- Assumed planner gates apply broadly — they do NOT touch the Exception Leader stream.

### 운영 / next (no build in this step — audit only)
- Per-candidate EL safety must come from **price-reconstructable** signals (ML features are absent
  by design). Peak done. Candidate future guards: volume-confirmation of the move, gap-up chase,
  liquidity — **each must be forward-validated before adding** (no eyeball filters).
- The cohort forward gate carries the safety load → **regime robustness is the dominant risk**
  (roadmap Phase 3 thread). Single-regime validation is the main caveat on everything here.
- Optional: reconstruct `position`/volume for EL so the existing loss_risk regains its peak
  component — candidate step, validate first.
