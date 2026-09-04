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


# --- 2026-09-04: 리프트 기준 (운영자 결정) ---

SWING = dict(oos_auc=0.5018, oos_win_rate_pct=42.31, oos_avg_return_pct=-2.12, oos_n=527,
             signal_direction="normal",
             oos_baseline_win_rate_pct=34.7, oos_baseline_avg_return_pct=-4.33)
INTRADAY = dict(oos_auc=0.4732, oos_win_rate_pct=37.61, oos_avg_return_pct=-0.892, oos_n=2079,
                signal_direction="normal",
                oos_baseline_win_rate_pct=37.61, oos_baseline_avg_return_pct=-0.88)


def test_lift_separates_a_discriminating_model_from_a_baseline_clone():
    """절대 임계값만 보면 둘 다 탈락해 구분이 안 된다. 아래는 실측값이다(2026-09-03, 70/15/15).

    SWING 은 기준선 −4.33% 장에서 −2.12% 를 냈다 — 절대로는 음수지만 리프트 +2.21pp 이고
    승률 리프트 +7.6pp 은 1SE(2.2pp)의 세 배가 넘는다.
    INTRADAY 는 기준선을 소수점까지 그대로 복제한다.
    """
    assert phase25_weak_oos_reasons(**SWING) == []
    reasons = phase25_weak_oos_reasons(**INTRADAY)
    assert any("oos_lift_win" in r for r in reasons)
    assert any("oos_lift_ret" in r for r in reasons)


def test_lift_floor_scales_with_the_sample():
    """0 초과만 요구하면 잡음이 절반은 통과한다. 하한을 표본에서 유도한다."""
    small = {**SWING, "oos_n": 100, "oos_win_rate_pct": 34.7 + 2.0}   # 1SE=5.0pp → 미달
    big = {**SWING, "oos_n": 10000, "oos_win_rate_pct": 34.7 + 2.0}   # 1SE=0.5pp → 통과
    assert any("oos_lift_win" in r for r in phase25_weak_oos_reasons(**small))
    assert phase25_weak_oos_reasons(**big) == []


def test_below_random_is_broken_regardless_of_lift():
    """무작위 미만은 기준선과 무관하게 고장이다."""
    assert any(r.startswith("oos_auc=") for r in phase25_weak_oos_reasons(**{**SWING, "oos_auc": 0.42}))


def test_missing_baseline_falls_back_to_the_absolute_rule():
    """리프트를 못 재면 **느슨해지면 안 된다** — 옛 절대 기준으로 떨어진다."""
    no_base = {k: v for k, v in SWING.items() if not k.startswith("oos_baseline")}
    assert phase25_weak_oos_reasons(**no_base) == [
        "oos_win=42.3%<60.0%",
        "oos_avg=-2.12%<0.0%",
    ]
