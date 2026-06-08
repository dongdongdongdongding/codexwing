#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_ticker_valuechain_master import (  # noqa: E402
    TICKER_VALUECHAIN_MASTER_PATH,
    TICKER_VALUECHAIN_REPORT_DIR,
    TICKER_VALUECHAIN_SOURCE_PATH,
    build_ticker_valuechain_master,
    load_verified_valuechain_sources,
    write_ticker_valuechain_master,
)
from modules.kis_theme_valuechain import VALUECHAIN_CONFIDENCE_FLOOR  # noqa: E402


def _write_markdown(path: Path, payload: Mapping[str, Any], *, source_path: Path) -> Path:
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    refresh = payload.get("refresh_policy") if isinstance(payload.get("refresh_policy"), Mapping) else {}
    lines = [
        "# KIS Ticker Value-Chain Master",
        "",
        f"- version: `{payload.get('version')}`",
        f"- generated_at: `{payload.get('generated_at')}`",
        f"- source_path: `{source_path}`",
        f"- ticker_profiles: `{summary.get('ticker_profiles', 0)}`",
        f"- verified_edges: `{summary.get('verified_edges', 0)}`",
        f"- blocked_edges: `{summary.get('blocked_edges', 0)}`",
        f"- refresh_cadence_days: `{refresh.get('refresh_cadence_days', 90)}`",
        f"- production_requires_official_evidence: `{refresh.get('production_requires_official_evidence')}`",
        "",
        "## Role Distribution",
        "",
    ]
    roles = summary.get("role_distribution") if isinstance(summary.get("role_distribution"), Mapping) else {}
    lines.extend([f"- {role}: `{count}`" for role, count in sorted(roles.items())] or ["- none"])
    lines.extend(["", "## Profiles", ""])
    for profile in payload.get("ticker_profiles") or []:
        if not isinstance(profile, Mapping):
            continue
        lines.append(
            f"- {profile.get('ticker')} {profile.get('stock_name')}: "
            f"roles=`{','.join(profile.get('valuechain_roles') or [])}` "
            f"upstream=`{','.join(profile.get('upstream_symbols') or []) or '-'}` "
            f"downstream=`{','.join(profile.get('downstream_symbols') or []) or '-'}`"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the slow-changing ticker-level KIS value-chain master.")
    parser.add_argument("--source-json", type=str, default=str(TICKER_VALUECHAIN_SOURCE_PATH))
    parser.add_argument("--output-json", type=str, default=str(TICKER_VALUECHAIN_MASTER_PATH))
    parser.add_argument("--output-md", type=str, default=str(TICKER_VALUECHAIN_REPORT_DIR / "master.md"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_path = PROJECT_ROOT / args.source_json
    sources = load_verified_valuechain_sources(source_path)
    payload = build_ticker_valuechain_master(sources, confidence_floor=VALUECHAIN_CONFIDENCE_FLOOR)
    output_json = PROJECT_ROOT / args.output_json
    output_md = PROJECT_ROOT / args.output_md
    if not args.dry_run:
        write_ticker_valuechain_master(payload, output_json)
        _write_markdown(output_md, payload, source_path=source_path)
    summary = dict(payload.get("summary") or {})
    summary.update(
        {
            "output_json": str(output_json),
            "output_md": str(output_md),
            "source_path": str(source_path),
            "warnings": [] if summary.get("verified_edges", 0) else ["ticker_valuechain_master_has_no_verified_edges"],
        }
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
