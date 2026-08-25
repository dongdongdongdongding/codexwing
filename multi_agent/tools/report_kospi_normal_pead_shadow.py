#!/usr/bin/env python3
"""Non-edge falsification ledger for the KOSPI-NORMAL price+flow+PEAD ensemble candidate.

NOT an edge candidate. This was the last surviving daily-selection candidate, but a clean
re-verification (2026-06-23, Claude+Codex; ~/research_cache/verify_benchmark.py) RETRACTED
the edge: scoring the SAME >=100억 KOSPI-NORMAL top-5 picks against an internally-consistent
benchmark (the panel's own liquidity/cap-weighted market return) gives ~0 market-excess with
a bootstrap CI that INCLUDES 0 (panel-capw -0.01% CI[-0.56,+0.56]; equal-weighted +0.09%;
2-model variant +0.12% CI[-0.61,+0.76]). The earlier "+1.5% CI>0" was a benchmark artifact:
it used the external FDR KS11 series, whose snapshot diverged from the true cap-weighted
market. So there is NO validated daily-selection edge. See memory/daily_selection_closed_final.

This tracker is kept ONLY to forward-observe / falsify: it logs the picks the model would
have made and resolves their realised 5D return against BOTH benchmarks (panel cap-weighted
= primary gate; KS11 = reference diagnostic only). Production stays OFF.

Methodology mirrors the research (so live features match the training distribution): warm-
start the panel from ~/research_cache parquets, extend the tail with fresh FDR OHLC + KIS
investor flow, compute identical features, rolling-retrain the ensemble on the trailing ~400
sessions of KOSPI rows (all regimes; label=first-touch ft_5_5), score ONLY when KOSPI regime
is NORMAL. Regime uses the lagged 20D index momentum (.shift(1)) matching build_px_long --
NOTE this lags sharp reversals (a -10% crash can still read UP), so it is a trend gate, not a
reversal guard.

Observation-only: writes a JSONL ledger + report. Routes to the live web/Discord surface only
when AG_KOSPI_NORMAL_PEAD_PRODUCTION=1 (keep =0). Registered in run_daily_ops.sh as
AG_KOSPI_NORMAL_PEAD_SHADOW_ENABLE (=1 for ledger accumulation; this is observation, not a
recommendation).

  python3 multi_agent/tools/report_kospi_normal_pead_shadow.py [--universe 300] [--min-liq 100]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:  # make KIS / OPENDART keys available when run standalone (no-op if already set in env)
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env.local")
except Exception:
    pass

CACHE = Path(os.path.expanduser("~/research_cache"))
LEDGER = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "kospi_normal_pead_shadow_ledger.jsonl"
REPORT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "kospi_normal_pead_shadow_latest.json"
REPORT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "kospi_normal_pead_shadow_latest.md"

from modules.trading_costs import KR_ROUNDTRIP_COST_PCT as COST  # 단일 출처(0.215)
RAW = ["ret_5d", "ret_20d", "ma20_dist", "ma60_dist", "dist_hi20", "dist_lo20"]
FLOW = ["frgn_acc5_r", "orgn_acc5_r", "smart_acc5_r", "both_buy", "frgn_int"]
PEAD = ["days_since", "post_earn", "reaction", "post_x_react"]
BASE = [f + "_z" for f in RAW] + FLOW + ["regstate"] + PEAD


# ---------------------------------------------------------------------------
# Panel construction (warm-start from research_cache + fresh tail)
# ---------------------------------------------------------------------------

def _liquid_kospi_universe(px: pd.DataFrame, n: int) -> List[str]:
    recent = px[(px["market"] == "KOSPI") & (px["date"] >= px["date"].max() - pd.Timedelta(days=90))]
    return recent.groupby("code")["liq"].median().sort_values(ascending=False).head(n).index.astype(str).tolist()


def _extend_price(px: pd.DataFrame, codes: List[str]) -> pd.DataFrame:
    """Append fresh FDR OHLC (since the panel's last date) so 'today' exists."""
    import FinanceDataReader as fdr
    last = px["date"].max()
    start = (last - pd.Timedelta(days=8)).strftime("%Y-%m-%d")
    add = []
    for code in codes:
        try:
            h = fdr.DataReader(code, start)
        except Exception:
            continue
        if h is None or "Close" not in h.columns or h.empty:
            continue
        h = h.reset_index().rename(columns={"Date": "date", "Close": "close", "Volume": "vol"})
        h["code"] = str(code)
        h["date"] = pd.to_datetime(h["date"])
        h = h[h["date"] > last]
        if h.empty:
            continue
        h["liq"] = (h["close"] * h["vol"]).astype(float)
        h["market"] = "KOSPI"
        add.append(h[["code", "date", "close", "liq", "market"]])
    if not add:
        return px
    nxt = pd.concat(add, ignore_index=True)
    keep = [c for c in ["code", "date", "close", "liq", "market", "idx_mom20", "ft_5_5"] if c in px.columns]
    return pd.concat([px[keep], nxt], ignore_index=True).drop_duplicates(["code", "date"], keep="first")


def _extend_flow(flow: pd.DataFrame, codes: List[str]) -> pd.DataFrame:
    """Append fresh KIS investor flow (identical parse to ~/research_cache/flow_bf.py)."""
    os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
    try:
        from modules.kis_openapi import KISOpenAPIClient, KISConfig
        cli = KISOpenAPIClient(KISConfig.from_env())
        cli.get_access_token()
    except Exception:
        return flow
    last = pd.to_datetime(flow["date"], format="%Y%m%d").max()
    to_i = lambda x: int(str(x).replace(",", "")) if str(x).replace(",", "").lstrip("-").isdigit() else 0
    buf = []
    for code in codes:
        seen = set()
        cur = datetime.now()
        for _ in range(4):
            try:
                r = cli.investor_trading_daily(code, trade_date=cur.strftime("%Y%m%d"))
                out = r.get("output2", []) if isinstance(r, dict) else []
            except Exception:
                out = []
            if not out:
                break
            for row in out:
                d = row.get("stck_bsop_date")
                if not d or d in seen or pd.to_datetime(d) <= last:
                    continue
                seen.add(d)
                buf.append({"code": str(code), "date": d, "frgn_ntby": to_i(row.get("frgn_ntby_qty")),
                            "orgn_ntby": to_i(row.get("orgn_ntby_qty")), "prsn_ntby": to_i(row.get("prsn_ntby_qty")),
                            "frgn_val": to_i(row.get("frgn_ntby_tr_pbmn")), "orgn_val": to_i(row.get("orgn_ntby_tr_pbmn")),
                            "acml_val": to_i(row.get("acml_tr_pbmn"))})
            try:
                cur = datetime.strptime(min(seen), "%Y%m%d") - timedelta(days=2)
            except Exception:
                break
        time.sleep(0.02)
    if not buf:
        return flow
    return pd.concat([flow, pd.DataFrame(buf)], ignore_index=True).drop_duplicates(["code", "date"], keep="first")


def _refresh_dart(codes: List[str], da: pd.DataFrame) -> pd.DataFrame:
    """Append recent periodic-report announcements (identical parse to ~/research_cache/dart_bf.py)
    so PEAD days_since stays fresh as new quarters are disclosed. Best-effort; persists back to the
    research_cache parquet so subsequent runs warm-start from the refreshed set."""
    import io
    import re
    import zipfile
    import xml.etree.ElementTree as ET

    import requests

    key = os.environ.get("OPENDART_API_KEY")
    if not key:
        return da
    cc_path = CACHE / "dart_corpcode.json"
    try:
        if cc_path.exists():
            mp = json.loads(cc_path.read_text(encoding="utf-8"))
        else:
            r = requests.get("https://opendart.fss.or.kr/api/corpCode.xml", params={"crtfc_key": key}, timeout=60)
            z = zipfile.ZipFile(io.BytesIO(r.content)); root = ET.fromstring(z.read(z.namelist()[0]).decode("utf-8"))
            mp = {}
            for e in root.iter("list"):
                sc = e.findtext("stock_code"); co = e.findtext("corp_code")
                if sc and sc.strip():
                    mp[sc.strip()] = co.strip()
            cc_path.write_text(json.dumps(mp), encoding="utf-8")
    except Exception:
        return da
    today = datetime.now().strftime("%Y%m%d")
    bgn = (datetime.now() - timedelta(days=150)).strftime("%Y%m%d")
    per_re = re.compile(r"\((\d{4})\.(\d{2})\)")
    buf = []
    for code in codes:
        cc = mp.get(str(code))
        if not cc:
            continue
        try:
            rr = requests.get("https://opendart.fss.or.kr/api/list.json",
                              params={"crtfc_key": key, "corp_code": cc, "bgn_de": bgn, "end_de": today,
                                      "pblntf_ty": "A", "page_count": 100}, timeout=15).json()
        except Exception:
            continue
        for it in (rr.get("list", []) if isinstance(rr, dict) else []):
            nm = it.get("report_nm", "")
            if any(k in nm for k in ("분기보고서", "반기보고서", "사업보고서")):
                mt = per_re.search(nm)
                if mt:
                    buf.append({"code": str(code), "period": mt.group(1) + mt.group(2), "ann": it.get("rcept_dt"), "rpt": nm[:8]})
        time.sleep(0.03)
    if not buf:
        return da
    out = pd.concat([da, pd.DataFrame(buf)], ignore_index=True).drop_duplicates()
    try:
        out.to_parquet(CACHE / "dart_ann.parquet")
    except Exception:
        pass
    return out


def build_panel(universe_n: int) -> pd.DataFrame:
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "close", "liq", "market", "idx_mom20", "ft_5_5"])
    px["code"] = px["code"].astype(str); px["date"] = pd.to_datetime(px["date"])
    px = px[px["market"] == "KOSPI"]
    px = px[px["date"] >= px["date"].max() - pd.Timedelta(days=470)]  # 252d z + 400d train window
    codes = _liquid_kospi_universe(px, universe_n)
    px = px[px["code"].isin(codes)].copy()
    px = _extend_price(px, codes)

    # index regime (recompute idx_mom20 on the extended tail from KS11)
    import FinanceDataReader as fdr
    ks = fdr.DataReader("KS11", (px["date"].min() - pd.Timedelta(days=40)).strftime("%Y-%m-%d"))["Close"]
    ks = pd.to_numeric(ks, errors="coerce").dropna()
    ksm = ((ks / ks.shift(20) - 1) * 100).shift(1)  # .shift(1) matches build_px_long:92 (lagged trend gate, no look-ahead)
    px["idx_mom20"] = px["date"].map(ksm).astype(float)
    px = px.sort_values(["code", "date"]).reset_index(drop=True)

    # flow features
    flow = pd.read_parquet(CACHE / "flow.parquet"); flow["code"] = flow["code"].astype(str)
    flow = flow[flow["code"].isin(codes)]
    flow = _extend_flow(flow, codes)
    flow["date"] = pd.to_datetime(flow["date"], format="%Y%m%d", errors="coerce")
    sh = pd.read_parquet(CACHE / "shares.parquet"); sh["code"] = sh["code"].astype(str)
    fm = flow.merge(sh, on="code", how="left").sort_values(["code", "date"]); gf = fm.groupby("code")
    fm["frgn_r"] = fm["frgn_ntby"] / (fm["shares"] + 1) * 1e4; fm["orgn_r"] = fm["orgn_ntby"] / (fm["shares"] + 1) * 1e4
    fm["frgn_acc5_r"] = gf["frgn_r"].transform(lambda s: s.rolling(5).sum())
    fm["orgn_acc5_r"] = gf["orgn_r"].transform(lambda s: s.rolling(5).sum())
    fm["smart_acc5_r"] = fm["frgn_acc5_r"] + fm["orgn_acc5_r"]
    fm["both_buy"] = ((fm["frgn_acc5_r"] > 0) & (fm["orgn_acc5_r"] > 0)).astype(float)
    fm["frgn_int"] = (fm["frgn_val"] / (fm["acml_val"] + 1)).groupby(fm["code"]).transform(lambda s: s.rolling(5).mean())
    df = px.merge(fm[["code", "date"] + FLOW], on=["code", "date"], how="left").sort_values(["code", "date"]).reset_index(drop=True)

    # price features + own-series z-norm (rolling 252, min 60)
    g = df.groupby("code")
    df["ret_5d"] = g["close"].transform(lambda s: s.pct_change(5) * 100)
    df["ret_20d"] = g["close"].transform(lambda s: s.pct_change(20) * 100)
    df["ma20_dist"] = g["close"].transform(lambda s: (s / s.rolling(20).mean() - 1) * 100)
    df["ma60_dist"] = g["close"].transform(lambda s: (s / s.rolling(60).mean() - 1) * 100)
    df["dist_hi20"] = g["close"].transform(lambda s: (s / s.rolling(20).max() - 1) * 100)
    df["dist_lo20"] = g["close"].transform(lambda s: (s / s.rolling(20).min() - 1) * 100)
    for f in RAW:
        mm = g[f].transform(lambda s: s.rolling(252, min_periods=60).mean())
        sd = g[f].transform(lambda s: s.rolling(252, min_periods=60).std())
        df[f + "_z"] = ((df[f] - mm) / (sd + 1e-9)).clip(-6, 6)
    df["regstate"] = df["idx_mom20"]

    # coarse PEAD (leak-blocked reaction), identical to research
    g2 = df.groupby("code")
    df["rfwd2"] = g2["close"].transform(lambda s: (s.shift(-2) / s - 1) * 100)
    _dap = CACHE / "dart_ann.parquet"   # 캐시(없으면 빈 df로 시작 → _refresh_dart가 DART API에서 재생성)
    da = pd.read_parquet(_dap) if _dap.exists() else pd.DataFrame(columns=["code", "period", "ann", "rpt"])
    da["code"] = da["code"].astype(str)
    da = _refresh_dart(codes, da)  # pull newly-disclosed quarters so days_since stays fresh
    da["ann"] = pd.to_datetime(da["ann"], format="%Y%m%d", errors="coerce")
    da = da.dropna(subset=["ann"]).sort_values("ann").drop_duplicates(["code", "period"], keep="first")
    ev = pd.merge_asof(da[["code", "ann"]].sort_values("ann"), df[["code", "date", "rfwd2"]].sort_values("date"),
                       left_on="ann", right_on="date", by="code", direction="forward", tolerance=pd.Timedelta(days=7))
    ev = ev.dropna(subset=["date"]).rename(columns={"rfwd2": "reaction"})[["code", "ann", "reaction"]]
    df = pd.merge_asof(df.sort_values("date"), ev.sort_values("ann"), left_on="date", right_on="ann", by="code", direction="backward")
    df["days_since"] = (df["date"] - df["ann"]).dt.days.clip(0, 120)
    df["post_earn"] = ((df["days_since"] >= 0) & (df["days_since"] <= 20)).astype(float)
    df["reaction"] = df["reaction"].fillna(0); df.loc[df["days_since"] < 2, "reaction"] = 0.0
    df["post_x_react"] = df["post_earn"] * df["reaction"]
    df["liq억"] = df["liq"] / 1e8
    return df.drop(columns=["ann"], errors="ignore")


# ---------------------------------------------------------------------------
# Scoring + resolution
# ---------------------------------------------------------------------------

def _regime(mom: float) -> str:
    return "DOWN" if mom < -2.0 else ("UP" if mom > 2.0 else "NORMAL")


def score_today(df: pd.DataFrame, min_liq: float, top_picks: int) -> Dict[str, Any]:
    import lightgbm as lgb, xgboost as xgb
    from sklearn.ensemble import ExtraTreesClassifier
    asof = df["date"].max()
    mom_today = df[df["date"] == asof]["idx_mom20"].dropna()
    regime = _regime(float(mom_today.iloc[0])) if len(mom_today) else None
    if regime != "NORMAL":
        return {"asof": str(asof.date()), "regime": regime, "picks": [], "note": "abstain (KOSPI regime != NORMAL)"}

    train = df[(df["date"] < asof) & (df["date"] >= asof - pd.Timedelta(days=400))].dropna(subset=BASE + ["ft_5_5"])
    today = df[df["date"] == asof].dropna(subset=BASE).copy()
    if len(train) < 8000 or today.empty:
        return {"asof": str(asof.date()), "regime": regime, "picks": [], "note": f"insufficient data (train={len(train)})"}

    Xtr, ytr = train[BASE].fillna(0), train["ft_5_5"]
    mk = {
        "LGBM": lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31, min_child_samples=100,
                                   subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1),
        "XGB": xgb.XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8,
                                 colsample_bytree=0.7, reg_lambda=3, verbosity=0, n_jobs=-1),
        "ET": ExtraTreesClassifier(n_estimators=150, min_samples_leaf=60, random_state=0, n_jobs=-1),
    }
    ranks = []
    for m in mk.values():
        m.fit(Xtr, ytr)
        ranks.append(pd.Series(m.predict_proba(today[BASE].fillna(0))[:, 1], index=today.index).rank(pct=True))
    today["p"] = sum(ranks) / len(ranks)

    elig = today[today["liq억"] >= float(min_liq)]
    top = elig.nlargest(int(top_picks), "p")
    picks = [{"ticker": str(r["code"]) + ".KS", "p": round(float(r["p"]), 4), "liq억": round(float(r["liq억"]), 1),
              "entry_reference_price": float(r["close"]), "days_since": int(r["days_since"]),
              "post_earn": int(r["post_earn"]), "frgn_acc5_r": round(float(r["frgn_acc5_r"]), 2) if pd.notna(r["frgn_acc5_r"]) else None}
             for _, r in top.iterrows()]
    return {"asof": str(asof.date()), "regime": regime, "picks": picks,
            "eligible": int(len(elig)), "note": f"NORMAL; {len(elig)} names >= {min_liq}억"}


_CAPW_CACHE: Dict[str, Optional[float]] = {}


def _capw_market_return(start: str, weight_cap: int = 120) -> Optional[float]:
    """Internally-consistent benchmark: liquidity(cap)-weighted 5D return of the liquid KOSPI
    universe from `start` (the panel's own market, NOT external KS11). Cached per start date."""
    if start in _CAPW_CACHE:
        return _CAPW_CACHE[start]
    import FinanceDataReader as fdr
    try:
        px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "liq", "market"])
        px = px[px["market"] == "KOSPI"]; px["date"] = pd.to_datetime(px["date"])
        recent = px[px["date"] >= px["date"].max() - pd.Timedelta(days=90)]
        wts = recent.groupby("code")["liq"].median().sort_values(ascending=False).head(weight_cap)
    except Exception:
        _CAPW_CACHE[start] = None; return None
    rets, ws = [], []
    for code, w in wts.items():
        try:
            h = pd.to_numeric(fdr.DataReader(str(code), start)["Close"], errors="coerce").dropna()
            if len(h) >= 6:
                rets.append((h.iloc[5] / h.iloc[0] - 1) * 100); ws.append(float(w))
        except Exception:
            pass
    r = float(np.average(rets, weights=ws)) if rets else None
    _CAPW_CACHE[start] = r
    return r


def resolve_pending(today: str) -> Dict[str, Any]:
    """Resolve elapsed picks against BOTH benchmarks: panel cap-weighted (primary gate) and
    KS11 (reference diagnostic only). market-excess net = stock_5D - benchmark_5D - cost."""
    import FinanceDataReader as fdr
    if not LEDGER.exists():
        return {"resolved": 0, "panel_capw_excess_avg": None, "ks11_excess_avg": None}
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = False
    for row in rows:
        if row.get("panel_capw_excess") is not None and row.get("ks11_excess") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.isna(d) or (pd.Timestamp(today) - d).days < 9:
            continue
        try:
            bare = str(row["ticker"]).replace(".KS", "").replace(".KQ", "")
            h = pd.to_numeric(fdr.DataReader(bare, str(d.date()))["Close"], errors="coerce").dropna()
            idx = pd.to_numeric(fdr.DataReader("KS11", str(d.date()))["Close"], errors="coerce").dropna()
            if len(h) < 6:
                continue
            sret = (h.iloc[5] / h.iloc[0] - 1) * 100
            capw = _capw_market_return(str(d.date()))                       # primary: panel cap-weighted
            if row.get("panel_capw_excess") is None and capw is not None:
                row["panel_capw_excess"] = round(float(sret - capw - COST), 3)
            if row.get("ks11_excess") is None and len(idx) >= 6:           # reference: KS11
                row["ks11_excess"] = round(float(sret - (idx.iloc[5] / idx.iloc[0] - 1) * 100 - COST), 3)
            changed = changed or (row.get("panel_capw_excess") is not None or row.get("ks11_excess") is not None)
        except Exception:
            pass
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    capw_res = [r["panel_capw_excess"] for r in rows if r.get("panel_capw_excess") is not None]
    ks_res = [r["ks11_excess"] for r in rows if r.get("ks11_excess") is not None]
    out: Dict[str, Any] = {"resolved": len(capw_res or ks_res)}
    out["panel_capw_excess_avg"] = round(float(np.mean(capw_res)), 3) if capw_res else None
    out["ks11_excess_avg"] = round(float(np.mean(ks_res)), 3) if ks_res else None
    out["win_rate_pct"] = round(float(np.mean([1 for x in capw_res if x > 0]) / len(capw_res) * 100), 1) if capw_res else None
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="KOSPI-NORMAL price+flow+PEAD ensemble shadow forward-tracker.")
    ap.add_argument("--universe", type=int, default=300)
    ap.add_argument("--min-liq", type=float, default=100.0)
    ap.add_argument("--top-picks", type=int, default=5)
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        df = build_panel(args.universe)
        result = score_today(df, args.min_liq, args.top_picks)
    except Exception as exc:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps({"error": repr(exc)[:300], "today": today}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"error": repr(exc)[:200]}, ensure_ascii=False)); return

    picks = result.get("picks", [])
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in picks:
            fh.write(json.dumps({"date": result["asof"], "panel_capw_excess": None, "ks11_excess": None, **p},
                                ensure_ascii=False) + "\n")
    summary = resolve_pending(today)

    production = os.getenv("AG_KOSPI_NORMAL_PEAD_PRODUCTION", "0").strip() not in ("0", "", "false", "False")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "today": today, **result,
              "forward_summary": summary, "production_enabled": production,
              "note": "NON-EDGE falsification ledger (edge retracted 2026-06-23: ~0 vs internally-consistent "
                      "benchmark, CI includes 0). KOSPI NORMAL; price+flow+coarse-PEAD ENS; >=100억; top-5. "
                      "Primary metric = panel_capw_excess (stock5d - panel cap-weighted 5d - 0.6%); ks11_excess "
                      "is reference-only. Observation; production stays OFF."}
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# KOSPI-NORMAL PEAD-ENS shadow — NON-EDGE falsification ledger ({result['asof']})", "",
             f"- regime: {result.get('regime')} | {result.get('note')}",
             f"- forward (resolved): n={summary['resolved']} | panel-capw excess avg={summary.get('panel_capw_excess_avg')}% "
             f"(primary) | ks11 excess avg={summary.get('ks11_excess_avg')}% (ref) | win={summary.get('win_rate_pct')}%", "",
             "| Ticker | p | liq(억) | days_since | frgn_acc5 |", "|---|---:|---:|---:|---:|"]
    for p in picks:
        lines.append(f"| {p['ticker']} | {p['p']:.3f} | {p['liq억']} | {p['days_since']} | {p.get('frgn_acc5_r')} |")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"asof": result["asof"], "regime": result.get("regime"), "picks": len(picks),
                      "forward_summary": summary, "production": production}, ensure_ascii=False))


if __name__ == "__main__":
    main()
