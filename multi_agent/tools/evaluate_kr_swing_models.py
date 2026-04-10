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


def build_segment() -> tuple[pd.DataFrame, list[str]]:
    df = engineer_features(load_scan_archive())
    seg = df[
        df["market_subtype"].isin(["KOSPI", "KOSDAQ"])
        & df["scan_mode"].eq("SWING")
        & df["return_3d_pct"].notna()
    ].copy()
    seg["target"] = (pd.to_numeric(seg["return_3d_pct"], errors="coerce") >= 5.0).astype(int)
    feat_cols = [col for col in FEATURE_COLS if col in seg.columns]
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


def fit_and_eval(name: str, model, X_train, X_val, y_train, y_val, returns_val, feat_cols):
    scaler = None
    if name in {"logistic"}:
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_val = scaler.transform(X_val)

    model.fit(X_train, y_train)
    if hasattr(model, "predict_proba"):
        prob = model.predict_proba(X_val)[:, 1]
    else:
        raw = model.decision_function(X_val)
        prob = 1 / (1 + np.exp(-raw))
    pred = (prob >= 0.5).astype(int)
    auc = float(roc_auc_score(y_val, prob))
    report = classification_report(y_val, pred, target_names=["negative", "positive"], output_dict=True)
    sweep, best = threshold_sweep(prob, returns_val, y_val.to_numpy())
    result = {
        "model": name,
        "auc": auc,
        "accuracy": float(report["accuracy"]),
        "positive_precision": float(report["positive"]["precision"]),
        "positive_recall": float(report["positive"]["recall"]),
        "threshold_sweep": sweep,
        "best_threshold_row": best,
    }
    payload = {
        "model": model,
        "scaler": scaler,
        "features": feat_cols,
        "trained_at": datetime.now().isoformat(),
        "auc": auc,
        "segment": "phase25_kr_swing_benchmark",
        "return_col": "return_3d_pct",
        "positive_threshold": 5.0,
        "recommended_probability_threshold": (best or {}).get("threshold", 0.5),
        "description": f"KR swing benchmark candidate ({name}) trained on realized 3D >= +5%.",
        "benchmark_model": name,
        "benchmark_avg_return": (best or {}).get("avg_return"),
        "benchmark_win_rate": (best or {}).get("win_rate"),
        "benchmark_hit_rate": (best or {}).get("hit_rate"),
    }
    return result, payload


def main():
    seg, feat_cols = build_segment()
    X = seg[feat_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = seg["target"].astype(int)
    returns = pd.to_numeric(seg["return_3d_pct"], errors="coerce")

    split_idx = int(len(seg) * 0.7)
    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
    returns_val = returns.iloc[split_idx:].to_numpy()

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
        result, payload = fit_and_eval(name, model, X_train, X_val, y_train, y_val, returns_val, feat_cols)
        results.append(result)
        payloads[name] = payload

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_save_map = {
        "xgboost": MODELS_DIR / "phase25_kr_swing_xgboost.pkl",
        "lightgbm": MODELS_DIR / "phase25_kr_swing_lightgbm.pkl",
        "histgb": MODELS_DIR / "phase25_kr_swing_histgb.pkl",
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
