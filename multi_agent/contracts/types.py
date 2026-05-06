from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunContext:
    run_id: str
    created_at: str = field(default_factory=utc_now_iso)
    as_of_date: str = ""
    market: str = ""
    strategy_version: str = ""
    model_version: str = ""
    code_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WarningItem:
    code: str
    message: str
    severity: str = "info"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScannerCandidate:
    ticker: str
    score: float
    reasons: List[str] = field(default_factory=list)
    feature_snapshot: Dict[str, Any] = field(default_factory=dict)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    theme_context: Dict[str, Any] = field(default_factory=dict)
    leader_metrics: Dict[str, Any] = field(default_factory=dict)
    routing_path: str = ""
    warnings: List[WarningItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = [w.to_dict() for w in self.warnings]
        return payload


@dataclass
class ScannerHandoff:
    run_context: RunContext
    candidates: List[ScannerCandidate] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[WarningItem] = field(default_factory=list)
    produced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_context": self.run_context.to_dict(),
            "candidates": [c.to_dict() for c in self.candidates],
            "summary": self.summary,
            "warnings": [w.to_dict() for w in self.warnings],
            "produced_at": self.produced_at,
        }


@dataclass
class AggregationHandoff:
    run_context: RunContext
    concentration: Dict[str, Any] = field(default_factory=dict)
    clusters: List[Dict[str, Any]] = field(default_factory=list)
    leaderboard: List[Dict[str, Any]] = field(default_factory=list)
    quality_notes: List[str] = field(default_factory=list)
    warnings: List[WarningItem] = field(default_factory=list)
    produced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_context": self.run_context.to_dict(),
            "concentration": self.concentration,
            "clusters": self.clusters,
            "leaderboard": self.leaderboard,
            "quality_notes": self.quality_notes,
            "warnings": [w.to_dict() for w in self.warnings],
            "produced_at": self.produced_at,
        }


@dataclass
class BacktestHandoff:
    run_context: RunContext
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    regime_sensitivity: Dict[str, Any] = field(default_factory=dict)
    calibration: Dict[str, Any] = field(default_factory=dict)
    warnings: List[WarningItem] = field(default_factory=list)
    produced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_context": self.run_context.to_dict(),
            "diagnostics": self.diagnostics,
            "regime_sensitivity": self.regime_sensitivity,
            "calibration": self.calibration,
            "warnings": [w.to_dict() for w in self.warnings],
            "produced_at": self.produced_at,
        }


@dataclass
class MarketContextHandoff:
    run_context: RunContext
    regime: Dict[str, Any] = field(default_factory=dict)
    macro_overlay: Dict[str, Any] = field(default_factory=dict)
    news_impact: Dict[str, Any] = field(default_factory=dict)
    warnings: List[WarningItem] = field(default_factory=list)
    produced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_context": self.run_context.to_dict(),
            "regime": self.regime,
            "macro_overlay": self.macro_overlay,
            "news_impact": self.news_impact,
            "warnings": [w.to_dict() for w in self.warnings],
            "produced_at": self.produced_at,
        }


@dataclass
class PlannerDecision:
    ticker: str
    priority_rank: int
    decision: str
    confidence: float
    stock_name: str = ""
    alpha_score: Optional[float] = None
    conviction_score: Optional[float] = None
    decision_score: Optional[float] = None
    entry_reference_price: Optional[float] = None
    prob_5: Optional[float] = None
    prob_clean: Optional[float] = None
    real_trend: str = ""
    strategy_family: str = ""
    scan_mode: str = ""
    phase25_variant: str = ""
    phase25_prob: Optional[float] = None
    phase25_shadow_variant: str = ""
    phase25_shadow_prob: Optional[float] = None
    phase25_recommended_threshold: Optional[float] = None
    phase25_signal_direction: str = ""
    phase25_raw_auc: Optional[float] = None
    phase25_oos_auc: Optional[float] = None
    phase25_oos_win_rate_pct: Optional[float] = None
    phase25_oos_avg_return_pct: Optional[float] = None
    expected_edge_score: Optional[float] = None
    expected_return_1d_pct: Optional[float] = None
    expected_return_3d_pct: Optional[float] = None
    quant_priority_score: Optional[float] = None
    quant_score_1d: Optional[float] = None
    quant_score_3d: Optional[float] = None
    selection_lane: str = ""
    target_horizon_days: int = 3
    scanner_timeframe_profile: str = ""
    kr_universe_role: str = ""
    explosive_eligible: bool = False
    explosive_gate_reasons: List[str] = field(default_factory=list)
    continuation_eligible: bool = False
    continuation_enabled: bool = False
    continuation_prob_3d: Optional[float] = None
    continuation_evidence: int = 0
    continuation_gate_reasons: List[str] = field(default_factory=list)
    primary_theme: str = ""
    theme_source: str = ""
    theme_inference_status: str = ""
    secondary_themes: List[str] = field(default_factory=list)
    theme_routing_path: str = ""
    theme_rationale: List[str] = field(default_factory=list)
    theme_risk: List[str] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    warnings: List[WarningItem] = field(default_factory=list)
    realized_outcome_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = [w.to_dict() for w in self.warnings]
        return payload


@dataclass
class PlannerHandoff:
    run_context: RunContext
    decisions: List[PlannerDecision] = field(default_factory=list)
    watchlist: List[str] = field(default_factory=list)
    watchlist_meta: List[Dict[str, Any]] = field(default_factory=list)
    avoid_list: List[str] = field(default_factory=list)
    global_warnings: List[WarningItem] = field(default_factory=list)
    produced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_context": self.run_context.to_dict(),
            "decisions": [d.to_dict() for d in self.decisions],
            "watchlist": self.watchlist,
            "watchlist_meta": self.watchlist_meta,
            "avoid_list": self.avoid_list,
            "global_warnings": [w.to_dict() for w in self.global_warnings],
            "produced_at": self.produced_at,
        }


@dataclass
class ImprovementTicket:
    ticket_id: str
    run_id: str
    owner_agent: str
    owner_module: str
    title: str
    hypothesis: str
    requested_change: str
    priority: str = "medium"
    status: str = "open"
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PostmortemReport:
    run_context: RunContext
    scope: str
    failure_summary: str
    likely_causes: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    decisions_reviewed: List[str] = field(default_factory=list)
    tickets: List[ImprovementTicket] = field(default_factory=list)
    produced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_context": self.run_context.to_dict(),
            "scope": self.scope,
            "failure_summary": self.failure_summary,
            "likely_causes": self.likely_causes,
            "evidence_refs": self.evidence_refs,
            "decisions_reviewed": self.decisions_reviewed,
            "tickets": [t.to_dict() for t in self.tickets],
            "produced_at": self.produced_at,
        }


@dataclass
class OrchestratorRequest:
    run_context: RunContext
    task_id: str
    user_request: str
    task_kind: str
    requested_market: str = ""
    requested_agents: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    input_artifacts: List[str] = field(default_factory=list)
    produced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_context": self.run_context.to_dict(),
            "task_id": self.task_id,
            "user_request": self.user_request,
            "task_kind": self.task_kind,
            "requested_market": self.requested_market,
            "requested_agents": self.requested_agents,
            "constraints": self.constraints,
            "input_artifacts": self.input_artifacts,
            "produced_at": self.produced_at,
        }


@dataclass
class OrchestratorAssignment:
    step_id: str
    agent_name: str
    objective: str
    depends_on: List[str] = field(default_factory=list)
    input_refs: List[str] = field(default_factory=list)
    output_ref: Optional[str] = None
    status: str = "pending"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OrchestratorReport:
    run_context: RunContext
    task_id: str
    request_summary: Dict[str, Any] = field(default_factory=dict)
    assignments: List[OrchestratorAssignment] = field(default_factory=list)
    shared_evidence: List[str] = field(default_factory=list)
    validation_checks: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[WarningItem] = field(default_factory=list)
    status: str = "pending"
    produced_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_context": self.run_context.to_dict(),
            "task_id": self.task_id,
            "request_summary": self.request_summary,
            "assignments": [a.to_dict() for a in self.assignments],
            "shared_evidence": self.shared_evidence,
            "validation_checks": self.validation_checks,
            "warnings": [w.to_dict() for w in self.warnings],
            "status": self.status,
            "produced_at": self.produced_at,
        }
