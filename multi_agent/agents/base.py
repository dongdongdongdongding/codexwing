from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from multi_agent.contracts.types import RunContext
from multi_agent.storage.memory_layers import MemoryManager


class AgentBase(ABC):
    agent_name: str = "base"

    @abstractmethod
    def run(self, context: RunContext, memory: MemoryManager) -> Path:
        """Run agent task and persist a structured handoff artifact."""
        raise NotImplementedError
