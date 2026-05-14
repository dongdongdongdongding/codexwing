#!/usr/bin/env python3
"""Record daily Shadow/Top5/Exception Leader return and win-rate snapshots."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.signal_section_performance import (
    DEFAULT_ARCHIVE_CSV,
    build_latest_performance_markdown,
    build_section_performance_metrics,
    load_archive_rows,
    write_daily_section_performance_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record daily KR signal-section performance snapshots.")
    parser.add_argument("--archive-csv", default=str(DEFAULT_ARCHIVE_CSV))
    parser.add_argument("--as-of-date", default="")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    rows = load_archive_rows(Path(args.archive_csv))
    metrics = build_section_performance_metrics(rows, as_of_date=args.as_of_date or None)
    paths = write_daily_section_performance_snapshot(metrics)
    payload = {"metrics": metrics, "paths": paths, "markdown": build_latest_performance_markdown(metrics)}
    if args.print_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["markdown"])
        print(json.dumps({"paths": paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
