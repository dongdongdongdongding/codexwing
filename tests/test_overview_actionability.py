"""개요 화면이 '살 수 있는 픽'을 말하는지 고정한다.

전부 실제 결함에서 나왔다(2026-08-20 실측):
- 픽 10건이 전부 차단 상태인데 헤더는 "A 10 · B 0" 이라 열 개가 대기 중인 것처럼 보였다.
- 만료 1일 지난 08-18 장중 픽이 신선한 08-20 스윙 픽들보다 위에 있었다.
- 분봉 신선도를 2,614개 캐시 중 `sorted(glob)[0]` 한 종목으로 판정해 08-20 데이터가 있는데
  08-19 로 나왔다.
"""
import web.backend.services as sv


def _pick(code, prob, **kw):
    row = {"code": code, "lane": kw.pop("lane", "kospi_swing"), "signal_class": "A", "prob": prob}
    row.update(kw)
    return row


def test_blockers_name_every_reason_a_pick_cannot_be_taken():
    p = _pick("A", 90, expired=True, stale_days=3, stream_excluded=True,
              operator_verdict="KILL", attainability="LIMIT_UP")
    b = sv.pick_blockers(p)
    assert "만료 3일" in b
    assert "상한가 체결불가" in b
    assert "관측전용" in b
    assert "폐기선 아래" in b


def test_a_clean_pick_has_no_blockers():
    assert sv.pick_blockers(_pick("A", 70)) == []


def test_frequency_shortfall_counts_as_a_blocker():
    p = _pick("A", 70, lane_frequency={"frequency_ok": False, "median_gap": 9})
    assert "발화 부족" in sv.pick_blockers(p)


def test_an_expired_pick_does_not_outrank_a_clean_one(monkeypatch):
    """확률이 높아도 살 수 없으면 먼저 오지 않는다 — 이게 원래 결함이다."""
    stale = _pick("STALE", 95, expired=True, stale_days=1, lane="kospi_intraday")
    clean = _pick("CLEAN", 60)
    monkeypatch.setattr(sv, "picks", lambda: [stale, clean])
    monkeypatch.setattr(sv, "freshness", lambda: {"_lag": {}})
    top = sv.overview(top=2)["top_picks"]
    assert [p["code"] for p in top] == ["CLEAN", "STALE"]


def test_blocked_picks_are_shown_not_hidden(monkeypatch):
    """차단된 픽을 빼면 왜 없는지 알 수 없다. 순서만 내리고 그대로 싣는다."""
    stale = _pick("STALE", 95, expired=True, stale_days=1)
    monkeypatch.setattr(sv, "picks", lambda: [stale])
    monkeypatch.setattr(sv, "freshness", lambda: {"_lag": {}})
    ov = sv.overview(top=6)
    assert [p["code"] for p in ov["top_picks"]] == ["STALE"]
    assert ov["top_picks"][0]["blockers"] == ["만료 1일"]


def test_counts_separate_actionable_from_total(monkeypatch):
    rows = [_pick("A", 90, operator_verdict="KILL"), _pick("B", 80), _pick("C", 70, stream_excluded=True)]
    monkeypatch.setattr(sv, "picks", lambda: rows)
    monkeypatch.setattr(sv, "freshness", lambda: {"_lag": {}})
    c = sv.overview()["counts"]
    assert c["A"] == 3, "총 건수는 그대로 유지한다"
    assert c["actionable"] == 1
    assert c["blocked"] == 2


def test_all_blocked_reports_zero_actionable(monkeypatch):
    """오늘의 실제 상태다. 0을 0이라고 말해야 한다."""
    rows = [_pick(str(i), 90 - i, operator_verdict="KILL") for i in range(10)]
    monkeypatch.setattr(sv, "picks", lambda: rows)
    monkeypatch.setattr(sv, "freshness", lambda: {"_lag": {}})
    c = sv.overview()["counts"]
    assert c["actionable"] == 0 and c["blocked"] == 10


def test_a_more_blocked_pick_ranks_below_a_less_blocked_one(monkeypatch):
    """전부 차단인 날에는 '차단 여부'만으로 갈리지 않는다 — 걸린 개수까지 센다.
    실측(2026-08-20): 10건이 전부 차단이라, 만료까지 겹친 08-18 장중 픽이
    관측전용뿐인 08-20 스윙 픽 위에 남아 있었다."""
    worse = _pick("WORSE", 77.1, expired=True, stale_days=1,
                  stream_excluded=True, operator_verdict="KILL", lane="kospi_intraday")
    better = _pick("BETTER", 74.7, stream_excluded=True, operator_verdict="KILL")
    monkeypatch.setattr(sv, "picks", lambda: [worse, better])
    monkeypatch.setattr(sv, "freshness", lambda: {"_lag": {}})
    top = sv.overview(top=2)["top_picks"]
    assert [p["code"] for p in top] == ["BETTER", "WORSE"], "확률이 높아도 더 많이 막힌 픽이 아래다"
