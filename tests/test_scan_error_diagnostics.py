import json
from types import SimpleNamespace

import pytest

from modules import scanner_runtime as runtime
from modules.scan_error_diagnostics import record_scan_error, safe_error_message, scan_error_detail
from modules.scan_persistence import persist_scan_run_artifacts
from multi_agent.storage.memory_layers import MemoryManager


def call_worker():
    return runtime.scan_symbol_with_retry(
        'IOND', tickers_dict={'IOND': 'test'}, is_us=True, is_amex=False,
        is_advanced_engine=False, r_status='NORMAL', intel_data=None, macro_ctx=None,
        market_gate={}, rank_adjustment_fn=lambda **kw: 0,
        news_adjustment_fn=lambda **kw: {}, backoff_state=runtime.SharedBackoffState(),
        max_retries=0, run_id='RUN-ERROR-TEST',
    )


def test_actual_worker_failure_survives_parallel_collection_and_disk(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv('TEST_API_KEY', 'configured-secret-123')
    def fail_fetch(**kw):
        raise ValueError('bad quote configured-secret-123 https://provider.test/?token=url-secret')
    monkeypatch.setattr(runtime.quant_analysis, 'QuantStrategy', lambda *a, **k: SimpleNamespace(fetch_data=fail_fetch))
    diagnostics = {}
    def on_item(i, n, sym, data, exc):
        if exc is not None or data and 'error' in data:
            record_scan_error(diagnostics, sym, data=data, exc=exc)
    result = runtime.run_parallel_scan(ticker_list=['IOND'], max_scan=1, worker_fn=lambda _: call_worker(), on_item=on_item)
    assert result == {'results': [], 'total_scans': 1, 'error_count': 1}
    assert diagnostics['worker_error_count'] == 1
    monkeypatch.setenv('AG_SCAN_UNIVERSE_SNAPSHOT_WRITE_DB', '0')
    persist_scan_run_artifacts(run_id='RUN-ERROR-TEST', market='NASDAQ', scan_mode='SWING',
        results=result['results'], total_scans=1, diagnostics=diagnostics,
        bridge_info={}, top_deep_reports={}, memory=MemoryManager(tmp_path))
    raw = (tmp_path/'artifacts/RUN-ERROR-TEST/raw_scan_results.json').read_text()
    saved = json.loads(raw)['diagnostics']['errors_by_symbol']['IOND'][0]
    assert saved['error_type'] == 'ValueError' and saved['attempts'] == 1
    assert saved['stage'] == 'worker'
    assert saved['frames'][-1]['function'] == 'fail_fetch'
    assert set(saved['frames'][-1]) == {'file', 'line', 'function'}
    output = capsys.readouterr().out
    for secret in ['configured-secret-123', 'url-secret']:
        assert secret not in raw + output


def test_executor_exception_keeps_distinct_count_and_success():
    diagnostics = {}
    def worker(sym):
        if sym == 'FAIL':
            raise KeyError('missing Close')
        return {'ticker': sym}
    def on_item(i, n, sym, data, exc):
        if exc:
            record_scan_error(diagnostics, sym, exc=exc)
    result = runtime.run_parallel_scan(ticker_list=['GOOD', 'FAIL'], max_scan=2, worker_fn=worker, on_item=on_item)
    assert result['results'] == [{'ticker': 'GOOD'}] and result['error_count'] == 1
    assert diagnostics['executor_exception_count'] == 1 and diagnostics.get('worker_error_count', 0) == 0
    assert diagnostics['errors_by_symbol']['FAIL'][0]['error_type'] == 'KeyError'


def test_rate_limit_exhaustion_keeps_attempt_count(monkeypatch):
    def fail(*a, **kw):
        raise runtime.quant_analysis.RateLimitError('quota exceeded')
    monkeypatch.setattr(runtime.quant_analysis, 'QuantStrategy', fail)
    data = call_worker()
    assert data['error'] == 'RATE_LIMIT_EXHAUSTED'
    assert data['error_detail']['error_type'] == 'RateLimitError'
    assert data['error_detail']['attempts'] == 1


@pytest.mark.parametrize('message,secret', [
    ('Authorization: Bearer abcdefghijk', 'abcdefghijk'),
    ('api_key="secret with spaces"', 'secret with spaces'),
    ("{'appsecret': 'private-value'}", 'private-value'),
    ('request https://a.test/path?token=foo', 'token=foo'),
])
def test_credentials_redacted(message, secret):
    assert secret not in safe_error_message(message)


def test_legacy_payload_and_bounded_json_message():
    diagnostics = {}
    detail = record_scan_error(diagnostics, 'OLD', data={'error': 'x' * 5000})
    assert detail['error_type'] == 'WorkerError' and len(detail['message']) == 1000
    assert json.loads(json.dumps(diagnostics)) == diagnostics
