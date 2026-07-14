#!/usr/bin/env python3
"""웨이브3-②: 코스닥 학습 유니버스 확장 검증 (사전등록, 배포 없음).
현상: 학습패널 128종목(ohlc_daily 교집합) vs 운용 스코어링 450종목 — 분포 불일치.
실험: ohlc_full(+미보유 124 추가수집)로 패널을 적격 전체로 재구축 → 월재학습 walk-forward
  (2025-11..2026-06, pcal>=0.70, vwap 가드) — 기준(128) 대비 픽/주·win·EV.
판정: 빈도 증가 & win>=70% & EV CI>0 유지 시 채택 제안 (학습 패널 소스 교체)."""
import os, sys, time, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser("~/research_cache")

# 0) ohlc_full에 코스닥 적격 미보유 124종목 추가 (FDR)
import FinanceDataReader as fdr
oh = pd.read_parquet(f"{CACHE}/ohlc_full.parquet")
px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=["code","date","market","liq","idx_mom20","idx_vol20"])
px["code"] = px["code"].astype(str).str.zfill(6); px["date"] = pd.to_datetime(px["date"])
recent = px[px["date"] >= px["date"].max()-pd.Timedelta(days=90)]
kq_liq = recent[recent["market"]=="KOSDAQ"].groupby("code")["liq"].median()
elig = sorted(set(kq_liq[kq_liq>=30e8].index.astype(str)))
missing = [c for c in elig if c not in set(oh["code"].unique())]
print(f"미보유 {len(missing)} 수집", flush=True)
buf = []
for c in missing:
    try:
        h = fdr.DataReader(c, "2024-06-01")
        if len(h) < 100: continue
        f = h[["Open","High","Low","Close","Volume"]].reset_index()
        f.columns = ["date","open","high","low","close","volume"]; f["code"] = c
        buf.append(f)
    except Exception: pass
if buf:
    oh = pd.concat([oh, pd.concat(buf, ignore_index=True)], ignore_index=True)
    oh.to_parquet(f"{CACHE}/ohlc_full.parquet")
    print(f"ohlc_full 확장 → {oh['code'].nunique()}종목", flush=True)

# 1) 확장 패널 재구축 (프로덕션 피처함수, og=ohlc_full)
from modules.kosdaq_intraday_vwap_guard import compute_pre_entry_features, compute_daily_prev_context
kq = px[px["market"]=="KOSDAQ"]
liq_map = kq.set_index(["code","date"])["liq"]
idx_map = kq.drop_duplicates("date").set_index("date")[["idx_mom20","idx_vol20"]]
oh["date"] = pd.to_datetime(oh["date"]); oh = oh.sort_values(["code","date"])
oh2 = oh.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})
og = {c: g.reset_index(drop=True) for c, g in oh2.groupby("code")}
rows, t0, done = [], time.time(), 0
for code in elig:
    fp = f"{CACHE}/intraday/{code}.parquet"
    if code not in og or not os.path.exists(fp): continue
    try: m = pd.read_parquet(fp)
    except Exception: continue
    dd = og[code]
    mi = pd.to_datetime(m.index)
    days = sorted(set(mi.strftime("%Y-%m-%d")))
    didx = {str(d.date()): i for i, d in enumerate(dd["date"])}
    for tstr in days:
        i = didx.get(tstr)
        if i is None or i < 21 or i + 5 >= len(dd): continue
        liq_prev = liq_map.get((code, dd["date"].iloc[i-1]), np.nan)
        if not np.isfinite(liq_prev) or liq_prev < 30e8: continue
        g = m[mi.strftime("%Y-%m-%d") == tstr]
        g = g[(pd.to_datetime(g.index).time >= pd.Timestamp("09:00").time()) & (pd.to_datetime(g.index).time <= pd.Timestamp("15:00").time())]
        if len(g) < 60: continue
        prev_close = float(dd["Close"].iloc[i-1])
        try:
            feat = compute_pre_entry_features(g, prev_close=prev_close, liq_prev_eok=liq_prev/1e8, trade_date=tstr.replace("-",""))
            ctx = compute_daily_prev_context(dd.iloc[:i])
        except Exception: continue
        if feat is None: continue
        entry = float(dd["Close"].iloc[i])
        hi5 = dd["High"].iloc[i+1:i+6].astype(float); op5 = dd["Open"].iloc[i+1:i+6].astype(float); cl5 = dd["Close"].iloc[i+1:i+6].astype(float)
        tgt10 = entry*1.10
        pol = float((cl5.iloc[-1]/entry-1)*100)
        for k in range(len(hi5)):
            if hi5.iloc[k] >= tgt10:
                fill = max(tgt10, float(op5.iloc[k])) if k>0 else tgt10
                pol = (fill/entry-1)*100; break
        # 3d +5 터치 라벨 (y)
        hi3 = dd["High"].iloc[i+1:i+4].astype(float)
        y = int((hi3 >= entry*1.05).any())
        ix = idx_map.reindex([dd["date"].iloc[i]])
        rec = {"code": code, "date": dd["date"].iloc[i], **feat, **(ctx or {}),
               "idx_mom20": float(ix["idx_mom20"].iloc[0]) if len(ix) else np.nan,
               "idx_vol20": float(ix["idx_vol20"].iloc[0]) if len(ix) else np.nan,
               "touch3d_t5": y, "policy_t10_h5": pol}
        rows.append(rec)
    done += 1
    if done % 100 == 0: print(f"  {done}종목 rows={len(rows)} ({time.time()-t0:.0f}s)", flush=True)
P = pd.DataFrame(rows)
P.to_parquet(os.path.join(HERE, "kosdaq_panel_expanded.parquet"))
print(f"확장패널 {len(P)} rows, {P['code'].nunique()}종목", flush=True)

# 2) walk-forward 비교 (월재학습, pcal>=0.70)
import lightgbm as lgb, joblib
from sklearn.isotonic import IsotonicRegression
b = joblib.load("/Users/dongdong/Projects/codex_swing/swing-main/models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl")
FEATS = [f for f in b["features"] if f in P.columns]
LGBP = {k: v for k, v in (b.get("lgbm_params") or {}).items() if k not in ("random_state","verbose")}
d = P.dropna(subset=["touch3d_t5"]).sort_values("date")
pools = []
for tm in pd.period_range("2025-11","2026-06",freq="M"):
    t0m, t1m = tm.start_time, tm.end_time
    tr = d[d["date"]<t0m]; te = d[(d["date"]>=t0m)&(d["date"]<=t1m)].copy()
    if te.empty or len(tr)<3000: continue
    Xtr = tr[FEATS].fillna(0).values; ytr = tr["touch3d_t5"].values
    n85 = int(len(tr)*0.85)
    m1 = lgb.LGBMClassifier(**LGBP, random_state=0, verbose=-1); m1.fit(Xtr[:n85], ytr[:n85])
    iso = IsotonicRegression(out_of_bounds="clip").fit(m1.predict_proba(Xtr[n85:])[:,1], ytr[n85:])
    mf = lgb.LGBMClassifier(**LGBP, random_state=0, verbose=-1); mf.fit(Xtr, ytr)
    te["pcal"] = iso.predict(mf.predict_proba(te[FEATS].fillna(0).values)[:,1])
    pools.append(te)
A = pd.concat(pools)
A = A[A["pre_vwap_dist_pct"]>=0].dropna(subset=["policy_t10_h5"])
tw = A["date"].dt.to_period("W").nunique()
rng = np.random.default_rng(0)
s = A[A["pcal"]>=0.70].sort_values("pcal", ascending=False).groupby("date", group_keys=False).head(1)
net = s["policy_t10_h5"] - 0.33
bs = [rng.choice(net.values, len(net), True).mean() for _ in range(300)]
print(f"\n확장 유니버스 (pcal>=0.70, {A['code'].nunique()}종목): 주당 {len(s)/tw:.1f}픽 win={(net>0).mean()*100:.0f}% EV={net.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}]")
print("기준(128종목): 주당 2.9픽 win=72% EV=+3.58 CI[+1.19,+5.43]")
json.dump({"done": True}, open(os.path.join(HERE, "kosdaq_universe_expand.done"), "w"))
print("DONE", flush=True)
