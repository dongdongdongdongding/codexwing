"""CLI: build and persist the US→KR theme transfer artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.theme_transfer import ARTIFACT_PATH, build_transfer_artifact, write_transfer_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Build US→KR theme_transfer artifact.")
    parser.add_argument("--archive-csv", type=str, default=None,
                        help="Archive CSV used to refine confidences (default: reports/archive path)")
    parser.add_argument("--out", type=str, default=str(ARTIFACT_PATH))
    parser.add_argument("--version", type=str, default=None)
    args = parser.parse_args()
    archive = Path(args.archive_csv) if args.archive_csv else None
    artifact = build_transfer_artifact(archive_csv=archive, version=args.version)
    out_path = write_transfer_artifact(artifact, Path(args.out))
    print(json.dumps({
        "path": str(out_path),
        "version": artifact["version"],
        "edge_count": len(artifact["edges"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
