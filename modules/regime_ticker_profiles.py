from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


def _default_profile_path() -> Path:
    raw = os.getenv("AG_REGIME_PROFILE_PATH", "models/regime_ticker_profiles.json")
    return Path(raw)


def resolve_profile_regime(market_gate: str | None) -> str:
    gate = str(market_gate or "").strip().upper()
    if gate in {"BULL", "BEAR", "NEUTRAL"}:
        return gate
    if gate == "GREEN":
        return "BULL"
    if gate == "RED":
        return "BEAR"
    return "NEUTRAL"


def resolve_profile_market(market_type: str | None, ticker: str | None) -> str:
    ticker = str(ticker or "").upper()
    market_type = str(market_type or "").upper()
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    if market_type in {"KOSPI", "KOSDAQ", "US", "AMEX"}:
        return "US" if market_type in {"US", "AMEX"} else market_type
    return "US"


@lru_cache(maxsize=4)
def _load_profiles_cached(path_str: str) -> Dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_profiles(path: Optional[str] = None) -> Dict[str, Any]:
    return _load_profiles_cached(str(Path(path) if path else _default_profile_path()))


def get_ticker_profile(
    *,
    ticker: str,
    market_type: str | None,
    market_gate: str | None,
    min_signals: int = 3,
) -> Optional[Dict[str, Any]]:
    profiles = load_profiles()
    if not profiles:
        return None

    market = resolve_profile_market(market_type=market_type, ticker=ticker)
    regime = resolve_profile_regime(market_gate)
    market_bucket = profiles.get("profiles", {}).get(market, {})
    regime_bucket = market_bucket.get(regime, {})
    item = regime_bucket.get(str(ticker).upper())
    if not isinstance(item, dict):
        return None
    if int(item.get("signals", 0) or 0) < int(min_signals):
        return None
    return item


def compute_profile_adjustment(profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not profile:
        return {"score_adjustment": 0.0, "confidence": 0.0, "policy": "NONE"}

    signals = float(profile.get("signals", 0) or 0)
    avg_5d = float(profile.get("avg_5d_pct", 0.0) or 0.0)
    win_5d = float(profile.get("win_5d_pct", 0.0) or 0.0)
    rr = float(profile.get("risk_reward_ratio", 0.0) or 0.0)

    # Confidence rises with sample size but saturates quickly.
    sample_conf = min(1.0, math.log1p(max(signals, 0.0)) / math.log(10.0))
    edge = ((win_5d - 50.0) * 0.28) + (avg_5d * 0.9) + ((rr - 1.5) * 2.0)
    adjustment = max(-18.0, min(22.0, edge * sample_conf))
    policy = "POSITIVE" if adjustment > 1.5 else ("NEGATIVE" if adjustment < -1.5 else "NEUTRAL")
    return {
        "score_adjustment": round(adjustment, 1),
        "confidence": round(sample_conf, 3),
        "policy": policy,
    }


def apply_profile_to_setup(setup: Dict[str, Any], profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not setup or not profile:
        return setup

    try:
        entry_price = float(setup.get("Entry Price", 0) or 0)
        if entry_price <= 0:
            return setup

        stop_pct = float(profile.get("adaptive_stop_pct", 0.0) or 0.0)
        target_pct = float(profile.get("safe_take_profit_pct", 0.0) or 0.0)
        if stop_pct <= 0 or target_pct <= 0:
            return setup

        updated = dict(setup)
        updated["Legacy Stop Loss"] = setup.get("Stop Loss")
        updated["Legacy Target Price"] = setup.get("Target Price")
        updated["Stop Loss"] = entry_price * (1.0 - (stop_pct / 100.0))
        updated["Target Price"] = entry_price * (1.0 + (target_pct / 100.0))
        updated["ATR Stop %"] = f"-{stop_pct:.1f}%"
        updated["ATR Target %"] = f"+{target_pct:.1f}%"
        risk = entry_price - float(updated["Stop Loss"])
        reward = float(updated["Target Price"]) - entry_price
        updated["Risk/Reward"] = f"1:{(reward / risk):.1f}" if risk > 0 else updated.get("Risk/Reward", "1:0")
        updated["Profile Stop %"] = round(stop_pct, 2)
        updated["Profile Target %"] = round(target_pct, 2)
        updated["Profile Signals"] = int(profile.get("signals", 0) or 0)
        updated["Profile Win 5D %"] = round(float(profile.get("win_5d_pct", 0.0) or 0.0), 1)
        updated["Profile Avg 5D %"] = round(float(profile.get("avg_5d_pct", 0.0) or 0.0), 2)
        return updated
    except Exception:
        return setup
