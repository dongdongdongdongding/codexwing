#!/usr/bin/env python3
"""신규 엣지 후보: 회복 확인 신호 (사전등록 2정의 고정 — 국면 전환기 전용 연구).
질문: 반등국면(현재, 검증된 데드존)의 '끝'을 조기 확인할 수 있는가 — 확인 시점부터
NORMAL 플레이(모멘텀·B·코스피 장중 재가동)를 앞당기는 엣지.
D1 dd회복 확인: dd20이 -12 미만 찍은 후 처음으로 -8 위로 복귀한 날
D2 breadth 서지: 풀 내 종목 중 ma20 상회 비율이 30% 미만에서 55% 위로 복귀한 날
결과: 이벤트 후 10d/20d — ①스윙픽 EV ②모멘텀 프로필(과열셀) forward ③지수(블록CI)
플라시보: 이벤트 날짜 원형시프트 100회. 킬: 플라시보 분리 실패 시 기각."""
import os, warnings, json
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(0)
px = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet",
                     columns=["code","date","market","ret_1d","liq","ma20_dist","ret_5d","rsi14","ft_5_5","exec_5d"])
px["date"] = pd.to_datetime(px["date"])
P = pd.read_parquet("/Users/dongdong/research_cache/picks_8y_swing.parquet")
P["date"] = pd.to_datetime(P["date"]); P["net"] = P["policy_ret"] - 0.3

def block_ci(v, B=300, block=5):
    v = np.asarray(v); n = len(v); nb = max(1, n // block)
    ms = []
    for _ in range(B):
        st = rng.integers(0, max(1, n - block), nb)
        ms.append(np.nanmean(np.concatenate([v[s:s+block] for s in st])[:n]))
    return np.percentile(ms, 2.5), np.percentile(ms, 97.5)

for mkt in ("KOSPI", "KOSDAQ"):
    liq = 100e8 if mkt == "KOSPI" else 30e8
    d = px[(px["market"] == mkt) & (px["liq"] >= liq)]
    g = d.groupby("date")
    m = g["ret_1d"].mean().sort_index()
    lvl = (1 + m / 100).cumprod()
    dd20 = (lvl / lvl.rolling(20).max() - 1) * 100
    breadth = g.apply(lambda x: (x["ma20_dist"] > 0).mean() * 100).sort_index()
    f10 = (lvl.shift(-10) / lvl - 1) * 100
    f20 = (lvl.shift(-20) / lvl - 1) * 100
    # D1: dd<-12 경험 후 첫 -8 상회
    deep = (dd20 < -12)
    was_deep = deep.rolling(15, min_periods=1).max().astype(bool)
    cross = (dd20 > -8) & (dd20.shift(1) <= -8) & was_deep.shift(1).fillna(False)
    d1 = dd20.index[cross]
    # D2: breadth 30 미만 경험 후 55 상회
    lowb = (breadth < 30).rolling(15, min_periods=1).max().astype(bool)
    crossb = (breadth > 55) & (breadth.shift(1) <= 55) & lowb.shift(1).fillna(False)
    d2 = breadth.index[crossb]
    pk = P[P["market"] == mkt]
    print(f"== {mkt}: D1 {len(d1)}회 / D2 {len(d2)}회")
    for nm, evts in (("D1 dd회복", d1), ("D2 breadth", d2)):
        if len(evts) < 8:
            print(f"  {nm}: 이벤트 {len(evts)}회 부족"); continue
        i10 = f10.reindex(evts).dropna(); i20 = f20.reindex(evts).dropna()
        lo, hi = block_ci(i10.values, block=1)  # 이벤트 간 독립 근사(희소)
        # 이벤트 후 10일 내 스윙픽 EV
        win_ev = []
        for e in evts:
            w = pk[(pk["date"] > e) & (pk["date"] <= e + pd.Timedelta(days=14))]["net"].dropna()
            if len(w): win_ev.append(w.mean())
        # 플라시보: 원형시프트
        plc = []
        vals = f10.dropna()
        for _ in range(100):
            k = rng.integers(30, len(vals) - 30)
            sh = pd.Series(np.roll(vals.values, k), index=vals.index)
            plc.append(sh.reindex(evts).dropna().mean())
        p95 = np.nanpercentile(np.abs(np.array(plc) - vals.mean()), 95)
        sig = "✅" if abs(i10.mean() - vals.mean()) > p95 else "―"
        print(f"  {nm}: 지수 10d {i10.mean():+.2f} CI[{lo:+.2f},{hi:+.2f}] (기저 {vals.mean():+.2f}, 플라시보95 {p95:.2f}) {sig} | 20d {i20.mean():+.2f} | 후속 스윙픽 EV {np.mean(win_ev):+.2f} (n이벤트 {len(win_ev)})")
json.dump({"done": True}, open(os.path.join(HERE, "recovery_confirmation.done"), "w"))
print("DONE", flush=True)
