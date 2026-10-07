import pytest
import pandas as pd

from research.audit_us_split_history_20261007 import page, validate_page
from research.compare_us_split_history_20261007 import basis_diagnostics


def response(dates, symbol='AIXI'):
    return {'rt_cd': '0', 'output1': {'rsym': 'DNAS' + symbol, 'nrec': str(len(dates))},
            'output2': [{'xymd': d} for d in dates]}


@pytest.mark.parametrize('payload,end,seen', [
    (response(['20260513'], 'WRONG'), '20260513', set()),
    (response(['20260514']), '20260513', set()),
    (response(['20260513', '20260513']), '20260513', set()),
    (response(['20260512', '20260513']), '20260513', set()),
    (response(['20260513']), '20260513', {'20260513'}),
    (response(['20260230']), '20260513', set()),
])
def test_invalid_page_cannot_be_used_for_coverage(payload, end, seen):
    with pytest.raises(ValueError):
        validate_page(payload, 'AIXI', end, seen)


def test_empty_terminal_and_descending_pages():
    assert validate_page(response([]), 'AIXI', '20260513', set()) == []
    assert validate_page(response(['20260513', '20260512']), 'AIXI', '20260513', set()) == ['20260513', '20260512']


def test_saved_response_is_reused_without_network_and_tamper_rejected(tmp_path):
    (tmp_path / 'pages').mkdir()
    class Client:
        calls = 0
        def overseas_daily_bars(self, **kw):
            self.calls += 1
            return response(['20260513'])
    client = Client()
    first = page(client, tmp_path, 'AIXI', 0, '20260513')
    assert page(client, tmp_path, 'AIXI', 0, '20260513') == first
    assert client.calls == 1
    (tmp_path / 'pages/AIXI_MODP0_20260513.json').write_text('{}')
    with pytest.raises(ValueError, match='saved_response_changed'):
        page(client, tmp_path, 'AIXI', 0, '20260513')
    assert client.calls == 1


def test_basis_diagnostic_detects_partial_field_adjustment_and_volume_change():
    dates = pd.to_datetime(['2026-09-15', '2026-09-16'])
    raw = pd.DataFrame({'open': ['1', '2'], 'high': ['2', '3'], 'low': ['.5', '1'],
                        'close': ['1', '2'], 'volume': ['100', '200']}, index=dates)
    adjusted = raw.copy()
    for field in ['open', 'high', 'low', 'close']:
        adjusted[field] = (adjusted[field].astype(float) * 20).astype(str)
    result = basis_diagnostics(raw, adjusted)
    assert result['inconsistent_OHLC_factor_dates'] == []
    assert result['different_volume_dates'] == []
    adjusted.loc[dates[0], 'high'] = '2'
    adjusted.loc[dates[1], 'volume'] = '10'
    result = basis_diagnostics(raw, adjusted)
    assert result['inconsistent_OHLC_factor_dates'] == ['2026-09-15']
    assert result['different_volume_dates'] == ['2026-09-16']
