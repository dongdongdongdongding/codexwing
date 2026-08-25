"""전진 기록의 **구성 전환 경계** (2026-08-25 운영자 지적).

화면이 `forward EV -0.33% (n=206)` 을 띄우는데 그 206건은 **구성을 바꾸기 전 셀**의 기록이다.
새 셀은 2026-08-21 에 첫 픽을 냈다. 화면만 보면 **새 셀이 -0.33% 를 낸 것처럼 읽힌다** —
우리가 교체한 이유가 된 숫자를 교체 결과로 보여주는 것이다.

판정 자체는 게이트가 내린다(정지점). 여기서 고치는 것은 **그 판정이 무엇을 채점했는지**다.
"""
import json

import pytest

import web.backend.services as S


def _rows(tmp_path, monkeypatch, rows, lane="t_lane"):
    p = tmp_path / "led.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(S, "REPO", str(tmp_path))
    (tmp_path / "runtime_state" / "reports" / "experimental").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime_state" / "reports" / "experimental" / "led.jsonl").write_text(
        p.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setitem(S.LANES, lane, {"ledger": "led.jsonl", "label": "t", "kind": "SWING", "badge": "x"})


def test_gate_field_marks_the_new_configuration(tmp_path, monkeypatch):
    """경계 표지는 `gate` 다 — 새 생산자가 **발행 시점**에 쓴다."""
    _rows(tmp_path, monkeypatch, [
        {"date": "2026-07-03", "market": "KOSPI", "policy_ret": -1.0},                   # 구성 이전
        {"date": "2026-07-04", "market": "KOSPI", "policy_ret": 5.0},                    # 구성 이전
        {"date": "2026-08-21", "market": "KOSPI", "policy_ret": None, "gate": "FIRE"},   # 현행
    ])
    ep = S._forward_epoch("t_lane", market="KOSPI")
    assert ep["previous"]["resolved"] == 2 and ep["previous"]["since"] == "2026-07-03"
    assert ep["current"]["picks"] == 1 and ep["current"]["resolved"] == 0
    assert ep["current"]["since"] == "2026-08-21"


def test_contract_h_is_not_a_boundary_marker(tmp_path, monkeypatch):
    """🔴 `contract_h` 로 가르면 안 된다 — `resolve_pending` 이 **정산 시점에** 찍으므로
    전환 이전 픽에도 붙는다(실측: 2026-08-12 행에도 있다). 표지는 발행 시점에 써야 한다."""
    _rows(tmp_path, monkeypatch, [
        {"date": "2026-07-03", "market": "KOSPI", "policy_ret": -1.0, "contract_h": 5},  # 정산 때 찍힌 것
        {"date": "2026-08-21", "market": "KOSPI", "policy_ret": None, "gate": "FIRE"},
    ])
    ep = S._forward_epoch("t_lane", market="KOSPI")
    assert ep["previous"]["resolved"] == 1, "contract_h 가 있다고 현행 구성으로 세면 안 된다"
    assert ep["current"]["picks"] == 1


def test_epoch_splits_by_market_so_one_lane_does_not_carry_the_other(tmp_path, monkeypatch):
    """`GATE_LANE_MAP` 이 두 스윙 레인을 하나로 묶어 EV 가 풀링된다
    (실측 KOSPI −0.68 / KOSDAQ +0.05 / 풀링 −0.33). 표시만이라도 갈라야 한다."""
    _rows(tmp_path, monkeypatch, [
        {"date": "2026-07-03", "market": "KOSPI", "policy_ret": -5.0},
        {"date": "2026-07-03", "market": "KOSDAQ", "policy_ret": 5.0},
    ])
    kp = S._forward_epoch("t_lane", market="KOSPI")["previous"]
    kq = S._forward_epoch("t_lane", market="KOSDAQ")["previous"]
    assert kp["ev"] != kq["ev"], "시장을 안 가르면 한 레인이 다른 레인의 손실을 진다"
    # 비용은 `modules.trading_costs` 단일 출처에서 온다 — 여기 박아 두면
    # 비용이 바뀔 때마다 깨지고, 이 값들이 비용에 딸린 값이라는 사실도 가려진다.
    # `ev` 는 표시용이라 소수 2자리로 반올림돼 나온다.
    assert kp["ev"] == round(-5.0 - S.COST_PCT, 2)
    assert kq["ev"] == round(5.0 - S.COST_PCT, 2)


def test_kill_note_says_it_is_judging_the_previous_configuration(tmp_path, monkeypatch):
    """정산 표본이 30건 미만이면 **「아직 판정 표본이 아니다」**를 반드시 붙인다.
    안 붙이면 사용자가 새 셀의 성적으로 읽는다 — 이 수정의 목적 그 자체다."""
    _rows(tmp_path, monkeypatch, [
        {"date": "2026-07-03", "market": "KOSPI", "policy_ret": -1.0},
        {"date": "2026-08-21", "market": "KOSPI", "policy_ret": None, "gate": "FIRE"},
    ], lane="kospi_swing")
    monkeypatch.setattr(S, "_lane_forward_ev", lambda: {"swing_candidate": (-0.33, 69.9, 206)})
    row = {"market": "KOSPI", "size_pct_total": 2.0}
    S._apply_operator_ev_floor(row, "kospi_swing")
    note = " ".join(str(v) for v in row.values())
    assert "구성 전환 이전" in note and "아직 판정 표본이 아니다" in note
    assert row["operator_verdict"] == "KILL", "판정 자체는 게이트가 내린다 — 문구만 고친다"
