#!/usr/bin/env python3
"""Regime event library (재귀 연구의 축적 자산 — 희소한 레짐 이벤트를 자본처럼 큐레이션).

8y equal-weight liquid-pool levels (§6 construction) -> episode detection:
  CRASH    peak-to-trough <= -10% within <=40 sessions
  MELTUP   trough-to-peak >= +15% within <=40 sessions
  (나머지 구간은 CHOP으로 간주 — 라이브러리엔 이벤트만 기록)
Per event: depth/magnitude, duration, and the §6 profile evaluation inside the event —
momentum-profile vs oversold-profile mean exec_5d (which style won). Every new strategy
should be evaluated against this library as standard practice; it also feeds P4
meta-labeling context features (event phase at pick date).

Output: runtime_state/long_term/learning/regime_event_library.json
        runtime_state/reports/learning/regime_event_library_latest.md

  python3 multi_agent/tools/build_regime_event_library.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = PROJECT_ROOT / "runtime_state" / "long_term" / "learning" / "regime_event_library.json"
OUT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "learning" / "regime_event_library_latest.md"
LIQ = {"KOSPI": 100e8, "KOSDAQ": 30e8}
CRASH_TH, MELT_TH, MAX_LEN = -10.0, 15.0, 40


def detect_events(lvl: pd.Series, market: str) -> list:
    """Zigzag-style episode detection on the pool level series."""
    events = []
    dates = lvl.index
    v = lvl.values
    i = 0
    n = len(v)
    while i < n - 5:
        # look for local extreme swings within MAX_LEN
        win_end = min(i + MAX_LEN, n - 1)
        seg = v[i:win_end + 1]
        rel = (seg / v[i] - 1) * 100
        lo_j, hi_j = int(np.argmin(rel)), int(np.argmax(rel))
        if rel[lo_j] <= CRASH_TH and (hi_j > lo_j or rel[hi_j] < -rel[lo_j] / 2):
            j = i + lo_j
            events.append({"market": market, "type": "CRASH",
                           "start": str(dates[i].date()), "end": str(dates[j].date()),
                           "magnitude_pct": round(float(rel[lo_j]), 1), "sessions": int(lo_j)})
            i = j + 1
            continue
        if rel[hi_j] >= MELT_TH:
            j = i + hi_j
            events.append({"market": market, "type": "MELTUP",
                           "start": str(dates[i].date()), "end": str(dates[j].date()),
                           "magnitude_pct": round(float(rel[hi_j]), 1), "sessions": int(hi_j)})
            i = j + 1
            continue
        i += 5
    # merge adjacent same-type overlapping events
    merged = []
    for e in events:
        if merged and merged[-1]["type"] == e["type"] and merged[-1]["end"] >= e["start"]:
            merged[-1]["end"] = max(merged[-1]["end"], e["end"])
            merged[-1]["magnitude_pct"] = round(merged[-1]["magnitude_pct"] + e["magnitude_pct"], 1)
        else:
            merged.append(dict(e))
    return merged


def main() -> None:
    cols = ["code", "date", "market", "liq", "ret_1d", "ret_20d", "ret_5d", "dist_hi20", "rsi14", "exec_5d"]
    px = pd.read_parquet(os.path.expanduser("~/research_cache/px_long.parquet"), columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px["exec_5d"] = px["exec_5d"].replace([np.inf, -np.inf], np.nan)
    lib = []
    for mkt in ("KOSPI", "KOSDAQ"):
        d = px[(px["market"] == mkt) & (px["liq"] >= LIQ[mkt])]
        mret = d.groupby("date")["ret_1d"].mean().sort_index()
        lvl = (1 + mret / 100).cumprod()
        events = detect_events(lvl, mkt)
        # profile evaluation inside each event (§6: momentum vs oversold, exec_5d)
        dd = d.dropna(subset=["exec_5d"]).copy()
        dd["r20_rank"] = dd.groupby("date")["ret_20d"].rank(pct=True)
        dd["r5_rank"] = dd.groupby("date")["ret_5d"].rank(pct=True)
        mom = (dd["r20_rank"] >= 0.9) & (dd["dist_hi20"] >= -4)
        ovs = (dd["r5_rank"] <= 0.1) & (dd["rsi14"] < 35)
        for e in events:
            m = (dd["date"] >= e["start"]) & (dd["date"] <= e["end"])
            e["pool_ev5"] = round(float(dd.loc[m, "exec_5d"].mean()), 2) if m.any() else None
            e["momentum_ev5"] = round(float(dd.loc[m & mom, "exec_5d"].mean()), 2) if (m & mom).any() else None
            e["oversold_ev5"] = round(float(dd.loc[m & ovs, "exec_5d"].mean()), 2) if (m & ovs).any() else None
            e["winner_style"] = ("MOMENTUM" if (e["momentum_ev5"] or -99) > (e["oversold_ev5"] or -99) else "OVERSOLD") \
                if (e["momentum_ev5"] is not None or e["oversold_ev5"] is not None) else None
        lib += events
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "definition": {"CRASH": f"<= {CRASH_TH}% within {MAX_LEN} sessions",
                             "MELTUP": f">= +{MELT_TH}% within {MAX_LEN} sessions",
                             "profiles": "§6: momentum=top-decile ret_20d & near-high; oversold=bottom-decile ret_5d & rsi<35"},
              "events": lib}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Regime event library — {report['generated_at'][:10]} ({len(lib)} events, 8y)", "",
             "| Market | Type | Start | End | Mag% | Sess | Pool EV5 | Mom EV5 | Ovs EV5 | Winner |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---|"]
    for e in sorted(lib, key=lambda x: x["start"]):
        lines.append(f"| {e['market']} | {e['type']} | {e['start']} | {e['end']} | {e['magnitude_pct']} | "
                     f"{e['sessions']} | {e.get('pool_ev5', '–')} | {e.get('momentum_ev5', '–')} | "
                     f"{e.get('oversold_ev5', '–')} | {e.get('winner_style', '–')} |")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    from collections import Counter
    print(json.dumps({"events": len(lib), "by_type": dict(Counter(f"{e['market']}:{e['type']}" for e in lib)),
                      "winners": dict(Counter(e.get("winner_style") for e in lib if e.get("winner_style")))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
