from pathlib import Path
from multi_agent.tools.backfill_scanner_full_returns import _build_update_payload


def test_unadjusted_fallback_cannot_refill_normalized_immature_labels():
    row = {"return_5d_pct":None,"feature_snapshot":{"daily_outcome_basis":{
        "kind":"adjusted_signal_close_to_close","asof":"2026-10-02"}}}
    assert _build_update_payload(row,{"return_5d_pct":99}) == {}
    other = {"feature_snapshot":{"daily_outcome_basis":{
        "kind":"adjusted_signal_close_to_close","asof":"2026-10-01"}},"return_5d_pct":99}
    assert _build_update_payload(row,other) == {}


def test_legacy_backfill_still_fills_missing_cells_only():
    patch = _build_update_payload({"return_1d_pct":3},{"return_1d_pct":3,"return_3d_pct":4})
    assert "return_1d_pct" not in patch
    assert patch["return_3d_pct"] == 4


def test_conflicting_existing_horizon_cannot_be_mixed_with_new_provider():
    assert _build_update_payload({"return_1d_pct":3},{"return_1d_pct":9,"return_3d_pct":4}) == {}


def test_distinct_market_denominators_and_dates_cannot_be_combined():
    row = {"base_trade_date":"2026-09-17","entry_reference_price":53800.,"return_3d_pct":None}
    other = {"base_trade_date":"2026-09-17","entry_reference_price":53000.,"return_3d_pct":-7.}
    assert _build_update_payload(row,other) == {}
    assert _build_update_payload(row,{**other,"entry_reference_price":53800.,"base_trade_date":"2026-09-18"}) == {}
    assert _build_update_payload(row,{**other,"entry_reference_price":53800.})["return_3d_pct"] == -7.


def test_advancing_latest_return_is_not_a_fixed_horizon_conflict():
    assert _build_update_payload({"latest_return_pct":2,"return_1d_pct":1},
                                 {"latest_return_pct":3,"return_1d_pct":1,"return_3d_pct":4})["return_3d_pct"] == 4


def test_new_issued_rows_use_dedicated_refresh_even_before_first_normalization():
    assert _build_update_payload({"run_id":"SWING-CAND-20261007"}, {"return_1d_pct":2.}) == {}


def test_backfill_reports_conflicting_bases_without_counting_them_as_filled(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from modules import db_manager
    from multi_agent.tools import backfill_scanner_full_returns as m
    monkeypatch.setattr(db_manager, 'DBManager', lambda: SimpleNamespace(client=object()))
    monkeypatch.setattr(m, 'PROJECT_ROOT', tmp_path)
    rows = [{'id':i,'run_id':f'RUN-{i}','ticker':str(i),'recommended_at':'2026-09-17T00:00:00Z',
             'entry_reference_price':53800.,'return_1d_pct':1.} for i in [1,2]]
    monkeypatch.setattr(m, '_fetch_scanner_rows_missing_returns', lambda *a,**kw:rows)
    index={(f'RUN-{i}',str(i)):{'entry_reference_price':price,'return_1d_pct':1.,'return_3d_pct':2.}
           for i,price in [(1,53000.),(2,53800.)]}
    monkeypatch.setattr(m, '_build_outcome_index', lambda *a:index)
    report=m.run_backfill(shared_dir=tmp_path,limit_runs=1,dry_run=True,market_filter=None,allow_history_fallback=False)
    assert report['incompatible_daily_basis_by_field']=={'entry_reference_price':1}
    assert report['eligible_updates']==1
    assert report['fill_rate_after_pct_estimate']==50.
    assert report['updated']==0
    import json
    backup=json.loads(Path(report['audit']['backup']).read_text())
    assert backup['plan'][0]['before']['run_id']=='RUN-2'
    assert 'performance_updated_at' not in backup['plan'][0]['patch']


def test_archive_fetch_uses_bounded_keyset_and_retains_any_missing_horizon():
    from types import SimpleNamespace
    from multi_agent.tools import backfill_scanner_full_returns as m
    full={f'return_{h}d_pct':1. for h in m.HORIZONS_FROM_HISTORY}
    rows=[{**full,'id':i,'market_type':'KR','feature_origin':'scanner_full','return_30d_pct':None if i in [1,4] else 1.}
          for i in range(1,5)]
    rows.append({**full,'id':5,'market_type':'US','feature_origin':'scanner_full','return_1d_pct':None})
    pages=[]
    class Query:
        def __init__(self):self.filters=[];self.desc=False;self.n=500;self.lower=None;self.upper=None;self.columns=''
        def select(self,cols):self.columns=cols;return self
        def in_(self,key,vals):self.filters.append(lambda r:r[key] in vals);return self
        def eq(self,key,value):self.filters.append(lambda r:r[key]==value);return self
        def order(self,key,desc=False):assert key=='id';self.desc=desc;return self
        def limit(self,n):self.n=n;return self
        def lte(self,key,value):assert key=='id';self.upper=value;return self
        def gt(self,key,value):assert key=='id';self.lower=value;return self
        def execute(self):
            selected=[r for r in rows if all(f(r) for f in self.filters) and
                      (self.upper is None or r['id']<=self.upper) and (self.lower is None or r['id']>self.lower)]
            result=sorted(selected,key=lambda r:r['id'],reverse=self.desc)[:self.n]
            if self.columns=='id':
                # A new row arrives after the fixed upper watermark is read.
                rows.append({**full,'id':6,'market_type':'KR','feature_origin':'scanner_full','return_1d_pct':None})
            else:pages.append([r['id'] for r in result])
            return SimpleNamespace(data=result)
    db=SimpleNamespace(client=SimpleNamespace(table=lambda _:Query()))
    result=m._fetch_scanner_rows_missing_returns(db,page_size=2,market_filter='KR')
    assert [r['id'] for r in result]==[1,4]
    assert pages==[[1,2],[3,4]]


def test_outcome_index_never_borrows_same_ticker_day_from_another_run(tmp_path):
    import json
    from multi_agent.tools import backfill_scanner_full_returns as m
    for run,value in [('RUN-8BB50B37',-13.112885),('RUN-FB04A013',-13.340935)]:
        d=tmp_path/run;d.mkdir()
        row={'ticker':'037710.KS','recommended_at':'2026-07-12T00:37:42Z','return_14d_pct':value}
        (d/'realized_outcomes.json').write_text(json.dumps({'outcomes':[row]}))
    index=m._build_outcome_index(tmp_path,0)
    assert index[('RUN-8BB50B37','037710.KS')]['return_14d_pct']==-13.112885
    assert index[('RUN-FB04A013','037710.KS')]['return_14d_pct']==-13.340935
    assert m._build_update_payload({'run_id':'RUN-8BB50B37'},index[('RUN-FB04A013','037710.KS')])=={}


def test_ambiguous_duplicate_inside_same_run_is_omitted(tmp_path):
    import json
    from multi_agent.tools import backfill_scanner_full_returns as m
    d=tmp_path/'RUN-A';d.mkdir()
    rows=[{'ticker':'037710.KS','base_trade_date':'2026-07-13','return_1d_pct':x} for x in [1,2,1]]
    (d/'realized_outcomes.json').write_text(json.dumps({'outcomes':rows}))
    assert m._build_outcome_index(tmp_path,0)=={}


def test_history_dates_follow_market_timezone_but_date_only_values_do_not_shift():
    from multi_agent.tools.backfill_scanner_full_returns import _row_scan_date
    assert _row_scan_date({'ticker':'005930.KS','recommended_at':'2026-07-06T22:00:00Z'})=='2026-07-07'
    assert _row_scan_date({'ticker':'AAPL','recommended_at':'2026-07-07T01:00:00Z'})=='2026-07-06'
    assert _row_scan_date({'ticker':'AAPL','base_trade_date':'2026-07-07'})=='2026-07-07'
    assert _row_scan_date({'ticker':'AAPL','recommended_at':'garbage'}) is None


def test_postgrest_variable_fraction_precision_never_falls_back_to_stale_base_date():
    from multi_agent.tools.backfill_scanner_full_returns import _row_scan_date
    for fraction in ['1', '12', '123', '1234', '17633', '123456', '1234567']:
        row = {'ticker':'079550.KS','recommended_at':f'2026-07-23T22:37:09.{fraction}+00:00',
               'base_trade_date':'2026-07-23'}
        assert _row_scan_date(row) == '2026-07-24'


def test_run_limit_uses_modification_time_not_random_run_id_order(tmp_path):
    import os
    from multi_agent.tools.backfill_scanner_full_returns import _iter_run_dirs
    a=tmp_path/'RUN-A';z=tmp_path/'RUN-Z';a.mkdir();z.mkdir()
    os.utime(a,(200,200));os.utime(z,(100,100))
    assert _iter_run_dirs(tmp_path,1)==[a]
