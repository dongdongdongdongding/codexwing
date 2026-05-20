# Scanner Product Contract

Updated: 2026-05-19

This document fixes the operator-facing meaning of scanner sections, action
labels, probability fields, and the improvement loop. It is a product contract,
not a trading guarantee.

## Non-Negotiables

- Scanner candidates remain visible. The system should not hide a candidate
  only because a later planner/action label is cautious.
- Selection strength and buyability are separate. A strong candidate can still
  be expensive, late, illiquid, or blocked by flow/risk.
- Action labels are deterministic interpretations of stored fields and traces.
  They are not subjective suppression by the UI or by an agent.
- Top5, Exception Leader, Shadow, and radar sections have different jobs. They
  must not be merged into one confusing ranking without explicit validation.
- Model failures feed postmortem learning. Misses and losses are recorded,
  analyzed, converted into issues, and retested before promotion.

## Candidate Sections

| Section | Role | Operator Meaning |
|---|---|---|
| Top5 | production priority | Main production scanner output. This is the first section to inspect, but action labels and entry conditions still decide whether it is tradable. |
| Exception Leader | momentum exception stream | Strong out-of-rank momentum stream. It is not a Top5 replacement; it is a separate high-volatility observation and precision-analysis target. |
| Shadow | validated observer group | Generic grouping for gates under forward observation. Shadow rows do not change production ranking. |
| KOSDAQ Ordered Shadow | KOSDAQ ordered observer | KOSDAQ ordered rebound observer. It appears near the top for visibility, but remains shadow-only until validation says otherwise. |
| KOSDAQ Low-loss Shadow | KOSDAQ low-loss observer | KOSDAQ low-loss/theme observer focused on reducing loss tails. It is not the same gate as KOSDAQ Ordered Shadow. |
| KOSPI Shadow | KOSPI ordered observer | KOSPI ordered observer gate. It is tracked separately from Top5 and Exception Leader. |
| 별도 급등 레이더 | next-day surge radar | Separate next-day surge radar. It is shadow-only and does not replace Top5 or Exception Leader. |

## Action Labels

| Label | Meaning |
|---|---|
| 즉시 매수 가능 | Quality, upside room, entry timing, and risk filters are simultaneously favorable. |
| 조건부 매수 가능 | Candidate is valid only if the displayed Entry/TP/SL, support/rebreak, and flow conditions are respected. |
| 눌림 대기 | Candidate quality is acceptable, but price is late. Wait for support and recovery. |
| 돌파 확인 | Resistance breakout and volume retention must be confirmed before entry. |
| 눌림/확인 대기 | UI-short label for pullback support or rebreak confirmation before chasing. |
| 조건부 대기 | Some conditions are missing. Keep observing, but do not treat it as an active buy label. |
| 관망 | Direction or edge is unclear. The candidate remains visible with its reasons. |
| 매수 금지 | Overheat, flow exit, loss risk, or hard risk filters block new entry. |
| 스윙 제외 | Structural swing-trading exclusion such as offering risk, managed/watchlist status, persistent losses, audit risk, or clinical-bio event risk. |
| 급등 분리 관찰 | Exception Leader display label. Treat as a separate high-volatility observation stream with strict stop rules. |
| 별도 급등 관찰 | Radar label. It is pre-promotion, shadow-only observation. |
| 확인 필요 | Contract fallback. Review trace and data quality before interpreting it. |

## Entry Readiness Contract

Every recommendation-worthy candidate should carry `entry_readiness_contract_v1`
or an unavailable contract when price/flow data is missing. Required fields:

- `stock_quality_score`, `stock_quality_grade`
- `upside_room_score`, `upside_room_grade`
- `entry_timing_score`, `entry_timing_grade`
- `chase_risk_level`, `chase_risk_reasons`, `exclusion_risk_level`
- `final_action`, `action_reason_codes`
- `input_signals`, `missing_fields`, `warnings`
- `policy_version`

The contract is a traceable interpretation layer. It must not rewrite scanner
ranking unless a separate validated model promotion issue explicitly changes
the production scanner.

## Accuracy And Probability Sources

Accuracy should be shown from validated or outcome-linked sources:

- `phase25_oos_win_rate_pct`
- `phase25_prob_clean`
- `ml_prob`
- `segment_accuracy`
- `realized_expectancy_admission`
- `section_performance_calibration`
- `post_scan_outcome_ledger`

Do not present a raw model score as guaranteed win rate. When samples are small,
display sample size, date range, average/median return, best/worst return, and
loss-tail metrics alongside win rate.

## Data-Quality Warnings

- Do not fabricate missing prices, entry prices, stop prices, or flow values.
- Flow windows must be explicit. Same-day foreigner/institution/retail flow,
  3-day cumulative flow, and 10-day cumulative flow cannot be silently mixed.
- If same-day flow is missing, mark it missing and fall back only with a clear
  warning that the value is not same-day flow.
- If a candidate is selected from scanner output but Top Deep/archive save
  fails, this is a data-integrity bug, not a normal empty state.
- Every stored scan row should retain run ID, market, section, rank, action
  label, entry/stop condition, and outcome placeholder or linked outcome row.

## Improvement Loop

1. Scanner emits Top5, Exception Leader, Shadow, and radar candidates with
   section labels.
2. Top Deep builds the entry-readiness contract without hiding candidates.
3. Archive and Supabase/local stores persist scan rows, detail rows, and
   outcome placeholders.
4. Outcome jobs backfill 1D/3D/5D and loss-tail metrics.
5. Validation reports compare Top5, Exception Leader, and Shadow by market,
   horizon, average, median, best, worst, win rate, and stop/loss rate.
6. PM/postmortem analysis creates targeted beads issues for misses, data
   failures, and promotion candidates.
7. A new model or gate is promoted only after forward validation beats the
   current production baseline with enough sample size.

## Web And Discord Alignment

The Streamlit UI and Discord bot must use the same sections, action labels, and
run artifacts. Discord may compress the layout into embeds/buttons/select
menus, but the information content should match the web view:

- Top5, Exception Leader, Shadow, and radar section identity
- final action and reason codes
- entry condition and stop/exclusion condition
- quality/upside/timing grades
- chase/exclusion risk
- same-day and cumulative flow fields with missing-data warnings
- run ID, archive reference, and realized outcome status
