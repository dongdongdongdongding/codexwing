"""Regression: pooled healthy verdict must never bypass current swing evidence."""
from copy import deepcopy

import pytest

from conftest import synthetic_gate_entry
from modules import stream_exclusion as se
from modules.swing_epoch_evidence import current_epochs, SPECS
from modules.candidate_interpretation import build_candidate_interpretation
from web.backend import services as S


def state(lane='swing_candidate'):
    return {'usable': True, 'lanes': {lane: synthetic_gate_entry(lane, 'CONFIRM')}}


@pytest.mark.parametrize('key,gate,market', [
    ('kospi_swing', 'swing_candidate', 'KOSPI'),
    ('kosdaq_swing', 'swing_candidate', 'KOSDAQ'),
    ('swing_candidate', 'swing_candidate', 'KOSPI'),
    ('nasdaq_swing', 'nasdaq_session_tape', 'NASDAQ'),
])
@pytest.mark.parametrize('flag', [None, False, True])
def test_pooled_evidence_cannot_opt_out(key, gate, market, flag, monkeypatch):
    report = state(gate)
    report['lanes'][gate].pop('current_epochs')
    if flag is not None:
        report['lanes'][gate]['epoch_scope_required'] = flag
    row = {'market': market, 'size_pct_total': 2, 'buy_ready': True}
    se.apply_stream_exclusion(row, key, gate_state=report)
    assert row['stream_exclusion_reason'] == 'epoch_evidence_missing'
    assert row['buy_ready'] is False and 'size_pct_total' not in row
    monkeypatch.setattr(se, 'load_gate_state', lambda *a, **k: report)
    monkeypatch.setattr(S, '_lane_forward_ev', lambda: {gate: (99, 99, 1000)})
    shown = S._apply_operator_ev_floor({'market': market, 'size_pct_total': 2}, key)
    assert shown['operator_verdict'] == 'UNKNOWN'
    assert 'size_pct_total' not in shown and 'forward_ev' not in shown
    if key == 'swing_candidate':
        interp = build_candidate_interpretation({'decision_bucket': key, 'market': market,
            'ticker': '005930.KS', 'prediction': {'phase25_prob': .99},
            'contract_h': 10, 'contract_tp': .05, 'price': {'close': 71000}})
        assert interp['buy_ready'] is False
        assert interp['operational_action_level'] == 'OBSERVE_ONLY'


@pytest.mark.parametrize('epochs', [None, [], 'bad', {}, {'KOSPI': []}])
def test_malformed_epoch_container_fails_closed(epochs):
    report = state()
    report['lanes']['swing_candidate']['current_epochs'] = epochs
    assert se.stream_status('kospi_swing', gate_state=report)['excluded'] is True


@pytest.mark.parametrize('field,value', [('market', 'KOSDAQ'), ('contract_h', 5),
    ('contract_tp', .1), ('top_k', 1), ('gate_q', .5), ('gate_kind', 'other')])
def test_wrong_scope_cannot_confer_qualification(field, value):
    report = state()
    report['lanes']['swing_candidate']['current_epochs']['KOSPI']['scope'][field] = value
    assert se.stream_status('kospi_swing', gate_state=report)['reason'] == 'epoch_scope_mismatch'


@pytest.mark.parametrize('field,value', [('confirm_qualified', None), ('confirm_qualified', False),
    ('confirm_qualified', 'true'), ('confirm_qualified', 1), ('publication_block', None),
    ('publication_block', 0), ('publication_block', 'false')])
def test_missing_or_coerced_qualification_never_opens(field, value):
    report = state()
    report['lanes']['swing_candidate']['current_epochs']['KOSPI'][field] = value
    assert se.stream_status('kospi_swing', gate_state=report)['reason'] == 'epoch_qualification_missing'


def test_web_lane_cannot_override_conflicting_row_market():
    assert se.stream_status('kospi_swing', gate_state=state(), market='KOSDAQ')['reason'] == 'epoch_scope_mismatch'


def test_scope_diagnostic_does_not_inherit_other_tp_rows():
    row = {**SPECS['KOSPI'], 'market': 'KOSPI', 'date': '2026-09-01', 'policy_ret': 5}
    result = current_epochs([row, {**row, 'contract_tp': .1}], ['2026-09-01'])['KOSPI']
    assert result['issued_picks'] == 1 and result['n'] == 1
    assert result['publication_block'] is True


def test_real_current_evidence_remains_blocked_when_flag_removed():
    report = state()
    report['lanes']['swing_candidate']['current_epochs'] = current_epochs([], [])
    before = deepcopy(report)
    assert se.stream_status('kospi_swing', gate_state=report)['reason'] == 'publication_block'
    assert report == before
