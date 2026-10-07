from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from modules import naver_investor_flow as naver
from modules import quant_analysis
from modules.quant_analysis import QuantStrategy

FIXTURES = Path(__file__).parent / 'fixtures/naver_trend_20261007'
TODAY = date(2026, 10, 7)


def payload(code='005930'):
    return json.loads((FIXTURES / f'{code}.json').read_text())


@pytest.mark.parametrize('code', ['005930', '035420'])
def test_captured_actual_krx_contract_has_exact_10_rows(code):
    source = payload(code)
    frame, metadata = naver.parse_trend(source, today=TODAY, reference_session='2026-10-06')
    assert len(frame) == 10 and frame.iloc[0]['날짜'] == '2026-10-06'
    for n in [1, 3, 10]:
        rows = source['result']['items'][:n]
        assert frame.head(n)['Foreigner'].sum() == sum(int(x['krx']['foreignNetVolume']) for x in rows)
        assert frame.head(n)['Institution'].sum() == sum(int(x['krx']['organizationNetVolume']) for x in rows)
        assert metadata[f'reported_retail_{n}d'] == sum(int(x['krx']['individualNetVolume']) for x in rows)
    assert metadata['flow_venue'] == 'KRX'
    assert metadata['retail_basis'] == 'reported_individual_net_volume'


def test_actual_stale_symbol_is_missing_not_zero():
    with pytest.raises(ValueError, match='missing_krx'):
        naver.parse_trend(payload('091990'), today=TODAY)


@pytest.mark.parametrize('mutation,reason', [
    (lambda p: p.update(isSuccess=False), 'unsuccessful'),
    (lambda p: p['result'].update(items=p['result']['items'][:5]), 'insufficient'),
    (lambda p: p['result']['items'][0]['krx'].update(foreignNetVolume=None), 'missing_or_invalid'),
    (lambda p: p['result']['items'][0]['krx'].update(foreignNetVolume='NaN'), 'missing_or_invalid'),
    (lambda p: p['result']['items'][0]['krx'].update(foreignNetVolume='0'), 'inconsistent'),
    (lambda p: p['result']['items'][0]['krx'].update(tradingVolume='0'), 'no_latest_trading'),
    (lambda p: p['result']['items'][0].update(localTradedAt='2026-10-08'), 'future_duplicate'),
    (lambda p: p['result']['items'][1].update(localTradedAt='2026-10-06'), 'future_duplicate'),
])
def test_incomplete_corrupt_or_unobserved_data_is_rejected(mutation, reason):
    source = payload()
    mutation(source)
    with pytest.raises(ValueError, match=reason):
        naver.parse_trend(source, today=TODAY)


def test_known_later_session_rejects_old_source_and_holiday_does_not():
    naver.parse_trend(payload(), today=date(2026, 10, 11), reference_session='2026-10-06')
    with pytest.raises(ValueError, match='older_than_observed'):
        naver.parse_trend(payload(), today=date(2026, 10, 11), reference_session='2026-10-07')


def test_measured_zero_net_with_positive_volume_is_valid():
    source = payload()
    for who in ['foreign', 'organization', 'individual']:
        source['result']['items'][0]['krx'].update({who+'NetVolume': '0', who+'BuyVolume': '100', who+'SellVolume': '100'})
    frame, _ = naver.parse_trend(source, today=TODAY)
    assert frame.iloc[0]['Foreigner'] == frame.iloc[0]['Institution'] == 0


def test_real_response_through_quant_fallback_without_live_io(monkeypatch):
    raw = (FIXTURES / '005930.json').read_bytes()
    class Response:
        content = raw
        def raise_for_status(self): pass
        def json(self): return json.loads(raw)
    def fake_get(url, **kwargs):
        assert url == naver.URL
        assert kwargs['params'] == {'code': '005930', 'exchangeType': 'KRX', 'size': 20}
        return Response()
    monkeypatch.setattr(naver.requests, 'get', fake_get)
    monkeypatch.setattr('modules.market_sessions.price_sessions', lambda *a: (['2026-10-02'], 'captured_calendar'))
    monkeypatch.setattr(quant_analysis, 'HAS_PYKRX', False)
    monkeypatch.setenv('AG_ENABLE_KIS_INVESTOR_FLOW', '0')
    monkeypatch.setenv('AG_KR_INVESTOR_FLOW_PROVIDER', '')
    flow = QuantStrategy('005930.KS').get_investor_flows()
    assert flow['valid'] and flow['flow_source'] == 'naver' and flow['flow_unit'] == 'shares'
    assert flow['flow_asof'] == '2026-10-06'
    assert flow['flow_response_sha256'] == hashlib.sha256(raw).hexdigest()
    assert flow['foreigner_1d'] == -2064174 and flow['institution_1d'] == -193422
    assert flow['retail_1d'] == flow['reported_retail_1d'] == 1273618
    assert flow['retail_1d'] != -(flow['foreigner_1d'] + flow['institution_1d'])
    assert flow['flow_freshness_check'] == 'not_older_than_observed_previous_session'
    from modules.scanner_services import build_kr_scan_outputs
    from modules.top_deep_report import _fetch_investor_flow_snapshot
    monkeypatch.setenv('AG_ENABLE_KIS_SIDECAR', '0')
    output = build_kr_scan_outputs(
        sym='005930.KS', stock_name='Samsung', alpha_score=80, whale_score=flow['whale_score'],
        whale_trend=flow['whale_trend'], real_trend='UP', prev_pct_change=1.0, consec_days=1,
        setup={'Entry Price': 100, 'Target Price': 105, 'Stop Loss': 90, 'Volume Ratio': 2},
        news_tag='', strategy_tag='test', surge_tag='', wr=70, position='Rising', prob_5=60,
        prob_clean=60, decision_score=80, conviction_score=70, tier='T1', tier_sort=1,
        tech_score=70, fund_ok=True, m_type='KOSPI', verdict_label='test', market_gate='GREEN',
        kospi_chg=0, whale_data=flow)
    row, db = output['res_data'], output['db_payload']
    assert row['flow_contract'] == db['leader_metrics']['flow_contract'] == flow['flow_contract']
    assert row['retail_1d'] == db['retail_1d'] == 1273618
    direct = _fetch_investor_flow_snapshot('005930.KS', row, {})
    assert direct['flow_contract'] == flow['flow_contract'] and direct['retail_1d'] == 1273618
    stored = _fetch_investor_flow_snapshot('005930.KS', db, {})
    assert stored['flow_contract'] == flow['flow_contract']
    malformed = {**row, 'flow_contract': None, '_leader_metrics': 'invalid', 'leader_metrics': 'invalid'}
    assert _fetch_investor_flow_snapshot('005930.KS', malformed, {})['flow_contract'] == {}
    live = _fetch_investor_flow_snapshot('005930.KS', {}, {})
    assert live['flow_contract']['flow_response_sha256'] == flow['flow_contract']['flow_response_sha256']
    assert live['flow_contract']['retail_basis'] == 'reported_individual_net_volume'
    assert live['retail_1d'] == 1273618


def test_http_error_does_not_become_zero_flow(monkeypatch):
    import requests
    def fail(*a, **kw): raise requests.HTTPError('503')
    monkeypatch.setattr(naver.requests, 'get', fail)
    monkeypatch.setattr(quant_analysis, 'HAS_PYKRX', False)
    monkeypatch.setenv('AG_ENABLE_KIS_INVESTOR_FLOW', '0')
    monkeypatch.setenv('AG_KR_INVESTOR_FLOW_PROVIDER', '')
    flow = QuantStrategy('005930.KS').get_investor_flows()
    assert not flow['valid'] and 'naver_flow_failed:503' in flow['warnings']
