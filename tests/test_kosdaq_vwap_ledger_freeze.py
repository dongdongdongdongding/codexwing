import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from multi_agent.tools import report_kosdaq_intraday_vwap_guard as m


def pick(ticker="144960.KQ", day="20260626", p=.9):
    return {"ticker":ticker,"base_trade_date":day,"candidate_id":m.CANDIDATE_ID,
            "p":p,"priority_rank":1,"target_tp_pct":5.,"hold_days":3,
            "decision":"KOSDAQ_INTRADAY_3D_T5_BUY","decision_bucket":"kosdaq_intraday_3d_t5_vwap_guard"}


@pytest.fixture
def ledger(tmp_path,monkeypatch):
    path=tmp_path/"ledger.jsonl"
    monkeypatch.setattr(m,"LEDGER",path)
    monkeypatch.setenv("AG_KOSDAQ_INTRADAY_TOP_N","1")
    return path


def test_rescore_preserves_score_contract_timestamp_and_settlement_bytes(ledger):
    m.record_picks([pick()],generated_at="2026-06-26T06:00:00+00:00")
    row=m._ledger_rows()[0];row.update(ret3d=20.7,touch3d_t5=1,resolved_at="2026-06-30",exit_t10_h5=10.)
    m._write_ledger_rows([row]);before=ledger.read_bytes()
    assert m.record_picks([{**pick(p=.2),"hold_days":5,"target_tp_pct":10}],generated_at="2026-07-01T00:00:00+00:00")==0
    assert ledger.read_bytes()==before


def test_rescore_cannot_append_new_tickers_to_recorded_day(ledger,monkeypatch):
    monkeypatch.setenv("AG_KOSDAQ_INTRADAY_TOP_N","2")
    assert m.record_picks([pick("A"),pick("B")],generated_at="first")==2
    before=ledger.read_bytes()
    assert m.record_picks([pick("C")],generated_at="later")==0
    assert ledger.read_bytes()==before
    assert m.record_picks([pick("D","20260629")],generated_at="newday")==1
    assert [r["ticker"] for r in m.frozen_day_picks("20260626")]==["A","B"]


def test_duplicate_incoming_keys_and_quota_do_not_inflate_ledger(ledger):
    assert m.record_picks([pick(),pick(),pick("NEW")],generated_at="first")==1
    assert len(m._ledger_rows())==1


def test_malformed_ledger_is_not_silently_rewritten(ledger):
    ledger.write_text('{"ticker": "A"}\nbroken\n');before=ledger.read_bytes()
    with pytest.raises(ValueError):m.record_picks([pick()],generated_at="new")
    assert ledger.read_bytes()==before


def test_failed_atomic_replace_keeps_original_and_cleans_temp(ledger,monkeypatch):
    m.record_picks([pick()],generated_at="first");before=ledger.read_bytes()
    def fail(*a):raise OSError("replace failed")
    monkeypatch.setattr(m.os,"replace",fail)
    with pytest.raises(OSError):m.record_picks([pick(day="20260629")],generated_at="second")
    assert ledger.read_bytes()==before
    assert sorted(p.name for p in ledger.parent.iterdir())==["ledger.jsonl","ledger.lock"]


def test_two_processes_freeze_one_day_without_lost_update(ledger):
    source="""import sys,json
from pathlib import Path
from multi_agent.tools import report_kosdaq_intraday_vwap_guard as m
m.LEDGER=Path(sys.argv[1])
m.record_picks([json.loads(sys.argv[2])],generated_at='first')
"""
    env={**os.environ,"PYTHONPATH":str(Path(m.__file__).resolve().parents[2])}
    processes=[subprocess.Popen([sys.executable,"-c",source,str(ledger),json.dumps(pick(ticker))],env=env,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for ticker in ["A","B"]]
    for p in processes:
        stdout,stderr=p.communicate(timeout=30)
        assert p.returncode==0,stderr
    rows=m._ledger_rows();assert len(rows)==1 and rows[0]["ticker"] in {"A","B"}


def test_main_report_and_routing_use_frozen_values(ledger,monkeypatch):
    m.record_picks([pick()],generated_at="2026-06-26T06:00:00+00:00")
    expected=m._ledger_rows();captured={}
    monkeypatch.setattr(m.sys,"argv",["report"])
    monkeypatch.setenv("AG_KOSDAQ_INTRADAY_PRODUCTION","1")
    monkeypatch.setattr(m,"_trade_date_arg",lambda _:"20260626")
    monkeypatch.setattr(m.joblib,"load",lambda _: {})
    from modules import kis_openapi
    monkeypatch.setattr(kis_openapi.KISConfig,"from_env",lambda:None)
    monkeypatch.setattr(kis_openapi,"KISOpenAPIClient",lambda *_:SimpleNamespace(get_access_token=lambda:None))
    monkeypatch.setattr(m,"score_live_candidates",lambda **kw:{"picks":[pick("NEW",p=.99)],"run_id":"R","trade_date":"20260626"})
    from multi_agent.tools import report_kospi_intraday_swing as kp
    monkeypatch.setattr(kp,"market_drawdown_state",lambda _: {"mkt_state":"NEW_STATE"})
    monkeypatch.setattr(m,"resolve_pending",lambda *a,**k:{"resolved":0})
    def route(rows,**kw):captured["routed"]=rows;return len(rows)
    monkeypatch.setattr(m,"route_live_intraday",route)
    monkeypatch.setattr(m,"_write_report",lambda report:captured.update(report=report))
    assert m.main()==0
    assert captured["routed"]==captured["report"]["picks"]==expected
    assert captured["report"]["rescored_picks"][0]["ticker"]=="NEW"
    assert captured["report"]["ledger_recorded"]==0


def test_route_preserves_per_pick_original_timestamp_and_rank(monkeypatch):
    from modules import db_manager,candidate_interpretation,top_deep_report
    payloads=[];reports=[]
    monkeypatch.setattr(db_manager,"DBManager",lambda:SimpleNamespace(upsert_scan_result=lambda p,**kw:payloads.append(p)))
    monkeypatch.setattr(candidate_interpretation,"build_candidate_interpretation",lambda row:{})
    def deep(rows):reports.extend(rows);return {"rows_upserted":len(rows)}
    monkeypatch.setattr(top_deep_report,"upsert_reports_to_supabase",deep)
    original="2026-06-26T06:00:00+00:00"
    p={**pick(),"generated_at":original,"priority_rank":2,"ordered_entry_at":"2026-06-26T14:59:00"}
    assert m.route_live_intraday([p],run_id="R",recommended_at="2026-10-07T00:00:00+00:00")==1
    assert payloads[0]["recommended_at"]==payloads[0]["created_at"]==original
    assert reports[0]["generated_at"]==original and reports[0]["rank"]==2
    assert reports[0]["trade_plan"]["hold_days"]==3

    assert payloads[0]["ordered_entry_at"]=="2026-06-26T14:59:00+09:00"
    assert p["ordered_entry_at"]=="2026-06-26T14:59:00"
