"""Gemini 분석 폐기(2026-10-29, swing-main-wi1t) — 어떤 경로도 LLM 을 부르지 않고, 과거 캐시의 Gemini 판정도 노출하지 않는다."""
import json
import urllib.request

import pytest

from web.backend import scans
from web.backend import services as S

FACTS = {"code": "005930", "name": "삼성전자", "market": "KOSPI",
         "model": {"in_a": None, "in_b": None}, "features": {"ret_20d": 20.0},
         "flow": {"frgn_5d": 10}, "events": {"dart": [], "pead": None}, "regime": "하락"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("LLM/network call is retired")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setenv("GEMINI_API_KEY", "still-set-in-env")


def test_rule_verdict_ignores_gemini_key():
    v = S._rule_verdict(FACTS)
    assert v["source"] == "rule"
    assert "외국인 순매수" in v["text"] and "단기 과열" in v["text"] and "하락 레짐" in v["text"]


def test_cached_gemini_verdict_is_replaced_on_read(monkeypatch, tmp_path):
    monkeypatch.setattr(scans, "CACHE_DIR", str(tmp_path))
    d = tmp_path / "scan_1"
    d.mkdir()
    cached = dict(FACTS, verdict={"text": "LLM 문장", "source": "gemini-2.5-flash"})
    (d / "005930.json").write_text(json.dumps(cached, ensure_ascii=False))
    monkeypatch.setattr(S, "analyze", lambda code: pytest.fail("cache hit must not regenerate"))

    out = scans.scan_analyze("scan_1", "005930.KS")

    assert out["verdict"]["source"] == "rule"
    assert "LLM 문장" not in out["verdict"]["text"]
    assert out["features"] == FACTS["features"]  # 스냅샷 사실은 그대로
