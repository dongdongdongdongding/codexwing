from types import SimpleNamespace

from multi_agent.contracts.types import RunContext
from multi_agent.workflows.legacy_orchestration import (
    _build_relative_zero_pass_decisions,
    _build_realized_outcomes_placeholder,
    _build_watchlist_only_meta,
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
    assert meta["horizon_days"] == 5
    assert meta["target_tp_pct"] == 5.0
    assert meta["hold_days"] == 5


def test_exception_leader_collection_skips_hard_loss_risk(monkeypatch):
    monkeypatch.setattr(
        "multi_agent.workflows.legacy_orchestration._resolve_ticker_names",
        lambda market, tickers: {ticker: "Risk Co" for ticker in tickers},
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
                            "alpha_score": 99.0,
                            "tech_score": 95,
                            "whale_score": 80,
                            "volume_ratio": 0.2,
                            "volume_confirmed": False,
                            "conviction_score": 95.0,
                            "prob_5": 12.0,
                            "prob_clean": 15.0,
                            "real_trend": "DOWN",
                            "tier_sort": 3,
                            "position": "Peak",
                            "tier": "T3",
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

    assert result["watchlist"] == []
    assert result["skipped_hard_loss_risk"] == 1


def test_kosdaq_swing_exception_leader_requires_up_trend(monkeypatch):
    monkeypatch.setattr(
        "multi_agent.workflows.legacy_orchestration._resolve_ticker_names",
        lambda market, tickers: {ticker: "Neutral Co" for ticker in tickers},
    )
    monkeypatch.setattr(
        "multi_agent.workflows.legacy_orchestration.get_ticker_profile",
        lambda **kwargs: {},
    )
    context = RunContext(run_id="RUN-TEST", market="KOSDAQ")
    scanner_payload = {
        "summary": {
            "input_meta": {"market_gate": {"gate": "GREEN"}, "scan_mode": "SWING"},
            "diagnostics": {
                "reject_reasons_by_symbol": {"123450.KQ": "KR_HARD_FILTER_FAIL"},
                "reject_details_by_symbol": {
                    "123450.KQ": [
                        {
                            "ticker": "123450.KQ",
                            "alpha_score": 90.0,
                            "tech_score": 80,
                            "whale_score": 75,
                            "volume_ratio": 2.5,
                            "volume_confirmed": True,
                            "conviction_score": 85.0,
                            "prob_5": 52.0,
                            "prob_clean": 49.0,
                            "real_trend": "NEUTRAL",
                            "tier_sort": 1,
                            "position": "Rising",
                            "tier": "T1",
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

    assert result["watchlist"] == []


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
                "loss_risk_score": 41.5,
                "theme_risk": ["LOSS_RISK_SOFT_CAP"],
                "rationale": ["planner wait"],
                "final_action": "눌림 대기",
                "entry_condition_text": "20일선 지지 후 전일 고가 돌파",
                "stop_condition_text": "20일선 종가 이탈",
                "structured_conditions": {
                    "entry_policy": "-2% limit",
                    "target_tp_pct": 10.0,
                    "stop_sl_pct": -10.0,
                    "hold_days": 5,
                },
                "target_tp_pct": 10.0,
                "stop_sl_pct": -10.0,
                "hold_days": 5,
                "entry_policy": "-2% limit",
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
    assert row["target_horizon_days"] == 3
    assert row["loss_risk_score"] == 41.5
    assert row["theme_risk"] == ["LOSS_RISK_SOFT_CAP"]
    assert row["rationale"] == ["planner wait"]
    assert row["final_action"] == "눌림 대기"
    assert row["entry_condition_text"] == "20일선 지지 후 전일 고가 돌파"
    assert row["stop_condition_text"] == "20일선 종가 이탈"
    assert row["entry_policy"] == "-2% limit"


def test_watchlist_only_meta_preserves_loss_risk_and_action_plan():
    meta = _build_watchlist_only_meta(
        watchlist=["005930.KS"],
        policy_summary={
            "market_gate": "RED",
            "mode": "avoid",
            "policy": {"win_5d_pct": 33.3, "avg_5d_pct": -1.2},
        },
        ticker_names={"005930.KS": "삼성전자"},
        decision_details={
            "005930.KS": {
                "loss_risk_score": 51.2,
                "theme_risk": ["LOSS_RISK_SOFT_CAP"],
                "rationale": ["market policy downgrade"],
                "final_action": "관망",
                "entry_condition_text": "시장 정책이 관망 구간입니다. GREEN/YELLOW 회복 후 재평가",
                "stop_condition_text": "진입 전 상태이므로 손절가 대신 제외 조건으로 관리",
                "structured_conditions": {
                    "entry_policy": "open/reference",
                    "target_tp_pct": 20.0,
                    "stop_sl_pct": -5.0,
                    "hold_days": 5,
                },
                "target_tp_pct": 20.0,
                "stop_sl_pct": -5.0,
                "hold_days": 5,
                "entry_policy": "open/reference",
            },
        },
    )

    row = meta[0]
    assert row["risk_label"] == "WATCHLIST_ONLY"
    assert row["loss_risk_score"] == 51.2
    assert row["theme_risk"] == ["LOSS_RISK_SOFT_CAP"]
    assert row["rationale"] == ["market policy downgrade"]
    assert row["final_action"] == "관망"
    assert "GREEN/YELLOW" in row["entry_condition_text"]
    assert "제외 조건" in row["stop_condition_text"]
    assert row["structured_conditions"]["target_tp_pct"] == 20.0
    assert row["entry_policy"] == "open/reference"


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


def test_realized_outcome_placeholder_excludes_hard_loss_risk_from_trade_rank():
    context = RunContext(run_id="RUN-TEST", market="KOSDAQ")
    planner_handoff = SimpleNamespace(
        decisions=[
            SimpleNamespace(
                ticker="111111.KQ",
                stock_name="Hard Risk Observe",
                priority_rank=1,
                decision="OBSERVE",
                loss_risk_score=88.0,
                target_horizon_days=3,
                scan_mode="SWING",
                strategy_family="KR_CORE",
            ),
            SimpleNamespace(
                ticker="222222.KQ",
                stock_name="Soft Watchlist",
                priority_rank=2,
                decision="WATCHLIST_ONLY",
                loss_risk_score=40.0,
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
    assert by_ticker["111111.KQ"]["decision_bucket"] == "watchlist"
    assert by_ticker["111111.KQ"]["priority_rank"] is None
    assert by_ticker["222222.KQ"]["decision_bucket"] == "watchlist"
    assert by_ticker["222222.KQ"]["priority_rank"] == 1


def test_realized_outcome_placeholder_demotes_hard_risk_exception_meta():
    context = RunContext(run_id="RUN-TEST", market="KOSPI")
    planner_handoff = SimpleNamespace(
        decisions=[],
        watchlist=["111111.KS"],
        watchlist_meta=[
            {
                "ticker": "111111.KS",
                "stock_name": "Hard Exception",
                "reason": "exception_leader_watchlist",
                "loss_risk_score": 92.0,
            }
        ],
    )

    payload = _build_realized_outcomes_placeholder(context, planner_handoff, scanner_payload={})

    row = payload["outcomes"][0]
    assert row["decision"] == "OBSERVE"
    assert row["decision_bucket"] == "watchlist"
    assert row["priority_rank"] is None


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
