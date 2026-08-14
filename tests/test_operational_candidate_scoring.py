import pytest

from modules import operational_candidate_scoring as ocs
from modules.operational_candidate_scoring import (
    adjust_return_for_buy_premium,
    attach_operational_candidate_score,
    build_operational_candidate_score,
)

# 공식 밸류체인 마스터(runtime_state/long_term/kis_ticker_valuechain/master.json)는
# .gitignore 대상 런타임 산출물이라 메인 체크아웃에만 있다. 실물에 의존하면 theme_valuechain
# 축이 환경마다 달라져(메인 >60 / 새 클론 56.0) 클론·워커 워크트리에서 항상 깨진다.
# 축의 의도(공식 밸류체인 검증 엣지가 있으면 테마축이 올라간다)를 고정값으로 못 박는다.
_PINNED_VALUECHAIN = {"005930.KS": {"verified_edge_count": 2}}


@pytest.fixture(autouse=True)
def _pin_valuechain_profiles(monkeypatch):
    monkeypatch.setattr(ocs, "_valuechain_profiles", lambda: dict(_PINNED_VALUECHAIN))


def test_adjust_return_for_buy_premium_uses_entry_price_ratio():
    assert adjust_return_for_buy_premium(10.0, 2.0) == 7.843137
    assert adjust_return_for_buy_premium(-5.0, 2.0) == -6.862745


def test_chart_only_candidate_is_observation_not_operable():
    row = {
        "ticker": "123456.KQ",
        "market": "KOSDAQ",
        "trend": "UP",
        "position": "Rising",
        "tech_score": 90,
        "alpha_score": 88,
        "volume_ratio": 3.0,
        "market_gate": "GREEN",
        "primary_theme": "unclassified",
    }

    score = build_operational_candidate_score(row)

    assert score["axes"]["chart"] >= 80
    assert score["chart_only"] is True
    assert score["action_level"] == "OBSERVE_CHART_ONLY"


def test_multi_axis_candidate_is_operable_with_non_chart_support():
    row = {
        "ticker": "005930.KS",
        "market": "KOSPI",
        "trend": "UP",
        "position": "Rising",
        "tech_score": 82,
        "alpha_score": 80,
        "volume_ratio": 1.8,
        "whale_score": 74,
        "foreigner_1d": 10_000_000,
        "institution_1d": 15_000_000,
        "market_gate": "GREEN",
        "regime_breadth_pct": 64,
        "primary_theme": "반도체",
        "theme_context": {"primary_theme": "반도체", "theme_strength_score": 76, "theme_direction": "BENEFICIARY"},
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
    }

    row = attach_operational_candidate_score(row)

    assert row["chart_only_candidate"] is False
    assert row["operational_action_level"] == "OPERABLE"
    assert row["operational_score_axes"]["axes"]["flow"] > 60
    assert row["operational_score_axes"]["axes"]["theme_valuechain"] > 60
