from __future__ import annotations

import argparse
import json

from multi_agent.agents.orchestrator import OrchestratorAgent
from multi_agent.storage.memory_layers import MemoryManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Run top-level orchestrator over the 5-agent pipeline.")
    parser.add_argument("--request", type=str, required=True, help="User request to decompose and orchestrate.")
    parser.add_argument("--market", type=str, default="KR", help="Market code (e.g. KOSPI, KOSDAQ, NASDAQ, KR, US).")
    parser.add_argument("--scanner-input", type=str, default=None, help="Optional legacy scanner rows JSON path.")
    parser.add_argument("--strategy-version", type=str, default="orchestrator-v1")
    parser.add_argument("--model-version", type=str, default="legacy")
    parser.add_argument("--code-version", type=str, default="orchestrator-workflow-v1")
    args = parser.parse_args()

    agent = OrchestratorAgent(
        user_request=args.request,
        market=args.market,
        strategy_version=args.strategy_version,
        model_version=args.model_version,
        code_version=args.code_version,
        scanner_input_path=args.scanner_input,
    )
    report_path = agent.run(memory=MemoryManager())
    payload = dict(agent.last_execution or {})
    payload["orchestrator_report"] = str(report_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
