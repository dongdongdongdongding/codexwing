from ui.intelligence_view import (
    build_intelligence_catalysts,
    build_intelligence_highlights,
    build_next_session_theme_line,
    intelligence_signal_line,
    intelligence_tactical_line,
    theme_name_line,
    theme_tone,
)


def test_theme_and_signal_helpers_prioritize_structured_themes():
    intel = {
        "beneficiary_themes": [{"theme_name": "AI반도체"}, {"theme_name": "전력기기"}],
        "headwind_themes": [{"theme_name": "2차전지"}],
    }

    assert theme_tone("BENEFICIARY") == ("good", "수혜")
    assert theme_tone("HEADWIND") == ("risk", "역풍")
    assert theme_name_line(intel["beneficiary_themes"]) == "AI반도체, 전력기기"
    assert intelligence_signal_line(intel, kind="beneficiary") == "AI반도체, 전력기기"
    assert intelligence_signal_line(intel, kind="headwind") == "2차전지"


def test_intelligence_highlights_include_risk_and_macro_rows():
    intel = {
        "key_insight": "선별 장세",
        "beneficiary_themes": [{"theme_name": "조선"}],
        "risk_flags": ["환율 변동"],
        "macro_drivers": [{"signal": "BULLISH", "market_impact": 1, "category": "금리", "description": "금리 안정"}],
    }

    highlights = build_intelligence_highlights(intel)

    assert ("핵심", "선별 장세") in highlights
    assert ("수혜", "강하게 받쳐주는 테마는 조선 입니다.") in highlights
    assert any(label == "리스크" and "환율 변동" in text for label, text in highlights)
    assert intelligence_tactical_line(intel).startswith("BULLISH")


def test_next_session_theme_line_scores_distribution_rows():
    theme_summary = {
        "rows": [
            {"theme_name": "조선", "avg_day_return_pct": 0.2, "strength_score": 30, "positive_ratio": 0.6},
            {"theme_name": "반도체", "avg_day_return_pct": 1.5, "strength_score": 20, "positive_ratio": 0.7},
        ]
    }

    assert build_next_session_theme_line(theme_summary, {}) == "반도체, 조선"


def test_build_intelligence_catalysts_combines_theme_disclosure_and_macro():
    intel = {
        "disclosure_events": [{"company": "A사", "label": "수주", "report_name": "단일판매"}],
        "macro_drivers": [{"description": "미장 반도체 강세"}],
    }
    theme_summary = {
        "rows": [
            {
                "theme_name": "반도체",
                "avg_day_return_pct": 2.1,
                "positive_ratio": 0.75,
                "industry_samples": ["장비"],
            }
        ]
    }

    catalysts = build_intelligence_catalysts(intel, theme_summary)

    assert catalysts[0] == "반도체: 평균 +2.10%, 양봉 비중 75%, 대표 업종 장비"
    assert "A사: 수주 이벤트 반영 (단일판매)" in catalysts
    assert "미장 반도체 강세" in catalysts
