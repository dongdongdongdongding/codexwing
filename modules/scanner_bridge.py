from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List
from uuid import uuid4

from multi_agent.agents.orchestrator import OrchestratorAgent
from multi_agent.contracts.types import RunContext
from multi_agent.storage.memory_layers import MemoryManager


def _attach_shared_working_artifacts(info: Dict[str, Any]) -> None:
    run_dir = Path(str(info.get("shared_working_dir", "") or ""))
    if not run_dir.exists():
        return

    artifact_names = [
        "scanner_handoff",
        "aggregation_handoff",
        "backtest_handoff",
        "market_context_handoff",
        "planner_handoff",
        "profile_diagnostics",
        "postmortem_report",
        "orchestrator_request",
        "orchestrator_report",
        "orchestrator_compact_summary",
    ]
    for name in artifact_names:
        if info.get(name):
            continue
        path = run_dir / f"{name}.json"
        if path.exists():
            info[name] = str(path)


def _ensure_downstream_diagnostics(
    info: Dict[str, Any],
    logger: Callable[[str], None] | None = None,
) -> None:
    scanner_handoff = str(info.get("scanner_handoff") or "").strip()
    if not scanner_handoff:
        return
    if info.get("profile_diagnostics") and info.get("postmortem_report"):
        return

    try:
        from multi_agent.workflows.legacy_orchestration import run_legacy_orchestration

        extra_paths = run_legacy_orchestration(scanner_handoff)
        if isinstance(extra_paths, dict):
            info.update(extra_paths)
            _attach_shared_working_artifacts(info)
        if logger:
            logger("🧩 Legacy downstream diagnostics attached from scanner handoff.")
    except Exception as exc:
        info.setdefault("errors", []).append(f"downstream_diagnostics_failed:{exc}")
        if logger:
            logger(f"⚠️ Downstream diagnostics attach failed: {exc}")


def run_legacy_agent_bridge(
    results: List[Dict[str, Any]],
    market: str,
    strategy_version: str,
    model_version: str = "legacy",
    code_version: str = "bridge-v1",
    summary_overrides: Dict[str, Any] | None = None,
    run_id: str | None = None,
    logger: Callable[[str], None] | None = None,
) -> Dict[str, Any]:
    """Route legacy scanner output into the top-level orchestrator.

    This wrapper keeps UI/bot files thin and consistent.
    """

    info: Dict[str, Any] = {"ok": False, "errors": []}
    temp_input_path = ""

    try:
        memory = MemoryManager()
        temp_run_key = f"BRIDGE-{uuid4().hex[:8].upper()}"
        temp_input_dir = memory.local_short_term("orchestrator_bridge", temp_run_key)
        temp_input = temp_input_dir / "legacy_scan_results.json"
        payload = {
            "results": results,
            "meta": {**(summary_overrides or {}), **({"run_id": str(run_id)} if run_id else {})},
        }
        with temp_input.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        temp_input_path = str(temp_input)
        info["scanner_input"] = temp_input_path
        if logger:
            logger(f"🧾 Orchestrator scanner input prepared: `{temp_input_path}`")
    except Exception as exc:
        msg = f"Scanner input export failed: {exc}"
        info["errors"].append(msg)
        if logger:
            logger(f"⚠️ {msg}")
        return info

    try:
        agent = OrchestratorAgent(
            user_request="Run full scan pipeline from scanner bridge input and synthesize planner-ready outputs.",
            market=market,
            strategy_version=strategy_version,
            model_version=model_version,
            code_version=code_version,
            scanner_input_path=temp_input_path,
        )
        context = None
        if run_id:
            context = RunContext(
                run_id=str(run_id),
                market=market,
                strategy_version=strategy_version,
                model_version=model_version,
                code_version=code_version,
            )
        report_path = agent.run(context=context, memory=MemoryManager())
        execution = dict(agent.last_execution or {})
        execution["orchestrator_report"] = str(report_path)
        info.update(execution)
        _attach_shared_working_artifacts(info)
        _ensure_downstream_diagnostics(info, logger=logger)
        if logger:
            logger(f"🧠 Orchestrator report: `{execution.get('orchestrator_report', '')}`")
    except Exception as exc:
        msg = f"Agent orchestration failed: {exc}"
        info["errors"].append(msg)
        if logger:
            logger(f"⚠️ {msg}")
        return info

    info["ok"] = True
    return info
