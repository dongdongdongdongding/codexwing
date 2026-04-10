#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, roc_auc_score
from sklearn.model_selection import train_test_split


FEATURES = ["alpha_score", "ai_prediction", "target_pct", "stop_pct_abs", "rr"]


def prepare_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["market"].isin(["KOSPI", "KOSDAQ"])].copy()
    for c in ["alpha_score", "ai_prediction", "entry_price", "target_price", "stop_loss", "return_5d"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["target_pct"] = (df["target_price"] / df["entry_price"] - 1.0) * 100.0
    df["stop_pct_abs"] = ((df["entry_price"] - df["stop_loss"]) / df["entry_price"] * 100.0).abs()
    df["rr"] = df["target_pct"] / df["stop_pct_abs"].replace(0, pd.NA)
    return df


def train_bucket(sub: pd.DataFrame) -> Dict[str, Any] | None:
    sub = sub[FEATURES + ["return_5d"]].dropna().copy()
    if len(sub) < 80:
        return None

    X = sub[FEATURES]
    y_reg = sub["return_5d"]
    y_cls = (sub["return_5d"] > 0).astype(int)

    X_train, X_test, y_train_reg, y_test_reg = train_test_split(X, y_reg, test_size=0.3, shuffle=False)
    y_train_cls = (y_train_reg > 0).astype(int)
    y_test_cls = (y_test_reg > 0).astype(int)

    reg = RandomForestRegressor(n_estimators=300, max_depth=5, min_samples_leaf=10, random_state=42)
    reg.fit(X_train, y_train_reg)
    pred_reg = reg.predict(X_test)
    mae = mean_absolute_error(y_test_reg, pred_reg)

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=5,
        min_samples_leaf=10,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train_cls)
    prob = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test_cls, prob) if len(set(y_test_cls)) > 1 else None

    return {
        "classifier": clf,
        "regressor": reg,
        "metrics": {
            "samples": int(len(sub)),
            "mae": float(mae),
            "auc": float(auc) if auc is not None else None,
            "test_samples": int(len(X_test)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train KR regime ranker from enriched external signals CSV.")
    parser.add_argument("--enriched-csv", type=str, default="runtime_state/reports/external_signals/signals_rows_enriched.csv")
    parser.add_argument("--output", type=str, default="models/kr_regime_ranker.pkl")
    parser.add_argument("--metrics-output", type=str, default="runtime_state/reports/external_signals/kr_regime_ranker_metrics.json")
    parser.add_argument("--min-auc", type=float, default=0.60)
    args = parser.parse_args()

    df = prepare_df(args.enriched_csv)
    bundle: Dict[str, Any] = {"features": FEATURES, "models": {}, "metrics": {}, "min_auc": float(args.min_auc)}

    for (market, regime), sub in df.groupby(["market", "regime"], dropna=False):
        if pd.isna(market) or pd.isna(regime):
            continue
        trained = train_bucket(sub)
        key = f"{market}:{regime}"
        if not trained:
            bundle["metrics"][key] = {"samples": int(len(sub)), "auc": None, "mae": None, "enabled": False}
            continue
        auc = trained["metrics"]["auc"]
        enabled = auc is not None and auc >= float(args.min_auc)
        bundle["metrics"][key] = {**trained["metrics"], "enabled": bool(enabled)}
        if enabled:
            bundle["models"][key] = {
                "classifier": trained["classifier"],
                "regressor": trained["regressor"],
            }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output)

    metrics_output = Path(args.metrics_output)
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.write_text(json.dumps(bundle["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "metrics_output": str(metrics_output), "metrics": bundle["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
