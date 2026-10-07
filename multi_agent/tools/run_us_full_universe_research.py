#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules import quant_analysis
from modules.scanner_services import resolve_strategy_family
from multi_agent.workflows.non_ui_scan_pipeline import run_non_ui_scan_pipeline


def _chunk(items: List[str], size: int) -> List[List[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as fh:
        temporary = Path(fh.name)
        try:
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def summarize_health(summaries, universe_size, batch_count, failure=None):
    """Runtime error_count already includes worker and executor failures."""
    total_errors = 0
    mismatches = []
    for item in summaries:
        diagnostics = int(item.get("worker_error_count", 0) or 0) + int(item.get("executor_exception_count", 0) or 0)
        errors = int(item.get("error_count", diagnostics) or 0)
        total_errors += max(errors, diagnostics)
        if errors != diagnostics:
            mismatches.append(item.get("run_id"))
    scans = sum(int(item.get("total_scans", 0) or 0) for item in summaries)
    incomplete = len(summaries) != batch_count or scans != universe_size
    status = "failed" if failure else ("degraded" if total_errors or incomplete or mismatches else "ok")
    return {"status": status, "exit_code": 0 if status == "ok" else 2,
            "total_errors": total_errors, "completed_batch_count": len(summaries),
            "scan_coverage_complete": not incomplete, "error_count_mismatch_run_ids": mismatches,
            "batch_failure": failure}


def _write_md(path: Path, report: Dict[str, Any]) -> None:
    lines = [
        f"# US Full Universe Research ({report.get('market')})",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- status: {report.get('status')}",
        f"- market: {report.get('market')}",
        f"- strategy_family: {report.get('strategy_family')}",
        f"- scan_mode: {report.get('scan_mode')}",
        f"- universe_size: {report.get('universe_size')}",
        f"- batches: {report.get('batch_count')}",
        f"- total_scans: {report.get('total_scans')}",
        f"- total_results: {report.get('total_results')}",
        f"- total_filtered: {report.get('total_filtered')}",
        f"- total_errors: {report.get('total_errors')}",
        "",
        "## Top Reject Reasons",
    ]
    reject_reason_counts = report.get("reject_reason_counts", {})
    if isinstance(reject_reason_counts, dict) and reject_reason_counts:
        for key, value in sorted(reject_reason_counts.items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full-universe research scan for NASDAQ or AMEX in batches.")
    parser.add_argument("--market", choices=["NASDAQ", "AMEX"], required=True)
    parser.add_argument("--profile", default="prod")
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--scan-mode", choices=["SWING", "INTRADAY"], default="SWING")
    parser.add_argument("--advanced-engine", action="store_true")
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--limit-tickers", type=int, default=0)
    parser.add_argument("--force-macro-refresh", action="store_true")
    parser.add_argument("--strategy-version", default="us-research-v1")
    parser.add_argument("--model-version", default="research-baseline")
    parser.add_argument("--code-version", default="orchestrated-us-research")
    parser.add_argument("--output-dir", default="runtime_state/reports/us_research")
    args = parser.parse_args()

    ticker_map = quant_analysis.QuantStrategy.get_market_tickers(args.market)
    tickers = list(ticker_map.keys())
    if args.limit_tickers and args.limit_tickers > 0:
        tickers = tickers[: int(args.limit_tickers)]
    if not tickers:
        raise SystemExit(f"No tickers fetched for market={args.market}")

    batch_size = max(1, int(args.batch_size))
    batches = _chunk(tickers, batch_size)
    summaries: List[Dict[str, Any]] = []
    reject_reason_counts: Dict[str, int] = {}
    total_scans = 0
    total_results = 0
    total_filtered = 0
    failure = None

    for idx, batch in enumerate(batches, start=1):
        print(f"[BATCH {idx}/{len(batches)}] market={args.market} tickers={len(batch)}")
        try:
            summary = run_non_ui_scan_pipeline(
                market=args.market,
                profile=str(args.profile),
                max_scan=len(batch),
                max_workers=int(args.max_workers),
                is_advanced_engine=bool(args.advanced_engine),
                max_retries=int(args.max_retries),
                tickers=",".join(batch),
                force_macro_refresh=bool(args.force_macro_refresh and idx == 1),
                strategy_version=str(args.strategy_version),
                model_version=str(args.model_version),
                code_version=str(args.code_version),
                scan_mode=str(args.scan_mode).upper(),
            )
        except Exception as exc:
            failure = {"batch_index": idx, "ticker_count": len(batch), "error_type": type(exc).__name__}
            break
        summaries.append(summary)
        total_scans += int(summary.get("total_scans", 0) or 0)
        total_results += int(summary.get("result_count", 0) or 0)
        total_filtered += int(summary.get("filtered_count", 0) or 0)
        for key, value in (summary.get("reject_reason_counts", {}) or {}).items():
            reject_reason_counts[str(key)] = int(reject_reason_counts.get(str(key), 0) or 0) + int(value or 0)

    strategy_family = resolve_strategy_family(args.market, is_amex=(args.market == "AMEX"))
    output_dir = Path(args.output_dir)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": str(args.market),
        "strategy_family": strategy_family,
        "scan_mode": str(args.scan_mode).upper(),
        "profile": str(args.profile),
        "universe_size": len(tickers),
        "batch_size": batch_size,
        "batch_count": len(batches),
        "total_scans": total_scans,
        "total_results": total_results,
        "total_filtered": total_filtered,
        **summarize_health(summaries, len(tickers), len(batches), failure),
        "reject_reason_counts": reject_reason_counts,
        "run_ids": [str(item.get("run_id")) for item in summaries if item.get("run_id")],
        "batch_summaries": summaries,
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    json_path = output_dir / f"{args.market.lower()}_{str(args.scan_mode).lower()}_research_{stamp}.json"
    md_path = output_dir / f"{args.market.lower()}_{str(args.scan_mode).lower()}_research_{stamp}.md"
    _write_json(json_path, report)
    _write_md(md_path, report)
    receipt = {k: v for k, v in report.items() if k not in {"batch_summaries", "reject_reason_counts"}}
    receipt.update(json_path=str(json_path.resolve()), md_path=str(md_path.resolve()))
    if os.environ.get("US_RESEARCH_RECEIPT_PATH"):
        _write_json(Path(os.environ["US_RESEARCH_RECEIPT_PATH"]), receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
