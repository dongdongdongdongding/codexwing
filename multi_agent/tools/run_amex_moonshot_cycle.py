#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules import quant_analysis


def _run(cmd: List[str]) -> Dict[str, Any]:
    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = (completed.stdout or "").strip()
    payload: Dict[str, Any] = {
        "command": cmd,
        "stdout": stdout,
        "stderr": (completed.stderr or "").strip(),
    }
    if stdout:
        json_payload = None
        for idx, ch in enumerate(stdout):
            if ch != "{":
                continue
            candidate = stdout[idx:].strip()
            try:
                json_payload = json.loads(candidate)
                break
            except Exception:
                continue
        payload["json"] = json_payload
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AMEX moonshot full-universe research cycle.")
    parser.add_argument("--profile", default="prod")
    parser.add_argument("--scan-mode", choices=["SWING", "INTRADAY"], default="SWING")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--limit-tickers", type=int, default=0)
    parser.add_argument("--force-macro-refresh", action="store_true")
    parser.add_argument("--strategy-version", default="amex-moonshot-v1")
    parser.add_argument("--model-version", default="amex-research-baseline")
    parser.add_argument("--code-version", default="amex-moonshot-cycle")
    parser.add_argument("--output-dir", default="runtime_state/reports/us_research")
    parser.add_argument("--skip-export", action="store_true")
    args = parser.parse_args()

    universe = quant_analysis.QuantStrategy.get_market_tickers("AMEX") or {}
    tickers = list(universe.keys())
    if args.limit_tickers and args.limit_tickers > 0:
        tickers = tickers[: int(args.limit_tickers)]

    research_cmd = [
        "python3",
        "multi_agent/tools/run_us_full_universe_research.py",
        "--market",
        "AMEX",
        "--profile",
        str(args.profile),
        "--batch-size",
        str(int(args.batch_size)),
        "--max-workers",
        str(int(args.max_workers)),
        "--scan-mode",
        str(args.scan_mode).upper(),
        "--max-retries",
        str(int(args.max_retries)),
        "--strategy-version",
        str(args.strategy_version),
        "--model-version",
        str(args.model_version),
        "--code-version",
        str(args.code_version),
        "--output-dir",
        str(args.output_dir),
    ]
    if args.limit_tickers and args.limit_tickers > 0:
        research_cmd.extend(["--limit-tickers", str(int(args.limit_tickers))])
    if args.force_macro_refresh:
        research_cmd.append("--force-macro-refresh")

    validation_cmd = [
        "python3",
        "multi_agent/tools/report_us_strategy_validation.py",
        "--market",
        "AMEX",
        "--scan-mode",
        str(args.scan_mode).upper(),
        "--strategy-family",
        "AMEX_MOONSHOT",
        "--output-dir",
        str(args.output_dir),
    ]

    sub7_cmd = [
        "python3",
        "multi_agent/tools/report_amex_sub7_patterns.py",
        "--output-dir",
        str(args.output_dir),
    ]

    export_cmd = [
        "python3",
        "multi_agent/tools/export_scan_archive_learning_dataset.py",
        "--market",
        "AMEX",
        "--scan-mode",
        str(args.scan_mode).upper(),
        "--strategy-family",
        "AMEX_MOONSHOT",
        "--limit",
        "5000",
    ]

    research_result = _run(research_cmd)
    validation_result = _run(validation_cmd)
    sub7_result = _run(sub7_cmd)
    export_result: Dict[str, Any] | None = None
    if not args.skip_export:
        export_result = _run(export_cmd)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": "AMEX",
        "strategy_family": "AMEX_MOONSHOT",
        "scan_mode": str(args.scan_mode).upper(),
        "profile": str(args.profile),
        "universe_size": len(universe),
        "requested_tickers": len(tickers),
        "research": research_result.get("json") or research_result,
        "validation": validation_result.get("json") or validation_result,
        "sub7_patterns": sub7_result.get("json") or sub7_result,
        "learning_export": export_result.get("json") if export_result else None,
    }
    manifest_path = out_dir / f"amex_moonshot_cycle_{stamp}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"manifest_path": str(manifest_path), "requested_tickers": len(tickers)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
