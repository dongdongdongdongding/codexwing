from __future__ import annotations

from typing import List
from uuid import uuid4

from multi_agent.contracts.types import ImprovementTicket, PostmortemReport, RunContext


def create_improvement_ticket(
    run_id: str,
    owner_agent: str,
    owner_module: str,
    title: str,
    hypothesis: str,
    requested_change: str,
    priority: str = "medium",
) -> ImprovementTicket:
    return ImprovementTicket(
        ticket_id=f"TKT-{uuid4().hex[:8].upper()}",
        run_id=run_id,
        owner_agent=owner_agent,
        owner_module=owner_module,
        title=title,
        hypothesis=hypothesis,
        requested_change=requested_change,
        priority=priority,
    )


def build_postmortem_report(
    context: RunContext,
    scope: str,
    failure_summary: str,
    likely_causes: List[str],
    evidence_refs: List[str],
    decision_refs: List[str],
    tickets: List[ImprovementTicket],
) -> PostmortemReport:
    return PostmortemReport(
        run_context=context,
        scope=scope,
        failure_summary=failure_summary,
        likely_causes=likely_causes,
        evidence_refs=evidence_refs,
        decisions_reviewed=decision_refs,
        tickets=tickets,
    )
