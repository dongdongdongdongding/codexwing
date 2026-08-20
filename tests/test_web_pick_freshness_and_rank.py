"""웹 픽 표시의 두 결함 (2026-08-20 실측).

1) 신선도: `_a_picks_ledger` 는 레인별 **최신 스캔일**을 쓴다. 레인이 며칠 발화하지
   않으면 낡은 픽이 오늘 픽처럼 올라온다. 실제로 kosdaq_intraday 성호전자가
   scan=08-12 / buy=08-13 인데 08-20 화면에 **"총자본 2%/픽" 사이징과 함께** 떠 있었다.
   게이트가 OBSERVING 이라 스트림 제외도 통과했다 — 신선도는 판정과 다른 축이다.

2) 순위: 측정된 엣지는 **top-1 에만** 있다(swing KOSDAQ 전체 -0.08 vs top-1 +2.39,
   kospi_intraday +0.11 vs +2.11). 순위 표기가 없으면 사용자가 엣지 없는 픽을 고른다.
"""
from __future__ import annotations

import json
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
    S._apply_operator_ev_floor(row, "nasdaq_swing")
    assert row["operator_verdict"] == "KILL"
    assert "size_pct_total" not in row
    assert "폐기선" in row["size_note"] and "+0.34" in row["size_note"]
    assert row["forward_ev"] == 0.34


def test_deploy_band_needs_both_ev_and_win(monkeypatch):
    """EV 만 높고 승률이 낮으면 즉시적용이 아니다 — 목표는 두 축이다."""
    _fake_gate(monkeypatch, ev=20.0, win=60.0)
    row = {"size_pct_total": 2.0}
    S._apply_operator_ev_floor(row, "nasdaq_swing")
    assert row["operator_verdict"] == "OBSERVE"

    _fake_gate(monkeypatch, ev=20.0, win=80.0)
    row = {"size_pct_total": 2.0}
    S._apply_operator_ev_floor(row, "nasdaq_swing")
    assert row["operator_verdict"] == "DEPLOY"
    assert "즉시적용" in row["size_note"]


def test_middle_band_keeps_sizing_and_is_labelled_observe(monkeypatch):
    _fake_gate(monkeypatch, ev=2.4, win=84.6)
    row = {"size_pct_total": 2.0, "size_note": "총자본 2%/픽"}
    S._apply_operator_ev_floor(row, "nasdaq_swing")
    assert row["operator_verdict"] == "OBSERVE"
    assert row["size_pct_total"] == 2.0, "폐기선 위 관측대는 사이징을 유지한다"


def test_unknown_ev_is_fail_closed(monkeypatch):
    """모르는 것을 통과시키면 그게 이 리포가 반복해 온 fail-open 이다."""
    if hasattr(S._lane_forward_ev, "cache_clear"):
        S._lane_forward_ev.cache_clear()
    monkeypatch.setattr(S, "_lane_forward_ev", lambda: {})
    row = {"size_pct_total": 2.0}
    S._apply_operator_ev_floor(row, "nasdaq_swing")
    assert row["operator_verdict"] == "UNKNOWN"
    assert "size_pct_total" not in row


def test_nasdaq_lane_is_registered_and_mapped_to_the_gate():
    """웹에 레인만 넣고 게이트 매핑을 빼면 '모른다'가 차단 사유가 된다."""
    from modules.stream_exclusion import GATE_LANE_MAP, UNGATED_PUBLISHED_LANES
    assert "nasdaq_swing" in S.LANES
    assert S.LANES["nasdaq_swing"]["dir"] == "us_research"
    assert GATE_LANE_MAP.get("nasdaq_swing") == "nasdaq_session_tape"
    assert "nasdaq_swing" not in UNGATED_PUBLISHED_LANES, (
        "이 레인은 게이트 원장을 읽는다 — UNGATED 로 두면 CONFIRM 이 나와도 "
        "화면엔 '게이트가 판단하지 않는 레인'으로 막힌다")


def test_nasdaq_is_produced_by_exactly_one_path():
    """급소 — 같은 원장을 두 곳에서 읽어 AXTI·MRNA 가 화면에 두 번 떴다.

    nasdaq_picks() 가 자체 리더를 갖고 있었고 내가 별도 레인을 추가해 중복이 됐다.
    한 경로로 합쳐야 순위·만료·EV기준·발화빈도가 KR 레인과 같은 규칙으로 붙는다.
    """
    import inspect
    src = inspect.getsource(S.nasdaq_picks)
    assert "_a_picks_ledger" in src, "등록 레인으로 위임해야 한다"
    assert "open(" not in src, "자체 리더를 두면 사본이 된다"
    psrc = inspect.getsource(S.picks)
    assert "a_picks() + b_picks() + nasdaq_picks()" not in psrc, "합산하면 중복이다"
    assert 'lane == "nasdaq_swing"' not in psrc, (
        "특례가 남으면 그 레인만 순위·만료·EV기준을 다른 경로로 받는다")


def test_ledger_reader_accepts_the_symbol_key():
    """원장마다 종목 키가 다르다 — 나스닥은 `symbol` 이다.

    ticker 만 물으면 code 가 빈 문자열이 되어 이름도 차트도 안 붙는다.
    라이브에서 실제로 나스닥 픽의 종목명이 비어 있었다.
    """
    import inspect
    src = inspect.getsource(S._a_picks_ledger)
    assert 'r.get("ticker") or r.get("symbol")' in src
    assert "if not code:" in src, "코드가 없으면 픽을 만들지 않아야 한다"


# ── 4. 발화 빈도 (운영자 기준: 3거래일 1회) ──────────────────────────────────

def test_trading_days_skips_weekends():
    assert S._trading_days_between("2026-08-19", "2026-08-20") == 1
    assert S._trading_days_between("2026-08-14", "2026-08-18") == 2   # 금->화, 주말 제외
    assert S._trading_days_between("2026-08-20", "2026-08-19") == 0
    assert S._trading_days_between("깨진값", "2026-08-20") is None


def test_sparse_lane_loses_sizing_even_with_good_ev(monkeypatch):
    """EV 가 좋아도 픽이 안 나오면 거래할 수 없다.

    kosdaq_intraday 가 실제로 그렇다 — 원장 8건이 전부이고 2026-06-29 -> 07-31
    한 달 공백이 있다. 화면이 말하지 않으면 살아있는 레인으로 오해한다.
    """
    monkeypatch.setattr(S, "_lane_frequency",
                        lambda lane, today=None: {"last_fired": "2026-08-11", "days_since": 7,
                                                  "median_gap": 11, "worst_gap": 24,
                                                  "firing_days": 8, "frequency_ok": False})
    monkeypatch.setattr(S, "_lane_forward_ev", lambda: {"kosdaq_intraday_t10": (7.0, 85.7, 7)})
    row = S._pick_row("053110", "KOSDAQ", "kosdaq_intraday", entry=1000.0, prob=0.8,
                      scan_date="2026-08-20")
    assert "size_pct_total" not in row, "발화가 드문 레인에 사이징을 주면 안 된다"
    assert "발화 부족" in row["size_note"]
    assert row["lane_frequency"]["median_gap"] == 11


def test_frequent_lane_keeps_sizing(monkeypatch):
    """오탐 방지 — 매일 도는 레인까지 막으면 화면이 비어 아무도 안 본다."""
    monkeypatch.setattr(S, "_lane_frequency",
                        lambda lane, today=None: {"last_fired": "2026-08-20", "days_since": 0,
                                                  "median_gap": 1, "worst_gap": 3,
                                                  "firing_days": 32, "frequency_ok": True})
    monkeypatch.setattr(S, "_lane_forward_ev", lambda: {"swing_candidate": (2.4, 84.6, 46)})
    row = S._pick_row("000001", "KOSDAQ", "kosdaq_swing", entry=1000.0, prob=0.8,
                      scan_date="2026-08-20")
    assert row.get("size_pct_total") == 2.0
    assert "발화 부족" not in (row.get("size_note") or "")


# ── 5. LANES 밖 레인 (실제로 /api/picks 를 500 으로 만들었다) ────────────────

@pytest.mark.parametrize("lane", ["b_market_neutral", "", "존재하지않는레인", "swing_ensemble"])
def test_lanes_outside_the_registry_do_not_crash(lane):
    """급소 — LANES 에 없는 레인이 빈도 조회에 닿으면 ledger 가 "" 가 되어
    경로가 디렉터리가 되고 open() 이 IsADirectoryError 를 냈다.
    `picks()` 는 a_picks + b_picks 를 합치므로 **전체 API 가 죽는다.**
    단위 테스트가 LANES 안 레인만 봐서 못 잡았고, 브라우저로 열어서 잡았다.

    2026-08-20 갱신: `nasdaq_swing` 은 그 뒤 정식 등록돼 더는 "밖"이 아니다.
    **레인을 등록했으면 그 레인을 밖이라 부르는 테스트도 같이 고쳐야 한다** —
    안 고쳐서 라이브에서만 깨졌다(런타임 원장이 있어 실제 값이 나왔다).
    """
    assert S._lane_frequency(lane) is None


def test_read_ledger_never_opens_a_directory():
    assert S._read_ledger("") == []
    assert S._read_ledger(None) == []
    assert S._read_ledger("없는파일.jsonl") == []


def test_pick_row_survives_a_lane_outside_the_registry():
    """LANES 밖 레인으로도 픽 한 줄은 만들어져야 한다 — 죽으면 전체가 죽는다."""
    row = S._pick_row("AXTI", "NASDAQ", "b_market_neutral", entry=10.0, prob=0.8,
                      scan_date="2026-08-20", name="AXT Inc")
    assert row["code"] == "AXTI"
    assert "lane_frequency" not in row, "근거가 없으면 빈도를 지어내지 않는다"
    assert row.get("operator_verdict") == "UNKNOWN"
    assert "size_pct_total" not in row, "근거 없는 레인에 사이징을 주면 안 된다"


# ── 6. 매수 타이밍 (2026-08-20 브라우저 확인) ────────────────────────────────

def test_timing_reads_the_nasdaq_ledger_directory():
    """디렉터리 인자를 빠뜨리면 이 화면에서만 나스닥이 통째로 사라진다(탭도 안 생긴다)."""
    import inspect
    src = inspect.getsource(S.buy_timing)
    assert '_read_ledger(meta["ledger"], meta.get("dir"))' in src


def test_timing_win_rate_comes_from_the_gate_not_a_constant():
    """화면이 "실측"이라 말하면 실측이어야 한다.

    종전에는 하드코딩 상수(kospi_intraday PRIMARY=86)를 "실측 승률"로 표시했다.
    게이트 실측은 그와 다르고(fwd_win 70.8) 상수는 갱신되지 않는다.
    """
    import inspect
    src = inspect.getsource(S.buy_timing)
    assert "_lane_forward_ev()" in src, "게이트 실측을 읽어야 한다"
    assert "게이트 실측" in src and "참고치" in src, "실측/참고치를 구분해 표시해야 한다"
    assert 'f"레인 교차 최선 — {best[\'lane_label\']} 실측 승률 ~{_w(best)}%"' not in src


def test_timing_recommends_nothing_when_everything_is_below_the_kill_floor():
    """최선이 없는 날은 없다고 말해야 한다.

    억지로 하나를 세우면 화면이 매일 매수를 권하는 도구가 된다.
    실제로 만료된 픽(삼성공조, 매수일 08-19)이 08-20 화면에서 "오늘의 최선"이었다.
    """
    import inspect
    src = inspect.getsource(S.buy_timing)
    assert "tradable" in src and "OPERATOR_EV_KILL_PCT" in src
    assert "no_best_reason" in src, "고르지 않은 사유를 남겨야 한다"

    ts = (ROOT_TS := Path(__file__).resolve().parents[1] / "web/frontend/src/pages/Timing.tsx").read_text(encoding="utf-8")
    assert "no_best_reason" in ts, "화면이 그 사유를 읽어야 한다"
    assert "오늘의 최선: 없음" in ts


def test_performance_says_why_nasdaq_is_absent_from_the_alpha_table():
    """조용히 빼면 "나스닥은 성과가 없다"로 읽힌다.

    레인별 알파는 px_long(KR 유니버스) 대비라 US 종목은 벤치마크가 없다 —
    누락이 아니라 구조적 한계다. 화면이 그 사실을 말해야 한다.
    """
    import inspect
    src = inspect.getsource(S.performance)
    assert "lanes_note" in src, "사유를 산출에 실어야 한다"
    assert "구조적 한계" in src

    tsx = (Path(__file__).resolve().parents[1] / "web/frontend/src/pages/Performance.tsx").read_text(encoding="utf-8")
    assert "lanes_note" in tsx, "화면이 그 사유를 읽어야 한다"


def test_timing_says_which_lanes_it_cannot_price():
    """나스닥이 이 화면에 없는 것은 구조적 한계다 — ohlc_daily 는 KR 6자리 코드 전용이라
    US 심볼에 가격을 못 붙인다. 조용히 빼면 "추적하지 않는다"로 읽힌다."""
    import inspect
    src = inspect.getsource(S.buy_timing)
    assert "coverage_note" in src and "구조적 한계" in src
    ts = (Path(__file__).resolve().parents[1] / "web/frontend/src/pages/Timing.tsx").read_text(encoding="utf-8")
    assert "coverage_note" in ts and "{cov}" in ts


# ── 7. 운영 화면 에스컬레이션 (2026-08-20) ──────────────────────────────────

def test_ops_status_carries_the_escalations():
    """판정기는 매일 critical 을 내는데 운영 화면엔 데이터 신선도만 있었다.

    경보를 만들어 놓고 아무도 읽지 않는 파일에 쓰면 그것도 조용한 실패다.
    """
    import inspect
    src = inspect.getsource(S.ops_status)
    assert "_ops_escalations()" in src


def test_missing_sentinel_output_says_so_instead_of_showing_zero(tmp_path, monkeypatch):
    """급소 — 산출이 없을 때 조용히 0건으로 보이면 "문제 없음"으로 읽힌다."""
    monkeypatch.setattr(S, "REPO", str(tmp_path))
    out = S._ops_escalations()
    assert out["items"] == []
    assert out["note"] and "0건이라는 뜻이 아니다" in out["note"]


def test_escalations_include_both_sources(tmp_path, monkeypatch):
    """판정기와 미채점 경보를 한 자리에 모은다 — 두 곳을 따로 보게 하면 하나는 안 본다."""
    v = tmp_path / "runtime_state" / "reports" / "validation"
    v.mkdir(parents=True)
    (v / "sentinel_latest.json").write_text(json.dumps({
        "generated_at": "2026-08-20T01:00:00", "worst_severity": "critical",
        "escalations": [{"severity": "critical", "check": "prereg_kill_criteria",
                         "id": "kr_ranking_shadow_kill_enforced", "verdict": "FIRED",
                         "detail": "킬 이후 200건", "on_fire": "정지 지점으로 올린다"}],
    }), encoding="utf-8")
    (v / "unresolved_staleness_latest.json").write_text(json.dumps({
        "stale_days": 10, "breached_ledgers": ["swing_candidate"]}), encoding="utf-8")
    monkeypatch.setattr(S, "REPO", str(tmp_path))

    out = S._ops_escalations()
    checks = {i["check"] for i in out["items"]}
    assert checks == {"prereg_kill_criteria", "unresolved_staleness"}
    kill = [i for i in out["items"] if i["check"] == "prereg_kill_criteria"][0]
    assert kill["action"] == "정지 지점으로 올린다", "무엇을 해야 하는지가 함께 와야 한다"


def test_ops_page_renders_the_escalations():
    ops = (Path(__file__).resolve().parents[1] / "web/frontend/src/pages/Ops.tsx").read_text(encoding="utf-8")
    assert "escalations" in ops and "에스컬레이션" in ops
    assert "CRIT" in ops, "심각도가 구분돼 보여야 한다"
    assert "e.note" in ops, "산출 부재도 화면에 남겨야 한다"


# ── 8. 체결 가능성 (2026-08-20, [G] 발견 · 운영자 승인) ─────────────────────

def test_limit_up_pick_is_blocked_as_unfillable():
    """급소 — 상한가에는 매도호가가 없어 그 가격에 체결할 수 없다.

    라이브 원장 실측: `kospi_intraday` 58건 중 5건(8.9%)이 당일 +29% 이상 종가.
    `475150.KS 2026-07-23` 은 +30.00% 에 잡혀 **ret3d −39.58%** 인데
    원장에는 `exit_t5_h5 = 5.0`(터치 성공)으로 기록돼 있다.
    걷어내면 백테스트 우위가 소멸한다(KOSDAQ −0.50 p=0.92 / KOSPI +0.72 p=0.18).
    """
    row = {"kind": "INTRADAY", "day_change": 29.79, "size_pct_total": 2.0}
    got = S._entry_attainability(row)
    assert got["attainable"] is False
    assert got["attainability"] == "LIMIT_UP"
    assert "체결할 수 없다" in got["attainability_note"]


@pytest.mark.parametrize("dc,want", [
    (29.0, "LIMIT_UP"), (30.0, "LIMIT_UP"), (28.9, "OK"),
    (-29.0, "LIMIT_DOWN"), (-30.0, "LIMIT_DOWN"), (-28.9, "OK"),
    # 하한가는 **차단이 아니라 경고**다 — 진입은 매수이고 하한가엔 매도 물량이 쌓여 있다
    (0.0, "OK"), (None, "OK"),
])
def test_limit_threshold_boundaries(dc, want):
    """경계를 정확히 — 호가단위 반올림 때문에 29.0%를 판정선으로 쓴다."""
    row = {"kind": "SWING", "day_change": dc}
    assert S._entry_attainability(row)["attainability"] == want


def test_stale_reference_price_is_flagged_not_blocked():
    """진입가가 '스캔일 종가'인데 매수일이 다음날이면 그 가격은 이미 지나갔다.

    실측: `entry_reference_price` 는 당일 종가와 중앙 편차 0.000%(57%가 정확일치)인데
    **익일 시가와는 |차|<0.5% 가 0%**, 중앙 −0.79%, 최대 +12.99% 어긋난다.
    불가가 아니라 **불확실**이므로 차단하지 않고 표시한다 — 차단하면 화면이 비고,
    그러면 사용자는 아무 정보도 못 받는다.
    """
    row = {"kind": "INTRADAY", "scan_date": "2026-08-19", "buy_date": "2026-08-20"}
    got = S._entry_attainability(row)
    assert got["attainable"] is None, "불가가 아니라 불확실이다"
    assert got["attainability"] == "STALE_REFERENCE"
    assert "종가" in got["attainability_note"] and "체결가는 다르다" in got["attainability_note"]


def test_swing_next_open_entry_is_not_flagged_stale():
    """오탐 방지 — 스윙은 설계상 '익일 시가 진입'이라 정합하다.
    실측: 스윙 원장 logged_at 중앙 20:38 KST → 익일 09:00 진입. 어긋나지 않는다."""
    row = {"kind": "SWING", "scan_date": "2026-08-19", "buy_date": "2026-08-20"}
    assert S._entry_attainability(row)["attainability"] == "OK"


def test_unfillable_pick_loses_sizing_in_pick_row():
    """체결 불가는 사이징을 뗀다. **그리고 다른 사유에 가려지지 않아야 한다.**

    2026-08-20: 각 가드가 `size_note` 를 덮어써서 상한가 경고가 폐기선 문구에 가려졌다.
    `blocks` 로 누적하고 심각도 순으로 정렬한다.
    """
    row = S._pick_row("001510", "KOSPI", "kospi_intraday", entry=2810.0, prob=0.8,
                      scan_date="2026-08-20", extra={"day_change": 29.79})
    assert row["attainable"] is False
    assert "size_pct_total" not in row
    assert "체결 불가" in row.get("block_labels", []), "사유가 목록에 남아야 한다"
    assert row["size_note"].startswith("⛔ 체결 불가"), "가장 심각한 사유가 앞에 와야 한다"


def test_blockers_accumulate_and_sort_by_severity():
    """급소 — 사유가 여럿일 때 덜 심각한 것이 더 심각한 것을 덮으면 안 된다."""
    row = {"size_pct_total": 2.0}
    S._add_block(row, "kill", "폐기선 아래", "EV -0.19%")
    S._add_block(row, "unfillable", "체결 불가", "상한가")
    S._add_block(row, "expired", "만료 7일", "매수일 경과")
    assert row["block_labels"] == ["체결 불가", "만료 7일", "폐기선 아래"]
    assert row["size_note"].startswith("⛔ 체결 불가")
    assert "그 외: 만료 7일, 폐기선 아래" in row["size_note"]
    assert "size_pct_total" not in row


def test_same_blocker_is_not_duplicated():
    row = {}
    S._add_block(row, "kill", "폐기선 아래", "x")
    S._add_block(row, "kill", "폐기선 아래", "y")
    assert row["block_labels"] == ["폐기선 아래"]


def test_frontend_shows_attainability_first():
    """못 사는 픽은 나머지 정보가 의미 없으니 칩이 가장 먼저 와야 한다."""
    ui = (Path(__file__).resolve().parents[1] / "web/frontend/src/components/ui.tsx").read_text(encoding="utf-8")
    assert "LIMIT_UP" in ui and "체결불가" in ui
    assert ui.index("LIMIT_UP") < ui.index("is_top1"), "체결 가능성이 순위보다 먼저"
    pk = (Path(__file__).resolve().parents[1] / "web/frontend/src/pages/Picks.tsx").read_text(encoding="utf-8")
    assert "attainability_note" in pk, "상세에 사유가 있어야 한다"


def test_day_change_is_carried_from_the_ledger():
    """원장에서 안 실어 오면 상한가를 못 거른다."""
    assert "day_change" in S._LEDGER_EXTRA_KEYS



def test_limit_down_is_a_warning_not_a_block():
    """방향을 틀리면 안 된다 — 진입은 **매수**다.

    상한가: 매도 물량이 없어 **살 수 없다** → 차단.
    하한가: 매수 물량이 없어 **팔 수 없다** → 매수는 체결된다. 차단이 아니라
            "출구가 막힐 수 있다"는 경고다.
    2026-08-20: abs() 로 묶어 둘을 같이 처리했던 것을 정정했다.
    """
    up = S._entry_attainability({"kind": "INTRADAY", "day_change": 29.9})
    dn = S._entry_attainability({"kind": "INTRADAY", "day_change": -29.9})
    assert up["attainable"] is False, "상한가는 살 수 없다 — 차단"
    assert dn["attainable"] is None, "하한가는 살 수 있다 — 경고"
    assert "출구가 막힐" in dn["attainability_note"]
