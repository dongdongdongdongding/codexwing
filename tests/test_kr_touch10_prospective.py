from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import pandas as pd
import pytest

from multi_agent.tools.observe_kr_touch10_prospective import capture, evaluate


def spec():
    s = json.loads((Path(__file__).resolve().parents[1]/"research/prereg_kr_touch10_prospective_20261007.json").read_text())
    s["registered_at"] = "2026-10-06T16:00:00+00:00"
    return s


def fixture():
    s = spec()
    gate = {m:{"gate_kind":v["gate_kind"],"gate_q":v["gate_q"],"fire":False} for m,v in s["selection"].items()}
    report = {"as_of":"2026-10-07","generated_at":"2026-10-07T16:00:00+09:00","gate":gate,"picks":[]}
    panel = pd.DataFrame([{"date":pd.Timestamp("2026-10-07"),"code":c,"market":m,"liq":2e10,"volume":10}
                          for m,c in [("KOSPI","111111"),("KOSDAQ","222222")]])
    return s,report,panel


def test_abstention_is_frozen_as_a_real_zero_pick_day():
    s,r,p = fixture()
    out = capture(r,[],p,s,datetime.fromisoformat("2026-10-07T20:00:00+09:00"))
    assert out["picks"] == []
    assert set(out["universe"]) == {"KOSPI","KOSDAQ"}


def test_pre_entry_deadline_rejects_historical_backfill():
    s,r,p = fixture()
    with pytest.raises(ValueError,match="capture_window"):
        capture(r,[],p,s,datetime.fromisoformat("2026-10-08T09:00:00+09:00"))
    r["generated_at"] = "2026-10-07T15:00:00+09:00"
    with pytest.raises(ValueError,match="capture_window"):
        capture(r,[],p,s,datetime.fromisoformat("2026-10-07T20:00:00+09:00"))


def test_selection_drift_missing_universe_and_known_outcome_fail_closed():
    s,r,p = fixture()
    bad = deepcopy(r); bad["gate"]["KOSPI"]["gate_q"] = .6
    now = datetime.fromisoformat("2026-10-07T20:00:00+09:00")
    with pytest.raises(ValueError,match="gate_changed"):
        capture(bad,[],p,s,now)
    with pytest.raises(ValueError,match="universe"):
        capture(r,[],p.iloc[:1],s,now)
    pick = {"date":"2026-10-07","market":"KOSPI","ticker":"111111.KS",
            "top_k":3,"in_contract":True,"logged_at":"2026-10-07T16:00:00+09:00","policy_ret":5}
    r["picks"] = [pick]; r["gate"]["KOSPI"]["fire"] = True
    with pytest.raises(ValueError,match="outcome_already"):
        capture(r,[pick],p,s,now)


def test_valid_original_pick_is_captured_under_new_h10_contract():
    s,r,p = fixture()
    pick = {"date":"2026-10-07","market":"KOSDAQ","ticker":"222222.KQ","p":.8,"close":100.,
            "top_k":1,"rank":1,"in_contract":True,"contract_h":5,"input_sig":"frozen-input",
            "label_max_date":"2026-09-25","gate_kind":"mkt_weakness","gate_q":.5,
            "logged_at":"2026-10-07T16:00:00+09:00","policy_ret":None}
    r["picks"] = [pick]; r["gate"]["KOSDAQ"]["fire"] = True
    out = capture(r,[pick],p,s,datetime.fromisoformat("2026-10-07T20:00:00+09:00"))
    assert out["contract"]["horizon_sessions"] == 10
    assert out["picks"][0]["p"] == .8
    assert pick["contract_h"] == 5  # the original ledger remains untouched
    r["gate"]["KOSPI"].pop("fire")
    with pytest.raises(ValueError,match="missing_gate_fire"):
        capture(r,[pick],p,s,datetime.fromisoformat("2026-10-07T20:00:00+09:00"))


def synthetic():
    s = spec(); s["evaluation_sessions"] = 10; s["horizon_sessions"] = 2
    s["targets"]["min_resolved"] = 1; s["targets"]["min_unique_resolved_dates"] = 1
    days = pd.bdate_range("2026-10-07",periods=12).strftime("%Y-%m-%d").tolist()
    snapshots=[]
    for i,d in enumerate(days[:10]):
        picks = [{"date":d,"market":m,"ticker":c+suffix} for m,c,suffix in
                 [("KOSPI","111111",".KS"),("KOSDAQ","222222",".KQ")]] if i%2 == 0 else []
        snapshots.append({"date":d,"picks":picks,"universe":{"KOSPI":["111111","333333"],"KOSDAQ":["222222","444444"]}})
    prices = pd.DataFrame([{"code":c,"date":pd.Timestamp(d),"adj_open":100.,"adj_high":106. if c in ["111111","222222"] else 100.,
                           "adj_close":100.,"volume":10.} for c in ["111111","222222","333333","444444"] for d in days])
    return s,days,snapshots,prices


def test_fixed_window_prevents_early_promotion_and_pass_still_needs_gate_review():
    s,days,snaps,prices = synthetic()
    early = evaluate(snaps[:5],prices[prices.date <= pd.Timestamp(days[4])],days[:5],s)
    assert early["decision"] == "PENDING_FIXED_WINDOW"
    assert early["publication_allowed"] is False
    final = evaluate(snaps,prices,days,s)
    assert final["decision"] == "VALIDATION_PASSED_PENDING_GATE_REVIEW", final["failures"]
    assert final["publication_allowed"] is False
    assert final["firing_dates_per_five_sessions"] == 2.5
    assert final["controls"]["KOSPI"]["timing_diagnostic"]["rotations"] == 9


def test_missing_capture_is_not_counted_as_abstention_or_ignored():
    s,days,snaps,prices = synthetic()
    out = evaluate(snaps[1:],prices,days,s)
    assert out["decision"] == "REJECT"
    assert out["missing_capture_dates"] == [days[0]]
    assert "missing_capture_days" in out["failures"]


def test_missing_peer_price_prevents_clean_alpha_claim():
    s,days,snaps,prices = synthetic()
    out = evaluate(snaps,prices[prices.code != "333333"],days,s)
    assert out["decision"] == "REJECT"
    assert out["control_status_counts"]["data_error"] > 0


def cadence_spec():
    path=Path(__file__).resolve().parents[1]/'research/prereg_kr_touch10_cadence_20261007.json'
    return json.loads(path.read_text())


def test_rolling_cadence_caps_three_dates_without_looking_at_outcomes():
    from multi_agent.tools.observe_kr_touch10_prospective import apply_cadence,validate_cadence
    s=cadence_spec()
    days=pd.bdate_range('2026-10-07',periods=15).strftime('%Y-%m-%d').tolist()
    frozen=[]
    for day in days:
        source=[{'date':day,'market':m,'ticker':t,'p':.1} for m,t in [('KOSPI','111111.KS'),('KOSDAQ','222222.KQ')]]
        snap=apply_cadence({'date':day,'picks':source},frozen,days,s)
        assert snap['source_picks']==source
        frozen.append(snap)
    fired=[bool(snap['picks']) for snap in frozen]
    assert fired==[True,True,True,False,False]*3
    assert all(sum(fired[i:i+5])<=3 for i in range(len(fired)-4))
    assert sum(fired)*5/len(fired)==3
    validate_cadence(frozen,days,s)
    bad=deepcopy(frozen);bad[3]['picks']=bad[3]['source_picks']
    with pytest.raises(ValueError,match='inconsistent'):validate_cadence(bad,days,s)


def test_cadence_missing_history_is_not_abstention_and_empty_day_uses_no_quota():
    from multi_agent.tools.observe_kr_touch10_prospective import apply_cadence
    s=cadence_spec();days=['2026-10-07','2026-10-08','2026-10-12']
    with pytest.raises(ValueError,match='missing_prior'):
        apply_cadence({'date':days[-1],'picks':[{'ticker':'111111.KS'}]},[],days,s)
    prior=[]
    for d in days[:2]:prior.append(apply_cadence({'date':d,'picks':[]},prior,days,s))
    last=apply_cadence({'date':days[-1],'picks':[{'ticker':'111111.KS'}]},prior,days,s)
    assert last['cadence_decision']['preceding_firing_dates']==0
    assert len(last['picks'])==1


def test_cadence_below_two_dates_fails_instead_of_forcing_picks():
    from multi_agent.tools.observe_kr_touch10_prospective import apply_cadence
    s,days,snaps,prices=synthetic()
    s.update(cadence=cadence_spec()['cadence'],multiple_testing=cadence_spec()['multiple_testing'])
    frozen=[]
    for snap in snaps:
        # One eligible date across ten sessions; no synthetic filler picks.
        if snap['date']!=days[0]:snap['picks']=[]
        frozen.append(apply_cadence(snap,frozen,days,s))
    out=evaluate(frozen,prices,days,s)
    assert out['firing_dates_per_five_sessions']==.5
    assert 'frequency_outside_target' in out['failures']
    assert out['publication_allowed'] is False
    assert 0 in out['calendar_week_firing_dates'].values()
    for control in out['controls'].values():
        assert control['family_adjusted_random_ticker_p_ge']==min(1.,2*control['random_ticker_p_ge'])
