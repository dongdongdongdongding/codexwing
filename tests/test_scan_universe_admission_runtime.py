import modules.scan_universe_admission as admission
from modules.kis_shadow_exit_policy import POLICY_VERSION
from modules.scan_universe_admission import (
    KIS_SHADOW_SECTION,
    _extract_feature_columns,
    build_kis_shadow_admission_records,
    build_scan_universe_admission_input_rows,
    build_scan_universe_admission_records,
    kis_shadow_gate_status,
    merge_kis_prefilter_evidence_into_rows,
)


def test_runtime_feature_extractor_reads_display_and_nested_scan_fields():
    row = {
        "티커": "005930.KS",
        "Antigrav": 91,
        "Decision Score": 88.5,
        "AI확률": "55.0%",
        "정밀확률": "48.0%",
        "수급": "83.0점 당일+3일 순매수",
        "거래량": "✅ 2.40",
        "전일비": "+3.25%",
        "매수가(-2%)": "73,200",
        "feature_snapshot": {
            "kr_universe_role": "EXPLOSIVE_LEADER",
            "scanner_timeframe_profile": "DAILY_PRIMARY_WITH_1H_REFRESH",
        },
        "leader_metrics": {
            "kr_flow_consensus_buying": True,
            "kr_retail_dominant": False,
        },
    }

    features = _extract_feature_columns(row, market="KOSPI")

    assert features["alpha_score"] == 91.0
    assert features["tech_score"] == 91.0
    assert features["ml_prob"] == 55.0
    assert features["prob_clean"] == 48.0
    assert features["whale_score"] == 83.0
    assert features["volume_ratio"] == 2.4
    assert features["day_return_pct"] == 3.25
    assert features["entry_reference_price"] == 73200.0
    assert "turnover" in features["feature_missing_keys"]
    assert features["kr_universe_role"] == "EXPLOSIVE_LEADER"
    assert features["scanner_timeframe_profile"] == "DAILY_PRIMARY_WITH_1H_REFRESH"
    assert features["flow_consensus_buying"] is True


def test_runtime_feature_extractor_reads_kis_sidecar_and_prefilter_features():
    row = {
        "ticker": "005930.KS",
        "feature_snapshot": {
            "kis_sidecar": {
                "contract_version": "kis_operational_contract_v1",
                "feature_origin": "kis_openapi_sidecar",
                "coverage": {"quote_snapshot": True, "daily_ohlcv": True, "rank_membership": True},
                "replacement_readiness": {"model_sidecar_ready": True, "production_replacement_ready": False},
                "news_contract": {
                    "checked": True,
                    "source_status": "ok",
                    "news_count": 1,
                    "rows": [{"title": "AI 반도체 공급 계약 수주", "mksc_shrn_iscd": "005930"}],
                },
                "stock_info_contract": {
                    "checked": True,
                    "sector_name": "semiconductor",
                    "standard_industry_code": "C261",
                },
                "model_candidate_features": {
                    "kis_value_traded": 123456789.0,
                    "kis_daily_return_20d_pct": 6.7,
                    "kis_rank_volume": 4,
                    "kis_stock_sector_name": "semiconductor",
                },
            },
            "kis_operational_prefilter": {
                "feature_origin": "kis_openapi_prefilter",
                "sources": ["volume_rank", "vi_status"],
                "rank": {"volume_rank": 1, "volume_power_rank": 3},
                "selection_score": 122.5,
                "vi_triggered": True,
                "quote_ok": True,
                "quote": {"source_status": "ok", "value_traded": 111000000.0, "prev_volume_ratio": 155.2},
                "flow_ok": True,
                "flow": {"flow_source": "kis_openapi", "valid": True, "whale_score": 71.0},
            },
        },
    }

    features = _extract_feature_columns(row, market="KOSPI")

    assert features["kis_sidecar_present"] == 1.0
    assert features["kis_sidecar_model_ready"] == 1.0
    assert features["kis_sidecar_coverage_rank_membership"] == 1.0
    assert features["kis_value_traded"] == 123456789.0
    assert features["kis_daily_return_20d_pct"] == 6.7
    assert features["kis_rank_volume"] == 4.0
    assert features["kis_stock_sector_name"] == "semiconductor"
    assert features["kis_theme_news_kis_backed"] == 1.0
    assert features["kis_theme_news_news_count"] == 1.0
    assert features["kis_theme_news_kis_sector_name"] == "semiconductor"
    assert features["kis_theme_news_source_scope"] == "symbol_specific"
    assert features["kis_theme_news_promotion_blocked"] == 0.0
    assert features["kis_theme_news_top_positive_tag"] == "contract_order"
    assert features["kis_prefilter_present"] == 1.0
    assert features["kis_prefilter_selection_score"] == 122.5
    assert features["kis_prefilter_rank_volume_power"] == 3.0
    assert features["kis_prefilter_quote_prev_volume_ratio"] == 155.2
    assert features["kis_prefilter_flow_whale_score"] == 71.0


def test_runtime_feature_extractor_attaches_close_failure_prior_profile(monkeypatch):
    monkeypatch.setattr(
        admission,
        "load_close_failure_prior_profile",
        lambda: {
            "groups": {
                "ticker": {
                    "values": {
                        "005930.KS": {
                            "touch5_n": 5,
                            "failure_rate_pct": 20.0,
                            "clean_defense_rate_pct": 60.0,
                            "stop5_rate_pct": 10.0,
                            "avg_close_5d_pct": 4.0,
                            "avg_mfe_5d_pct": 12.0,
                            "avg_mae_5d_pct": -3.0,
                            "risk_score": 2.5,
                            "risk_bucket": "LOW",
                        }
                    }
                },
                "market": {"values": {"KOSPI": {"touch5_n": 20, "risk_score": 45.0, "risk_bucket": "MODERATE"}}},
            }
        },
    )

    features = _extract_feature_columns({"ticker": "005930.KS", "market": "KOSPI"}, market="KOSPI")

    assert features["close_failure_prior_ticker_touch5_n"] == 5
    assert features["close_failure_prior_ticker_failure_rate_pct"] == 20.0
    assert features["close_failure_prior_ticker_risk_bucket"] == "LOW"
    assert features["close_failure_prior_market_touch5_n"] == 20
    assert features["close_failure_prior_market_risk_bucket"] == "MODERATE"


def test_merge_kis_prefilter_evidence_into_rows_uses_real_summary_payload_only():
    rows = [
        {"ticker": "005930.KS", "feature_snapshot": {"alpha_score": 91}},
        {"ticker": "000660.KS", "feature_snapshot": {"alpha_score": 88}},
    ]
    summary = {
        "kis_operational_prefilter": {
            "selected": [
                {
                    "ticker": "005930.KS",
                    "feature_origin": "kis_openapi_prefilter",
                    "is_dummy_data": False,
                    "quote_ok": True,
                    "quote": {"value_traded": 123456789.0},
                },
                {
                    "ticker": "000660.KS",
                    "feature_origin": "kis_openapi_prefilter",
                    "is_dummy_data": True,
                    "quote_ok": True,
                },
            ]
        }
    }

    merged = merge_kis_prefilter_evidence_into_rows(rows, summary)

    first_snapshot = merged[0]["feature_snapshot"]
    assert first_snapshot["kis_operational_prefilter"]["ticker"] == "005930.KS"
    assert first_snapshot["kis_operational_prefilter"]["is_dummy_data"] is False
    assert merged[0]["kis_operational_prefilter"]["feature_origin"] == "kis_openapi_prefilter"
    assert "kis_openapi_prefilter" in merged[0]["feature_origin"]
    assert "kis_operational_prefilter" not in merged[1]["feature_snapshot"]


def test_kis_shadow_records_require_real_kis_runtime_evidence(monkeypatch):
    bundle = {
        "market": "KOSPI",
        "model_name": "fake",
        "label": "fake",
        "feature_set": "fake",
        "selection_rule": "fake_rule",
        "prob_threshold": 0.99,
        "topn": 1,
        "_model_path": "fake.pkl",
        "validation": {"metrics": {"n": 10, "win_5d_pct": 80.0, "avg_5d_pct": 3.0, "min_5d_pct": -2.0}},
    }
    scored = [
        {
            "ticker": "005930.KS",
            "stock_name": "삼성전자",
            "_admission_probability": 0.88,
            "_admission_source_role": "emitted",
            "feature_snapshot": {
                "kis_sidecar": {
                    "feature_origin": "kis_openapi_sidecar",
                    "coverage": {"news_titles": True, "stock_info": True},
                    "replacement_readiness": {"model_sidecar_ready": True},
                    "news_contract": {
                        "checked": True,
                        "source_status": "ok",
                        "news_count": 1,
                        "rows": [{"title": "AI 반도체 공급 계약 수주", "mksc_shrn_iscd": "005930"}],
                    },
                    "stock_info_contract": {
                        "checked": True,
                        "sector_name": "반도체",
                        "standard_industry_code": "C261",
                    },
                }
            },
            "theme_context": {"primary_theme": "AI반도체"},
            "_admission_features": {
                "feature_coverage_score": 1.0,
                "feature_missing_keys": [],
                "volume_ratio": 1.8,
                "kis_sidecar_present": 1.0,
                "kis_sidecar_model_ready": 1.0,
            },
        },
        {
            "ticker": "000660.KS",
            "stock_name": "SK하이닉스",
            "_admission_probability": 0.99,
            "_admission_source_role": "emitted",
            "_admission_features": {
                "feature_coverage_score": 1.0,
                "feature_missing_keys": [],
                "volume_ratio": 2.1,
            },
        },
    ]
    monkeypatch.setattr(admission, "load_kis_shadow_model", lambda _market: {**bundle, "_shadow_model_loaded": True})
    monkeypatch.setattr(admission, "_score_scan_universe_admission_rows_with_bundle", lambda _rows, market, bundle: scored)
    monkeypatch.setattr(
        admission,
        "_load_kis_shadow_report",
        lambda _market: {
            "report_path": "runtime_state/reports/learning/kis_model_market_comparison.json",
            "identity": {
                "label": "kis",
                "feature_set": "kis",
                "model": "xgboost",
                "selection_rule": "top1",
                "topn": 3,
                "promotion_candidate": {"blocking_reasons": ["active_day_sample_below_gate"]},
            },
            "metrics": {
                "n": 12,
                "active_days": 6,
                "active_runs": 8,
                "win_1d_pct": 58.3,
                "avg_1d_pct": 0.8,
                "min_1d_pct": 0.0,
                "win_3d_pct": 66.7,
                "avg_3d_pct": 1.4,
                "win_5d_pct": 75.0,
                "avg_5d_pct": 2.5,
                "min_5d_pct": -1.2,
                "min_min_low_5d_pct": -4.0,
                "bad_path_pct": 10.0,
                "stop5_pct": 5.0,
            },
        },
    )

    records = build_kis_shadow_admission_records(scored, market="KOSPI", limit=3)

    assert [row["ticker"] for row in records] == ["005930.KS"]
    row = records[0]
    assert row["_analysis_section"] == KIS_SHADOW_SECTION
    assert row["_analysis_section_order"] == -250
    assert row["decision"] == "KIS_SHADOW"
    assert row["kis_shadow_candidate"]["shadow_only"] is True
    assert row["kis_shadow_candidate"]["shadow_model_loaded"] is True
    assert row["kis_shadow_candidate"]["source"] == "real_kis_sidecar_or_prefilter_evidence"
    assert row["kis_shadow_candidate"]["gate_status"] == "shadow_ready"
    assert row["kis_shadow_candidate"]["production_ready"] is False
    assert row["kis_shadow_candidate"]["kis_model_gate"]["shadow_display_allowed"] is True
    assert row["kis_theme_news_evidence"]["kis_backed"] is True
    assert row["kis_theme_news_evidence"]["theme"]["kis_sector_name"] == "반도체"
    assert "AI 반도체 공급 계약 수주" in row["kis_shadow_candidate"]["theme_news_evidence"]["summary"]
    assert row["realized_expectancy_admission"]["source"] == "kis_shadow_validation_report"
    assert row["realized_expectancy_admission"]["kis_model_gate_status"] == "shadow_ready"
    assert row["realized_expectancy_admission"]["5d_prob"] == 75.0
    assert row["trade_plan"]["target_tp_pct"] == 7.0
    assert row["trade_plan"]["stop_sl_pct"] == -5.0
    assert row["execution_stop"]["display_stop_source"] == "kis_shadow_dynamic_exit_policy"
    assert row["kis_shadow_candidate"]["dynamic_exit_policy"]["version"] == POLICY_VERSION


def test_kis_shadow_gate_status_exposes_blocked_display_reason(monkeypatch):
    monkeypatch.setattr(
        admission,
        "_load_kis_shadow_report",
        lambda _market: {
            "report_path": "runtime_state/reports/learning/kis_model_market_comparison.json",
            "identity": {
                "label": "kis",
                "feature_set": "kis_sidecar",
                "model": "random_forest",
                "selection_rule": "top1",
            },
            "metrics": {
                "n": 7,
                "active_days": 5,
                "win_5d_pct": 71.4,
                "close_win_5d_pct": 0.0,
                "avg_5d_pct": -18.7,
            },
            "kis_model_gate": {
                "status": "blocked",
                "production_ready": False,
                "shadow_display_allowed": False,
                "production_blocking_reasons": ["avg_5d_below_zero", "active_day_sample_below_gate"],
            },
        },
    )

    gate = kis_shadow_gate_status("KOSDAQ")

    assert gate["shadow_display_allowed"] is False
    assert gate["production_ready"] is False
    assert "avg_5d_below_zero" in gate["blocking_reasons"]
    assert "5D" in gate["metrics"]


def test_admission_records_include_full_result_interpretation():
    rows = [
        {
            "티커": "005930.KS",
            "종목명": "삼성전자",
            "Antigrav": 91,
            "Decision Score": 88.5,
            "AI확률": "55.0%",
            "정밀확률": "48.0%",
            "수급": "83.0점 당일+3일 순매수",
            "거래량": "✅ 2.40",
            "전일비": "+3.25%",
            "매수가(-2%)": "73,200",
            "leader_metrics": {
                "kr_turnover": 1234567890,
                "kr_foreign_flow": 100,
                "kr_institution_flow": 50,
                "kr_retail_flow": -150,
            },
            "flow": {
                "foreigner_3d": 200,
                "institution_3d": 80,
                "retail_3d": -280,
            },
        },
        {
            "티커": "000660.KS",
            "종목명": "SK하이닉스",
            "Antigrav": 80,
            "Decision Score": 78,
            "AI확률": "45.0%",
            "정밀확률": "42.0%",
            "수급": "55.0점 혼조",
            "거래량": "⚠️ 0.70",
            "전일비": "-1.20%",
            "매수가(-2%)": "120,000",
            "leader_metrics": {"kr_turnover": 987654321},
        },
    ]

    result = build_scan_universe_admission_records(rows, market="KOSPI", limit=1, include_near_miss=True)

    assert result["scored_count"] == 2
    assert len(result["all_records"]) == 2
    first = result["all_records"][0]
    interpretation = first["scan_result_interpretation"]
    assert interpretation["model_decision"] in {"운영 통과", "기준 미달"}
    assert interpretation["threshold_gap_pct_points"] is not None
    assert interpretation["drivers"]
    assert first["scan_universe_admission"]["feature_missing_keys"] == []


def test_universe_input_rows_include_feature_rich_rejected_diagnostics():
    result = build_scan_universe_admission_input_rows(
        [{"ticker": "005930.KS", "stock_name": "삼성전자"}],
        market="KOSPI",
        diagnostics={
            "reject_reasons_by_symbol": {"000660.KS": "KR_PRECISION_GATE_FAIL"},
            "reject_details_by_symbol": {
                "000660.KS": [
                    {
                        "ticker": "000660.KS",
                        "stock_name": "SK하이닉스",
                        "stage": "precision_gate",
                        "alpha_score": 72.0,
                        "ml_prob": 61.0,
                        "volume_ratio": 2.1,
                    }
                ]
            },
        },
    )

    assert result["total_input_rows"] == 2
    assert result["emitted_count"] == 1
    assert result["rejected_feature_rows"] == 1
    rejected = [row for row in result["rows"] if row.get("_admission_source_role") == "legacy_rejected"][0]
    assert rejected["ticker"] == "000660.KS"
    assert rejected["reject_reason"] == "KR_PRECISION_GATE_FAIL"


def test_universe_input_rows_preserve_rejected_day_change_diagnostics():
    result = build_scan_universe_admission_input_rows(
        [],
        market="KOSDAQ",
        diagnostics={
            "reject_reasons_by_symbol": {"322310.KQ": "LOW_LIQUIDITY"},
            "reject_details_by_symbol": {
                "322310.KQ": [
                    {
                        "ticker": "322310.KQ",
                        "stock_name": "오성첨단소재",
                        "stage": "liquidity_gate",
                        "day_return_pct": -4.32,
                        "전일비": "-4.32%",
                        "alpha_score": 72.0,
                        "ml_prob": 61.0,
                        "volume_ratio": 2.1,
                    }
                ]
            },
        },
    )

    rejected = result["rows"][0]
    features = _extract_feature_columns(rejected, market="KOSDAQ")
    assert rejected["day_return_pct"] == -4.32
    assert rejected["전일비"] == "-4.32%"
    assert features["day_return_pct"] == -4.32


def test_critical_legacy_reject_can_be_scored_but_not_promoted(monkeypatch):
    bundle = {
        "market": "KOSPI",
        "model_name": "fake",
        "label": "fake",
        "feature_set": "fake",
        "selection_rule": "fake_rule",
        "prob_threshold": 0.6,
        "topn": 1,
        "_model_path": "fake.pkl",
        "validation": {"metrics": {"n": 10, "win_5d_pct": 80.0, "avg_5d_pct": 3.0, "min_5d_pct": -2.0}},
    }
    scored = [
        {
            "ticker": "000001.KS",
            "stock_name": "저유동성",
            "_admission_probability": 0.9,
            "_admission_source_role": "legacy_rejected",
            "row_role": "rejected",
            "reject_reason": "LIQUIDITY_FILTER_FAIL",
            "reject_reason_codes": ["LIQUIDITY_FILTER_FAIL"],
            "_admission_features": {
                "feature_coverage_score": 1.0,
                "feature_missing_keys": [],
                "volume_ratio": 0.2,
                "day_return_pct": 1.0,
            },
        }
    ]
    monkeypatch.setattr(admission, "load_admission_model", lambda _market: bundle)
    monkeypatch.setattr(admission, "score_scan_universe_admission_rows", lambda _rows, market: scored)

    result = build_scan_universe_admission_records(scored, market="KOSPI", limit=1, include_near_miss=True)

    assert result["passed"] == []
    assert result["near_miss"] == []
    assert result["blocked"] == []
    assert len(result["liquidity_blocked"]) == 1
    row = result["liquidity_blocked"][0]
    assert row["scan_universe_admission"]["promotion_blocked"] is True
    assert row["scan_universe_admission"]["promotion_block_reason"] == "LIQUIDITY_FILTER_FAIL"
    assert row["scan_result_interpretation"]["model_decision"] == "모델 기준 통과·운영 차단"


def test_blocked_top_rank_does_not_prevent_next_eligible_promotion(monkeypatch):
    bundle = {
        "market": "KOSPI",
        "model_name": "fake",
        "label": "fake",
        "feature_set": "fake",
        "selection_rule": "fake_rule",
        "prob_threshold": 0.6,
        "topn": 1,
        "_model_path": "fake.pkl",
        "validation": {"metrics": {"n": 10, "win_5d_pct": 80.0, "avg_5d_pct": 3.0, "min_5d_pct": -2.0}},
    }
    scored = [
        {
            "ticker": "000001.KS",
            "stock_name": "저유동성",
            "_admission_probability": 0.9,
            "_admission_source_role": "legacy_rejected",
            "row_role": "rejected",
            "reject_reason": "LIQUIDITY_FILTER_FAIL",
            "reject_reason_codes": ["LIQUIDITY_FILTER_FAIL"],
            "_admission_features": {"feature_coverage_score": 1.0, "feature_missing_keys": [], "volume_ratio": 0.2},
        },
        {
            "ticker": "005930.KS",
            "stock_name": "삼성전자",
            "_admission_probability": 0.8,
            "_admission_source_role": "emitted",
            "row_role": "emitted",
            "_admission_features": {"feature_coverage_score": 1.0, "feature_missing_keys": [], "volume_ratio": 1.5},
        },
    ]
    monkeypatch.setattr(admission, "load_admission_model", lambda _market: bundle)
    monkeypatch.setattr(admission, "score_scan_universe_admission_rows", lambda _rows, market: scored)

    result = build_scan_universe_admission_records(scored, market="KOSPI", limit=2, include_near_miss=True)

    assert [row["ticker"] for row in result["passed"]] == ["005930.KS"]
    assert [row["ticker"] for row in result["liquidity_blocked"]] == ["000001.KS"]
    assert result["passed"][0]["scan_universe_admission"]["model_rank"] == 2
    assert result["all_records"][0]["scan_universe_admission"]["promotion_blocked"] is True
    assert result["all_records"][1]["scan_universe_admission"]["passed"] is True


def test_tail_risk_gate_blocks_high_primary_probability_candidate(monkeypatch):
    bundle = {
        "market": "KOSPI",
        "model_name": "fake",
        "label": "touch5_dd10_5d",
        "feature_set": "fake",
        "selection_rule": "top1_p0.60_tail0.80",
        "prob_threshold": 0.6,
        "tail_risk_prob_threshold": 0.8,
        "topn": 1,
        "_model_path": "fake.pkl",
        "validation": {"metrics": {"n": 10, "hit5_5d_pct": 80.0, "avg_max_high_5d_pct": 6.0, "min_min_low_5d_pct": -9.0}},
    }
    scored = [
        {
            "ticker": "000001.KS",
            "stock_name": "고위험상위후보",
            "_admission_probability": 0.95,
            "_tail_risk_probability": 0.4,
            "_admission_source_role": "emitted",
            "row_role": "emitted",
            "_admission_features": {"feature_coverage_score": 1.0, "feature_missing_keys": [], "volume_ratio": 2.0},
        },
        {
            "ticker": "005930.KS",
            "stock_name": "삼성전자",
            "_admission_probability": 0.9,
            "_tail_risk_probability": 0.86,
            "_admission_source_role": "emitted",
            "row_role": "emitted",
            "_admission_features": {"feature_coverage_score": 1.0, "feature_missing_keys": [], "volume_ratio": 1.5},
        },
    ]
    monkeypatch.setattr(admission, "load_admission_model", lambda _market: bundle)
    monkeypatch.setattr(admission, "score_scan_universe_admission_rows", lambda _rows, market: scored)

    result = build_scan_universe_admission_records(scored, market="KOSPI", limit=2, include_near_miss=True)

    assert [row["ticker"] for row in result["passed"]] == ["005930.KS"]
    assert [row["ticker"] for row in result["near_miss"]] == ["000001.KS"]
    assert result["near_miss"][0]["scan_universe_admission"]["tail_risk_gate_passed"] is False
    assert "TAIL_RISK_THRESHOLD_NOT_MET" in result["near_miss"][0]["risk_flags"]
    assert "목표터치 확률 95.0% >= 운영기준 60.0%" in result["near_miss"][0]["entry_condition_text"]
    assert "-10% 방어확률 40.0% < 기준 80.0%" in result["near_miss"][0]["entry_condition_text"]


def test_ambiguous_kis_news_scope_blocks_admission_promotion(monkeypatch):
    bundle = {
        "market": "KOSPI",
        "model_name": "fake",
        "label": "fake",
        "feature_set": "fake",
        "selection_rule": "fake_rule",
        "prob_threshold": 0.6,
        "topn": 1,
        "_model_path": "fake.pkl",
    }
    scored = [
        {
            "ticker": "005930.KS",
            "stock_name": "삼성전자",
            "_admission_probability": 0.9,
            "_admission_source_role": "emitted",
            "row_role": "emitted",
            "_admission_features": {"feature_coverage_score": 1.0, "feature_missing_keys": [], "volume_ratio": 1.5},
            "feature_snapshot": {
                "kis_sidecar": {
                    "coverage": {"news_titles": True, "stock_info": True},
                    "news_contract": {
                        "checked": True,
                        "source_status": "ok",
                        "news_count": 1,
                        "rows": [{"title": "AI 반도체 공급 계약 수주"}],
                    },
                    "stock_info_contract": {"checked": True, "product_name": "삼성전자", "sector_name": "반도체"},
                }
            },
        }
    ]
    monkeypatch.setattr(admission, "load_admission_model", lambda _market: bundle)
    monkeypatch.setattr(admission, "score_scan_universe_admission_rows", lambda _rows, market: scored)

    result = build_scan_universe_admission_records(scored, market="KOSPI", limit=1, include_near_miss=True)

    assert result["passed"] == []
    assert len(result["blocked"]) == 1
    assert result["blocked"][0]["scan_universe_admission"]["promotion_block_reason"] == "KIS_NEWS_SCOPE_AMBIGUOUS"
