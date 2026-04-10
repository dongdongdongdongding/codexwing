#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score


FEATURES = ["decision_score", "alpha_score", "ml_prob", "trend_signal"]


def _trend_signal(value: Any) -> float:
    text = str(value or "").strip().upper()
    if text == "UP":
        return 1.0
    if text == "DOWN":
        return -1.0
    if text in {"SIDE", "NEUTRAL"}:
        return 0.0
    return 0.0


def _prepare_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if "validation_excluded" in df.columns:
        raw = df["validation_excluded"]
        if raw.dtype == "object":
            excluded = raw.astype(str).str.lower().isin({"true", "1", "yes"})
        else:
            excluded = raw.astype("boolean").fillna(False)
        df = df[~excluded].copy()

    for col in ["return_3d_pct", "decision_score", "alpha_score", "ml_prob"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["trend_signal"] = df.get("trend", "").map(_trend_signal)
    df["trade_date"] = pd.to_datetime(df.get("base_trade_date", df.get("recommended_at")), errors="coerce")
    df["feature_count"] = df[["decision_score", "alpha_score", "ml_prob"]].notna().sum(axis=1)
    return df


def _topn_metrics(frame: pd.DataFrame, score_col: str, topn: int) -> Dict[str, float]:
    top = frame.sort_values(score_col, ascending=False).head(topn)
    if top.empty:
        return {"avg_3d": 0.0, "positive_3d": 0.0}
    return {
        "avg_3d": round(float(top["return_3d_pct"].mean()), 6),
        "positive_3d": round(float((top["return_3d_pct"] > 0).mean()), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train KOSDAQ 3D continuation classifier from scan archive.")
    parser.add_argument("--input", default="runtime_state/reports/archive/scan_archive_learning_dataset_kosdaq.csv")
    parser.add_argument("--output", default="models/kosdaq_3d_continuation_ranker.pkl")
    parser.add_argument("--metrics-output", default="runtime_state/reports/validation/kosdaq_3d_continuation_model_metrics.json")
    parser.add_argument("--min-auc", type=float, default=0.72)
    args = parser.parse_args()

    df = _prepare_df(str(args.input))
    sample = (
        df[
            df["return_3d_pct"].notna()
            & df["feature_count"].ge(3)
            & df["trade_date"].notna()
        ]
        .copy()
        .sort_values("trade_date")
    )
    if len(sample) < 120:
        raise SystemExit(f"Not enough evidence-rich KOSDAQ continuation rows: {len(sample)}")

    cut = max(80, int(len(sample) * 0.7))
    train = sample.iloc[:cut].copy()
    test = sample.iloc[cut:].copy()

    imputer = SimpleImputer(strategy="median")
    X_train = imputer.fit_transform(train[FEATURES])
    X_test = imputer.transform(test[FEATURES])
    y_train = (train["return_3d_pct"] > 0).astype(int)
    y_test = (test["return_3d_pct"] > 0).astype(int)

    clf = HistGradientBoostingClassifier(
        max_depth=4,
        learning_rate=0.05,
        max_iter=200,
        random_state=42,
    )
    clf.fit(X_train, y_train)
    prob = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, prob) if len(set(y_test)) > 1 else None

    test_scored = test.copy()
    test_scored["prob_up_3d"] = prob
    test_scored["combo_score"] = test_scored["decision_score"].fillna(0.0) + ((test_scored["prob_up_3d"] - 0.5) * 120.0)

    metrics = {
        "samples": int(len(sample)),
        "train_samples": int(len(train)),
        "test_samples": int(len(test)),
        "positive_rate_train": round(float(y_train.mean()), 6),
        "positive_rate_test": round(float(y_test.mean()), 6),
        "auc": round(float(auc), 6) if auc is not None else None,
        "enabled": bool(auc is not None and auc >= float(args.min_auc)),
        "benchmarks": {
            "baseline_top20": _topn_metrics(test_scored, "decision_score", 20),
            "model_top20": _topn_metrics(test_scored, "prob_up_3d", 20),
            "combo_top20": _topn_metrics(test_scored, "combo_score", 20),
            "baseline_top60": _topn_metrics(test_scored, "decision_score", 60),
            "model_top60": _topn_metrics(test_scored, "prob_up_3d", 60),
            "combo_top60": _topn_metrics(test_scored, "combo_score", 60),
        },
        "train_start": str(train["trade_date"].min().date()),
        "train_end": str(train["trade_date"].max().date()),
        "test_start": str(test["trade_date"].min().date()),
        "test_end": str(test["trade_date"].max().date()),
    }

    bundle = {
        "features": FEATURES,
        "imputer": imputer,
        "classifier": clf,
        "metrics": metrics,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output)

    metrics_output = Path(args.metrics_output)
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "metrics_output": str(metrics_output), "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
