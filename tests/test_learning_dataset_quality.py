import pandas as pd

from multi_agent.tools.export_scan_archive_learning_dataset import _apply_quality_tier, _dedupe_archive_rows


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


def test_dedupe_archive_rows_prefers_clean_latest_outcome_row():
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-A",
                "ticker": "005930.KS",
                "recommended_at": "2026-05-01T00:00:00+00:00",
                "source_ref": "local_returns:return_3d_pct",
                "scan_mode": "INTRADAY",
                "market": None,
                "market_type": "KR",
                "outcome_path_warnings": "['partial_intraday_bar_contains_pre_scan_range']",
                "performance_updated_at": "2026-05-02T00:00:00+00:00",
                "created_at": "2026-05-02T00:00:00+00:00",
            },
            {
                "id": 2,
                "run_id": "RUN-A",
                "ticker": "005930.KS",
                "recommended_at": "2026-05-01T00:00:00+00:00",
                "source_ref": "local_returns:return_3d_pct",
                "scan_mode": "INTRADAY",
                "market": "KOSPI",
                "market_type": "KR",
                "outcome_path_warnings": "['post_scan_intraday_empty']",
                "performance_updated_at": "2026-05-01T00:00:00+00:00",
                "created_at": "2026-05-01T00:00:00+00:00",
            },
        ]
    )

    result, removed = _dedupe_archive_rows(df)

    assert removed == 1
    assert result["id"].tolist() == [2]
    assert "partial_intraday_bar_contains_pre_scan_range" not in result["outcome_path_warnings"].iloc[0]


def test_dedupe_archive_rows_keeps_distinct_source_refs():
    df = pd.DataFrame(
        [
            _gold_row(
                run_id="RUN-A",
                source_ref="planner_handoff.json#005930.KS",
                recommended_at="2026-05-01T00:00:00+00:00",
                scan_mode="SWING",
            ),
            _gold_row(
                run_id="RUN-A",
                source_ref="planner_handoff.watchlist_meta#005930.KS",
                recommended_at="2026-05-01T00:00:00+00:00",
                scan_mode="SWING",
            ),
        ]
    )

    result, removed = _dedupe_archive_rows(df)

    assert removed == 0
    assert len(result) == 2


def test_resolved_missing_outcomes_are_unknown_not_losses():
    from multi_agent.tools.export_scan_archive_learning_dataset import observed_label
    values = pd.Series([None, float('nan'), float('inf'), float('-inf'), -2., 0., 3., 5.])
    resolved = pd.Series([True]*7 + [False])
    result = observed_label(values, values.gt(0), resolved)
    assert result.iloc[:4].isna().all()
    assert result.iloc[4:7].tolist() == [0, 0, 1]
    assert pd.isna(result.iloc[7])


def test_export_main_preserves_missing_labels_in_csv_and_json(tmp_path, monkeypatch):
    import json
    import sys
    from types import SimpleNamespace
    from multi_agent.tools import export_scan_archive_learning_dataset as module
    from modules import db_manager
    rows = [
        _gold_row(ticker='MISSING.KS', return_1d_pct=None, return_3d_pct=None, return_close_pct=None),
        _gold_row(ticker='LOSS.KS', return_1d_pct=-1., return_3d_pct=-2., return_close_pct=-.5),
        _gold_row(ticker='PENDING.KS', outcome_status='PENDING', return_1d_pct=10., return_3d_pct=12., return_close_pct=5.),
    ]
    class Query:
        def table(self, *_): return self
        def select(self, *_): return self
        def order(self, *_, **kw): return self
        def range(self, *_): return self
        def execute(self): return SimpleNamespace(data=rows)
    monkeypatch.setattr(db_manager, 'DBManager', lambda: SimpleNamespace(client=Query()))
    monkeypatch.setattr(sys, 'argv', ['export', '--output-dir', str(tmp_path)])
    module.main()
    csv = pd.read_csv(tmp_path/'scan_archive_learning_dataset_all.csv').set_index('ticker')
    js = {row['ticker']: row for row in json.loads((tmp_path/'scan_archive_learning_dataset_all.json').read_text())}
    for col in ['label_win_close', 'label_win_1d', 'label_win_3d']:
        assert pd.isna(csv.loc['MISSING.KS', col]) and js['MISSING.KS'][col] is None
        assert csv.loc['LOSS.KS', col] == 0 and js['LOSS.KS'][col] == 0
        assert pd.isna(csv.loc['PENDING.KS', col]) and js['PENDING.KS'][col] is None
