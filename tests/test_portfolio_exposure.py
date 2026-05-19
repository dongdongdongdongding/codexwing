from modules.portfolio_exposure import build_portfolio_exposure_summary, render_portfolio_exposure_lines


def test_portfolio_exposure_detects_duplicate_theme_and_sell_flow():
    rows = [
        {
            "ticker": "000001.KS",
            "market": "KOSPI",
            "selection_alignment": {"analysis_section": "Top5"},
            "theme": {"primary_theme": "전력기기"},
            "loss_risk_score": 70,
            "flow": {"foreigner_1d": -1000, "institution_1d": -500},
        },
        {
            "ticker": "000002.KS",
            "market": "KOSPI",
            "selection_alignment": {"analysis_section": "Exception Leader"},
            "theme": {"primary_theme": "전력기기"},
            "loss_risk_score": 68,
            "flow": {"foreigner_1d": -100, "institution_1d": 0},
        },
        {
            "ticker": "000003.KQ",
            "market": "KOSDAQ",
            "_analysis_section": "KOSDAQ Ordered Shadow",
            "theme": {"primary_theme": "반도체"},
            "loss_risk_score": 20,
            "flow": {"foreigner_1d": 100, "institution_1d": 200},
        },
    ]

    summary = build_portfolio_exposure_summary(rows, run_id="RUN-TEST")
    assert summary["version"] == "portfolio_exposure_v1"
    assert summary["candidate_count"] == 3
    assert summary["dominant_theme"]["label"] == "전력기기"
    assert summary["dominant_theme"]["count"] == 2
    assert "THEME_CROWDED" in summary["risk_flags"]
    assert "LOSS_RISK_CLUSTER" in summary["risk_flags"]
    assert "FLOW_SELL_CLUSTER" in summary["risk_flags"]
    assert summary["section_counts"]["Top5"] == 1
    assert summary["section_counts"]["Exception Leader"] == 1
    assert summary["section_counts"]["KOSDAQ Ordered Shadow"] == 1
    assert summary["flow_direction_counts"]["foreign_institution_sell"] == 2

    lines = render_portfolio_exposure_lines(summary)
    assert any("동일 테마" in line for line in lines)
    assert any("수급방향" in line for line in lines)


def test_portfolio_exposure_handles_diversified_mixed_market_rows():
    rows = [
        {"ticker": "000001.KS", "market": "KOSPI", "primary_theme": "조선", "loss_risk_score": 20},
        {"ticker": "000002.KQ", "market": "KOSDAQ", "primary_theme": "반도체", "loss_risk_score": 40},
        {"ticker": "AAPL", "market": "NASDAQ", "primary_theme": "AI", "loss_risk_score": 30},
    ]

    summary = build_portfolio_exposure_summary(rows)
    assert summary["interpretation"] == "diversified_or_insufficient_rows"
    assert "THEME_CROWDED" not in summary["risk_flags"]
    assert summary["market_counts"] == {"KOSPI": 1, "KOSDAQ": 1, "NASDAQ": 1}
