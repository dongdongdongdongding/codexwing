#!/usr/bin/env python3
"""A2 (swing-main-xz61, qyu3 실행): §39 섹터동반 항복 심화 — 사전등록.

운영자 평가 "너무 단순"에 대한 응답 4파트. §24/§39 기반 정의 승계:
항복 = ret_5d<=-13 (유동풀), policy_ret = touch5→+5 else exec_5d, 초과 = 같은날 횡단면 평균 대비.

P1 진앙 정의 다변화 + 적대 통제:
   D1 sec_q<=0.25 (배포본: 업종 60d 수익 분위) / D2 강도 sec_ret60<=-15% / D3 지속(20d AND 60d 하위¼)
   / D4 업종 flow(외인+기관 5d합) 하위¼.
   ⚠적대 통제 = D0 자기-60d: 종목 자신의 ret_60d 하위¼ 조건화가 섹터 조건화를 설명하는가 —
   이중정렬(자기60d 통제 후 섹터 증분)이 핵심 판정. 랜덤 섹터 플라시보(동일 크기 무작위 재배정) 동반.
P2 크래시 유형 분해: 시장 5d<=-3 에피소드를 KOFIA 반대매매 z로 청산형/공황형 구분(2018+)
   → 유형별 섹터동반 셀 EV.
P3 랭커 섹터 피처: §7-A 기계(분기 walk-forward, 2y LGBM) BASE vs +SECTOR(sec_q,sec_ret60,rs_vs_sec)
   vs +NOISE(동수 가우시안) — 시드 3, 같은 폴드 페어 대조, top-3 픽 net EV.
P4 비진앙 단독항복 정보성: 비진앙×시장비붕괴 항복의 fwd 20/60d 초과 — 지속 열위면 정보성 확인.

킬 기준(사전): P1 이중정렬 증분 <0.3%p 또는 랜덤섹터 플라시보와 구분 불가 → 섹터 조건화는
자기-모멘텀 프록시로 강등(배포 태그 재검토 제안). P3 SECTOR-BASE 페어 Δ가 NOISE-BASE Δ와
구분 불가(시드3 전체) → 랭커 피처 기각.
"""
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import pandas as pd

CACHE = os.path.expanduser("~/research_cache")
COST = 0.3
rng = np.random.default_rng(0)

print("=== 로드", flush=True)
cols = ["code", "date", "market", "liq", "industry", "ft_5_5", "exec_5d",
        "ret_5d", "ret_1d", "ret_20d", "ret_60d"]
px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
px["date"] = pd.to_datetime(px["date"])
liq_ok = ((px["market"] == "KOSPI") & (px["liq"] >= 100e8)) | ((px["market"] == "KOSDAQ") & (px["liq"] >= 30e8))
pxl = px[liq_ok].copy()
pxl["exec_5d"] = pxl["exec_5d"].replace([np.inf, -np.inf], np.nan)
pxl["policy_ret"] = np.where(pxl["ft_5_5"] == 1, 5.0, pxl["exec_5d"])
mret = pxl.groupby(["market", "date"])["ret_1d"].mean().rename("m1")
lvl = (1 + mret / 100).groupby("market").cumprod()
m5 = (lvl / lvl.groupby("market").shift(5) - 1) * 100
pxl = pxl.join(m5.rename("mkt5"), on=["market", "date"])
pxl["pol_ex"] = pxl["policy_ret"] - pxl.groupby("date")["policy_ret"].transform("mean")

# 업종 일별 시계열 (전 유니버스 px 기준 — 현행 분류를 과거에 소급 적용, 한계 명시)
ind = px[px["industry"].notna() & (px["industry"] != "NA")]
sec60 = ind.groupby(["industry", "date"])["ret_60d"].mean().rename("sec_ret60")
sec20 = ind.groupby(["industry", "date"])["ret_20d"].mean().rename("sec_ret20")
secn = ind.groupby(["industry", "date"])["ret_60d"].size().rename("sec_n")
sec = pd.concat([sec60, sec20, secn], axis=1).reset_index()
sec = sec[sec["sec_n"] >= 5]
sec["sec_q"] = sec.groupby("date")["sec_ret60"].rank(pct=True)
sec["sec_q20"] = sec.groupby("date")["sec_ret20"].rank(pct=True)
pxl = pxl.merge(sec[["industry", "date", "sec_ret60", "sec_q", "sec_q20"]], on=["industry", "date"], how="left")
pxl["own_q60"] = pxl.groupby("date")["ret_60d"].rank(pct=True)

cap = pxl[pxl["ret_5d"] <= -13].dropna(subset=["policy_ret", "mkt5", "sec_q"]).copy()
print(f"항복 표본 n={len(cap)} (8y, sec_q 조인 후)", flush=True)


def stat(d, name, min_n=150):
    v = d["pol_ex"].dropna()
    if len(v) < min_n:
        print(f"  {name:52s} n={len(v)} 부족")
        return None
    bs = [rng.choice(v.values, len(v), True).mean() for _ in range(300)]
    yr = v.groupby(d["date"].dt.year).mean()
    r = (float(v.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
    print(f"  {name:52s} n={len(v):6d} 초과={r[0]:+.3f} CI[{r[1]:+.2f},{r[2]:+.2f}] yr+={int((yr > 0).sum())}/{len(yr)}")
    return r


print("\n=== P1. 진앙 정의 다변화 + 적대 통제", flush=True)
stat(cap, "항복 전체 (기준선)")
defs = {
    "D1 sec_q<=0.25 (배포본)": cap["sec_q"] <= 0.25,
    "D2 강도 sec_ret60<=-15%": cap["sec_ret60"] <= -15,
    "D3 지속 (20d AND 60d 하위 1/4)": (cap["sec_q"] <= 0.25) & (cap["sec_q20"] <= 0.25),
    "D0 자기-60d 하위 1/4 (적대 통제)": cap["own_q60"] <= 0.25,
}
for nm, m in defs.items():
    stat(cap[m], nm)
    stat(cap[~m], nm.split(" ")[0] + " 여집합")
print("-- 이중정렬: 자기-60d 통제 후 섹터 증분", flush=True)
for own_band, om in (("자기60d 하위1/4 내", cap["own_q60"] <= 0.25), ("자기60d 상위3/4 내", cap["own_q60"] > 0.25)):
    sub = cap[om]
    a = stat(sub[sub["sec_q"] <= 0.25], f"  [{own_band}] 진앙", min_n=100)
    b = stat(sub[sub["sec_q"] > 0.5], f"  [{own_band}] 비진앙", min_n=100)
    if a and b:
        print(f"    → 섹터 증분(진앙-비진앙) = {a[0] - b[0]:+.3f}%p")
print("-- 랜덤 섹터 플라시보 (20회: 업종 라벨 무작위 재배정 후 D1 스프레드)", flush=True)
real_spread = float(cap[cap["sec_q"] <= 0.25]["pol_ex"].mean() - cap[cap["sec_q"] > 0.5]["pol_ex"].mean())
ph = []
codes = pxl[["code", "industry"]].drop_duplicates("code")
for k in range(20):
    r2 = np.random.default_rng(100 + k)
    fake = dict(zip(codes["code"], r2.permutation(codes["industry"].values)))
    tmp = pxl[["code", "date", "ret_60d"]].copy()
    tmp["find"] = tmp["code"].map(fake)
    fs = tmp.groupby(["find", "date"])["ret_60d"].agg(["mean", "size"]).reset_index()
    fs = fs[fs["size"] >= 5]
    fs["fq"] = fs.groupby("date")["mean"].rank(pct=True)
    cf = cap.merge(fs[["find", "date", "fq"]].rename(columns={"find": "industry"}),
                   on=["industry", "date"], how="left")
    # 주의: cap의 industry는 진짜 — 가짜 라벨은 code로 다시 매핑
    cf["find"] = cf["code"].map(fake)
    cf = cap.reset_index(drop=True).assign(find=cap["code"].map(fake).values).merge(
        fs[["find", "date", "fq"]], on=["find", "date"], how="left").dropna(subset=["fq"])
    ph.append(float(cf[cf["fq"] <= 0.25]["pol_ex"].mean() - cf[cf["fq"] > 0.5]["pol_ex"].mean()))
print(f"  진짜 D1 스프레드 {real_spread:+.3f} vs 랜덤섹터 {np.mean(ph):+.3f}±{np.std(ph):.3f} "
      f"(p_perm={np.mean([abs(p) >= abs(real_spread) for p in ph]):.2f})", flush=True)

print("\n=== P2. 크래시 유형 분해 (KOFIA 반대매매 z, 2018+)", flush=True)
ko = pd.read_parquet(f"{CACHE}/kofia_stress.parquet")
dep = ko[ko["kind"] == "deposit"].set_index("date").sort_index()
fz = ((dep["forced_sell_amt"] - dep["forced_sell_amt"].rolling(120).mean())
      / dep["forced_sell_amt"].rolling(120).std()).rename("fz")
cap2 = cap[cap["date"] >= "2018-07-01"].join(fz, on="date")
crash = cap2[cap2["mkt5"] <= -3].copy()
liq_type = crash["fz"] >= 2      # 청산형: 반대매매 z>=2 동반
print(f"동반붕괴 항복 n={len(crash)} | 청산형(반대매매 z>=2) {int(liq_type.sum())} / 공황·일반형 {int((~liq_type).sum())}")
for tnm, tm in (("청산형", liq_type), ("공황·일반형", ~liq_type)):
    sub = crash[tm]
    stat(sub[sub["sec_q"] <= 0.25], f"{tnm} × 진앙", min_n=80)
    stat(sub[sub["sec_q"] > 0.5], f"{tnm} × 비진앙", min_n=80)

print("\n=== P4. 비진앙 단독항복의 정보성 (fwd 20/60d 초과)", flush=True)
fwd = px[["code", "date", "ret_20d", "ret_60d"]].copy()
fwd["date_sig"] = fwd.groupby("code")["date"].shift(0)
# fwd 수익: t+20/t+60의 ret_20d/ret_60d를 당겨오기 (달력 아닌 거래일 시프트)
px_s = px.sort_values(["code", "date"])
px_s["fwd20"] = px_s.groupby("code")["ret_20d"].shift(-20)
px_s["fwd60"] = px_s.groupby("code")["ret_60d"].shift(-60)
cap3 = cap.merge(px_s[["code", "date", "fwd20", "fwd60"]], on=["code", "date"], how="left")
for h in ("fwd20", "fwd60"):
    cap3[h + "_ex"] = cap3[h] - cap3.groupby("date")[h].transform("mean")
loner = cap3[(cap3["mkt5"] > -3) & (cap3["sec_q"] > 0.5)]
epi_c = cap3[(cap3["mkt5"] <= -3) & (cap3["sec_q"] <= 0.25)]
for nm, d in (("비진앙×시장비붕괴 (단독항복)", loner), ("진앙×동반붕괴 (반등코어)", epi_c)):
    for h in ("fwd20_ex", "fwd60_ex"):
        v = d[h].dropna()
        if len(v) >= 100:
            bs = [rng.choice(v.values, len(v), True).mean() for _ in range(300)]
            print(f"  {nm:32s} {h}: {v.mean():+.2f} CI[{np.percentile(bs, 2.5):+.2f},{np.percentile(bs, 97.5):+.2f}] n={len(v)}")

print("\n=== P3. 랭커 섹터 피처 페어 대조 (분기 WF, 시드3 — 시간 소요)", flush=True)
import lightgbm as lgb
FEATS = ["ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d", "ret_60d", "ma5_dist", "ma20_dist", "ma60_dist",
         "ma120_dist", "ma20_slope", "ma60_slope", "rsi14", "rsi_slope", "accel", "consec_up", "dist_hi20",
         "dist_hi60", "dist_hi120", "dist_lo20", "dist_lo60", "pos20", "bb_pctb", "bb_bw", "atr_pct", "vol20",
         "close_loc", "gap", "vol_ratio", "vol_trend", "turn_z", "obv_slope", "cmf20", "idx_mom20", "idx_vol20"]
pxf = pd.read_parquet(f"{CACHE}/px_long.parquet",
                      columns=list(dict.fromkeys(["code", "date", "market", "liq", "industry", "ft_5_5", "exec_5d"] + FEATS)))
pxf["date"] = pd.to_datetime(pxf["date"])
lq = ((pxf["market"] == "KOSPI") & (pxf["liq"] >= 100e8)) | ((pxf["market"] == "KOSDAQ") & (pxf["liq"] >= 30e8))
pxf = pxf[lq].merge(sec[["industry", "date", "sec_ret60", "sec_q"]], on=["industry", "date"], how="left")
pxf["rs_vs_sec"] = pxf["ret_60d"] - pxf["sec_ret60"]
pxf["policy_ret"] = np.where(pxf["ft_5_5"] == 1, 5.0, pxf["exec_5d"].replace([np.inf, -np.inf], np.nan))
SEC_F = ["sec_q", "sec_ret60", "rs_vs_sec"]
qs = pd.period_range("2021Q1", "2026Q2", freq="Q")   # 최근 5.5y 폴드(시간 절약, 22폴드×2시장)
res = {}
for variant in ("BASE", "SECTOR", "NOISE"):
    for seed in (0, 1, 2):
        evs = []
        for q in qs:
            t0, t1 = q.start_time, q.end_time
            for mkt in ("KOSPI", "KOSDAQ"):
                d = pxf[pxf["market"] == mkt]
                tr = d[(d["date"] < t0) & (d["date"] >= t0 - pd.DateOffset(years=2))].dropna(subset=["ft_5_5"])
                te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
                if len(tr) < 20000 or te.empty:
                    continue
                f = FEATS.copy()
                if variant == "SECTOR":
                    f += SEC_F
                elif variant == "NOISE":
                    r3 = np.random.default_rng(1000 + seed)
                    for j in range(3):
                        tr = tr.assign(**{f"nz{j}": r3.normal(size=len(tr))})
                        te = te.assign(**{f"nz{j}": np.random.default_rng(2000 + seed + j).normal(size=len(te))})
                    f += [f"nz{j}" for j in range(3)]
                m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=63,
                                       min_child_samples=100, subsample=0.8, colsample_bytree=0.7,
                                       reg_lambda=5, random_state=seed, verbose=-1)
                m.fit(tr[f].fillna(0).clip(-1e4, 1e4), tr["ft_5_5"])
                te["p"] = m.predict_proba(te[f].fillna(0).clip(-1e4, 1e4))[:, 1]
                top = te.sort_values("p", ascending=False).groupby("date").head(3)
                evs.append(top["policy_ret"].dropna() - COST)
        allv = pd.concat(evs)
        res[(variant, seed)] = float(allv.mean())
        print(f"  {variant} seed{seed}: net EV {allv.mean():+.3f} (n={len(allv)})", flush=True)
for v in ("SECTOR", "NOISE"):
    ds = [res[(v, s)] - res[("BASE", s)] for s in (0, 1, 2)]
    print(f"  Δ({v}-BASE) 시드3: {['%+.3f' % x for x in ds]} 평균 {np.mean(ds):+.3f}")
print("DONE", flush=True)
