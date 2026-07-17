#!/usr/bin/env python3
"""나스닥 테이프 × US 국면 조건화 (사전등록, swing-main-gja0). §31 유도: 나스닥은 전 국면
지수 양수(buy-the-dip)라 KR식 베토 이식 금지 — 대신 레인 픽의 국면 조건부 EV를 직접 측정.
셀 4개 고정(§31과 동일 정의). 판정: 음수 CI 셀 발견 시에만 soft 베토 제안."""
import os, sys, warnings, json
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main/research/harness_2026_07")
os.chdir("/Users/dongdong/Projects/codex_swing/swing-main/research/harness_2026_07")
import importlib
p2 = importlib.import_module("nasdaq_session_p2")
HERE = "/private/tmp/claude-501/-Users-dongdong-Projects-codex-swing-swing-main/4f929c12-f183-4aa8-ab51-372498389c15/scratchpad"
rng = np.random.default_rng(0)
# p2.main()의 풀 생성 로직 재사용이 어려우면 직접 실행 후 파일로? p2는 main에서 print만 —
# 간단히: main 내부 로직 복제 대신 rank-1 풀만 재생성
sf = p2.session_features()
# p2.main()의 라벨 병합 재현: 8y 패널에서 ft_5_5 + 경로(h1..h5,o1..o5,c5) → pol5
cols = ["date", "symbol", "open", "high", "close", "ft_5_5"] + p2.DLF
pxp = pd.read_parquet(p2.PANEL, columns=list(dict.fromkeys(cols)))
pxp["date"] = pd.to_datetime(pxp["date"])
pxp = pxp.sort_values(["symbol", "date"]).reset_index(drop=True)
g = pxp.groupby("symbol")
for k in range(1, 6):
    pxp[f"h{k}"] = g["high"].shift(-k)
    pxp[f"o{k}"] = g["open"].shift(-k)
pxp["c5"] = g["close"].shift(-5)
sf = sf.merge(pxp, on=["symbol", "date"], how="inner")
e = sf["close"].values
pol5 = (sf["c5"].values / e - 1) * 100
tgt = e * 1.05
done = np.zeros(len(sf), bool)
for k in range(1, 6):
    hit = (~done) & np.isfinite(sf[f"h{k}"].values) & (sf[f"h{k}"].values >= tgt)
    if k > 1:
        fill = np.maximum(tgt, sf[f"o{k}"].values)
    else:
        fill = tgt
    pol5 = np.where(hit, (fill / e - 1) * 100, pol5)
    done |= hit
sf["pol5"] = pol5
import FinanceDataReader as fdr
ix = fdr.DataReader("IXIC", "2018-01-01")["Close"]
ix.index = pd.to_datetime(ix.index).tz_localize(None).normalize()
dd20 = (ix/ix.rolling(20).max()-1)*100
r5 = (ix/ix.shift(5)-1)*100
r20 = (ix/ix.shift(20)-1)*100
ph = pd.Series("NORMAL", index=ix.index)
ph[r5<=-3] = "동반붕괴"
ph[(dd20<-8)&(r5>-3)] = "반등국면"
ph[(dd20>-2)&(r20>8)] = "과열"
# p2 main 재현 (rank-1 픽 풀)
import lightgbm as lgb
d = sf.dropna(subset=["ft_5_5"]).sort_values("date").copy()
# 누수 차단: 미래 경로(h*,o*,c5)·가격 원값 제외 — 세션피처 + DLF만
_ban = {"date","symbol","ft_5_5","pol5","pol10","open","high","low","close","c5"} | {f"h{k}" for k in range(1,6)} | {f"o{k}" for k in range(1,6)}
FE = [c for c in d.columns if c not in _ban and d[c].dtype != object]
print("피처 수:", len(FE), "| 경로컬럼 잔존:", [c for c in FE if c.startswith(('h','o')) and len(c)==2])
months = sorted(d["date"].dt.to_period("M").unique())
pools = []
for tm in months[6:]:
    t0, t1 = tm.start_time, tm.end_time
    tr = d[d["date"]<t0]; te = d[(d["date"]>=t0)&(d["date"]<=t1)].copy()
    if len(tr)<3000 or te.empty: continue
    m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=60,
                           subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)
    m.fit(tr[FE].replace([np.inf,-np.inf],np.nan).fillna(0), tr["ft_5_5"])
    te["p"] = m.predict_proba(te[FE].replace([np.inf,-np.inf],np.nan).fillna(0))[:,1]
    pools.append(te.sort_values("p",ascending=False).groupby("date",group_keys=False).head(1))
A = pd.concat(pools).dropna(subset=["pol5"])
A["phase"] = A["date"].map(ph)
def seg(dd, name):
    v = dd["pol5"] - 0.25
    if len(v)<25: print(f"  {name:14s} n={len(v)} 부족"); return
    bs=[rng.choice(v.values,len(v),True).mean() for _ in range(300)]
    print(f"  {name:14s} n={len(v):4d} EV={v.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] 승={(v>0).mean()*100:.0f}%")
print(f"rank-1 풀 {len(A)} ({A['date'].min().date()}..{A['date'].max().date()})")
seg(A, "전체")
for p in ("동반붕괴","반등국면","NORMAL","과열"):
    seg(A[A["phase"]==p], p)
json.dump({"done": True}, open(os.path.join(HERE, "nasdaq_phase.done"), "w"))
print("DONE", flush=True)
