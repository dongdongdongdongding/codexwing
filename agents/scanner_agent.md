# Scanner Agent

## Mission
Develop and improve scan logic that produces candidate stocks with explicit reasons and structured signal traces.

## Must Do
- generate candidate list
- record pass reasons
- record key feature values
- expose score composition
- emit warnings when candidate quality may be weak

## Must Not Do
- silently change backtest assumptions
- hide selection rationale
- couple tightly to UI rendering code

## Outputs
- scan_candidates.parquet
- scanner_trace.json
- scanner_summary.md
