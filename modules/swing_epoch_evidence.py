"""Separate current issued swing configurations from the historical pooled lane.

Evidence is diagnostic until a matching preregistered research basis is approved.
The legacy pooled CONFIRM cannot confer publication eligibility on a new contract.
"""
from collections import Counter
import math

import numpy as np
import pandas as pd

from modules.trading_costs import KR_ROUNDTRIP_COST_PCT

SPECS = {
    "KOSPI": {"gate": "FIRE", "gate_kind": "mkt_weakness", "gate_q": .4,
              "top_k": 3, "contract_h": 10},
    "KOSDAQ": {"gate": "FIRE", "gate_kind": "mkt_weakness", "gate_q": .5,
               "top_k": 1, "contract_h": 5},
}


def block_ci(rows, calendar):
    if not rows or len(calendar) < 5:
        return None
    daily = pd.DataFrame(rows).groupby("date").net.agg(["sum", "count"])
    values = daily.reindex(calendar, fill_value=0).to_numpy(dtype=float)
    rng = np.random.default_rng(20261007)
    starts = rng.integers(0, len(values)-4, size=(5000, math.ceil(len(values)/5)))
    ix = (starts[..., None]+np.arange(5)).reshape(5000, -1)[:, :len(values)]
    sampled = values[ix].sum(axis=1)
    sampled = sampled[sampled[:, 1] > 0]
    return np.quantile(sampled[:, 0]/sampled[:, 1], [.025, .975]).tolist() if len(sampled) else None


def current_epochs(rows, sessions):
    result = {}
    for market, spec in SPECS.items():
        issued = [r for r in rows if r.get("market") == market and
                  all(r.get(k) == v for k,v in spec.items())]
        counts = Counter(r.get("date") for r in issued)
        ambiguous = {d for d,n in counts.items() if n > spec["top_k"]}
        # Never invent a historical rank to remove the losing/winning extra row.
        scoped = [r for r in issued if r.get("date") not in ambiguous and r.get("in_contract") is not False]
        done = [dict(date=r["date"], net=float(r["policy_ret"])-KR_ROUNDTRIP_COST_PCT)
                for r in scoped if isinstance(r.get("policy_ret"),(int,float))
                and not isinstance(r.get("policy_ret"),bool) and math.isfinite(r["policy_ret"])]
        dates = sorted({r["date"] for r in done})
        calendar = [d for d in sessions if dates and dates[0] <= d <= dates[-1]]
        ci = block_ci(done, calendar) if set(dates) <= set(calendar) else None
        unmet = []
        if len(done) < 30:
            unmet.append("n_below_30")
        if len(dates) < 20:
            unmet.append("unique_dates_below_20")
        if ci is None or ci[0] <= 0:
            unmet.append("positive_block_ci_not_established")
        # There is no frozen OOS expectation for this exact issued configuration
        # in the pooled legacy gate. Do not borrow its expectation or CONFIRM.
        unmet.append("matching_research_basis_not_validated")
        result[market] = {
            "scope": {"market":market, **spec}, "issued_picks":len(issued),
            "scoped_picks":len(scoped), "ambiguous_dates":sorted(ambiguous),
            "excluded_ambiguous_picks":sum(counts[d] for d in ambiguous),
            "n":len(done), "unique_dates":len(dates), "since":min((r["date"] for r in scoped),default=None),
            "fwd_ev":round(float(np.mean([r["net"] for r in done])),4) if done else None,
            "fwd_win":round(100*float(np.mean([r["net"] > 0 for r in done])),2) if done else None,
            "fwd_ci":ci, "ci_method":"5_market_session_moving_blocks_5000",
            "verdict":"OBSERVING", "confirm_qualified":False,
            "publication_block":True, "publication_block_reason":";".join(unmet),
            "basis":"current issued configuration; net > 0 is win, not calibrated touch probability"}
    return result
