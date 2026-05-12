# Runtime Artifact Policy

## Purpose

`runtime_state/` is operational state, not source code. It contains scan runs,
context caches, generated reports, model validation output, and local artifacts
that can quickly dominate repository size and make review/rebase unsafe.

## Tracking Rules

- Source code, schemas, tools, and small hand-curated fixtures may be tracked.
- Generated run directories under `runtime_state/shared_working/` are not tracked.
- Context caches, instrument master caches, theme membership caches, and local
  retrain trigger/smoke state under `runtime_state/long_term/` are not tracked.
- Selected append-only long-term summary logs may be tracked when they provide
  compact audit evidence (`outcome_health`, `postmortems`,
  `profile_diagnostics`, `tickets`) and remain small enough for review.
- Daily, archive, smoke, data-quality, data-health, top-deep, and
  instrument-master reports are not tracked by default.
- Validation and learning reports are tracked only when they are explicit release
  evidence or small curated summaries.
- Trading reports are tracked only when they summarize paper-trade ledger output
  for operator review.
- Large model binaries remain ignored under `models/*.pkl`; model metadata should
  be captured in JSON/Markdown reports.

## Current Baseline

Measured on 2026-05-06 before cleanup:

- `runtime_state/` size: 479 MB
- tracked `runtime_state` files: 4,164

Post-cleanup status on 2026-05-13:

- generated run artifacts were removed from the Git index with `git rm --cached`
- local files were preserved on disk
- tracked `runtime_state` files were reduced to 515
- `.gitignore` now blocks future bulk artifacts, including shared working runs,
  artifact bundles, context caches, instrument/theme caches, archive datasets,
  top-deep per-run reports, and data-quality dumps

## Curated Evidence

When preserving evidence for planning or release review, prefer:

- one JSON summary with machine-readable metrics
- one Markdown summary with human-readable interpretation
- links or identifiers for external artifact storage
- explicit generated timestamp, source command, and data window

Do not preserve whole run directories unless a failure investigation requires
that exact artifact tree.
