from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "learning"
MODELS_DIR = PROJECT_ROOT / "models"

import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrain_ml import FEATURE_COLS, engineer_features, load_scan_archive
from modules.phase25_governance import phase25_bundle_metadata
from modules.inverted_signal_features import compute_low_prob_high_score_features


INVERTED_SIGNAL_FEATURES = [
    "model_prob_available_count",
    "model_prob_mean",
    "low_model_prob_score",
    "low_prob_high_score",
    "expected_edge_inversion_score",
]


def add_inverted_signal_features(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    rows = [
        compute_low_prob_high_score_features(
            alpha_score=row.get("alpha_score"),
            tech_score=row.get("tech_score"),
            ml_prob=row.get("ml_prob"),
            prob_clean=row.get("prob_clean"),
            phase25_prob=row.get("phase25_prob"),
            expected_edge_score=row.get("expected_edge_score"),
        )
        for _, row in work.iterrows()
    ]
    feat_df = pd.DataFrame(rows, index=work.index)
    for col in INVERTED_SIGNAL_FEATURES:
        work[col] = pd.to_numeric(feat_df[col], errors="coerce").fillna(0.0)
    return work


def build_segment() -> tuple[pd.DataFrame, list[str]]:
    # 2026-05-08 (swing-main-4lm + 01i): return_3d_pct → return_5d_pct 변경.
    # KOSPI SWING 학습 OOS auc 0.485 (random 미만)는 3d target이 노이즈로
    # 학습 가능 신호를 못 만들어서. dedup 후 KOSPI SWING OBSERVE 5d win
    # 67.6% / 7d 75.6% — 5d로 학습하면 운영 분포와 target 일치.
    # KOSDAQ SWING은 horizon_policy에서 이미 5d.
    df = add_inverted_signal_features(engineer_features(load_scan_archive()))
    seg = df[
        df["market_subtype"].isin(["KOSPI", "KOSDAQ"])
        & df["scan_mode"].eq("SWING")
        & df["return_5d_pct"].notna()
    ].copy()
    seg["target"] = (pd.to_numeric(seg["return_5d_pct"], errors="coerce") >= 5.0).astype(int)
    feat_cols = [col for col in list(FEATURE_COLS) + INVERTED_SIGNAL_FEATURES if col in seg.columns]
    return seg.sort_values("created_at").copy(), feat_cols


def threshold_sweep(prob: np.ndarray, returns: np.ndarray, target: np.ndarray) -> tuple[list[dict], dict | None]:
    rows = []
    for th in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
        mask = prob >= th
        picks = int(mask.sum())
        if picks == 0:
            rows.append({"threshold": th, "picks": 0, "avg_return": None, "win_rate": None, "hit_rate": None})
            continue
        rows.append(
            {
                "threshold": th,
                "picks": picks,
                "avg_return": float(np.mean(returns[mask])),
                "win_rate": float(np.mean(returns[mask] > 0) * 100),
                "hit_rate": float(np.mean(target[mask] == 1) * 100),
            }
        )
    viable = [r for r in rows if r["picks"] >= 8 and r["avg_return"] is not None]
    best = max(viable, key=lambda r: (r["avg_return"], r["win_rate"], r["hit_rate"])) if viable else None
    return rows, best


def fit_and_eval(name: str, model, X_train, X_sel, X_rep, y_train, y_sel, y_rep,
                 returns_sel, returns_rep, feat_cols):
    """train 70% 학습 → sel 15% 에서 임계값 선택 → rep 15% 에서 보고.

    2026-09-03: 이전에는 30% 검증 슬라이스 **하나**에서 임계값을 argmax 로 고르고
    그 슬라이스의 승률·수익을 그대로 성적으로 실었다(규율 28: argmax 승자의 저주).
    고른 자리에서 재면 부풀려진다 — 그 수치가 이제 출하 게이트를 먹이므로
    **고르는 슬라이스와 재는 슬라이스를 나눈다.**
    """
    scaler = None
    if name in {"logistic"}:
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_sel = scaler.transform(X_sel)
        X_rep = scaler.transform(X_rep)

    model.fit(X_train, y_train)

    def _prob(X):
        if hasattr(model, "predict_proba"):
            return model.predict_proba(X)[:, 1]
        return 1 / (1 + np.exp(-model.decision_function(X)))

    prob_sel = _prob(X_sel)
    prob_rep = _prob(X_rep)
    pred = (prob_sel >= 0.5).astype(int)
    auc = float(roc_auc_score(y_sel, prob_sel))
    report = classification_report(y_sel, pred, target_names=["negative", "positive"], output_dict=True)
    sweep, best = threshold_sweep(prob_sel, returns_sel, y_sel.to_numpy())

    # 고르지 않은 슬라이스에서 재는 성적 — 이 값들이 출하 게이트로 간다.
    thr = float((best or {}).get("threshold", 0.5))
    rep_mask = prob_rep >= thr
    oos_n = int(rep_mask.sum())
    oos_auc = float(roc_auc_score(y_rep, prob_rep)) if y_rep.nunique() >= 2 else None
    oos_win = float(np.mean(returns_rep[rep_mask] > 0) * 100) if oos_n else None
    oos_ret = float(np.mean(returns_rep[rep_mask])) if oos_n else None

    # 2026-09-03: **그 구간 자체의 기준선**을 같이 적는다. 절대 임계값(win>=60%, ret>=0)만
    # 보면 「모델이 나쁘다」와 「그 구간 장이 나빴다」가 구분되지 않는다 — 실측에서
    # SWING rep 구간 기준선이 win 34.7% / 평균 −4.33% 였고, 모델 픽은 42.3% / −1.76% 로
    # **리프트 +7.6pp / +2.6pp** 인데 절대 기준으로는 둘 다 탈락한다.
    # 판정은 아래 게이트가 하고, 여기서는 **자를 같이 실어 보낸다**(규율 16).
    base_win = float(np.mean(returns_rep > 0) * 100) if len(returns_rep) else None
    base_ret = float(np.mean(returns_rep)) if len(returns_rep) else None
    result = {
        "model": name,
        "auc": auc,
        "accuracy": float(report["accuracy"]),
        "positive_precision": float(report["positive"]["precision"]),
        "positive_recall": float(report["positive"]["recall"]),
        "threshold_sweep": sweep,
        "best_threshold_row": best,
        "oos_auc": oos_auc,
        "oos_n": oos_n,
        "oos_win_rate_pct": oos_win,
        "oos_avg_return_pct": oos_ret,
        "oos_baseline_win_rate_pct": base_win,
        "oos_baseline_avg_return_pct": base_ret,
        "oos_n_slice": int(len(returns_rep)),
    }
    payload = {
        "model": model,
        "scaler": scaler,
        "features": feat_cols,
        "trained_at": datetime.now().isoformat(),
        "auc": auc,
        "segment": "phase25_kr_swing_benchmark",
        "return_col": "return_5d_pct",
        "positive_threshold": 5.0,
        "recommended_probability_threshold": (best or {}).get("threshold", 0.5),
        "description": f"KR swing benchmark candidate ({name}) trained on realized 5D >= +5%.",
        "benchmark_model": name,
        "benchmark_avg_return": (best or {}).get("avg_return"),
        "benchmark_win_rate": (best or {}).get("win_rate"),
        "benchmark_hit_rate": (best or {}).get("hit_rate"),
    }
    # 2026-09-03: 이 필드들이 없어서 modules/phase25_governance.py 가 한 번도 발동하지 못했다.
    # 값이 없어서가 아니라 **어휘가 달라서**였다 — 같은 수치를 benchmark_* 로만 적었고
    # 분모(picks)는 아예 버렸다. 이제 생성기 한 곳에서 만든다.
    payload.update(
        phase25_bundle_metadata(
            raw_auc=auc,
            oos_auc=oos_auc,
            oos_n=oos_n,
            oos_win_rate_pct=oos_win,
            oos_avg_return_pct=oos_ret,
        )
    )
    payload["oos_baseline_win_rate_pct"] = base_win
    payload["oos_baseline_avg_return_pct"] = base_ret
    payload["oos_n_slice"] = int(len(returns_rep))
    return result, payload


def main():
    seg, feat_cols = build_segment()
    X = seg[feat_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = seg["target"].astype(int)
    returns = pd.to_numeric(seg["return_5d_pct"], errors="coerce")

    # 시간순 70 / 15 / 15. sel 에서 임계값을 고르고 rep 에서 성적을 낸다(규율 28).
    n_rows = len(seg)
    i_train = int(n_rows * 0.70)
    i_sel = int(n_rows * 0.85)
    X_train, X_sel, X_rep = X.iloc[:i_train], X.iloc[i_train:i_sel], X.iloc[i_sel:]
    y_train, y_sel, y_rep = y.iloc[:i_train], y.iloc[i_train:i_sel], y.iloc[i_sel:]
    returns_sel = returns.iloc[i_train:i_sel].to_numpy()
    returns_rep = returns.iloc[i_sel:].to_numpy()

    candidates = {
        "rf": RandomForestClassifier(n_estimators=500, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1),
        "extratrees": ExtraTreesClassifier(n_estimators=500, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1),
        "histgb": HistGradientBoostingClassifier(max_depth=6, learning_rate=0.05, max_iter=300, random_state=42),
        "logistic": LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42),
    }

    try:
        import lightgbm as lgb

        candidates["lightgbm"] = lgb.LGBMClassifier(
            n_estimators=400,
            learning_rate=0.03,
            max_depth=6,
            num_leaves=31,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    except Exception:
        pass

    try:
        from xgboost import XGBClassifier

        candidates["xgboost"] = XGBClassifier(
            n_estimators=400,
            learning_rate=0.03,
            max_depth=5,
            random_state=42,
            n_jobs=-1,
            eval_metric="auc",
        )
    except Exception:
        pass

    results = []
    payloads = {}
    for name, model in candidates.items():
        result, payload = fit_and_eval(name, model, X_train, X_sel, X_rep,
                                       y_train, y_sel, y_rep, returns_sel, returns_rep, feat_cols)
        results.append(result)
        payloads[name] = payload

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    # 2026-05-08 (5d 학습): logistic이 dedup 후 best_avg 6.29%로 boost 계열보다
    # 약간 우수. logistic도 저장해 fallback 라우팅에서 사용 가능하게.
    model_save_map = {
        "xgboost": MODELS_DIR / "phase25_kr_swing_xgboost.pkl",
        "lightgbm": MODELS_DIR / "phase25_kr_swing_lightgbm.pkl",
        "histgb": MODELS_DIR / "phase25_kr_swing_histgb.pkl",
        "logistic": MODELS_DIR / "phase25_kr_swing_logistic.pkl",
    }
    saved_models = {}
    for name, path in model_save_map.items():
        payload = payloads.get(name)
        if not payload:
            continue
        joblib.dump(payload, path)
        saved_models[name] = str(path)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "kr_swing_model_benchmark.json"
    md_path = REPORT_DIR / "kr_swing_model_benchmark.md"
    payload = {
        "generated_at": datetime.now().isoformat(),
        "rows": int(len(seg)),
        "positives": int(y.sum()),
        "features": feat_cols,
        "results": results,
        "saved_models": saved_models,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# KR Swing Model Benchmark", ""]
    lines.append(f"- rows: `{len(seg)}`")
    lines.append(f"- positives(3D >= 5%): `{int(y.sum())}`")
    lines.append("")
    for row in sorted(results, key=lambda r: ((r.get('best_threshold_row') or {}).get('avg_return', -999), r["auc"]), reverse=True):
        lines.append(f"## {row['model']}")
        lines.append(f"- auc: `{row['auc']:.4f}`")
        lines.append(f"- accuracy: `{row['accuracy']:.4f}`")
        lines.append(f"- positive_precision: `{row['positive_precision']:.4f}`")
        lines.append(f"- positive_recall: `{row['positive_recall']:.4f}`")
        best = row.get("best_threshold_row")
        if best:
            lines.append(
                f"- best_threshold: `{best['threshold']:.2f}` | picks `{best['picks']}` | "
                f"avg_return `{best['avg_return']:+.2f}%` | win `{best['win_rate']:.1f}%` | hit `{best['hit_rate']:.1f}%`"
            )
        lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
