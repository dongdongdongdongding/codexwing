"""Exit-policy shadow resolution (observation-only) on the intraday lane ledgers.

swing-main-ayu1: resolve_pending additionally records exit_t5_h5 / exit_t10_h5 / ret5d
(sell-at-touch limit, gap-up fills at open, else 5d close hold) without touching the
existing touch3d_t5 / ret3d contract fields.
"""
import json

import pandas as pd

import multi_agent.tools.report_kosdaq_intraday_vwap_guard as guard


class _FakeClient:
    def daily_bars(self, code, **kwargs):
        return {"marker": "fake"}


def _future_frame():
    idx = pd.bdate_range("2026-06-01", periods=6)  # trade day + 5 future sessions
    # entry(close of trade day)=1000; day3 high touches +5% and +10%; 5d close = 980
    return pd.DataFrame(
        {
            "Open": [1000, 990, 1005, 1020, 1000, 985],
            "High": [1010, 1000, 1030, 1120, 1010, 990],
            "Low": [980, 970, 990, 1010, 970, 960],
            "Close": [1000, 995, 1010, 1060, 990, 980],
        },
        index=idx,
    )


def test_resolve_pending_records_exit_shadow_fields(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    row = {
        "ticker": "123456.KQ",
        "trade_date": "20260601",
        "entry_reference_price": 1000.0,
        "touch3d_t5": None,
    }
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
    monkeypatch.setattr(guard, "LEDGER", ledger)
    monkeypatch.setattr(guard, "normalize_kis_daily_bars", lambda code, payload: _future_frame())

    summary = guard.resolve_pending(_FakeClient(), today_trade_date="20260615")

    saved = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines()]
    assert len(saved) == 1
    out = saved[0]
    # 3d contract fields unchanged in semantics
    assert out["touch3d_t5"] == 1  # day3 high 1120 >= 1050
    assert out["ret3d"] == 6.0  # close day3 1060
    # exit shadow: +5% touch on day3 (high 1030 < 1050? no -> day4 wait) — day4 high 1120 >= 1050
    # fill = max(1050, open 1020) = 1050 -> +5.0
    assert out["exit_t5_h5"] == 5.0
    # +10% target 1100: day4 high 1120 >= 1100, fill max(1100, 1020) = 1100 -> +10.0
    assert out["exit_t10_h5"] == 10.0
    assert out["ret5d"] == -2.0  # 5th future close 980
    assert summary["exit_shadow"]["n"] == 1
    assert summary["exit_shadow"]["exit_t10_h5_avg"] == 10.0


def test_resolve_pending_exit_shadow_waits_for_five_sessions(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    row = {
        "ticker": "123456.KQ",
        "trade_date": "20260601",
        "entry_reference_price": 1000.0,
        "touch3d_t5": None,
    }
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
    monkeypatch.setattr(guard, "LEDGER", ledger)
    monkeypatch.setattr(guard, "normalize_kis_daily_bars", lambda code, payload: _future_frame())

    # age 6 days: 3d resolves, 5d exit shadow must NOT (needs age>=9)
    summary = guard.resolve_pending(_FakeClient(), today_trade_date="20260607")

    saved = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines()]
    out = saved[0]
    assert out["touch3d_t5"] is not None
    assert "exit_t5_h5" not in out or out["exit_t5_h5"] is None
    assert "exit_shadow" not in summary


def test_market_drawdown_state_flags_risk_off():
    from multi_agent.tools.report_kospi_intraday_swing import market_drawdown_state

    idx = pd.bdate_range("2026-05-01", periods=40)
    # two synthetic stocks: flat for 30 days then -1.5%/day for 10 days -> dd20 < -5, ret5 < -3
    rets = [0.0] * 30 + [-1.5] * 10
    px = pd.DataFrame(
        {
            "date": list(idx) * 2,
            "market": ["KOSDAQ"] * 80,
            "liq": [50e8] * 80,
            "ret_1d": rets * 2,
        }
    )
    st = market_drawdown_state("KOSDAQ", px=px)
    assert st["mkt_state"] == "RISK_OFF"
    assert st["mkt_dd20"] < -5.0
    assert st["mkt_ret5"] < -3.0

    # flat market -> NORMAL
    px_flat = px.copy()
    px_flat["ret_1d"] = 0.1
    st2 = market_drawdown_state("KOSDAQ", px=px_flat)
    assert st2["mkt_state"] == "NORMAL"


def test_selective_shadow_view_rank1_and_tiers(tmp_path, monkeypatch):
    import multi_agent.tools.report_kr_selective_shadow as sel

    ledger = tmp_path / "led.jsonl"
    rows = [
        {"date": "2026-06-01", "ticker": "A.KS", "p": 0.9, "exit_t5_h5": 5.0},
        {"date": "2026-06-01", "ticker": "B.KS", "p": 0.5, "exit_t5_h5": -3.0},
        {"date": "2026-06-02", "ticker": "C.KS", "p": 0.4, "exit_t5_h5": -2.0},
    ]
    ledger.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    monkeypatch.setitem(sel.LANES, "KOSPI", {"ledger": ledger, "exit_key": "exit_t5_h5",
                                             "quantile": 0.2, "window": 40, "min_history": 15,
                                             "fallback_threshold": 0.65, "date_key": "date"})
    lv = sel.lane_view("KOSPI")
    assert lv["picks_total_days"] == 2
    # rank-1 on 06-01 is A (p 0.9, PRIMARY, +5); 06-02 is C (CANDIDATE, -2)
    assert lv["rank1_all"]["n"] == 2 and lv["rank1_all"]["ev_avg"] == 1.5
    assert lv["rank1_primary"]["n"] == 1 and lv["rank1_primary"]["ev_avg"] == 5.0
    tiers = {x["date"]: x["tier"] for x in lv["latest"]}
    assert tiers["2026-06-01"] == "PRIMARY" and tiers["2026-06-02"] == "CANDIDATE"


def test_swing_candidate_resolution_touch_and_entry(tmp_path, monkeypatch):
    import sys, types
    import multi_agent.tools.report_kr_swing_candidate as swc

    idx = pd.bdate_range("2026-06-02", periods=7)  # sessions after a 06-01 signal
    frame = pd.DataFrame(
        {
            "Open": [1000, 1010, 1020, 990, 980, 970, 960],
            "High": [1030, 1040, 1060, 1000, 990, 980, 970],
            "Low": [990, 1000, 1010, 960, 950, 940, 930],
            "Close": [1010, 1030, 1040, 980, 960, 950, 940],
        },
        index=idx,
    )
    fake = types.SimpleNamespace(DataReader=lambda code, start: frame)
    monkeypatch.setitem(sys.modules, "FinanceDataReader", fake)
    ledger = tmp_path / "cand.jsonl"
    ledger.write_text(json.dumps({"date": "2026-06-01", "ticker": "000001.KS"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(swc, "LEDGER", ledger)

    summary = swc.resolve_pending(pd.Timestamp("2026-06-20"))

    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert row["entry_open"] == 1000.0          # next-open entry
    assert row["ft_touch5"] == 1                # day3 high 1060 >= 1050
    assert row["policy_ret"] == 5.0             # fill max(1050, open 1020) = 1050
    assert summary["resolved"] == 1 and summary["touch5_pct"] == 100.0
