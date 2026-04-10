#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.workflows.outcome_buckets import MEASURED_OUTCOME_BUCKETS, resolve_outcome_bucket
from multi_agent.workflows.run_quality import detect_market_gate_quality

HORIZONS = ["1d", "3d", "5d", "7d"]


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _metric(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"samples": 0, "n": 0, "avg_return_pct": 0.0, "win_rate_pct": 0.0}
    wins = sum(1 for v in values if v > 0)
    return {
        "samples": int(len(values)),
        "n": int(len(values)),
        "avg_return_pct": round(sum(values) / len(values), 4),
        "win_rate_pct": round(wins / len(values) * 100.0, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily prediction validation by market and decision bucket.")
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--market", default=None)
    parser.add_argument("--limit-runs", type=int, default=300)
    parser.add_argument("--include-contaminated", action="store_true")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    args = parser.parse_args()

    shared_dir = Path(args.shared_dir)
    run_dirs = sorted([p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")], key=lambda p: p.name)
    if args.limit_runs > 0:
        run_dirs = run_dirs[-int(args.limit_runs):]
    market_filter = str(args.market or "").upper().strip()

    rows_considered = 0
    excluded_runs: List[str] = []
    metrics: Dict[str, Dict[str, List[float]]] = {bucket: {h: [] for h in HORIZONS} for bucket in MEASURED_OUTCOME_BUCKETS}
    market_rows = 0
    for run_dir in run_dirs:
        scanner_payload = _load_json(run_dir / "scanner_handoff.json")
        outcomes_payload = _load_json(run_dir / "realized_outcomes.json")
        if not scanner_payload or not outcomes_payload:
            continue
        run_market = str((scanner_payload.get("run_context") or {}).get("market") or "").upper()
        if market_filter and run_market != market_filter:
            continue
        quality = detect_market_gate_quality(scanner_payload)
        if quality.get("validation_excluded") and not args.include_contaminated:
            excluded_runs.append(run_dir.name)
            continue
        outcomes = outcomes_payload.get("outcomes", [])
        if not isinstance(outcomes, list):
            continue
        market_rows += len(outcomes)
        rows_considered += 1
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            bucket = resolve_outcome_bucket(row)
            if bucket not in MEASURED_OUTCOME_BUCKETS:
                continue
            for horizon in HORIZONS:
                key = f"return_{horizon}_pct"
                value = row.get(key)
                if value is None or value == "":
                    continue
                try:
                    metrics[bucket][horizon].append(float(value))
                except Exception:
                    continue

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": market_filter or None,
        "runs_considered": rows_considered,
        "rows_considered": market_rows,
        "excluded_runs": excluded_runs,
        "buckets": {
            bucket: {horizon: _metric(values) for horizon, values in horizon_map.items()}
            for bucket, horizon_map in metrics.items()
        },
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = market_filter.lower() if market_filter else "all"
    json_path = out_dir / f"prediction_validation_{suffix}.json"
    md_path = out_dir / f"prediction_validation_{suffix}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Prediction Validation ({suffix.upper()})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- runs_considered: {report['runs_considered']}",
        f"- rows_considered: {report['rows_considered']}",
        f"- excluded_runs: {len(excluded_runs)}",
        "",
        "## Buckets",
    ]
    for bucket in MEASURED_OUTCOME_BUCKETS:
        lines.append(f"- {bucket}:")
        for horizon in HORIZONS:
            block = report["buckets"][bucket][horizon]
            lines.append(
                f"  - {horizon}: n={block['samples']} avg={block['avg_return_pct']:+.2f}% win={block['win_rate_pct']:.1f}%"
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "excluded_runs": len(excluded_runs)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
