from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from multi_agent.storage.memory_layers import MemoryManager


def _append_jsonl(path: Path, row: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def log_run_summary(
    memory: MemoryManager,
    run_id: str,
    market: str,
    strategy_version: str,
    model_version: str,
    code_version: str,
    artifact_refs: Dict[str, str],
) -> Path:
    path = memory.long_term("runs") / "agent_runs.jsonl"
    row = {
        "run_id": run_id,
        "market": market,
        "strategy_version": strategy_version,
        "model_version": model_version,
        "code_version": code_version,
        "artifact_refs": artifact_refs,
    }
    return _append_jsonl(path, row)


def log_postmortem(memory: MemoryManager, row: Dict[str, Any]) -> Path:
    path = memory.long_term("postmortems") / "postmortems.jsonl"
    return _append_jsonl(path, row)


def log_improvement_tickets(memory: MemoryManager, tickets: List[Dict[str, Any]]) -> Path:
    path = memory.long_term("tickets") / "improvement_tickets.jsonl"
    last_path = path
    for ticket in tickets:
        last_path = _append_jsonl(path, ticket)
    return last_path


def log_profile_diagnostics(memory: MemoryManager, row: Dict[str, Any]) -> Path:
    path = memory.long_term("profile_diagnostics") / "profile_diagnostics.jsonl"
    return _append_jsonl(path, row)


def log_outcome_health(memory: MemoryManager, row: Dict[str, Any]) -> Path:
    path = memory.long_term("outcome_health") / "outcome_health.jsonl"
    return _append_jsonl(path, row)


def log_orchestrator_execution(memory: MemoryManager, row: Dict[str, Any]) -> Path:
    path = memory.long_term("orchestrator") / "orchestrator_runs.jsonl"
    return _append_jsonl(path, row)
