#!/usr/bin/env python3
"""Write the daily KOSDAQ ordered rebound shadow observer report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kosdaq_shadow_observer import (
    DEFAULT_JSON_PATH,
    DEFAULT_MD_PATH,
    DEFAULT_SOURCE_CSV,
    PromotionGuardrails,
    build_kosdaq_shadow_observer_markdown,
    build_kosdaq_shadow_observer_report,
    load_observer_rows,
    write_kosdaq_shadow_observer_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report KOSDAQ ordered rebound shadow observer metrics.")
    parser.add_argument("--source-csv", default=str(DEFAULT_SOURCE_CSV))
    parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH))
    parser.add_argument("--md-path", default=str(DEFAULT_MD_PATH))
    parser.add_argument("--as-of-date", default="")
    parser.add_argument("--min-ready-n", type=int, default=50)
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    rows = load_observer_rows(Path(args.source_csv))
    report = build_kosdaq_shadow_observer_report(
        rows,
        as_of_date=args.as_of_date or None,
        guardrails=PromotionGuardrails(min_ready_n=args.min_ready_n),
    )
    paths = write_kosdaq_shadow_observer_report(
        report,
        json_path=Path(args.json_path),
        md_path=Path(args.md_path),
    )
    payload = {"report": report, "paths": paths}
    if args.print_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(build_kosdaq_shadow_observer_markdown(report))
        print(json.dumps({"paths": paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
