from __future__ import annotations

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo


KR_TZ = ZoneInfo("Asia/Seoul")
US_TZ = ZoneInfo("America/New_York")


def normalize_market_key(value: str) -> str:
    text = str(value or "").strip().upper()
    if text in {"KOSPI", "KOSDAQ", "KR"}:
        return "KR"
    if text in {"NASDAQ", "NYSE", "AMEX", "S&P500", "SP500", "US"}:
        return "US"
    if text.endswith(".KS") or text.endswith(".KQ"):
        return "KR"
    return "US"


def is_market_open_now(market: str) -> bool:
    key = normalize_market_key(market)
    if key == "KR":
        now = datetime.now(KR_TZ)
        if now.weekday() >= 5:
            return False
        start = time(9, 0)
        end = time(15, 30)
        return start <= now.time() <= end

    now = datetime.now(US_TZ)
    if now.weekday() >= 5:
        return False
    start = time(9, 30)
    end = time(16, 0)
    return start <= now.time() <= end


def live_mode_enabled(market: str) -> bool:
    force = str(os.getenv("AG_FORCE_LIVE_SCAN_MODE", "")).strip().lower()
    if force in {"1", "true", "yes", "on"}:
        return True
    if force in {"0", "false", "no", "off"}:
        return False
    return is_market_open_now(market)


def context_ttl_seconds(market: str, *, open_seconds: int, closed_seconds: int) -> int:
    return int(open_seconds if live_mode_enabled(market) else closed_seconds)

