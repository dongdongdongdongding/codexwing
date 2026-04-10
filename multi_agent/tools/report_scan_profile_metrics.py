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


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def build_report(artifacts_dir: Path, limit_runs: int, market: str | None) -> Dict[str, Any]:
    runs = _iter_runs(artifacts_dir, limit_runs)
    market_filter = str(market or "").strip().upper()
    rows: List[Dict[str, Any]] = []
    grouped: Dict[str, Dict[str, Any]] = {}

    for run_dir in runs:
        summary_path = run_dir / "scan_pipeline_summary.json"
        if not summary_path.exists():
            continue
        payload = _load_json(summary_path)
        run_market = str(payload.get("market", "")).upper()
        if market_filter and run_market != market_filter:
            continue

        run_id = str(payload.get("run_id", run_dir.name))
        profile = str(payload.get("execution_profile", "unknown")).lower()
        total_scans = _safe_int(payload.get("total_scans"))
        result_count = _safe_int(payload.get("result_count"))
        filtered_count = _safe_int(payload.get("filtered_count"))
        pass_rate_pct = round((result_count / total_scans * 100.0), 2) if total_scans > 0 else 0.0
        filtered_rate_pct = round((filtered_count / total_scans * 100.0), 2) if total_scans > 0 else 0.0
        reject_reason_counts = payload.get("reject_reason_counts", {})
        if not isinstance(reject_reason_counts, dict):
            reject_reason_counts = {}

        row = {
            "run_id": run_id,
            "market": run_market,
            "profile": profile,
            "total_scans": total_scans,
            "result_count": result_count,
            "filtered_count": filtered_count,
            "pass_rate_pct": pass_rate_pct,
            "filtered_rate_pct": filtered_rate_pct,
            "reject_reason_counts": reject_reason_counts,
        }
        rows.append(row)

        bucket = grouped.setdefault(
            profile,
            {
                "profile": profile,
                "runs": 0,
                "total_scans": 0,
                "total_results": 0,
                "total_filtered": 0,
                "sum_pass_rate_pct": 0.0,
                "sum_filtered_rate_pct": 0.0,
                "reject_reason_counts": {},
            },
        )
        bucket["runs"] += 1
        bucket["total_scans"] += total_scans
        bucket["total_results"] += result_count
        bucket["total_filtered"] += filtered_count
        bucket["sum_pass_rate_pct"] += pass_rate_pct
        bucket["sum_filtered_rate_pct"] += filtered_rate_pct
        rr = bucket["reject_reason_counts"]
        for reason, count in reject_reason_counts.items():
            rr[reason] = _safe_int(rr.get(reason)) + _safe_int(count)

    profile_summary: List[Dict[str, Any]] = []
    for profile in sorted(grouped.keys()):
        bucket = grouped[profile]
        runs_count = _safe_int(bucket["runs"])
        total_scans = _safe_int(bucket["total_scans"])
        total_results = _safe_int(bucket["total_results"])
        total_filtered = _safe_int(bucket["total_filtered"])
        avg_pass_rate = round(_safe_float(bucket["sum_pass_rate_pct"]) / runs_count, 2) if runs_count > 0 else 0.0
        avg_filtered_rate = round(_safe_float(bucket["sum_filtered_rate_pct"]) / runs_count, 2) if runs_count > 0 else 0.0
        weighted_pass_rate = round((total_results / total_scans * 100.0), 2) if total_scans > 0 else 0.0
        weighted_filtered_rate = round((total_filtered / total_scans * 100.0), 2) if total_scans > 0 else 0.0
        top_reject_reasons = sorted(
            bucket["reject_reason_counts"].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        profile_summary.append(
            {
                "profile": profile,
                "runs": runs_count,
                "total_scans": total_scans,
                "total_results": total_results,
                "total_filtered": total_filtered,
                "avg_pass_rate_pct": avg_pass_rate,
                "avg_filtered_rate_pct": avg_filtered_rate,
                "weighted_pass_rate_pct": weighted_pass_rate,
                "weighted_filtered_rate_pct": weighted_filtered_rate,
                "top_reject_reasons": top_reject_reasons,
            }
        )

    return {
        "artifacts_dir": str(artifacts_dir),
        "market_filter": market_filter or None,
        "runs_scanned": len(runs),
        "runs_included": len(rows),
        "profile_summary": profile_summary,
        "run_breakdown": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report scan pass/filter diagnostics by execution profile.")
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default="runtime_state/artifacts",
        help="Artifacts directory containing RUN-* folders with scan_pipeline_summary.json.",
    )
    parser.add_argument(
        "--limit-runs",
        type=int,
        default=200,
        help="Limit number of latest runs to scan.",
    )
    parser.add_argument(
        "--market",
        type=str,
        default=None,
        help="Optional market filter (e.g., NASDAQ, KOSPI).",
    )
    args = parser.parse_args()

    report = build_report(
        artifacts_dir=Path(args.artifacts_dir),
        limit_runs=int(args.limit_runs),
        market=args.market,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

