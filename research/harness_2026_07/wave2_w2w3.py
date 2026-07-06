#!/usr/bin/env python3
"""웨이브2 W2+W3 (swing-main-h3cu).

W3 레짐 조건부 top-k 증폭: picks_8y(rank1-3) — SEVERE에서 top3 확대가 EV 유지+빈도 3배?
W2 DART 독립 이벤트 레인: 공시 익일 진입 표준계약(px_long ft_5_5/exec_5d = next-open 라벨),
   etype별 net EV·시장초과·랜덤일 플라시보(같은 종목, 공시일 셔플). 유동성 가드.
"""
import os, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = "/Users/dongdong/research_cache"
COST = 0.3
rng = np.random.default_rng(0)


def seg(d, name):
    v = (d["policy_ret"] - COST).dropna()
    if len(v) < 80:
        print(f"  {name:34s} n={len(v)} 부족"); return
    bs = [rng.choice(v.values, len(v), True).mean() for _ in range(300)]
    yr = v.groupby(d["date"].dt.year).mean()
    ex = d["pol_ex"].dropna()
    print(f"  {name:34s} n={len(v):5d} EV={v.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] "
          f"초과={ex.mean():+.3f} 터치={(d['ft_5_5']==1).mean()*100:.0f}% yr+={int((yr>0).sum())}/{len(yr)}")


print("===== W3 레짐 조건부 top-k 증폭 (스윙, 8y) =====", flush=True)
P = pd.read_parquet(os.path.join(HERE, "picks_8y.parquet"))
P["date"] = pd.to_datetime(P["date"])
P["sev"] = (P["mkt_dd20"] < -12) | (P["mkt_ret5"] < -6)
P["dd"] = (P["mkt_dd20"] < -5) | (P["mkt_ret5"] < -3)
mkt_pol = P.groupby("date")["policy_ret"].mean()
P["pol_ex"] = P["policy_ret"] - P["date"].map(mkt_pol)
for mkt in ("KOSPI", "KOSDAQ"):
    M = P[P["market"] == mkt]
    for st, nm in ((M["sev"], "SEVERE"), ((M["dd"] & ~M["sev"]), "경증DD"), ((~M["dd"]), "NORMAL")):
        for k in (1, 3):
            d = M[st & (M["rank"] <= k)]
            seg(d, f"{mkt} {nm} top{k}")
# 제안 정책: NORMAL top1 / SEVERE top3
prop = P[((~P["dd"]) & (P["rank"] == 1)) | (P["sev"] & (P["rank"] <= 3)) | (P["dd"] & ~P["sev"] & (P["rank"] == 1))]
seg(prop, "제안: NORMAL/DD top1 + SEVERE top3")
base = P[P["rank"] == 1]
seg(base, "기준: 항상 top1")
print(f"  빈도: 기준 {len(base)/8:.0f}건/yr → 제안 {len(prop)/8:.0f}건/yr", flush=True)

print("\n===== W2 DART 독립 이벤트 레인 (2023-10..2026-07, 익일시가 진입 표준계약) =====", flush=True)
ev = pd.read_parquet(f"{CACHE}/dart_events.parquet")
ev["date"] = pd.to_datetime(ev["ann"], format="%Y%m%d", errors="coerce")
ev["code"] = ev["code"].astype(str).str.zfill(6)
cols = ["code", "date", "market", "liq", "ft_5_5", "exec_5d", "ret_1d"]
px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
px["date"] = pd.to_datetime(px["date"])
px = px[px["date"] >= "2023-09-01"]
px["exec_5d"] = px["exec_5d"].replace([np.inf, -np.inf], np.nan)
liq_ok = ((px["market"] == "KOSPI") & (px["liq"] >= 100e8)) | ((px["market"] == "KOSDAQ") & (px["liq"] >= 30e8))
px = px[liq_ok].copy()
px["policy_ret"] = np.where(px["ft_5_5"] == 1, 5.0, px["exec_5d"])
mkt_pol = px.groupby("date")["policy_ret"].mean()
px["pol_ex"] = px["policy_ret"] - px["date"].map(mkt_pol)
m = ev.merge(px, on=["code", "date"], how="inner")
print(f"  병합 {len(m)} / 원 이벤트 {len(ev)} (유동성 가드 후)", flush=True)
for etype, g in m.groupby("etype"):
    if len(g) >= 150:
        seg(g, f"{etype} ({g['edir'].iloc[0]})")
# 방향 결합
seg(m[m["edir"] == "+"], "호재군(+) 전체")
seg(m[m["edir"] == "-"], "악재군(-) 전체")
# 플라시보: 같은 종목, 공시일을 그 종목의 다른 거래일로 셔플
plc_rows = []
px_by_code = {c: g["date"].values for c, g in px.groupby("code")}
for _, r in m.iterrows():
    ds = px_by_code.get(r["code"])
    if ds is not None and len(ds) > 10:
        plc_rows.append((r["code"], pd.Timestamp(rng.choice(ds)), r["edir"]))
plc = pd.DataFrame(plc_rows, columns=["code", "date", "edir"]).merge(px, on=["code", "date"], how="inner")
seg(plc[plc["edir"] == "+"], "플라시보 호재군(랜덤일)")
seg(plc[plc["edir"] == "-"], "플라시보 악재군(랜덤일)")
json.dump({"done": True}, open(os.path.join(HERE, "wave2_w2w3.done"), "w"))
print("\nDONE", flush=True)
