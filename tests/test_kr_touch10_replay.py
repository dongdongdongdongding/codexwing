import json
import pandas as pd
import pytest
from research.validate_kr_touch10 import run, metrics


def test_replay_pairs_same_picks_and_does_not_rewrite_ledger(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    dates = pd.bdate_range("2026-08-24", periods=15)
    frames = []
    for code, market in [("000001", "KOSPI"), ("000002", "KOSDAQ"),
                         ("000003", "KOSPI"), ("000004", "KOSDAQ")]:
        p = pd.DataFrame({"code": code, "date": dates, "market": market,
                          "adj_open": 100., "adj_high": 101., "adj_low": 89.,
                          "adj_close": 90., "volume": 1000., "liq": 20e9})
        if code in {"000001", "000002"}:
            p.loc[7, "adj_high"] = 106.  # first touch beyond H5, within H10
        frames.append(p)
    px = pd.concat(frames)
    px.to_parquet(cache / "px_delisted.parquet", index=False)
    px.to_parquet(cache / "px_long.parquet", index=False)
    ledger = tmp_path / "runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl"
    ledger.parent.mkdir(parents=True)
    picks = [{"date": "2026-08-24", "ticker": code+suffix, "market": market,
              "contract_h": horizon, "top_k": k, "fire": True}
             for code, suffix, market, horizon, k in [("000001", ".KS", "KOSPI", 10, 3),
                                                       ("000002", ".KQ", "KOSDAQ", 5, 1)]]
    ledger.write_text("\n".join(json.dumps(p) for p in picks))
    before = ledger.read_bytes()
    spec = {"id": "fixture", "scope": {"signal_start": "2026-08-24", "signal_end": "2026-09-11",
                                       "universe_liq_krw": {"KOSPI": 10e9, "KOSDAQ": 3e9}}}
    r = run(tmp_path, cache, spec)
    assert r["metrics"]["KOSDAQ/baseline"]["touch_rate"] == 0
    assert r["metrics"]["KOSDAQ/candidate_h10"]["touch_rate"] == 1
    assert r["paired_h10_minus_baseline"]["mean_net_delta_pp"] == pytest.approx(7.5)
    assert r["same_day_controls"]["KOSDAQ"]["same_day_net_excess_pp"] == pytest.approx(15)
    assert not r["production_replacement_ready"]
    assert ledger.read_bytes() == before


def test_pending_and_unfilled_are_neither_wins_nor_losses():
    r = metrics([{"status": "pending"}, {"status": "unfilled_entry"}], ["2026-08-24"])
    assert r["selected"] == 2 and r["n"] == 0
    assert r["touch_rate"] is None and r["net_ev_pct"] is None
