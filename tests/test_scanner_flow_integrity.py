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
