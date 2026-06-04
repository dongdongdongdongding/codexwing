# KIS Consumer Parity Report

## Summary
- promotion_ready: `False`
- dummy_policy: No dummy, synthetic, or fabricated KIS data is allowed. Missing KIS values must stay missing with warnings.
- scanner_candidate_count: `4`
- scanner_sidecar_candidate_count: `4`
- scanner_sidecar_model_ready_candidate_count: `4`
- scanner_sidecar_production_ready_candidate_count: `0`
- scanner_sidecar_coverage_pct: `100.0`
- error_count: `0`
- warning_count: `1`

## DB Contract
- mapped_fields: `['feature_snapshot', 'leader_metrics']`
- local_schema_extensions: `['feature_snapshot', 'leader_metrics']`
- payload_preserves_feature_snapshot: `True`
- payload_preserves_leader_metrics: `True`

## Issues
- `warning` `KIS_PRODUCTION_REPLACEMENT_NOT_READY` 
