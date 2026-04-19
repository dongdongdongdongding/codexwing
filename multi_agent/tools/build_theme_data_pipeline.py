from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.theme_data_pipeline import refresh_theme_data_pipeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default="ALL", help="KR, US, or ALL")
    args = parser.parse_args()

    market_arg = str(args.market or "ALL").upper()
    markets = ["KR", "US"] if market_arg == "ALL" else [market_arg]
    results = {}
    for market in markets:
        results[market] = refresh_theme_data_pipeline(market)
    summary = {
        market: {
            "instrument_master_version": payload["instrument_master"].get("version", ""),
            "theme_membership_version": payload["theme_membership"].get("version", ""),
            "report_paths": payload.get("report_paths", {}),
        }
        for market, payload in results.items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
