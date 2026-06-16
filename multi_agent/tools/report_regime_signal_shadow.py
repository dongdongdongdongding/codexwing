#!/usr/bin/env python3
"""Shadow forward-tracker for the regime-conditional price signal (iter 5).

Runs the validated regime-conditional scorer (modules/regime_conditional_scorer) over a liquid KR
universe each day, ranks within regime, applies tail-aware sizing, records the picks, and -- on
later runs -- resolves the realized 5D outcome of past picks so the live edge is measured BEFORE
the signal is ever given a production role.

This is observation-only: it writes a report + a JSONL pick ledger, and never changes the live
scanner/planner. Validated OOS edge is thin (+~2pp win over base, down/chop reversal 62.6%) so
each pick carries a tail-aware position_factor; never trade unsized.

  python3 multi_agent/tools/report_regime_signal_shadow.py [--top-universe 120] [--top-picks 10]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.regime_conditional_scorer import compute_regime_score

LEDGER = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "regime_signal_shadow_ledger.jsonl"
REPORT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "regime_signal_shadow_latest.json"
REPORT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "regime_signal_shadow_latest.md"
COST_PCT = 0.6  # KR round-trip


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------

def tail_tier(dist_from_high_20d: Optional[float]) -> Dict[str, Any]:
    """Equal-risk-budget tail sizing from entry-time distance to the 20D high (validated tiers)."""
    if dist_from_high_20d is None:
        return {"tier": "UNKNOWN", "position_factor": 0.5, "suggested_stop_pct": -8.0}
    if dist_from_high_20d >= -4.0:
        return {"tier": "A", "position_factor": 1.0, "suggested_stop_pct": -8.0}
    if dist_from_high_20d >= -8.0:
        return {"tier": "B", "position_factor": 0.45, "suggested_stop_pct": -9.0}
    return {"tier": "C", "position_factor": 0.40, "suggested_stop_pct": -10.0}


def rank_and_pick(scored: List[Dict[str, Any]], top_picks: int) -> List[Dict[str, Any]]:
    """Rank scored candidates by regime score (desc) within each market and take the top N each."""
    picks: List[Dict[str, Any]] = []
    df = pd.DataFrame([s for s in scored if s.get("ok") and s.get("score") is not None])
    if df.empty:
        return picks
    for market, g in df.groupby("market"):
        g = g.sort_values("score", ascending=False).head(int(top_picks))
        for _, r in g.iterrows():
            tier = tail_tier(r.get("dist_hi20"))
            picks.append({
                "ticker": r["ticker"], "market": market,
                "regime": r.get("regime"), "factor": r.get("factor"),
                "score": round(float(r["score"]), 4),
                "ma60_dist": r.get("ma60_dist"), "dist_hi20": r.get("dist_hi20"),
                **tier,
            })
    return picks


def down_buy_scan_rows(picks, run_id: str, recommended_at: str):
    """Convert DOWN/chop-regime picks into market_scan_results payloads (the unification adapter).

    Only the DOWN/chop reversal leg -- the OOS-validated 75%+ slice -- becomes a production buy.
    Routing these through market_scan_results makes them outcome-tracked (update_realized_outcomes)
    AND learned (the archive export reads market_scan_results), so "what the user sees = what is
    tracked = what is learned" holds for this stream. Distinct decision/lane keep them separable
    from the legacy planner stream. UP/NORMAL picks are NOT written here (UP has no close-accuracy
    edge; NORMAL is observation until validated).
    """
    from modules.db_schema import build_scan_result_payload
    down = sorted([p for p in picks if str(p.get("regime")) == "down_chop"],
                  key=lambda p: -float(p.get("score") or 0.0))
    rows = []
    for i, p in enumerate(down, start=1):
        src = {
            "ticker": p["ticker"], "market_type": p["market"], "scan_mode": "SWING",
            "decision_score": p.get("score"), "run_id": run_id, "priority_rank": i,
            "decision": "REGIME_DOWN_BUY", "decision_bucket": "regime_down",
            "recommended_at": recommended_at, "selection_lane": "REGIME_DOWN",
        }
        rows.append(build_scan_result_payload(
            src, overrides={"market": p["market"], "recommended_at": recommended_at}))
    return rows


def down_buy_deep_rows(picks, run_id: str, recommended_at: str):
    """Convert DOWN/chop-regime picks into scan_deep_reports rows (the web/Discord surface).

    Writing these (under a distinct REGIME-DOWN run_id) puts the DOWN production buys into the SAME
    table the web and Discord render from, in the production `Top5` section -- so surface = archive
    = learning all show the same DOWN tickers/order. Mirrors down_buy_scan_rows (same selection).
    """
    from modules.candidate_interpretation import build_candidate_interpretation
    down = sorted([p for p in picks if str(p.get("regime")) == "down_chop"],
                  key=lambda p: -float(p.get("score") or 0.0))
    rows = []
    for i, p in enumerate(down, start=1):
        row = {
            "ticker": p["ticker"], "stock_name": p.get("stock_name") or p["ticker"],
            "market": p["market"], "run_id": run_id, "rank": i,
            "decision": "REGIME_DOWN_BUY", "decision_bucket": "regime_down",
            "signal_label": "REGIME_DOWN_BUY", "analysis_section": "Top5", "analysis_section_rank": i,
            "buy_score": p.get("score"), "generated_at": recommended_at,
            "selection_alignment": {"analysis_section": "Top5", "analysis_section_rank": i},
        }
        row["candidate_interpretation"] = build_candidate_interpretation(row)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def _build_universe(market: str, top_n: int) -> List[str]:
    import FinanceDataReader as fdr
    lst = fdr.StockListing(market)
    cap_col = next((c for c in lst.columns if str(c).lower() in ("marcap", "market_cap", "cap")), None)
    code_col = next((c for c in lst.columns if str(c).lower() in ("code", "symbol")), "Code")
    if cap_col:
        lst = lst.sort_values(cap_col, ascending=False)
    suffix = ".KS" if market == "KOSPI" else ".KQ"
    return [str(c) + suffix for c in lst[code_col].astype(str).head(int(top_n)).tolist()]


def _score_universe(top_universe: int) -> List[Dict[str, Any]]:
    import FinanceDataReader as fdr
    out: List[Dict[str, Any]] = []
    for market in ("KOSPI", "KOSDAQ"):
        idx_code = "KS11" if market == "KOSPI" else "KQ11"
        try:
            idx = fdr.DataReader(idx_code, "2025-12-01")
            iclose = pd.to_numeric(idx["Close"], errors="coerce").dropna()
        except Exception:
            continue
        for tkr in _build_universe(market, top_universe):
            try:
                h = fdr.DataReader(str(tkr).replace(".KS", "").replace(".KQ", ""), "2025-12-01")
            except Exception:
                continue
            if h is None or h.empty or "Close" not in h.columns:
                continue
            close = pd.to_numeric(h["Close"], errors="coerce").dropna()
            high = pd.to_numeric(h.get("High", h["Close"]), errors="coerce").dropna()
            r = compute_regime_score(close, high, iclose)
            r["ticker"] = tkr
            r["market"] = market
            out.append(r)
    return out


def _resolve_pending(today: str) -> Dict[str, Any]:
    """Resolve realized 5D return for picks whose 5-session window has elapsed; return summary."""
    import FinanceDataReader as fdr
    if not LEDGER.exists():
        return {"resolved": 0, "win_pct": None, "net_avg_pct": None}
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = False
    for row in rows:
        if row.get("realized_5d_pct") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.isna(d) or (pd.Timestamp(today) - d).days < 7:
            continue
        try:
            h = fdr.DataReader(str(row["ticker"]).replace(".KS", "").replace(".KQ", ""), str(d.date()))
            c = pd.to_numeric(h["Close"], errors="coerce").dropna()
            if len(c) >= 6:
                row["realized_5d_pct"] = round(float(c.iloc[5] / c.iloc[0] - 1) * 100, 4)
                changed = True
        except Exception:
            pass
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    res = [r["realized_5d_pct"] for r in rows if r.get("realized_5d_pct") is not None]
    if not res:
        return {"resolved": 0, "win_pct": None, "net_avg_pct": None}
    s = pd.Series(res)
    return {"resolved": len(res), "win_pct": round(float((s > 0).mean() * 100), 1),
            "net_avg_pct": round(float(s.mean() - COST_PCT), 3)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Regime-conditional signal shadow forward-tracker.")
    ap.add_argument("--top-universe", type=int, default=120)
    ap.add_argument("--top-picks", type=int, default=10)
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scored = _score_universe(args.top_universe)
    picks = rank_and_pick(scored, args.top_picks)

    # append today's picks to the ledger (unresolved)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in picks:
            fh.write(json.dumps({"date": today, "realized_5d_pct": None, **p}, ensure_ascii=False) + "\n")
    summary = _resolve_pending(today)

    # Unification adapter (flag-gated, default OFF): route DOWN/chop buys through
    # market_scan_results so surface = archive = learning. Stays OFF until the shadow ledger
    # confirms the live forward edge; deployment is then a single flag flip.
    persisted = 0
    deep_persisted = 0
    if os.getenv("AG_REGIME_DOWN_PRODUCTION", "0").strip() not in ("0", "", "false", "False"):
        run_id = "REGIME-DOWN-" + today.replace("-", "")
        recommended_at = datetime.now(timezone.utc).isoformat()
        rows = down_buy_scan_rows(picks, run_id, recommended_at)
        deep_rows = down_buy_deep_rows(picks, run_id, recommended_at)
        try:
            from modules.db_manager import DBManager
            db = DBManager()
            for payload in rows:                       # archive + learning
                db.upsert_scan_result(payload)
                persisted += 1
            if deep_rows:                              # web + Discord surface
                from modules.top_deep_report import upsert_reports_to_supabase
                res = upsert_reports_to_supabase(deep_rows)
                deep_persisted = int(res.get("rows_upserted", 0)) if isinstance(res, dict) else 0
        except Exception as exc:  # fail-safe: never break the shadow run on a write error
            persisted = -1
            print(json.dumps({"regime_down_persist_error": repr(exc)[:200]}, ensure_ascii=False))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "regime_signal_shadow_v1",
        "today": today,
        "scored": len(scored),
        "picks_today": picks,
        "forward_summary": summary,
        "down_buys_persisted": persisted,
        "down_buys_deep_persisted": deep_persisted,
        "production_enabled": bool(os.getenv("AG_REGIME_DOWN_PRODUCTION", "0").strip() not in ("0", "", "false", "False")),
        "note": "observation-only until AG_REGIME_DOWN_PRODUCTION=1; thin OOS edge; trade only with the tail-aware position_factor.",
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# Regime Signal Shadow ({today})", "",
             f"- scored: {len(scored)} | picks: {len(picks)}",
             f"- forward (resolved): n={summary['resolved']} win={summary['win_pct']}% net_avg={summary['net_avg_pct']}%",
             "", "| Market | Ticker | Regime | Score | dist_hi20 | Tier | Size |", "|---|---|---|---:|---:|---|---:|"]
    for p in picks:
        lines.append(f"| {p['market']} | {p['ticker']} | {p['regime']} | {p['score']:.2f} | "
                     f"{p['dist_hi20'] if p['dist_hi20'] is None else round(p['dist_hi20'],1)} | {p['tier']} | {p['position_factor']} |")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"picks": len(picks), "scored": len(scored), "forward_summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
