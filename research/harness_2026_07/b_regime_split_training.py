#!/usr/bin/env python3
"""웨이브3-①: B 레짐 분리 '학습' (사전등록). §26 C1(발행보류)은 배포됨 — 이번엔 학습 데이터 자체를
NORMAL 일로 한정하면 NORMAL 알파가 더 오르는가 (혼합학습이 레짐 노이즈를 섞는다는 가설).
C4a: NORMAL-only 학습 → NORMAL 발행 (C1 위 증분?)
C4b: 전체 학습(현행) → NORMAL 발행 (= §26 C1 기준선)
판정: C4a > C4b + 시드 불변 시 채택 제안."""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
from b_engine import model_engine as E
HERE = os.path.dirname(os.path.abspath(__file__))
px = E.load_panel().dropna(subset=["a5"]).copy()
px["date"] = pd.to_datetime(px["date"])
pxl = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["date","market","ret_1d","liq"])
pxl["date"] = pd.to_datetime(pxl["date"])
pool = pxl[((pxl["market"]=="KOSPI")&(pxl["liq"]>=100e8))|((pxl["market"]=="KOSDAQ")&(pxl["liq"]>=30e8))]
m = pool.groupby("date")["ret_1d"].mean().sort_index()
lvl = (1+m/100).cumprod()
ro = ((lvl/lvl.rolling(20).max()-1)*100 < -5) | ((lvl/lvl.shift(5)-1)*100 < -3)
px = px.join(ro.rename("risk_off"), on="date")
months = pd.period_range("2024-07","2026-06",freq="M")
res = {}
for tag, train_filter in (("C4b 전체학습(기준)", None), ("C4a NORMAL만 학습", "normal")):
    pools = []
    for tm in months:
        t0, t1 = tm.start_time, tm.end_time
        tr = px[(px["date"]<t0)&(px["date"]>=t0-pd.DateOffset(months=E.TRAIN_MONTHS))]
        if train_filter == "normal":
            tr = tr[~tr["risk_off"].fillna(False)]
        te = px[(px["date"]>=t0)&(px["date"]<=t1)].copy()
        te = te[~te["risk_off"].fillna(False)]   # 발행은 둘 다 NORMAL만 (C1)
        if len(tr) < 15000 or te.empty: continue
        models = E._fit_ensemble(tr)
        te["pred"] = E._predict(models, te)
        pools.append(te)
    A = pd.concat(pools)
    for k in (10, 3):
        sel = A.sort_values("pred", ascending=False).groupby("date", group_keys=False).head(k)
        v = sel["a5"].dropna()
        print(f"  {tag} top{k}: n={len(v)} α={v.mean():+.3f} 승={(v>0).mean()*100:.0f}%", flush=True)
        res[f"{tag}_top{k}"] = float(v.mean())
json.dump(res, open(os.path.join(HERE, "b_regime_split.done"), "w"))
print("DONE", flush=True)
