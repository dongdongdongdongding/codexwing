#!/usr/bin/env python3
"""Pick autopsy collector (재귀 연구 루프의 가설 생성 기질).

Every resolved pick is a labeled experiment. This tool accumulates, per pick:
pick-time attributes (p, tier, liq, contract) + market context (drawdown state at pick
date, historical series) + outcome + a rule-based failure/success mode tag. The weekly
mode×lane×state distribution is the raw material for data-born hypotheses — e.g. if 60%
of LOSS_TAIL comes from RISK_OFF entries in one lane, that's a discovered research lead,
not an a-priori guess.

Output: runtime_state/long_term/learning/pick_autopsy.jsonl (upsert by lane|date|ticker)
        runtime_state/reports/learning/pick_autopsy_summary_latest.md

  python3 multi_agent/tools/build_pick_autopsy.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
EXP = PROJECT_ROOT / "runtime_state" / "reports" / "experimental"
USR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"
OUT = PROJECT_ROOT / "runtime_state" / "long_term" / "learning" / "pick_autopsy.jsonl"
SUMMARY = PROJECT_ROOT / "runtime_state" / "reports" / "learning" / "pick_autopsy_summary_latest.md"

# lane: (ledger, realized-return field(s) in priority order, target_pct, market for state)
LANES = {
    "kospi_intraday": (EXP / "kospi_intraday_swing_ledger.jsonl", ["exit_t5_h5", "ret3d"], 5.0, "KOSPI"),
    "kosdaq_intraday": (EXP / "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", ["exit_t10_h5", "ret3d"], 10.0, "KOSDAQ"),
    "swing_candidate": (EXP / "kr_swing_candidate_ledger.jsonl", ["policy_ret"], 5.0, None),
    "swing_ensemble": (EXP / "swing_ensemble_ledger.jsonl", ["first_touch_ret"], 5.0, None),
    "b_market_neutral": (PROJECT_ROOT / "b_engine" / "data" / "b_shadow.jsonl", ["alpha"], None, "KOSDAQ"),
    "nasdaq_session_tape": (USR / "nasdaq_session_tape_ledger.jsonl", ["policy_ret"], 5.0, None),
}


def _rows(fp: Path) -> List[Dict[str, Any]]:
    if not fp.exists():
        return []
    out = []
    for l in fp.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def market_state_series() -> Dict[str, pd.Series]:
    """§6 construction, full history: per-market RISK_OFF/NORMAL by date."""
    px = pd.read_parquet(os.path.expanduser("~/research_cache/px_long.parquet"),
                         columns=["date", "market", "liq", "ret_1d"])
    px["date"] = pd.to_datetime(px["date"])
    out = {}
    for mkt, floor in (("KOSPI", 100e8), ("KOSDAQ", 30e8)):
        d = px[(px["market"] == mkt) & (px["liq"] >= floor)]
        mret = d.groupby("date")["ret_1d"].mean().sort_index()
        lvl = (1 + mret / 100).cumprod()
        ro = (((lvl / lvl.rolling(20).max() - 1) * 100 < -5) | ((lvl / lvl.shift(5) - 1) * 100 < -3))
        out[mkt] = ro.map({True: "RISK_OFF", False: "NORMAL"})
    return out


def mode_tag(ret: float, target: Optional[float]) -> str:
    if target is not None and ret >= target * 0.9:
        return "WIN_TOUCH"
    if ret > 0.3:
        return "WIN_DRIFT"
    if ret > -3:
        return "LOSS_SHALLOW"
    if ret > -7:
        return "LOSS_DEEP"
    return "LOSS_TAIL"


def main() -> None:
    states = market_state_series()
    existing = {f"{r['lane']}|{r['date']}|{r['ticker']}" for r in _rows(OUT)}
    added = []
    for lane, (fp, fields, target, state_mkt) in LANES.items():
        for r in _rows(fp):
            ret = next((float(r[f]) for f in fields if isinstance(r.get(f), (int, float))), None)
            if ret is None:
                continue
            date = str(r.get("date") or r.get("scan_date") or "")[:10]
            ticker = str(r.get("ticker") or r.get("symbol") or r.get("code") or "")
            key = f"{lane}|{date}|{ticker}"
            if not date or not ticker or key in existing:
                continue
            mkt = state_mkt or ("KOSPI" if ticker.endswith(".KS") else ("KOSDAQ" if ticker.endswith(".KQ") else None))
            st = None
            if mkt in states:
                try:
                    st = states[mkt].asof(pd.Timestamp(date))
                except Exception:
                    st = None
            rec = {"lane": lane, "date": date, "ticker": ticker, "ret": round(ret, 2),
                   "mode": mode_tag(ret, target),
                   "mkt_state": r.get("mkt_state") or st,
                   "p": r.get("p") or r.get("p_raw") or r.get("pred_alpha_5d"),
                   "tier": r.get("tier"),
                   "dow": pd.Timestamp(date).day_name()[:3] if date else None,
                   "collected_at": datetime.now(timezone.utc).isoformat()}
            added.append(rec)
            existing.add(key)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as fh:
        for rec in added:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    allrows = _rows(OUT)
    df = pd.DataFrame(allrows)
    lines = [f"# Pick autopsy — {datetime.now(timezone.utc).date()} (총 {len(df)}건, 신규 {len(added)})", ""]
    if len(df):
        lines.append("## mode × lane")
        lines.append("```\n" + df.pivot_table(index="lane", columns="mode", values="ret", aggfunc="size", fill_value=0).to_string() + "\n```")
        lines.append("")
        lines.append("## mode × mkt_state (가설 리드: 상태별 실패 편중)")
        lines.append("```\n" + df.pivot_table(index="mkt_state", columns="mode", values="ret", aggfunc="size", fill_value=0).to_string() + "\n```")
        lines.append("")
        tail = df[df["mode"] == "LOSS_TAIL"]
        if len(tail):
            lines.append(f"## LOSS_TAIL 명부 ({len(tail)}건 — 최우선 부검 대상)")
            for _, r in tail.sort_values("ret").head(15).iterrows():
                lines.append(f"- {r['date']} {r['lane']} {r['ticker']} {r['ret']}% p={r.get('p')} state={r.get('mkt_state')}")
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(df), "added": len(added),
                      "modes": df["mode"].value_counts().to_dict() if len(df) else {}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
