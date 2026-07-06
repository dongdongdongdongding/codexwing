#!/usr/bin/env python3
"""승률 개선 레버 검증 (swing-main-41o8).

8y 분기 walk-forward rank-1..3 픽(배포 랭커와 동일 구성)에서:
  A) mkt_state(드로다운) 조건부 EV/승률 — 기권이 이득인가 손해인가
  B) 재픽 베토 — 직전 5세션 내 같은 종목을 더 낮은 가격에 재픽한 경우의 EV
  C) tail_p 거부 × 레짐 교호 — 드로다운에서만 최악 X% 거부
승률(ft_5_5 터치율)과 EV가 동행하는지 판정. 픽은 picks_8y.parquet 캐시(재사용).
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
import lightgbm as lgb

CACHE = "/Users/dongdong/research_cache"
PICKS_FP = os.path.join(HERE, "picks_8y.parquet")
FEATS = ["ret_1d","ret_3d","ret_5d","ret_10d","ret_20d","ret_60d","ma5_dist","ma20_dist","ma60_dist",
         "ma120_dist","ma20_slope","ma60_slope","rsi14","rsi_slope","accel","consec_up","dist_hi20",
         "dist_hi60","dist_hi120","dist_lo20","dist_lo60","pos20","bb_pctb","bb_bw","atr_pct","vol20",
         "close_loc","gap","vol_ratio","vol_trend","turn_z","obv_slope","cmf20","idx_mom20","idx_vol20"]
LIQ = {"KOSPI": 100e8, "KOSDAQ": 30e8}
COST = 0.3
VETO_F = ["dist_hi20","dist_hi60","consec_up","ret_5d","ret_20d","rsi14","atr_pct",
          "gap","vol_ratio","turn_z","bb_bw","liq_log","p","mkt_dd20","mkt_ret5"]


def gen_picks(mkt):
    cols = list(dict.fromkeys(["code","date","market","liq","ft_5_5","exec_5d","ret_1d","close"] + FEATS))
    px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
    px = px[px["market"] == mkt].copy()
    px["date"] = pd.to_datetime(px["date"])
    px["exec_5d"] = px["exec_5d"].replace([np.inf,-np.inf], np.nan)
    px = px[px["liq"] >= LIQ[mkt]]
    px["policy_ret"] = np.where(px["ft_5_5"] == 1, 5.0, px["exec_5d"])
    d = px.dropna(subset=["ft_5_5"] + FEATS[:6]).copy()
    mret = d.groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + mret/100).cumprod()
    st = pd.DataFrame({"mkt_dd20": (lvl/lvl.rolling(20).max()-1)*100,
                       "mkt_ret5": (lvl/lvl.shift(5)-1)*100})
    picks = []
    for q in pd.period_range("2019Q1","2026Q2",freq="Q"):
        t0, t1 = q.start_time, q.end_time
        tr = d[(d["date"] < t0) & (d["date"] >= t0 - pd.DateOffset(years=2))]
        te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
        m.fit(tr[FEATS].clip(-1e4,1e4), tr["ft_5_5"])
        te["p"] = m.predict_proba(te[FEATS].clip(-1e4,1e4))[:,1]
        pk = te.sort_values("p", ascending=False).groupby("date", group_keys=False).head(3)
        pk["rank"] = pk.groupby("date")["p"].rank(ascending=False, method="first")
        picks.append(pk)
        print(f"  {mkt} {q} done", flush=True)
    P = pd.concat(picks, ignore_index=True).join(st, on="date")
    P["liq_log"] = np.log10(P["liq"].clip(1))
    P["market"] = mkt
    return P


def seg(df, name):
    if df.empty:
        return f"{name:34s} n=0"
    net = df["policy_ret"] - COST
    win = (df["ft_5_5"] == 1).mean()*100
    yr = net.groupby(df["date"].dt.year).mean()
    return (f"{name:34s} n={len(df):5d} EV={net.mean():+.3f} 승률(터치)={win:.1f}% "
            f"CVaR10={net[net<=net.quantile(0.1)].mean():+.2f} yr+={int((yr>0).sum())}/{len(yr)}")


def main():
    if os.path.exists(PICKS_FP):
        P = pd.read_parquet(PICKS_FP)
        P["date"] = pd.to_datetime(P["date"])
        print(f"픽 캐시 재사용: {len(P)}", flush=True)
    else:
        P = pd.concat([gen_picks(m) for m in ("KOSDAQ","KOSPI")], ignore_index=True)
        P.to_parquet(PICKS_FP)
    P = P.dropna(subset=["policy_ret","mkt_dd20","mkt_ret5"]).sort_values("date").reset_index(drop=True)
    P["dd_state"] = ((P["mkt_dd20"] < -5) | (P["mkt_ret5"] < -3))
    P["sev_state"] = ((P["mkt_dd20"] < -12) | (P["mkt_ret5"] < -6))

    print("\n===== A) 레짐 조건부 (시장별) =====", flush=True)
    for mkt in ("KOSPI","KOSDAQ"):
        M = P[P["market"] == mkt]
        print(seg(M, f"{mkt} 전체"))
        print(seg(M[~M["dd_state"]], f"{mkt} NORMAL"))
        print(seg(M[M["dd_state"] & ~M["sev_state"]], f"{mkt} DRAWDOWN(경증 -5~-12)"))
        print(seg(M[M["sev_state"]], f"{mkt} SEVERE(dd<-12|ret5<-6)"))

    print("\n===== B) 재픽 베토 (직전 5세션 내 같은 종목, 더 낮은 진입가) =====", flush=True)
    P = P.sort_values(["market","code","date"]).reset_index(drop=True)
    g = P.groupby(["market","code"])
    P["prev_date"] = g["date"].shift(1)
    P["prev_close"] = g["close"].shift(1)
    gap_days = (P["date"] - P["prev_date"]).dt.days
    P["repick_lower"] = (gap_days <= 7) & (P["close"] < P["prev_close"])
    P["repick_any"] = gap_days <= 7
    print(seg(P[~P["repick_any"]], "신규픽"))
    print(seg(P[P["repick_any"] & ~P["repick_lower"]], "재픽(가격 유지/상승)"))
    print(seg(P[P["repick_lower"]], "재픽(하락 물타기)"))
    print(seg(P[P["repick_lower"] & P["dd_state"]], "재픽 물타기 × 드로다운"))

    print("\n===== C) tail_p 거부 × 레짐 (연도 walk-forward) =====", flush=True)
    P = P.sort_values("date").reset_index(drop=True)
    P["tail"] = (P["policy_ret"] <= -10).astype(int)
    years = sorted(P["date"].dt.year.unique())
    rows = []
    for yr in years:
        if yr < years[0] + 2:
            continue
        tr = P[P["date"].dt.year < yr]
        te = P[P["date"].dt.year == yr].copy()
        if tr["tail"].sum() < 50 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=50,
                               subsample=0.8, colsample_bytree=0.8, reg_lambda=3, random_state=0,
                               scale_pos_weight=5, verbose=-1)
        m.fit(tr[VETO_F].fillna(0), tr["tail"])
        te["tail_p"] = m.predict_proba(te[VETO_F].fillna(0))[:,1]
        rows.append(te)
    T = pd.concat(rows, ignore_index=True)
    print(f"OOS {T['date'].dt.year.min()}..{T['date'].dt.year.max()} n={len(T)}")
    for label, mask in (("전구간 거부", pd.Series(True, index=T.index)),
                        ("드로다운에서만 거부", T["dd_state"])):
        print(f"-- {label}")
        for v in (0.1, 0.2):
            th = T.loc[mask, "tail_p"].quantile(1 - v)
            keep = T[~(mask & (T["tail_p"] >= th))]
            print("  " + seg(keep, f"veto {v:.0%} 후"))
    print(seg(T, "베이스(거부 없음)"))

    json.dump({"done": True, "n": len(P)}, open(os.path.join(HERE, "winrate_levers.done"), "w"))
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
