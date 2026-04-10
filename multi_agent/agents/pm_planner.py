from __future__ import annotations

from pathlib import Path

from multi_agent.agents.planner_runtime import build_planner_handoff
from multi_agent.agents.base import AgentBase
from multi_agent.contracts.serialization import read_json, write_json
from multi_agent.contracts.types import PlannerHandoff, RunContext, WarningItem
from multi_agent.storage.memory_layers import MemoryManager


class PMPlannerAgent(AgentBase):
    agent_name = "pm_planner_agent"

    def run(self, context: RunContext, memory: MemoryManager) -> Path:
        out = memory.shared_working(context.run_id) / "planner_handoff.json"
        scanner_path = memory.shared_working(context.run_id) / "scanner_handoff.json"
        aggregation_path = memory.shared_working(context.run_id) / "aggregation_handoff.json"
        try:
            scanner_payload = read_json(scanner_path)
            candidates = scanner_payload.get("candidates", []) if isinstance(scanner_payload, dict) else []
            if not isinstance(candidates, list):
                candidates = []

            weak_ratio = 1.0
            try:
                agg_payload = read_json(aggregation_path)
                conc = agg_payload.get("concentration", {}) if isinstance(agg_payload, dict) else {}
                weak_ratio = float(conc.get("weak_candidate_ratio", 1.0) or 1.0)
            except Exception:
                pass

            handoff = build_planner_handoff(
                context=context,
                candidates=candidates,
                weak_ratio=weak_ratio,
            )
            return write_json(out, handoff.to_dict())
        except Exception:
            handoff = PlannerHandoff(
                run_context=context,
                decisions=[],
                watchlist=[],
                avoid_list=[],
                global_warnings=[
                    WarningItem(
                        code="PLANNER_FALLBACK",
                        message="Fallback output only. Scanner/Aggregation handoff read failed.",
                        severity="warning",
                    )
                ],
            )
            return write_json(out, handoff.to_dict())
