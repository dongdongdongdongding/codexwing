#!/usr/bin/env python3
"""웨이브5: 근본가정 2개 검증 (사전등록, swing-main 최종 프론티어).
W5-A 저유동성 밴드(일중거래 5~30억): 개인 자본만 진입 가능한 영역 — 8y 분기 walk-forward
  랭커(운영 동일 구성), 비용 1.0%(스프레드 보수). 랭커 학습은 밴드 내 데이터로.
W5-B 월간 지평: 20d 보유, 저변동(σ하위1/3)×모멘텀 콤포짓 — 시장초과, 블록CI, 셔플 플라시보.
"""
import os, warnings, json
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import lightgbm as lgb
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(0)
CACHE = "/Users/dongdong/research_cache"
FEATS = ["ret_1d","ret_3d","ret_5d","ret_10d","ret_20d","ret_60d","ma5_dist","ma20_dist","ma60_dist",
         "ma120_dist","ma20_slope","ma60_slope","rsi14","rsi_slope","accel","consec_up","dist_hi20",
         "dist_hi60","dist_hi120","dist_lo20","dist_lo60","pos20","bb_pctb","bb_bw","atr_pct","vol20",
         "close_loc","gap","vol_ratio","vol_trend","turn_z","obv_slope","cmf20","idx_mom20","idx_vol20"]
cols = list(dict.fromkeys(["code","date","market","liq","ft_5_5","exec_5d","exec_10d","ret_1d","close","vol20","atr_pct","ret_20d","ret_60d"] + FEATS))
px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
px["date"] = pd.to_datetime(px["date"])
px["exec_5d"] = px["exec_5d"].replace([np.inf,-np.inf], np.nan)
px["exec_10d"] = px["exec_10d"].replace([np.inf,-np.inf], np.nan)
px["policy_ret"] = np.where(px["ft_5_5"]==1, 5.0, px["exec_5d"])

print("===== W5-A 저유동성 밴드 (5~30억, 비용 1.0%) =====", flush=True)
band = px[(px["liq"]>=5e8) & (px["liq"]<30e8)].copy()
print(f"밴드 패널 {len(band)} rows, 일평균 종목 {band.groupby('date').size().mean():.0f}", flush=True)
d = band.dropna(subset=["ft_5_5"] + FEATS[:6])
picks = []
for q in pd.period_range("2019Q1","2026Q2",freq="Q"):
    t0, t1 = q.start_time, q.end_time
    tr = d[(d["date"]<t0)&(d["date"]>=t0-pd.DateOffset(years=2))]
    te = d[(d["date"]>=t0)&(d["date"]<=t1)].copy()
    if len(tr)<20000 or te.empty: continue
    m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                           subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
    m.fit(tr[FEATS].clip(-1e4,1e4), tr["ft_5_5"])
    te["p"] = m.predict_proba(te[FEATS].clip(-1e4,1e4))[:,1]
    picks.append(te.sort_values("p",ascending=False).groupby("date",group_keys=False).head(3))
    print(f"  {q} done", flush=True)
A = pd.concat(picks).dropna(subset=["policy_ret"])
for cost, nm in ((1.0,"보수 1.0%"), (0.6,"중간 0.6%")):
    net = A["policy_ret"] - cost
    bs = [rng.choice(net.values, len(net), True).mean() for _ in range(300)]
    yr = net.groupby(A["date"].dt.year).mean()
    print(f"  랭커 top3 (비용 {nm}): n={len(net)} EV={net.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] "
          f"터치={( A['ft_5_5']==1).mean()*100:.0f}% yr+={int((yr>0).sum())}/{len(yr)}", flush=True)
# 플라시보 (라벨셔플 랭커는 비용상 스킵 — 셔플 신호 랭킹)
Ap = A.copy(); Ap["p_plc"] = rng.permutation(Ap["p"].values)
top_p = Ap.sort_values("p_plc",ascending=False).groupby("date",group_keys=False).head(3)
netp = top_p["policy_ret"] - 1.0
print(f"  플라시보(신호셔플): EV={netp.mean():+.3f}", flush=True)

print("\n===== W5-B 월간 지평: 저변동×모멘텀 (20d 보유, 시장초과) =====", flush=True)
liq_ok = ((px["market"]=="KOSPI")&(px["liq"]>=100e8))|((px["market"]=="KOSDAQ")&(px["liq"]>=30e8))
U = px[liq_ok].dropna(subset=["exec_10d","vol20","ret_60d"]).copy()
# forward 20d 근사: exec_10d 두 구간 합성 불가 → close 기반 fwd20 직접
U = U.sort_values(["code","date"])
g = U.groupby("code")
U["fwd20"] = (g["close"].shift(-20)/g["close"].shift(-1)-1)*100   # 익일 진입, 20d
mkt20 = U.groupby("date")["fwd20"].transform("mean")
U["ex20"] = U["fwd20"] - mkt20
qv = U.groupby("date")["vol20"].rank(pct=True)
qm = U.groupby("date")["ret_60d"].rank(pct=True)
def seg(dd, name):
    v = dd["ex20"].dropna()
    if len(v)<500: print(f"  {name:30s} n={len(v)} 부족"); return
    # 월별 1회 샘플로 중복 창 완화 + 블록CI
    dm = dd.copy(); dm["ym"] = dm["date"].dt.to_period("M")
    v2 = dm.groupby(["ym","code"])["ex20"].first().dropna()
    arr = v2.values
    nb = max(1,len(arr)//20)
    ms=[np.nanmean(np.concatenate([arr[s:s+20] for s in rng.integers(0,max(1,len(arr)-20),nb)])[:len(arr)]) for _ in range(300)]
    yr = v.groupby(dd.loc[v.index,"date"].dt.year).mean()
    print(f"  {name:30s} n(월샘플)={len(v2):6d} 초과20d={v2.mean():+.3f} 블록CI[{np.percentile(ms,2.5):+.2f},{np.percentile(ms,97.5):+.2f}] yr+={int((yr>0).sum())}/{len(yr)}", flush=True)
seg(U[qv<=0.33], "저변동 1/3")
seg(U[(qv<=0.33)&(qm>=0.6)], "저변동 × 모멘텀 상위")
seg(U[qv>0.67], "고변동 1/3 (대조)")
plc = U.copy(); plc["vol_p"] = plc.groupby("date")["vol20"].transform(lambda s: rng.permutation(s.values))
qp = plc.groupby("date")["vol_p"].rank(pct=True)
seg(plc[qp<=0.33].rename(columns={}), "플라시보 저변동(일내셔플)")
json.dump({"done": True}, open(os.path.join(HERE, "wave5.done"), "w"))
print("DONE", flush=True)
