#!/usr/bin/env python3
"""웨이브4: 거시 조건부 발행 게이트 (사전등록 5축 고정 — 낚시 금지).
질문: 종목선택이 아니라 '오늘 발행이 적기인가'를 거시가 알려주는가.
스트림: 스윙 8y 픽(picks_8y_swing) — 일단위 조건부 EV. 각 축 3분할, 셔플 플라시보, 연도 일관성.
축: A1 US(IXIC) 전일 수익 / A2 USDKRW 5d 변화 / A3 반도체 프록시(SOX) 전일 / A4 어닝스시즌 / A5 idx_vol 레벨."""
import os, warnings, json
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import FinanceDataReader as fdr
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(0)
P = pd.read_parquet("/Users/dongdong/research_cache/picks_8y_swing.parquet")
P["date"] = pd.to_datetime(P["date"])
P["net"] = P["policy_ret"] - 0.3
# 거시 시계열 (2018~) — 신호는 픽 날짜에 '알 수 있는' 값 (US 전일 종가 등)
ix = fdr.DataReader("IXIC", "2018-01-01")["Close"]
sox = None
for s in ("SOXX", "SOX"):
    try:
        sox = fdr.DataReader(s, "2018-01-01")["Close"]; break
    except Exception: pass
fx = fdr.DataReader("USD/KRW", "2018-01-01")["Close"]
def as_daily(s):
    s = s.copy(); s.index = pd.to_datetime(s.index).tz_localize(None).normalize(); return s[~s.index.duplicated()]
ix, fx = as_daily(ix), as_daily(fx)
sox = as_daily(sox) if sox is not None else None
cal = pd.DatetimeIndex(sorted(P["date"].unique()))
ctx = pd.DataFrame(index=cal)
# KR 날짜 d의 픽 → 직전 미국 세션 = d-1 (KST 아침에 확정) → asof로 정렬
ixr = ix.pct_change() * 100
ctx["us_prev"] = ixr.reindex(ixr.index.union(cal - pd.Timedelta(days=1))).ffill().reindex(cal - pd.Timedelta(days=1)).values
fx5 = (fx / fx.shift(5) - 1) * 100
ctx["fx_5d"] = fx5.reindex(fx5.index.union(cal)).ffill().reindex(cal).values
if sox is not None:
    sxr = sox.pct_change() * 100
    ctx["sox_prev"] = sxr.reindex(sxr.index.union(cal - pd.Timedelta(days=1))).ffill().reindex(cal - pd.Timedelta(days=1)).values
ctx["earn_season"] = cal.month.isin([1, 4, 7, 10]) & (cal.day >= 10) & (cal.day <= 31)
iv = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["date","market","idx_vol20"])
iv["date"] = pd.to_datetime(iv["date"])
ivs = iv[iv["market"]=="KOSPI"].drop_duplicates("date").set_index("date")["idx_vol20"]
ctx["ivol"] = ivs.reindex(cal).values
P = P.join(ctx, on="date")

def seg(d, name):
    v = d["net"].dropna()
    if len(v) < 300: print(f"  {name:30s} n={len(v)} 부족"); return
    bs = [rng.choice(v.values, len(v), True).mean() for _ in range(300)]
    yr = v.groupby(d["date"].dt.year).mean()
    print(f"  {name:30s} n={len(v):5d} EV={v.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] 터치={(d['ft_5_5']==1).mean()*100:.0f}% yr+={int((yr>0).sum())}/{len(yr)}")

AXES = [("us_prev", "A1 US 전일"), ("fx_5d", "A2 환율 5d"), ("sox_prev", "A3 반도체 전일"), ("ivol", "A5 idx_vol")]
for col, nm in AXES:
    if col not in P or P[col].isna().all(): print(f"{nm}: 데이터 없음"); continue
    q = P[col].rank(pct=True)
    print(f"== {nm}")
    seg(P[q <= 0.3], "  하위 30%")
    seg(P[(q > 0.3) & (q <= 0.7)], "  중간")
    seg(P[q > 0.7], "  상위 30%")
print("== A4 어닝스시즌")
seg(P[P["earn_season"] == True], "  시즌 중")
seg(P[P["earn_season"] == False], "  시즌 외")
print("== 플라시보 (일자 셔플 — 축별 최강 셀 재현성 기준선)")
dates = P["date"].unique(); perm = dict(zip(dates, rng.permutation(dates)))
Pp = P.copy(); Pp["pd"] = Pp["date"].map(perm)
for col, nm in AXES[:1]:
    ctx2 = P.drop_duplicates("date").set_index("date")[col]
    Pp[col+"_plc"] = Pp["pd"].map(ctx2)
    q = Pp[col+"_plc"].rank(pct=True)
    seg(Pp[q <= 0.3], f"  플라시보 {nm} 하위30%")
    seg(Pp[q > 0.7], f"  플라시보 {nm} 상위30%")
json.dump({"done": True}, open(os.path.join(HERE, "macro_gate.done"), "w"))
print("DONE", flush=True)
