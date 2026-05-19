#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.tradable_pnl import TradableCostModel, build_tradable_pnl_rows, load_post_scan_ledger_rows, summarize_tradable_pnl

DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def _markdown(report):
    lines = [
        "# Tradable PnL Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- model_version: `{report['cost_assumptions']['version']}`",
        f"- rows: `{report['summary']['rows']}`",
        f"- missing_return_rows: `{report['summary']['missing_return_rows']}`",
        f"- release_gate_pass: `{report['summary']['release_gate_pass']}`",
        "",
        "## Gross vs Net",
    ]
    for row in report["summary"]["groups"]:
        lines.append(
            f"- {row['market']} / {row['section']} / {row['action_label']}: "
            f"3D gross win={row['gross_3d_win_pct']} avg={row['gross_3d_avg_pct']} "
            f"net win={row['net_3d_win_pct']} avg={row['net_3d_avg_pct']} drag={row['cost_drag_3d_pct']} | "
            f"5D gross win={row['gross_5d_win_pct']} avg={row['gross_5d_avg_pct']} "
            f"net win={row['net_5d_win_pct']} avg={row['net_5d_avg_pct']} drag={row['cost_drag_5d_pct']}"
        )
    if report["summary"]["net_regression_groups"]:
        lines.extend(["", "## Net Regression Groups"])
        for row in report["summary"]["net_regression_groups"]:
            lines.append(
                f"- {row['market']} / {row['section']} / {row['action_label']} / {row['horizon']}: "
                f"gross_avg={row['gross_avg_pct']} net_avg={row['net_avg_pct']}"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build real-tradable gross/net PnL report from post-scan outcome ledgers.")
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--limit-runs", type=int, default=200)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--buy-fee-bps", type=float, default=1.5)
    parser.add_argument("--sell-fee-bps", type=float, default=1.5)
    parser.add_argument("--buy-slippage-bps", type=float, default=8.0)
    parser.add_argument("--sell-slippage-bps", type=float, default=8.0)
    parser.add_argument("--spread-bps", type=float, default=4.0)
    parser.add_argument("--sell-tax-bps", type=float, default=15.0)
    parser.add_argument("--fill-rate", type=float, default=1.0)
    parser.add_argument("--fail-on-gross-net-regression", action="store_true")
    args = parser.parse_args()

    cost_model = TradableCostModel(
        buy_fee_bps=float(args.buy_fee_bps),
        sell_fee_bps=float(args.sell_fee_bps),
        buy_slippage_bps=float(args.buy_slippage_bps),
        sell_slippage_bps=float(args.sell_slippage_bps),
        spread_bps=float(args.spread_bps),
        sell_tax_bps=float(args.sell_tax_bps),
        fill_rate=float(args.fill_rate),
    )
    source_rows = load_post_scan_ledger_rows(Path(args.shared_dir), run_ids=args.run_id, limit_runs=int(args.limit_runs))
    pnl_rows = build_tradable_pnl_rows(source_rows, cost_model=cost_model)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {"shared_dir": str(args.shared_dir), "run_ids": list(args.run_id or []), "limit_runs": int(args.limit_runs)},
        "cost_assumptions": asdict(cost_model),
        "summary": summarize_tradable_pnl(pnl_rows),
        "rows_sample": pnl_rows[:200],
    }
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "tradable_pnl_report.json"
    md_path = out_dir / "tradable_pnl_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "rows": len(pnl_rows),
                "groups": len(report["summary"]["groups"]),
                "release_gate_pass": report["summary"]["release_gate_pass"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.fail_on_gross_net_regression and not report["summary"]["release_gate_pass"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
