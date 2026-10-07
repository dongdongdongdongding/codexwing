"""Shared readiness times for existing KR producers and their status consumer."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo('Asia/Seoul')
KRX_CLOSE = time(15, 30)
SETTLE_MINUTES = 10
SWING_READY = (datetime.combine(date(2000, 1, 1), KRX_CLOSE)
               + timedelta(minutes=SETTLE_MINUTES)).time()
INTRADAY_READY = time(15, 10)


def kst_now(now=None):
    value = now or datetime.now(KST)
    if value.tzinfo is None:
        raise ValueError('producer reference time must be timezone-aware')
    return value.astimezone(KST)


def ready_time(lane):
    if lane in ('kospi_swing', 'kosdaq_swing'):
        return SWING_READY
    if lane == 'kosdaq_intraday':
        return INTRADAY_READY
    raise ValueError(f'unknown KR producer: {lane}')


def eligible_session(sessions, lane, *, now=None):
    current = kst_now(now)
    today = current.date()
    include_today = current.time() >= ready_time(lane)
    parsed = [date.fromisoformat(str(day)[:10]) for day in sessions]
    eligible = [d for d in parsed if d < today or (d == today and include_today)]
    return max(eligible).isoformat() if eligible else None


def observed_sessions(*, now=None):
    """Read actual price dates, including today's potentially unfinished bar."""
    from modules.market_sessions import price_sessions
    current = kst_now(now)
    return price_sessions('KR', current.date() + timedelta(days=1))
