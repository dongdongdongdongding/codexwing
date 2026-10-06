"""Fixed preregistered contract replay; never changes signals, ledgers or routing."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.kr_contract_settlement import settle
from modules.trading_costs import KR_ROUNDTRIP_COST_PCT


def block_ci(rows, calendar, field, seed=20261007, draws=5000):
    """Five-market-session moving blocks, ratio of sums preserves pick weights."""
    if not rows:
        return None
    daily = pd.DataFrame(rows).groupby("date")[field].agg(["sum", "count"])
    a = daily.reindex(calendar, fill_value=0).to_numpy(dtype=float)
    if len(a) < 5:
        return None
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(a) - 4, size=(draws, int(np.ceil(len(a) / 5))))
    ix = (starts[..., None] + np.arange(5)).reshape(draws, -1)[:, :len(a)]
    sums = a[ix].sum(axis=1)
    usable = sums[:, 1] > 0
    return np.quantile(sums[usable, 0] / sums[usable, 1], [.025, .975]).tolist()


def metrics(rows, calendar):
    done = [r for r in rows if r["status"] == "resolved"]
    n = len(done)
    return {"selected": len(rows), "status_counts": dict(Counter(r["status"] for r in rows)),
            "n": n, "unique_dates": len({r["date"] for r in done}),
            "touch_rate": float(np.mean([r["touch"] for r in done])) if n else None,
            "touch_rate_block_ci95": block_ci(done, calendar, "touch"),
            "net_ev_pct": float(np.mean([r["net"] for r in done])) if n else None,
            "net_ev_block_ci95": block_ci(done, calendar, "net"),
            "worst_net_pct": min((r["net"] for r in done), default=None),
            "stress_ev_pct": {str(c): float(np.mean([r["policy_ret"] - c for r in done]))
                              if n else None for c in [.5, 1.0]}}


def controls(cache, scope, picks, records, groups, sessions, calendar):
    """Same-date liquidity pool; never rerank or choose a threshold using outcomes."""
    panel = pd.read_parquet(cache / "px_long.parquet", columns=["date", "code", "market", "liq", "volume"],
                            filters=[("date", ">=", pd.Timestamp(scope["signal_start"])),
                                     ("date", "<=", pd.Timestamp(scope["signal_end"]))])
    out = {}
    for market in ["KOSPI", "KOSDAQ"]:
        eligible = panel[(panel.market == market) & (panel.liq >= scope["universe_liq_krw"][market])
                         & (panel.volume > 0)].copy()
        if eligible.duplicated(["code", "date"]).any():
            raise ValueError("duplicate control key")
        day_pools, counts = {}, Counter()
        for day, frame in eligible.groupby("date"):
            date = str(day.date())
            selected = {p["ticker"].split(".")[0] for p in picks if p["date"] == date}
            values = []
            for code in frame.code.astype(str).str.zfill(6):
                if code in selected:
                    continue
                bars = groups.get(code)
                r = {"status": "data_error"} if bars is None else settle(bars, sessions, date, 10)
                counts[r["status"]] += 1
                if r["status"] == "resolved":
                    values.append(r["policy_ret"]-KR_ROUNDTRIP_COST_PCT)
            if values:
                day_pools[date] = np.array(values)
        done = [r for r in records if r["market"] == market and r["variant"] == "candidate_h10"
                and r["status"] == "resolved"]
        paired, missing = [], []
        for r in done:
            pool = day_pools.get(r["date"])
            if pool is None:
                missing.append(r["date"])
            else:
                paired.append({**r, "excess": r["net"]-float(pool.mean())})
        rng = np.random.default_rng(20261007)
        placebo = np.zeros(5000)
        sizes = Counter(r["date"] for r in paired)
        for day, n in sizes.items():
            pool = day_pools[day]
            if len(pool) < n:
                raise ValueError("control pool too small")
            placebo += np.array([rng.choice(pool, n, replace=False).sum() for _ in range(5000)])
        observed = sum(r["net"] for r in paired)
        # Timing diagnostic only: rotate the firing indicator over mature market
        # dates. This measures inherited gate timing, not cross-sectional alpha.
        dates = [d for d in calendar if d in day_pools]
        firing = np.array([d in sizes for d in dates])
        bench = np.array([day_pools[d].mean() for d in dates])
        timing = None
        if firing.any() and len(dates) > 1:
            actual = float(bench[firing].mean())
            shifted = [float(bench[np.roll(firing, k)].mean()) for k in range(1, len(dates))]
            timing = {"statistic": "mean control return on firing days", "actual": actual,
                      "p_ge": (1+sum(v >= actual for v in shifted))/(1+len(shifted)),
                      "rotations": len(shifted), "scope": "inherited timing diagnostic, not alpha test"}
        out[market] = {"paired_n": len(paired), "control_status_counts": dict(counts),
                       "missing_control_dates": sorted(set(missing)),
                       "same_day_net_excess_pp": float(np.mean([r["excess"] for r in paired])) if paired else None,
                       "excess_block_ci95": block_ci(paired, calendar, "excess"),
                       "random_ticker_placebo_p_ge": float((1+(placebo >= observed).sum())/5001) if paired else None,
                       "circular_timing_placebo": timing}
    return out


def run(root, cache, spec):
    scope = spec["scope"]
    start, end = scope["signal_start"], scope["signal_end"]
    source = root / "runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl"
    raw = source.read_bytes()
    ledger = [json.loads(line) for line in raw.splitlines() if line.strip()]
    picks = [r for r in ledger if start <= r["date"] <= end
             and r.get("top_k") == {"KOSPI": 3, "KOSDAQ": 1}.get(r.get("market"))
             and r.get("fire") is True and r.get("in_contract", True)
             and not r.get("stream_excluded")]
    keys = [(r["date"], r["ticker"]) for r in picks]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate published pick")
    px_path = cache / "px_delisted.parquet"
    px = pd.read_parquet(px_path, filters=[("date", ">=", pd.Timestamp(start))],
                         columns=["code", "date", "adj_open", "adj_high", "adj_low", "adj_close", "volume"])
    sessions = sorted(px.date.unique())
    calendar = [str(pd.Timestamp(d).date()) for d in sessions if str(pd.Timestamp(d).date()) <= end]
    groups = {str(c).zfill(6): g for c, g in px.groupby("code")}
    records = []
    for pick in picks:
        bars = groups.get(pick["ticker"].split(".")[0])
        for variant, horizon in [("baseline", int(pick["contract_h"])), ("candidate_h10", 10)]:
            result = ({"status": "data_error", "reason": "missing_ticker"} if bars is None else
                      settle(bars, sessions, pick["date"], horizon))
            rec = {"date": pick["date"], "ticker": pick["ticker"], "market": pick["market"],
                   "variant": variant, "horizon": horizon, **result}
            if result["status"] == "resolved":
                rec["net"] = result["policy_ret"] - KR_ROUNDTRIP_COST_PCT
            records.append(rec)
    results = {}
    for market in ["KOSPI", "KOSDAQ", "combined"]:
        for variant in ["baseline", "candidate_h10"]:
            rows = [r for r in records if r["variant"] == variant and
                    (market == "combined" or r["market"] == market)]
            results[f"{market}/{variant}"] = metrics(rows, calendar)
    # Evaluate identical mature picks; H5-only recently resolved rows cannot enter the pair.
    paired = pd.DataFrame([r for r in records if r["status"] == "resolved"])
    pairs = paired.pivot(index=["date", "ticker", "market"], columns="variant", values="net").dropna()
    paired_rows = [{"date": idx[0], "delta": r.candidate_h10-r.baseline} for idx, r in pairs.iterrows()]
    frequency = {}
    for market in ["KOSPI", "KOSDAQ", "combined"]:
        dates = {p["date"] for p in picks if market == "combined" or p["market"] == market}
        weeks = pd.DataFrame({"date": calendar})
        weeks["week"] = pd.to_datetime(weeks.date).dt.to_period("W-SUN").astype(str)
        weeks["fired"] = weeks.date.isin(dates).astype(int)
        weekly = weeks.groupby("week").fired.sum()
        frequency[market] = {"sessions": len(calendar), "firing_dates": len(dates),
                             "per_five_sessions": 5*len(dates)/len(calendar),
                             "calendar_week_firing_dates": weekly.to_dict()}
    control_results = controls(cache, scope, picks, records, groups, sessions, calendar)
    blockers = ["new_contract_forward_gate_not_available"]
    for market in ["KOSPI", "KOSDAQ"]:
        m = results[f"{market}/candidate_h10"]
        if m["n"] < 30 or m["unique_dates"] < 20:
            blockers.append(f"{market}:insufficient_mature_sample")
        if m["touch_rate"] is None or m["touch_rate"] < .70:
            blockers.append(f"{market}:touch_below_70pct")
        if not m["net_ev_block_ci95"] or m["net_ev_block_ci95"][0] <= 0:
            blockers.append(f"{market}:net_ci_not_positive")
        c = control_results[market]
        if not c["excess_block_ci95"] or c["excess_block_ci95"][0] <= 0:
            blockers.append(f"{market}:same_day_excess_ci_not_positive")
        if c["missing_control_dates"] or c["control_status_counts"].get("data_error", 0):
            blockers.append(f"{market}:control_price_data_errors")
    if not 2 <= frequency["combined"]["per_five_sessions"] <= 3:
        blockers.append("combined_frequency_outside_2_to_3")
    if any(r["status"] == "data_error" for r in records):
        blockers.append("price_data_errors")
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "prereg_id": spec["id"], "scope": scope, "ledger_sha256": hashlib.sha256(raw).hexdigest(),
            "price_source": str(px_path), "price_mtime_ns": px_path.stat().st_mtime_ns,
            "price_as_of": str(pd.Timestamp(max(sessions)).date()), "metrics": results,
            "same_day_controls": control_results,
            "frequency": frequency, "paired_h10_minus_baseline": {
                "n": len(pairs), "mean_net_delta_pp": float((pairs.candidate_h10-pairs.baseline).mean()),
                "block_ci95": block_ci(paired_rows, calendar, "delta")},
            "production_replacement_ready": False, "blockers": blockers, "records": records,
            "limitations": ["Retrospective re-contracting is not a pristine holdout or a calibrated individual probability.",
                            "No capital allocation, execution queue, impact or portfolio drawdown simulation.",
                            "Adjusted prices use repository corporate-action heuristics, not a verified exchange action feed."]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--cache", type=Path, default=Path.home()/"research_cache")
    ap.add_argument("--spec", type=Path, default=ROOT/"research/prereg_kr_touch10_20261007.json")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = run(args.root, args.cache, json.loads(args.spec.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k != "records"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
