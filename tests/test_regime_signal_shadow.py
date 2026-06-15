"""Unit tests for the regime-signal shadow pure helpers (network-free)."""
from multi_agent.tools.report_regime_signal_shadow import tail_tier, rank_and_pick


def test_tail_tier_equal_risk_budget():
    assert tail_tier(-1.0)["tier"] == "A" and tail_tier(-1.0)["position_factor"] == 1.0
    assert tail_tier(-6.0)["tier"] == "B" and tail_tier(-6.0)["position_factor"] == 0.45
    assert tail_tier(-20.0)["tier"] == "C" and tail_tier(-20.0)["position_factor"] == 0.40
    assert tail_tier(None)["tier"] == "UNKNOWN"


def test_rank_and_pick_top_n_per_market_and_sizes():
    scored = [
        {"ok": True, "ticker": "A.KS", "market": "KOSPI", "regime": "up", "factor": "ma60_dist", "score": 10.0, "ma60_dist": 10.0, "dist_hi20": -1.0},
        {"ok": True, "ticker": "B.KS", "market": "KOSPI", "regime": "up", "factor": "ma60_dist", "score": 30.0, "ma60_dist": 30.0, "dist_hi20": -12.0},
        {"ok": True, "ticker": "C.KS", "market": "KOSPI", "regime": "up", "factor": "ma60_dist", "score": 5.0, "ma60_dist": 5.0, "dist_hi20": -2.0},
        {"ok": True, "ticker": "D.KQ", "market": "KOSDAQ", "regime": "down_chop", "factor": "dist_hi20_oversold", "score": 8.0, "ma60_dist": -5.0, "dist_hi20": -8.0},
        {"ok": False, "ticker": "E.KS", "market": "KOSPI", "score": None},
    ]
    picks = rank_and_pick(scored, top_picks=2)
    kospi = [p for p in picks if p["market"] == "KOSPI"]
    # top-2 KOSPI by score = B(30) then A(10); C(5) dropped
    assert [p["ticker"] for p in kospi] == ["B.KS", "A.KS"]
    # B is deep-pullback -> tier C size 0.40; A is near-high -> tier A size 1.0
    b = next(p for p in picks if p["ticker"] == "B.KS")
    a = next(p for p in picks if p["ticker"] == "A.KS")
    assert b["tier"] == "C" and b["position_factor"] == 0.40
    assert a["tier"] == "A" and a["position_factor"] == 1.0
    # KOSDAQ keeps its own top-N independently
    assert any(p["ticker"] == "D.KQ" for p in picks)


def test_rank_and_pick_empty():
    assert rank_and_pick([], 5) == []
    assert rank_and_pick([{"ok": False}], 5) == []
