#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

python3 multi_agent/tools/update_realized_outcomes.py --limit-runs 200 "$@"
python3 multi_agent/tools/report_outcome_conversion.py --limit-runs 200
