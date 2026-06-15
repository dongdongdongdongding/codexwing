# Research Log — performance roadmap execution

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

## Step 2 — Full feature & guard-coverage audit (planned)
Status: ⏸ planned. Map all scan features × per-cohort fill-rate, and which guard fires on which
stream (so no other guard is silently blind like the peak guard was). Loop fields to be filled
when started.
