import os

from modules.horizon_policy import horizon_days_from_return_col, resolve_horizon_policy


def test_kr_swing_horizon_policy_is_explicit():
    # 2026-05-08 (swing-main-4lm): KOSPI SWING horizon 3d→5d. horizon
    # 진단에서 KOSPI SWING 운영 분포가 5d/7d에서 75%+ win, 3d 학습 OOS auc
    # 0.485 — target_horizon이 짧아 학습 가능 신호를 못 만듦.
    assert resolve_horizon_policy("KOSPI", "SWING")["return_col"] == "return_5d_pct"
    assert resolve_horizon_policy("KOSPI", "SWING")["horizon_days"] == 5
    assert resolve_horizon_policy("KOSDAQ", "SWING")["return_col"] == "return_5d_pct"
    assert resolve_horizon_policy("KOSDAQ", "SWING")["horizon_days"] == 5


def test_retrain_segments_use_horizon_policy():
    # 2026-05-08 (swing-main-01i): 단일 segment 4개 모델은 prod 정렬 효과
    # 0/-14pp로 무용. AG_PHASE25_DISABLE_SEGMENTS 토글로 SEGMENTS에서 제외 (기본
    # 1=disabled). rollback 검증을 위해 토글 0으로 강제 후 재로딩.
    os.environ["AG_PHASE25_DISABLE_SEGMENTS"] = "0"
    import importlib
    import retrain_ml
    importlib.reload(retrain_ml)
    try:
        by_name = {spec.name: spec for spec in retrain_ml.SEGMENTS}
        assert "phase25_kospi_swing" in by_name, "rollback should re-enable single-segment specs"
        assert by_name["phase25_kospi_swing"].return_col == "return_5d_pct"
        assert by_name["phase25_kosdaq_swing"].return_col == "return_5d_pct"
        assert horizon_days_from_return_col(by_name["phase25_kosdaq_swing"].return_col) == 5
    finally:
        os.environ["AG_PHASE25_DISABLE_SEGMENTS"] = "1"
        importlib.reload(retrain_ml)


def test_retrain_segments_default_disables_single_segments():
    # 기본 (AG_PHASE25_DISABLE_SEGMENTS=1) 에서 단일 segment 4개 제외 확인.
    os.environ.pop("AG_PHASE25_DISABLE_SEGMENTS", None)
    import importlib
    import retrain_ml
    importlib.reload(retrain_ml)
    names = {spec.name for spec in retrain_ml.SEGMENTS}
    assert "phase25_global" in names
    for disabled in (
        "phase25_kospi_swing",
        "phase25_kosdaq_swing",
        "phase25_kospi_intraday",
        "phase25_kosdaq_intraday",
    ):
        assert disabled not in names, f"{disabled} must be disabled by default"
