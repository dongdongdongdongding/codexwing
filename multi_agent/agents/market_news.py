from __future__ import annotations

from pathlib import Path

from multi_agent.agents.market_context_runtime import build_market_context_handoff
from multi_agent.agents.base import AgentBase
from multi_agent.contracts.serialization import write_json
from multi_agent.contracts.types import RunContext
from multi_agent.storage.memory_layers import MemoryManager


class MarketNewsContextAgent(AgentBase):
    agent_name = "market_news_context_agent"

    def run(self, context: RunContext, memory: MemoryManager) -> Path:
        handoff = build_market_context_handoff(context)
        out = memory.shared_working(context.run_id) / "market_context_handoff.json"
        return write_json(out, handoff.to_dict())
