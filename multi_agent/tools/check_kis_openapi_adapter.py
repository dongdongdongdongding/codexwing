#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_openapi import KISConfig, KISOpenAPIClient, build_kis_adapter_health


def _today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


def _live_error(name: str, exc: Exception) -> Dict[str, Any]:
    return {
        "name": name,
        "ok": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }


def run_check(args: argparse.Namespace) -> Dict[str, Any]:
    load_dotenv()
    load_dotenv(".env.local")

    config = KISConfig.from_env()
    if args.mode:
        config = KISConfig(
            app_key=config.app_key,
            app_secret=config.app_secret,
            account_no=config.account_no,
            account_product_code=config.account_product_code,
            cust_type=config.cust_type,
            mode=args.mode,
            live_network_allowed=bool(args.allow_live_network),
        )
    elif args.allow_live_network:
        config.live_network_allowed = True

    client = KISOpenAPIClient(config=config, timeout=float(args.timeout))
    report: Dict[str, Any] = {
        "tool": "check_kis_openapi_adapter",
        "dry_run": not bool(args.allow_live_network),
        "health": build_kis_adapter_health(os.environ),
        "endpoint_contract": client.endpoint_contract(),
        "live_checks": [],
    }

    if not args.allow_live_network:
        report["next_step"] = (
            "Set KIS credentials and rerun with --allow-live-network for token/quote smoke. "
            "Production scanner wiring remains disabled."
        )
        return report

    try:
        token = client.get_access_token(force=True)
        report["live_checks"].append({"name": "token", "ok": bool(token)})
    except Exception as exc:
        report["live_checks"].append(_live_error("token", exc))
        return report

    if args.quote:
        try:
            snapshot = client.quote_snapshot(args.quote, market_div=args.market_div)
            report["live_checks"].append({"name": "quote_snapshot", "ok": snapshot.get("source_status") == "ok", "snapshot": snapshot})
        except Exception as exc:
            report["live_checks"].append(_live_error("quote_snapshot", exc))

    if args.daily:
        try:
            payload = client.daily_bars(
                args.daily,
                start_date=args.start_date or _today_yyyymmdd(),
                end_date=args.end_date or _today_yyyymmdd(),
                market_div=args.market_div,
            )
            report["live_checks"].append(
                {
                    "name": "daily_bars",
                    "ok": payload.get("rt_cd") in (None, "0"),
                    "row_count": len(payload.get("output2") or payload.get("output") or []),
                }
            )
        except Exception as exc:
            report["live_checks"].append(_live_error("daily_bars", exc))

    if args.investor:
        try:
            payload = client.investor_flow_snapshot(args.investor, trade_date=args.investor_date or _today_yyyymmdd())
            report["live_checks"].append({"name": "investor_flow_snapshot", "ok": payload.get("source_status") == "ok", "snapshot": payload})
        except Exception as exc:
            report["live_checks"].append(_live_error("investor_flow_snapshot", exc))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or live smoke check for the KIS OpenAPI adapter.")
    parser.add_argument("--allow-live-network", action="store_true", help="Actually call KIS. Default is contract-only dry-run.")
    parser.add_argument("--mode", choices=["paper", "real"], default="", help="Override KIS_MODE for this check.")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--market-div", default="UN", help="FID_COND_MRKT_DIV_CODE for quote/daily checks.")
    parser.add_argument("--quote", default="", help="Optional ticker for live quote smoke, e.g. 005930 or 005930.KS.")
    parser.add_argument("--daily", default="", help="Optional ticker for live daily bar smoke.")
    parser.add_argument("--start-date", default="", help="YYYYMMDD for live daily bar smoke.")
    parser.add_argument("--end-date", default="", help="YYYYMMDD for live daily bar smoke.")
    parser.add_argument("--investor", default="", help="Optional ticker for live investor flow smoke.")
    parser.add_argument("--investor-date", default="", help="YYYYMMDD for live investor flow smoke.")
    args = parser.parse_args()
    try:
        print(json.dumps(run_check(args), ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
