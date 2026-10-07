"""Naver's public KRX share-volume trend, with explicit observation evidence."""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import re
from zoneinfo import ZoneInfo

import pandas as pd
import requests

URL = 'https://m.stock.naver.com/front-api/stock/domestic/trend'


def _integer(value):
    if not isinstance(value, str) or not re.fullmatch(r'[+-]?\d+', value):
        raise ValueError('naver_missing_or_invalid_quantity')
    return int(value)


def parse_trend(payload, *, today: date, reference_session: str | None = None):
    if not isinstance(payload, dict) or payload.get('isSuccess') is not True:
        raise ValueError('naver_unsuccessful_response')
    items = (payload.get('result') or {}).get('items')
    if not isinstance(items, list) or len(items) < 10:
        raise ValueError('naver_insufficient_10_observations')
    rows, dates, reported_retail = [], [], []
    for item in items[:10]:
        day = date.fromisoformat(item['localTradedAt'])
        if day > today or (dates and day >= dates[-1]):
            raise ValueError('naver_future_duplicate_or_unordered_date')
        dates.append(day)
        krx = item.get('krx')
        if not isinstance(krx, dict):
            raise ValueError('naver_missing_krx_observation')
        values = {}
        for participant in ('foreign', 'organization', 'individual'):
            net = _integer(krx.get(participant + 'NetVolume'))
            buy = _integer(krx.get(participant + 'BuyVolume'))
            sell = _integer(krx.get(participant + 'SellVolume'))
            if buy < 0 or sell < 0 or net != buy - sell:
                raise ValueError('naver_inconsistent_net_volume')
            values[participant] = net
        volume = _integer(krx.get('tradingVolume'))
        if volume < 0 or (not rows and volume == 0):
            raise ValueError('naver_no_latest_trading_volume')
        rows.append({'날짜': day.isoformat(), 'Institution': values['organization'],
                     'Foreigner': values['foreign'], 'Retail': values['individual']})
        reported_retail.append(values['individual'])
    if reference_session and dates[0] < date.fromisoformat(reference_session):
        raise ValueError('naver_older_than_observed_previous_session')
    metadata = {
        'flow_contract_version': 'naver_krx_shares_v1',
        'flow_venue': 'KRX', 'flow_observation_count': 10,
        'retail_basis': 'reported_individual_net_volume',
        'reported_retail_1d': reported_retail[0],
        'reported_retail_3d': sum(reported_retail[:3]),
        'reported_retail_10d': sum(reported_retail),
        'flow_reference_session': reference_session,
        'flow_freshness_check': ('not_older_than_observed_previous_session'
                                 if reference_session else 'calendar_unavailable'),
    }
    return pd.DataFrame(rows), metadata


def fetch_naver_flow_frame(code, *, today: date | None = None):
    if not re.fullmatch(r'\d{6}', str(code)):
        raise ValueError('naver_invalid_stock_code')
    today = today or datetime.now(ZoneInfo('Asia/Seoul')).date()
    response = requests.get(URL, params={'code': str(code), 'exchangeType': 'KRX', 'size': 20},
                            headers={'User-Agent': 'Mozilla/5.0',
                                     'Referer': 'https://m.stock.naver.com/'}, timeout=5)
    response.raise_for_status()
    # A stale calendar cannot certify freshness. It can still reject a source
    # older than a market session known to have occurred before this request.
    reference, calendar_source = None, None
    try:
        from modules.market_sessions import price_sessions
        sessions, calendar_source = price_sessions('KR', today)
        if sessions:
            reference = sessions[-1]
    except (OSError, ValueError, RuntimeError):
        pass
    frame, metadata = parse_trend(response.json(), today=today, reference_session=reference)
    metadata.update(flow_response_sha256=hashlib.sha256(response.content).hexdigest(),
                    flow_received_at=datetime.now(ZoneInfo('UTC')).isoformat(),
                    flow_calendar_source=calendar_source)
    metadata["flow_contract"] = dict(metadata)
    return frame, metadata
