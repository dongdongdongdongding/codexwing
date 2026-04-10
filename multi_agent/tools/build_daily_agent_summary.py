from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.workflows.daily_summary import build_daily_summary, write_daily_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily multi-agent summary (JSON + Markdown).")
    parser.add_argument("--date", type=str, default=date.today().isoformat(), help="Target date (YYYY-MM-DD).")
    parser.add_argument(
        "--shared-dir",
        type=str,
        default="runtime_state/shared_working",
        help="Directory containing RUN-* handoff folders.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="runtime_state/reports/daily",
        help="Output directory for daily summary artifacts.",
    )
    parser.add_argument("--market", type=str, default=None, help="Optional market filter (e.g., NASDAQ).")
    parser.add_argument("--limit-runs", type=int, default=0, help="Optional latest run limit before date filtering.")
    args = parser.parse_args()

    summary = build_daily_summary(
        shared_dir=Path(args.shared_dir),
        target_date=str(args.date),
        market=args.market,
        limit_runs=int(args.limit_runs),
    )
    paths = write_daily_summary(
        summary=summary,
        output_dir=Path(args.output_dir),
        target_date=str(args.date),
        market=args.market,
    )
    print(
        json.dumps(
            {
                "summary_paths": paths,
                "headline": {
                    "target_date": summary.get("target_date"),
                    "total_runs": summary.get("total_runs"),
                    "outcomes": summary.get("outcomes", {}),
                    "top_warning_codes": summary.get("top_warning_codes", []),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
