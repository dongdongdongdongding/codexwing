import json

import pytest

from modules import realized_expectancy_admission as rea
from modules import regime_theme_calibration as rtc
from modules.realized_expectancy_admission import (
    ADMISSION_POLICY_VERSION,
    build_realized_expectancy_admission,
    compare_original_vs_expectancy_order,
    compare_unadjusted_vs_regime_theme_order,
    sort_by_realized_expectancy,
)

# 픽스처가 갈아끼우기 전의 진짜 로더를 임포트 시점에 붙잡아 둔다.
# 아래 순수성 회귀 테스트가 "핀이 없으면 실제로 깨진다"를 증명하는 데 쓴다.
_REAL_DAILY_CALIBRATIONS = rea._daily_section_calibrations

STRONG_EXCEPTION_LEADER_ROW = {
    "market": "KOSPI",
    "_analysis_section": "Exception Leader",
    "expected_edge_score": -1.0,
    "prob_clean": 62.0,
    "decision_score": 86.0,
    "loss_risk_score": 30.0,
    "trend": "UP",
    "volume_ratio": 2.4,
    "day_change_pct": 3.5,
    "position": "Rising",
}


@pytest.fixture(autouse=True)
def pin_calibration_sources(monkeypatch):
    """이 파일은 점수 '공식'을 재는 곳이지 오늘자 운영 데이터를 재는 곳이 아니다.

    `calibration_for()`는 DEFAULT_CALIBRATIONS 위에 런타임 산출물 두 개를 덮어쓴다:

      - runtime_state/reports/validation/kr_section_performance_calibration.json  (.gitignore:61)
      - runtime_state/reports/trading/signal_section_performance_daily.json       (.gitignore:60)

    둘 다 **상대경로**라 cwd에 따라, 그리고 데일리옵스를 돌렸는지에 따라 있다가 없다가 한다.
    운영자 체크아웃(파일 있음)에서는 KOSPI/Exception Leader의 avg_return_5d_pct가
    +8.88(validated_profile_default) → -1.36(signal_section_performance_daily)로 뒤집혀
    ranking_score_5d가 **83.70 → 56.15**로 내려앉고
    test_negative_expected_edge_can_pass_* 가 빨간불이 됐다(실측).
    새 클론에는 그 파일이 없어 초록이라, 클론 기준 CI로는 영원히 보이지 않는다.

    9b1410b(밸류체인 프로필 핀)와 같은 계열이고 방향만 반대다. 같은 처방을 쓴다 —
    테스트가 보는 캘리브레이션을 코드에 고정된 기본 프로필로 못박는다.
    운영 코드는 건드리지 않는다. 산출물이 실제 판정을 바꾼다는 사실 자체는
    test_scoring_is_immune_to_runtime_calibration_artifacts 가 따로 지킨다.
    """
    rea._ARTIFACT_CALIBRATION_CACHE.clear()
    rea._DAILY_CALIBRATION_CACHE.clear()
    monkeypatch.setattr(rea, "_artifact_calibrations", lambda: {})
    monkeypatch.setattr(rea, "_daily_section_calibrations", lambda: {})
    # theme_cache/KR.json은 tracked지만 데일리옵스가 매일 덮어쓴다. 지금은 배수 1.0이라
    # 수치에 영향이 없지만(실측), 잠재 의존을 남겨둘 이유가 없어 같이 못박는다.
    monkeypatch.setattr(rtc, "load_theme_cache", lambda path=rtc.DEFAULT_THEME_CACHE_PATH: {})
    yield
    rea._ARTIFACT_CALIBRATION_CACHE.clear()
    rea._DAILY_CALIBRATION_CACHE.clear()


def test_negative_expected_edge_can_pass_when_momentum_and_section_are_strong():
    admission = build_realized_expectancy_admission(
        dict(STRONG_EXCEPTION_LEADER_ROW),
        market="KOSPI",
        section="Exception Leader",
    )

    assert admission["available"] is True
    assert admission["policy_version"] == ADMISSION_POLICY_VERSION
    # 어떤 프로필로 잰 점수인지까지 못박는다. 이게 빠져 있어서 런타임 산출물이
    # 조용히 기준을 갈아끼워도 아무도 몰랐다.
    assert admission["calibration_source"] == "validated_profile_default"
    assert admission["ranking_score_5d"] >= 58.0
    assert admission["stop_first_risk_pct"] < 28.0
    assert admission["base_expected_value_5d_pct"] == admission["expected_value_5d_pct"]
    assert admission["stress_expected_value_5d_pct"] < admission["base_expected_value_5d_pct"]
    assert admission["expected_value_band"]["stress_5d_pct"] == admission["stress_expected_value_5d_pct"]


def _write_hostile_daily_snapshot(root) -> None:
    """운영자 체크아웃에서 실제로 관측된 모양의 일자 스냅샷을 심는다.

    실측값(2026-08-14 운영자 체크아웃, KOSPI/Exception Leader):
    win_5d 45.32% / avg_5d -1.3597% — 기본 프로필(86.7% / +8.88%)과 부호가 반대다.
    """
    path = root / "runtime_state" / "reports" / "trading" / "signal_section_performance_daily.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for horizon, win, avg, worst, best, avg_loss in (
        (3, 49.46, -0.2002, -34.8688, 34.7962, -7.3385),
        (5, 45.32, -1.3597, -41.0496, 52.1531, -10.9052),
    ):
        rows.append(
            {
                "market": "KOSPI",
                "section": "Exception Leader",
                "scan_mode": "SWING",
                "horizon_days": horizon,
                "sample_n": 552,
                "win_rate_pct": win,
                "avg_return_pct": avg,
                "avg_loss_return_pct": avg_loss,
                "worst_return_pct": worst,
                "best_return_pct": best,
                "as_of_date": "2026-08-13",
                "generated_at": "2026-08-13T23:59:00+00:00",
            }
        )
    path.write_text(json.dumps(rows), encoding="utf-8")


def test_scoring_is_immune_to_runtime_calibration_artifacts(tmp_path, monkeypatch):
    """F-5 회귀: gitignore된 런타임 산출물의 유무가 이 파일의 판정을 바꿔선 안 된다.

    이 테스트는 두 가지를 동시에 지킨다.
      ① 위험이 실재한다 — 산출물을 그대로 먹이면 ranking_score_5d가 임계선 아래로 떨어진다.
      ② 그런데도 핀이 걸린 경로는 한 글자도 안 바뀐다.
    ①이 없으면 이 테스트는 아무것도 증명하지 않는 no-op이 된다.
    """
    pinned = build_realized_expectancy_admission(
        dict(STRONG_EXCEPTION_LEADER_ROW), market="KOSPI", section="Exception Leader"
    )

    monkeypatch.chdir(tmp_path)
    _write_hostile_daily_snapshot(tmp_path)
    rea._DAILY_CALIBRATION_CACHE.clear()

    # ① 핀을 풀면 실제로 뒤집힌다 (운영자 체크아웃 재현)
    hostile = _REAL_DAILY_CALIBRATIONS()
    assert hostile[("KOSPI", "Exception Leader")].avg_return_5d_pct < 0.0
    poisoned = build_realized_expectancy_admission(
        dict(STRONG_EXCEPTION_LEADER_ROW),
        market="KOSPI",
        section="Exception Leader",
        calibrations={**rea.DEFAULT_CALIBRATIONS, **hostile},
    )
    assert poisoned["calibration_source"] == "signal_section_performance_daily"
    assert poisoned["ranking_score_5d"] < 58.0

    # ② 핀이 걸린 기본 경로는 산출물이 발밑에 있어도 그대로다
    after = build_realized_expectancy_admission(
        dict(STRONG_EXCEPTION_LEADER_ROW), market="KOSPI", section="Exception Leader"
    )
    assert after["calibration_source"] == "validated_profile_default"
    assert after == pinned


def test_high_score_with_weak_edge_and_stop_risk_is_penalized():
    admission = build_realized_expectancy_admission(
        {
            "market": "KOSDAQ",
            "_analysis_section": "Top5",
            "expected_edge_score": -5.0,
            "prob_clean": 38.0,
            "decision_score": 92.0,
            "loss_risk_score": 78.0,
            "trend": "DOWN",
            "volume_ratio": 0.5,
            "day_change_pct": -5.0,
            "position": "Peak",
        },
        market="KOSDAQ",
        section="Top5",
    )

    assert admission["available"] is True
    assert admission["ranking_score_5d"] < 45.0
    assert admission["action_label_input"] == "realized_expectancy_risk"


def test_missing_calibration_returns_explicit_unavailable_reason():
    admission = build_realized_expectancy_admission({"market": "NASDAQ"}, market="NASDAQ", section="Top5")

    assert admission["available"] is False
    assert admission["unavailable_reason"] == "missing_calibration:NASDAQ:Top5"


def test_regime_theme_adjustment_is_applied_with_trace(monkeypatch):
    def fake_adjustment(_row):
        return {
            "version": "test",
            "prob_multiplier": 1.2,
            "return_multiplier": 1.2,
            "stop_risk_multiplier": 0.8,
            "confidence": 0.75,
            "warnings": [],
            "evidence": ["market_gate", "same_scan_theme"],
        }

    monkeypatch.setattr("modules.realized_expectancy_admission.build_regime_theme_adjustment", fake_adjustment)
    base_row = {
        "market": "KOSPI",
        "_analysis_section": "Top5",
        "expected_edge_score": 5.0,
        "prob_clean": 64.0,
        "decision_score": 82.0,
        "loss_risk_score": 34.0,
        "trend": "UP",
        "volume_ratio": 2.1,
        "day_change_pct": 2.0,
    }

    admission = build_realized_expectancy_admission(base_row, market="KOSPI", section="Top5")

    assert admission["3d_prob"] > admission["unadjusted_expectancy"]["3d_prob"]
    assert admission["avg_return_5d_pct"] > admission["unadjusted_expectancy"]["avg_return_5d_pct"]
    assert admission["stop_first_risk_pct"] < admission["unadjusted_expectancy"]["stop_first_risk_pct"]
    assert admission["regime_theme_adjustment"]["evidence"] == ["market_gate", "same_scan_theme"]
    assert admission["trace"]["regime_theme_effective_confidence"] == 0.75


def test_sparse_feature_rows_keep_rank_fallback_despite_regime_adjustment(monkeypatch):
    monkeypatch.setattr(
        "modules.realized_expectancy_admission.build_regime_theme_adjustment",
        lambda _row: {
            "version": "test",
            "prob_multiplier": 1.2,
            "return_multiplier": 1.2,
            "stop_risk_multiplier": 0.8,
            "confidence": 0.75,
            "warnings": [],
            "evidence": ["market_gate"],
        },
    )

    admission = build_realized_expectancy_admission(
        {"ticker": "005930.KS", "market": "KR", "_analysis_section_rank": 3},
        market="KR",
        section="Top5",
    )

    assert admission["ranking_score_5d"] == 97.0
    assert admission["trace"]["feature_evidence_count"] < 2


def test_kr_market_rows_are_normalized_from_ticker_suffix():
    admission = build_realized_expectancy_admission({"ticker": "005930.KS", "market": "KR"}, market="KR", section="Top5")

    assert admission["available"] is True
    assert admission["market"] == "KOSPI"


def test_sort_by_realized_expectancy_keeps_original_rows_but_changes_order():
    rows = [
        {
            "ticker": "A.KS",
            "market": "KOSPI",
            "_analysis_section": "Top5",
            "_analysis_section_rank": 1,
            "expected_edge_score": -5.0,
            "prob_clean": 35.0,
            "loss_risk_score": 80.0,
            "trend": "DOWN",
        },
        {
            "ticker": "B.KS",
            "market": "KOSPI",
            "_analysis_section": "Top5",
            "_analysis_section_rank": 2,
            "expected_edge_score": 7.0,
            "prob_clean": 68.0,
            "loss_risk_score": 25.0,
            "trend": "UP",
            "volume_ratio": 2.0,
        },
    ]
    enriched = [dict(row, realized_expectancy_admission=build_realized_expectancy_admission(row, market="KOSPI", section="Top5")) for row in rows]

    sorted_rows = sort_by_realized_expectancy(enriched, horizon=5)

    assert [row["ticker"] for row in sorted_rows] == ["B.KS", "A.KS"]
    assert [row["ticker"] for row in enriched] == ["A.KS", "B.KS"]


def test_validation_comparison_reports_old_vs_expectancy_metrics():
    report = compare_original_vs_expectancy_order(
        [
            {
                "ticker": "A.KS",
                "market": "KOSPI",
                "section": "Top5",
                "section_rank": 1,
                "expected_edge_score": -5.0,
                "prob_clean": 35.0,
                "loss_risk_score": 80.0,
                "trend": "DOWN",
                "return_3d_pct": -2.0,
                "return_5d_pct": -4.0,
                "stop_before_target_5d": True,
            },
            {
                "ticker": "B.KS",
                "market": "KOSPI",
                "section": "Top5",
                "section_rank": 2,
                "expected_edge_score": 8.0,
                "prob_clean": 70.0,
                "loss_risk_score": 20.0,
                "trend": "UP",
                "volume_ratio": 2.0,
                "return_3d_pct": 4.0,
                "return_5d_pct": 9.0,
                "stop_before_target_5d": False,
            },
        ],
        top_n=1,
    )

    assert report["original_order"]["tickers"] == ["A.KS"]
    assert report["expectancy_order"]["tickers"] == ["B.KS"]
    assert report["comparison_groups"] == 1
    assert report["original_order"]["return_5d"]["avg_pct"] == -4.0
    assert report["expectancy_order"]["return_5d"]["avg_pct"] == 9.0


def test_regime_theme_comparison_reports_unadjusted_vs_adjusted(monkeypatch):
    monkeypatch.setattr(
        "modules.realized_expectancy_admission.build_regime_theme_adjustment",
        lambda row: {
            "version": "test",
            "prob_multiplier": 1.2 if row.get("ticker") == "B.KS" else 0.85,
            "return_multiplier": 1.2 if row.get("ticker") == "B.KS" else 0.85,
            "stop_risk_multiplier": 0.8 if row.get("ticker") == "B.KS" else 1.2,
            "confidence": 0.75,
            "warnings": [],
            "evidence": ["market_gate", "same_scan_theme"],
        },
    )
    rows = [
        {
            "ticker": "A.KS",
            "market": "KOSPI",
            "section": "Top5",
            "section_rank": 1,
            "expected_edge_score": 2.0,
            "prob_clean": 64.0,
            "loss_risk_score": 34.0,
            "trend": "UP",
            "return_3d_pct": -1.0,
            "return_5d_pct": -2.0,
            "stop_before_target_5d": True,
        },
        {
            "ticker": "B.KS",
            "market": "KOSPI",
            "section": "Top5",
            "section_rank": 2,
            "expected_edge_score": 2.0,
            "prob_clean": 64.0,
            "loss_risk_score": 34.0,
            "trend": "UP",
            "return_3d_pct": 3.0,
            "return_5d_pct": 7.0,
            "stop_before_target_5d": False,
        },
    ]

    report = compare_unadjusted_vs_regime_theme_order(rows, top_n=1)

    assert report["unadjusted_order"]["tickers"] == ["A.KS"]
    assert report["regime_theme_order"]["tickers"] == ["B.KS"]
    assert report["regime_theme_order"]["regime_theme_applied_rows"] == 1
