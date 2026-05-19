from __future__ import annotations

from typing import Any, Dict, List, Tuple


STRATEGY_FAMILY_POLICY_VERSION = "strategy_family_policy_v1"


def apply_strategy_family_policy(
    *,
    decision: str,
    strategy_family: str,
    market: str,
    scan_mode: str,
    target_horizon_days: int,
) -> Tuple[str, int, Dict[str, Any]]:
    family = _upper(strategy_family) or "UNKNOWN"
    market_key = _upper(market)
    mode = _upper(scan_mode)
    horizon = int(target_horizon_days or 0)
    rationale: List[str] = []
    risk_flags: List[str] = []

    # Matrix evidence refreshed 2026-05-19:
    # AMEX_MOONSHOT/AMEX/SWING n=53 has weak 1D/3D but 5D win=88.68%,
    # avg=+3.73%. Do not exclude it; route the holding contract to 5D.
    if family == "AMEX_MOONSHOT" and market_key in {"AMEX", "US", ""} and mode == "SWING":
        if horizon < 5:
            horizon = 5
        rationale.append("strategy_family_horizon_reroute=AMEX_MOONSHOT:5d")

    # UNKNOWN/KR/INTRADAY is mostly legacy missing-family data, so a blanket
    # drop would contaminate live decisions. The matrix is still bad enough
    # (1D win=13.72%, avg=-4.72%; 3D win=21.99%, avg=-3.49%) to block PRIORITY
    # until scanner rows carry an explicit strategy_family again.
    if family == "UNKNOWN" and market_key in {"KR", "KOSPI", "KOSDAQ"} and mode == "INTRADAY":
        capped = _demote_to_watchlist(decision)
        if capped != decision:
            decision = capped
            rationale.append("strategy_family_priority_cap=UNKNOWN_KR_INTRADAY")
        risk_flags.append("STRATEGY_FAMILY_UNKNOWN_KR_INTRADAY")

    return (
        decision,
        horizon,
        {
            "version": STRATEGY_FAMILY_POLICY_VERSION,
            "strategy_family": family,
            "market": market_key,
            "scan_mode": mode,
            "target_horizon_days": horizon,
            "rationale": rationale,
            "risk_flags": risk_flags,
        },
    )


def _demote_to_watchlist(decision: str) -> str:
    ranks = {
        "AVOID": 0,
        "OBSERVE": 1,
        "WATCHLIST": 2,
        "PRIORITY_WATCHLIST": 3,
    }
    by_rank = {value: key for key, value in ranks.items()}
    rank = ranks.get(_upper(decision), 1)
    return by_rank[min(rank, ranks["WATCHLIST"])]


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


__all__ = [
    "STRATEGY_FAMILY_POLICY_VERSION",
    "apply_strategy_family_policy",
]
