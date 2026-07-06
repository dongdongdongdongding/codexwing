"""묘지 재감사 1호 (swing-main-e639): 폭락 서식지 전용 반등 레인.
서식지 = 인과적 드로다운 상태(dd20<-5 | ret5<-3, §6 검증). 그 창 안에서만:
과매도 풀(하위 20% ret_5d) → ML 랭킹(ft_5_5) → rank-1~3, 익일시가 진입 +5% 터치익절/5d.
검증: 8y 분기 walk-forward(학습은 전체 데이터, 발행만 서식지 한정), 연도별, 라벨셔플 플라시보,
서식지 활성 주간 커버리지. 대조: 같은 창의 모멘텀 레인(사망 확인용) + 무랭킹 과매도 풀."""
import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
import lightgbm as lgb
from swing_firsttouch_ranker_8y import FEATS, LIQ, COST

CACHE="/Users/dongdong/research_cache"
cols=list(dict.fromkeys(["code","date","market","liq","ft_5_5","exec_5d","ret_1d","ret_5d","rsi14","ret_20d","dist_hi20"]+FEATS))
px=pd.read_parquet(f"{CACHE}/px_long.parquet",columns=cols)
px["date"]=pd.to_datetime(px["date"]); px["exec_5d"]=px["exec_5d"].replace([np.inf,-np.inf],np.nan)
px["policy_ret"]=np.where(px["ft_5_5"]==1,5.0,px["exec_5d"])

for mkt in ("KOSDAQ","KOSPI"):
    d=px[(px["market"]==mkt)&(px["liq"]>=LIQ[mkt])].copy()
    # 서식지: 인과적 드로다운 상태 (당일 종가 기준 계산 → 당일 신호로 사용 가능)
    mret=d.groupby("date")["ret_1d"].mean().sort_index()
    lvl=(1+mret/100).cumprod()
    habitat=(((lvl/lvl.rolling(20).max()-1)*100<-5)|((lvl/lvl.shift(5)-1)*100<-3))
    d["habitat"]=d["date"].map(habitat).fillna(False)
    d["r5_rank"]=d.groupby("date")["ret_5d"].rank(pct=True)
    dd=d.dropna(subset=["ft_5_5"]+FEATS[:6]).sort_values("date")
    quarters=pd.period_range("2019Q1","2026Q2",freq="Q")
    rng=np.random.default_rng(0)
    pools=[]
    for q in quarters:
        t0,t1=q.start_time,q.end_time
        tr=dd[(dd["date"]<t0)&(dd["date"]>=t0-pd.DateOffset(years=2))]
        te=dd[(dd["date"]>=t0)&(dd["date"]<=t1)].copy()
        if len(tr)<20000 or te.empty: continue
        m=lgb.LGBMClassifier(n_estimators=400,learning_rate=0.05,num_leaves=63,min_child_samples=100,
                             subsample=0.8,colsample_bytree=0.7,reg_lambda=5,random_state=0,verbose=-1)
        m.fit(tr[FEATS].clip(-1e4,1e4),tr["ft_5_5"])
        te["p"]=m.predict_proba(te[FEATS].clip(-1e4,1e4))[:,1]
        mp=lgb.LGBMClassifier(n_estimators=400,learning_rate=0.05,num_leaves=63,min_child_samples=100,
                              subsample=0.8,colsample_bytree=0.7,reg_lambda=5,random_state=1,verbose=-1)
        mp.fit(tr[FEATS].clip(-1e4,1e4),rng.permutation(tr["ft_5_5"].values))
        te["p_plc"]=mp.predict_proba(te[FEATS].clip(-1e4,1e4))[:,1]
        pools.append(te)
    A=pd.concat(pools)
    H=A[A["habitat"]].copy()                      # 서식지 창만
    OV=H[H["r5_rank"]<=0.2]                       # 과매도 풀 (하위 20%)
    MO=H[(H["ret_20d"].groupby(H["date"]).rank(pct=True)>=0.9)&(H["dist_hi20"]>=-4)] if len(H) else H
    hab_days=H["date"].nunique(); hab_weeks=H["date"].dt.to_period("W").nunique()
    print(f"\n== {mkt} 서식지: {hab_days}일 ({hab_days/A['date'].nunique()*100:.0f}% of days), {hab_weeks}주")
    def ev(sel,label,score=None,k=1):
        if score: sel=sel.sort_values(score,ascending=False).groupby("date",group_keys=False).head(k)
        s=sel.dropna(subset=["policy_ret"])
        if len(s)<50: print(f"  {label:36s} n<50"); return
        net=s["policy_ret"]-COST
        yr=s.groupby(s["date"].dt.year).apply(lambda g:(g["policy_ret"]-COST).mean())
        bs=[np.random.default_rng(x).choice(net.values,len(net),True).mean() for x in range(300)]
        wk=s.groupby(s["date"].dt.to_period("W"))["date"].nunique().mean()
        print(f"  {label:36s} n={len(s):5d} win={(net>0).mean()*100:5.1f}% EV={net.mean():5.2f} CI=({np.percentile(bs,2.5):.2f},{np.percentile(bs,97.5):.2f}) 활성주픽 {wk:.1f} yr+={int((yr>0).sum())}/{len(yr)}")
    ev(OV, "과매도풀 전체 (무랭킹 기준선)")
    ev(OV, "과매도+ML rank-1", "p", 1)
    ev(OV, "과매도+ML rank-3", "p", 3)
    ev(OV, "과매도+플라시보 rank-1", "p_plc", 1)
    ev(MO, "모멘텀 rank-1 (사망 확인)", "p", 1)
