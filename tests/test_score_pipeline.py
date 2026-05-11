import unittest

from multi_agent.agents.planner_runtime import build_planner_handoff
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
                    "추세": "UP",
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
        self.assertEqual(decision.relative_rank_model, "kospi_decision_score_relative_v1")
        self.assertEqual(decision.market_gate, "YELLOW")
        self.assertEqual(decision.scanner_timeframe_profile, "SWING_DAILY")
        self.assertEqual(decision.kr_universe_role, "CORE_TREND")
        serialized = decision.to_dict()
        self.assertEqual(serialized["market_gate"], "YELLOW")
        self.assertEqual(serialized["scanner_timeframe_profile"], "SWING_DAILY")
        self.assertEqual(serialized["kr_universe_role"], "CORE_TREND")

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
        self.assertEqual(decision.relative_rank_model, "kosdaq_tech_volume_inversion_relative_v2")
        self.assertIn("PHASE25_SWING_BELOW_THRESHOLD_INVERTED_OVERRIDE", decision.theme_risk)
        self.assertIn("kosdaq_swing_inverted_prob_override", " ".join(decision.rationale))

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
        self.assertEqual(planner.decisions[0].relative_rank_model, "kosdaq_tech_volume_inversion_relative_v2")


if __name__ == "__main__":
    unittest.main()
