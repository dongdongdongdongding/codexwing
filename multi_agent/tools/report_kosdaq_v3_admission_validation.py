#!/usr/bin/env python3
"""Write KOSDAQ v3 admission forward-validation metrics."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kosdaq_v3_admission_validation import (
    DEFAULT_ARCHIVE_CSV,
    DEFAULT_JSON_PATH,
    DEFAULT_MD_PATH,
    build_kosdaq_v3_admission_validation_markdown,
    build_kosdaq_v3_admission_validation_report,
    load_archive_rows,
    write_kosdaq_v3_admission_validation_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report KOSDAQ v3 admission realized-return validation.")
    parser.add_argument("--archive-csv", default=str(DEFAULT_ARCHIVE_CSV))
    parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH))
    parser.add_argument("--md-path", default=str(DEFAULT_MD_PATH))
    parser.add_argument("--as-of-date", default="")
    parser.add_argument("--min-matured-5d", type=int, default=30)
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    rows = load_archive_rows(Path(args.archive_csv))
    report = build_kosdaq_v3_admission_validation_report(
        rows,
        as_of_date=args.as_of_date or None,
        min_matured_5d=args.min_matured_5d,
    )
    paths = write_kosdaq_v3_admission_validation_report(
        report,
        json_path=Path(args.json_path),
        md_path=Path(args.md_path),
    )
    payload = {"report": report, "paths": paths}
    if args.print_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(build_kosdaq_v3_admission_validation_markdown(report))
        print(json.dumps({"paths": paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
