"""B 엔진 v2 (배포) — 시장중립 적응형 앙상블. signal_class=B. A(스윙/장중)와 완전 별개.

검증된 엣지 (B_ENGINE.md 참조, 이 세션 2026-06):
  - 일봉 횡단면 시장중립 알파 + 적응형 walk-forward + 레짐피처.
  - 매일 전종목 랭킹 → top10 픽. 5일 보유.
  - OOS 2024/25/26 전부 양(플라시보 검증). top5% Sharpe 1.22~1.37.
  - 절대수익(베타포함): 상승장 연 58~84% / 시장중립 알파(로버스트): 연 34~65%.
  - 승률: 개별 ~50%, 포트 일별 60%대. (분류타깃·피처스택·집중과다는 과적합 → 안 씀)

⚠️ 낙관(비용0.3%·슬리피지/decay 미반영·OOS 1.8년) → forward-shadow로 라이브 확인 후 실자본.
⚠️ 누수금지: px_long의 ft_*/exec_*/cl_* (forward 라벨) 피처 사용 금지.
2026-07 P2 검증: credit(신용잔고) 피처 기각(동수 노이즈 플라시보 대조 CI 0 포함 — 피처 수
자체가 top-k α를 부풀리는 아티팩트 확인, 피처군 주장엔 노이즈 플라시보 필수), HOLD 3/5/10
프런티어에서 5 확정(net α/일 동률, 3d 라벨은 노이지, 10d는 2024 음수).

데이터: ~/research_cache/{px_long.parquet, flow.parquet, shares.parquet}.
CLI: python -m b_engine.model_engine train|pick
"""
from __future__ import annotations
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)
RESEARCH = os.environ.get("B_RESEARCH_CACHE", os.path.expanduser("~/research_cache"))
PX_LONG = os.path.join(RESEARCH, "px_long.parquet")
FLOW = os.path.join(RESEARCH, "flow.parquet")
SHARES = os.path.join(RESEARCH, "shares.parquet")
NAMES = os.path.join(RESEARCH, "names.parquet")
FLOW_FFILL_LIMIT = 20   # 수급 데이터 지연시 마지막값 유지 한도(거래일) — 픽을 최신가격에 맞춤
MODEL_PATH = os.path.join(DATA, "b_model.pkl")
META_PATH = os.path.join(DATA, "b_model_meta.json")

# ── 검증된 상수 ──────────────────────────────────────────
FEAT = ["ret_5d", "ret_10d", "ret_20d", "ret_60d", "rsi14", "rsi_slope", "bb_pctb", "bb_bw",
        "ma20_dist", "ma60_dist", "ma120_dist", "ma20_slope", "ma60_slope", "dist_hi20", "dist_hi60",
        "dist_lo20", "pos20", "vol_ratio", "vol_trend", "turn_z", "obv_slope", "cmf20", "atr_pct",
        "accel", "consec_up", "close_loc", "idx_mom20", "idx_vol20"]   # 누수컬럼(ft_/exec_/cl_) 제외
FL = ["smart5", "smart20", "frgn_acc5", "frgn_acc20", "orgn_acc5"]
ALLF = FEAT + FL
HOLD = 5            # 보유 거래일
TOP_N = 10         # 매일 픽 종목수
UNIVERSE_N = 500   # 유동 상위
TRAIN_MONTHS = 9   # 적응형 학습 윈도우(개월)
N_SEEDS = 3        # 앙상블
LGB = dict(n_estimators=300, learning_rate=0.03, num_leaves=31, min_child_samples=120,
           subsample=0.75, colsample_bytree=0.6, reg_lambda=5)


def load_panel(min_date="2023-12-01"):
    """px_long(일봉피처) + flow(정규화 수급) 병합 → 모델 패널. 수급은 당일 EOD(스코어시 T-1까지 known)."""
    px = pd.read_parquet(PX_LONG, columns=["code", "date", "close", "liq"] + FEAT)
    px["code"] = px["code"].astype(str); px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["code", "date"])
    sh = pd.read_parquet(SHARES); sh["code"] = sh["code"].astype(str)
    fl = pd.read_parquet(FLOW); fl["code"] = fl["code"].astype(str); fl["date"] = pd.to_datetime(fl["date"])
    fl = fl.merge(sh, on="code", how="left").sort_values(["code", "date"])
    gf = fl.groupby("code")
    for inv in ["frgn", "orgn"]:
        fl[inv + "_r"] = fl[inv + "_ntby"] / (fl["shares"] + 1) * 1e4
        fl[f"{inv}_acc5"] = gf[inv + "_r"].transform(lambda s: s.rolling(5).sum())
        fl[f"{inv}_acc20"] = gf[inv + "_r"].transform(lambda s: s.rolling(20).sum())
    fl["smart5"] = fl["frgn_acc5"] + fl["orgn_acc5"]; fl["smart20"] = fl["frgn_acc20"] + fl["orgn_acc20"]
    px = px.merge(fl[["code", "date"] + FL], on=["code", "date"], how="left").sort_values(["code", "date"])
    # 수급이 px_long보다 늦으면(파이프라인 지연) 마지막값 ffill → 픽이 최신 가격일에 나오게.
    for c in FL:
        px[c] = px.groupby("code")[c].ffill(limit=FLOW_FFILL_LIMIT)
    g = px.groupby("code")
    px["nxe"] = g["close"].shift(-(HOLD + 1)); px["f5"] = (px["nxe"] / g["close"].shift(-1) - 1) * 100
    liq = px[px["date"] >= px["date"].max() - pd.Timedelta(days=120)].groupby("code")["liq"].median()
    codes = set(liq.sort_values(ascending=False).head(UNIVERSE_N).index.astype(str))
    # 수급 notna 강제 대신 핵심 가격피처(ret_20d) 존재 + 수급 ffill 결과 존재로 완화 → 최신일 픽 가능.
    px = px[px["code"].isin(codes) & (px["date"] >= pd.Timestamp(min_date))
            & px["ret_20d"].notna() & px["smart5"].notna()].copy()
    px["a5"] = px["f5"] - px.groupby("date")["f5"].transform("mean")  # 시장중립 알파(타깃)
    for c in ALLF:
        px[c] = pd.to_numeric(px[c], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return px


def _fit_ensemble(train):
    import lightgbm as lgb
    models = []
    for sd in range(N_SEEDS):
        m = lgb.LGBMRegressor(**LGB, random_state=sd, verbose=-1)
        m.fit(train[ALLF].fillna(0), train["a5"])
        models.append(m)
    return models


def _predict(models, X):
    return np.mean([m.predict(X[ALLF].fillna(0)) for m in models], axis=0)


def train():
    """배포 모델: 최근 TRAIN_MONTHS 개월로 앙상블 학습 → 저장."""
    import joblib
    px = load_panel()
    px = px.dropna(subset=["a5"])           # 학습엔 타깃 필요
    last = px["date"].max()
    start = last - pd.DateOffset(months=TRAIN_MONTHS)
    train_df = px[(px["date"] > start) & (px["date"] <= last)]
    models = _fit_ensemble(train_df)
    joblib.dump(models, MODEL_PATH)
    # 확률 보정: pred_alpha → P(시장대비 초과, a5>0) 로지스틱. B픽에 '확률' 표시용.
    calib = {"a": 0.0, "b": 0.0}
    try:
        from sklearn.linear_model import LogisticRegression
        pred_tr = _predict(models, train_df)
        y = (train_df["a5"].values > 0).astype(int)
        lr = LogisticRegression().fit(pred_tr.reshape(-1, 1), y)
        calib = {"a": float(lr.coef_[0][0]), "b": float(lr.intercept_[0])}
    except Exception:
        pass
    meta = {"signal_class": "B", "engine": "market_neutral_adaptive_ensemble_v2",
            "features": ALLF, "hold_days": HOLD, "top_n": TOP_N, "universe_n": UNIVERSE_N,
            "train_months": TRAIN_MONTHS, "n_seeds": N_SEEDS, "prob_calib": calib,
            "trained_through": str(last.date()), "train_rows": int(len(train_df))}
    with open(META_PATH, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"B모델 학습 저장: {len(models)}앙상블 · 학습 {train_df['date'].min().date()}~{last.date()} · {len(train_df):,}행", flush=True)
    return models, meta


def pick(as_of=None):
    """최신(또는 지정)일 전종목 스코어 → top10 픽. 누수0(피처는 당일 close까지, 수급 당일 EOD)."""
    import joblib
    if not os.path.exists(MODEL_PATH):
        train()
    models = joblib.load(MODEL_PATH)
    px = load_panel()
    day = px["date"].max() if as_of is None else pd.Timestamp(as_of)
    s = px[px["date"] == day].copy()
    if not len(s):
        print(f"데이터 없음: {day.date()}", flush=True); return None
    s["pred_alpha"] = _predict(models, s)
    s = s.sort_values("pred_alpha", ascending=False)
    top = s.head(TOP_N)
    # 확률(보정): 시장대비 초과 가능성. meta의 로지스틱 계수 사용.
    calib = {"a": 0.0, "b": 0.0}
    try:
        with open(META_PATH) as f:
            calib = json.load(f).get("prob_calib", calib)
    except Exception:
        pass
    import math
    def _prob(pa):
        try:
            return round(1.0 / (1.0 + math.exp(-(calib["a"] * float(pa) + calib["b"]))) * 100, 1)
        except Exception:
            return None
    names = {}
    if os.path.exists(NAMES):
        try:
            nm = pd.read_parquet(NAMES); nm["code"] = nm["code"].astype(str)
            names = dict(zip(nm["code"], nm["name"]))
        except Exception:
            pass
    picks = []
    for rank, (_, r) in enumerate(top.iterrows(), start=1):
        picks.append({
            "code": r["code"], "name": names.get(r["code"], r["code"]), "signal_class": "B",
            "pred_alpha_5d": round(float(r["pred_alpha"]), 3),
            "prob_win": _prob(r["pred_alpha"]),   # 시장대비 초과 확률(보정)
            "close": round(float(r["close"]), 2),
            "ret_20d": round(float(r["ret_20d"]), 2) if pd.notna(r["ret_20d"]) else None,
            "smart5": round(float(r["smart5"]), 2) if pd.notna(r["smart5"]) else None,
            "rsi14": round(float(r["rsi14"]), 1) if pd.notna(r["rsi14"]) else None,
            "hold_days": HOLD,
            # b_model_zoo(2026-07-03, 월별 walk-forward 24폴드): top3 집중 α 2.18 CI(1.07,3.19)
            # vs top10 1.63 — 연도별 단조, 플라시보 사망. top1은 CI 넓고 2024 붕괴 → 3이 안전 집중.
            "rank": rank,
            "tier": "PRIMARY" if rank <= 3 else "CANDIDATE",
        })
    return {"scan_date": str(day.date()), "signal_class": "B", "hold_days": HOLD,
            "top_n": TOP_N, "universe": int(s["code"].nunique()), "picks": picks}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pick"
    if cmd == "train":
        train()
    elif cmd == "pick":
        out = pick()
        if out:
            print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)
