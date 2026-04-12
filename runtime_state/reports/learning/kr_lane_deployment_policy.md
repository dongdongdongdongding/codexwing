# KR Lane Deployment Policy

- generated_at: 2026-04-10
- purpose: deploy trained lane champions only where full-archive validation supports live rerank use

## Active

- `kosdaq_explosive_1d`
  - deployment: `active`
  - activation guard: `feature_evidence >= 6` and `|prob_up - 50| >= 8pt`
  - archive activation count: `1033`
  - latest full-archive primary basket effect:
    - KOSDAQ top5 `avg 1D -1.38% -> -0.53%`
    - KOSDAQ top10 `avg 1D -0.82% -> +0.14%`
    - KOSDAQ top20 `avg 1D -0.01% -> +0.85%`

## Shadow

- `kospi_core_1d`
  - deployment: `shadow`
  - reason: strong holdout model, but not needed in current mixed KOSPI production basket

- `kospi_core_3d`
  - deployment: `shadow`
  - reason: excellent holdout result, but full-archive additive rerank did not improve KOSPI 3D enough to justify live override

- `kosdaq_core_3d`
  - deployment: `shadow`
  - reason: good research model, but KOSDAQ active lane is still `1d` and release gate for 3D primary promotion is not cleared

## Disabled

- `kosdaq_core_1d`
  - deployment: `disabled`
  - reason: weak holdout edge and weak full-archive separation

## Operating Principle

- do not let champion models override a lane unless they improve full-archive ranking behavior in the target live basket
- keep strong but not-yet-additive models in `shadow` for traceability and later re-promotion
- favor lane-specific deployment over global score replacement
