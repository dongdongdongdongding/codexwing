from ui.view_chrome import coerce_text_rows


def test_coerce_text_rows_handles_dict_list_and_scalar_values():
    assert coerce_text_rows({"금리": "하락", "환율": ""}) == ["금리: 하락", "환율"]
    assert coerce_text_rows([{"label": "반도체", "value": "강세"}, {"summary": "수급 개선"}, "거래대금 증가"]) == [
        "반도체: 강세",
        "수급 개선",
        "거래대금 증가",
    ]
    assert coerce_text_rows("단기 과열", limit=1) == ["단기 과열"]


def test_coerce_text_rows_respects_limit():
    assert coerce_text_rows(["a", "b", "c"], limit=2) == ["a", "b"]
