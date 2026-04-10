from __future__ import annotations

import argparse
import json
from pathlib import Path

from multi_agent.agents.orchestrator import OrchestratorAgent
from multi_agent.storage.memory_layers import MemoryManager


def run_scaffold_pipeline(market: str = "KR", scanner_input_path: str | None = None) -> str:
    agent = OrchestratorAgent(
        user_request="Run scaffold pipeline through the top-level orchestrator.",
        market=market,
        strategy_version="legacy-compatible",
        model_version="legacy",
        code_version="scaffold-v1",
        scanner_input_path=scanner_input_path,
    )
    agent.run(memory=MemoryManager())
    execution = dict(agent.last_execution or {})
    return str(execution.get("run_id") or "")


def run_placeholder_pipeline(market: str = "KR", scanner_input_path: str | None = None) -> str:
    """Backward-compatible alias."""
    return run_scaffold_pipeline(market=market, scanner_input_path=scanner_input_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run additive multi-agent scaffold pipeline.")
    parser.add_argument("--market", type=str, default="KR", help="Market code (e.g., KR, US).")
    parser.add_argument(
        "--scanner-input",
        type=str,
        default=None,
        help="Path to legacy scanner rows JSON (list or {'results': [...]}).",
    )
    args = parser.parse_args()

    scanner_input_path: str | None = args.scanner_input
    if scanner_input_path:
        path = Path(scanner_input_path)
        if not path.exists():
            raise FileNotFoundError(f"scanner input not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, (list, dict)):
            raise ValueError("scanner input must be a JSON list or object.")

    rid = run_scaffold_pipeline(market=args.market, scanner_input_path=scanner_input_path)
    print(f"scaffold pipeline complete: {rid}")
