import pandas as pd

from multi_agent.tools.export_scan_archive_learning_dataset import _apply_quality_tier


def _gold_row(**overrides):
    row = {
        "ticker": "005930.KS",
        "outcome_status": "RESOLVED",
        "is_dummy_data": False,
        "validation_excluded": False,
        "feature_quality": "complete",
        "alpha_score": 82,
        "tech_score": 74,
        "ml_prob": 61.0,
        "whale_score": 55,
        "decision_score": 88.0,
        "volume_ratio": 2.3,
        "entry_reference_price": 51200.0,
        "return_5d_pct": 6.2,
    }
    row.update(overrides)
    return row


def test_gold_quality_tier_keeps_only_training_safe_rows():
    df = pd.DataFrame(
        [
            _gold_row(ticker="gold.KS"),
            _gold_row(ticker="missing.KS", volume_ratio=None),
            _gold_row(ticker="excluded.KS", validation_excluded=True),
            _gold_row(ticker="pending.KS", outcome_status="PENDING"),
        ]
    )

    result = _apply_quality_tier(df, "GOLD")

    assert result["ticker"].tolist() == ["gold.KS"]
    assert result["learning_quality_tier"].tolist() == ["gold"]


def test_silver_quality_tier_keeps_resolved_non_dummy_rows_for_diagnostics():
    df = pd.DataFrame(
        [
            _gold_row(ticker="complete.KS"),
            _gold_row(ticker="legacy.KS", feature_quality="incomplete", validation_excluded=True),
            _gold_row(ticker="dummy.KS", is_dummy_data=True),
            _gold_row(ticker="pending.KS", outcome_status="PENDING"),
        ]
    )

    result = _apply_quality_tier(df, "SILVER")

    assert result["ticker"].tolist() == ["complete.KS", "legacy.KS"]
    assert set(result["learning_quality_tier"]) == {"silver"}
