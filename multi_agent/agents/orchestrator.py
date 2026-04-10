from __future__ import annotations

from pathlib import Path

from multi_agent.agents.base import AgentBase
from multi_agent.agents.orchestrator_runtime import (
    build_orchestrator_request,
    execute_orchestrated_request,
)
from multi_agent.storage.memory_layers import MemoryManager
from multi_agent.contracts.types import RunContext


class OrchestratorAgent(AgentBase):
    agent_name = "orchestrator_agent"

    def __init__(
        self,
        *,
        user_request: str,
        market: str = "KR",
        strategy_version: str = "orchestrator-v1",
        model_version: str = "legacy",
        code_version: str = "orchestrator-agent-v1",
        scanner_input_path: str | None = None,
    ) -> None:
        self.user_request = str(user_request or "").strip()
        self.market = market
        self.strategy_version = strategy_version
        self.model_version = model_version
        self.code_version = code_version
        self.scanner_input_path = scanner_input_path
        self.last_execution: dict | None = None

    def run(self, context: RunContext | None = None, memory: MemoryManager | None = None) -> Path:
        mem = memory or MemoryManager()
        ctx = context
        request = None
        if ctx is None:
            ctx, request = build_orchestrator_request(
                user_request=self.user_request,
                market=self.market,
                strategy_version=self.strategy_version,
                model_version=self.model_version,
                code_version=self.code_version,
                scanner_input_path=self.scanner_input_path,
            )
        else:
            _, request = build_orchestrator_request(
                user_request=self.user_request,
                market=ctx.market or self.market,
                strategy_version=ctx.strategy_version or self.strategy_version,
                model_version=ctx.model_version or self.model_version,
                code_version=ctx.code_version or self.code_version,
                scanner_input_path=self.scanner_input_path,
                run_id=ctx.run_id,
            )
        result = execute_orchestrated_request(
            request=request,
            memory=mem,
            scanner_input_path=self.scanner_input_path,
        )
        self.last_execution = result
        return Path(result["orchestrator_report"])
