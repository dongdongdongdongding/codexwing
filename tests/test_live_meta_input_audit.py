from research.audit_live_meta_inputs import declared_contract, entry_timing, classify, summarize


def test_legacy_text_is_separate_from_missing_numeric_metadata():
    c=declared_contract({"contract":"buy next open; +5% touch exit within 5 sessions else 5d close"})
    assert c=={"horizon":5.,"tp_pct":5.,"conflict":False}


def test_conflicting_contracts_are_not_resolved_by_preference():
    c=declared_contract({"contract_h":10,"contract_tp":.05,"contract":"+5% touch within 5 sessions"})
    assert c["conflict"] and c["horizon"] is None


def test_shadow_h5_tp10_label_does_not_become_issued_h3_tp5():
    r=classify({"date":"2026-06-26","ticker":"A","hold_days":3,"target_tp_pct":5,
                "exit_t10_h5":10.,"p":.9},"kosdaq_intraday_vwap","exit_t10_h5",[],set())
    assert r["settled_by_old_harness_field"]
    assert r["old_harness_label_alignment"]=="shadow_label_differs_from_declared_contract"
    assert not r["declared_tp5_h10"]


def test_nonfinite_and_boolean_returns_are_not_settled():
    for value in [True,float("nan"),float("inf"),"5.0",None]:
        r=classify({"policy_ret":value},"kr_swing_candidate","policy_ret",[],set())
        assert not r["settled_by_old_harness_field"]


def test_kr_timestamp_uses_next_observed_session_not_next_calendar_day():
    row={"date":"2026-09-23","logged_at":"2026-09-27T22:00:00+00:00"}
    sessions=["2026-09-23","2026-09-28"]
    assert entry_timing(row,"kr_swing_candidate",sessions)=="recorded_before_entry"
    row["logged_at"]="2026-09-28T00:00:01+00:00"
    assert entry_timing(row,"kr_swing_candidate",sessions)=="recorded_after_entry"
    row["logged_at"]="2026-09-28T00:00:00"
    assert entry_timing(row,"kr_swing_candidate",sessions)=="missing_aware_creation_timestamp"


def test_kosdaq_late_generation_is_not_pick_time_proof():
    row={"date":"2026-09-23","ordered_entry_at":"2026-09-23T15:00:00",
         "generated_at":"2026-09-28T05:36:57.109171+00:00"}
    assert entry_timing(row,"kosdaq_intraday_vwap",[])=="recorded_after_entry"


def test_counts_separate_contract_declared_settlement_and_creation_time():
    rows=[]
    for horizon,when in [(5,"2026-09-23T10:00:00+00:00"),(10,"2026-09-23T10:00:00+00:00"),
                         (10,"2026-09-28T01:00:00+00:00")]:
        rows.append(classify({"date":"2026-09-23","ticker":"A","market":"KOSPI",
                              "contract_h":horizon,"contract_tp":.05,"logged_at":when,"policy_ret":5.},
                             "kr_swing_candidate","policy_ret",["2026-09-23","2026-09-28"],set()))
    s=summarize(rows)
    assert s["settled"]==3 and s["settled_declared_tp5_h10"]==2
    assert s["timely_recorded_declared_tp5_h10"]==1
    assert s["timely_recorded_declared_tp5_h10_with_input_signature"]==0
