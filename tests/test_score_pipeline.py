import unittest
from unittest.mock import patch

from multi_agent.agents.planner_runtime import _apply_kospi_swing_edge_promotion, build_planner_handoff
from multi_agent.contracts.types import RunContext
from multi_agent.workflows.legacy_export import build_scanner_handoff_from_legacy_results


class ScorePipelineTests(unittest.TestCase):
    def test_legacy_export_maps_antigrav_and_conviction_into_feature_snapshot(self):
        handoff = build_scanner_handoff_from_legacy_results(
            results=[
                {
                    "티커": "005930.KS",
                    "종목명": "삼성전자",
                    "Antigrav": 100,
                    "확신도": 84.1,
                    "Decision Score": 91.2,
                    "AI확률": "55.0%",
                    "정밀확률": "48.0%",
                    "수급": "83.0점 당일+3일 순매수",
                    "거래량": "✅ 2.40",
                    "추세": "UP",
                    "매수가(-2%)": "73,200",
                    "scan_mode": "SWING",
                }
            ],
            context=RunContext(run_id="RUN-TEST", market="KOSPI"),
        )
        snap = handoff.candidates[0].feature_snapshot
        self.assertEqual(snap["alpha_score"], 100.0)
        self.assertEqual(snap["conviction_score"], 84.1)
        self.assertEqual(snap["prob_5"], 55.0)
        self.assertEqual(snap["prob_clean"], 48.0)
        self.assertEqual(snap["entry_reference_price"], 73200.0)
        self.assertEqual(snap["whale_score"], 83.0)
        self.assertEqual(snap["volume_ratio"], 2.4)
        self.assertEqual(snap["tech_score"], 100.0)

    def test_legacy_export_preserves_kis_sidecar_in_feature_snapshot(self):
        kis_sidecar = {
            "feature_origin": "kis_openapi_sidecar",
            "model_candidate_features": {"kis_value_traded": 12345.0},
            "replacement_readiness": {"production_replacement_ready": False},
        }
        handoff = build_scanner_handoff_from_legacy_results(
            results=[
                {
                    "티커": "005930.KS",
                    "종목명": "삼성전자",
                    "Antigrav": 80,
                    "Decision Score": 82.5,
                    "수급": "70점",
                    "_leader_metrics": {"kis_sidecar": kis_sidecar},
                }
            ],
            context=RunContext(run_id="RUN-KIS", market="KOSPI"),
        )

        snap = handoff.candidates[0].feature_snapshot
        self.assertEqual(snap["kis_sidecar"]["feature_origin"], "kis_openapi_sidecar")
        self.assertEqual(snap["kis_model_candidate_features"]["kis_value_traded"], 12345.0)
        self.assertEqual(handoff.candidates[0].leader_metrics["kis_sidecar"], kis_sidecar)

    def test_planner_handoff_preserves_alpha_and_conviction_scores(self):
        planner = build_planner_handoff(
            context=RunContext(run_id="RUN-TEST", market="KOSPI"),
            weak_ratio=0.1,
            candidates=[
                {
                    "ticker": "005930.KS",
                    "score": 88.0,
                    "reasons": ["테스트"],
                    "feature_snapshot": {
                        "stock_name": "삼성전자",
                        "alpha_score": 79.0,
                        "conviction_score": 67.5,
                        "decision_score": 88.0,
                        "prob_5": 56.0,
                        "prob_clean": 49.0,
                        "phase25_prob": 22.0,
                        "real_trend": "UP",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "market_gate": "YELLOW",
                        "scanner_timeframe_profile": "SWING_DAILY",
                        "kr_universe_role": "CORE_TREND",
                    },
                    "warnings": [],
                }
            ],
        )
        self.assertEqual(len(planner.decisions), 1)
        decision = planner.decisions[0]
        self.assertEqual(decision.alpha_score, 79.0)
        self.assertEqual(decision.conviction_score, 67.5)
        self.assertEqual(decision.model_prob_available_count, 3.0)
        self.assertAlmostEqual(decision.model_prob_mean, 42.333333, places=6)
        self.assertAlmostEqual(decision.low_model_prob_score, 7.666667, places=6)
        self.assertAlmostEqual(decision.low_prob_high_score, 36.666667, places=6)
        self.assertIn("inverted_prob_features:", " ".join(decision.rationale))
        self.assertEqual(decision.regime_adjusted_grade, "RELATIVE_PRIORITY")
        self.assertEqual(decision.relative_rank_model, "kospi_floor_win_relative_v2")
        self.assertEqual(decision.market_gate, "YELLOW")
        self.assertEqual(decision.scanner_timeframe_profile, "SWING_DAILY")
        self.assertEqual(decision.kr_universe_role, "CORE_TREND")
        serialized = decision.to_dict()
        self.assertEqual(serialized["market_gate"], "YELLOW")
        self.assertEqual(serialized["scanner_timeframe_profile"], "SWING_DAILY")
        self.assertEqual(serialized["kr_universe_role"], "CORE_TREND")

    def test_planner_handoff_uses_entry_price_as_reference_price_fallback(self):
        planner = build_planner_handoff(
            context=RunContext(run_id="RUN-TEST", market="KOSDAQ"),
            weak_ratio=0.1,
            candidates=[
                {
                    "ticker": "322310.KQ",
                    "score": 88.0,
                    "reasons": ["entry fallback"],
                    "feature_snapshot": {
                        "stock_name": "오로스테크놀로지",
                        "alpha_score": 88.0,
                        "tech_score": 80.0,
                        "conviction_score": 74.0,
                        "decision_score": 88.0,
                        "entry_price": "12,340",
                        "prob_5": 56.0,
                        "prob_clean": 51.0,
                        "phase25_prob": 65.0,
                        "phase25_recommended_threshold": 55.0,
                        "real_trend": "UP",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                    },
                    "warnings": [],
                }
            ],
        )

        self.assertEqual(planner.decisions[0].entry_reference_price, 12340.0)

    def test_kosdaq_swing_low_prob_override_prevents_hard_avoid(self):
        planner = build_planner_handoff(
            context=RunContext(run_id="RUN-TEST", market="KOSDAQ"),
            weak_ratio=0.1,
            candidates=[
                {
                    "ticker": "322310.KQ",
                    "score": 93.6,
                    "reasons": ["실제 RUN-B156C712 패턴"],
                    "feature_snapshot": {
                        "stock_name": "오로스테크놀로지",
                        "alpha_score": 97.0,
                        "tech_score": 43.0,
                        "conviction_score": 80.0,
                        "decision_score": 93.6,
                        "prob_5": 22.1,
                        "prob_clean": 31.1,
                        "phase25_prob": 18.9,
                        "phase25_variant": "phase25_kr_swing_logistic",
                        "phase25_recommended_threshold": 55.0,
                        # 2026-09-03: OOS 메타데이터를 픽스처에 싣는다. 없으면 fail-closed 게이트가
                        # PHASE25_WEAK_OOS_PRIORITY_BLOCK 에서 먼저 끊어 뒤 경로를 못 본다.
                        # 라이브에서는 quant_analysis.py:2095-2101 이 이 필드들을 항상 채운다.
                        "phase25_signal_direction": "normal",
                        "phase25_oos_auc": 0.58,
                        "phase25_oos_win_rate_pct": 72.0,
                        "phase25_oos_avg_return_pct": 5.4,
                        "real_trend": "UP",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "low_model_prob_score": 25.966667,
                        "low_prob_high_score": 45.966667,
                    },
                    "warnings": [],
                }
            ],
        )

        decision = planner.decisions[0]
        self.assertNotEqual(decision.decision, "AVOID")
        self.assertEqual(decision.regime_adjusted_grade, "RELATIVE_PRIORITY")
        self.assertEqual(decision.relative_rank_model, "kosdaq_floor_win_relative_v5")
        self.assertIn("PHASE25_SWING_BELOW_THRESHOLD_INVERTED_OVERRIDE", decision.theme_risk)
        self.assertIn("kosdaq_swing_inverted_prob_override", " ".join(decision.rationale))

    def test_kosdaq_swing_validated_touch_exception_is_demoted_after_ordered_recheck(self):
        planner = build_planner_handoff(
            context=RunContext(run_id="RUN-KQ-TOUCH", market="KOSDAQ"),
            weak_ratio=0.1,
            candidates=[
                {
                    "ticker": "123456.KQ",
                    "score": 93.0,
                    "reasons": ["validated 5d touch slice"],
                    "feature_snapshot": {
                        "stock_name": "Validated Touch",
                        "alpha_score": 94.0,
                        "tech_score": 82.0,
                        "conviction_score": 82.0,
                        "decision_score": 93.0,
                        "prob_5": 35.0,
                        "prob_clean": 34.0,
                        "phase25_prob": 20.0,
                        "phase25_variant": "phase25_kr_swing_logistic",
                        "phase25_recommended_threshold": 55.0,
                        # 2026-09-03: 위와 같은 이유 — 이 테스트가 보려는 것은
                        # KOSDAQ_SWING_PROBATION 경로이고, 메타데이터가 없으면 그 앞에서 끊긴다.
                        "phase25_signal_direction": "normal",
                        "phase25_oos_auc": 0.58,
                        "phase25_oos_win_rate_pct": 72.0,
                        "phase25_oos_avg_return_pct": 5.4,
                        "volume_ratio": 2.4,
                        "real_trend": "UP",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                    },
                    "warnings": [],
                }
            ],
        )

        decision = planner.decisions[0]
        self.assertEqual(decision.decision, "OBSERVE")
        self.assertIn("KOSDAQ_SWING_VALIDATED_TOUCH_DEPRECATED", decision.theme_risk)
        self.assertIn("KOSDAQ_SWING_PROBATION", decision.theme_risk)
        self.assertIn("kosdaq_validated_touch_deprecated", " ".join(decision.rationale))

    def test_kosdaq_relative_ranking_is_shadow_only_by_default(self):
        context = RunContext(run_id="RUN-KQ-RANK-SHADOW", market="KOSDAQ")
        planner = build_planner_handoff(
            context=context,
            weak_ratio=0.0,
            candidates=[
                {
                    "ticker": "111111.KQ",
                    "stock_name": "Higher Scanner Score",
                    "score": 95.0,
                    "feature_snapshot": {
                        "market": "KOSDAQ",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 98.0,
                        "tech_score": 80.0,
                        "decision_score": 95.0,
                        "prob_5": 45.0,
                        "prob_clean": 40.0,
                        "volume_ratio": 0.2,
                        "real_trend": "UP",
                    },
                },
                {
                    "ticker": "222222.KQ",
                    "stock_name": "Relative Leader",
                    "score": 80.0,
                    "feature_snapshot": {
                        "market": "KOSDAQ",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 86.0,
                        "tech_score": 100.0,
                        "decision_score": 80.0,
                        "prob_5": 45.0,
                        "prob_clean": 40.0,
                        "volume_ratio": 4.0,
                        "real_trend": "UP",
                    },
                },
            ],
        )

        self.assertEqual(planner.decisions[0].relative_rank_model, "kosdaq_floor_win_relative_v5")
        self.assertIn("KOSDAQ_RELATIVE_RANKING_SHADOW_ONLY", planner.decisions[0].theme_risk)
        self.assertIn("relative_rank_shadow_only:model=kosdaq_floor_win_relative_v5", " ".join(planner.decisions[0].rationale))
        self.assertTrue(
            all("KOSDAQ_RELATIVE_RANKING_SHADOW_ONLY" in decision.theme_risk for decision in planner.decisions)
        )

    @patch.dict("os.environ", {"AG_KOSDAQ_RELATIVE_RANKING_ENABLED": "1"})
    def test_kosdaq_relative_ranking_prefers_volume_supported_tech_leader(self):
        context = RunContext(run_id="RUN-KQ-RANK", market="KOSDAQ")
        planner = build_planner_handoff(
            context=context,
            weak_ratio=0.0,
            candidates=[
                {
                    "ticker": "111111.KQ",
                    "stock_name": "Weak Volume",
                    "score": 95.0,
                    "feature_snapshot": {
                        "market": "KOSDAQ",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 98.0,
                        "tech_score": 80.0,
                        "decision_score": 95.0,
                        "prob_5": 45.0,
                        "prob_clean": 40.0,
                        "volume_ratio": 0.2,
                        "real_trend": "UP",
                    },
                },
                {
                    "ticker": "222222.KQ",
                    "stock_name": "Volume Leader",
                    "score": 80.0,
                    "feature_snapshot": {
                        "market": "KOSDAQ",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 86.0,
                        "tech_score": 100.0,
                        "decision_score": 80.0,
                        "prob_5": 45.0,
                        "prob_clean": 40.0,
                        "volume_ratio": 4.0,
                        "real_trend": "UP",
                    },
                },
            ],
        )

        self.assertEqual(planner.decisions[0].ticker, "222222.KQ")
        self.assertEqual(planner.decisions[0].relative_rank_model, "kosdaq_floor_win_relative_v5")

    @patch.dict("os.environ", {"AG_KOSDAQ_RELATIVE_RANKING_ENABLED": "1"})
    def test_kosdaq_relative_ranking_penalizes_loss_risk(self):
        context = RunContext(run_id="RUN-KQ-FLOOR", market="KOSDAQ")
        planner = build_planner_handoff(
            context=context,
            weak_ratio=0.0,
            candidates=[
                {
                    "ticker": "333333.KQ",
                    "stock_name": "Risky Chase",
                    "score": 96.0,
                    "feature_snapshot": {
                        "market": "KOSDAQ",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 99.0,
                        "tech_score": 93.0,
                        "decision_score": 96.0,
                        "prob_5": 15.0,
                        "prob_clean": 18.0,
                        "volume_ratio": 0.2,
                        "volume_confirmed": False,
                        "position": "Peak",
                        "tier": "T3",
                        "real_trend": "DOWN",
                    },
                },
                {
                    "ticker": "444444.KQ",
                    "stock_name": "Supported Leader",
                    "score": 84.0,
                    "feature_snapshot": {
                        "market": "KOSDAQ",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 88.0,
                        "tech_score": 90.0,
                        "decision_score": 84.0,
                        "prob_5": 42.0,
                        "prob_clean": 45.0,
                        "volume_ratio": 3.5,
                        "volume_confirmed": True,
                        "position": "Rising",
                        "tier": "T1",
                        "real_trend": "UP",
                    },
                },
            ],
        )

        self.assertEqual(planner.decisions[0].ticker, "444444.KQ")
        self.assertEqual(planner.decisions[0].relative_rank_model, "kosdaq_floor_win_relative_v5")

    @patch.dict("os.environ", {"AG_KOSDAQ_RELATIVE_RANKING_ENABLED": "1"})
    def test_kosdaq_relative_ranking_pushes_down_weak_entry_timing(self):
        context = RunContext(run_id="RUN-KQ-ENTRY-TIMING", market="KOSDAQ")
        planner = build_planner_handoff(
            context=context,
            weak_ratio=0.0,
            candidates=[
                {
                    "ticker": "555555.KQ",
                    "stock_name": "Delayed Swing Chase",
                    "score": 94.0,
                    "feature_snapshot": {
                        "market": "KOSDAQ",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 92.0,
                        "tech_score": 90.0,
                        "decision_score": 94.0,
                        "prob_5": 42.0,
                        "prob_clean": 42.0,
                        "volume_ratio": 1.4,
                        "volume_confirmed": True,
                        "expected_return_1d_pct": -0.8,
                        "expected_return_3d_pct": 6.4,
                        "expected_edge_score": -1.0,
                        "prev_pct_change_1d": 8.0,
                        "prev_pct_change_5d": 18.0,
                        "position": "Rising",
                        "tier": "T1",
                        "real_trend": "UP",
                    },
                },
                {
                    "ticker": "666666.KQ",
                    "stock_name": "Cleaner Entry",
                    "score": 90.0,
                    "feature_snapshot": {
                        "market": "KOSDAQ",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 92.0,
                        "tech_score": 90.0,
                        "decision_score": 90.0,
                        "prob_5": 42.0,
                        "prob_clean": 42.0,
                        "volume_ratio": 1.4,
                        "volume_confirmed": True,
                        "expected_return_1d_pct": 2.2,
                        "expected_return_3d_pct": 5.2,
                        "expected_edge_score": 3.0,
                        "prev_pct_change_1d": 1.0,
                        "prev_pct_change_5d": 4.0,
                        "position": "Rising",
                        "tier": "T1",
                        "real_trend": "UP",
                    },
                },
            ],
        )

        self.assertEqual(planner.decisions[0].ticker, "666666.KQ")
        self.assertIn("entry_timing_risk_score=", " ".join(planner.decisions[1].rationale))

    def test_kospi_relative_ranking_penalizes_loss_risk(self):
        context = RunContext(run_id="RUN-KS-FLOOR", market="KOSPI")
        planner = build_planner_handoff(
            context=context,
            weak_ratio=0.0,
            candidates=[
                {
                    "ticker": "111111.KS",
                    "stock_name": "Risky KOSPI Chase",
                    "score": 98.0,
                    "feature_snapshot": {
                        "market": "KOSPI",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 99.0,
                        "tech_score": 90.0,
                        "decision_score": 98.0,
                        "prob_5": 12.0,
                        "prob_clean": 15.0,
                        "volume_ratio": 0.2,
                        "volume_confirmed": False,
                        "position": "Peak",
                        "tier": "T3",
                        "real_trend": "DOWN",
                    },
                },
                {
                    "ticker": "222222.KS",
                    "stock_name": "Supported KOSPI",
                    "score": 86.0,
                    "feature_snapshot": {
                        "market": "KOSPI",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 86.0,
                        "tech_score": 75.0,
                        "decision_score": 86.0,
                        "prob_5": 42.0,
                        "prob_clean": 42.0,
                        "volume_ratio": 3.0,
                        "volume_confirmed": True,
                        "position": "Rising",
                        "tier": "T1",
                        "real_trend": "UP",
                    },
                },
            ],
        )

        self.assertEqual(planner.decisions[0].ticker, "222222.KS")
        self.assertEqual(planner.decisions[0].relative_rank_model, "kospi_floor_win_relative_v2")

    def test_kospi_swing_edge_promotion_is_off_by_default_after_panel_capw_revalidation(self):
        planner = build_planner_handoff(
            context=RunContext(run_id="RUN-KS-EDGE", market="KOSPI"),
            weak_ratio=0.0,
            candidates=[
                {
                    "ticker": "333333.KS",
                    "stock_name": "Edge Supported KOSPI",
                    "score": 58.0,
                    "feature_snapshot": {
                        "market": "KOSPI",
                        "scan_mode": "SWING",
                        "strategy_family": "KR_CORE",
                        "alpha_score": 82.0,
                        "tech_score": 75.0,
                        "conviction_score": 70.0,
                        "decision_score": 86.0,
                        "prob_5": 52.0,
                        "prob_clean": 50.0,
                        "expected_edge_score": 6.2,
                        "expected_return_1d_pct": -1.0,
                        "expected_return_3d_pct": -1.0,
                        "volume_ratio": 1.2,
                        "volume_confirmed": True,
                        "position": "Rising",
                        "tier": "T1",
                        "real_trend": "UP",
                    },
                }
            ],
        )

        decision = planner.decisions[0]
        self.assertEqual(decision.decision, "OBSERVE")
        self.assertNotIn("kospi_swing_edge_promotion=", " ".join(decision.rationale))

    def test_kospi_swing_edge_promotion_can_be_enabled_for_research(self):
        with patch.dict("os.environ", {"AG_KOSPI_SWING_EDGE_PROMOTION": "1"}):
            planner = build_planner_handoff(
                context=RunContext(run_id="RUN-KS-EDGE-ON", market="KOSPI"),
                weak_ratio=0.0,
                candidates=[
                    {
                        "ticker": "333333.KS",
                        "stock_name": "Research Edge KOSPI",
                        "score": 58.0,
                        "feature_snapshot": {
                            "market": "KOSPI",
                            "scan_mode": "SWING",
                            "strategy_family": "KR_CORE",
                            "alpha_score": 82.0,
                            "tech_score": 75.0,
                            "conviction_score": 70.0,
                            "decision_score": 86.0,
                            "prob_5": 52.0,
                            "prob_clean": 50.0,
                            "expected_edge_score": 6.2,
                            "expected_return_1d_pct": -1.0,
                            "expected_return_3d_pct": -1.0,
                            "volume_ratio": 1.2,
                            "volume_confirmed": True,
                            "position": "Rising",
                            "tier": "T1",
                            "real_trend": "UP",
                        },
                    }
                ],
            )

        decision = planner.decisions[0]
        self.assertEqual(decision.decision, "PRIORITY_WATCHLIST")
        self.assertIn("kospi_swing_edge_promotion=", " ".join(decision.rationale))

    def test_kospi_swing_score_only_promotion_is_off_by_default(self):
        rationale = []

        decision = _apply_kospi_swing_edge_promotion(
            decision="OBSERVE",
            run_market="KOSPI",
            scan_mode="SWING",
            expected_edge_score=None,
            decision_score=95.0,
            rationale=rationale,
        )

        self.assertEqual(decision, "OBSERVE")
        self.assertEqual(rationale, [])

    def test_kospi_swing_score_promotion_can_be_enabled_for_research(self):
        rationale = []

        with patch.dict(
            "os.environ",
            {"AG_KOSPI_SWING_EDGE_PROMOTION": "1", "AG_KOSPI_SWING_SCORE_PROMOTION": "1"},
        ):
            decision = _apply_kospi_swing_edge_promotion(
                decision="OBSERVE",
                run_market="KOSPI",
                scan_mode="SWING",
                expected_edge_score=None,
                decision_score=95.0,
                rationale=rationale,
            )

        self.assertEqual(decision, "PRIORITY_WATCHLIST")
        self.assertIn("decision_score=95.00>=min95.00", " ".join(rationale))

    def test_kosdaq_relative_admission_promotes_soft_risk_when_no_tradeable_candidate(self):
        context = RunContext(run_id="RUN-KQ-ADMIT", market="KOSDAQ")
        with patch.dict("os.environ", {"AG_KOSDAQ_RELATIVE_ADMISSION_FLOOR": "1"}):
            planner = build_planner_handoff(
                context=context,
                weak_ratio=0.0,
                candidates=[
                    {
                        "ticker": "555555.KQ",
                        "stock_name": "Hard Risk",
                        "score": 98.0,
                        "feature_snapshot": {
                            "market": "KOSDAQ",
                            "scan_mode": "SWING",
                            "strategy_family": "KR_CORE",
                            "alpha_score": 99.0,
                            "tech_score": 95.0,
                            "decision_score": 98.0,
                            "prob_5": 10.0,
                            "prob_clean": 12.0,
                            "volume_ratio": 0.2,
                            "volume_confirmed": False,
                            "position": "Peak",
                            "tier": "T3",
                            "real_trend": "DOWN",
                        },
                    },
                    {
                        "ticker": "666666.KQ",
                        "stock_name": "Soft Relative",
                        "score": 72.0,
                        "feature_snapshot": {
                            "market": "KOSDAQ",
                            "scan_mode": "SWING",
                            "strategy_family": "KR_CORE",
                            "alpha_score": 58.0,
                            "tech_score": 65.0,
                            "decision_score": 72.0,
                            "prob_5": 50.0,
                            "prob_clean": 50.0,
                            "phase25_prob": 20.0,
                            "phase25_recommended_threshold": 60.0,
                            "phase25_signal_direction": "normal",
                            "phase25_variant": "phase25_kosdaq_swing",
                            "volume_ratio": 2.5,
                            "volume_confirmed": True,
                            "position": "Rising",
                            "tier": "T1",
                            "real_trend": "UP",
                        },
                    },
                ],
            )

        soft = next(dec for dec in planner.decisions if dec.ticker == "666666.KQ")
        hard = next(dec for dec in planner.decisions if dec.ticker == "555555.KQ")
        self.assertEqual(soft.decision, "WATCHLIST_ONLY")
        self.assertGreaterEqual(float(hard.loss_risk_score or 0.0), 65.0)
        self.assertIn("666666.KQ", planner.watchlist)
        self.assertIn("kosdaq_relative_admission_floor", " ".join(soft.rationale))

    def test_kosdaq_relative_admission_floor_defaults_off(self):
        context = RunContext(run_id="RUN-KQ-ADMIT-OFF", market="KOSDAQ")
        with patch.dict("os.environ", {"AG_KOSDAQ_RELATIVE_ADMISSION_FLOOR": "0"}):
            planner = build_planner_handoff(
                context=context,
                weak_ratio=0.0,
                candidates=[
                    {
                        "ticker": "666666.KQ",
                        "stock_name": "Soft Relative",
                        "score": 72.0,
                        "feature_snapshot": {
                            "market": "KOSDAQ",
                            "scan_mode": "SWING",
                            "strategy_family": "KR_CORE",
                            "alpha_score": 58.0,
                            "tech_score": 65.0,
                            "decision_score": 72.0,
                            "prob_5": 50.0,
                            "prob_clean": 50.0,
                            "phase25_prob": 20.0,
                            "phase25_recommended_threshold": 60.0,
                            "phase25_signal_direction": "normal",
                            "phase25_variant": "phase25_kosdaq_swing",
                            "volume_ratio": 2.5,
                            "volume_confirmed": True,
                            "position": "Rising",
                            "tier": "T1",
                            "real_trend": "UP",
                        },
                    },
                ],
            )

        soft = planner.decisions[0]
        self.assertNotIn("kosdaq_relative_admission_floor", " ".join(soft.rationale))


if __name__ == "__main__":
    unittest.main()
