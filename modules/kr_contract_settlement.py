"""Settlement from adjusted daily bars; missing bars are never losing/winning trades."""
from __future__ import annotations

import math
import pandas as pd


def settle(bars, sessions, signal_date, horizon, tp=.05, entry_mode="next_open"):
    """Entry day counts for next-open; close entry starts counting the next session.

    Entire horizon must be observed. A halted scheduled entry is unfilled, not a
    delayed entry. A halted terminal exit remains pending, never a synthetic fill.
    """
    day = pd.Timestamp(signal_date)
    future = [pd.Timestamp(d) for d in sessions if pd.Timestamp(d) > day]
    if not future:
        return {"status": "pending"}
    g = bars.set_index("date").sort_index()
    if not g.index.is_unique:
        return {"status": "data_error", "reason": "duplicate_price_date"}
    entry_day = future[0] if entry_mode == "next_open" else day
    if entry_day not in g.index:
        return {"status": "data_error", "reason": "missing_entry_bar"}
    first = g.loc[entry_day]
    price = float(first["adj_open" if entry_mode == "next_open" else "adj_close"])
    volume = float(first["volume"])
    if not math.isfinite(price) or not math.isfinite(volume):
        return {"status": "data_error", "reason": "invalid_entry_bar"}
    if price <= 0 or volume == 0:
        return {"status": "unfilled_entry", "reason": "scheduled_entry_suspended",
                "entry_date": str(entry_day.date())}
    if len(future) < horizon:
        return {"status": "pending"}
    window = future[:horizon]
    if any(d not in g.index for d in window):
        return {"status": "data_error", "reason": "missing_horizon_bar"}
    w = g.loc[window]
    target = price * (1 + tp)
    for i, (date, bar) in enumerate(w.iterrows()):
        if bar["volume"] > 0 and bar["adj_high"] >= target:
            op = float(bar["adj_open"])
            if not math.isfinite(op) or op <= 0:
                return {"status": "data_error", "reason": "invalid_touch_open"}
            fill = target if entry_mode == "next_open" and i == 0 else max(target, op)
            return {"status": "resolved", "entry_open": price, "touch": 1,
                    "policy_ret": (fill / price - 1) * 100, "exit_date": str(date.date())}
    last = w.iloc[-1]
    if last["volume"] <= 0 or last["adj_open"] <= 0:
        return {"status": "pending", "reason": "scheduled_exit_suspended"}
    close = float(last["adj_close"])
    if not math.isfinite(close) or close <= 0:
        return {"status": "data_error", "reason": "invalid_exit_bar"}
    return {"status": "resolved", "entry_open": price, "touch": 0,
            "policy_ret": (close / price - 1) * 100, "exit_date": str(window[-1].date())}
