import pandas as pd

from multi_agent.tools.train_scan_universe_admission_challenger import (
    fetch_rows,
    LABEL_SPECS,
    candidate_verdict,
    current_top_indices,
    kis_feature_readiness,
    label_series,
    metrics,
    prepare_dataset,
    rank_candidate_results,
    top_indices_by_run,
)
import multi_agent.tools.train_scan_universe_admission_challenger as trainer


def _spec(name):
    return next(item for item in LABEL_SPECS if item.name == name)


def test_prepare_dataset_and_labels_use_scan_universe_path_fields():
    raw = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-A",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "emitted",
                "priority_rank": 1,
                "return_1d_pct": 1.0,
                "return_3d_pct": 2.0,
                "return_5d_pct": 3.0,
                "min_low_return_5d_pct": -2.0,
                "target_before_stop_5d": True,
                "stop_before_target_5d": False,
            },
            {
                "id": 2,
                "run_id": "RUN-A",
                "ticker": "000002.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "rejected",
                "return_1d_pct": -1.0,
                "return_3d_pct": -2.0,
                "return_5d_pct": -3.0,
                "min_low_return_5d_pct": -6.0,
                "target_before_stop_5d": False,
                "stop_before_target_5d": True,
            },
        ]
    )

    df, sanity = prepare_dataset(raw)
    target, valid = label_series(df, _spec("target_first_sustain_5d"))
    clean, clean_valid = label_series(df, _spec("sustain_1_3_5_lowdd"))

    assert sanity["removed_rows"] == 0
    assert valid.tolist() == [True, True]
    assert target.tolist() == [True, False]
    assert clean_valid.tolist() == [True, True]
    assert clean.tolist() == [True, False]
    assert df["bad_path"].tolist() == [False, True]


def test_top_indices_and_metrics_report_all_horizons():
    raw = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-A",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "emitted",
                "priority_rank": 1,
                "decision_score": 10,
                "return_1d_pct": 1.0,
                "return_3d_pct": 3.0,
                "return_5d_pct": 5.0,
                "min_low_return_5d_pct": -1.0,
                "max_high_return_5d_pct": 7.0,
                "target_before_stop_5d": True,
                "stop_before_target_5d": False,
            },
            {
                "id": 2,
                "run_id": "RUN-A",
                "ticker": "000002.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "emitted",
                "priority_rank": 2,
                "decision_score": 20,
                "return_1d_pct": -2.0,
                "return_3d_pct": -4.0,
                "return_5d_pct": -6.0,
                "min_low_return_5d_pct": -8.0,
                "max_high_return_5d_pct": 1.0,
                "target_before_stop_5d": False,
                "stop_before_target_5d": True,
            },
        ]
    )
    df, _sanity = prepare_dataset(raw)
    label, _valid = label_series(df, _spec("pos_5d"))
    idx = top_indices_by_run(df, pd.Series([0.9, 0.1], index=df.index), 1)
    current_idx = current_top_indices(df, 1, include_exception=False)

    got = metrics(df, idx, label)
    current = metrics(df, current_idx, label)

    assert got["n"] == 1
    assert got["win_1d_pct"] == 100.0
    assert got["avg_5d_pct"] == 5.0
    assert got["min_5d_pct"] == 5.0
    assert got["max_5d_pct"] == 5.0
    assert got["target_before_stop_5d_pct"] == 100.0
    assert current["avg_5d_pct"] == 5.0


def test_touch_labels_use_entry_price_high_and_guard_low_path():
    raw = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-A",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "max_high_return_5d_pct": 12.0,
                "min_low_return_5d_pct": -4.9,
            },
            {
                "id": 2,
                "run_id": "RUN-A",
                "ticker": "000002.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "max_high_return_5d_pct": 12.0,
                "min_low_return_5d_pct": -5.1,
            },
            {
                "id": 3,
                "run_id": "RUN-A",
                "ticker": "000003.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "max_high_return_5d_pct": 4.0,
                "min_low_return_5d_pct": -1.0,
            },
        ]
    )

    df, _sanity = prepare_dataset(raw)
    touch10, valid = label_series(df, _spec("touch10_5d"))
    touch10_guard, guard_valid = label_series(df, _spec("touch10_guard_5d"))
    touch5_guard, _ = label_series(df, _spec("touch5_guard_5d"))

    assert valid.tolist() == [True, True, True]
    assert guard_valid.tolist() == [True, True, True]
    assert touch10.tolist() == [True, True, False]
    assert touch10_guard.tolist() == [True, False, False]
    assert touch5_guard.tolist() == [True, False, False]


def test_fetch_rows_clamps_supabase_page_size_to_1000(monkeypatch):
    calls = []
    rows = [{"id": i, "ticker": f"{i:06d}.KS", "market": "KOSPI", "scan_mode": "SWING"} for i in range(1, 1002)]

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self):
            self._last_id = 0
            self._limit = None

        def select(self, _cols):
            return self

        def order(self, _field):
            return self

        def gt(self, _field, value):
            self._last_id = int(value)
            return self

        def limit(self, value):
            self._limit = int(value)
            calls.append(self._limit)
            return self

        def eq(self, _field, _value):
            return self

        def execute(self):
            batch = [row for row in rows if row["id"] > self._last_id][: self._limit]
            return Result(batch)

    class Client:
        def table(self, _table):
            return Query()

    class FakeDB:
        client = Client()

    monkeypatch.setattr(trainer, "DBManager", lambda: FakeDB())

    got = fetch_rows(market="ALL", scan_mode="ALL", page_size=2000)

    assert len(got) == 1001
    assert calls == [1000, 1000]


def test_fetch_rows_applies_chunk_filters_and_limit(monkeypatch):
    calls = {"eq": [], "gte": [], "lte": [], "gt": [], "limit": []}
    rows = [
        {"id": i, "ticker": f"{i:06d}.KS", "market": "KOSPI", "scan_mode": "SWING", "base_trade_date": "2026-05-21"}
        for i in range(100, 111)
    ]

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self):
            self._last_id = 0
            self._limit = None
            self._max_id = None

        def select(self, _cols):
            return self

        def order(self, _field):
            return self

        def gt(self, field, value):
            calls["gt"].append((field, value))
            self._last_id = int(value)
            return self

        def gte(self, field, value):
            calls["gte"].append((field, value))
            return self

        def lte(self, field, value):
            calls["lte"].append((field, value))
            if field == "id":
                self._max_id = int(value)
            return self

        def limit(self, value):
            calls["limit"].append(int(value))
            self._limit = int(value)
            return self

        def eq(self, field, value):
            calls["eq"].append((field, value))
            return self

        def execute(self):
            batch = [row for row in rows if row["id"] > self._last_id and (self._max_id is None or row["id"] <= self._max_id)]
            return Result(batch[: self._limit])

    class Client:
        def table(self, _table):
            return Query()

    class FakeDB:
        client = Client()

    monkeypatch.setattr(trainer, "DBManager", lambda: FakeDB())

    got = fetch_rows(
        market="KOSPI",
        scan_mode="SWING",
        page_size=3,
        min_id=101,
        max_id=109,
        min_base_date="2026-05-20",
        max_base_date="2026-05-22",
        limit=5,
    )

    assert got["id"].tolist() == [101, 102, 103, 104, 105]
    assert calls["gt"][0] == ("id", 100)
    assert ("id", 109) in calls["lte"]
    assert ("market", "KOSPI") in calls["eq"]
    assert ("scan_mode", "SWING") in calls["eq"]
    assert ("base_trade_date", "2026-05-20") in calls["gte"]
    assert ("base_trade_date", "2026-05-22") in calls["lte"]
    assert calls["limit"][:2] == [3, 3]


def test_fetch_rows_retries_statement_timeout_with_smaller_page(monkeypatch):
    calls = {"limit": []}
    rows = [
        {"id": 1, "ticker": "000001.KS", "market": "KOSPI", "scan_mode": "SWING"},
        {"id": 2, "ticker": "000002.KS", "market": "KOSPI", "scan_mode": "SWING"},
    ]

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        failures = 0

        def __init__(self):
            self._last_id = 0
            self._limit = None

        def select(self, _cols):
            return self

        def order(self, _field):
            return self

        def gt(self, _field, value):
            self._last_id = int(value)
            return self

        def limit(self, value):
            self._limit = int(value)
            calls["limit"].append(self._limit)
            return self

        def eq(self, _field, _value):
            return self

        def execute(self):
            if self._limit == 1000 and Query.failures == 0:
                Query.failures += 1
                raise RuntimeError("57014 canceling statement due to statement timeout")
            batch = [row for row in rows if row["id"] > self._last_id][: self._limit]
            return Result(batch)

    class Client:
        def table(self, _table):
            return Query()

    class FakeDB:
        client = Client()

    monkeypatch.setattr(trainer, "DBManager", lambda: FakeDB())

    got = fetch_rows(market="ALL", scan_mode="ALL", page_size=1000)

    assert got["id"].tolist() == [1, 2]
    assert calls["limit"][:2] == [1000, 500]


def test_prepare_dataset_filters_impossible_kr_return_labels():
    raw = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-A",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "return_1d_pct": 1.0,
                "return_3d_pct": 2.0,
                "return_5d_pct": 3.0,
            },
            {
                "id": 2,
                "run_id": "RUN-A",
                "ticker": "000002.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "return_1d_pct": 900.0,
                "return_3d_pct": 900.0,
                "return_5d_pct": 900.0,
            },
        ]
    )

    df, sanity = prepare_dataset(raw)

    assert df["ticker"].tolist() == ["000001.KS"]
    assert sanity["removed_rows"] == 1
    assert sanity["column_violations"]["return_1d_pct"] == 1


def test_prepare_dataset_empty_result_still_returns_sanity_tuple():
    raw = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "market": "NASDAQ",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
            }
        ]
    )

    df, sanity = prepare_dataset(raw)

    assert df.empty
    assert sanity["removed_rows"] == 0


def test_prepare_dataset_flattens_kis_sidecar_and_prefilter_features():
    raw = pd.DataFrame(
        [
            {
                "id": 1,
                "run_id": "RUN-KIS",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20",
                "row_role": "emitted",
                "return_5d_pct": 2.0,
                "feature_snapshot": {
                    "kis_sidecar": {
                        "contract_version": "kis_operational_contract_v1",
                        "feature_origin": "kis_openapi_sidecar",
                        "coverage": {"quote_snapshot": True, "daily_ohlcv": True, "news_titles": True, "stock_info": True},
                        "replacement_readiness": {"model_sidecar_ready": True, "production_replacement_ready": False},
                        "news_contract": {
                            "checked": True,
                            "source_status": "ok",
                            "news_count": 1,
                            "rows": [{"title": "AI 반도체 공급 계약 수주"}],
                        },
                        "stock_info_contract": {
                            "checked": True,
                            "sector_name": "semiconductor",
                            "standard_industry_code": "C261",
                        },
                        "model_candidate_features": {
                            "kis_value_traded": 123456789.0,
                            "kis_daily_return_5d_pct": 3.4,
                            "kis_stock_sector_name": "semiconductor",
                        },
                    },
                    "kis_operational_prefilter": {
                        "feature_origin": "kis_openapi_prefilter",
                        "snapshot_feature_version": "kis_operational_prefilter_snapshot_v1",
                        "sources": ["volume_rank", "vi_status"],
                        "rank": {"volume_rank": 2},
                        "selection_score": 91.25,
                        "vi_triggered": True,
                        "quote_ok": True,
                        "quote": {"source_status": "ok", "value_traded": 987654321.0, "prev_volume_ratio": 155.2},
                        "flow_ok": True,
                        "flow": {"valid": True, "whale_score": 71.0, "foreigner_1d": 10, "institution_1d": 20},
                        "score_components": {"value_traded": 20.0, "vi_triggered": 8.0},
                    },
                },
            }
        ]
    )

    df, _sanity = prepare_dataset(raw)
    feature_map = trainer.feature_sets(df)

    assert df.loc[df.index[0], "kis_sidecar_present"] == 1.0
    assert df.loc[df.index[0], "kis_sidecar_model_ready"] == 1.0
    assert df.loc[df.index[0], "kis_value_traded"] == 123456789.0
    assert df.loc[df.index[0], "kis_daily_return_5d_pct"] == 3.4
    assert df.loc[df.index[0], "kis_stock_sector_name"] == "semiconductor"
    assert df.loc[df.index[0], "kis_theme_news_kis_backed"] == 1.0
    assert df.loc[df.index[0], "kis_theme_news_news_count"] == 1.0
    assert df.loc[df.index[0], "kis_theme_news_kis_sector_name"] == "semiconductor"
    assert df.loc[df.index[0], "kis_theme_news_top_positive_tag"] == "contract_order"
    assert df.loc[df.index[0], "kis_prefilter_present"] == 1.0
    assert df.loc[df.index[0], "kis_prefilter_selection_score"] == 91.25
    assert df.loc[df.index[0], "kis_prefilter_rank_volume"] == 2.0
    assert df.loc[df.index[0], "kis_prefilter_flow_whale_score"] == 71.0
    assert "kis_sidecar_augmented" in feature_map
    assert "kis_prefilter_augmented" in feature_map
    assert "kis_full_augmented" in feature_map
    assert "kis_theme_news_evidence_score" in feature_map["kis_sidecar_augmented"][0]
    assert "kis_theme_news_kis_sector_name" in feature_map["kis_sidecar_augmented"][1]


def test_kis_feature_set_training_requires_mature_real_kis_rows():
    raw = pd.DataFrame(
        [
            {
                "id": idx,
                "run_id": f"RUN-{idx // 2}",
                "ticker": f"{idx:06d}.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20" if idx <= 3 else "2026-05-21",
                "row_role": "emitted",
                "return_5d_pct": 1.0 if idx % 2 else -1.0,
                "feature_snapshot": {
                    "kis_sidecar": {
                        "coverage": {"quote_snapshot": True, "daily_ohlcv": True},
                        "replacement_readiness": {"model_sidecar_ready": True},
                        "model_candidate_features": {
                            "kis_value_traded": float(idx * 1000),
                            "kis_daily_return_5d_pct": float(idx),
                        },
                    }
                },
            }
            for idx in range(1, 7)
        ]
    )
    df, _sanity = prepare_dataset(raw)
    numeric, categorical = trainer.feature_sets(df)["kis_sidecar_augmented"]

    result = trainer.run_candidate(
        df,
        market="KOSPI",
        label_spec=_spec("pos_5d"),
        feature_name="kis_sidecar_augmented",
        numeric=numeric,
        categorical=categorical,
        model_name="logistic",
        topn=1,
        prob_threshold=None,
        min_train_rows=2,
        min_test_rows=1,
        min_train_days=1,
        test_days=1,
        max_folds=1,
        min_kis_rows=3,
        min_kis_days=3,
    )

    assert result["status"] == "skipped"
    assert result["skip_reason"] == "insufficient_kis_feature_days"
    assert result["kis_valid_label_rows"] == 6
    assert result["kis_valid_label_days"] == 2


def test_kis_feature_readiness_reports_date_coverage():
    raw = pd.DataFrame(
        [
            {
                "id": idx,
                "run_id": f"RUN-{idx // 2}",
                "ticker": f"{idx:06d}.KS",
                "market": "KOSPI" if idx <= 2 else "KOSDAQ",
                "scan_mode": "SWING",
                "base_trade_date": "2026-05-20" if idx <= 3 else "2026-05-21",
                "return_5d_pct": 1.0,
                "feature_snapshot": {
                    "kis_sidecar": {
                        "coverage": {"quote_snapshot": True, "daily_ohlcv": True},
                        "replacement_readiness": {"model_sidecar_ready": True},
                        "model_candidate_features": {"kis_value_traded": float(idx * 1000)},
                    }
                },
            }
            for idx in range(1, 5)
        ]
    )
    df, _sanity = prepare_dataset(raw)

    readiness = kis_feature_readiness(df, min_train_rows=2, min_test_rows=1, min_kis_rows=3, min_kis_days=2)
    coverage = readiness["families"]["sidecar"]["date_coverage"]

    assert readiness["families"]["sidecar"]["mature_for_training"] is True
    assert coverage["2026-05-20"]["rows"] == 3
    assert coverage["2026-05-20"]["outcome_label_rows"] == 3
    assert coverage["2026-05-20"]["rows_by_market"] == {"KOSDAQ": 1, "KOSPI": 2}
    assert readiness["by_market"]["KOSDAQ"]["sidecar"]["date_coverage"]["2026-05-21"]["rows"] == 1


def test_candidate_verdict_blocks_sparse_high_score_candidate():
    sparse = {
        "topn": 1,
        "metrics": {
            "n": 7,
            "active_runs": 7,
            "active_days": 3,
            "win_3d_pct": 100.0,
            "win_5d_pct": 100.0,
            "avg_3d_pct": 10.0,
            "avg_5d_pct": 10.0,
            "min_1d_pct": -1.0,
            "min_5d_pct": 1.0,
            "stop5_pct": 0.0,
        },
    }
    stable = {
        "topn": 1,
        "metrics": {
            "n": 18,
            "active_runs": 15,
            "active_days": 8,
            "win_3d_pct": 90.0,
            "win_5d_pct": 90.0,
            "avg_3d_pct": 7.0,
            "avg_5d_pct": 8.0,
            "min_1d_pct": 0.0,
            "min_5d_pct": -4.0,
            "stop5_pct": 0.0,
        },
    }

    assert candidate_verdict(sparse)["promotable"] is False
    assert "sample_too_small" in candidate_verdict(sparse)["blocking_reasons"]
    assert candidate_verdict(stable)["promotable"] is True


def test_risk_first_ranking_prefers_lower_path_risk_before_quality():
    high_quality_high_risk = {
        "label": "touch10_5d",
        "feature_set": "kis_sidecar_only",
        "topn": 1,
        "quality_score": 2000.0,
        "metrics": {
            "n": 20,
            "active_runs": 15,
            "active_days": 10,
            "label_win_pct": 90.0,
            "hit5_5d_pct": 100.0,
            "hit10_5d_pct": 90.0,
            "hit10_guard_5d_pct": 30.0,
            "avg_max_high_5d_pct": 30.0,
            "min_max_high_5d_pct": 5.0,
            "min_1d_pct": -6.1,
            "min_5d_pct": 5.0,
            "min_min_low_5d_pct": -11.0,
            "stop5_pct": 57.0,
            "bad_path_pct": 57.0,
            "target_before_stop_5d_pct": 30.0,
            "stop_before_target_5d_pct": 57.0,
        },
        "fold_metrics": [
            {"stop5_pct": 100.0, "bad_path_pct": 100.0, "target_before_stop_5d_pct": 10.0},
            {"stop5_pct": 14.0, "bad_path_pct": 14.0, "target_before_stop_5d_pct": 86.0},
        ],
    }
    lower_quality_lower_risk = {
        "label": "touch10_5d",
        "feature_set": "kis_sidecar_only",
        "topn": 1,
        "quality_score": 800.0,
        "metrics": {
            "n": 20,
            "active_runs": 15,
            "active_days": 10,
            "label_win_pct": 70.0,
            "hit5_5d_pct": 90.0,
            "hit10_5d_pct": 60.0,
            "hit10_guard_5d_pct": 50.0,
            "avg_max_high_5d_pct": 15.0,
            "min_max_high_5d_pct": 3.0,
            "min_1d_pct": -2.0,
            "min_5d_pct": 1.0,
            "min_min_low_5d_pct": -4.0,
            "stop5_pct": 10.0,
            "bad_path_pct": 15.0,
            "target_before_stop_5d_pct": 70.0,
            "stop_before_target_5d_pct": 10.0,
        },
        "fold_metrics": [
            {"stop5_pct": 10.0, "bad_path_pct": 15.0, "target_before_stop_5d_pct": 70.0},
            {"stop5_pct": 12.0, "bad_path_pct": 16.0, "target_before_stop_5d_pct": 68.0},
        ],
    }

    ranked = rank_candidate_results([high_quality_high_risk, lower_quality_lower_risk])

    assert ranked[0]["quality_score"] == 800.0
    assert ranked[0]["risk_gate"]["pass"] is True
    assert ranked[1]["promotion_candidate"]["promotable"] is False
    assert "fold_stop5_above_50" in ranked[1]["risk_gate"]["blocking_reasons"]
    assert "hit10_guard_5d_pct_raw_ratio_lt_70" in ranked[1]["risk_gate"]["blocking_reasons"]


def test_kis_candidate_verdict_uses_kis_model_gate_for_kosdaq_drawdown():
    candidate = {
        "market": "KOSDAQ",
        "label": "touch10_guard_5d",
        "feature_set": "kis_sidecar_only",
        "model": "random_forest",
        "selection_rule": "top3_p0.65",
        "topn": 3,
        "metrics": {
            "n": 11,
            "active_runs": 5,
            "active_days": 3,
            "label_win_pct": 70.0,
            "hit5_5d_pct": 90.0,
            "hit10_5d_pct": 60.0,
            "hit10_guard_5d_pct": 50.0,
            "avg_max_high_5d_pct": 15.0,
            "min_max_high_5d_pct": 3.0,
            "win_3d_pct": 90.9,
            "win_5d_pct": 54.55,
            "avg_3d_pct": 20.67,
            "avg_5d_pct": 15.8,
            "min_1d_pct": -5.85,
            "min_5d_pct": -21.02,
            "min_min_low_5d_pct": -21.39,
            "bad_path_pct": 45.45,
            "stop5_pct": 9.09,
            "stop_before_target_5d_pct": 9.09,
            "target_before_stop_5d_pct": 90.9,
        },
    }

    verdict = candidate_verdict(candidate)

    assert verdict["promotable"] is False
    assert verdict["kis_model_gate"]["status"] == "shadow_risk_review"
    assert verdict["kis_model_gate"]["shadow_display_allowed"] is True
    assert "bad_path_gt_15" in verdict["blocking_reasons"]
