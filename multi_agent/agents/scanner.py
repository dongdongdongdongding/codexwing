from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from multi_agent.agents.base import AgentBase
from multi_agent.contracts.serialization import read_json, write_json
from multi_agent.contracts.types import RunContext, ScannerHandoff, WarningItem
from multi_agent.storage.memory_layers import MemoryManager
from multi_agent.workflows.legacy_export import export_legacy_scanner_handoff


class ScannerAgent(AgentBase):
    agent_name = "scanner_agent"

    def __init__(self, legacy_results_path: str | Path | None = None) -> None:
        self.legacy_results_path = Path(legacy_results_path) if legacy_results_path else None

    def _resolve_input_path(self, context: RunContext, memory: MemoryManager) -> Path:
        if self.legacy_results_path:
            return self.legacy_results_path
        return memory.local_short_term(self.agent_name, context.run_id) / "legacy_scan_results.json"

    @staticmethod
    def _parse_results(payload: Any) -> tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
        if isinstance(payload, list):
            return True, [row for row in payload if isinstance(row, dict)], {}
        if isinstance(payload, dict):
            meta = payload.get("meta", {})
            if not isinstance(meta, dict):
                meta = {}
            for key in ("results", "rows", "candidates"):
                value = payload.get(key)
                if isinstance(value, list):
                    return True, [row for row in value if isinstance(row, dict)], meta
        return False, [], {}

    def run(self, context: RunContext, memory: MemoryManager) -> Path:
        input_path = self._resolve_input_path(context=context, memory=memory)
        if input_path.exists():
            try:
                payload = read_json(input_path)
                parsed, results, meta = self._parse_results(payload)
                if parsed:
                    summary_overrides: Dict[str, Any] = {}
                    if meta:
                        summary_overrides["input_meta"] = meta
                        for key in (
                            "execution_profile",
                            "applied_profile_defaults",
                            "gate_config",
                            "warnings",
                            "diagnostics",
                            "market_gate",
                            "regime",
                        ):
                            if key in meta:
                                summary_overrides[key] = meta.get(key)
                    out_path = export_legacy_scanner_handoff(
                        results=results,
                        market=context.market,
                        strategy_version=context.strategy_version or "legacy-ui-v1",
                        model_version=context.model_version or "legacy",
                        code_version=context.code_version or "scanner-agent-v1",
                        run_context=context,
                        source="scanner_agent_input",
                        summary_overrides=summary_overrides,
                    )
                    return Path(out_path)
            except Exception:
                pass

        handoff = ScannerHandoff(
            run_context=context,
            candidates=[],
            summary={
                "status": "placeholder",
                "note": "Scanner input missing or unreadable.",
                "expected_input": str(input_path),
            },
            warnings=[
                WarningItem(
                    code="SCANNER_NOT_WIRED",
                    message="Placeholder output only. Provide legacy_scan_results.json to scanner local memory or set explicit input path.",
                    severity="warning",
                )
            ],
        )
        out = memory.shared_working(context.run_id) / "scanner_handoff.json"
        return write_json(out, handoff.to_dict())
