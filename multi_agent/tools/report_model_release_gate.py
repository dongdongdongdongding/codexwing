#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.model_governance import build_policy_release_report_from_payload, write_policy_release_report


DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build champion-challenger scanner/model release gate report.")
    parser.add_argument("--input-json", required=True, help="JSON spec containing champion_metrics and challenger_metrics.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--stem", default="kr_model_release_gate")
    parser.add_argument("--fail-on-reject", action="store_true")
    args = parser.parse_args()

    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    report = build_policy_release_report_from_payload(payload)
    paths = write_policy_release_report(report, Path(args.output_dir), stem=str(args.stem))
    print(
        json.dumps(
            {
                **paths,
                "release_ready": report["release_ready"],
                "promotion_status": report["promotion_status"],
                "failed_checks": [row for row in report.get("all_checks", []) if not row.get("passed")],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.fail_on_reject and not report["release_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
