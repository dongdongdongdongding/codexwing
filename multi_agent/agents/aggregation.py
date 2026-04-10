from __future__ import annotations

from pathlib import Path

from multi_agent.agents.aggregation_runtime import build_aggregation_handoff
from multi_agent.agents.base import AgentBase
from multi_agent.contracts.serialization import read_json, write_json
from multi_agent.contracts.types import AggregationHandoff, RunContext, WarningItem
from multi_agent.storage.memory_layers import MemoryManager


class AggregationAgent(AgentBase):
    agent_name = "aggregation_agent"

    def run(self, context: RunContext, memory: MemoryManager) -> Path:
        out = memory.shared_working(context.run_id) / "aggregation_handoff.json"
        scanner_path = memory.shared_working(context.run_id) / "scanner_handoff.json"

        try:
            payload = read_json(scanner_path)
            candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
            if not isinstance(candidates, list):
                candidates = []
            handoff, _metrics = build_aggregation_handoff(context=context, candidates=candidates)
            return write_json(out, handoff.to_dict())
        except Exception:
            handoff = AggregationHandoff(
                run_context=context,
                concentration={"status": "placeholder"},
                clusters=[],
                quality_notes=["Aggregation fallback: scanner_handoff not available or unreadable."],
                warnings=[
                    WarningItem(
                        code="AGGREGATION_FALLBACK",
                        message="Fallback output only. Scanner handoff read failed for this run.",
                        severity="warning",
                    )
                ],
            )
            return write_json(out, handoff.to_dict())
