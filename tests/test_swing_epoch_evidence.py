import json
from datetime import datetime, timezone

import pandas as pd

from modules.swing_epoch_evidence import current_epochs, SPECS
from modules import stream_exclusion as se
import web.backend.services as S


def test_exact_issued_configuration_excludes_legacy_other_market_and_ambiguous_day():
    days = pd.bdate_range("2026-08-24", periods=25).strftime("%Y-%m-%d").tolist()
    rows = [{**SPECS["KOSPI"], "market":"KOSPI", "date":d, "policy_ret":5} for d in days]
    rows += [{"market":"KOSPI", "date":days[0], "policy_ret":-99, "contract_h":10}]
    rows += [{**SPECS["KOSDAQ"], "market":"KOSDAQ", "date":d, "policy_ret":-5} for d in days]
    rows += [{**rows[0]} for _ in range(3)]
    out = current_epochs(rows, days)
    assert out["KOSPI"]["n"] == 24
    assert out["KOSPI"]["unique_dates"] == 24
    assert out["KOSPI"]["excluded_ambiguous_picks"] == 4
    assert out["KOSPI"]["fwd_ev"] > 4
    assert out["KOSDAQ"]["fwd_ev"] < -5
    assert out["KOSPI"]["publication_block"] is True
    assert "matching_research_basis_not_validated" in out["KOSPI"]["publication_block_reason"]


def gate_file(tmp_path):
    epochs = current_epochs([{**SPECS["KOSPI"], "market":"KOSPI", "date":"2026-08-24", "policy_ret":5}],
                            ["2026-08-24"])
    path = tmp_path/"gate.json"
    path.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(), "results":[{
        "lane":"swing_candidate", "verdict":"CONFIRM", "n":300, "fwd_ev":-.5,
        "epoch_scope_required":True, "current_epochs":epochs}]}))
    return path


def test_current_epoch_block_overrides_pooled_confirm_in_both_consumers(tmp_path, monkeypatch):
    path = gate_file(tmp_path)
    state = se.load_gate_state(path, use_cache=False)
    for key in ["kospi_swing", "swing_candidate"]:
        row = se.apply_stream_exclusion({"market":"KOSPI", "buy_ready":True,"size_pct_total":2},key,gate_state=state)
        assert row["stream_excluded"] is True
        assert row["stream_exclusion_reason"] == "publication_block"
        assert row["buy_ready"] is False
    monkeypatch.setattr(se,"load_gate_state",lambda:state)
    monkeypatch.setattr(S,"_forward_epoch",lambda *a,**k:None)
    row = S._apply_operator_ev_floor({"market":"KOSPI"},"kospi_swing")
    assert row["operator_verdict"] == "OBSERVE"
    assert row["forward_ev"] > 4
    assert row["forward_n"] == 1


def test_missing_market_or_epoch_does_not_inherit_pooled_confirm(tmp_path):
    state = se.load_gate_state(gate_file(tmp_path),use_cache=False)
    assert se.stream_status("swing_candidate",gate_state=state)["excluded"] is True
    state["lanes"]["swing_candidate"]["current_epochs"] = {}
    assert se.stream_status("kospi_swing",gate_state=state)["reason"] == "epoch_evidence_missing"


def test_nonfinite_returns_do_not_inflate_sample():
    rows = [{**SPECS["KOSPI"], "market":"KOSPI", "date":"2026-08-24", "policy_ret":float("nan")}]
    assert current_epochs(rows,["2026-08-24"])["KOSPI"]["n"] == 0
