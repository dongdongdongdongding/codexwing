#!/usr/bin/env python3
"""장중 레인(§7-E 구성) 8 OOS월 rank-1 픽을 레짐·픽프로필로 조건화 (swing-main-41o8).

라이브 부검 가설 검증:
  H1 과열픽(드로다운 중 rsi>=65 & ret_5d>0) = 꼬리원 → 베토 시 EV/승률 상승?
  H2 중간낙폭픽(ret_5d_d -13~-3, 미항복) 승률 저조, 항복픽(ret_5d_d<=-13)이 코어?
  H3 시장 드로다운 상태 전체기권은 손해인가(반등 놓침) 이득인가
KOSPI(t5)+KOSDAQ(t10) 모두, seed 0/1/2 평균으로 판정.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

os.chdir("/Users/dongdong/Projects/codex_swing/swing-main/research/harness_2026_07")
sys.path.insert(0, ".")
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
import lightgbm as lgb, xgboost as xgb
from sklearn.ensemble import ExtraTreesClassifier
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, assemble
from exit_policy_research import attach_paths
from model_zoo_intraday import policy_ret_frame

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/private/tmp/claude-501/-Users-dongdong-Projects-codex-swing-swing-main/4f929c12-f183-4aa8-ab51-372498389c15/scratchpad"
BASE = ITF + [c + "_d" for c in DLF]
COST = 0.3

# 시장상태 (px_long, causal)
px = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["date", "market", "ret_1d", "liq"])
px["date"] = pd.to_datetime(px["date"])
ST = {}
for mkt in ("KOSPI", "KOSDAQ"):
    liq = 100e8 if mkt == "KOSPI" else 30e8
    m = px[(px["market"] == mkt) & (px["liq"] >= liq)].groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + m / 100).cumprod()
    ST[mkt] = pd.DataFrame({"mkt_dd20": (lvl / lvl.rolling(20).max() - 1) * 100,
                            "mkt_ret5": (lvl / lvl.shift(5) - 1) * 100})

P = assemble()


def seg(df, name, tp):
    if df.empty:
        return f"  {name:36s} n=0"
    net = df["pret"] - COST
    win = (net > 0.3).mean() * 100
    mo = df.assign(m=df["date"].dt.to_period("M")).groupby("m").apply(lambda g: (g["pret"] - COST).mean())
    return (f"  {name:36s} n={len(df):4d} EV={net.mean():+.2f} 승률={win:.1f}% "
            f"worst={net.min():+.1f} negMo={int((mo<0).sum())}/{len(mo)}")


for mkt, tp in (("KOSPI", 5.0), ("KOSDAQ", 10.0)):
    gd = GUARDS[mkt]
    dm = P[P["mkt"] == mkt].dropna(subset=ITF + ["y3"]).sort_values("date").copy()
    dm = attach_paths(dm)
    dm["pret"] = policy_ret_frame(dm, tp)
    pools = []
    for seed in (0, 1, 2):
        for tm in TEST_MONTHS:
            t0 = pd.Timestamp(tm + "-01"); t1 = t0 + pd.offsets.MonthEnd(1)
            tr = dm[dm["date"] < t0]; te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
            if len(tr) < 3000 or te.empty:
                continue
            Xtr = tr[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
            Xte = te[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
            ps = []
            for m in (lgb.LGBMClassifier(n_estimators=400, learning_rate=0.04, num_leaves=31, min_child_samples=60,
                                         subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=seed, verbose=-1),
                      xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.04, subsample=0.8,
                                        colsample_bytree=0.7, reg_lambda=3, verbosity=0, n_jobs=-1, random_state=seed),
                      ExtraTreesClassifier(n_estimators=250, min_samples_leaf=40, random_state=seed, n_jobs=-1)):
                m.fit(Xtr, tr["y3"]); ps.append(m.predict_proba(Xte)[:, 1])
            te["p"] = np.mean(ps, axis=0)
            q = te[(te["liq"] >= gd["min_liq"]) & (te["close_vwap"] >= gd["vwap"]) & (te["idx_vol20_d"] >= gd["idx_vol_min"])]
            pk = q.sort_values("p", ascending=False).groupby("date", group_keys=False).head(1).copy()
            pk["seed"] = seed
            pools.append(pk)
    A = pd.concat(pools).dropna(subset=["pret"]).copy()
    A = A.join(ST[mkt], on="date")
    A["dd_state"] = (A["mkt_dd20"] < -5) | (A["mkt_ret5"] < -3)
    r5 = A["ret_5d_d"]
    A["overheat"] = (A["rsi14_d"] >= 65) & (r5 > 0)
    A["capitulated"] = r5 <= -13
    A["midfall"] = (r5 > -13) & (r5 <= -3)

    print(f"\n===== {mkt} (t{int(tp)}/5d, seed 0/1/2 합산) =====", flush=True)
    print(seg(A, "베이스 전체", tp))
    print(seg(A[~A["dd_state"]], "NORMAL 상태", tp))
    print(seg(A[A["dd_state"]], "DRAWDOWN 상태 (H3: 기권 손익?)", tp))
    D = A[A["dd_state"]]
    print(seg(D[D["overheat"]], "DD × 과열픽 (H1 베토 대상)", tp))
    print(seg(D[D["capitulated"]], "DD × 항복픽 (ret5d<=-13)", tp))
    print(seg(D[D["midfall"]], "DD × 중간낙폭 (H2 -13~-3)", tp))
    print(seg(D[~D["overheat"] & ~D["midfall"]], "DD × (과열+중간낙폭 베토 후)", tp))
    print(seg(A[~(A["dd_state"] & (A["overheat"] | A["midfall"]))], "전체 − DD베토 적용 (제안 정책)", tp))
    N = A[~A["dd_state"]]
    print(seg(N[N["overheat"]], "NORMAL × 과열픽 (베토 일반화 체크)", tp))
    print(seg(N[N["midfall"]], "NORMAL × 중간낙폭", tp))

json.dump({"done": True}, open(os.path.join(OUT, "intraday_regime_veto.done"), "w"))
print("\nDONE", flush=True)
