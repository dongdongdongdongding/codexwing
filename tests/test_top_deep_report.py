from unittest.mock import patch

from modules.top_deep_report import build_top_deep_reports, upsert_reports_to_supabase, _fetch_investor_flow_snapshot


def test_build_top_deep_reports_merges_real_scan_and_planner_trace():
    with (
        patch("modules.top_deep_report._fetch_price_snapshot") as price,
        patch("modules.top_deep_report._fetch_news_snapshot") as news,
        patch("modules.top_deep_report._fetch_investor_flow_snapshot") as flow,
    ):
        price.return_value = {
            "warnings": [],
            "current_price": 100.0,
            "day_change_pct": 1.2,
            "volume": 10000,
            "volume_ratio_20d": 1.5,
            "ma5": 99.0,
            "ma20": 96.0,
            "return_5d_pct": 4.0,
            "return_20d_pct": 12.0,
            "return_60d_pct": 28.0,
            "pct_from_52w_high": -15.0,
            "prior_20d_high": 101.0,
            "gap_up_pct": 0.5,
            "close_location_pct": 70.0,
            "trend": "UP",
            "ohlcv_tail": [{"date": "2026-05-12", "close": 100.0}],
        }
        news.return_value = {
            "status": "OK",
            "sentiment_score": 0.25,
            "headlines": [{"title": "real headline", "score": 0.25}],
            "warnings": [],
        }
        flow.return_value = {
            "valid": True,
            "type": "KR",
            "source": "test",
            "whale_score": 64.0,
            "foreigner": 1500000000.0,
            "institution": 700000000.0,
            "retail": -2200000000.0,
            "dominant": "외인",
            "whale_trend": "↗ 순매수",
            "warnings": [],
        }

        reports = build_top_deep_reports(
            scan_rows=[
                {
                    "ticker": "005930.KS",
                    "stock_name": "삼성전자",
                    "Decision Score": 88.0,
                    "매수가(-2%)": "73,200",
                }
            ],
            planner_payload={
                "decisions": [
                    {
                        "ticker": "005930.KS",
                        "decision": "PRIORITY_WATCHLIST",
                        "priority_rank": 1,
                        "loss_risk_score": 42.0,
                        "relative_rank_score": 77.5,
                        "expected_return_1d_pct": 1.1,
                        "expected_return_3d_pct": 2.3,
                        "theme_risk": ["LOSS_RISK_SOFT_CAP"],
                    }
                ]
            },
            run_id="RUN-TEST",
            market="KOSPI",
            scan_mode="SWING",
            top_n=5,
        )

    assert len(reports) == 1
    report = reports[0]
    assert report["report_id"] == "RUN-TEST:005930.KS:top_deep_report_v1"
    assert report["signal_label"] == "PRIMARY_BUY"
    assert report["selection_alignment"]["raw_scan_rank"] == 1
    assert report["selection_alignment"]["source_order"] == "top5_main_plus_exception_addon"
    assert report["selection_alignment"]["analysis_section"] == "Top5"
    assert report["loss_risk_score"] == 42.0
    assert report["buy_score"] == 77.5
    assert report["accuracy"] is not None
    assert report["prediction"]["expected_return_3d_pct"] == 2.3
    assert report["selection_thesis"]["status"] == "planner_priority"
    assert report["selection_thesis"]["scanner_basis"]["expected_return_3d_pct"] == 2.3
    assert "selection_thesis" in report["trade_plan"]
    assert report["risk_overrides"]["severity"] in {"none", "soft"}
    assert report["entry_action"]["judgment"]["action"] in {"즉시 매수 가능", "조건부 매수 가능"}
    assert report["trade_plan"]["target_tp_pct"] is not None
    assert report["trade_plan"]["stop_sl_pct"] is not None
    assert report["trade_plan"]["hold_days"] is not None
    assert report["trade_plan"]["entry_policy"]
    assert report["trade_plan"]["entry_reference_price"] == 73200.0
    assert report["trade_plan"]["target_price"] is not None
    assert report["trade_plan"]["stop_price"] is not None
    assert report["trade_plan"]["target_price"] != report["trade_plan"]["stop_price"]
    assert report["trade_plan"]["risk_reward"] is not None
    assert report["trade_plan"]["entry_strategy"]["primary_condition"]
    assert report["trade_plan"]["entry_strategy"]["pullback_support_price"] == 99.0
    assert report["trade_plan"]["risk_management"]["stop_condition"]
    assert report["trade_plan"]["data_coverage"]["coverage_pct"] > 0
    assert report["flow"]["foreigner"] == 1500000000.0
    assert report["flow"]["retail"] == -2200000000.0
    readiness = report["trade_plan"]["readiness_analysis"]
    assert readiness["quality"]["grade"] != "N/A"
    assert readiness["upside"]["chase_risk_level"] == "낮음"
    assert readiness["final_buy_judgment"]["action"] in {"즉시 매수 가능", "조건부 매수 가능"}
    assert report["price"]["trend"] == "UP"
    assert report["news"]["headlines"][0]["title"] == "real headline"


def test_build_top_deep_reports_maps_korean_theme_field():
    with (
        patch("modules.top_deep_report._fetch_price_snapshot") as price,
        patch("modules.top_deep_report._fetch_news_snapshot") as news,
        patch("modules.top_deep_report._fetch_investor_flow_snapshot") as flow,
    ):
        price.return_value = {"warnings": [], "current_price": 100.0, "day_change_pct": 0.0}
        news.return_value = {"status": "OK", "headlines": [], "warnings": []}
        flow.return_value = {"valid": True, "type": "KR", "source": "test", "warnings": []}

        reports = build_top_deep_reports(
            scan_rows=[
                {
                    "ticker": "271560.KS",
                    "종목명": "오리온",
                    "테마": "소비재/유통",
                    "Decision Score": 55.3,
                }
            ],
            planner_payload={"decisions": []},
            run_id="RUN-THEME",
            market="KOSPI",
            scan_mode="SWING",
            top_n=5,
        )

    assert reports[0]["theme"]["primary_theme"] == "소비재/유통"


def test_upsert_reports_to_supabase_filters_columns_when_schema_cache_empty():
    captured = {}

    class FakeTable:
        def delete(self):
            return self

        def eq(self, *_args):
            return self

        def upsert(self, rows, **_kwargs):
            captured["rows"] = rows
            return self

        def execute(self):
            return type("Response", (), {"data": []})()

    class FakeClient:
        def table(self, _name):
            return FakeTable()

    class FakeDB:
        client = FakeClient()

        def _filter_payload_to_existing_columns(self, _table, payload):
            return dict(payload)

    with patch("modules.db_manager.DBManager", return_value=FakeDB()):
        result = upsert_reports_to_supabase(
            [
                {
                    "report_id": "RUN-X:005930.KS:top_deep_report_v1",
                    "report_version": "top_deep_report_v1",
                    "run_id": "RUN-X",
                    "ticker": "005930.KS",
                    "generated_at": "2026-05-13T00:00:00+00:00",
                    "flow": {"foreigner": 1},
                }
            ]
        )

    assert result["rows_upserted"] == 1
    assert captured["rows"][0]["flow"] == {"foreigner": 1}


def test_investor_flow_fetches_breakdown_when_exception_has_score_only():
    with patch("modules.quant_analysis.QuantStrategy") as strategy:
        strategy.return_value.get_investor_flows.return_value = {
            "valid": True,
            "flow_source": "naver",
            "whale_score": 72.0,
            "foreigner": 1200000,
            "institution": -300000,
            "retail": -900000,
            "dominant": "외인",
        }

        flow = _fetch_investor_flow_snapshot(
            "278470.KS",
            {"ticker": "278470.KS", "decision": "EXCEPTION_LEADER"},
            {"whale_score": 80.0},
        )

    assert flow["source"] == "naver"
    assert flow["foreigner"] == 1200000.0
    assert flow["institution"] == -300000.0
    assert flow["retail"] == -900000.0


def test_build_top_deep_reports_follows_watchlist_meta_order_when_decisions_empty():
    with (
        patch("modules.top_deep_report._fetch_price_snapshot") as price,
        patch("modules.top_deep_report._fetch_news_snapshot") as news,
        patch("modules.top_deep_report._fetch_investor_flow_snapshot") as flow,
    ):
        price.return_value = {"warnings": [], "ohlcv_tail": []}
        news.return_value = {"status": "OK", "sentiment_score": 0.0, "headlines": [], "warnings": []}
        flow.return_value = {"valid": False, "warnings": ["test_unavailable"]}

        reports = build_top_deep_reports(
            scan_rows=[
                {"ticker": "CCC.KQ", "Decision Score": 99.0},
                {"ticker": "AAA.KQ", "Decision Score": 10.0},
                {"ticker": "BBB.KQ", "Decision Score": 20.0},
            ],
            planner_payload={
                "decisions": [],
                "watchlist_meta": [
                    {"ticker": "AAA.KQ", "decision": "WATCHLIST_ONLY", "decision_score": 10.0},
                    {"ticker": "BBB.KQ", "decision": "WATCHLIST_ONLY", "decision_score": 20.0},
                    {"ticker": "CCC.KQ", "decision": "WATCHLIST_ONLY", "decision_score": 99.0},
                ],
            },
            run_id="RUN-WATCH",
            market="KOSDAQ",
            scan_mode="SWING",
            top_n=3,
        )

    assert [row["ticker"] for row in reports] == ["AAA.KQ", "BBB.KQ", "CCC.KQ"]
    assert [row["rank"] for row in reports] == [1, 2, 3]


def test_build_top_deep_reports_adds_exception_after_top5_main():
    with (
        patch("modules.top_deep_report._fetch_price_snapshot") as price,
        patch("modules.top_deep_report._fetch_news_snapshot") as news,
        patch("modules.top_deep_report._fetch_investor_flow_snapshot") as flow,
    ):
        price.return_value = {"warnings": [], "ohlcv_tail": []}
        news.return_value = {"status": "OK", "sentiment_score": 0.0, "headlines": [], "warnings": []}
        flow.return_value = {"valid": False, "warnings": ["test_unavailable"]}

        reports = build_top_deep_reports(
            scan_rows=[
                {"ticker": "RAW.KS", "Decision Score": 99.0},
                {"ticker": "EX.KS", "Decision Score": 70.0},
                {"ticker": "TOP.KS", "Decision Score": 88.0},
            ],
            planner_payload={
                "decisions": [
                    {"ticker": "TOP.KS", "decision": "PRIORITY_WATCHLIST", "priority_rank": 1, "relative_rank_score": 70.0},
                    {"ticker": "EX.KS", "decision": "WATCHLIST", "decision_bucket": "exception_leader", "priority_rank": 2, "relative_rank_score": 50.0},
                    {"ticker": "RAW.KS", "decision": "WATCHLIST", "priority_rank": 3, "relative_rank_score": 30.0},
                ],
            },
            run_id="RUN-EXEC",
            market="KOSPI",
            scan_mode="SWING",
            top_n=3,
        )

    assert [row["ticker"] for row in reports] == ["TOP.KS", "RAW.KS", "EX.KS"]
    assert reports[0]["selection_alignment"]["analysis_section"] == "Top5"
    assert reports[-1]["selection_alignment"]["analysis_section"] == "Exception Leader"
    assert reports[-1]["selection_alignment"]["source_order"] == "top5_main_plus_exception_addon"


def test_top_deep_report_does_not_promote_material_risk_to_primary_buy():
    with (
        patch("modules.top_deep_report._fetch_price_snapshot") as price,
        patch("modules.top_deep_report._fetch_news_snapshot") as news,
        patch("modules.top_deep_report._fetch_investor_flow_snapshot") as flow,
    ):
        price.return_value = {
            "warnings": [],
            "current_price": 47800.0,
            "day_change_pct": 10.78,
            "volume_ratio_20d": 1.27,
            "ma5": 46200.0,
            "ma20": 45949.0,
            "return_5d_pct": 12.0,
            "return_20d_pct": 18.0,
            "return_60d_pct": 24.0,
            "pct_from_52w_high": -12.0,
            "prior_20d_high": 55400.0,
            "close_location_pct": 70.0,
            "ohlcv_tail": [{"date": "2026-05-15", "close": 47800.0}],
        }
        news.return_value = {
            "status": "OK",
            "sentiment_score": -0.4,
            "headlines": [{"title": "한화솔루션, 유상증자 일정 재확정...신주 상장 7월"}],
            "warnings": [],
        }
        flow.return_value = {"valid": False, "warnings": ["test_unavailable"]}

        reports = build_top_deep_reports(
            scan_rows=[
                {
                    "ticker": "009830.KS",
                    "stock_name": "한화솔루션",
                    "Decision Score": 89.5,
                    "매수가(-2%)": "46,844",
                    "전일비": 10.78,
                }
            ],
            planner_payload={
                "decisions": [
                    {
                        "ticker": "009830.KS",
                        "decision": "PRIORITY_WATCHLIST",
                        "priority_rank": 3,
                        "loss_risk_score": 26.656,
                        "relative_rank_score": 68.4743,
                        "expected_return_1d_pct": 0.01,
                        "expected_return_3d_pct": 0.02,
                        "expected_edge_score": 0.14,
                        "theme_risk": ["EXPECTED_EDGE_PRIORITY_GUARD_SOFT"],
                    }
                ]
            },
            run_id="RUN-RISK",
            market="KOSPI",
            scan_mode="SWING",
            top_n=5,
        )

    report = reports[0]
    readiness = report["trade_plan"]["readiness_analysis"]
    assert report["signal_label"] == "NO_BUY"
    assert readiness["final_buy_judgment"]["action"] == "매수 금지"
    assert report["entry_action"]["judgment"]["action"] == "매수 금지"
    assert any("특수 리스크" in warning for warning in readiness["warnings"])


def test_top_deep_report_prefers_validated_winner_profile_over_raw_priority():
    with (
        patch("modules.top_deep_report._fetch_price_snapshot") as price,
        patch("modules.top_deep_report._fetch_news_snapshot") as news,
        patch("modules.top_deep_report._fetch_investor_flow_snapshot") as flow,
    ):
        price.return_value = {"warnings": [], "current_price": 100.0, "ohlcv_tail": []}
        news.return_value = {"status": "OK", "sentiment_score": 0.0, "headlines": [], "warnings": []}
        flow.return_value = {"valid": False, "warnings": ["test_unavailable"]}

        reports = build_top_deep_reports(
            scan_rows=[
                {"ticker": "BAD.KS", "stock_name": "Bad", "Decision Score": 95.0},
                {"ticker": "GOOD.KS", "stock_name": "Good", "Decision Score": 88.0},
            ],
            planner_payload={
                "decisions": [
                    {
                        "ticker": "BAD.KS",
                        "decision": "PRIORITY_WATCHLIST",
                        "priority_rank": 1,
                        "relative_rank_score": 80.0,
                        "expected_edge_score": 0.1,
                        "prob_clean": 30.0,
                        "alpha_score": 68.0,
                    },
                    {
                        "ticker": "GOOD.KS",
                        "decision": "PRIORITY_WATCHLIST",
                        "priority_rank": 4,
                        "relative_rank_score": 65.0,
                        "expected_edge_score": 7.2,
                        "prob_clean": 41.0,
                        "alpha_score": 76.0,
                    },
                ],
            },
            run_id="RUN-VALIDATED",
            market="KOSPI",
            scan_mode="SWING",
            top_n=5,
        )

    assert [row["ticker"] for row in reports] == ["GOOD.KS"]
    profile = reports[0]["selection_alignment"]["validated_winner_profile"]
    assert profile["profile"] == "rank_top5__edge_ge_7"


def test_build_top_deep_reports_adds_planner_only_exception_leaders_up_to_five():
    with (
        patch("modules.top_deep_report._fetch_price_snapshot") as price,
        patch("modules.top_deep_report._fetch_news_snapshot") as news,
        patch("modules.top_deep_report._fetch_investor_flow_snapshot") as flow,
    ):
        price.return_value = {"warnings": [], "ohlcv_tail": []}
        news.return_value = {"status": "OK", "sentiment_score": 0.0, "headlines": [], "warnings": []}
        flow.return_value = {"valid": False, "warnings": ["test_unavailable"]}

        reports = build_top_deep_reports(
            scan_rows=[
                {"ticker": f"TOP{i}.KQ", "stock_name": f"Top {i}", "Decision Score": 100.0 - i}
                for i in range(1, 6)
            ],
            planner_payload={
                "decisions": [
                    {
                        "ticker": f"TOP{i}.KQ",
                        "decision": "PRIORITY_WATCHLIST",
                        "priority_rank": i,
                        "relative_rank_score": 90.0 - i,
                    }
                    for i in range(1, 6)
                ],
                "watchlist_meta": [
                    {
                        "ticker": f"EX{i}.KQ",
                        "stock_name": f"Exception {i}",
                        "risk_label": "EXCEPTION_LEADER",
                        "reason": "exception_leader_watchlist",
                        "priority_rank": 100 + i,
                        "relative_rank_score": 70.0 - i,
                    }
                    for i in range(1, 7)
                ],
            },
            run_id="RUN-PLANNER-EX",
            market="KOSDAQ",
            scan_mode="SWING",
            top_n=5,
        )

    assert [row["ticker"] for row in reports] == [f"TOP{i}.KQ" for i in range(1, 6)] + [
        f"EX{i}.KQ" for i in range(1, 6)
    ]
    assert len(reports) == 10
    assert [row["selection_alignment"]["analysis_section"] for row in reports[:5]] == ["Top5"] * 5
    assert [row["selection_alignment"]["analysis_section"] for row in reports[5:]] == ["Exception Leader"] * 5
