import numpy as np
import pandas as pd
import pytest
import json

from multi_agent.tools import backfill_us_daily_features as bf
from multi_agent.tools import research_nasdaq_session_edge as research


def bars(n=500):
    close = 100 + np.arange(n) * .1 + np.sin(np.arange(n))
    return pd.DataFrame({'date':pd.bdate_range('2023-01-02', periods=n),
        'symbol':'AAA','name':'AAA','market':'NASDAQ','open':close,
        'high':close+2,'low':close-2,'close':close,'volume':1000.,
        'raw_close':close,'adj_close':close,'adj_factor':1.,'dollar_volume':close*1000})


@pytest.mark.parametrize('column,value,reason',[
    ('close',-1.,'invalid_prices'),('low',0.,'invalid_prices'),
    ('open',np.nan,'invalid_prices'),('high',1.,'invalid_OHLC_order'),
    ('volume',-1.,'invalid_volume')])
def test_invalid_dates_remain_and_features_and_labels_cannot_cross(column,value,reason):
    source=bars();source.loc[150,column]=value
    out=bf.compute_feature_frame(source)
    assert len(out)==len(source)
    assert out.loc[150,'date']==source.loc[150,'date']
    assert out.loc[150,'source_issue']==reason
    assert out.loc[150,'feature_ready']==0
    assert out.loc[150,['open','high','low','close']].isna().all()
    assert pd.isna(out.loc[151,'ret_1d'])
    assert pd.notna(out.loc[129,'fwd_high_ret_20d'])
    assert out.loc[130:150,'fwd_high_ret_20d'].isna().all()
    assert out.loc[146:150,'first_up_day_5d'].isna().all()
    assert out.iloc[-1].feature_ready==1
    changed=source.copy()
    changed.loc[:149,['open','high','low','close']]*=10
    changed_out=bf.compute_feature_frame(changed)
    pd.testing.assert_frame_equal(out.iloc[151:].reset_index(drop=True),changed_out.iloc[151:].reset_index(drop=True))


def test_no_partial_horizon_extreme_labels_even_when_early_touch_observed():
    source=bars();source.loc[499,'high']=1000
    out=bf.compute_feature_frame(source)
    for horizon in bf.RETURN_HORIZONS:
        columns=[f'{prefix}_{horizon}d' for prefix in ['fwd_close_ret','fwd_high_ret','fwd_low_ret','touch5','touch10','dd5','dd10']]
        assert out.tail(horizon)[columns].isna().all().all()
        assert out.iloc[-horizon-1][columns].notna().all()


def test_invalid_latest_is_not_replaced_with_an_older_good_bar(tmp_path):
    paths=bf.BackfillPaths(tmp_path,'NASDAQ');paths.raw_dir.mkdir(parents=True)
    source=bars();source.loc[499,'high']=1
    source.to_parquet(bf._raw_path(paths,'AAA'),index=False)
    universe=pd.DataFrame({'symbol':['AAA'],'name':['AAA']})
    info=bf.write_feature_panel(universe,paths,start='2023-01-01',end='2026-01-01',output_prefix='daily_features',feature_batch_size=1)
    latest=pd.read_parquet(info['output_latest_path'])
    assert latest.iloc[0].date==source.iloc[-1].date
    assert latest.iloc[0].source_bar_valid==0 and pd.isna(latest.iloc[0].close)
    assert info['invalid_source_bars']=={'AAA':1}
    pd.testing.assert_frame_equal(pd.read_parquet(bf._raw_path(paths,'AAA')),source)


def test_bad_raw_date_is_not_silently_removed():
    source=bars(10);source.loc[3,'date']=pd.NaT
    with pytest.raises(ValueError,match='invalid_or_duplicate_raw_dates'):
        bf.compute_feature_frame(source)


def test_raw_outcome_keeps_invalid_date_and_rejects_crossing_window(tmp_path):
    source=bars(10);source.loc[3,'close']=np.nan
    source.to_parquet(tmp_path/'AAA.parquet',index=False)
    loaded=research._load_raw_daily('AAA',tmp_path)
    assert len(loaded)==10
    assert research._outcome_from_raw_daily(loaded,source.iloc[0].date,entry_price=100,include_current_date=False) is None


def test_pending_settlement_does_not_accept_inconsistent_provider_bar(tmp_path,monkeypatch):
    import yfinance as yf
    from multi_agent.tools import report_nasdaq_session_tape as tape
    ledger=tmp_path/'ledger.jsonl'
    original=json.dumps({'symbol':'AAA','date':'2023-01-02','entry':100.,'policy_ret':None,'contract_h':5})+'\n'
    ledger.write_text(original)
    monkeypatch.setattr(tape,'LEDGER',ledger)
    source=bars(10).set_index('date')[['open','high','low','close']]
    source.iloc[3,source.columns.get_loc('high')]=1.
    source.columns=source.columns.str.title()
    monkeypatch.setattr(yf,'download',lambda *a,**kw:source)
    tape.resolve_pending(pd.Timestamp('2023-02-01'))
    assert ledger.read_text()==original


def test_daily_previous_close_uses_observation_before_readiness_filter(tmp_path):
    source=bars(3)
    source['liq20']=1e9
    source['feature_ready']=[1.,0.,1.]
    path=tmp_path/'panel.parquet';source.to_parquet(path,index=False)
    context=research._read_daily_context(path)
    assert context.iloc[-1].prev_daily_close==source.iloc[1].close


@pytest.mark.parametrize('field',['Open','Adj Close','Volume'])
def test_provider_extraction_preserves_partial_bar_and_unknown_values(field):
    from modules.ohlcv_quality import bar_issues
    payload=pd.DataFrame({'Open':[100.,100.,np.nan],'High':[101.,101.,np.nan],
        'Low':[99.,99.,np.nan],'Close':[100.,100.,np.nan],
        'Adj Close':[100.,100.,np.nan],'Volume':[1000.,1000.,np.nan]},
        index=pd.bdate_range('2026-01-01',periods=3))
    payload.loc[payload.index[0],field]=np.nan
    raw=bf._extract_yfinance_frame(payload,'AAA')
    assert len(raw)==2 and raw.iloc[0].date==payload.index[0]
    assert bar_issues(raw).iloc[0]!=''
    assert bar_issues(raw).iloc[1]==''
