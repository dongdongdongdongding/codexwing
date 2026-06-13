import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from modules.quant_analysis import QuantStrategy
from modules.scanner_runtime import run_parallel_scan
from modules.ui_helpers import (
    build_action_display,
    build_kr_shadow_gate_records,
    build_live_cockpit_summary,
    build_operating_challenger_gate_diagnostics,
    build_signal_display_rows,
    build_top5_plus_exception_records,
    build_top_candidate_rows,
    build_watchlist_display_rows,
    compute_progress_fraction,
    enrich_signal_rows_with_planner_trace,
    format_volume_display,
    merge_profile_exception_leaders_into_planner,
    resolve_display_price,
    should_auto_refresh_scan_panel,
    sort_signal_rows_by_planner_rank,
)
from ui.scan_cockpit import build_kis_shadow_gate_summary_lines


class UIHelperTests(unittest.TestCase):
    def test_compute_progress_fraction_clamps_bounds(self):
        self.assertEqual(compute_progress_fraction(0, 10), 0.0)
        self.assertEqual(compute_progress_fraction(3, 10), 0.3)
        self.assertEqual(compute_progress_fraction(12, 10), 1.0)
        self.assertEqual(compute_progress_fraction(1, 0), 0.0)

    def test_display_helpers_use_safe_fallbacks(self):
        self.assertEqual(resolve_display_price(101.25, 99.0), 101.25)
        self.assertEqual(resolve_display_price(0, 99.0), 99.0)
        self.assertEqual(resolve_display_price(None, 88.5), 88.5)
        self.assertEqual(format_volume_display(15320.2), "15,320")
        self.assertEqual(format_volume_display(None), "0")

    def test_build_top_candidate_rows_sorts_by_priority_then_score(self):
        rows = build_top_candidate_rows(
            {
                "decisions": [
                    {"ticker": "BBB", "stock_name": "Beta", "priority_rank": 2, "decision_score": 91, "expected_return_1d_pct": 1.2},
                    {"ticker": "AAA", "stock_name": "Alpha", "priority_rank": 1, "decision_score": 88, "expected_return_1d_pct": 0.8},
                    {"ticker": "CCC", "stock_name": "Gamma", "priority_rank": 1, "decision_score": 95, "expected_return_1d_pct": 1.5},
                ]
            },
            limit=2,
        )
        self.assertEqual([row["Ticker"] for row in rows], ["CCC", "AAA"])

    def test_build_top_candidate_rows_demotes_chart_only_candidates(self):
        rows = build_top_candidate_rows(
            {
                "decisions": [
                    {
                        "ticker": "111111.KQ",
                        "stock_name": "ChartOnly",
                        "priority_rank": 1,
                        "decision": "PRIORITY_WATCHLIST",
                        "decision_score": 99,
                        "trend": "UP",
                        "position": "Rising",
                        "tech_score": 96,
                        "alpha_score": 94,
                        "volume_ratio": 3.2,
                        "market_gate": "GREEN",
                    },
                    {
                        "ticker": "005930.KS",
                        "stock_name": "Samsung",
                        "priority_rank": 2,
                        "decision": "PRIORITY_WATCHLIST",
                        "decision_score": 88,
                        "trend": "UP",
                        "position": "Rising",
                        "tech_score": 80,
                        "alpha_score": 78,
                        "volume_ratio": 1.6,
                        "whale_score": 72,
                        "foreigner_1d": 100,
                        "institution_1d": 200,
                        "market_gate": "GREEN",
                        "theme_context": {
                            "primary_theme": "반도체",
                            "theme_strength_score": 76,
                            "theme_direction": "BENEFICIARY",
                        },
                        "kis_theme_news_evidence": {
                            "available": True,
                            "kis_backed": True,
                            "evidence_strength_score": 78,
                            "news": {"checked": True, "news_count": 2, "positive_tags": ["contract_order"]},
                        },
                        "kis_sidecar": {
                            "model_candidate_features": {
                                "kis_per": 18,
                                "kis_pbr": 1.8,
                                "kis_market_cap": 500000000000000,
                            }
                        },
                    },
                ]
            },
            limit=2,
        )

        self.assertEqual([row["Ticker"] for row in rows], ["005930.KS"])
        self.assertEqual(rows[0]["Operational"], "운용 후보")

    def test_should_auto_refresh_scan_panel_only_for_live_states(self):
        self.assertTrue(should_auto_refresh_scan_panel("queued"))
        self.assertTrue(should_auto_refresh_scan_panel("running"))
        self.assertFalse(should_auto_refresh_scan_panel("completed"))
        self.assertFalse(should_auto_refresh_scan_panel("failed"))

    def test_build_watchlist_display_rows_uses_only_exact_source_fields(self):
        rows, visible = build_watchlist_display_rows(
            watchlist=["005930.KS"],
            watchlist_meta=[{"ticker": "005930.KS", "stock_name": "삼성전자", "reason": "planner_lane_watchlist"}],
            decisions=[{"ticker": "005930.KS", "prob_5": 50.0, "prob_clean": 50.0, "decision_score": 88.0, "alpha_score": 81.0, "conviction_score": 64.0}],
            scanner_payload={"candidates": [{"ticker": "005930.KS", "feature_snapshot": {"alpha_score": 79.0, "conviction_score": 63.0, "decision_score": 77.0}}]},
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Alpha"], 81.0)
        self.assertEqual(rows[0]["Conviction"], 64.0)
        self.assertEqual(rows[0]["Decision Score"], 88.0)
        self.assertEqual(rows[0]["Prob5"], 50.0)
        self.assertEqual(rows[0]["Clean"], 50.0)
        self.assertEqual(visible, ["Alpha", "Conviction", "Decision Score", "Prob5", "Clean"])

    def test_build_signal_display_rows_keeps_core_scan_fields(self):
        rows = build_signal_display_rows(
            [
                {
                    "티커": "322310.KQ",
                    "종목명": "오성첨단소재",
                    "Tier": "T1",
                    "전략": "Momentum",
                    "정밀확률": "31.1%",
                    "전일비": "-10.25%",
                    "Decision Score": 99.1,
                    "loss_risk_score": 47.2,
                    "theme_risk": ["LOSS_RISK_SOFT_CAP", "ENTRY_TIMING_RISK_HIGH"],
                    "테마": "반도체",
                    "추세": "UP",
                }
            ]
        )

        self.assertEqual(rows[0]["ticker"], "322310.KQ")
        self.assertEqual(rows[0]["buy_signal"], "T1 · Momentum")
        self.assertEqual(rows[0]["accuracy"], "31.1%")
        self.assertEqual(rows[0]["day_change"], "-10.25%")
        self.assertEqual(rows[0]["day_change_value"], -10.25)
        self.assertEqual(rows[0]["score"], "99.1")
        self.assertEqual(rows[0]["loss_risk"], "47.2")
        self.assertEqual(rows[0]["loss_risk_level"], "주의")
        self.assertEqual(rows[0]["risk_flags"], ["LOSS_RISK_SOFT_CAP", "ENTRY_TIMING_RISK_HIGH"])
        self.assertEqual(rows[0]["action_label"], "눌림/확인 대기")
        self.assertEqual(rows[0]["action_condition"], "지지·재돌파 확인 후 검토")

    def test_kis_shadow_gate_summary_lines_surface_near_production_candidate(self):
        lines = build_kis_shadow_gate_summary_lines(
            {
                "status": "shadow_ready",
                "shadow_display_allowed": True,
                "production_ready": False,
                "near_production_candidate": {
                    "selection_rule": "top3_ev_p0p3_tail0p9",
                    "sample_blockers": ["active_days_lt_15"],
                    "metrics": {
                        "n": 142,
                        "active_days": 11,
                        "hit5_dd10_5d_pct": 83.8028,
                        "avg_5d_pct": 9.912085,
                        "min_min_low_5d_pct": -9.864936,
                    },
                },
            }
        )

        self.assertIn("관찰표시=가능", lines[0])
        self.assertTrue(any("승격근접" in line for line in lines))
        self.assertTrue(any("top3_ev_p0p3_tail0p9" in line for line in lines))
        self.assertTrue(any("hit5=83.8%" in line for line in lines))
        self.assertTrue(any("active_days_lt_15" in line for line in lines))

    def test_build_signal_display_rows_does_not_fabricate_day_change(self):
        # 2026-05-09: phase25_prob은 raw score(0-100)로 calibrated probability가
        # 아니다. 카드 '정확성' coalesce에서 제외함 — 사용자에게 모델 raw score를
        # '정확도'로 보여주면 KOSPI SWING 35% / KOSDAQ SWING 12%처럼 오해 발생.
        # 진짜 정확성 source: phase25_oos_win_rate_pct, prob_clean, ml_prob.
        rows = build_signal_display_rows([{
            "ticker": "005930.KS",
            "phase25_prob": 61.2,             # raw score (사용 안 함)
            "phase25_oos_win_rate_pct": 75.4,  # OOS holdout win rate
            "return_1d_pct": 3.4,
        }])
        self.assertEqual(rows[0]["accuracy"], "75.4%")
        self.assertEqual(rows[0]["day_change"], "-")
        self.assertEqual(rows[0]["day_change_value"], None)

    def test_build_signal_display_rows_uses_admission_feature_day_change(self):
        rows = build_signal_display_rows([
            {
                "ticker": "322310.KQ",
                "stock_name": "오성첨단소재",
                "scan_universe_admission": {
                    "probability_pct": 61.2,
                    "feature_values": {"day_return_pct": -4.32},
                },
            }
        ])

        self.assertEqual(rows[0]["day_change"], "-4.32%")
        self.assertEqual(rows[0]["day_change_value"], -4.32)

    def test_build_signal_display_rows_adds_korean_display_labels_without_dropping_codes(self):
        rows = build_signal_display_rows([
            {
                "ticker": "320000.KQ",
                "stock_name": "한울반도체",
                "decision": "ADMISSION_PASS",
                "_analysis_section": "Scan Universe Admission",
                "risk_flags": ["SCAN_UNIVERSE_ADMISSION_MODEL", "model=lightgbm", "objective=5d_touch_5"],
                "final_action": "Admission 모델 통과 - 5D +5% 목표터치 후보",
                "stop_condition_text": "표시 손절 · unavailable",
                "scan_universe_admission": {
                    "model_name": "lightgbm",
                    "selection_rule": "top1",
                    "input_source_role": "rejected",
                    "legacy_reject_reason": "KR_BASELINE_FILTER_FAIL",
                },
                "scan_result_interpretation": {
                    "model_decision": "ADMISSION_PASS",
                    "action": "Admission 모델 통과",
                    "drivers": ["SCAN_UNIVERSE_ADMISSION_MODEL"],
                    "warnings": ["KR_BASELINE_FILTER_FAIL"],
                    "plain_text": "Admission 모델 기준",
                },
            }
        ])

        self.assertEqual(rows[0]["buy_signal"], "ADMISSION_PASS")
        self.assertEqual(rows[0]["buy_signal_label"], "운영 통과")
        self.assertEqual(rows[0]["analysis_section_label"], "운영 모델 통과")
        self.assertEqual(rows[0]["risk_flags"][0], "SCAN_UNIVERSE_ADMISSION_MODEL")
        self.assertEqual(rows[0]["risk_flag_labels"][0], "운영 모델 판단")
        self.assertEqual(rows[0]["action_label_display"], "운영 모델 통과 - 5D +5% 목표터치 후보")
        self.assertIn("미제공", rows[0]["stop_condition_display"])
        self.assertEqual(rows[0]["admission_model_label"], "LightGBM")
        self.assertEqual(rows[0]["admission_selection_rule_label"], "1순위 선발")
        self.assertEqual(rows[0]["admission_input_source_role_label"], "기존 필터 탈락 종목")
        self.assertEqual(rows[0]["admission_legacy_reject_reason_label"], "기존 운영 필터 탈락")
        self.assertEqual(rows[0]["scan_model_decision_label"], "운영 통과")
        self.assertEqual(rows[0]["scan_interpretation_warning_labels"], ["기존 운영 필터 탈락"])
        self.assertEqual(rows[0]["scan_interpretation_text_label"], "운영 모델 기준")

    def test_build_signal_display_rows_preserves_kis_theme_news_summary(self):
        rows = build_signal_display_rows([
            {
                "ticker": "005930.KS",
                "stock_name": "삼성전자",
                "kis_theme_news_evidence": {
                    "contract_version": "kis_theme_news_evidence_v1",
                    "available": True,
                    "kis_backed": True,
                    "evidence_strength_score": 78.0,
                    "evidence_strength_level": "strong",
                    "theme": {"primary_theme": "AI반도체", "kis_sector_name": "반도체"},
                    "news": {
                        "checked": True,
                        "news_count": 1,
                        "headlines": [{"title": "KIS headline"}],
                        "positive_tags": ["contract_order"],
                        "risk_tags": [],
                    },
                    "market_action": {"prefilter_sources": ["volume_rank"], "vi_triggered": True},
                    "warnings": [],
                },
            }
        ])

        self.assertTrue(rows[0]["kis_theme_news_kis_backed"])
        self.assertEqual(rows[0]["kis_theme_news_score"], 78.0)
        self.assertIn("KIS headline", rows[0]["kis_theme_news_summary"])

    def test_build_action_display_maps_existing_trace_without_core_policy_change(self):
        self.assertEqual(
            build_action_display({
                "decision": "PRIORITY_WATCHLIST",
                "theme_risk": [],
                "loss_risk_score": 22.0,
            })["label"],
            "조건부 매수 가능",
        )
        self.assertEqual(
            build_action_display({
                "decision": "PRIORITY_WATCHLIST",
                "theme_risk": ["ENTRY_TIMING_RISK_HIGH"],
            })["label"],
            "눌림/확인 대기",
        )
        blocked = build_action_display({
            "decision": "WATCHLIST",
            "theme_risk": ["LOSS_RISK_HARD_CAP"],
        })
        self.assertEqual(blocked["label"], "매수 금지")
        self.assertEqual(blocked["condition"], "리스크 해소 전 신규 진입 금지")

    def test_build_action_display_prefers_planner_action_plan(self):
        action = build_action_display({
            "decision": "WATCHLIST_ONLY",
            "loss_risk_score": 35.0,
            "final_action": "관망",
            "entry_condition_text": "시장 정책이 관망 구간입니다. GREEN/YELLOW 회복 후 재평가",
            "stop_condition_text": "진입 전 상태이므로 손절가 대신 제외 조건으로 관리",
        })

        self.assertEqual(action["label"], "관망")
        self.assertIn("GREEN/YELLOW", action["condition"])
        self.assertIn("제외 조건", action["stop_condition"])

    def test_build_signal_display_rows_ignores_raw_phase25_prob(self):
        # phase25_prob 단독이면 accuracy는 None. raw score를 정확도로 표시 금지.
        rows = build_signal_display_rows([{
            "ticker": "005930.KS",
            "phase25_prob": 35.7,             # KOSPI SWING 평균 raw score
        }])
        self.assertEqual(rows[0]["accuracy"], "-")

    def test_build_live_cockpit_summary_surfaces_validated_policy(self):
        with patch("modules.ui_helpers.live_policy_summary") as live_policy:
            live_policy.return_value = {
                "policy": "exception_leader OR expected_edge_score>=5",
                "validated_win": "72.5%",
                "validated_return": "+7.65%",
                "sample": "n=447 · loss5 9.5%",
                "quality_scope": "observed_archive",
                "validation_pass": True,
            }
            summary = build_live_cockpit_summary(
                [{"ticker": "005930.KS"}],
                [{"ticker": "000660.KS"}],
                market="KOSPI",
                strict_quality_gate=False,
            )

        self.assertEqual(summary["actionable_count"], 2)
        self.assertEqual(summary["quality_gate"], "OFF")
        self.assertEqual(summary["policy"], "exception_leader OR expected_edge_score>=5")
        self.assertEqual(summary["validated_win"], "72.5%")
        self.assertEqual(summary["quality_scope"], "observed_archive")

    def test_enrich_signal_rows_with_planner_trace_adds_loss_risk(self):
        rows = enrich_signal_rows_with_planner_trace(
            [{"ticker": "005930.KS", "Decision Score": 90.0}],
            {
                "decisions": [
                    {
                        "ticker": "005930.KS",
                        "decision": "PRIORITY_WATCHLIST",
                        "loss_risk_score": 42.5,
                        "theme_risk": ["LOSS_RISK_SOFT_CAP"],
                    }
                ]
            },
        )
        self.assertEqual(rows[0]["loss_risk_score"], 42.5)
        self.assertEqual(rows[0]["theme_risk"], ["LOSS_RISK_SOFT_CAP"])
        display = build_signal_display_rows(rows)
        self.assertEqual(display[0]["loss_risk"], "42.5")
        self.assertEqual(display[0]["risk_flags"], ["LOSS_RISK_SOFT_CAP"])

    def test_watchlist_meta_enrichment_adds_action_plan_to_scan_rows(self):
        rows = enrich_signal_rows_with_planner_trace(
            [{"ticker": "005930.KS", "Decision Score": 90.0}],
            {
                "decisions": [],
                "watchlist_meta": [
                    {
                        "ticker": "005930.KS",
                        "decision": "WATCHLIST_ONLY",
                        "loss_risk_score": 52.1,
                        "theme_risk": ["LOSS_RISK_SOFT_CAP"],
                        "final_action": "관망",
                        "entry_condition_text": "시장 정책이 관망 구간입니다. GREEN/YELLOW 회복 후 재평가",
                        "stop_condition_text": "진입 전 상태이므로 손절가 대신 제외 조건으로 관리",
                    }
                ],
            },
        )

        self.assertEqual(rows[0]["loss_risk_score"], 52.1)
        self.assertEqual(rows[0]["final_action"], "관망")
        display = build_signal_display_rows(rows)
        self.assertEqual(display[0]["loss_risk"], "52.1")
        self.assertEqual(display[0]["action_label"], "관망")
        self.assertIn("GREEN/YELLOW", display[0]["action_condition"])
        self.assertIn("제외 조건", display[0]["stop_condition"])

    def test_sort_signal_rows_by_planner_rank_uses_final_priority_before_raw_score(self):
        rows = enrich_signal_rows_with_planner_trace(
            [
                {"ticker": "RAW1.KS", "score": 99.0},
                {"ticker": "TOP1.KS", "score": 70.0},
                {"ticker": "TOP2.KS", "score": 80.0},
            ],
            {
                "decisions": [
                    {"ticker": "TOP1.KS", "decision": "PRIORITY_WATCHLIST", "priority_rank": 1, "relative_rank_score": 60.0},
                    {"ticker": "TOP2.KS", "decision": "WATCHLIST", "priority_rank": 2, "relative_rank_score": 55.0},
                    {"ticker": "RAW1.KS", "decision": "WATCHLIST", "priority_rank": 3, "relative_rank_score": 40.0},
                ]
            },
        )
        sorted_rows = sort_signal_rows_by_planner_rank(rows)
        self.assertEqual([row["ticker"] for row in sorted_rows], ["TOP1.KS", "TOP2.KS", "RAW1.KS"])

    def test_top5_plus_exception_keeps_top5_main_and_exception_addon(self):
        rows = [
            {"ticker": "RAW1.KS", "Decision Score": 99.0, "_raw_scan_rank": 1},
            {"ticker": "EX1.KS", "Decision Score": 70.0, "_raw_scan_rank": 8},
            {"ticker": "TOP1.KS", "Decision Score": 88.0, "_raw_scan_rank": 2},
        ]
        planner = {
            "decisions": [
                {"ticker": "TOP1.KS", "decision": "PRIORITY_WATCHLIST", "priority_rank": 1, "relative_rank_score": 70.0},
                {"ticker": "EX1.KS", "decision": "WATCHLIST", "decision_bucket": "exception_leader", "priority_rank": 2, "relative_rank_score": 50.0},
                {"ticker": "RAW1.KS", "decision": "WATCHLIST", "priority_rank": 3, "relative_rank_score": 30.0},
            ]
        }

        groups = build_top5_plus_exception_records(rows, planner, top_limit=2, exception_limit=2)

        self.assertEqual([row["ticker"] for row in groups["top5"]], ["TOP1.KS", "RAW1.KS"])
        self.assertEqual([row["ticker"] for row in groups["exception_leaders"]], ["EX1.KS"])
        self.assertEqual([row["ticker"] for row in groups["combined"]], ["TOP1.KS", "RAW1.KS", "EX1.KS"])
        self.assertEqual(groups["top5"][0]["_analysis_section"], "Top5")
        self.assertEqual(groups["exception_leaders"][0]["_analysis_section"], "Exception Leader")

    def test_top5_plus_exception_fills_top5_after_validated_profile_promotion(self):
        rows = [
            {"ticker": "VALID.KS", "Decision Score": 90.0, "_raw_scan_rank": 1},
            {"ticker": "RAW1.KS", "Decision Score": 80.0, "_raw_scan_rank": 2},
            {"ticker": "RAW2.KS", "Decision Score": 70.0, "_raw_scan_rank": 3},
        ]

        def fake_profile(row):
            if row.get("ticker") == "VALID.KS":
                return {"level": "pass", "label": "검증 Top5", "profile": "test", "metrics": "n=1"}
            return {"level": "fail", "label": "검증 미달", "profile": "", "metrics": ""}

        with patch("modules.ui_helpers.validated_winner_profile", side_effect=fake_profile):
            groups = build_top5_plus_exception_records(rows, None, top_limit=3, exception_limit=0)

        self.assertEqual([row["ticker"] for row in groups["top5"]], ["VALID.KS", "RAW1.KS", "RAW2.KS"])
        self.assertEqual(groups["top5"][0]["_validated_winner_profile"]["profile"], "test")
        self.assertEqual(len(groups["combined"]), 3)

    def test_top5_plus_exception_does_not_promote_near_profile(self):
        rows = [
            {"ticker": "RAW1.KQ", "Decision Score": 90.0, "_raw_scan_rank": 1},
            {"ticker": "NEAR.KQ", "Decision Score": 80.0, "_raw_scan_rank": 2},
        ]

        def fake_profile(row):
            if row.get("ticker") == "NEAR.KQ":
                return {"level": "near", "label": "관찰", "profile": "near", "metrics": "n=10"}
            return {"level": "fail", "label": "검증 미달", "profile": "", "metrics": ""}

        with patch("modules.ui_helpers.validated_winner_profile", side_effect=fake_profile):
            groups = build_top5_plus_exception_records(rows, None, top_limit=2, exception_limit=0)

        self.assertEqual([row["ticker"] for row in groups["top5"]], ["RAW1.KQ", "NEAR.KQ"])
        self.assertNotIn("_validated_winner_profile", groups["top5"][0])

    def test_top5_plus_exception_lifts_practical_gate_without_duplicate_combined_rows(self):
        rows = [
            {"ticker": "PRACTICAL.KS", "Decision Score": 90.0, "_raw_scan_rank": 1},
            {"ticker": "RAW1.KS", "Decision Score": 80.0, "_raw_scan_rank": 2},
            {"ticker": "EX1.KS", "Decision Score": 70.0, "_raw_scan_rank": 8},
        ]
        planner = {
            "decisions": [
                {"ticker": "PRACTICAL.KS", "decision": "PRIORITY_WATCHLIST", "priority_rank": 1},
                {"ticker": "RAW1.KS", "decision": "WATCHLIST", "priority_rank": 2},
                {"ticker": "EX1.KS", "decision": "WATCHLIST", "decision_bucket": "exception_leader", "priority_rank": 3},
            ]
        }

        def fake_practical(row):
            if row.get("ticker") == "PRACTICAL.KS":
                return {"level": "pass", "promote": True, "label": "실전 80% 필터 통과"}
            return {"level": "fail", "promote": False, "label": "실전 80% 필터 미달"}

        with patch("modules.ui_helpers.evaluate_practical_entry_gate", side_effect=fake_practical):
            groups = build_top5_plus_exception_records(rows, planner, top_limit=2, exception_limit=2)

        self.assertEqual([row["ticker"] for row in groups["practical"]], ["PRACTICAL.KS"])
        self.assertEqual(groups["practical"][0]["_analysis_section"], "Practical 80 Gate")
        self.assertEqual([row["ticker"] for row in groups["combined"]], ["PRACTICAL.KS", "RAW1.KS", "EX1.KS"])
        self.assertEqual(len({row["ticker"] for row in groups["combined"]}), len(groups["combined"]))

    def test_top5_plus_exception_adds_planner_only_exception_leaders(self):
        rows = [
            {"ticker": f"TOP{i}.KQ", "Decision Score": 100.0 - i, "_raw_scan_rank": i}
            for i in range(1, 6)
        ]
        planner = {
            "decisions": [
                {
                    "ticker": f"TOP{i}.KQ",
                    "decision": "PRIORITY_WATCHLIST",
                    "priority_rank": i,
                    "relative_rank_score": 90.0 - i,
                }
                for i in range(1, 6)
            ],
            "watchlist_meta": [
                {
                    "ticker": f"EX{i}.KQ",
                    "stock_name": f"Exception {i}",
                    "risk_label": "EXCEPTION_LEADER",
                    "reason": "exception_leader_watchlist",
                    "priority_rank": 100 + i,
                    "relative_rank_score": 70.0 - i,
                }
                for i in range(1, 7)
            ],
        }

        groups = build_top5_plus_exception_records(rows, planner, top_limit=5, exception_limit=5)

        self.assertEqual([row["ticker"] for row in groups["top5"]], [f"TOP{i}.KQ" for i in range(1, 6)])
        self.assertEqual(
            [row["ticker"] for row in groups["exception_leaders"]],
            [f"EX{i}.KQ" for i in range(1, 6)],
        )
        self.assertEqual(len(groups["combined"]), 10)
        self.assertEqual(groups["combined"][-1]["_analysis_section"], "Exception Leader")

    def test_kr_shadow_gate_records_lift_kosdaq_and_kospi_sections(self):
        rows = [
            {
                "ticker": "KQ1.KQ",
                "market": "KOSDAQ",
                "primary_theme": "로봇/자동화",
                "tech_score": 75,
                "trend": "UP",
                "theme_day_symbol_count": 7,
                "theme_day_avg_decision_score": 60,
            },
            {
                "ticker": "KS1.KS",
                "market": "KOSPI",
                "primary_theme": "전력기기",
                "alpha_score": 70.0,
                "prob_clean": 36.0,
                "kr_universe_role": "CORE_TREND",
            },
            {
                "ticker": "KS2.KS",
                "market": "KOSPI",
                "primary_theme": "전력기기",
                "alpha_score": 90.0,
                "prob_clean": 36.0,
                "kr_universe_role": "EXPLOSIVE_LEADER",
            },
            {
                "ticker": "KS3.KS",
                "market": "KOSPI",
                "primary_theme": "게임",
                "alpha_score": 66.0,
                "prob_clean": 36.0,
                "kr_universe_role": "CORE_TREND",
            },
        ]

        groups = build_kr_shadow_gate_records(rows, limit=5)

        self.assertEqual([row["ticker"] for row in groups["kosdaq"]], ["KQ1.KQ"])
        self.assertEqual([row["ticker"] for row in groups["kospi"]], ["KS1.KS"])
        self.assertEqual(groups["kosdaq"][0]["_analysis_section"], "KOSDAQ Low-loss Shadow")
        self.assertEqual(groups["kospi"][0]["_analysis_section"], "KOSPI Shadow")

    def test_kr_shadow_gate_records_promote_operating_challengers_first(self):
        rows = [
            {
                "ticker": "KSOP.KS",
                "market": "KOSPI",
                "priority_rank": 1,
                "phase25_prob": 30.0,
                "theme_day_strength_rank": 3,
                "theme_day_strength_score": 2.5,
            },
            {
                "ticker": "KQOP.KQ",
                "market": "KOSDAQ",
                "theme_day_avg_volume_ratio": 1.0,
                "theme_day_avg_expected_return_1d_pct": 0.2,
                "tech_score": 60,
                "theme_day_avg_alpha_score": 60.0,
            },
            {
                "ticker": "KQLOW.KQ",
                "market": "KOSDAQ",
                "primary_theme": "로봇/자동화",
                "tech_score": 75,
                "trend": "UP",
                "theme_day_symbol_count": 7,
                "theme_day_avg_decision_score": 60,
            },
        ]

        groups = build_kr_shadow_gate_records(rows, limit=5)

        self.assertEqual([row["ticker"] for row in groups["operating"]], ["KSOP.KS", "KQOP.KQ"])
        self.assertEqual(
            [row["_analysis_section"] for row in groups["combined"][:2]],
            ["KOSPI Operating Challenger", "KOSDAQ Operating Challenger"],
        )
        self.assertEqual([row["ticker"] for row in groups["kospi_operating"]], ["KSOP.KS"])
        self.assertEqual([row["ticker"] for row in groups["kosdaq_operating"]], ["KQOP.KQ"])
        self.assertEqual(groups["combined"][2]["_analysis_section"], "KOSDAQ Low-loss Shadow")

    def test_operating_gate_diagnostics_show_near_miss_percentages(self):
        rows = [
            {
                "ticker": "NEAR.KS",
                "market": "KOSPI",
                "priority_rank": 4,
                "phase25_prob": 30.0,
                "theme_day_strength_rank": 3,
                "theme_day_strength_score": 2.5,
                "decision_score": 90,
            },
            {
                "ticker": "FAR.KS",
                "market": "KOSPI",
                "priority_rank": 9,
                "phase25_prob": 80.0,
                "theme_day_strength_rank": 20,
                "theme_day_strength_score": 0.2,
                "decision_score": 99,
            },
        ]

        diagnostics = build_operating_challenger_gate_diagnostics(rows, market="KOSPI", limit=2)

        self.assertEqual(diagnostics[0]["ticker"], "NEAR.KS")
        self.assertGreater(diagnostics[0]["completion_pct"], diagnostics[1]["completion_pct"])
        self.assertEqual(diagnostics[0]["passed_count"], 3)
        self.assertEqual(diagnostics[0]["total_count"], 4)
        failed_labels = [item["label"] for item in diagnostics[0]["conditions"] if not item["passed"]]
        self.assertEqual(failed_labels, ["Top3"])

    def test_kr_shadow_gate_separates_kosdaq_ordered_and_low_loss_contracts(self):
        rows = [
            {
                "ticker": "ORDERED.KQ",
                "market": "KOSDAQ",
                "candidate_id": "5D_ordered_5v5",
                "volume_ratio": 1.2,
                "trend": "DOWN",
                "selection_lane": "1d",
            },
            {
                "ticker": "LOWLOSS.KQ",
                "market": "KOSDAQ",
                "primary_theme": "로봇/자동화",
                "tech_score": 75,
                "trend": "UP",
                "theme_day_symbol_count": 7,
                "theme_day_avg_decision_score": 60,
            },
            {
                "ticker": "THEMERANK.KQ",
                "market": "KOSDAQ",
                "primary_theme": "반도체",
                "prob_clean": 30,
                "theme_day_avg_decision_score": 75,
                "theme_day_strength_rank": 1,
                "theme_day_strength_score": 2.1,
            },
        ]

        groups = build_kr_shadow_gate_records(rows, limit=5)

        self.assertEqual([row["ticker"] for row in groups["kosdaq_ordered"]], ["ORDERED.KQ"])
        self.assertEqual([row["ticker"] for row in groups["kosdaq_theme_rank"]], ["THEMERANK.KQ"])
        self.assertEqual([row["ticker"] for row in groups["kosdaq_low_loss"]], ["LOWLOSS.KQ"])
        self.assertEqual(
            [row["_analysis_section"] for row in groups["kosdaq"]],
            ["KOSDAQ Ordered Shadow", "KOSDAQ Theme Rank Shadow", "KOSDAQ Low-loss Shadow"],
        )

    def test_kr_shadow_gate_uses_planner_theme_metrics_display_fields(self):
        rows = [
            {
                "티커": "KQ2.KQ",
                "market": "KOSDAQ",
                "종목명": "Planner Lane",
                "테마": "로봇/자동화",
                "추세": "UP",
                "Tech": 75,
                "theme_day_symbol_count": 7,
                "theme_day_avg_decision_score": 60,
            }
        ]
        planner = {
            "decisions": [
                {
                    "ticker": "KQ2.KQ",
                    "stock_name": "Planner Lane",
                    "primary_theme": "로봇/자동화",
                    "real_trend": "UP",
                    "tech_score": 75,
                    "decision_score": 70,
                    "theme_day_symbol_count": 7,
                    "theme_day_avg_decision_score": 60,
                }
            ]
        }

        groups = build_kr_shadow_gate_records(rows, planner, limit=5)

        self.assertEqual([row["티커"] for row in groups["kosdaq"]], ["KQ2.KQ"])
        self.assertEqual(groups["kosdaq"][0]["Tech"], 75)
        self.assertEqual(groups["kosdaq"][0]["추세"], "UP")

    def test_profile_only_exception_leaders_are_merged_into_planner_contract(self):
        planner = {
            "decisions": [{"ticker": "TOP1.KS", "decision": "PRIORITY_WATCHLIST"}],
            "watchlist_meta": [],
        }
        profile = {
            "exception_leaders": {
                "watchlist_meta": [
                    {
                        "ticker": "EX1.KS",
                        "stock_name": "Profile Exception",
                        "risk_label": "EXCEPTION_LEADER",
                        "reason": "exception_leader_watchlist",
                    }
                ]
            }
        }

        merged = merge_profile_exception_leaders_into_planner(planner, profile)
        groups = build_top5_plus_exception_records(
            [{"ticker": "TOP1.KS", "Decision Score": 90.0}],
            merged,
            top_limit=5,
            exception_limit=5,
        )

        self.assertEqual([row["ticker"] for row in groups["top5"]], ["TOP1.KS"])
        self.assertEqual([row["ticker"] for row in groups["exception_leaders"]], ["EX1.KS"])


class ScannerRuntimeTests(unittest.TestCase):
    def test_run_parallel_scan_emits_callback_for_each_symbol(self):
        progress_updates = []

        def worker(sym):
            return {"ticker": sym}

        def on_item(i, total_scans, sym, data, exc):
            progress_updates.append((sym, compute_progress_fraction(i + 1, total_scans), exc, data))

        result = run_parallel_scan(
            ticker_list=["A", "B", "C"],
            max_scan=0,
            worker_fn=worker,
            max_workers=2,
            on_item=on_item,
        )

        self.assertEqual(result["total_scans"], 3)
        self.assertEqual(len(progress_updates), 3)
        self.assertEqual([round(item[1], 4) for item in progress_updates], [0.3333, 0.6667, 1.0])
        self.assertTrue(all(item[2] is None for item in progress_updates))


class QuantStrategyRealtimePriceTests(unittest.TestCase):
    @patch("modules.quant_analysis.yf.Ticker")
    def test_get_realtime_price_prefers_fast_info(self, ticker_cls):
        ticker_mock = MagicMock()
        ticker_mock.fast_info = {"last_price": 123.45}
        ticker_mock.info = {"currentPrice": 120.0}
        ticker_cls.return_value = ticker_mock

        qs = QuantStrategy("AAPL")
        qs.df = pd.DataFrame({"Close": [111.0]})

        self.assertEqual(qs.get_realtime_price(), 123.45)

    @patch("modules.quant_analysis.yf.Ticker")
    def test_get_realtime_price_falls_back_to_info_then_dataframe(self, ticker_cls):
        ticker_mock = MagicMock()
        ticker_mock.fast_info = {"last_price": None}
        ticker_mock.info = {"regularMarketPrice": 77.7}
        ticker_cls.return_value = ticker_mock

        qs = QuantStrategy("AAPL")
        qs.df = pd.DataFrame({"Close": [55.0]})
        self.assertEqual(qs.get_realtime_price(), 77.7)

        ticker_mock.info = {}
        self.assertEqual(qs.get_realtime_price(), 55.0)


class QuantStrategyFetchDataVolumeTests(unittest.TestCase):
    @patch.object(QuantStrategy, "get_intraday_volume_multiplier", return_value=1.0)
    @patch("modules.quant_analysis.live_mode_enabled", return_value=True)
    @patch("modules.quant_analysis.get_history")
    def test_fetch_data_refreshes_last_daily_bar_from_intraday_tape(self, get_history_mock, _live_mode_mock, _multiplier_mock):
        daily_index = pd.date_range("2026-02-19", periods=60, freq="D")
        daily_df = pd.DataFrame(
            {
                "Open": [100.0 + i for i in range(60)],
                "High": [110.0 + i for i in range(60)],
                "Low": [99.0 + i for i in range(60)],
                "Close": [108.0 + i for i in range(60)],
                "Volume": [1000.0 + i for i in range(60)],
            },
            index=daily_index,
        )
        daily_df.iloc[-1] = [101.0, 111.0, 100.0, 109.0, 1200.0]
        intraday_index = pd.to_datetime(["2026-04-19 10:00", "2026-04-19 11:00"])
        intraday_df = pd.DataFrame(
            {
                "Open": [103.0, 106.0],
                "High": [115.0, 118.0],
                "Low": [102.0, 105.0],
                "Close": [107.0, 117.0],
                "Volume": [900.0, 800.0],
            },
            index=intraday_index,
        )
        get_history_mock.side_effect = [daily_df, intraday_df]

        qs = QuantStrategy("005930.KS")

        self.assertTrue(qs.fetch_data(period="5y"))
        self.assertEqual(float(qs.df.iloc[-1]["Open"]), 103.0)
        self.assertEqual(float(qs.df.iloc[-1]["High"]), 118.0)
        self.assertEqual(float(qs.df.iloc[-1]["Low"]), 100.0)
        self.assertEqual(float(qs.df.iloc[-1]["Close"]), 117.0)
        self.assertEqual(float(qs.df.iloc[-1]["Volume"]), 1700.0)


if __name__ == "__main__":
    unittest.main()
