from datetime import datetime, timezone
import json

import pandas as pd
import pytest

from modules import pipeline_status as status
from modules.kr_producer_calendar import KST, eligible_session
from multi_agent.tools import report_kr_swing_candidate as swing
from multi_agent.tools import report_kosdaq_intraday_vwap_guard as intraday

SESSIONS = ['2026-10-02', '2026-10-06', '2026-10-07']


@pytest.mark.parametrize('clock,swing_day,intraday_day', [
    ('09:00', '2026-10-06', '2026-10-06'),
    ('15:09', '2026-10-06', '2026-10-06'),
    ('15:10', '2026-10-06', '2026-10-07'),
    ('15:30', '2026-10-06', '2026-10-07'),
    ('15:39', '2026-10-06', '2026-10-07'),
    ('15:40', '2026-10-07', '2026-10-07'),
    ('20:00', '2026-10-07', '2026-10-07'),
])
def test_reference_matches_both_actual_producer_cutoffs(monkeypatch, clock, swing_day, intraday_day):
    hour, minute = map(int, clock.split(':'))
    now = datetime(2026, 10, 7, hour, minute, tzinfo=KST)
    px = pd.DataFrame({'date': pd.to_datetime(SESSIONS)})
    assert swing._drop_unconfirmed_session(px, now=now)['date'].max().date().isoformat() == swing_day
    monkeypatch.setattr(intraday, '_now_kst', lambda: now)
    monkeypatch.setattr(intraday.pd, 'read_parquet', lambda *a, **k: px)
    assert intraday._trade_date_arg(None) == intraday_day.replace('-', '')
    assert eligible_session(SESSIONS, 'kospi_swing', now=now) == swing_day
    assert eligible_session(SESSIONS, 'kosdaq_swing', now=now) == swing_day
    assert eligible_session(SESSIONS, 'kosdaq_intraday', now=now) == intraday_day


def test_observed_holiday_and_weekend_without_weekday_guess():
    for now in [datetime(2026, 10, 5, 20, tzinfo=KST), datetime(2026, 10, 4, 16, tzinfo=KST)]:
        assert eligible_session(SESSIONS, 'kospi_swing', now=now) == '2026-10-02'
    # UTC boundary crosses the calendar date in Korea.
    assert eligible_session(SESSIONS, 'kospi_swing', now=datetime(2026, 10, 6, 22, tzinfo=timezone.utc)) == '2026-10-06'
    with pytest.raises(ValueError, match='timezone-aware'):
        eligible_session(SESSIONS, 'kospi_swing', now=datetime(2026, 10, 7))


def write_reports(root, asof='2026-10-06'):
    exp = root / 'runtime_state/reports/experimental'
    exp.mkdir(parents=True)
    (exp / 'kr_swing_candidate_latest.json').write_text(json.dumps({
        'as_of': asof, 'picks': [], 'gate': {'KOSPI': {'gate': 'ABSTAIN', 'fire': False},
                                           'KOSDAQ': {'gate': 'ABSTAIN', 'fire': False}}}))
    (exp / 'kosdaq_intraday_1500_3d_t5_vwap_guard_latest.json').write_text(json.dumps({
        'trade_date': asof.replace('-', ''), 'scored_rows': 216, 'picks': []}))


def test_real_failure_shape_is_abstain_in_daytime_and_stale_after_cutoff(tmp_path):
    write_reports(tmp_path)
    before = status.kr_producer_status(tmp_path, sessions=SESSIONS, now=datetime(2026, 10, 7, 13, 38, tzinfo=KST))
    assert [r['status'] for r in before] == ['abstain', 'abstain', 'no_candidates']
    assert all(r['expected_as_of'] == '2026-10-06' for r in before)
    middle = status.kr_producer_status(tmp_path, sessions=SESSIONS, now=datetime(2026, 10, 7, 15, 10, tzinfo=KST))
    assert [r['status'] for r in middle] == ['abstain', 'abstain', 'stale']
    after = status.kr_producer_status(tmp_path, sessions=SESSIONS, now=datetime(2026, 10, 7, 15, 40, tzinfo=KST))
    assert all(r['status'] == 'stale' for r in after)


def test_missing_calendar_and_unconfirmed_report_never_look_current(tmp_path, monkeypatch):
    write_reports(tmp_path, '2026-10-07')
    now = datetime(2026, 10, 7, 13, tzinfo=KST)
    assert all(r['status'] == 'blocked' for r in status.kr_producer_status(tmp_path, sessions=SESSIONS, now=now))
    assert all(r['status'] == 'error' for r in status.kr_producer_status(tmp_path, sessions=[], now=now))
    def missing(**kw): raise FileNotFoundError('test missing calendar')
    monkeypatch.setattr(status, 'observed_sessions', missing)
    rows = status.kr_producer_status(tmp_path, now=now)
    assert all(r['status'] == 'error' and 'FileNotFoundError' in r['calendar_error'] for r in rows)


def test_web_consumer_uses_observed_cutoff_not_raw_daily_max(tmp_path, monkeypatch):
    from web.backend import services
    write_reports(tmp_path)
    monkeypatch.setattr(services, 'REPO', str(tmp_path))
    monkeypatch.setattr(status, 'kst_now', lambda now=None: datetime(2026, 10, 7, 13, 38, tzinfo=KST))
    monkeypatch.setattr(status, 'observed_sessions', lambda **kw: (SESSIONS, 'observed_test_calendar'))
    def forbidden(): raise AssertionError('raw maximum date must not decide producer freshness')
    monkeypatch.setattr(services, 'freshness', forbidden)
    rows = services.lane_status()
    assert [r['status'] for r in rows] == ['abstain', 'abstain', 'no_candidates']
    assert services.lane_status('kospi_swing') == rows[:1]
