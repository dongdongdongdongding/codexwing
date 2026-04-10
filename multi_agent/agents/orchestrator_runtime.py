from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from multi_agent.agents.aggregation import AggregationAgent
from multi_agent.agents.backtest_learning import BacktestLearningAgent
from multi_agent.agents.market_news import MarketNewsContextAgent
from multi_agent.agents.pm_planner import PMPlannerAgent
from multi_agent.agents.scanner import ScannerAgent
from multi_agent.contracts.serialization import read_json
from multi_agent.contracts.serialization import write_json
from multi_agent.contracts.types import (
    OrchestratorAssignment,
    OrchestratorReport,
    OrchestratorRequest,
    RunContext,
    WarningItem,
)
from multi_agent.storage.memory_layers import MemoryManager
from multi_agent.storage.long_term_memory import log_orchestrator_execution


AGENT_REGISTRY = {
    "scanner_agent": ScannerAgent,
    "aggregation_agent": AggregationAgent,
    "backtest_learning_agent": BacktestLearningAgent,
    "market_news_context_agent": MarketNewsContextAgent,
    "pm_planner_agent": PMPlannerAgent,
}

TASK_AGENT_SELECTION = {
    "scan_pipeline": [
        "scanner_agent",
        "aggregation_agent",
        "backtest_learning_agent",
        "market_news_context_agent",
        "pm_planner_agent",
    ],
    "general_pipeline": [
        "scanner_agent",
        "aggregation_agent",
        "backtest_learning_agent",
        "market_news_context_agent",
        "pm_planner_agent",
    ],
    "research_tuning": [
        "scanner_agent",
        "aggregation_agent",
        "backtest_learning_agent",
        "market_news_context_agent",
        "pm_planner_agent",
    ],
    "market_review": [
        "market_news_context_agent",
        "pm_planner_agent",
    ],
    "postmortem": [
        "scanner_agent",
        "aggregation_agent",
        "backtest_learning_agent",
        "market_news_context_agent",
        "pm_planner_agent",
    ],
}


def _normalize_market(value: str | None) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"KOSPI", "KOSDAQ", "NASDAQ", "S&P500", "AMEX", "KR", "US"}:
        return raw
    return "KR"


def infer_task_kind(user_request: str, scanner_input_path: str | None = None) -> str:
    text = str(user_request or "").lower()
    if scanner_input_path:
        return "scan_pipeline"
    if any(token in text for token in ["postmortem", "사후", "회고", "원인 분석"]):
        return "postmortem"
    if any(token in text for token in ["정확도", "accuracy", "수익률", "튜닝", "optimiz", "scan"]):
        return "research_tuning"
    if any(token in text for token in ["market", "macro", "뉴스", "regime", "장세"]):
        return "market_review"
    return "general_pipeline"


def select_agents_for_task_kind(task_kind: str) -> List[str]:
    selected = TASK_AGENT_SELECTION.get(str(task_kind or "").strip().lower())
    if selected:
        return list(selected)
    return list(TASK_AGENT_SELECTION["general_pipeline"])


def build_orchestrator_request(
    *,
    user_request: str,
    market: str,
    strategy_version: str,
    model_version: str,
    code_version: str,
    scanner_input_path: str | None = None,
    run_id: str | None = None,
) -> Tuple[RunContext, OrchestratorRequest]:
    context = RunContext(
        run_id=run_id or f"RUN-{uuid4().hex[:8].upper()}",
        as_of_date=str(date.today()),
        market=_normalize_market(market),
        strategy_version=strategy_version,
        model_version=model_version,
        code_version=code_version,
    )
    task_kind = infer_task_kind(user_request=user_request, scanner_input_path=scanner_input_path)
    requested_agents = select_agents_for_task_kind(task_kind)
    constraints = [
        "Preserve proven core logic.",
        "Prefer structured outputs and auditable traces.",
        "Do not rely on hidden reasoning as final evidence.",
    ]
    input_artifacts = [scanner_input_path] if scanner_input_path else []
    request = OrchestratorRequest(
        run_context=context,
        task_id=f"TASK-{uuid4().hex[:8].upper()}",
        user_request=str(user_request or "").strip(),
        task_kind=task_kind,
        requested_market=context.market,
        requested_agents=requested_agents,
        constraints=constraints,
        input_artifacts=input_artifacts,
    )
    return context, request


def build_execution_plan(request: OrchestratorRequest) -> List[OrchestratorAssignment]:
    requested = set(request.requested_agents or [])
    plan: List[OrchestratorAssignment] = []

    def add(step_id: str, agent_name: str, objective: str, depends_on: List[str], input_refs: List[str]) -> None:
        if agent_name not in requested:
            return
        deps = [dep for dep in depends_on if any(existing.step_id == dep for existing in plan)]
        plan.append(
            OrchestratorAssignment(
                step_id=step_id,
                agent_name=agent_name,
                objective=objective,
                depends_on=deps,
                input_refs=input_refs,
            )
        )

    add(
        "step_scanner",
        "scanner_agent",
        "Generate or ingest scanner handoff with candidate reasons and structured traces.",
        [],
        request.input_artifacts,
    )
    add(
        "step_aggregation",
        "aggregation_agent",
        "Analyze concentration, common traits, and candidate quality.",
        ["step_scanner"],
        ["scanner_handoff.json"],
    )
    add(
        "step_backtest",
        "backtest_learning_agent",
        "Validate current candidates with realistic diagnostics and regime sensitivity.",
        ["step_scanner", "step_aggregation"],
        ["scanner_handoff.json", "aggregation_handoff.json"],
    )
    add(
        "step_market",
        "market_news_context_agent",
        "Assess current market regime, macro pressure, and news context.",
        [],
        [],
    )
    add(
        "step_planner",
        "pm_planner_agent",
        "Synthesize all evidence into final decisions, watchlists, and warnings.",
        ["step_scanner", "step_aggregation", "step_backtest", "step_market"],
        [
            "scanner_handoff.json",
            "aggregation_handoff.json",
            "backtest_handoff.json",
            "market_context_handoff.json",
        ],
    )
    return plan


def _instantiate_agent(agent_name: str, scanner_input_path: str | None = None):
    if agent_name == "scanner_agent":
        return ScannerAgent(legacy_results_path=scanner_input_path)
    cls = AGENT_REGISTRY[agent_name]
    return cls()


def _validate_assignment_output(output_path: str | None) -> Dict[str, Any]:
    exists = False
    if output_path:
        try:
            exists = Path(output_path).exists()
        except Exception:
            exists = False
    return {
        "output_ref": output_path,
        "exists": bool(exists),
    }


def _build_compact_summary(
    *,
    run_dir: Path,
    request: OrchestratorRequest,
    report: OrchestratorReport,
) -> Dict[str, Any]:
    scanner_payload = read_json(run_dir / "scanner_handoff.json") if (run_dir / "scanner_handoff.json").exists() else {}
    planner_payload = read_json(run_dir / "planner_handoff.json") if (run_dir / "planner_handoff.json").exists() else {}
    profile_payload = read_json(run_dir / "profile_diagnostics.json") if (run_dir / "profile_diagnostics.json").exists() else {}
    postmortem_payload = read_json(run_dir / "postmortem_report.json") if (run_dir / "postmortem_report.json").exists() else {}

    scanner_summary = scanner_payload.get("summary", {}) if isinstance(scanner_payload.get("summary"), dict) else {}
    diagnostics = scanner_summary.get("diagnostics", {}) if isinstance(scanner_summary.get("diagnostics"), dict) else {}
    planner_warnings = planner_payload.get("global_warnings", []) if isinstance(planner_payload.get("global_warnings"), list) else []
    likely_causes = postmortem_payload.get("likely_causes", []) if isinstance(postmortem_payload.get("likely_causes"), list) else []
    return {
        "run_id": request.run_context.run_id,
        "task_id": request.task_id,
        "task_kind": request.task_kind,
        "market": request.requested_market,
        "status": report.status,
        "agents_executed": [a.agent_name for a in report.assignments if a.status == "completed"],
        "scanner": {
            "candidate_count": int(scanner_summary.get("candidate_count", 0) or 0),
            "top_reject_reason": profile_payload.get("current_top_reject_reason", {}),
            "reject_reason_counts": diagnostics.get("reject_reason_counts", {}),
        },
        "planner": {
            "decision_count": len(planner_payload.get("decisions", []) if isinstance(planner_payload.get("decisions"), list) else []),
            "watchlist_count": len(planner_payload.get("watchlist", []) if isinstance(planner_payload.get("watchlist"), list) else []),
            "warning_codes": [
                str(row.get("code", ""))
                for row in planner_warnings
                if isinstance(row, dict) and str(row.get("code", "")).strip()
            ],
        },
        "postmortem": {
            "likely_causes": [str(x) for x in likely_causes[:5]],
        },
    }


def execute_orchestrated_request(
    *,
    request: OrchestratorRequest,
    memory: MemoryManager,
    scanner_input_path: str | None = None,
) -> Dict[str, Any]:
    run_dir = memory.shared_working(request.run_context.run_id)
    request_path = write_json(run_dir / "orchestrator_request.json", request.to_dict())
    plan = build_execution_plan(request)

    warnings: List[WarningItem] = []
    evidence: List[str] = [str(request_path)]
    validations: List[Dict[str, Any]] = []

    for assignment in plan:
        assignment.status = "in_progress"
        try:
            agent = _instantiate_agent(assignment.agent_name, scanner_input_path=scanner_input_path)
            out_path = agent.run(request.run_context, memory=memory)
            assignment.output_ref = str(out_path)
            assignment.status = "completed"
            evidence.append(str(out_path))
            validations.append(
                {
                    "step_id": assignment.step_id,
                    "agent_name": assignment.agent_name,
                    **_validate_assignment_output(assignment.output_ref),
                }
            )
        except Exception as exc:
            assignment.status = "failed"
            assignment.notes.append(str(exc))
            warnings.append(
                WarningItem(
                    code="ORCHESTRATOR_STEP_FAILED",
                    message=f"{assignment.agent_name} failed during {assignment.step_id}: {exc}",
                    severity="error",
                )
            )
            validations.append(
                {
                    "step_id": assignment.step_id,
                    "agent_name": assignment.agent_name,
                    "output_ref": assignment.output_ref,
                    "exists": False,
                    "error": str(exc),
                }
            )
            break

    status = "completed"
    if any(item.get("exists") is False for item in validations):
        status = "partial_failure"
    if any(a.status == "failed" for a in plan):
        status = "failed"

    report = OrchestratorReport(
        run_context=request.run_context,
        task_id=request.task_id,
        request_summary={
            "task_kind": request.task_kind,
            "user_request": request.user_request,
            "requested_market": request.requested_market,
            "requested_agents": request.requested_agents,
        },
        assignments=plan,
        shared_evidence=evidence,
        validation_checks=validations,
        warnings=warnings,
        status=status,
    )
    report_path = write_json(run_dir / "orchestrator_report.json", report.to_dict())
    compact_summary = _build_compact_summary(run_dir=run_dir, request=request, report=report)
    compact_summary_path = write_json(run_dir / "orchestrator_compact_summary.json", compact_summary)
    try:
        log_orchestrator_execution(
            memory=memory,
            row={
                "run_id": request.run_context.run_id,
                "task_id": request.task_id,
                "task_kind": request.task_kind,
                "market": request.requested_market,
                "requested_agents": request.requested_agents,
                "status": status,
                "orchestrator_request": str(request_path),
                "orchestrator_report": str(report_path),
                "orchestrator_compact_summary": str(compact_summary_path),
            },
        )
    except Exception:
        pass
    return {
        "ok": status == "completed",
        "status": status,
        "run_id": request.run_context.run_id,
        "task_id": request.task_id,
        "orchestrator_request": str(request_path),
        "orchestrator_report": str(report_path),
        "orchestrator_compact_summary": str(compact_summary_path),
        "shared_working_dir": str(run_dir),
    }
