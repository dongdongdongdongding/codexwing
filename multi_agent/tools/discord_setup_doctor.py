#!/usr/bin/env python3
"""Validate Discord remote-control integration setup without starting a bot."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.discord_integration.commands import command_contract
from modules.discord_integration.config import load_discord_config


def main() -> int:
    config = load_discord_config(load_env=True)
    validation = config.validate()
    payload = {
        "validation": validation,
        "command_contract": command_contract(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if validation["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
