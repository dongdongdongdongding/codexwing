#!/usr/bin/env python3
"""KR selective high-conviction shadow lane (swing-main-zls0 follow-up).

Research basis (8 OOS months walk-forward, RESEARCH_LOG §7): dropping forced top-2 for
top-1-with-abstention + touch-exit contract clears the +5%/trade bar at 3+ pick-days/week:
  KOSPI  rank-1 p>=0.65, exit +5% touch else 5d close: win 89.5%, EV +4.82 CI(3.01,6.72), 0/7 neg months
  KOSDAQ rank-1 (any p),  exit +10% touch else 5d close: win 76.6%, EV +5.18 CI(3.15,6.93), 1/8 neg months

This tool is a VIEW over the existing lane ledgers (no new picks, no routing): per date it
selects the rank-1 pick by p, tags PRIMARY (p>=threshold) vs CANDIDATE, and scores forward
performance using the exit-shadow fields (exit_t5_h5 / exit_t10_h5) that the lane resolvers
already record. Caveat: live p distribution may differ from the walk-forward sim (live model
trains on full history), so BOTH rank-1 and rank-1+threshold tracks are reported; threshold
recalibration on live p is a follow-up.

  python3 multi_agent/tools/report_kr_selective_shadow.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP = PROJECT_ROOT / "runtime_state" / "reports" / "experimental"
LANES = {
    "KOSPI": {"ledger": EXP / "kospi_intraday_swing_ledger.jsonl", "exit_key": "exit_t5_h5",
              "p_threshold": 0.65, "date_key": "date"},
    "KOSDAQ": {"ledger": EXP / "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "exit_key": "exit_t10_h5",
               "p_threshold": 0.65, "date_key": "date"},
}
REPORT_JSON = EXP / "kr_selective_shadow_latest.json"
REPORT_MD = EXP / "kr_selective_shadow_latest.md"


def _rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _p_value(row: Dict[str, Any]) -> float:
    for key in ("p", "p_cal", "probability", "success_probability"):
        v = row.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return float("nan")


def lane_view(market: str) -> Dict[str, Any]:
    cfg = LANES[market]
    rows = _rows(cfg["ledger"])
    bydate: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        d = str(r.get(cfg["date_key"]) or "")[:10]
        if d:
            bydate.setdefault(d, []).append(r)
    picks = []
    for d, items in sorted(bydate.items()):
        items = [r for r in items if np.isfinite(_p_value(r))]
        if not items:
            continue
        top = max(items, key=_p_value)
        p = _p_value(top)
        picks.append({"date": d, "ticker": top.get("ticker"), "p": round(p, 4),
                      "tier": "PRIMARY" if p >= cfg["p_threshold"] else "CANDIDATE",
                      "mkt_state": top.get("mkt_state"),
                      "exit_ret": top.get(cfg["exit_key"]), "ret3d": top.get("ret3d")})

    def _summ(sel: List[Dict[str, Any]]) -> Dict[str, Any]:
        res = [x for x in sel if isinstance(x.get("exit_ret"), (int, float))]
        if not res:
            return {"n": 0}
        rets = [float(x["exit_ret"]) for x in res]
        return {"n": len(res), "ev_avg": round(float(np.mean(rets)), 2),
                "win_pct": round(float(np.mean([r > 0.3 for r in rets])) * 100, 1),
                "worst": round(float(np.min(rets)), 2)}

    return {"market": market, "exit_contract": cfg["exit_key"], "p_threshold": cfg["p_threshold"],
            "picks_total_days": len(picks),
            "rank1_all": _summ(picks),
            "rank1_primary": _summ([x for x in picks if x["tier"] == "PRIMARY"]),
            "latest": picks[-5:]}


def main() -> None:
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "note": "observation-only view over lane ledgers; forward evidence for the selective "
                      "high-conviction contract (RESEARCH_LOG §7). No routing, no pick changes.",
              "lanes": {m: lane_view(m) for m in LANES}}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# KR selective high-conviction shadow — {report['generated_at'][:10]}", ""]
    for m, lv in report["lanes"].items():
        lines.append(f"## {m} (exit={lv['exit_contract']}, p>={lv['p_threshold']})")
        lines.append(f"- days with rank-1 pick: {lv['picks_total_days']}")
        lines.append(f"- rank-1 all: {lv['rank1_all']}")
        lines.append(f"- rank-1 PRIMARY: {lv['rank1_primary']}")
        for x in lv["latest"]:
            lines.append(f"  - {x['date']} {x['ticker']} p={x['p']} [{x['tier']}] state={x.get('mkt_state')} exit={x['exit_ret']}")
        lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({m: report["lanes"][m]["rank1_all"] for m in report["lanes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
