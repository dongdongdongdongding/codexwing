#!/usr/bin/env python3
"""tail_p 관측 모델 학습 (§16 tail 사전탐지, swing-main-clbb).

research/harness_2026_07/tail_veto_research.py 의 레시피 그대로 재사용:
  픽 = 8y 분기 walk-forward ft_5_5 랭커 rank-1..3 (양시장), tail 라벨 = policy_ret <= -10,
  피처 = 픽 시점에 알 수 있는 leak-free 15개 (과열/갭/유동성/확신/시장상태).
§16 판정: 강제 베토 REJECT(최악픽 -71.6 미탐·동결기준 미충족) → 승인 방향은
관측 필드 노출 + 경고 배지 + forward 상관 추적뿐. 이 스크립트는 그 관측용 모델을
학습·저장한다 (발행/사이징/베토/랭킹 불변).

검증(정직): 연도별 walk-forward OOS tail_p → AUC · 상위 20% 분리(§16 top-quintile) ·
라벨셔플 플라시보. 최종 모델은 전체 픽으로 재학습(서빙용) — OOS 통계는 meta JSON에 기록.

산출물 (멱등, 고정 시드 → 재실행시 동일):
  models/tail_p/tail_p_lgbm.pkl   — {"model", "features", "trained_at", ...} pickle 번들
  models/tail_p/tail_p_meta.json  — 학습·검증 통계 + forward_tracking 스펙

실행: python3 multi_agent/tools/build_tail_p_model.py
"""
import os, sys, json, pickle, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "research/harness_2026_07"))
import lightgbm as lgb  # noqa: E402
from swing_firsttouch_ranker_8y import FEATS, LIQ, COST  # noqa: E402

CACHE = os.path.expanduser("~/research_cache")
OUT_DIR = os.path.join(REPO, "models/tail_p")
TAIL_THR = -10.0        # tail 라벨: policy_ret <= -10 (§16)
WARN_QUANTILE = 0.80    # 경고 배지 경계 = OOS tail_p 상위 20% (§16 top-quintile)

# §16 베토 피처: 과열(dist_hi, consec_up, ret_20d, rsi) · 갭/변동성 구조 · 유동성 ·
# 확신(p) · 인과적 시장상태 — 전부 픽 시점 knowable (tail_veto_research.py VETO_F 동일)
VETO_F = ["dist_hi20", "dist_hi60", "consec_up", "ret_5d", "ret_20d", "rsi14", "atr_pct",
          "gap", "vol_ratio", "turn_z", "bb_bw", "liq_log", "p", "mkt_dd20", "mkt_ret5"]

TAIL_LGBM = dict(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=50,
                 subsample=0.8, colsample_bytree=0.8, reg_lambda=3, random_state=0,
                 scale_pos_weight=5, verbose=-1)


def gen_picks(mkt: str) -> pd.DataFrame:
    """tail_veto_research.gen_picks 동일 — 분기 walk-forward 랭커로 rank-1..3 픽 생성."""
    cols = list(dict.fromkeys(["code", "date", "market", "liq", "ft_5_5", "exec_5d", "ret_1d"] + FEATS))
    px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
    px = px[px["market"] == mkt].copy()
    px["date"] = pd.to_datetime(px["date"])
    px["exec_5d"] = px["exec_5d"].replace([np.inf, -np.inf], np.nan)
    px = px[px["liq"] >= LIQ[mkt]]
    px["policy_ret"] = np.where(px["ft_5_5"] == 1, 5.0, px["exec_5d"])
    d = px.dropna(subset=["ft_5_5"] + FEATS[:6]).copy()
    # 인과적 시장상태 (같은 유동성 필터 유니버스의 등가중 일수익 누적)
    mret = d.groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + mret / 100).cumprod()
    st = pd.DataFrame({"mkt_dd20": (lvl / lvl.rolling(20).max() - 1) * 100,
                       "mkt_ret5": (lvl / lvl.shift(5) - 1) * 100})
    picks = []
    for q in pd.period_range("2019Q1", "2026Q2", freq="Q"):
        t0, t1 = q.start_time, q.end_time
        tr = d[(d["date"] < t0) & (d["date"] >= t0 - pd.DateOffset(years=2))]
        te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
        m.fit(tr[FEATS].clip(-1e4, 1e4), tr["ft_5_5"])
        te["p"] = m.predict_proba(te[FEATS].clip(-1e4, 1e4))[:, 1]
        pk = te.sort_values("p", ascending=False).groupby("date", group_keys=False).head(3)
        picks.append(pk)
    P = pd.concat(picks, ignore_index=True)
    P = P.join(st, on="date")
    P["liq_log"] = np.log10(P["liq"].clip(1))
    P["market"] = mkt
    return P


def cvar10(x: np.ndarray) -> float:
    q = np.percentile(x, 10)
    return float(x[x <= q].mean())


def main():
    from sklearn.metrics import roc_auc_score
    P = pd.concat([gen_picks(m) for m in ("KOSDAQ", "KOSPI")], ignore_index=True)
    P = P.dropna(subset=["policy_ret"] + VETO_F).sort_values("date").reset_index(drop=True)
    P["tail"] = (P["policy_ret"] <= TAIL_THR).astype(int)
    print(f"picks={len(P)} tail_rate={P['tail'].mean()*100:.2f}% ({P['tail'].sum()} events)", flush=True)

    # 연도별 walk-forward OOS (tail_veto_research.py 동일) — 검증 통계용
    years = sorted(P["date"].dt.year.unique())
    rng = np.random.default_rng(0)
    rows, auc_by_year = [], {}
    for yr in years:
        if yr < years[0] + 2:
            continue
        tr = P[P["date"].dt.year < yr]
        te = P[P["date"].dt.year == yr].copy()
        if tr["tail"].sum() < 50 or te.empty:
            continue
        m = lgb.LGBMClassifier(**TAIL_LGBM)
        m.fit(tr[VETO_F].fillna(0), tr["tail"])
        te["tail_p"] = m.predict_proba(te[VETO_F].fillna(0))[:, 1]
        mp = lgb.LGBMClassifier(**{**TAIL_LGBM, "random_state": 1})
        mp.fit(tr[VETO_F].fillna(0), rng.permutation(tr["tail"].values))
        te["tail_plc"] = mp.predict_proba(te[VETO_F].fillna(0))[:, 1]
        if te["tail"].nunique() > 1:
            auc_by_year[int(yr)] = round(float(roc_auc_score(te["tail"], te["tail_p"])), 4)
        rows.append(te)
    T = pd.concat(rows, ignore_index=True)
    print(f"OOS picks: {len(T)} ({T['date'].dt.year.min()}..{T['date'].dt.year.max()}), tails {T['tail'].sum()}", flush=True)

    auc = float(roc_auc_score(T["tail"], T["tail_p"]))
    auc_plc = float(roc_auc_score(T["tail"], T["tail_plc"]))
    q80 = float(T["tail_p"].quantile(WARN_QUANTILE))
    top = T[T["tail_p"] >= q80]
    rest = T[T["tail_p"] < q80]
    sep = {"oos_q80_tail_p": round(q80, 4),
           "tail_rate_top20pct": round(float(top["tail"].mean() * 100), 2),
           "tail_rate_bottom80pct": round(float(rest["tail"].mean() * 100), 2),
           "n_top20pct": int(len(top))}
    veto_curve = {}
    for veto in (0.0, 0.1, 0.2, 0.3):
        th = T["tail_p"].quantile(1 - veto) if veto > 0 else np.inf
        keep = T[T["tail_p"] < th]
        net = (keep["policy_ret"] - COST).values
        veto_curve[f"{veto:.0%}"] = {"n": int(len(keep)), "ev": round(float(net.mean()), 3),
                                     "tail_pct": round(float(keep["tail"].mean() * 100), 2),
                                     "cvar10": round(cvar10(net), 2), "worst": round(float(net.min()), 1)}
    print(f"OOS AUC={auc:.4f} (placebo {auc_plc:.4f}) | top20% tail율 {sep['tail_rate_top20pct']}% "
          f"vs bottom80% {sep['tail_rate_bottom80pct']}%", flush=True)

    # 최종 서빙 모델: 전체 픽 재학습 (관측 전용 — 발행 경로에 개입하지 않음)
    final = lgb.LGBMClassifier(**TAIL_LGBM)
    final.fit(P[VETO_F].fillna(0), P["tail"])
    fi = sorted(zip(VETO_F, final.feature_importances_), key=lambda x: -x[1])
    print("tail 서명(중요도):", [(f, int(v)) for f, v in fi[:6]], flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    trained_at = datetime.now(timezone.utc).isoformat()
    # 경고 배지 경계 = OOS 상위 20% 경계(q80). 하드코딩 대신 측정값을 번들에 실어
    # 서빙(score_tail_p.warn_threshold)이 재학습마다 자동으로 따라가게 한다.
    warn_thr = round(q80, 4)
    bundle = {"model": final, "features": VETO_F, "trained_at": trained_at,
              "tail_thr": TAIL_THR, "warn_threshold": warn_thr,
              "issue": "swing-main-clbb", "recipe": "research/harness_2026_07/tail_veto_research.py"}
    with open(os.path.join(OUT_DIR, "tail_p_lgbm.pkl"), "wb") as f:
        pickle.dump(bundle, f)
    meta = {
        "issue": "swing-main-clbb", "section": "§16 tail 사전탐지 (관측 전용 — 강제 베토 REJECT)",
        "trained_at": trained_at,
        "recipe": "research/harness_2026_07/tail_veto_research.py (동일 피처·하이퍼파라미터·라벨)",
        "features": VETO_F, "tail_label": f"policy_ret <= {TAIL_THR}",
        "lgbm_params": {k: v for k, v in TAIL_LGBM.items() if k != "verbose"},
        "n_train_picks": int(len(P)), "n_tail_events": int(P["tail"].sum()),
        "train_tail_rate_pct": round(float(P["tail"].mean() * 100), 2),
        "train_date_range": [str(P["date"].min().date()), str(P["date"].max().date())],
        "validation": {
            "scheme": "연도별 walk-forward OOS (연도 t 예측은 t 이전 데이터만 학습)",
            "n_oos": int(len(T)), "oos_years": [int(T["date"].dt.year.min()), int(T["date"].dt.year.max())],
            "auc_oos": round(auc, 4), "auc_placebo_label_shuffle": round(auc_plc, 4),
            "auc_by_year": auc_by_year, "separation_top_quintile": sep,
            "veto_curve_reference_only": veto_curve,
            "note": "veto_curve는 §16 재현 참고용 — 베토는 REJECT됨(최악픽 -71.6 미탐). 관측 전용.",
        },
        "serving": {
            "flag": "AG_TAIL_P_OBS=1 (기본 0=OFF, OFF시 payload 불변)",
            "fields": {"tail_p": "P(policy_ret<=-10), float 0-1",
                       "tail_warn": f"tail_p>={warn_thr} (§16 OOS top-quintile 경계, 번들에서 로드)"},
            "warn_threshold": warn_thr,
            "scorer": "multi_agent/tools/score_tail_p.py (web/backend/services.py _pick_row에서 플래그 게이트 하에 호출)",
        },
        "forward_tracking": {
            "goal": "tail_p vs 실현 policy_ret forward 상관 — 관측 누적 후에만 개입 논의 (§16 승인 방향)",
            "log": "runtime_state/reports/experimental/tail_p_obs.jsonl — 플래그 ON일 때 픽별 "
                   "{logged_at, scan_date, code, lane, tail_p} append (기존 원장 스키마 불변, 사이드카)",
            "join": "픽 원장(kr_swing_candidate_ledger.jsonl 등)의 (date, ticker) ↔ 사이드카 (scan_date, code)로 "
                    "조인 → 실현 policy_ret/exit_* 대비 tail_p 상관·상위 quintile 실현 tail율을 후행 계산",
            "eval": "충분 표본(n>=100) 후: spearman(tail_p, realized), tail_warn 그룹 vs 나머지 tail율/CVaR 비교. "
                    "개입(발행/사이징) 전환은 별도 승인 필요 — 이 피처는 관측 전용으로 동결",
        },
    }
    with open(os.path.join(OUT_DIR, "tail_p_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"saved: {OUT_DIR}/tail_p_lgbm.pkl + tail_p_meta.json", flush=True)


if __name__ == "__main__":
    main()
