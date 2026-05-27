import pandas as pd

from multi_agent.tools.report_feature_combo_watchlist import evaluate_watch_rules


def _row(day, ticker, alpha, ml, ret5, rank=1, exact=True):
    return {
        "trade_date": day,
        "ticker": ticker,
        "market2": "KOSPI",
        "priority_rank": rank,
        "exception_leader": False,
        "ordered_path_exact": exact,
        "alpha_score": alpha,
        "ml_prob": ml,
        "return_1d_pct": 0.5,
        "return_3d_pct": 2.0,
        "return_5d_pct": ret5,
        "bad_path": ret5 < 0,
        "stop5_proxy": False,
    }


def test_pinned_feature_combo_watch_filters_exact_path_and_conditions():
    df = pd.DataFrame(
        [
            _row("2026-05-01", "000001.KS", 60, 20, 6),
            _row("2026-05-02", "000002.KS", 66, 29, 7),
            _row("2026-05-03", "000003.KS", 70, 20, -3),
            _row("2026-05-04", "000004.KS", 60, 40, 5),
            _row("2026-05-05", "000005.KS", 61, 21, 9, exact=False),
            _row("2026-05-06", "000006.KS", 62, 22, 8),
        ]
    )
    rule = {
        "rule_id": "test_low_alpha_ml",
        "issue_id": "test",
        "market": "KOSPI",
        "scope": "top5_exception",
        "quality_scope": "exact_path",
        "conditions": [
            {"feature": "alpha_score", "op": "<=", "value": 67.0},
            {"feature": "ml_prob", "op": "<=", "value": 30.45},
        ],
        "gate": {
            "min_train_n": 1,
            "min_train_days": 1,
            "min_train_win_5d_pct": 50.0,
            "min_test_n": 1,
            "min_test_days": 1,
            "min_test_win_5d_pct": 50.0,
            "min_test_avg_5d_pct": 0.0,
            "max_test_bad_path_pct": 50.0,
            "max_test_stop5_pct": 50.0,
        },
    }

    rows = evaluate_watch_rules(df, [rule])

    assert rows[0]["all"]["n"] == 3
    assert rows[0]["all"]["win_5d_pct"] == 100.0
    assert rows[0]["all"]["early_drop_1d_pct"] == 0.0
    assert rows[0]["all"]["loss_5d_pct"] == 0.0
    assert rows[0]["missing_features"] == []
    assert rows[0]["status"] == "review_candidate"


def test_pinned_feature_combo_watch_blocks_missing_feature():
    df = pd.DataFrame([_row("2026-05-01", "000001.KS", 60, 20, 6)]).drop(columns=["ml_prob"])
    rule = {
        "rule_id": "missing_ml",
        "market": "KOSPI",
        "scope": "top5_exception",
        "quality_scope": "exact_path",
        "conditions": [{"feature": "ml_prob", "op": "<=", "value": 30.45}],
        "gate": {},
    }

    rows = evaluate_watch_rules(df, [rule])

    assert rows[0]["status"] == "blocked_missing_feature"
    assert rows[0]["missing_features"] == ["ml_prob"]
