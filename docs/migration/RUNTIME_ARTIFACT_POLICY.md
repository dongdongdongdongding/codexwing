# Runtime Artifact Policy

## Purpose

`runtime_state/` is operational state, not source code. It contains scan runs,
context caches, generated reports, model validation output, and local artifacts
that can quickly dominate repository size and make review/rebase unsafe.

## Tracking Rules

- Source code, schemas, tools, and small hand-curated fixtures may be tracked.
- Generated run directories under `runtime_state/shared_working/` are not tracked.
- Cache and append-only operational logs under `runtime_state/long_term/` are not tracked.
- Daily, archive, smoke, data-health, and instrument-master reports are not tracked.
- Validation and learning reports are tracked only when they are explicit release
  evidence or small curated summaries.
- Large model binaries remain ignored under `models/*.pkl`; model metadata should
  be captured in JSON/Markdown reports.

## Current Baseline

Measured on 2026-05-06:

- `runtime_state/` size: 479 MB
- tracked `runtime_state` files: 4,164

This is above the desired repository hygiene threshold. The `.gitignore` now
blocks future bulk runtime artifacts, but files already in the git index require
an explicit index-prune change (`git rm --cached ...`) in a git-enabled cleanup
session.

## Curated Evidence

When preserving evidence for planning or release review, prefer:

- one JSON summary with machine-readable metrics
- one Markdown summary with human-readable interpretation
- links or identifiers for external artifact storage
- explicit generated timestamp, source command, and data window

Do not preserve whole run directories unless a failure investigation requires
that exact artifact tree.
