import pandas as pd

import retrain_ml


def test_archive_derivation_adds_band_and_role_onehots():
    df = pd.DataFrame(
        [
            {
                "ticker": "005930.KS",
                "market": "KOSPI",
                "market_type": "KR",
                "scan_mode": "SWING",
                "strategy_family": "KR_CORE",
                "decision_bucket": "picked",
                "entry_reference_price": 12.5,
                "price_band": "7_15",
                "marcap_band": 3,
                "kr_universe_role": "CORE_TREND",
            },
            {
                "ticker": "123456.KQ",
                "market": "KOSDAQ",
                "market_type": "KR",
                "scan_mode": "SWING",
                "strategy_family": "KR_CORE",
                "decision_bucket": "watchlist",
                "entry_reference_price": 5.0,
                "price_band": "sub_7",
                "marcap_band": 0,
                "kr_universe_role": "EXPLOSIVE_LEADER",
            },
        ]
    )

    out = retrain_ml._derive_features_from_archive(df)

    assert out.loc[0, "price_7_15"] == 1
    assert out.loc[0, "marcap_large"] == 1
    assert out.loc[0, "role_core_trend"] == 1
    assert out.loc[0, "role_explosive_leader"] == 0

    assert out.loc[1, "is_sub7"] == 1
    assert out.loc[1, "marcap_micro"] == 1
    assert out.loc[1, "role_explosive_leader"] == 1


def test_new_band_role_columns_are_model_features():
    for col in [
        "marcap_micro",
        "marcap_small",
        "marcap_mid",
        "marcap_large",
        "marcap_mega",
        "role_core_trend",
        "role_explosive_leader",
        "role_transitional",
        "role_reject_risk",
    ]:
        assert col in retrain_ml.FEATURE_COLS
