from __future__ import annotations

import os
from typing import Dict, Tuple


PROFILE_ENV_PRESETS: Dict[str, Dict[str, str]] = {
    "prod": {
        "AG_US_SIGNAL_LOOKBACK": "10",
        "AG_US_SIGNAL_MIN_HITS": "1",
        "AG_US_HARD_MIN_ALPHA": "40",
        "AG_US_HARD_MIN_ALPHA_DOWN": "55",
        "AG_US_HARD_AMEX_RS_MIN": "-5",
        "AG_AMEX_MOONSHOT_MIN_PRICE": "0.7",
        "AG_AMEX_MOONSHOT_PREFERRED_MAX_PRICE": "7.0",
        "AG_AMEX_MOONSHOT_MAX_PRICE": "25",
        "AG_AMEX_MOONSHOT_MIN_ALPHA": "28",
        "AG_AMEX_MOONSHOT_MIN_ALPHA_DOWN": "40",
        "AG_AMEX_MOONSHOT_MIN_VOLUME_RATIO": "1.8",
        "AG_AMEX_MOONSHOT_MIN_DAY_CHANGE": "4.0",
        "AG_AMEX_MOONSHOT_MIN_RANGE_PCT": "6.0",
        "AG_AMEX_MOONSHOT_MIN_RS": "-12.0",
        "AG_AMEX_MOONSHOT_BREAKOUT_LOOKBACK": "20",
        "AG_AMEX_MOONSHOT_MAX_CLOSE_TO_HIGH_PCT": "2.5",
        "AG_AMEX_MOONSHOT_SIGNAL_LOOKBACK": "20",
        "AG_AMEX_MOONSHOT_SIGNAL_MIN_HITS": "0",
        "AG_AMEX_MOONSHOT_MIN_SCORE": "62",
        "AG_AMEX_MOONSHOT_POLICY_OVERRIDE_SCORE": "78",
        "AG_AMEX_MOONSHOT_SUB7_BONUS": "10.0",
        "AG_AMEX_MOONSHOT_SUB7_BREAKOUT_BONUS": "8.0",
        "AG_AMEX_RED_MIN_CONVICTION": "56",
        "AG_AMEX_SCAN_MIN_PROB": "42",
        "AG_AMEX_SCAN_MIN_CLEAN_PROB": "38",
        "AG_KOSDAQ_RED_MIN_CONVICTION": "64",
        "AG_KOSDAQ_RED_ALPHA_RELAX_FLOOR": "45",
        "AG_KOSDAQ_BEAR_DOWN_MIN_ALPHA": "45",
        "AG_KOSPI_UNIVERSE_MIN_AMOUNT": "12000000000",
        "AG_KOSDAQ_UNIVERSE_MIN_AMOUNT": "5000000000",
        "AG_KOSPI_MIN_TURNOVER": "10000000000",
        "AG_KOSDAQ_MIN_TURNOVER": "7000000000",
        "AG_INTRADAY_KOSPI_MIN_TURNOVER": "700000000",
        "AG_INTRADAY_KOSDAQ_MIN_TURNOVER": "300000000",
        "AG_INTRADAY_KR_MIN_VOLUME": "20000",
        "AG_INTRADAY_US_MIN_TURNOVER": "1500000",
        "AG_INTRADAY_US_MIN_VOLUME": "40000",
        "AG_INTRADAY_AMEX_MIN_TURNOVER": "400000",
        "AG_INTRADAY_AMEX_MIN_VOLUME": "20000",
    },
    "dev": {
        "AG_US_SIGNAL_LOOKBACK": "20",
        "AG_US_SIGNAL_MIN_HITS": "0",
        "AG_US_HARD_MIN_ALPHA": "20",
        "AG_US_HARD_MIN_ALPHA_DOWN": "30",
        "AG_US_HARD_AMEX_RS_MIN": "-5",
        "AG_AMEX_MOONSHOT_MIN_PRICE": "0.5",
        "AG_AMEX_MOONSHOT_PREFERRED_MAX_PRICE": "7.0",
        "AG_AMEX_MOONSHOT_MAX_PRICE": "30",
        "AG_AMEX_MOONSHOT_MIN_ALPHA": "22",
        "AG_AMEX_MOONSHOT_MIN_ALPHA_DOWN": "34",
        "AG_AMEX_MOONSHOT_MIN_VOLUME_RATIO": "1.5",
        "AG_AMEX_MOONSHOT_MIN_DAY_CHANGE": "3.0",
        "AG_AMEX_MOONSHOT_MIN_RANGE_PCT": "5.0",
        "AG_AMEX_MOONSHOT_MIN_RS": "-15.0",
        "AG_AMEX_MOONSHOT_BREAKOUT_LOOKBACK": "20",
        "AG_AMEX_MOONSHOT_MAX_CLOSE_TO_HIGH_PCT": "3.0",
        "AG_AMEX_MOONSHOT_SIGNAL_LOOKBACK": "25",
        "AG_AMEX_MOONSHOT_SIGNAL_MIN_HITS": "0",
        "AG_AMEX_MOONSHOT_MIN_SCORE": "56",
        "AG_AMEX_MOONSHOT_POLICY_OVERRIDE_SCORE": "72",
        "AG_AMEX_MOONSHOT_SUB7_BONUS": "8.0",
        "AG_AMEX_MOONSHOT_SUB7_BREAKOUT_BONUS": "6.0",
        "AG_AMEX_RED_MIN_CONVICTION": "52",
        "AG_AMEX_SCAN_MIN_PROB": "38",
        "AG_AMEX_SCAN_MIN_CLEAN_PROB": "34",
        "AG_KOSDAQ_RED_MIN_CONVICTION": "60",
        "AG_KOSDAQ_RED_ALPHA_RELAX_FLOOR": "40",
        "AG_KOSDAQ_BEAR_DOWN_MIN_ALPHA": "40",
        "AG_KOSPI_UNIVERSE_MIN_AMOUNT": "8000000000",
        "AG_KOSDAQ_UNIVERSE_MIN_AMOUNT": "3000000000",
        "AG_KOSPI_MIN_TURNOVER": "8000000000",
        "AG_KOSDAQ_MIN_TURNOVER": "5000000000",
        "AG_INTRADAY_KOSPI_MIN_TURNOVER": "500000000",
        "AG_INTRADAY_KOSDAQ_MIN_TURNOVER": "200000000",
        "AG_INTRADAY_KR_MIN_VOLUME": "15000",
        "AG_INTRADAY_US_MIN_TURNOVER": "1000000",
        "AG_INTRADAY_US_MIN_VOLUME": "30000",
        "AG_INTRADAY_AMEX_MIN_TURNOVER": "300000",
        "AG_INTRADAY_AMEX_MIN_VOLUME": "15000",
    },
}


def normalize_profile_name(profile: str | None) -> str:
    raw = str(profile or "").strip().lower()
    if raw in PROFILE_ENV_PRESETS:
        return raw
    return "prod"


def apply_scan_gate_profile(profile: str | None) -> Tuple[str, Dict[str, str]]:
    """Apply profile defaults into environment without overriding explicit env values.

    Returns:
      (resolved_profile_name, applied_defaults)
    """
    resolved = normalize_profile_name(profile)
    preset = PROFILE_ENV_PRESETS[resolved]
    applied: Dict[str, str] = {}
    for key, value in preset.items():
        if os.getenv(key) is None:
            os.environ[key] = value
            applied[key] = value
    return resolved, applied
