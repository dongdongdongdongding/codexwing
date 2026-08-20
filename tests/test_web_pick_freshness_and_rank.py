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
    rows = [
        {"lane": "kosdaq_swing", "scan_date": "2026-08-20", "prob": 80.0},
        {"lane": "kosdaq_swing", "scan_date": "2026-08-20", "prob": 91.0},
        {"lane": "kosdaq_swing", "scan_date": "2026-08-20", "prob": 70.0},
    ]
    S._attach_day_rank(rows)
    top = [r for r in rows if r.get("is_top1")]
    assert len(top) == 1 and top[0]["prob"] == 91.0, "확률 최댓값이 1순위여야 한다"
    assert "1순위" in top[0]["rank_note"]
    others = [r for r in rows if not r.get("is_top1")]
    assert all("1순위에만" in r["rank_note"] for r in others), "엣지가 어디 있는지 말해줘야 한다"
    assert {r["rank_in_day"] for r in rows} == {1, 2, 3}
    assert all(r["picks_in_day"] == 3 for r in rows)


def test_rank_is_scoped_to_lane_and_day():
    """레인이나 날짜가 다르면 각자 1순위가 있어야 한다 — 섞으면 순위가 거짓이 된다."""
    rows = [
        {"lane": "kospi_swing", "scan_date": "2026-08-20", "prob": 60.0},
        {"lane": "kosdaq_swing", "scan_date": "2026-08-20", "prob": 50.0},
        {"lane": "kospi_swing", "scan_date": "2026-08-19", "prob": 40.0},
    ]
    S._attach_day_rank(rows)
    assert all(r["is_top1"] for r in rows), "각 (레인,날짜) 그룹마다 1순위가 하나씩"
    assert all(r["picks_in_day"] == 1 for r in rows)


def test_rank_is_attached_on_the_merged_list_not_per_path():
    """DB 경로와 원장 경로 양쪽을 지난 뒤에 붙어야 한다.

    한쪽 경로에만 두면 화면이 데이터 출처에 따라 달라진다 — 실제로 그랬다:
    KR 레인은 DB 경로라 순위가 없고 나스닥만 원장 경로라 순위가 붙었다.
    """
    import inspect
    src = inspect.getsource(S.a_picks)
    assert "_attach_day_rank(rows)" in src, "최종 목록에 붙여야 한다"
    assert "_attach_day_rank" not in inspect.getsource(S._a_picks_ledger), "경로별 사본 금지"
    assert "_attach_day_rank" not in inspect.getsource(S._pick_row), "경로별 사본 금지"


def test_rank_absent_does_not_invent_a_label():
    """확률이 없으면 조용히 1순위라고 하지 않는다 — 없는 근거를 만들면 안 된다."""
    rows = [{"lane": "kospi_swing", "scan_date": "2026-08-20", "prob": None},
            {"lane": "kospi_swing", "scan_date": "2026-08-20", "prob": None}]
    S._attach_day_rank(rows)
    assert all("is_top1" not in r and "rank_note" not in r for r in rows)


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


def test_ledger_reader_accepts_the_symbol_key():
    """원장마다 종목 키가 다르다 — 나스닥은 `symbol` 이다.

    ticker 만 물으면 code 가 빈 문자열이 되어 이름도 차트도 안 붙는다.
    라이브에서 실제로 나스닥 픽의 종목명이 비어 있었다.
    """
    import inspect
    src = inspect.getsource(S._a_picks_ledger)
    assert 'r.get("ticker") or r.get("symbol")' in src
    assert "if not code:" in src, "코드가 없으면 픽을 만들지 않아야 한다"
