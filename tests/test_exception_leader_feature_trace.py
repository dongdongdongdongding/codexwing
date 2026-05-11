from types import SimpleNamespace

from multi_agent.contracts.types import RunContext
from multi_agent.workflows.legacy_orchestration import (
    _build_relative_zero_pass_decisions,
    _build_realized_outcomes_placeholder,
    _collect_exception_leaders_from_scanner_payload,
)


def test_exception_leader_collection_preserves_scanner_feature_fields(monkeypatch):
    monkeypatch.setattr(
        "multi_agent.workflows.legacy_orchestration._resolve_ticker_names",
        lambda market, tickers: {ticker: "Test Co" for ticker in tickers},
    )
    monkeypatch.setattr(
        "multi_agent.workflows.legacy_orchestration.get_ticker_profile",
        lambda **kwargs: {},
    )
    context = RunContext(run_id="RUN-TEST", market="KOSDAQ")
    scanner_payload = {
        "summary": {
            "input_meta": {"market_gate": {"gate": "GREEN"}},
            "diagnostics": {
                "reject_reasons_by_symbol": {"123450.KQ": "KR_HARD_FILTER_FAIL"},
                "reject_details_by_symbol": {
                    "123450.KQ": [
                        {
                            "ticker": "123450.KQ",
                            "alpha_score": 72.0,
                            "tech_score": 68,
                            "whale_score": 64,
                            "volume_ratio": 2.35,
                            "volume_confirmed": True,
                            "volume": "✅ x2.35",
                            "market_gate": "GREEN",
                            "scanner_timeframe_profile": "SWING_DAILY",
                            "kr_universe_role": "EXPLOSIVE_LEADER",
                            "conviction_score": 69.0,
                            "prob_5": 52.0,
                            "prob_clean": 49.0,
                            "real_trend": "UP",
                            "tier_sort": 2,
                        }
                    ]
                },
            },
        }
    }

    result = _collect_exception_leaders_from_scanner_payload(
        scanner_payload=scanner_payload,
        context=context,
        max_watchlist=1,
    )

    meta = result["watchlist_meta"][0]
    assert meta["tech_score"] == 68
    assert meta["whale_score"] == 64
    assert meta["volume_ratio"] == 2.35
    assert meta["volume_confirmed"] is True
    assert meta["volume"] == "✅ x2.35"
    assert meta["market_gate"] == "GREEN"
    assert meta["scanner_timeframe_profile"] == "SWING_DAILY"
    assert meta["kr_universe_role"] == "EXPLOSIVE_LEADER"


def test_realized_outcome_placeholder_preserves_watchlist_feature_fields(monkeypatch):
    monkeypatch.setattr(
        "multi_agent.workflows.legacy_orchestration.get_stock_theme_record",
        lambda symbol: {},
    )
    context = RunContext(run_id="RUN-TEST", market="KOSDAQ")
    planner_handoff = SimpleNamespace(
        decisions=[],
        watchlist=["123450.KQ"],
        watchlist_meta=[
            {
                "ticker": "123450.KQ",
                "reason": "exception_leader_watchlist",
                "alpha_score": 72.0,
                "tech_score": 68,
                "whale_score": 64,
                "volume_ratio": 2.35,
                "volume_confirmed": True,
                "volume": "✅ x2.35",
                "market_gate": "GREEN",
                "scanner_timeframe_profile": "SWING_DAILY",
                "kr_universe_role": "EXPLOSIVE_LEADER",
            }
        ],
    )

    payload = _build_realized_outcomes_placeholder(
        context,
        planner_handoff,
        scanner_payload={"summary": {"input_meta": {"market_gate": {"gate": "GREEN"}}}},
    )

    row = payload["outcomes"][0]
    assert row["decision"] == "EXCEPTION_LEADER"
    assert row["tech_score"] == 68
    assert row["whale_score"] == 64
    assert row["volume_ratio"] == 2.35
    assert row["volume_confirmed"] is True
    assert row["volume"] == "✅ x2.35"
    assert row["market_gate"] == "GREEN"
    assert row["scanner_timeframe_profile"] == "SWING_DAILY"
    assert row["kr_universe_role"] == "EXPLOSIVE_LEADER"


def test_realized_outcome_placeholder_ranks_only_tradeable_decisions():
    context = RunContext(run_id="RUN-TEST", market="KOSDAQ")
    planner_handoff = SimpleNamespace(
        decisions=[
            SimpleNamespace(
                ticker="111111.KQ",
                stock_name="Avoided",
                priority_rank=1,
                decision="AVOID",
                target_horizon_days=3,
                scan_mode="SWING",
                strategy_family="KR_CORE",
            ),
            SimpleNamespace(
                ticker="222222.KQ",
                stock_name="Tradeable",
                priority_rank=2,
                decision="EXCEPTION_LEADER",
                target_horizon_days=3,
                scan_mode="SWING",
                strategy_family="KR_CORE",
            ),
        ],
        watchlist=[],
        watchlist_meta=[],
    )

    payload = _build_realized_outcomes_placeholder(context, planner_handoff, scanner_payload={})

    by_ticker = {row["ticker"]: row for row in payload["outcomes"]}
    assert by_ticker["111111.KQ"]["decision_bucket"] == "ignored"
    assert by_ticker["111111.KQ"]["priority_rank"] is None
    assert by_ticker["222222.KQ"]["decision_bucket"] == "exception_leader"
    assert by_ticker["222222.KQ"]["priority_rank"] == 1


def test_relative_zero_pass_decisions_use_real_near_miss_meta():
    decisions = _build_relative_zero_pass_decisions(
        watchlist_meta=[
            {
                "ticker": "005930.KS",
                "stock_name": "삼성전자",
                "source_profile": "current_run_near_miss",
                "reject_reason": "precision_gate_t3_low_ml_support",
                "alpha_score": 77.0,
                "tech_score": 75.0,
                "conviction_score": 64.3,
                "decision_score": 125.28,
                "whale_score": 59.0,
                "volume": "✅ x1.00",
                "volume_ratio": 1.0,
                "volume_confirmed": True,
                "prob_5": 35.8,
                "prob_clean": 27.4,
                "real_trend": "UP",
                "market_gate": "GREEN",
                "scanner_timeframe_profile": "SWING_DAILY",
                "kr_universe_role": "CORE_TREND",
                "horizon_days": 2,
            }
        ],
        max_decisions=5,
    )

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.ticker == "005930.KS"
    assert decision.decision == "WATCHLIST"
    assert decision.market_gate == "GREEN"
    assert decision.tech_score == 75.0
    assert decision.whale_score == 59.0
    assert decision.volume == "✅ x1.00"
    assert decision.volume_ratio == 1.0
    assert decision.volume_confirmed is True
    assert decision.scanner_timeframe_profile == "SWING_DAILY"
    assert decision.kr_universe_role == "CORE_TREND"
    assert decision.target_horizon_days == 2
    assert "relative_zero_pass_promotion" in decision.rationale
    assert "ZERO_STRICT_PASS_RELATIVE_CANDIDATE" in decision.theme_risk
