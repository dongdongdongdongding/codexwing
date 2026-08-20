"""레인별 실측 승률의 시장 필터·비용 기준 (audit-gate.md F8).

두 결함이 겹쳐 있었다:

1. `kospi_swing`과 `kosdaq_swing`이 **같은 원장을 market 필터 없이** 읽어
   (`_read_ledger`에 필터가 없다) 두 레인에 **동일한 풀링 승률**이 각각
   "실측 N건"이라는 레인별 라벨을 달고 표시됐다. 실측: 두 레인 모두 71% (n=167).
2. 웹은 cost 미차감 **gross > 0.3**, 게이트(`report_research_recursion_gate.py:105,115`)는
   `gross - cost` 후 **net > 0.3**. 같은 원장의 두 소비자가 서로 다른 기준을 썼다.
   웹이 정확히 cost만큼 관대하다.
"""
from __future__ import annotations

import json

import pytest

from web.backend import services


@pytest.fixture(autouse=True)
def _isolated_ledgers(tmp_path, monkeypatch):
    monkeypatch.setattr(services, "EXP", str(tmp_path))
    services._MEASURED_WIN_CACHE.update(ts=0.0, data={})
    yield tmp_path
    services._MEASURED_WIN_CACHE.update(ts=0.0, data={})


def _write_ledger(root, fn, rows):
    (root / fn).write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def _swing_rows(n_kospi, kospi_ret, n_kosdaq, kosdaq_ret):
    rows = [{"market": "KOSPI", "ticker": f"{i:06d}.KS", "policy_ret": kospi_ret} for i in range(n_kospi)]
    rows += [{"market": "KOSDAQ", "ticker": f"{i:06d}.KQ", "policy_ret": kosdaq_ret} for i in range(n_kosdaq)]
    return rows


def test_swing_lanes_no_longer_share_one_pooled_win_rate(_isolated_ledgers):
    """F8-1 회귀: 두 스윙 레인이 서로 다른 시장을 재야 한다.

    KOSPI 30건은 전부 승(net 2.0 > 0.3), KOSDAQ 30건은 전부 패(net -1.3).
    풀링이면 둘 다 50%로 같아진다 — 그게 수정 전 동작이다.
    """
    _write_ledger(_isolated_ledgers, "kr_swing_candidate_ledger.jsonl",
                  _swing_rows(30, 2.3, 30, -1.0))

    win = services._measured_win()

    assert win["kospi_swing"][0] == 100
    assert win["kosdaq_swing"][0] == 0
    assert win["kospi_swing"][0] != win["kosdaq_swing"][0]


def test_each_swing_lane_counts_only_its_own_market_in_n(_isolated_ledgers):
    """'실측 N건' 라벨의 N도 레인별이어야 한다 (풀링 167이 아니라)."""
    _write_ledger(_isolated_ledgers, "kr_swing_candidate_ledger.jsonl",
                  _swing_rows(25, 2.3, 40, 2.3))

    win = services._measured_win()

    assert "25건" in win["kospi_swing"][1]
    assert "40건" in win["kosdaq_swing"][1]


def test_win_threshold_matches_the_gate_net_basis(_isolated_ledgers):
    """F8-2 회귀: 게이트와 같은 net 기준(gross - cost > 0.3)을 써야 한다.

    policy_ret=0.5는 gross로는 승(>0.3)이지만 net으로는 0.5-0.3=0.2로 패다.
    수정 전 웹은 이걸 승으로 셌고 게이트는 패로 셌다 — 1.9pp 괴리의 정체.
    """
    _write_ledger(_isolated_ledgers, "kr_swing_candidate_ledger.jsonl",
                  _swing_rows(25, 0.5, 25, 0.5))

    win = services._measured_win()

    assert win["kospi_swing"][0] == 0, "gross 기준이면 100%가 나온다"
    assert win["kosdaq_swing"][0] == 0


def test_net_basis_uses_the_per_lane_cost_constant(_isolated_ledgers):
    """kosdaq_intraday는 cost 0.33 (게이트 LANES와 동일). 0.6은 net 0.27로 패."""
    _write_ledger(_isolated_ledgers, "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl",
                  [{"market": "KOSDAQ", "exit_t10_h5": 0.6} for _ in range(25)])

    win = services._measured_win()

    assert win["kosdaq_intraday"][0] == 0

    services._MEASURED_WIN_CACHE.update(ts=0.0, data={})
    _write_ledger(_isolated_ledgers, "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl",
                  [{"market": "KOSDAQ", "exit_t10_h5": 0.64} for _ in range(25)])

    assert services._measured_win()["kosdaq_intraday"][0] == 100


def test_thin_lane_still_falls_back_to_frozen_backtest(_isolated_ledgers):
    """n<20 폴백 계약은 그대로여야 한다 (시장 필터로 n이 줄어도 동일하게 동작)."""
    _write_ledger(_isolated_ledgers, "kr_swing_candidate_ledger.jsonl",
                  _swing_rows(25, 2.3, 5, 2.3))

    win = services._measured_win()

    assert win["kospi_swing"][0] == 100
    assert win["kosdaq_swing"] == (62, "백테스트 8y")


def test_rows_without_a_market_field_are_not_silently_dropped(_isolated_ledgers):
    """원장 스키마 드리프트(F9) 대비 — market이 없으면 필터로 표본을 통째로 날리지 않는다."""
    _write_ledger(_isolated_ledgers, "kospi_intraday_swing_ledger.jsonl",
                  [{"exit_t5_h5": 2.0} for _ in range(25)])

    win = services._measured_win()

    assert win["kospi_intraday"][0] == 100
    assert "25건" in win["kospi_intraday"][1]
