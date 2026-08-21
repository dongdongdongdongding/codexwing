"""코스닥 15:00 레인의 계약이 네 갈래로 갈려 있었다 ([N] 표 A).

```
① 학습 라벨   touch3d_t5      = TP5 / H3
② 채점        3일 MFE ≥ +5%   = TP5 / H3
③ 모듈 선언   target_tp_pct=10.0, hold_days=5   ← §7-E 승격 계약
④ 웹 카드     TP5 / H3        ← 폴백이 ③을 덮었다
```
`route_live_intraday()` 의 `deep_rows` 에 `trade_plan` 이 없어
`candidate_interpretation.py:407-414` 의 `or 5.0` / `profile["horizon_days"]` 가 걸렸다.
**사용자는 모듈이 승격한 것과 다른 계약을 안내받고 있었다.**
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _src():
    from multi_agent.tools import report_kosdaq_intraday_vwap_guard as m
    return inspect.getsource(m.route_live_intraday)


def test_deep_rows_carry_the_declared_trade_plan():
    """급소 — trade_plan 이 없으면 카드가 폴백 TP5/H3 로 나간다."""
    s = _src()
    assert '"trade_plan"' in s, "deep_rows 에 trade_plan 이 있어야 폴백이 안 걸린다"
    for k in ("target_tp_pct", "hold_days", "stop_sl_pct", "entry_price"):
        assert k in s.split('"trade_plan"')[1][:600], f"trade_plan 에 {k} 가 없다"


def test_trade_plan_reads_the_module_declaration_not_a_constant():
    """계약을 여기서 다시 쓰면 다섯 번째 갈래가 생긴다. 픽이 실어 온 값을 그대로 써야 한다."""
    s = _src()
    seg = s.split('"trade_plan"')[1][:600]
    assert 'pick.get("target_tp_pct")' in seg, "모듈 선언값을 그대로 전달해야 한다"
    assert 'pick.get("hold_days")' in seg
    assert "5.0" not in seg and "10.0" not in seg, "계약 숫자를 여기에 하드코딩하면 안 된다"


def test_horizon_follows_the_declared_hold_days():
    """`horizon: "3D"` 하드코딩이 구 계약의 잔재였다."""
    s = _src()
    assert '"horizon": "3D"' not in s, "구 계약 하드코딩이 남아 있다"
    assert 'hold_days' in s.split('"horizon"')[1][:200]


def test_module_still_declares_the_promoted_contract():
    """이 테스트가 지키는 원본. 모듈 선언이 바뀌면 여기서 먼저 알아야 한다."""
    from modules import kosdaq_intraday_vwap_guard as g
    src = inspect.getsource(g)
    assert '"target_tp_pct": 10.0' in src, "§7-E 승격 계약은 TP+10% 다"
    assert '"hold_days": 5' in src
    assert '"stop_sl_pct": None' in src, "손절 없음이 계약이다"
