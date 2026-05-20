from modules.phase25_governance import phase25_oos_validates, phase25_weak_oos_reasons


def test_phase25_oos_validation_requires_all_release_metrics():
    assert phase25_oos_validates(oos_auc=0.56, oos_win_rate_pct=72.0, oos_avg_return_pct=5.2) is True
    assert phase25_oos_validates(oos_auc=0.56, oos_win_rate_pct=69.9, oos_avg_return_pct=5.2) is False
    assert phase25_oos_validates(oos_auc=0.56, oos_win_rate_pct=72.0, oos_avg_return_pct=4.9) is False


def test_phase25_weak_oos_reasons_are_explicit():
    assert phase25_weak_oos_reasons(
        oos_auc=0.517,
        oos_win_rate_pct=39.6825,
        oos_avg_return_pct=-1.8904,
    ) == [
        "oos_win=39.7%<60.0%",
        "oos_avg=-1.89%<0.0%",
    ]
