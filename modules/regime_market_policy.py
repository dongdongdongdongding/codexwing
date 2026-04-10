from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from modules.regime_ticker_profiles import resolve_profile_market, resolve_profile_regime


def _default_policy_path() -> Path:
    raw = os.getenv("AG_REGIME_MARKET_POLICY_PATH", "models/regime_scan_policies.json")
    return Path(raw)


@lru_cache(maxsize=4)
def _load_policy_cached(path_str: str) -> Dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_market_policies(path: Optional[str] = None) -> Dict[str, Any]:
    return _load_policy_cached(str(Path(path) if path else _default_policy_path()))


def get_market_policy(*, market_type: str | None, ticker: str | None, market_gate: str | None) -> Optional[Dict[str, Any]]:
    payload = load_market_policies()
    if not payload:
        return None
    market = resolve_profile_market(market_type=market_type, ticker=ticker)
    regime = resolve_profile_regime(market_gate)
    return payload.get("policies", {}).get(market, {}).get(regime)


def evaluate_market_policy(
    *,
    alpha_score: float,
    ai_prob: float,
    market_type: str | None,
    ticker: str | None,
    market_gate: str | None,
) -> Dict[str, Any]:
    policy = get_market_policy(market_type=market_type, ticker=ticker, market_gate=market_gate) or {}
    if not policy:
        return {"policy": None, "score_adjustment": 0.0, "hard_reject": False, "reason": None}

    alpha_min = float(policy.get("alpha_min", 0.0) or 0.0)
    ai_min = float(policy.get("ai_min", 0.0) or 0.0)
    mode = str(policy.get("mode", "neutral"))
    pass_alpha = float(alpha_score) >= alpha_min
    pass_ai = float(ai_prob) >= ai_min
    passed = pass_alpha and pass_ai

    score_adjustment = 0.0
    hard_reject = False
    reason = None

    if mode == "favorable":
        score_adjustment = 8.0 if passed else -6.0
        reason = "MARKET_POLICY_THRESHOLD_FAIL" if not passed else None
    elif mode == "cautious":
        score_adjustment = 3.0 if passed else -8.0
        reason = "MARKET_POLICY_THRESHOLD_FAIL" if not passed else None
    elif mode == "avoid":
        score_adjustment = -14.0 if not passed else -6.0
        hard_reject = not passed
        reason = "MARKET_POLICY_AVOID"
    else:
        score_adjustment = 1.0 if passed else -3.0
        reason = "MARKET_POLICY_THRESHOLD_FAIL" if not passed else None

    return {
        "policy": policy,
        "score_adjustment": round(score_adjustment, 1),
        "hard_reject": bool(hard_reject),
        "reason": reason,
        "passed": bool(passed),
        "mode": mode,
    }
