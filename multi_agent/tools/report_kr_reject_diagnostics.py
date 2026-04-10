from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _iter_runs(artifacts_dir: Path, limit_runs: int) -> List[Path]:
    runs = [p for p in artifacts_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
    runs = sorted(runs, key=lambda p: p.name)
    if limit_runs > 0:
        runs = runs[-limit_runs:]
    return runs


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def build_report(artifacts_dir: Path, market: str, limit_runs: int) -> Dict[str, Any]:
    market_filter = str(market).upper()
    reason_totals: Dict[str, int] = {}
    rows: List[Dict[str, Any]] = []

    for run_dir in _iter_runs(artifacts_dir, limit_runs):
        path = run_dir / "scan_pipeline_summary.json"
        if not path.exists():
            continue
        payload = _load_json(path)
        if str(payload.get("market", "")).upper() != market_filter:
            continue
        reject_counts = payload.get("reject_reason_counts", {})
        if not isinstance(reject_counts, dict):
            reject_counts = {}
        total_scans = _safe_int(payload.get("total_scans"))
        result_count = _safe_int(payload.get("result_count"))
        filtered_count = _safe_int(payload.get("filtered_count"))
        sorted_reasons = sorted(
            ((str(k), _safe_int(v)) for k, v in reject_counts.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        for reason, count in sorted_reasons:
            reason_totals[reason] = _safe_int(reason_totals.get(reason)) + count
        rows.append(
            {
                "run_id": str(payload.get("run_id", run_dir.name)),
                "execution_profile": str(payload.get("execution_profile", "unknown")),
                "total_scans": total_scans,
                "result_count": result_count,
                "filtered_count": filtered_count,
                "top_reject_reasons": sorted_reasons[:5],
                "warnings": payload.get("warnings", []),
            }
        )

    sorted_totals = sorted(reason_totals.items(), key=lambda x: x[1], reverse=True)
    return {
        "market": market_filter,
        "runs_included": len(rows),
        "top_reject_reasons_across_runs": sorted_totals[:10],
        "run_breakdown": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report KR scanner reject diagnostics across runs.")
    parser.add_argument("--artifacts-dir", type=str, default="runtime_state/artifacts")
    parser.add_argument("--market", type=str, default="KOSDAQ", choices=["KOSDAQ", "KOSPI"])
    parser.add_argument("--limit-runs", type=int, default=50)
    args = parser.parse_args()

    report = build_report(
        artifacts_dir=Path(args.artifacts_dir),
        market=args.market,
        limit_runs=int(args.limit_runs),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
