#!/usr/bin/env python3
"""현실 진입가 × 티커별 출구 설계 (사전등록, 운영자 지시).
데이터: picks_8y(스윙 rank1-3) × ohlc_full(8y 경로). 평가 = 정책 EV/발행픽(미체결=0 포함), 비용 0.3.

진입 (스윙): E0 익일시가(현행) / E1 지정가 전일종가(미체결시 놓침) / E2 지정가 시가-0.5ATR /
  E3 갭업 +2% 초과 스킵(뉴스팝 보조정리) — fill률과 총EV 함께.
출구 (E0 진입 고정): X0 +5%터치/5d(현행) / X1 ATR배리어 +1.5×ATR / X2 트레일링 고점-1.5ATR /
  X3 시간가변(3일 미터치→목표 +3%) / X4 부분청산(+5% 반청산+트레일) — ATR 밴드별 분해.
"""
import os, sys, warnings, json
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(0)
P = pd.read_parquet("/Users/dongdong/research_cache/picks_8y_swing.parquet")
P["date"] = pd.to_datetime(P["date"]); P["code"] = P["code"].astype(str)
OH = pd.read_parquet("/Users/dongdong/research_cache/ohlc_full.parquet")
OH["date"] = pd.to_datetime(OH["date"]); OH["code"] = OH["code"].astype(str)
OH = OH.sort_values(["code","date"]).set_index("code")
print(f"픽 {len(P)} | 경로 {OH.index.nunique()}종목", flush=True)
paths = {c: g.reset_index(drop=True) for c, g in OH.groupby(level=0)}

def get_win(code, date, n=6):
    g = paths.get(code)
    if g is None: return None
    w = g[g["date"] > date].head(n)
    return w if len(w) >= 2 else None

COST = 0.3
def run(policy_fn, name, atr_split=True):
    rows = []
    for _, r in P.iterrows():
        w = get_win(r["code"], r["date"])
        if w is None: continue
        ret = policy_fn(r, w)
        if ret is not None:
            rows.append((r["date"], r.get("atr_pct", np.nan), ret))
    d = pd.DataFrame(rows, columns=["date","atr","ret"])
    net = d["ret"] - COST
    filled = d["ret"].notna()
    bs = [rng.choice(net.values, len(net), True).mean() for _ in range(200)]
    yr = net.groupby(d["date"].dt.year).mean()
    print(f"  {name:34s} n={len(d):5d} EV={net.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] "
          f"승={(net>0).mean()*100:.0f}% yr+={int((yr>0).sum())}/{len(yr)}", flush=True)
    if atr_split and d["atr"].notna().mean() > 0.5:
        q = d["atr"].rank(pct=True)
        for nm, m in (("저ATR", q<=0.33), ("고ATR", q>0.67)):
            v = net[m]
            if len(v) > 200: print(f"    {nm}: EV={v.mean():+.3f} 승={(v>0).mean()*100:.0f}%", flush=True)
    return net.mean()

# ---- 진입 연구 (출구 = 현행 +5%/5d 터치) ----
def touch_exit(entry, w, tp=0.05, days=5):
    tgt = entry * (1 + tp)
    for k in range(min(days, len(w))):
        if w["high"].iloc[k] >= tgt:
            o = w["open"].iloc[k]
            fill = max(tgt, o) if k > 0 else tgt
            return (fill / entry - 1) * 100
    k = min(days, len(w)) - 1
    return (w["close"].iloc[k] / entry - 1) * 100

def e0(r, w):  # 익일 시가 (현행)
    e = w["open"].iloc[0]
    return touch_exit(e, w) if e > 0 else None
def e1(r, w):  # 지정가 = 전일종가, 익일 저가가 닿아야 체결; 미체결 = 0
    lim = r["close"]
    if w["low"].iloc[0] <= lim:
        e = min(lim, w["open"].iloc[0])
        return touch_exit(e, w)
    return 0.0 + COST  # 미체결: 비용도 없음 → net 0 되게 보정
def e2(r, w):  # 지정가 = 시가 - 0.5*ATR
    atr = r.get("atr_pct", np.nan)
    if not np.isfinite(atr): return None
    lim = w["open"].iloc[0] * (1 - 0.005 * atr)
    if w["low"].iloc[0] <= lim:
        return touch_exit(lim, w)
    return 0.0 + COST
def e3(r, w):  # 갭업 +2% 초과 스킵
    e = w["open"].iloc[0]
    if e / r["close"] - 1 > 0.02:
        return 0.0 + COST
    return touch_exit(e, w) if e > 0 else None

print("===== 진입 설계 (출구 고정 +5%/5d) =====", flush=True)
run(e0, "E0 익일시가 (현행)")
run(e1, "E1 지정가 전일종가 (미체결=0)")
run(e2, "E2 지정가 시가-0.5ATR (미체결=0)")
run(e3, "E3 갭업>2% 스킵")

# ---- 출구 연구 (진입 고정 = 익일시가) ----
def x1(r, w):  # ATR 배리어: +1.5*ATR 터치
    e = w["open"].iloc[0]
    atr = r.get("atr_pct", np.nan)
    if not (e > 0 and np.isfinite(atr)): return None
    return touch_exit(e, w, tp=0.015 * atr, days=5)
def x2(r, w):  # 트레일링: 고점 대비 -1.5*ATR 이탈 종가 청산 (일봉 근사: 종가 기준)
    e = w["open"].iloc[0]; atr = r.get("atr_pct", np.nan)
    if not (e > 0 and np.isfinite(atr)): return None
    hi = e
    for k in range(min(5, len(w))):
        hi = max(hi, w["high"].iloc[k])
        if w["close"].iloc[k] <= hi * (1 - 0.015 * atr):
            return (w["close"].iloc[k] / e - 1) * 100
    k = min(5, len(w)) - 1
    return (w["close"].iloc[k] / e - 1) * 100
def x3(r, w):  # 시간가변: 1-3일 +5%, 4-5일 +3%
    e = w["open"].iloc[0]
    if e <= 0: return None
    for k in range(min(5, len(w))):
        tp = 0.05 if k < 3 else 0.03
        tgt = e * (1 + tp)
        if w["high"].iloc[k] >= tgt:
            o = w["open"].iloc[k]
            return (max(tgt, o) / e - 1) * 100 if k > 0 else (tgt / e - 1) * 100
    k = min(5, len(w)) - 1
    return (w["close"].iloc[k] / e - 1) * 100
def x4(r, w):  # 부분: +5% 터치시 절반 익절, 나머지 5d 종가
    e = w["open"].iloc[0]
    if e <= 0: return None
    tgt = e * 1.05
    k5 = min(5, len(w)) - 1
    tail = (w["close"].iloc[k5] / e - 1) * 100
    for k in range(k5 + 1):
        if w["high"].iloc[k] >= tgt:
            first = (max(tgt, w["open"].iloc[k]) / e - 1) * 100 if k > 0 else 5.0
            return 0.5 * first + 0.5 * tail
    return tail

print("\n===== 출구 설계 (진입 고정 익일시가) =====", flush=True)
run(e0, "X0 +5%터치/5d (현행)")
run(x1, "X1 ATR배리어 +1.5×ATR")
run(x2, "X2 트레일링 고점-1.5ATR")
run(x3, "X3 시간가변 5%→3%")
run(x4, "X4 부분청산 (반+반)")
json.dump({"done": True}, open(os.path.join(HERE, "entry_exit_design.done"), "w"))
print("\nDONE", flush=True)
