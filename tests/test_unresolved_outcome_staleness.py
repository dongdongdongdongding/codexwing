"""미채점 행 임계 초과 경보 (F6, swing-main-r6sb).

미채점 행이 임계를 넘겨도 경보가 없었다. resolver 는 bare except 라 실패가 드러나지 않고,
재시도 상한·dead-letter 가 없어 실패한 행이 그냥 넘어가며, report_data_manifest 는 원장의
최신 date 만 봐서 개별 행 미채점을 못 본다. **이 침묵이 7,171건 만료의 상류다.**
"""
from __future__ import annotations

import datetime as dt
import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
st = importlib.import_module("multi_agent.tools.report_unresolved_outcome_staleness")

TODAY = dt.date(2026, 8, 16)


def ledger(tmp_path, rows, name="l.jsonl"):
    p = tmp_path / name
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return p


def cfg(path, field="policy_ret", date_field="date"):
    return {"ledger": path, "field": field, "date_field": date_field}


def test_stale_unresolved_rows_are_counted(tmp_path):
    """임계를 넘긴 미채점 행이 잡혀야 한다 — 라이브의 32일 방치가 이 형태다."""
    rows = [{"policy_ret": 1.0, "date": "2026-08-14"},          # 채점됨
            {"policy_ret": None, "date": "2026-08-14"},          # 미채점 2일 — 정상
            {"policy_ret": None, "date": "2026-07-15"}]          # 미채점 32일 — 방치
    r = st.scan_lane("l", cfg(ledger(tmp_path, rows)), TODAY, 10)
    assert r["rows"] == 3 and r["unresolved"] == 2
    assert r["stale"] == 1 and r["max_age_days"] == 32
    assert r["worst"][0]["date"] == "2026-07-15"


def test_fresh_unresolved_rows_are_not_flagged(tmp_path):
    """지평이 아직 안 익은 행까지 경보하면 매일 울려서 아무도 안 본다."""
    rows = [{"policy_ret": None, "date": "2026-08-14"}] * 5
    r = st.scan_lane("l", cfg(ledger(tmp_path, rows)), TODAY, 10)
    assert r["unresolved"] == 5 and r["stale"] == 0


def test_threshold_boundary_is_exclusive(tmp_path):
    """정확히 임계일이면 아직 경보하지 않는다 (초과분만)."""
    rows = [{"policy_ret": None, "date": str(TODAY - dt.timedelta(days=10))},
            {"policy_ret": None, "date": str(TODAY - dt.timedelta(days=11))}]
    r = st.scan_lane("l", cfg(ledger(tmp_path, rows)), TODAY, 10)
    assert r["stale"] == 1


def test_undated_rows_are_reported_not_silently_dropped(tmp_path):
    """날짜를 못 읽는 행을 조용히 버리면 그게 또 하나의 침묵이 된다."""
    rows = [{"policy_ret": None}, {"policy_ret": None, "date": "쓰레기"}]
    r = st.scan_lane("l", cfg(ledger(tmp_path, rows)), TODAY, 10)
    assert r["undated"] == 2 and r["stale"] == 0


def test_compact_dates_are_understood(tmp_path):
    rows = [{"alpha": None, "scan_date": "20260715"}]
    r = st.scan_lane("l", cfg(ledger(tmp_path, rows), field="alpha", date_field="scan_date"),
                     TODAY, 10)
    assert r["stale"] == 1 and r["max_age_days"] == 32


def test_scoring_pipe_is_judged_not_the_publish_scope(tmp_path):
    """발행되지 않는 픽도 채점은 돼야 한다 — publish_scope 를 적용하면 안 된다.

    여기서 묻는 것은 "무엇으로 판정할까"가 아니라 "파이프가 이 행을 처리했는가"다.
    """
    rows = [{"policy_ret": None, "date": "2026-07-15", "tier": "CANDIDATE"},
            {"policy_ret": None, "date": "2026-07-15", "tier": "PRIMARY"}]
    c = cfg(ledger(tmp_path, rows))
    c["publish_scope"] = {"tier": "PRIMARY"}
    assert st.scan_lane("l", c, TODAY, 10)["stale"] == 2, "발행범위로 걸러버렸다"


def test_targets_come_from_the_gate_lanes():
    """대상 정의를 여기 따로 적으면 두 벌이 갈린다 — 게이트 LANES 를 그대로 쓴다."""
    gate = importlib.import_module("multi_agent.tools.report_research_recursion_gate")
    assert st.LANES is gate.LANES


# --- 경보가 실제로 울리는가 -------------------------------------------------

def test_exit_code_is_nonzero_when_threshold_breached(tmp_path, monkeypatch, capsys):
    """세어만 두고 0 으로 끝내면 침묵을 하나 더 만드는 것이다."""
    led = ledger(tmp_path, [{"policy_ret": None, "date": "2026-07-01"}])
    monkeypatch.setattr(st, "LANES", {"l": cfg(led)})
    monkeypatch.setattr(sys, "argv", ["x", "--no-write"])
    rc = st.main()
    out = capsys.readouterr().out
    assert rc == 1, "임계 초과인데 성공으로 끝났다"
    assert "l" in json.loads(out.splitlines()[0])["breached_ledgers"]


def test_exit_code_is_zero_when_clean(tmp_path, monkeypatch, capsys):
    led = ledger(tmp_path, [{"policy_ret": 1.0, "date": "2026-08-14"}])
    monkeypatch.setattr(st, "LANES", {"l": cfg(led)})
    monkeypatch.setattr(sys, "argv", ["x", "--no-write"])
    assert st.main() == 0
    assert json.loads(capsys.readouterr().out.splitlines()[0])["total_stale"] == 0


def test_shared_ledger_is_not_double_counted(tmp_path, monkeypatch, capsys):
    """b 두 레인은 같은 원장을 쓴다 — 총계가 두 배로 잡히면 안 된다."""
    led = ledger(tmp_path, [{"alpha": None, "date": "2026-07-01"}])
    monkeypatch.setattr(st, "LANES", {"a": cfg(led, field="alpha"), "b": cfg(led, field="alpha")})
    monkeypatch.setattr(sys, "argv", ["x", "--no-write"])
    st.main()
    assert json.loads(capsys.readouterr().out.splitlines()[0])["total_stale"] == 1
