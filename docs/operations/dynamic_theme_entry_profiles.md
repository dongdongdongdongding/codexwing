# Dynamic Theme Entry Profiles

The practical 80% entry gate must not depend on fixed theme names. Themes rotate,
so the system now builds a daily profile from accumulated scan archive outcomes.

## Flow

1. `multi_agent/tools/report_dynamic_theme_entry_profiles.py` reads
   `runtime_state/reports/archive/scan_archive_learning_dataset_all.csv`.
2. It groups Korean swing candidates by market and `primary_theme`.
3. For each theme it mines scan-time condition slices such as `prob_clean>=50`,
   `decision_score>=95`, `trend==NEUTRAL`, or two-condition combinations.
4. A profile is selected only when the slice has enough realized outcomes and
   meets 5D win, practical-win, drawdown-path, and average-return gates.
5. `modules/practical_entry_gate.py` reads
   `runtime_state/reports/validation/dynamic_theme_entry_profiles.json` at
   runtime and evaluates only fields available at scan time.

## Runtime Rule

The gate passes a row only when:

- its market and `primary_theme` match a currently selected dynamic profile
- required trend and numeric thresholds in that profile are satisfied
- `loss_risk_score` does not exceed the profile risk limit, when present

Outcome fields such as `return_5d_pct`, `max_high_return_5d_pct`, and
`min_return_observed_pct` are labels for validation only and are not used by the
runtime gate.

## Daily Ops

`multi_agent/tools/run_daily_ops.sh` refreshes dynamic theme profiles before
`report_scan_cohort_performance.py`, so the cohort report measures the current
practical gate alongside Top1, Top5, and Exception Leader.
