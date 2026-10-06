import numpy as np
import pandas as pd
import pytest

from modules.us_symbol_lineage import daily_bar_issues, listing_symbols
from multi_agent.tools import backfill_us_daily_features as bf
from multi_agent.tools import report_nasdaq_session_tape as tape
from multi_agent.tools import research_nasdaq_session_edge as research


def sample():
    dates = pd.bdate_range('2022-09-01', '2024-06-01')
    p = np.arange(len(dates)) * .1 + 100
    return pd.DataFrame(dict(date=dates, symbol='CBIO', source='yfinance', name='Crescent',
        market='NASDAQ', open=p, high=p+2, low=p-2, close=p, raw_close=p,
        adj_close=p, adj_factor=1., volume=1000., dollar_volume=p*1000))


def test_aliases_preserve_identity_order_and_boundary():
    frame = pd.DataFrame({'symbol':['CBIO','GYRE','CBIO','CBIO','GLYC'],
        'date':['2025-06-16','2022-09-20','2024-10-25','2025-06-13','2024-10-25']},index=[5,5,3,1,0])
    original=frame.copy(deep=True)
    assert listing_symbols(frame).tolist()==['CBIO','CBIO','GLYC','GLYC','GLYC']
    pd.testing.assert_frame_equal(frame,original)


@pytest.mark.parametrize('adjustment',[11/12,np.nan,-1.1])
def test_known_wrong_dividend_not_only_negative_prices(adjustment):
    raw=sample();raw['adj_close']=raw.raw_close*adjustment
    issue=daily_bar_issues(raw)
    assert issue[raw.date<'2023-01-13'].eq('incompatible_issuer_dividend_adjustment').all()
    assert issue[raw.date>='2023-01-13'].eq('').all()


def test_rule_is_scoped_to_provider_and_series_and_allows_unit_adjustment():
    raw=sample();assert daily_bar_issues(raw).eq('').all()
    raw.adj_close*=11/12
    for field,value in [('symbol','GYRE'),('source','independent')]:
        other=raw.copy();other[field]=value
        assert daily_bar_issues(other).eq('').all()
    raw.loc[0,'close']=-1
    assert daily_bar_issues(raw).iloc[0]=='invalid_prices'


def test_quarantine_preserves_dates_resets_features_and_prevents_outcomes():
    raw=sample();bad=raw.date<'2023-01-13';raw.loc[bad,'adj_close']*=11/12
    original=raw.copy(deep=True)
    result=bf.compute_feature_frame(raw)
    assert result.date.equals(raw.date)
    assert result.loc[bad,'source_bar_valid'].eq(0).all()
    assert result.loc[bad,['close','fwd_high_ret_20d','ret_1d']].isna().all().all()
    assert pd.isna(result.loc[~bad,'ret_1d'].iloc[0])
    assert result.iloc[-1].feature_ready==1
    assert research._outcome_from_raw_daily(raw,raw.iloc[0].date,entry_price=100,include_current_date=False) is None
    pd.testing.assert_frame_equal(raw,original)


def test_listing_does_not_use_old_catalyst_or_backfill_snapshot_gaps(monkeypatch):
    listing=pd.DataFrame([
        ['2024-01-01','CBIO','Catalyst Common Stock','N','N'],
        ['2024-01-01','GLYC','GlycoMimetics Common Stock','N','N'],
        ['2024-02-01','CBIO','Catalyst Common Stock','N','N'],
        ['2025-03-01','GLYC','GlycoMimetics Common Stock','N','N'],
        ['2025-08-21','CBIO','Crescent Common Stock','N','N'],
    ],columns=['snapshot_ts','symbol','security_name','test_issue','etf'])
    monkeypatch.setattr(tape.pd,'read_parquet',lambda *a,**kw:listing.copy())
    panel=pd.DataFrame({'symbol':['CBIO']*5,'date':['2024-01-10','2024-02-10','2025-06-13','2025-06-16','2025-08-21']})
    assert tape._listed_pit(panel).tolist()==[True,False,True,False,True]


@pytest.mark.parametrize('current,previous,effective',[
    ('GYRE','CBIO','2023-10-31'),('ASTS','NPA','2021-04-07'),
    ('ATTT','RAY','2026-09-10'),('GMEX','FTEL','2026-03-12'),
    ('ITOC','PTHL','2026-01-16'),
])
def test_alias_uses_trading_boundary_and_does_not_chain(current,previous,effective):
    when=pd.Timestamp(effective)
    frame=pd.DataFrame({'symbol':[current]*2,'date':[when-pd.Timedelta(days=1),when]})
    assert listing_symbols(frame).tolist()==[previous,current]


def test_two_historical_cbio_meanings_do_not_converge():
    frame=pd.DataFrame({'symbol':['GYRE','CBIO'],'date':['2022-01-03']*2})
    assert listing_symbols(frame).tolist()==['CBIO','GLYC']


@pytest.mark.parametrize('symbol,start',[('CNL','2026-08-11'),('SPRC','2021-12-22'),('TLN','2024-07-10')])
def test_venue_history_cannot_become_nasdaq_membership_from_same_ticker(monkeypatch,symbol,start):
    when=pd.Timestamp(start)
    # A ticker may appear for another instrument in an old directory.
    listing=pd.DataFrame({'snapshot_ts':[when-pd.Timedelta(days=7),when+pd.Timedelta(days=1)],'symbol':[symbol]*2,
        'security_name':['Common Stock']*2,'test_issue':['N']*2,'etf':['N']*2})
    monkeypatch.setattr(tape.pd,'read_parquet',lambda *a,**kw:listing.copy())
    panel=pd.DataFrame({'symbol':[symbol]*3,'date':[when-pd.Timedelta(days=1),when,when+pd.Timedelta(days=1)]})
    assert tape._listed_pit(panel).tolist()==[False,False,True]


def test_new_alias_still_requires_observed_snapshot_membership(monkeypatch):
    listing=pd.DataFrame([
        ['2026-06-11','RAY','Raytech Common Stock','N','N'],
        ['2026-10-06 21:36:27','ATTT','Atlas Common Stock','N','N'],
    ],columns=['snapshot_ts','symbol','security_name','test_issue','etf'])
    listing.snapshot_ts=pd.to_datetime(listing.snapshot_ts,format='mixed')
    monkeypatch.setattr(tape.pd,'read_parquet',lambda *a,**kw:listing.copy())
    panel=pd.DataFrame({'symbol':['ATTT']*4,'date':['2026-09-09','2026-09-10','2026-10-06','2026-10-07']})
    assert tape._listed_pit(panel).tolist()==[True,False,False,True]


def test_new_cbio_epoch_cannot_inherit_old_catalyst_snapshot_across_gap(monkeypatch):
    listing=pd.DataFrame([
        ['2023-09-28','CBIO','Catalyst Common Stock','N','N'],
        ['2025-08-21','CBIO','Crescent Common Stock','N','N'],
    ],columns=['snapshot_ts','symbol','security_name','test_issue','etf'])
    monkeypatch.setattr(tape.pd,'read_parquet',lambda *a,**kw:listing.copy())
    panel=pd.DataFrame({'symbol':['CBIO','CBIO','GYRE'],'date':['2025-06-16','2025-08-21','2023-10-01']})
    assert tape._listed_pit(panel).tolist()==[False,True,True]
