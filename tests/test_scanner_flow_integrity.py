import json

from modules.scan_integrity import build_scan_integrity_report, build_observed_factor_snapshots
from modules.scanner_services import _flow_persistence_fields


def test_flow_persistence_does_not_fabricate_zero_when_flow_missing():
    fields = _flow_persistence_fields(
        {"valid": False, "foreigner": 0, "institution": 0, "retail": 0},
        {"foreign_flow": 0.0, "institution_flow": 0.0, "retail_flow": 0.0},
    )

    assert fields["foreigner"] is None
    assert fields["institution"] is None
    assert fields["retail"] is None
    assert fields["foreigner_1d"] is None
    assert fields["whale_flow"] is None
    assert fields["flow_asof"] is None


def test_flow_persistence_preserves_real_zero_when_source_is_valid():
    fields = _flow_persistence_fields(
        {
            "valid": True,
            "flow_source": "pykrx_value",
            "flow_asof": "2026-05-20",
            "foreigner_1d": 0,
            "institution_1d": 100,
            "retail_1d": -100,
            "foreigner_3d": 10,
            "institution_3d": 90,
            "retail_3d": -100,
            "foreigner_10d": 50,
            "institution_10d": 150,
            "retail_10d": -200,
        }
    )

    assert fields["foreigner"] is None
    assert fields["foreigner_1d"] == 0
    assert fields["institution_1d"] == 100
    assert fields["flow_source"] == "pykrx_value"
    assert fields["flow_asof"] == "2026-05-20"


def test_scan_integrity_requires_kr_multi_window_flow_fields():
    snapshots = build_observed_factor_snapshots(
        run_id="RUN-FLOW",
        market="KOSPI",
        scan_mode="SWING",
        created_at="2026-05-20T00:00:00Z",
        results=[
            {
                "ticker": "000660.KS",
                "stock_name": "SK하이닉스",
                "decision_score": 90,
                "alpha_score": 80,
                "tech_score": 70,
                "ml_prob": 60,
                "whale_score": 55,
                "volume_ratio": 1.5,
                "day_return_pct": 1.2,
                "trend": "UP",
                "entry_reference_price": 100,
                "expected_edge_score": 7,
                "expected_return_1d_pct": 1,
                "expected_return_3d_pct": 3,
                "loss_risk_score": 30,
                "selection_lane": "5d",
                "primary_theme": "반도체",
                "theme_routing_path": "theme_master",
                "foreigner_1d": 1000,
                "institution_1d": 500,
                "retail_1d": -1500,
            }
        ],
    )
    report = build_scan_integrity_report(
        run_id="RUN-FLOW",
        market="KOSPI",
        scan_mode="SWING",
        snapshots=snapshots,
        raw_result_count=1,
        total_scans=1,
    )

    missing = report["missing_by_ticker"]["000660.KS"]
    assert "foreigner_3d" in missing
    assert "institution_10d" in missing
    assert "flow_asof" in missing
    assert "FACTOR_COMPLETENESS_BELOW_95" in report["quality_flags"]


def test_scan_integrity_accepts_display_aliases_from_raw_scanner_rows():
    snapshots = build_observed_factor_snapshots(
        run_id="RUN-ALIAS",
        market="KOSPI",
        scan_mode="SWING",
        created_at="2026-05-21T00:00:00Z",
        results=[
            {
                "티커": "353200.KS",
                "종목명": "대덕전자",
                "Decision Score": 100,
                "Antigrav": 100,
                "확신도": 82.9,
                "AI확률": "39.0%",
                "수급": "77.0점 🔥 당일+3일 순매수",
                "거래량": "✅ 3.20",
                "전일비": "+7.74%",
                "추세": "UP",
                "매수가(-2%)": "140,434",
                "expected_edge_score": 3.85,
                "expected_return_1d_pct": 0.27,
                "expected_return_3d_pct": 0.49,
                "loss_risk_score": 30,
                "_quant_signal": {"lane": "3d"},
                "테마": "전자부품/디스플레이",
                "_routing_path": "core_only",
                "foreigner_1d": -7309,
                "institution_1d": 35184,
                "retail_1d": -27875,
                "foreigner_3d": 105,
                "institution_3d": 96139,
                "retail_3d": -96244,
                "foreigner_10d": -162176,
                "institution_10d": 357179,
                "retail_10d": -195003,
                "flow_asof": "2026.05.20",
            }
        ],
    )
    report = build_scan_integrity_report(
        run_id="RUN-ALIAS",
        market="KOSPI",
        scan_mode="SWING",
        snapshots=snapshots,
        raw_result_count=1,
        total_scans=1,
    )

    factors = snapshots[0]["factors"]
    assert factors["tech_score"] == 82.9
    assert factors["ml_prob"] == "39.0%"
    assert factors["whale_score"] == "77.0점 🔥 당일+3일 순매수"
    assert factors["volume_ratio"] == "✅ 3.20"
    assert factors["selection_lane"] == "3d"
    assert report["feature_completeness"] == 1.0
    assert report["quality_flags"] == []


def test_scan_integrity_enriches_planner_only_rows_from_top_deep_reports(tmp_path):
    profile_path = tmp_path / "profile.json"
    top_deep_path = tmp_path / "top_deep.json"
    profile_path.write_text(
        json.dumps(
            {
                "exception_leaders": {
                    "watchlist_meta": [
                        {
                            "ticker": "128940.KS",
                            "stock_name": "한미약품",
                            "alpha_score": 77,
                            "tech_score": 68,
                            "ml_prob": 13.4,
                            "whale_score": 71,
                            "volume_ratio": 2.2,
                            "trend": "UP",
                            "loss_risk_score": 24,
                            "primary_theme": "제약/바이오",
                            "foreigner_1d": 1000,
                            "institution_1d": 2000,
                            "retail_1d": -3000,
                            "foreigner_3d": 1100,
                            "institution_3d": 2100,
                            "retail_3d": -3200,
                            "foreigner_10d": 1200,
                            "institution_10d": 2200,
                            "retail_10d": -3400,
                            "flow_asof": "2026.06.05",
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    top_deep_path.write_text(
        json.dumps(
            [
                {
                    "report_version": "top_deep_report_v1",
                    "ticker": "128940.KS",
                    "stock_name": "한미약품",
                    "day_change_pct": 2.14,
                    "scan_universe_admission": {
                        "probability_pct": 13.4,
                        "input_source_role": "legacy_rejected",
                        "feature_values": {"day_return_pct": 2.14},
                        "validation": {
                            "avg_1d_pct": 9.8,
                            "avg_3d_pct": 43.1,
                            "avg_max_high_5d_pct": 68.8,
                        },
                    },
                    "realized_expectancy_admission": {"expected_value_5d_pct": 68.8},
                    "trade_plan": {"entry_reference_price": 499000.0},
                    "selection_alignment": {"source_order": "scan_universe_admission_model"},
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    snapshots = build_observed_factor_snapshots(
        run_id="RUN-TOP",
        market="KOSPI",
        scan_mode="SWING",
        created_at="2026-06-05T00:00:00Z",
        results=[],
        bridge_info={"profile_diagnostics": str(profile_path)},
        top_deep_reports={"local_path": str(top_deep_path)},
    )
    report = build_scan_integrity_report(
        run_id="RUN-TOP",
        market="KOSPI",
        scan_mode="SWING",
        snapshots=snapshots,
        raw_result_count=0,
        total_scans=5,
    )

    factors = snapshots[0]["factors"]
    assert factors["decision_score"] == 13.4
    assert factors["day_return_pct"] == 2.14
    assert factors["entry_reference_price"] == 499000.0
    assert factors["expected_edge_score"] == 68.8
    assert factors["expected_return_1d_pct"] == 9.8
    assert factors["expected_return_3d_pct"] == 43.1
    assert factors["selection_lane"] == "scan_universe_admission_model"
    assert factors["theme_routing_path"] == "scan_universe_admission_model"
    assert report["feature_completeness"] == 1.0
    assert report["quality_flags"] == []


def test_scan_integrity_uses_top_deep_rows_as_displayed_candidate_set(tmp_path):
    profile_path = tmp_path / "profile.json"
    top_deep_path = tmp_path / "top_deep.json"
    profile_path.write_text(
        json.dumps(
            {
                "exception_leaders": {
                    "watchlist_meta": [
                        {
                            "ticker": "999999.KS",
                            "stock_name": "표시되지않는후보",
                            "decision": "EXCEPTION_LEADER",
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    top_deep_path.write_text(
        json.dumps(
            [
                {
                    "report_version": "top_deep_report_v1",
                    "rank": 1,
                    "ticker": "005930.KS",
                    "stock_name": "삼성전자",
                    "decision_score": 13.4,
                    "loss_risk_score": 24,
                    "scan_universe_admission": {"probability_pct": 13.4},
                    "selection_alignment": {
                        "analysis_section": "Admission Near Miss",
                        "analysis_section_rank": 1,
                        "source_order": "scan_universe_admission_model",
                    },
                    "price": {
                        "day_change_pct": -1.2,
                        "volume_ratio_20d": 1.4,
                        "trend": "UP",
                    },
                    "trade_plan": {"entry_reference_price": 100.0},
                    "theme": {
                        "primary_theme": "반도체",
                        "theme_routing_path": "theme_master",
                    },
                    "prediction": {
                        "expected_edge_score": 7,
                        "expected_return_1d_pct": 1,
                        "expected_return_3d_pct": 3,
                    },
                    "flow": {
                        "whale_score": 55,
                        "foreigner_1d": 1000,
                        "institution_1d": 500,
                        "retail_1d": -1500,
                        "foreigner_3d": 1100,
                        "institution_3d": 600,
                        "retail_3d": -1700,
                        "foreigner_10d": 1200,
                        "institution_10d": 700,
                        "retail_10d": -1900,
                        "flow_asof": "2026.06.05",
                    },
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    snapshots = build_observed_factor_snapshots(
        run_id="RUN-TOP-ONLY",
        market="KOSPI",
        scan_mode="SWING",
        created_at="2026-06-05T00:00:00Z",
        results=[],
        bridge_info={"profile_diagnostics": str(profile_path)},
        top_deep_reports={"local_path": str(top_deep_path)},
    )
    report = build_scan_integrity_report(
        run_id="RUN-TOP-ONLY",
        market="KOSPI",
        scan_mode="SWING",
        snapshots=snapshots,
        raw_result_count=0,
        total_scans=835,
        top_deep_reports={"count": 1},
    )

    assert [snapshot["ticker"] for snapshot in snapshots] == ["005930.KS"]
    assert snapshots[0]["factors"]["analysis_section"] == "Admission Near Miss"
    assert snapshots[0]["factors"]["ml_prob"] == 13.4
    assert report["section_counts"] == {"Admission Near Miss": 1}
    assert report["picked_count"] == 0
    assert report["field_not_applicable_counts"]["alpha_score"] == 1
    assert report["field_not_applicable_counts"]["tech_score"] == 1
    assert report["feature_completeness"] == 1.0
    assert report["quality_flags"] == []
