#!/usr/bin/env python3
"""Register Discord slash commands from the local command contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.discord_integration.config import load_discord_config
from modules.discord_integration.register import register_application_commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Actually register commands even if DISCORD_DRY_RUN=1.")
    args = parser.parse_args()

    config = load_discord_config(load_env=True)
    result = register_application_commands(config, dry_run=not bool(args.live))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
