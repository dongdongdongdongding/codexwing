import json
from datetime import datetime, timezone

import pandas as pd

from modules.nasdaq_epoch_evidence import current_epoch, current_rows, statistics, contract_groups
from modules import stream_exclusion as se
from web.backend import services as S
from multi_agent.tools import research_reopen_queue as queue


def row(date='2026-09-01', **kwargs):
    return dict({'date': date, 'symbol': 'TEST', 'xq': .8, 'contract_h': 20,
                 'contract_tp': .05, 'policy_ret': 5, 'touch5': 1}, **kwargs)


def test_marker_contract_ambiguity_and_nonfinite_values():
    rows = [row(), row('2026-09-02', xq=None), row('2026-09-03', contract_h=5),
            row('2026-09-04', policy_ret=float('nan')), row('2026-09-05'), row('2026-09-05'),
            row('2026-09-06', policy_ret=True), row('2026-09-07', in_contract=False)]
    out = current_epoch(rows)
    assert out['n'] == 1 and out['issued_picks'] == 3
    assert out['excluded_marked_picks'] == 4
    assert out['fwd_ev'] == 4.75 and out['touch_pct'] == 100
    assert out['publication_block'] is True
    assert out['h10_tp5_probability_verified'] is False
    assert contract_groups(rows)[0]['contract_h'] == 20
    assert len(rows) == 8  # input remains intact


def test_many_winners_do_not_inherit_old_backtest_qualification():
    dates = pd.bdate_range('2026-08-01', periods=35).strftime('%Y-%m-%d').tolist()
    out = current_epoch([row(d) for d in dates], dates)
    assert out['n'] == 35 and out['fwd_ci'][0] > 0
    assert out['confirm_qualified'] is False
    assert 'matching_research_basis_not_validated' in out['publication_block_reason']
    assert 'executable_entry_not_verified' in out['publication_block_reason']


def test_current_epoch_blocks_pooled_confirm_for_web_and_stream(tmp_path, monkeypatch):
    epoch = current_epoch([row()])
    path = tmp_path/'gate.json'
    path.write_text(json.dumps({'generated_at': datetime.now(timezone.utc).isoformat(), 'results': [
        {'lane': 'nasdaq_session_tape', 'verdict': 'CONFIRM', 'n': 100, 'fwd_ev': 20,
         'epoch_scope_required': True, 'current_epochs': {'US': epoch}}]}))
    state = se.load_gate_state(path, use_cache=False)
    status = se.stream_status('nasdaq_swing', market='NASDAQ', gate_state=state)
    assert status['excluded'] is True and status['reason'] == 'publication_block'
    monkeypatch.setattr(se, 'load_gate_state', lambda: state)
    monkeypatch.setattr(S, '_forward_epoch', lambda *a, **k: None)
    shown = S._apply_operator_ev_floor({'market': 'NASDAQ', 'size_pct_total': 2}, 'nasdaq_swing')
    assert shown['forward_n'] == 1 and shown['forward_ev'] == 4.75
    assert shown['operator_verdict'] == 'OBSERVE'
    assert not shown.get('size_pct_total')
    state['lanes']['nasdaq_session_tape']['current_epochs'] = {}
    assert se.stream_status('nasdaq_swing', gate_state=state)['reason'] == 'epoch_evidence_missing'


def test_web_and_reopen_queue_use_current_only(tmp_path, monkeypatch):
    rows = [row(), row('2026-09-02', xq=None, contract_h=5, policy_ret=-30),
            {'date': '2026-07-01', 'policy_ret': .26}, row('2026-09-03', policy_ret=None)]
    folder = tmp_path/'runtime_state/reports/us_research'
    folder.mkdir(parents=True)
    (folder/'nasdaq_session_tape_ledger.jsonl').write_text('\n'.join(map(json.dumps, rows)))
    monkeypatch.setattr(S, 'REPO', str(tmp_path))
    monkeypatch.setattr(S, '_read_ledger', lambda *a, **k: [])
    monkeypatch.setattr(queue, 'PROJECT_ROOT', tmp_path)
    result = S.contract_performance()['lanes']
    assert result['nasdaq_tape']['n'] == 1 and '20거래일' in result['nasdaq_tape']['label']
    assert result['nasdaq_tape_legacy_0']['n'] == 2
    assert result['nasdaq_tape_legacy_0']['win_pct'] == 50  # US cost .25, not .30
    assert queue.QUEUE['nasdaq_tape_verdict_deep']['have']() == 1
    shown = S._forward_epoch('nasdaq_swing', market='NASDAQ')
    assert shown['current']['resolved'] == 1 and shown['previous']['resolved'] == 2


def test_gate_cli_artifact_carries_blocking_current_epoch(tmp_path, monkeypatch):
    from multi_agent.tools import report_research_recursion_gate as gate
    from modules import market_sessions
    monkeypatch.setattr(gate, 'LANES', {'nasdaq_session_tape': {'ledger': tmp_path/'ledger'}})
    monkeypatch.setattr(gate, '_rows', lambda *a: [row()])
    monkeypatch.setattr(gate, '_load_state', lambda: {})
    monkeypatch.setattr(gate, 'evaluate', lambda *a: {
        'lane': 'nasdaq_session_tape', 'verdict': 'CONFIRM', 'verdict_since': '2026-09-01',
        'n': 100, 'expect_ev': .75, 'expect_win': 79.3, 'win_verdict': 'OK', 'note': 'legacy'})
    monkeypatch.setattr(market_sessions, 'price_sessions', lambda *a: (['2026-09-01'], 'fixture'))
    monkeypatch.setattr(gate, 'STATE', tmp_path/'state.json')
    monkeypatch.setattr(gate, 'OUT_JSON', tmp_path/'report.json')
    monkeypatch.setattr(gate, 'OUT_MD', tmp_path/'report.md')
    monkeypatch.setattr('sys.argv', ['gate', '--no-tickets'])
    gate.main()
    result = json.loads(gate.OUT_JSON.read_text())['results'][0]
    assert result['current_epochs']['US']['n'] == 1
    assert result['publication_block'] is True
    assert result['evidence_scope'] == 'legacy_pooled_diagnostic_only'
    state = se.load_gate_state(gate.OUT_JSON, use_cache=False)
    assert se.stream_status('nasdaq_swing', gate_state=state)['excluded'] is True
    assert 'nasdaq_session_tape는 과거 합산 진단' in gate.OUT_MD.read_text()
