import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.audit_ext_transfer import chunks, controls_for, decisions, residual


def sample_panel(days=12):
    dates=pd.bdate_range('2026-01-05',periods=days).strftime('%Y-%m-%d').tolist()
    rng=np.random.default_rng(123)
    rows=[]
    for day in dates:
        for i in range(50):
            rows.append({'date':day,'code':f'{i:06d}','market':'KOSPI' if i<25 else 'KOSDAQ',
                         'regular':rng.normal(0,.01),'log_turnover':rng.normal(22,1),'after':rng.normal(0,.01)})
    return pd.DataFrame(rows),dates


def test_residual_removes_only_contemporaneous_linear_components():
    panel,_=sample_panel(1)
    shock=panel.after.to_numpy()
    y=2+.4*panel.regular+.03*panel.log_turnover+.2*(panel.market=='KOSDAQ')+shock
    expected=residual(panel)
    assert np.allclose(residual(panel,y),expected,atol=1e-12)
    assert abs(expected.sum())<1e-10


def test_match_is_market_local_and_excludes_selected():
    panel,_=sample_panel(1)
    controls=controls_for(panel,0)
    assert len(controls)==20 and len(set(controls))==20
    assert '000000' not in controls
    assert all(int(code)<25 for code in controls)


def test_selection_causal_order_independent_and_uses_missing_calendar_days():
    panel,calendar=sample_panel()
    seeds=[11,12,13]
    full=decisions(panel,calendar,seeds)
    shuffled=decisions(panel.sample(frac=1,random_state=55),calendar,seeds)
    assert full==shuffled
    short=decisions(panel[panel.date<=calendar[5]],calendar[:6],seeds)
    assert full[:6]==short
    accepted=[i for i,row in enumerate(full) if row['decision']=='ACCEPT']
    assert all(sum(i-4<=j<=i for j in accepted)<=3 for i in range(len(calendar)))
    # Missing observations remain a date in the rolling window, never compress time.
    sparse=panel[~panel.date.isin(calendar[1:4])]
    result=decisions(sparse,calendar,seeds)
    assert all(row['decision']=='NO_ELIGIBLE_SIGNAL_DATA' for row in result[1:4])
    assert result[4]['decision']=='ACCEPT'


def test_provider_chunks_cover_exact_range_once_with_bounded_sizes():
    result=list(chunks('2026-02-27','2026-10-06',60))
    dates=[]
    for start,end in result:
        window=pd.date_range(start,end)
        assert len(window)<=60
        dates.extend(window)
    assert dates==list(pd.date_range('2026-02-27','2026-10-06'))


def evaluation_fixture(tmp_path,monkeypatch,missing_code=None):
    from research import audit_ext_transfer as module
    panel,calendar=sample_panel(60)
    audit=tmp_path/'runtime_state/audit/ext_transfer_20261007';audit.mkdir(parents=True)
    path=audit/'signal_panel.parquet';panel.to_parquet(path,index=False)
    frozen={'prereg_sha256':'frozen','panel_sha256':module.sha(path),'calendar':calendar,
            'decisions':decisions(panel,calendar,[20261007,20261008,20261009]),'eligibility_counts':{}}
    (audit/'signal_decisions.json').write_text(json.dumps(frozen))
    bars=pd.DataFrame({'date':pd.to_datetime(calendar),'adj_open':100.,'adj_high':106.,'adj_low':99.,'adj_close':101.,'volume':1000.})
    groups={code:bars.copy() for code in panel.code.unique() if code!=missing_code}
    monkeypatch.setattr(module,'load_prices',lambda *args:(groups,[],{}))
    spec={'contract':{'horizon_sessions':10,'cost_pct':.215},'decision':{'mandatory_remaining':['prospective','PIT provenance']}}
    return module,spec,audit,frozen


def test_universal_high_touch_cannot_pass_matched_alpha_or_publish(tmp_path,monkeypatch):
    module,spec,audit,frozen=evaluation_fixture(tmp_path,monkeypatch)
    result=module.evaluate(spec,'frozen',audit)
    assert result['metrics']['touch_rate']==1
    assert result['matched_excess']['mean_pp']==pytest.approx(0,abs=1e-10)
    assert result['matched_excess']['ticker_placebo_p_max']==1
    assert 'ticker_placebo_not_significant' in result['decision']['mechanism_reject']
    assert result['publication_allowed'] is False
    assert json.loads((audit/'signal_decisions.json').read_text())==frozen


def test_missing_preselected_control_is_error_not_replaced(tmp_path,monkeypatch):
    module,spec,audit,frozen=evaluation_fixture(tmp_path,monkeypatch,missing_code='000000')
    result=module.evaluate(spec,'frozen',audit)
    assert result['status']=='INCONCLUSIVE'
    assert 'selected_or_control_data_errors' in result['decision']['inconclusive']
    assert any(c['status']=='data_error' for row in result['control_records'] for c in row['controls'])
    assert len(result['records'])==sum(r['decision']=='ACCEPT' for r in frozen['decisions'])
    assert all(len(row['controls'])==20 for row in result['control_records'])
