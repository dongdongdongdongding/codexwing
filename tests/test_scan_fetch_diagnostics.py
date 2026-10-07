from types import SimpleNamespace

import pandas as pd
import pytest

from modules import quant_analysis, scanner_runtime
from modules.scan_fetch_diagnostics import history_diagnostic, summarize_fetch_rejections
from multi_agent.tools.run_us_full_universe_research import summarize_health


def frame(rows):
    return pd.DataFrame({c:[10.]*rows for c in ['Open','High','Low','Close','Volume']},
                        index=pd.date_range('2026-01-01', periods=rows))


@pytest.mark.parametrize('rows,status', [(0,'empty'),(49,'insufficient_history'),(50,'usable')])
def test_fetch_preserves_fifty_complete_row_boundary(monkeypatch, rows, status):
    monkeypatch.setattr(quant_analysis, 'get_history', lambda *a,**k:frame(rows))
    monkeypatch.setattr(quant_analysis, 'live_mode_enabled', lambda *a:False)
    qs=quant_analysis.QuantStrategy('TEST')
    monkeypatch.setattr(qs, 'get_intraday_volume_multiplier', lambda **k:1.)
    assert qs.fetch_data(period='5y') is (rows==50)
    assert qs.fetch_diagnostic['status']==status
    assert qs.fetch_diagnostic['valid_rows']==rows


def test_minimum_applies_after_null_row_removal(monkeypatch):
    df=frame(50);df.loc[df.index[-1],'Close']=float('nan')
    monkeypatch.setattr(quant_analysis, 'get_history', lambda *a,**k:df.copy())
    qs=quant_analysis.QuantStrategy('TEST')
    assert qs.fetch_data(period='5y') is False
    assert qs.fetch_diagnostic['status']=='insufficient_valid_history'
    assert qs.fetch_diagnostic['valid_rows']==49


def test_provider_exception_keeps_sanitized_diagnostic(monkeypatch,capsys):
    monkeypatch.setenv('TEST_API_KEY','private-key-123')
    def fail(*a,**kw):raise ValueError('private-key-123 https://provider.test/?token=abc')
    monkeypatch.setattr(quant_analysis,'get_history',fail)
    qs=quant_analysis.QuantStrategy('TEST')
    assert qs.fetch_data(period='5y') is False
    assert qs.fetch_diagnostic['error_type']=='ValueError'
    assert 'private-key-123' not in str(qs.fetch_diagnostic)+capsys.readouterr().out


def test_worker_retains_fetch_reason_and_adds_evidence(monkeypatch):
    detail=history_diagnostic(frame(12),period='5y',interval='1d')
    monkeypatch.setattr(scanner_runtime.quant_analysis,'QuantStrategy',
        lambda *a,**k:SimpleNamespace(fetch_data=lambda **k:False,fetch_diagnostic=detail))
    reasons={};details={}
    result=scanner_runtime.scan_symbol_with_retry('NEW',tickers_dict={'NEW':'new'},is_us=True,
        is_amex=False,is_advanced_engine=False,r_status='NORMAL',intel_data=None,macro_ctx=None,
        market_gate={},rank_adjustment_fn=lambda **kw:0,news_adjustment_fn=lambda **kw:{},
        backoff_state=scanner_runtime.SharedBackoffState(),max_retries=0,
        reject_reason_fn=lambda sym,reason:reasons.update({sym:reason}),
        reject_detail_fn=lambda sym,row:details.setdefault(sym,[]).append(row))
    assert result is None and reasons=={'NEW':'FETCH_DATA_FAIL'}
    summary=summarize_fetch_rejections({'reject_reasons_by_symbol':reasons,
        'reject_details_by_symbol':details,'reject_reason_counts':{'FETCH_DATA_FAIL':1}})
    assert summary=={'fetch_rejection_count':1,'insufficient_history_count':1,'source_failure_count':0}
    assert summarize_health([{'total_scans':1,**summary}],1,1)['status']=='ok'


def test_legacy_unknown_fetch_failures_degrade_without_inflating_worker_errors():
    health=summarize_health([{'total_scans':211,'error_count':0,
        'reject_reason_counts':{'FETCH_DATA_FAIL':211}}],211,1)
    assert health['status']=='degraded' and health['exit_code']==2
    assert health['source_failure_count']==211 and health['total_errors']==0
    assert health['scan_coverage_complete'] and not health['source_coverage_complete']


def test_empty_and_bad_valid_rows_are_source_failures_not_history_exclusions():
    df=frame(50);df['Close']=float('nan')
    details={symbol:[{'fetch_diagnostic':history_diagnostic(value,period='5y',interval='1d')}]
        for symbol,value in [('EMPTY',frame(0)),('BAD',df)]}
    summary=summarize_fetch_rejections({'reject_reasons_by_symbol':{'EMPTY':'FETCH_DATA_FAIL','BAD':'FETCH_DATA_FAIL'},
        'reject_details_by_symbol':details,'reject_reason_counts':{'FETCH_DATA_FAIL':2}})
    assert summary['source_failure_count']==2 and summary['insufficient_history_count']==0


def test_shared_disk_summary_preserves_source_failure_and_short_history(tmp_path,monkeypatch):
    import json
    from modules.scan_persistence import persist_scan_run_artifacts
    from multi_agent.storage.memory_layers import MemoryManager
    monkeypatch.setenv('AG_RUNTIME_ARTIFACT_WRITE_DB','0')
    monkeypatch.setenv('AG_SCAN_UNIVERSE_SNAPSHOT_WRITE_DB','0')
    detail={'SHORT':[{'fetch_diagnostic':history_diagnostic(frame(12),period='5y',interval='1d')}],
            'EMPTY':[{'fetch_diagnostic':history_diagnostic(frame(0),period='5y',interval='1d')}]}
    diag={'filtered_count':2,'reject_reasons_by_symbol':{s:'FETCH_DATA_FAIL' for s in detail},
          'reject_details_by_symbol':detail,'reject_reason_counts':{'FETCH_DATA_FAIL':2}}
    receipt=persist_scan_run_artifacts(run_id='AUDIT-FETCH',market='NASDAQ',scan_mode='SWING',
        results=[],total_scans=2,diagnostics=diag,memory=MemoryManager(tmp_path))
    saved=json.loads(open(receipt['scan_pipeline_summary']).read())
    assert saved['source_failure_count']==saved['insufficient_history_count']==1
    assert 'SCAN_SOURCE_UNAVAILABLE' in [v['code'] for v in saved['warnings']]
