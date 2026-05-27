# Significant Feature Combination Mining

- generated_at: `2026-05-27T11:32:59.169368+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `4298`
- mined_combinations: `0`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `0`
- candidate features: `{'numeric': 0, 'categorical': 0, 'total': 0}`
- predicates: `{}`
- predicate support screen: `{}`
- result counts: `{}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
