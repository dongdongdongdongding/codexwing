"""B 엔진 (signal_class=B) — 분봉 점화 + first-touch 배리어 고승률 엔진.

A(스윙/장중 3~5일 모델)와 완전히 다른 신호계열. 가격 차트의 '움직임/모양'만 본다.

핵심 로직 (검증 완료, 누수차단·purge·종목분산·시기분산 통과 — B_ENGINE.md):
  1. 탐지: 종목이 장중 전일종가 +8~10% 첫 돌파 (stop-buy 체결 = fillable)
  2. 점수: 점화를 ML 스코어 (분봉모양 + '전일' 일봉맥락 — 점화 전 아는 정보만, 누수 0)
  3. 선별: 매일 확률 top2
  4. 청산: +5% 익절 / -5% 손절, first-touch, ≤3거래일

검증 (OOS 90일, purge 5일갭, 2026-02~06):
  top2/일 승률 74% · EV +2.21%/거래 · 종목분산(76종목) · 전반77/후반72%

⚠️ 한계: 데이터 전부 2026년(분봉캐시 1년). 하락장 미검증 → forward-shadow 필수.

CLI:
  python -m b_engine.engine build    # 점화패널 빌드 → data/panel.parquet
  python -m b_engine.engine train    # 패널로 모델학습 + OOS검증 → data/model.pkl
  python -m b_engine.engine validate # 저장된 패널 OOS 재검증 리포트
"""
from __future__ import annotations
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

# 데이터 경로 (env override 가능)
RESEARCH = os.environ.get("B_RESEARCH_CACHE", os.path.expanduser("~/research_cache"))
PX_LONG = os.environ.get("B_PX_LONG", os.path.join(RESEARCH, "px_long.parquet"))
INTRADAY_DIR = os.environ.get("B_INTRADAY_DIR", os.path.join(RESEARCH, "intraday"))

PANEL_PATH = os.path.join(DATA, "panel.parquet")
MODEL_PATH = os.path.join(DATA, "model.pkl")
META_PATH = os.path.join(DATA, "model_meta.json")

# ── 엔진 상수 (검증값과 동일) ──────────────────────────────
IGNITION_THRESHOLDS = [8, 10]      # 전일比 % 돌파 레벨
TP_PCT = 5.0                        # 익절 +5%
SL_PCT = 5.0                        # 손절 -5%
HOLD_DAYS = 3                       # 배리어 관찰 최대 거래일
SESSION_BARS = 390                  # 정규장 분봉수(09:00~15:30) — tod 고정분모(live 일관성)
MIN_DAY_BARS = 60                   # 너무 짧은 날 제외
COST_PCT = 0.3                      # 왕복 비용 가정
TOP_K = 2                           # 매일 선별 픽 수

# 일봉 맥락피처 (점화 '전일' 값으로 lag → 누수 0)
DAILY_CTX = [
    "dist_hi20", "dist_lo20", "atr_pct", "bb_pctb", "idx_mom20",
    "idx_vol20", "ret_5d", "ret_20d", "turn_z", "vol_ratio", "ma20_slope",
]
# 분봉 점화시점 피처 (점화 순간에 알 수 있는 값만)
MINUTE_FEATS = ["thr", "tod", "volx", "accel", "gap", "from_open"]
FEATURES = MINUTE_FEATS + [f"L_{k}" for k in DAILY_CTX]

LGB_PARAMS = dict(
    n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=80,
    subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0,
)


# ── 공용: 단일 종목-일 점화 탐지 + 피처 (학습/라이브 공유) ──────────
def detect_ignition(day_bars: pd.DataFrame, prev_close: float, daily_ctx: dict):
    """하루치 분봉(09:00~)에서 첫 점화(전일比 +THR% 첫 돌파)를 찾아 피처 dict 리스트 반환.

    day_bars: index=datetime, cols High/Low/Close/(Open)/Volume — 시간오름차순.
    prev_close: 전일 종가. daily_ctx: 전일 일봉피처 dict {k: value}.
    반환: 각 THR별 점화 1건씩 (없으면 빈 리스트). 'ignition_bar'는 돌파 봉 위치(int).
    """
    out = []
    if prev_close is None or not (prev_close > 0):
        return out
    bars = day_bars.sort_index()
    if len(bars) < MIN_DAY_BARS:
        return out
    H = bars["High"].to_numpy(dtype=float)
    C = bars["Close"].to_numpy(dtype=float)
    V = bars["Volume"].to_numpy(dtype=float)
    open_px = float(bars["Open"].to_numpy(dtype=float)[0]) if "Open" in bars else float(C[0])
    for thr in IGNITION_THRESHOLDS:
        level = prev_close * (1 + thr / 100.0)
        loc = np.where(H >= level)[0]
        if len(loc) == 0:
            continue
        i = int(loc[0])
        rv = V[: i + 1].sum()
        av = V[: i + 1].mean() * 10 + 1e-9
        # 현실 체결가: 갭상승으로 시가가 이미 레벨 위면 stop-buy는 레벨에 못 산다 → 시가 체결
        gap_open = open_px >= level
        entry = max(open_px, float(level))
        feat = {
            "thr": float(thr),
            "tod": i / SESSION_BARS,             # 시간대(고정분모=live 일관)
            "volx": rv / av,                      # 거래량 급증도
            "accel": thr / max(1, i),             # 돌파까지 속도
            "gap": (open_px / prev_close - 1) * 100,
            "from_open": (entry / open_px - 1) * 100,
            "entry": entry,                       # 현실 체결가 = max(시가, 레벨)
            "gap_open": int(gap_open),            # 갭상승 점화 플래그(현실성 진단)
            "ignition_bar": i,
            "ignition_time": bars.index[i],
        }
        for k in DAILY_CTX:
            feat[f"L_{k}"] = daily_ctx.get(k, np.nan)
        out.append(feat)
    return out


def barrier_outcome(fwd_high, fwd_low, fwd_close, entry, tp=TP_PCT, sl=SL_PCT):
    """점화 이후 분봉경로의 first-touch 결과(%). 동시봉=보수적 손절. 미터치=마지막종가."""
    up = entry * (1 + tp / 100.0)
    dn = entry * (1 - sl / 100.0)
    for k in range(len(fwd_high)):
        hit_up = fwd_high[k] >= up
        hit_dn = fwd_low[k] <= dn
        if hit_up and hit_dn:
            return -sl
        if hit_up:
            return tp
        if hit_dn:
            return -sl
    if len(fwd_close):
        return (fwd_close[-1] / entry - 1) * 100
    return 0.0


# ── 패널 빌드 (학습용) ─────────────────────────────────────
def _load_universe():
    cols = ["code", "date", "close", "liq"] + DAILY_CTX
    px = pd.read_parquet(PX_LONG, columns=cols)
    px["code"] = px["code"].astype(str)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["code", "date"])
    g = px.groupby("code")
    px["pc"] = g["close"].shift(1)
    for k in DAILY_CTX:
        px["L_" + k] = g[k].shift(1)        # 누수차단: 전일값
    liq = (
        px[px["date"] >= px["date"].max() - pd.Timedelta(days=90)]
        .groupby("code")["liq"].median()
    )
    min_liq = float(os.environ.get("B_MIN_LIQ", 100e8))
    universe_n = int(os.environ.get("B_UNIVERSE_N", 150))
    codes = liq[liq >= min_liq].index.astype(str).tolist()[:universe_n]
    return px, set(codes)


def build_panel(verbose=True):
    px, codes = _load_universe()
    PX = px[px["code"].isin(codes)].set_index(["code", "date"])
    rows = []
    for j, code in enumerate(codes):
        fp = os.path.join(INTRADAY_DIR, f"{code}.parquet")
        if not os.path.exists(fp):
            continue
        try:
            df = pd.read_parquet(fp)
            df.index = pd.to_datetime(df.index)
        except Exception:
            continue
        df = df.sort_index()
        df = df.assign(_d=df.index.normalize())
        days = np.array(sorted(df["_d"].unique()))
        H = df["High"].to_numpy(float); L = df["Low"].to_numpy(float)
        C = df["Close"].to_numpy(float); V = df["Volume"].to_numpy(float)
        D = df["_d"].to_numpy()
        for di, day in enumerate(days):
            try:
                r = PX.loc[(code, pd.Timestamp(day))]
            except KeyError:
                continue
            pc = r["pc"]
            if pd.isna(pc) or pc <= 0:
                continue
            dmask = np.where(D == day)[0]
            if len(dmask) < MIN_DAY_BARS:
                continue
            day_bars = df.iloc[dmask]
            ctx = {k: r["L_" + k] for k in DAILY_CTX}
            igs = detect_ignition(day_bars, float(pc), ctx)
            if not igs:
                continue
            end_day = days[min(di + HOLD_DAYS - 1, len(days) - 1)]
            for ig in igs:
                gi = dmask[0] + ig["ignition_bar"]
                fm = np.where((np.arange(len(D)) > gi) & (D <= end_day))[0]
                if len(fm) < 5:
                    continue
                ret = barrier_outcome(H[fm], L[fm], C[fm], ig["entry"])
                row = {"code": code, "dt": pd.Timestamp(day), "ret": ret, "win": int(ret > 0)}
                for f in FEATURES:
                    row[f] = ig[f]
                rows.append(row)
        if verbose and (j + 1) % 30 == 0:
            print(f"  ...{j+1}/{len(codes)} 종목, 누적 점화 {len(rows):,}", flush=True)
    panel = pd.DataFrame(rows)
    for c in FEATURES:
        panel[c] = pd.to_numeric(panel[c], errors="coerce").replace([np.inf, -np.inf], np.nan)
    panel = panel.sort_values("dt").reset_index(drop=True)
    panel.to_parquet(PANEL_PATH)
    if verbose:
        print(f"패널 저장 {PANEL_PATH} · {len(panel):,}점화 · 승률 {panel['win'].mean()*100:.0f}%", flush=True)
    return panel


# ── 검증 (purge OOS) ──────────────────────────────────────
def validate(panel=None, purge_days=5, train_frac=0.6):
    import lightgbm as lgb
    if panel is None:
        panel = pd.read_parquet(PANEL_PATH)
    udays = np.sort(panel["dt"].unique())
    cut = int(len(udays) * train_frac)
    tr_end = udays[cut - 1]
    te_start = udays[min(cut + purge_days, len(udays) - 1)]
    tr = panel[panel["dt"] <= tr_end]
    te = panel[panel["dt"] >= te_start].copy()
    m = lgb.LGBMClassifier(**LGB_PARAMS, verbose=-1)
    m.fit(tr[FEATURES].fillna(0), tr["win"])
    te["p"] = m.predict_proba(te[FEATURES].fillna(0))[:, 1]
    nd = te["dt"].nunique()
    tk = te.sort_values("p", ascending=False).groupby("dt").head(TOP_K)
    res = {
        "oos_days": int(nd),
        "base_win": round(float(panel["win"].mean()) * 100, 1),
        f"top{TOP_K}_win": round(float((tk["ret"] > 0).mean()) * 100, 1),
        f"top{TOP_K}_ev": round(float(tk["ret"].mean() - COST_PCT), 2),
        f"top{TOP_K}_n": int(len(tk)),
        "unique_codes": int(tk["code"].nunique()),
    }
    monthly = {}
    for mo, s in tk.groupby(tk["dt"].dt.to_period("M")):
        monthly[str(mo)] = {"n": int(len(s)), "win": round(float((s["ret"] > 0).mean()) * 100), "ev": round(float(s["ret"].mean() - COST_PCT), 2)}
    res["monthly"] = monthly
    print(json.dumps(res, ensure_ascii=False, indent=2), flush=True)
    return res


# ── 학습 + 저장 (배포 모델 = 전체데이터 학습) ──────────────
def train():
    import lightgbm as lgb
    import joblib
    if not os.path.exists(PANEL_PATH):
        print("패널 없음 → build 먼저", flush=True)
        build_panel()
    panel = pd.read_parquet(PANEL_PATH)
    # 검증 리포트(참고용 OOS) 먼저
    print("=== OOS 검증 (purge 5일) ===", flush=True)
    val = validate(panel)
    # 배포 모델: 전체 데이터로 재학습
    m = lgb.LGBMClassifier(**LGB_PARAMS, verbose=-1)
    m.fit(panel[FEATURES].fillna(0), panel["win"])
    joblib.dump(m, MODEL_PATH)
    meta = {
        "features": FEATURES, "tp": TP_PCT, "sl": SL_PCT, "hold_days": HOLD_DAYS,
        "ignition_thresholds": IGNITION_THRESHOLDS, "top_k": TOP_K, "cost": COST_PCT,
        "trained_rows": int(len(panel)),
        "train_date_min": str(panel["dt"].min().date()),
        "train_date_max": str(panel["dt"].max().date()),
        "oos_validation": val,
        "signal_class": "B",
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"\n모델 저장 {MODEL_PATH} · meta {META_PATH}", flush=True)
    return m, meta


def load_model():
    import joblib
    m = joblib.load(MODEL_PATH)
    with open(META_PATH) as f:
        meta = json.load(f)
    return m, meta


def score_features(rows: pd.DataFrame, model=None):
    """피처 DataFrame → 확률. 라이브 스코어용."""
    if model is None:
        model, _ = load_model()
    X = rows[FEATURES].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
    return model.predict_proba(X)[:, 1]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"
    if cmd == "build":
        build_panel()
    elif cmd == "validate":
        validate()
    elif cmd == "train":
        train()
    else:
        print(f"unknown: {cmd} (build|train|validate)")
