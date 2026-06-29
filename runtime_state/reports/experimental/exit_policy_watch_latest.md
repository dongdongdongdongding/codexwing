# Exit Policy Watch

- generated_at: `2026-06-29T08:41:26.522843+00:00`
- report_version: `exit_policy_watch_v1`
- optimizer_generated_at: `2026-06-29T08:41:26.403983+00:00`
- friction_pct: `0.35`
- watch_count: `0`
- blocked_path_warning_count: `0`
- ready_review_count: `0`

## Watch Rows

| Rank | State | Market | Cohort | Label | Model | TopN | N | Days | Target | Stop | Exit Win | Net Exit Avg | Exit Min | Close Avg5 | Close Min5 | Stop First | Path Warn | Failed Checks |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

## Blocked By Path Warning

| Rank | Market | Cohort | Label | Model | TopN | N | Days | Exit Win | Net Exit Avg | Path Warn | Failed Checks |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|

## Baselines

## Notes
- EXIT-WATCH is not a production scanner replacement.
- Close-hold failures remain visible through failed_checks and close_avg/min fields.
- Net exit average subtracts configured friction_pct for fees/slippage/tax approximation.
