"""갭 보너스는 **진입 시점 계약에 따라** 1일차 처리가 갈린다. 두 레인이 반대다.

- KR 스윙 (`report_kr_swing_candidate`): **익일 시가 진입**. 창의 1일차(k=0) 시가가 곧 진입가라
  자기 위로 갭업할 수 없다 → k=0 에서는 보너스가 없어야 한다(`fill = tgt`).
- 나스닥 (`report_nasdaq_session_tape`): **신호일 종가 진입**. 창은 신호일 **다음** 세션부터라
  k=0 시가는 전일 종가(=진입가) 위로 갭업할 수 있다 → k=0 에서도 보너스가 붙어야 한다.

이 차이를 모르고 KR 가드를 US 로 옮긴 것이 2026-08-22 에 고친 결함이다. 나스닥 원장 48건 중
터치 34건, 그중 21건이 1일차라 평균 +1.79pp 씩 깎여 **레인 전진 기록이 −0.78pp 축소**돼 있었다.

두 방향을 한 파일에서 못박는 이유: 누가 "두 resolve 가 다르니 통일하자"고 하면 반드시 한쪽이 깨진다.
"""
import json
import sys
import types

import pandas as pd
import pytest


def test_nasdaq_close_entry_takes_the_gap_bonus_on_day_one(tmp_path, monkeypatch):
    """종가 진입이므로 창 1일차 시가 갭업은 **실현된 이익**이다. 거부하면 안 된다."""
    import multi_agent.tools.report_nasdaq_session_tape as nst

    idx = pd.bdate_range("2026-06-02", periods=6)      # 신호일 06-01 다음 세션들
    frame = pd.DataFrame(
        {"Open":  [110.0, 108, 107, 106, 105, 104],    # 1일차가 목표(105) 위로 갭업
         "High":  [112.0, 109, 108, 107, 106, 105],
         "Low":   [ 99.0, 100, 101, 102, 103, 100],
         "Close": [111.0, 108, 107, 106, 105, 104]},
        index=idx,
    )
    monkeypatch.setitem(sys.modules, "yfinance",
                        types.SimpleNamespace(download=lambda *a, **k: frame))
    ledger = tmp_path / "nas.jsonl"
    ledger.write_text(json.dumps({"date": "2026-06-01", "symbol": "AAAA", "entry": 100.0}) + "\n",
                      encoding="utf-8")
    monkeypatch.setattr(nst, "LEDGER", ledger)

    nst.resolve_pending(pd.Timestamp("2026-06-20"))

    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert row["touch5"] == 1
    assert row["policy_ret"] == pytest.approx(10.0), (
        "1일차 시가 110 은 목표 105 위다 — fill=max(105,110)=110 이어야 한다. "
        "5.0 이 나오면 KR 익일시가용 `k > 0` 가드가 되살아난 것이다")


def test_kr_next_open_entry_has_no_bonus_on_day_one(tmp_path, monkeypatch):
    """익일시가 진입이므로 창 1일차 시가 = 진입가다. 자기 위로 갭업할 수 없다."""
    import multi_agent.tools.report_kr_swing_candidate as swc

    idx = pd.bdate_range("2026-06-02", periods=6)
    frame = pd.DataFrame(
        {"Open":  [1000.0, 1010, 1020, 1030, 1040, 1050],
         "High":  [1060.0, 1015, 1025, 1035, 1045, 1055],   # 1일차에 이미 +5% 터치
         "Low":   [ 990.0, 1000, 1010, 1020, 1030, 1040],
         "Close": [1050.0, 1010, 1020, 1030, 1040, 1050]},
        index=idx,
    )
    monkeypatch.setitem(sys.modules, "FinanceDataReader",
                        types.SimpleNamespace(DataReader=lambda code, start: frame))
    ledger = tmp_path / "kr.jsonl"
    ledger.write_text(json.dumps({"date": "2026-06-01", "ticker": "000001.KS"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(swc, "LEDGER", ledger)

    swc.resolve_pending(pd.Timestamp("2026-06-20"))

    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert row["entry_open"] == 1000.0
    assert row["ft_touch5"] == 1
    assert row["policy_ret"] == pytest.approx(5.0), (
        "진입가가 1일차 시가(1000)다 — 그 위로 갭업했다고 볼 수 없으므로 fill=목표가여야 한다")


def test_the_two_guards_are_deliberately_different():
    """소스에 두 형태가 공존해야 한다. 한쪽으로 통일되면 반드시 한 레인이 틀린다."""
    import pathlib
    kr = pathlib.Path("multi_agent/tools/report_kr_swing_candidate.py").read_text(encoding="utf-8")
    us = pathlib.Path("multi_agent/tools/report_nasdaq_session_tape.py").read_text(encoding="utf-8")
    assert "if (k > 0 and np.isfinite(o) and o > 0)" in kr, "KR 은 익일시가 진입이라 k>0 가드가 필요하다"
    assert "if (k > 0 and np.isfinite(o) and o > 0)" not in us, "US 는 종가 진입이라 k>0 가드가 있으면 틀린다"
