"""§16 tail 사전탐지 관측 배선 회귀 (swing-main-clbb).

계약: tail_p는 관측 전용 — 플래그 OFF면 페이로드 불변, ON이어도 발행/사이징/랭킹
필드는 일절 건드리지 않는다. 스코어러 실패는 전부 fail-safe(필드 누락).
실데이터(px_long 1.2GB) 없이 배선만 검증하려고 스코어러는 스텁으로 대체한다.
"""
from __future__ import annotations

import json

import pytest

from multi_agent.tools import score_tail_p
from web.backend import services

PICK_KW = dict(entry=70000.0, prob=0.62, name="테스트종목", scan_date="2026-08-13", source="A")


def _row(monkeypatch, flag, scorer, thr=0.348):
    monkeypatch.setenv("AG_TAIL_P_OBS", flag)
    monkeypatch.setattr(score_tail_p, "tail_p_for_pick", scorer)
    monkeypatch.setattr(score_tail_p, "log_tail_p_obs", lambda row: None)
    monkeypatch.setattr(score_tail_p, "warn_threshold", lambda: thr)
    return services._pick_row("005930.KS", "KOSPI", "kospi_swing", **PICK_KW)


def test_flag_off_leaves_payload_untouched(monkeypatch):
    def _boom(*a, **k):  # 플래그 OFF면 스코어러는 호출조차 되지 않아야 한다
        raise AssertionError("scorer must not run while AG_TAIL_P_OBS=0")

    row = _row(monkeypatch, "0", _boom)
    assert "tail_p" not in row and "tail_warn" not in row


def test_flag_on_attaches_observation_fields_only(monkeypatch):
    off = _row(monkeypatch, "0", lambda *a, **k: None)
    on = _row(monkeypatch, "1", lambda *a, **k: 0.4321)
    assert on["tail_p"] == 0.4321 and on["tail_warn"] is True
    # 관측 필드 외 나머지 페이로드(사이징·랭킹·계약)는 완전 동일
    assert {k: v for k, v in on.items() if k not in ("tail_p", "tail_warn")} == off


def test_warn_fires_only_at_or_above_bundle_threshold(monkeypatch):
    below = _row(monkeypatch, "1", lambda *a, **k: 0.3479)
    at = _row(monkeypatch, "1", lambda *a, **k: 0.348)
    assert below["tail_p"] == 0.3479 and "tail_warn" not in below
    assert at["tail_warn"] is True


def test_warn_threshold_comes_from_trained_artifact(monkeypatch):
    """하드코딩 금지 — 경계는 학습 시 기록된 OOS q80이어야 한다 (재학습시 자동 추종)."""
    import os

    score_tail_p.warn_threshold.cache_clear()
    monkeypatch.delenv("AG_TAIL_P_WARN", raising=False)
    with open(os.path.join(score_tail_p.REPO, "models/tail_p/tail_p_meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    q80 = meta["validation"]["separation_top_quintile"]["oos_q80_tail_p"]
    assert score_tail_p.warn_threshold() == q80 == meta["serving"]["warn_threshold"]

    score_tail_p.warn_threshold.cache_clear()
    monkeypatch.setenv("AG_TAIL_P_WARN", "0.5")
    assert score_tail_p.warn_threshold() == 0.5
    score_tail_p.warn_threshold.cache_clear()


@pytest.mark.parametrize("scorer", [
    lambda *a, **k: None,                                   # 피처 부재/stale
    lambda *a, **k: (_ for _ in ()).throw(RuntimeError()),  # 번들 손상 등 예외
])
def test_scorer_failure_is_fail_safe(monkeypatch, scorer):
    row = _row(monkeypatch, "1", scorer)
    assert "tail_p" not in row and "tail_warn" not in row


def test_obs_sidecar_appends_and_dedupes(monkeypatch, tmp_path):
    fp = tmp_path / "tail_p_obs.jsonl"
    monkeypatch.setattr(score_tail_p, "OBS_FP", str(fp))
    monkeypatch.setattr(score_tail_p, "_obs_seen", set())
    rec = {"scan_date": "2026-08-13", "code": "005930", "lane": "kospi_swing", "tail_p": 0.4321}
    score_tail_p.log_tail_p_obs(rec)
    score_tail_p.log_tail_p_obs(dict(rec))                       # 웹 재조회 = 중복 억제
    score_tail_p.log_tail_p_obs({**rec, "lane": "kospi_intraday"})  # 다른 레인 = 별도 관측
    lines = [json.loads(x) for x in fp.read_text(encoding="utf-8").splitlines()]
    assert [x["lane"] for x in lines] == ["kospi_swing", "kospi_intraday"]
    assert lines[0]["tail_p"] == 0.4321 and lines[0]["logged_at"]
