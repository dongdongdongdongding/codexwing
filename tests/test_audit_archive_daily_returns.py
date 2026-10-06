import pandas as pd
import pytest
from multi_agent.tools.audit_archive_daily_returns import audit


def inputs():
    days = pd.bdate_range('2026-09-01', periods=7)
    prices = pd.DataFrame({'code': ['000001']*7, 'date': days, 'close': [100, 50, 51, 52, 53, 54, 55],
                           'adj_close': [50, 50, 51, 52, 53, 54, 55], 'volume': [1]*7})
    row = {'id': 1, 'ticker': '000001.KS', 'run_id': 'RUN-1', 'base_trade_date': '2026-09-01',
           'recommended_at': '2026-09-01T08:00:00Z', 'validation_excluded': False,
           'return_1d_pct': -50., 'return_3d_pct': 4., 'return_5d_pct': 123.}
    return days, prices, pd.DataFrame([row])


def test_split_like_path_distinguishes_raw_adjusted_and_unexplained():
    days, prices, rows = inputs()
    result = audit(rows, prices, days)
    assert result['horizons']['1']['all_rows'] == {'matches_raw_only': 1}
    assert result['horizons']['3']['all_rows'] == {'matches_adjusted': 1}
    assert result['horizons']['5']['all_rows'] == {'mismatch_both': 1}
    assert result['mutations'] == 0


def test_missing_session_never_compressed_and_stale_source_not_mature():
    days, prices, rows = inputs()
    result = audit(rows, prices.drop(index=2), days)
    assert result['horizons']['3']['all_rows'] == {'missing_ticker_session_price': 1}
    result = audit(rows, prices.iloc[:3], days)
    assert result['horizons']['3']['all_rows'] == {'adjusted_source_not_current_to_horizon': 1}


def test_zero_volume_valuation_recorded_not_executable_and_exclusions_preserved():
    days, prices, rows = inputs()
    prices.loc[1, 'volume'] = 0
    rows['validation_excluded'] = True
    result = audit(rows, prices, days)
    assert result['differences'][0]['has_zero_volume_session'] is True
    assert result['horizons']['1']['not_marked_excluded'] == {}


def test_us_and_model_rows_explicitly_unreviewed():
    days, prices, rows = inputs()
    rows = pd.concat([rows, rows.assign(ticker='AAPL'), rows.assign(run_id='SWING-CAND-20260901')])
    result = audit(rows, prices, days)
    assert result['scope'] == {'archive_rows': 3, 'generic_KR_rows': 1,
                               'generic_non_KR_rows_unreviewed': 1, 'non_generic_rows_out_of_scope': 1}


def test_kst_date_boundary_flag_and_duplicate_price_rejected():
    days, prices, rows = inputs()
    rows['recommended_at'] = '2026-09-01T23:00:00Z'
    assert audit(rows, prices, days)['base_vs_recommended_KST_mismatches'][0]['recommended_KST'] == '2026-09-02'
    with pytest.raises(ValueError, match='duplicate_price_key'):
        audit(rows, pd.concat([prices, prices.iloc[:1]]), days)
