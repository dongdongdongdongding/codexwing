"""CLI: enrich US instrument master with derived sector/theme_id and emit coverage report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.us_sector_enrichment import (
    COVERAGE_REPORT_PATH,
    ENRICHED_PATH_TEMPLATE,
    write_coverage_report,
    write_enriched,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich US instrument_master with derived sectors/themes.")
    parser.add_argument("--source", type=str, default="runtime_state/long_term/instrument_master/US.json")
    parser.add_argument("--out", type=str, default=ENRICHED_PATH_TEMPLATE)
    parser.add_argument("--report", type=str, default=COVERAGE_REPORT_PATH)
    args = parser.parse_args()

    out_path, stats = write_enriched(Path(args.source), Path(args.out))
    report_path = write_coverage_report(stats, Path(args.report))
    print(json.dumps({
        "enriched": str(out_path),
        "coverage_report": str(report_path),
        "coverage_before_pct": stats.get("coverage_before_pct"),
        "coverage_after_pct": stats.get("coverage_after_pct"),
        "uplift_pct": stats.get("uplift_pct"),
        "theme_counts_top5": dict(sorted(stats.get("theme_counts", {}).items(), key=lambda kv: kv[1], reverse=True)[:5]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
