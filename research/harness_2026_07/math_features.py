#!/usr/bin/env python3
"""수학적 피처공간 증분 검증 (사용자 챌린지: 학습기가 아니라 표현의 수학).

베이스 스윙 랭커(35피처) 위에 4계열 수학 피처의 '증분'을 판정:
  M1 횡단면 정규화: 날짜별 z-score (핵심 8피처) — 레짐 불변 표현
  M2 잔차 모멘텀: 롤링 60d 베타 제거 후 20d 고유 모멘텀 + 고유변동성
  M3 시계열 구조: OU 반감기(AR1), Hurst 근사(분산비), EWMA 변동성 비율
  M4 시장 구조: 횡단면 분산·상승비율·신호일 시장수익 (date-level)
프로토콜: 2024/25/26 연도 walk-forward(2y 학습) top-3/일, policy EV net.
비교군: 베이스 / +각 계열 / +전부 / +동수 노이즈(플라시보). 판정 = 증분 > 플라시보 증분.
"""
import os, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import lightgbm as lgb

CACHE = "/Users/dongdong/research_cache"
COST = 0.3
rng = np.random.default_rng(0)
FEATS = ["ret_1d","ret_3d","ret_5d","ret_10d","ret_20d","ret_60d","ma5_dist","ma20_dist","ma60_dist",
         "ma120_dist","ma20_slope","ma60_slope","rsi14","rsi_slope","accel","consec_up","dist_hi20",
         "dist_hi60","dist_hi120","dist_lo20","dist_lo60","pos20","bb_pctb","bb_bw","atr_pct","vol20",
         "close_loc","gap","vol_ratio","vol_trend","turn_z","obv_slope","cmf20","idx_mom20","idx_vol20"]
CSZ_BASE = ["ret_5d", "ret_20d", "rsi14", "turn_z", "atr_pct", "dist_hi20", "gap", "vol_ratio"]


def build():
    cols = list(dict.fromkeys(["code","date","market","liq","ft_5_5","exec_5d","close"] + FEATS))
    px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px["exec_5d"] = px["exec_5d"].replace([np.inf,-np.inf], np.nan)
    liq_ok = ((px["market"]=="KOSPI") & (px["liq"]>=100e8)) | ((px["market"]=="KOSDAQ") & (px["liq"]>=30e8))
    px = px[liq_ok].copy()
    px["policy_ret"] = np.where(px["ft_5_5"]==1, 5.0, px["exec_5d"])
    px = px.sort_values(["code","date"]).reset_index(drop=True)

    # M1 횡단면 z (날짜별)
    for c in CSZ_BASE:
        g = px.groupby("date")[c]
        px[f"csz_{c}"] = (px[c] - g.transform("mean")) / (g.transform("std") + 1e-9)
    M1 = [f"csz_{c}" for c in CSZ_BASE]

    # M2 잔차 모멘텀 (롤링 60d 베타 제거) + 고유변동성
    mkt = px.groupby("date")["ret_1d"].mean().rename("mkt_ret")
    px = px.join(mkt, on="date")
    g = px.groupby("code", group_keys=False)
    cov = g.apply(lambda f: f["ret_1d"].rolling(60, min_periods=40).cov(f["mkt_ret"]))
    var = g["mkt_ret"].apply(lambda s: s.rolling(60, min_periods=40).var())
    px["beta60"] = (cov / (var + 1e-12)).clip(-3, 5)
    px["resid_1d"] = px["ret_1d"] - px["beta60"] * px["mkt_ret"]
    gr = px.groupby("code", group_keys=False)["resid_1d"]
    px["resid_mom20"] = gr.apply(lambda s: s.rolling(20, min_periods=15).sum().shift(1))
    px["ivol20"] = gr.apply(lambda s: s.rolling(20, min_periods=15).std().shift(1))
    M2 = ["beta60", "resid_mom20", "ivol20"]

    # M3 시계열 구조: AR1(OU), 분산비(Hurst 근사), EWMA fast/slow vol
    def ts_feats(f):
        r = f["ret_1d"]
        ar1 = r.rolling(60, min_periods=40).apply(
            lambda w: np.corrcoef(w[:-1], w[1:])[0, 1] if np.std(w[:-1]) > 0 and np.std(w[1:]) > 0 else 0.0, raw=True)
        r5 = f["close"].pct_change(5)
        vr = (r5.rolling(40, min_periods=25).var() / (5 * r.rolling(40, min_periods=25).var() * 1e-4 + 1e-12)) * 1e-4
        ew_f = r.ewm(span=5, min_periods=5).std(); ew_s = r.ewm(span=60, min_periods=30).std()
        return pd.DataFrame({"ar1_60": ar1, "vratio5": vr, "ewvol_ratio": ew_f / (ew_s + 1e-9)}, index=f.index)
    ts = px.groupby("code", group_keys=False).apply(ts_feats)
    px = pd.concat([px, ts], axis=1)
    M3 = ["ar1_60", "vratio5", "ewvol_ratio"]

    # M4 시장 구조 (date-level)
    d = px.groupby("date")["ret_1d"]
    px = px.join(d.std().rename("xs_disp"), on="date")
    px = px.join(d.apply(lambda s: (s > 0).mean()).rename("breadth"), on="date")
    M4 = ["xs_disp", "breadth", "mkt_ret"]

    # 플라시보: 동수(17) 노이즈
    NZ = []
    for i in range(len(M1 + M2 + M3 + M4)):
        px[f"nz{i}"] = rng.standard_normal(len(px))
        NZ.append(f"nz{i}")
    return px.dropna(subset=["ft_5_5"]), {"M1": M1, "M2": M2, "M3": M3, "M4": M4, "NZ": NZ}


def wf_ev(px, feats, tag):
    pools = []
    for yr in (2024, 2025, 2026):
        t0 = pd.Timestamp(f"{yr}-01-01")
        tr = px[(px["date"] < t0) & (px["date"] >= t0 - pd.DateOffset(years=2))]
        te = px[(px["date"] >= t0) & (px["date"] < t0 + pd.DateOffset(years=1))].copy()
        if len(tr) < 20000 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
        m.fit(tr[feats].replace([np.inf,-np.inf], np.nan).clip(-1e4,1e4), tr["ft_5_5"])
        te["p"] = m.predict_proba(te[feats].replace([np.inf,-np.inf], np.nan).clip(-1e4,1e4))[:,1]
        pools.append(te.sort_values("p", ascending=False).groupby("date", group_keys=False).head(3))
    A = pd.concat(pools).dropna(subset=["policy_ret"])
    net = A["policy_ret"] - COST
    yrs = {int(k): round(v,3) for k,v in net.groupby(A["date"].dt.year).mean().items()}
    win = (A["ft_5_5"]==1).mean()*100
    print(f"  {tag:22s} EV={net.mean():+.3f} 터치={win:.1f}% 연도별 {yrs}", flush=True)
    return float(net.mean())


def main():
    px, F = build()
    print(f"패널 {len(px)} rows | 수학피처 {sum(len(v) for k,v in F.items() if k!='NZ')}개 생성", flush=True)
    base = wf_ev(px, FEATS, "베이스(35)")
    for k in ("M1", "M2", "M3", "M4"):
        wf_ev(px, FEATS + F[k], f"+{k}")
    allm = F["M1"] + F["M2"] + F["M3"] + F["M4"]
    wf_ev(px, FEATS + allm, "+전부(M1-4)")
    wf_ev(px, FEATS + F["NZ"], "+노이즈17(플라시보)")
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump({"done": True}, open(os.path.join(here, "math_features.done"), "w"))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
