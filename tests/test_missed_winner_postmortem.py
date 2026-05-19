from modules.missed_winner_postmortem import (
    attach_reject_outcomes,
    build_missed_winner_postmortem,
    build_reject_rows_from_diagnostics,
    classify_missed_winner,
)


def test_classify_missed_winner_reports_score_theme_liquidity_and_no_signal():
    reasons = classify_missed_winner(
        {
            "ticker": "000001.KS",
            "priority_rank": 22,
            "decision_score": 70,
            "primary_theme": "",
            "volume_ratio": 0.4,
        }
    )

    assert "score_miss" in reasons
    assert "theme_miss" in reasons
    assert "liquidity_miss" in reasons

    no_signal = classify_missed_winner({"ticker": "000002.KQ", "primary_theme": "로봇"})
    assert "no_prior_signal" in no_signal


def test_build_reject_rows_from_diagnostics_and_attach_outcomes():
    rejects = build_reject_rows_from_diagnostics(
        [
            {
                "run_id": "RUN-1",
                "market": "KOSPI",
                "reject_details_by_symbol": {
                    "000001.KS": [{"stage": "liquidity_gate", "turnover": 1_000_000_000}],
                },
                "reject_reasons_by_symbol": {"000001.KS": ["LIQUIDITY_FILTER_FAIL"]},
            }
        ]
    )
    merged = attach_reject_outcomes(
        rejects,
        [{"run_id": "RUN-1", "ticker": "000001.KS", "return_1d_pct": 8.0}],
    )

    assert merged[0]["emitted"] is False
    assert merged[0]["outcome_available"] is True
    assert merged[0]["return_1d_pct"] == 8.0


def test_missed_winner_postmortem_reports_capture_and_reasons():
    report = build_missed_winner_postmortem(
        [
            {
                "run_id": "RUN-1",
                "market": "KOSPI",
                "ticker": "A.KS",
                "priority_rank": 1,
                "return_1d_pct": 6.0,
                "decision_score": 95,
                "primary_theme": "반도체",
            },
            {
                "run_id": "RUN-1",
                "market": "KOSPI",
                "ticker": "B.KS",
                "priority_rank": 9,
                "return_1d_pct": 7.0,
                "decision_score": 72,
                "primary_theme": "",
            },
        ],
        reject_rows=[
            {
                "run_id": "RUN-1",
                "market": "KOSPI",
                "ticker": "C.KS",
                "emitted": False,
                "return_1d_pct": 11.0,
                "reject_reasons": ["LIQUIDITY_FILTER_FAIL"],
                "outcome_available": True,
            },
            {
                "run_id": "RUN-1",
                "market": "KOSDAQ",
                "ticker": "D.KQ",
                "emitted": False,
                "reject_reasons": ["FETCH_DATA_FAIL"],
                "outcome_available": False,
            },
        ],
    )

    metric = report["metrics"]["KOSPI_1d_plus5"]
    assert metric["winner_count"] == 3
    assert metric["top5_capture_count"] == 1
    assert metric["top5_capture_rate_pct"] == 33.3333
    assert metric["emitted_capture_rate_pct"] == 66.6667
    assert metric["miss_reason_counts"]["filter_miss"] == 1
    assert metric["miss_reason_counts"]["score_miss"] >= 1
    assert report["reject_rows_without_outcomes"] == 1
    assert any(item["reason"] == "reject_outcome_gap" for item in report["proposed_rule_changes"])
