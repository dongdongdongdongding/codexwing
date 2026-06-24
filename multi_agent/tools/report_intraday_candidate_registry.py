#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.intraday_candidate_registry import (  # noqa: E402
    DEFAULT_JSON_PATH,
    DEFAULT_MD_PATH,
    build_intraday_candidate_registry,
    write_intraday_candidate_registry,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write INTRADAY-only candidate registry artifacts.")
    parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH))
    parser.add_argument("--md-path", default=str(DEFAULT_MD_PATH))
    args = parser.parse_args()

    report = build_intraday_candidate_registry()
    paths = write_intraday_candidate_registry(
        report,
        json_path=Path(args.json_path),
        md_path=Path(args.md_path),
    )
    print(f"Wrote {paths['json']}")
    print(f"Wrote {paths['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
