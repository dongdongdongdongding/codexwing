from datetime import datetime, timezone
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from modules import nasdaq_scan_universe as ns
from modules.quant_analysis import QuantStrategy
from multi_agent.tools import run_us_full_universe_research as us
from multi_agent.workflows import non_ui_scan_pipeline as pipeline


def directory_body():
    stamp = datetime.now(timezone.utc).astimezone(ZoneInfo('America/New_York')).strftime('%m%d%Y%H:%M')
    return ('Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n'
            'AAPL|Apple - Common Stock|Q|N|N|100|N|N\n'
            'PREF|Example - Preferred Stock|G|N|N|100|N|N\n'
            'FUND|Example ETF|G|N|N|100|Y|N\n'
            'RIGHT|Example - Right|G|N|N|100|N|N\n'
            'TEST|Test security|G|Y|N|100|N|N\n'
            'File Creation Time: ' + stamp + '|||||||\n').encode()


@pytest.fixture
def official(monkeypatch, tmp_path):
    monkeypatch.setattr(ns, 'AUDIT_ROOT', tmp_path)
    monkeypatch.setattr(ns, '_snapshot_cache', None)
    calls = []
    def get(url, timeout):
        calls.append((url, timeout))
        return SimpleNamespace(content=directory_body(), status_code=200, raise_for_status=lambda: None)
    monkeypatch.setattr(ns.requests, 'get', get)
    return calls


def test_complete_seed_guard_retains_types_and_records_removed_names(official):
    universe = ns.reconcile_seed({'OLD':'old','PREF':'pref','AAPL':'apple','FUND':'fund','TEST':'test'}, seed_source='fixture')
    assert list(universe) == ['PREF','AAPL','FUND']
    assert universe.provenance['excluded_symbols'] == ['OLD','TEST']
    evidence = json.loads(open(universe.provenance['selection_evidence']).read())
    assert evidence['selected_names'] == universe
    assert evidence['seed_names']['OLD'] == 'old'
    assert universe.provenance['source_sha256']
    assert len(official) == 1
    # Explicit instruments can be outside the seed, but must be officially listed.
    assert universe.select(['RIGHT']) == {'RIGHT':'Example - Right'}
    with pytest.raises(ns.NasdaqUniverseUnavailable):
        universe.select(['OLD'])


def test_expired_cache_failure_cannot_reuse_old_listing(official, monkeypatch):
    ns.current_directory()
    assert len(official) == 1
    ns.current_directory()
    assert len(official) == 1
    monkeypatch.setattr(ns, '_CACHE_SECONDS', -1)
    def fail(*args, **kwargs): raise TimeoutError('source down')
    monkeypatch.setattr(ns.requests, 'get', fail)
    with pytest.raises(ns.NasdaqUniverseUnavailable): ns.current_directory()


def test_invalid_directory_fails_closed(official, monkeypatch):
    monkeypatch.setattr(ns.requests, 'get', lambda *a,**k: SimpleNamespace(
        content=b'not a directory', status_code=200, raise_for_status=lambda:None))
    with pytest.raises(ns.NasdaqUniverseUnavailable):
        ns.reconcile_seed({'AAPL':'apple'}, seed_source='fixture')


def test_quant_fallback_still_requires_official_membership(official, monkeypatch):
    import modules.quant_analysis as qa
    monkeypatch.setattr(qa.fdr, 'StockListing', lambda market: (_ for _ in ()).throw(RuntimeError('down')))
    monkeypatch.setattr(QuantStrategy, '_fallback_us_tickers', lambda market: {'OLD':'old','AAPL':'apple'})
    universe = QuantStrategy.get_market_tickers('NASDAQ')
    assert universe == {'AAPL':'Apple - Common Stock'}
    assert universe.provenance['seed_is_fallback']
    monkeypatch.setattr(ns, '_snapshot_cache', None)
    monkeypatch.setattr(ns.requests, 'get', lambda *a,**k: (_ for _ in ()).throw(TimeoutError('down')))
    with pytest.raises(ns.NasdaqUniverseUnavailable): QuantStrategy.get_market_tickers('NASDAQ')


def test_manual_symbols_cannot_bypass_membership(official, monkeypatch):
    universe = ns.reconcile_seed({'AAPL':'apple'}, seed_source='fixture')
    monkeypatch.setattr(QuantStrategy,'get_market_tickers', lambda market:universe)
    assert pipeline._resolve_ticker_map('NASDAQ','RIGHT')['RIGHT'] == 'Example - Right'
    with pytest.raises(ns.NasdaqUniverseUnavailable): pipeline._resolve_ticker_map('NASDAQ','OLD')


def test_batch_receipt_marks_fallback_and_uses_one_frozen_universe(official, monkeypatch, tmp_path):
    universe = ns.reconcile_seed({'AAPL':'apple','PREF':'pref'}, seed_source='fallback',seed_is_fallback=True)
    monkeypatch.setattr(QuantStrategy,'get_market_tickers',lambda market:universe)
    calls=[]
    def scan(**kw):
        assert kw['ticker_universe'] is universe
        selected=kw['ticker_universe'].select(kw['tickers'].split(','))
        calls.append(selected)
        return {'total_scans':len(selected),'error_count':0}
    monkeypatch.setattr(us,'run_non_ui_scan_pipeline',scan)
    monkeypatch.setattr('sys.argv',['scan','--market','NASDAQ','--batch-size','1','--output-dir',str(tmp_path)])
    monkeypatch.setenv('US_RESEARCH_RECEIPT_PATH',str(tmp_path/'receipt.json'))
    assert us.main() == 2
    result=json.loads((tmp_path/'receipt.json').read_text())
    assert len(calls)==2 and result['status']=='degraded'
    assert result['universe_provenance']['membership_verified']
    assert result['universe_seed_complete'] is False


def test_universe_failure_has_durable_failed_receipt(monkeypatch, tmp_path):
    def fail(market): raise ns.NasdaqUniverseUnavailable('no source')
    monkeypatch.setattr(QuantStrategy,'get_market_tickers',fail)
    monkeypatch.setattr(us,'run_non_ui_scan_pipeline',lambda **kw:pytest.fail('must not scan'))
    monkeypatch.setattr('sys.argv',['scan','--market','NASDAQ','--output-dir',str(tmp_path)])
    monkeypatch.setenv('US_RESEARCH_RECEIPT_PATH',str(tmp_path/'receipt.json'))
    assert us.main()==2
    result=json.loads((tmp_path/'receipt.json').read_text())
    assert result['status']=='failed' and result['batch_failure']['stage']=='universe'
    assert not result['source_coverage_complete']
    assert not result['scan_coverage_complete']


def test_real_pipeline_uses_verified_batch_without_second_listing(official, monkeypatch):
    universe = ns.reconcile_seed({'AAPL':'apple','PREF':'pref'}, seed_source='fixture')
    monkeypatch.setattr(QuantStrategy,'get_market_tickers',lambda market:pytest.fail('must use frozen batch universe'))
    monkeypatch.setattr(pipeline,'MemoryManager',lambda:SimpleNamespace())
    monkeypatch.setattr(QuantStrategy,'detect_market_regime',lambda market:{'regime':'NORMAL'})
    monkeypatch.setattr(pipeline,'get_macro_context',lambda **kw:{})
    monkeypatch.setattr(pipeline,'compute_market_gate',lambda market:{})
    monkeypatch.setattr(pipeline,'_resolve_market_intel',lambda market:({},None))
    monkeypatch.setattr(pipeline,'_write_market_intel_snapshot',lambda *a,**kw:None)
    class ReachedWorkerDispatch(Exception):pass
    def dispatch(**kw):
        assert kw['ticker_list']==['PREF']
        raise ReachedWorkerDispatch()
    monkeypatch.setattr(pipeline,'run_parallel_scan',dispatch)
    with pytest.raises(ReachedWorkerDispatch):
        pipeline.run_non_ui_scan_pipeline(market='NASDAQ',profile='prod',max_scan=1,max_workers=1,
            is_advanced_engine=False,max_retries=0,tickers='PREF',force_macro_refresh=False,
            strategy_version='test',model_version='test',code_version='test',ticker_universe=universe)


def test_shared_persistence_retains_membership_evidence_and_fallback_warning(official, tmp_path, monkeypatch):
    from modules.scan_persistence import persist_scan_run_artifacts
    from multi_agent.storage.memory_layers import MemoryManager
    monkeypatch.setenv('AG_RUNTIME_ARTIFACT_WRITE_DB','0')
    monkeypatch.setenv('AG_SCAN_UNIVERSE_SNAPSHOT_WRITE_DB','0')
    universe=ns.reconcile_seed({'AAPL':'apple'},seed_source='fallback',seed_is_fallback=True)
    receipt=persist_scan_run_artifacts(run_id='AUDIT-NASDAQ',market='NASDAQ',scan_mode='SWING',
        results=[],total_scans=0,diagnostics={'universe_provenance':universe.provenance},memory=MemoryManager(tmp_path/'memory'))
    saved=json.loads(open(receipt['scan_pipeline_summary']).read())
    assert saved['universe_provenance']==universe.provenance
    assert 'SCAN_UNIVERSE_FALLBACK' in [w['code'] for w in saved['warnings']]
