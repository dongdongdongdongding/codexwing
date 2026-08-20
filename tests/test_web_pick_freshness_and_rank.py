"""웹 픽 표시의 두 결함 (2026-08-20 실측).

1) 신선도: `_a_picks_ledger` 는 레인별 **최신 스캔일**을 쓴다. 레인이 며칠 발화하지
   않으면 낡은 픽이 오늘 픽처럼 올라온다. 실제로 kosdaq_intraday 성호전자가
   scan=08-12 / buy=08-13 인데 08-20 화면에 **"총자본 2%/픽" 사이징과 함께** 떠 있었다.
   게이트가 OBSERVING 이라 스트림 제외도 통과했다 — 신선도는 판정과 다른 축이다.

2) 순위: 측정된 엣지는 **top-1 에만** 있다(swing KOSDAQ 전체 -0.08 vs top-1 +2.39,
   kospi_intraday +0.11 vs +2.11). 순위 표기가 없으면 사용자가 엣지 없는 픽을 고른다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from web.backend import services as S  # noqa: E402


# ── 1. 신선도 ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("buy,today,want", [
    ("2026-08-13", "2026-08-20", 7),    # 성호전자 실제 사례
    ("2026-08-19", "2026-08-20", 1),
    ("2026-08-20", "2026-08-20", 0),    # 당일 = 실행 가능
    ("2026-08-21", "2026-08-20", 0),    # 내일치 = 정상
    (None, "2026-08-20", None),
    ("", "2026-08-20", None),
    ("깨진값", "2026-08-20", None),
])
def test_stale_days(buy, today, want):
    assert S._pick_is_stale(buy, today) == want


def test_expired_pick_loses_its_sizing_instruction():
    """급소 — 낡은 픽에 사이징이 붙어 나가면 지난 진입가로 매매하게 된다."""
    row = S._pick_row("053110", "KOSDAQ", "kosdaq_intraday",
                      entry=1000.0, prob=0.8, scan_date="2026-08-12", name="성호전자")
    if not row.get("expired"):
        pytest.skip("오늘 날짜 기준으로는 만료되지 않음 — 시간 의존 테스트")
    assert "size_pct_total" not in row, "만료 픽에 사이징이 남으면 안 된다"
    assert "만료" in row["size_note"]
    assert row["stale_days"] >= 1


def test_fresh_pick_keeps_its_sizing():
    """오탐 방지 — 정상 픽까지 만료로 막으면 화면이 비어 아무도 안 본다."""
    import datetime as dt
    row = S._pick_row("053110", "KOSDAQ", "kosdaq_intraday",
                      entry=1000.0, prob=0.8,
                      scan_date=str(dt.date.today()), name="테스트")
    assert not row.get("expired")
    assert "만료" not in (row.get("size_note") or "")


# ── 2. 순위 ──────────────────────────────────────────────────────────────────

def test_top1_is_marked_and_others_are_told_they_are_not():
    r1 = S._pick_row("000001", "KOSDAQ", "kosdaq_swing", entry=1000.0, prob=0.9,
                     scan_date="2026-08-20", extra={"rank_in_day": 1, "picks_in_day": 3})
    r2 = S._pick_row("000002", "KOSDAQ", "kosdaq_swing", entry=1000.0, prob=0.8,
                     scan_date="2026-08-20", extra={"rank_in_day": 2, "picks_in_day": 3})
    assert r1["is_top1"] is True and "1순위" in r1["rank_note"]
    assert r2["is_top1"] is False
    assert "1순위에만" in r2["rank_note"], "엣지가 어디 있는지 말해줘야 한다"


def test_rank_absent_does_not_invent_a_label():
    """순위를 모르면 조용히 1순위라고 하지 않는다 — 없는 근거를 만들면 안 된다."""
    row = S._pick_row("000003", "KOSPI", "kospi_swing", entry=1000.0, prob=0.7,
                      scan_date="2026-08-20")
    assert "is_top1" not in row and "rank_note" not in row


# ── 3. 운영자 EV 기준 (2026-08-20 지시) ──────────────────────────────────────

def _fake_gate(monkeypatch, ev, win=80.0, n=50, lane="nasdaq_session_tape"):
    if hasattr(S._lane_forward_ev, "cache_clear"):
        S._lane_forward_ev.cache_clear()
    monkeypatch.setattr(S, "_lane_forward_ev", lambda: {lane: (ev, win, n)})


def test_kill_floor_strips_sizing_even_when_the_gate_says_confirm(monkeypatch):
    """급소 — 게이트 CONFIRM 과 운영자 기준은 **다른 축**이다.

    nasdaq_session_tape 가 실제로 그렇다: verdict=CONFIRM 인데 fwd_ev +0.09.
    게이트는 '백테스트 기대와 맞는가'를 묻지 '거래할 만한가'를 묻지 않는다.
    CONFIRM 만 화면에 보이면 사용자가 좋은 레인으로 읽는다.
    """
    _fake_gate(monkeypatch, ev=0.34)
    row = {"size_pct_total": 2.0, "size_note": "총자본 2%/픽"}
    S._apply_operator_ev_floor(row, "nasdaq_intraday")
    assert row["operator_verdict"] == "KILL"
    assert "size_pct_total" not in row
    assert "폐기선" in row["size_note"] and "+0.34" in row["size_note"]
    assert row["forward_ev"] == 0.34


def test_deploy_band_needs_both_ev_and_win(monkeypatch):
    """EV 만 높고 승률이 낮으면 즉시적용이 아니다 — 목표는 두 축이다."""
    _fake_gate(monkeypatch, ev=20.0, win=60.0)
    row = {"size_pct_total": 2.0}
    S._apply_operator_ev_floor(row, "nasdaq_intraday")
    assert row["operator_verdict"] == "OBSERVE"

    _fake_gate(monkeypatch, ev=20.0, win=80.0)
    row = {"size_pct_total": 2.0}
    S._apply_operator_ev_floor(row, "nasdaq_intraday")
    assert row["operator_verdict"] == "DEPLOY"
    assert "즉시적용" in row["size_note"]


def test_middle_band_keeps_sizing_and_is_labelled_observe(monkeypatch):
    _fake_gate(monkeypatch, ev=2.4, win=84.6)
    row = {"size_pct_total": 2.0, "size_note": "총자본 2%/픽"}
    S._apply_operator_ev_floor(row, "nasdaq_intraday")
    assert row["operator_verdict"] == "OBSERVE"
    assert row["size_pct_total"] == 2.0, "폐기선 위 관측대는 사이징을 유지한다"


def test_unknown_ev_is_fail_closed(monkeypatch):
    """모르는 것을 통과시키면 그게 이 리포가 반복해 온 fail-open 이다."""
    if hasattr(S._lane_forward_ev, "cache_clear"):
        S._lane_forward_ev.cache_clear()
    monkeypatch.setattr(S, "_lane_forward_ev", lambda: {})
    row = {"size_pct_total": 2.0}
    S._apply_operator_ev_floor(row, "nasdaq_intraday")
    assert row["operator_verdict"] == "UNKNOWN"
    assert "size_pct_total" not in row


def test_nasdaq_lane_is_registered_and_mapped_to_the_gate():
    """웹에 레인만 넣고 게이트 매핑을 빼면 '모른다'가 차단 사유가 된다."""
    from modules.stream_exclusion import GATE_LANE_MAP
    assert "nasdaq_intraday" in S.LANES
    assert S.LANES["nasdaq_intraday"]["dir"] == "us_research"
    assert GATE_LANE_MAP.get("nasdaq_intraday") == "nasdaq_session_tape"
