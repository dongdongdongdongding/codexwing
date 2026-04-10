from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.theme_catalog import build_stock_master_validation_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default="KR")
    args = parser.parse_args()

    report = build_stock_master_validation_report(args.market)
    out_dir = Path("runtime_state") / "reports" / "theme_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"kr_stock_theme_master_{str(args.market).lower()}"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# KR Stock Theme Master ({report['market']})",
        "",
        f"- source_path: {report['source_path']}",
        f"- records_loaded: {report['records_loaded']}",
        f"- market_counts: {report['market_counts']}",
        f"- inference_status_distribution: {report.get('inference_status_distribution', {})}",
        f"- rule_inferred_count: {report.get('rule_inferred_count', 0)}",
        f"- unclassified_count: {report['unclassified_count']}",
        f"- spac_excluded_count: {report['spac_excluded_count']}",
        f"- seed_conflict_count: {report['seed_conflict_count']}",
        "",
        "## Primary Theme Distribution",
    ]
    for theme_name, count in report.get("primary_theme_distribution", {}).items():
        lines.append(f"- {theme_name}: {count}")
    if report.get("seed_conflict_examples"):
        lines.extend(["", "## Seed Conflict Examples"])
        for row in report["seed_conflict_examples"][:10]:
            lines.append(
                f"- {row['ticker']} {row['stock_name']}: master={row['master_primary_theme']} / seed={row['seed_theme']}"
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(json_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
