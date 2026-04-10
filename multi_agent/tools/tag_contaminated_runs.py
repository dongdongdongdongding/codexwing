#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager
from multi_agent.workflows.run_quality import detect_market_gate_quality


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Tag contaminated runs caused by old market gate mismatches.")
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--limit-runs", type=int, default=300)
    parser.add_argument("--market", default=None)
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    args = parser.parse_args()

    shared_dir = Path(args.shared_dir)
    run_dirs = sorted([p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")], key=lambda p: p.name)
    if args.limit_runs > 0:
        run_dirs = run_dirs[-int(args.limit_runs):]
    market_filter = str(args.market or "").upper().strip()

    db = DBManager()
    rows: List[Dict[str, Any]] = []
    contaminated = 0
    synced = 0
    for run_dir in run_dirs:
        scanner_path = run_dir / "scanner_handoff.json"
        if not scanner_path.exists():
            continue
        scanner_payload = _load_json(scanner_path)
        if not scanner_payload:
            continue
        run_market = str((scanner_payload.get("run_context") or {}).get("market") or "").upper()
        if market_filter and run_market != market_filter:
            continue
        quality = detect_market_gate_quality(scanner_payload)
        quality["run_id"] = run_dir.name
        rows.append(quality)
        if quality.get("validation_excluded"):
            contaminated += 1
        if quality.get("quality_flags"):
            ok = db.update_run_quality_flags(
                run_id=run_dir.name,
                market=run_market,
                quality_flags=quality.get("quality_flags"),
                validation_excluded=bool(quality.get("validation_excluded")),
            )
            if ok:
                synced += 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_filter": market_filter or None,
        "runs_considered": len(rows),
        "contaminated_runs": contaminated,
        "db_synced_runs": synced,
        "runs": rows,
    }
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = market_filter.lower() if market_filter else "all"
    json_path = out_dir / f"contaminated_runs_{suffix}.json"
    md_path = out_dir / f"contaminated_runs_{suffix}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Contaminated Runs ({suffix.upper()})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- runs_considered: {report['runs_considered']}",
        f"- contaminated_runs: {report['contaminated_runs']}",
        f"- db_synced_runs: {report['db_synced_runs']}",
        "",
        "## Runs",
    ]
    for row in rows:
        flags = row.get("quality_flags") or []
        if not flags:
            continue
        lines.append(f"- {row.get('run_id')}: market={row.get('market')} flags={flags}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "contaminated_runs": contaminated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

