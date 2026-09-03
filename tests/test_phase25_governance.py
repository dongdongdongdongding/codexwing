from modules.phase25_governance import (
    OOS_VALIDATE_MIN_PICKS,
    phase25_oos_validates,
    phase25_signal_direction,
    phase25_weak_oos_reasons,
)


OK = dict(oos_auc=0.56, oos_win_rate_pct=72.0, oos_avg_return_pct=5.2, oos_n=120)


def test_phase25_oos_validation_requires_all_release_metrics():
    assert phase25_oos_validates(**OK) is True
    assert phase25_oos_validates(**{**OK, "oos_win_rate_pct": 69.9}) is False
    assert phase25_oos_validates(**{**OK, "oos_avg_return_pct": 4.9}) is False


def test_promotion_requires_a_denominator():
    """승격은 `uncertain` 을 `normal` 로 올리는 문이다. 분모 없이 승률만 보면
    픽 19건짜리 78% 가 통과한다 — 2026-09-03 이전이 정확히 그 상태였다."""
    assert phase25_oos_validates(**{**OK, "oos_n": None}) is False
    assert phase25_oos_validates(**{**OK, "oos_n": OOS_VALIDATE_MIN_PICKS - 1}) is False
    assert phase25_oos_validates(**{**OK, "oos_n": OOS_VALIDATE_MIN_PICKS}) is True


def test_phase25_weak_oos_reasons_are_explicit():
    assert phase25_weak_oos_reasons(
        oos_auc=0.517,
        oos_win_rate_pct=39.6825,
        oos_avg_return_pct=-1.8904,
        oos_n=200,
        signal_direction="normal",
    ) == [
        "oos_win=39.7%<60.0%",
        "oos_avg=-1.89%<0.0%",
    ]


def test_absent_metadata_is_a_reason_not_a_pass():
    """2026-09-03 회귀 방지. 값이 없으면 판정을 **보류**한다.

    이전에는 `None` 이 들어오면 각 검사를 건너뛰어 사유가 0건이 됐고, 그래서
    메타데이터가 통째로 없는 번들이 조용히 통과했다 — 실제로 서빙되던 두 번들이
    넉 달간 그 상태였다(FINDING_2026-09-03_serving_models_stale.md).
    """
    reasons = phase25_weak_oos_reasons(
        oos_auc=None, oos_win_rate_pct=None, oos_avg_return_pct=None, oos_n=None
    )
    assert reasons, "메타데이터 부재가 사유 0건이면 fail-open 이다"
    assert any(r.startswith("oos_meta_missing:") for r in reasons)
    assert "signal_direction" in reasons[0]


def test_rollback_switch_restores_the_old_permissive_behavior(monkeypatch):
    """되돌릴 수 있어야 한다 — 다만 되돌리면 판정 불가 모델이 조용히 나간다."""
    monkeypatch.setenv("AG_PHASE25_REQUIRE_OOS_META", "0")
    assert phase25_weak_oos_reasons(
        oos_auc=None, oos_win_rate_pct=None, oos_avg_return_pct=None
    ) == []


def test_direction_ruler_matches_the_retrain_rule():
    """세 트레이너가 같은 자를 써야 한다. 값은 retrain_ml.py 주석이 인용한 실제 사례다:
    2026-04-26 KOSDAQ INTRADAY raw_auc 0.274 / cv 0.579 → 이것을 `normal` 로 읽어
    4월 726행을 AVOID 로 막았고 forward 는 win 78% 로 정확히 inverted 였다."""
    assert phase25_signal_direction(0.274, 0.579) == "invert"
    assert phase25_signal_direction(0.60, 0.62) == "normal"
    assert phase25_signal_direction(0.53, 0.60) == "uncertain"
    assert phase25_signal_direction(0.62, None) == "normal"
    assert phase25_signal_direction(None, 0.62) == "uncertain"
