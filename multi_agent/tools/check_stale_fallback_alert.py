from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.workflows.alerts import emit_stale_fallback_alert


def main() -> None:
    parser = argparse.ArgumentParser(description="Check stale fallback pending rows and optionally send webhook alert.")
    parser.add_argument("--market", type=str, default="NASDAQ", help="Target market.")
    parser.add_argument("--shared-dir", type=str, default="runtime_state/shared_working", help="RUN-* root directory.")
    parser.add_argument("--threshold", type=int, default=3, help="Alert threshold for stale fallback pending count.")
    parser.add_argument("--limit-runs", type=int, default=200, help="Recent run window to inspect.")
    parser.add_argument("--webhook-url", type=str, default="", help="Webhook URL for alert dispatch.")
    parser.add_argument("--dry-run", action="store_true", help="Build payload only; do not POST webhook.")
    args = parser.parse_args()

    result = emit_stale_fallback_alert(
        shared_dir=Path(args.shared_dir),
        market=str(args.market),
        min_stale_count=int(args.threshold),
        webhook_url=str(args.webhook_url or ""),
        limit_runs=int(args.limit_runs),
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
