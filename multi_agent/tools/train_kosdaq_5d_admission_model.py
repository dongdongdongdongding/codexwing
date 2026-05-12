#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "learning"
MODELS_DIR = PROJECT_ROOT / "models" / "kr_lane_champions"

TARGET_WIN_RATE_PCT = 70.0
TARGET_AVG_RETURN_PCT = 5.0

NUMERIC_FEATURES = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "decision_score",
    "whale_score",
    "volume_ratio",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "relative_rank_score",
    "relative_rank_pct",
    "loss_risk_score",
    "low_model_prob_score",
    "low_prob_high_score",
    "expected_edge_inversion_score",
    "entry_reference_price",
    "priority_rank",
]

CATEGORICAL_FEATURES = [
    "decision_bucket",
    "feature_origin",
    "trend",
    "tier",
    "position",
    "strategy_family",
    "selection_lane",
    "scanner_timeframe_profile",
    "kr_universe_role",
]

SELECT_COLUMNS = ",".join(
    [
        "id",
        "ticker",
        "market",
        "market_type",
        "scan_mode",
        "recommended_at",
        "created_at",
        "decision",
        "decision_bucket",
        "feature_origin",
        "feature_quality",
        "validation_excluded",
        "is_dummy_data",
        "alpha_score",
        "tech_score",
        "ml_prob",
        "prob_clean",
        "decision_score",
        "whale_score",
        "volume_ratio",
        "expected_edge_score",
        "expected_return_1d_pct",
        "expected_return_3d_pct",
        "relative_rank_score",
        "relative_rank_pct",
        "loss_risk_score",
        "low_model_prob_score",
        "low_prob_high_score",
        "expected_edge_inversion_score",
        "entry_reference_price",
        "priority_rank",
        "trend",
        "tier",
        "position",
        "strategy_family",
        "selection_lane",
        "scanner_timeframe_profile",
        "kr_universe_role",
        "return_5d_pct",
    ]
)


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == "object":
        return series.fillna("").astype(str).str.lower().isin({"true", "1", "yes"})
    return series.fillna(False).astype(bool)


def _load_kosdaq_rows() -> pd.DataFrame:
    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")
    rows: List[Dict[str, Any]] = []
    page = 0
    page_size = 1000
    while True:
        res = (
            db.client.table("market_scan_results")
            .select(SELECT_COLUMNS)
            .eq("market_type", "KR")
            .ilike("ticker", "%.KQ")
            .eq("scan_mode", "SWING")
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return pd.DataFrame(rows)


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    ticker = work.get("ticker", pd.Series(index=work.index, dtype=object)).fillna("").astype(str).str.upper()
    work = work[ticker.str.endswith(".KQ")].copy()
    for col in NUMERIC_FEATURES + ["return_5d_pct"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    for col in CATEGORICAL_FEATURES:
        if col not in work.columns:
            work[col] = "UNKNOWN"
        work[col] = work[col].fillna("UNKNOWN").astype(str)
    if "is_dummy_data" in work.columns:
        work = work[~_bool_series(work["is_dummy_data"])].copy()
    work = work[work["return_5d_pct"].notna()].copy()
    rec = work.get("recommended_at", pd.Series(index=work.index, dtype=object))
    created = work.get("created_at", pd.Series(index=work.index, dtype=object))
    rec = rec.where(rec.notna() & rec.astype(str).str.len().gt(0), created)
    work["trade_date"] = pd.to_datetime(rec, errors="coerce").dt.strftime("%Y-%m-%d")
    work = work[work["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    work["target_win"] = work["return_5d_pct"].gt(0).astype(int)
    work["target_hit5"] = work["return_5d_pct"].ge(5).astype(int)
    return work.sort_values(["trade_date", "ticker", "id"]).copy()


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def _classifier_candidates() -> Dict[str, Any]:
    return {
        "logistic": LogisticRegression(max_iter=3000, class_weight="balanced", random_state=42),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=500,
            max_depth=6,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "hist_gb": HistGradientBoostingClassifier(
            max_iter=200,
            max_depth=4,
            learning_rate=0.05,
            l2_regularization=0.2,
            random_state=42,
        ),
    }


def _regressor_candidates() -> Dict[str, Any]:
    return {
        "extra_trees_reg": ExtraTreesRegressor(
            n_estimators=500,
            max_depth=6,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1,
        ),
        "hist_gb_reg": HistGradientBoostingRegressor(
            max_iter=200,
            max_depth=4,
            learning_rate=0.05,
            l2_regularization=0.2,
            random_state=42,
        ),
    }


def _time_folds(df: pd.DataFrame, min_train_days: int = 4) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    days = sorted(df["trade_date"].dropna().astype(str).unique().tolist())
    if len(days) < min_train_days + 2:
        return []
    test_chunks = np.array_split(days[min_train_days:], max(1, min(5, len(days) - min_train_days)))
    folds: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
    for chunk in test_chunks:
        test_days = [str(day) for day in chunk.tolist()]
        if not test_days:
            continue
        train_days = [day for day in days if day < test_days[0]]
        if len(train_days) < min_train_days:
            continue
        folds.append((df[df["trade_date"].isin(train_days)].copy(), df[df["trade_date"].isin(test_days)].copy()))
    return folds


def _fit_pipeline(estimator: Any, train: pd.DataFrame, target_col: str) -> Pipeline:
    pipe = Pipeline(steps=[("preprocessor", _preprocessor()), ("model", estimator)])
    pipe.fit(train[NUMERIC_FEATURES + CATEGORICAL_FEATURES], train[target_col])
    return pipe


def _predict_proba(pipe: Pipeline, test: pd.DataFrame) -> np.ndarray:
    model = pipe.named_steps["model"]
    x = test[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    if hasattr(model, "predict_proba"):
        return pipe.predict_proba(x)[:, 1]
    raw = pipe.decision_function(x)
    return 1.0 / (1.0 + np.exp(-raw))


def _build_oof_scores(df: pd.DataFrame, clf_name: str, reg_name: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    folds = _time_folds(df)
    clf_est = _classifier_candidates()[clf_name]
    hit_est = _classifier_candidates()[clf_name]
    reg_est = _regressor_candidates()[reg_name]
    scored_rows: List[pd.DataFrame] = []
    fold_metrics: List[Dict[str, Any]] = []
    for idx, (train, test) in enumerate(folds, start=1):
        win_pipe = _fit_pipeline(clf_est, train, "target_win")
        hit_pipe = _fit_pipeline(hit_est, train, "target_hit5")
        ret_pipe = _fit_pipeline(reg_est, train, "return_5d_pct")
        scored = test.copy()
        scored["p_win"] = _predict_proba(win_pipe, test)
        scored["p_hit5"] = _predict_proba(hit_pipe, test)
        pred_ret = ret_pipe.predict(test[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
        scored["pred_return_5d"] = pred_ret
        ret_scale = np.tanh(np.asarray(pred_ret, dtype=float) / 10.0)
        scored["admission_score"] = (0.45 * scored["p_win"]) + (0.35 * scored["p_hit5"]) + (0.20 * ret_scale)
        scored_rows.append(scored)
        metric: Dict[str, Any] = {
            "fold": idx,
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "train_days": int(train["trade_date"].nunique()),
            "test_days": int(test["trade_date"].nunique()),
            "test_start": str(test["trade_date"].min()),
            "test_end": str(test["trade_date"].max()),
        }
        for target, score_col in [("target_win", "p_win"), ("target_hit5", "p_hit5")]:
            if len(set(test[target])) > 1:
                metric[f"auc_{target}"] = round(float(roc_auc_score(test[target], scored[score_col])), 6)
            else:
                metric[f"auc_{target}"] = None
        fold_metrics.append(metric)
    if not scored_rows:
        return df.iloc[0:0].copy(), {"folds": []}
    return pd.concat(scored_rows, ignore_index=True), {"folds": fold_metrics}


def _slice_summary(df: pd.DataFrame, name: str, mask: pd.Series) -> Dict[str, Any] | None:
    group = df[mask].copy()
    if group.empty:
        return None
    ret = group["return_5d_pct"]
    return {
        "slice": name,
        "n": int(len(group)),
        "win_5d_pct": round(float(ret.gt(0).mean() * 100.0), 3),
        "avg_5d_pct": round(float(ret.mean()), 4),
        "median_5d_pct": round(float(ret.median()), 4),
        "hit_5pct_pct": round(float(ret.ge(5).mean() * 100.0), 3),
        "min_5d_pct": round(float(ret.min()), 4),
        "max_5d_pct": round(float(ret.max()), 4),
    }


def _evaluate_slices(scored: pd.DataFrame, min_n: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if scored.empty:
        return rows
    for col in ["admission_score", "p_win", "p_hit5", "pred_return_5d"]:
        if col not in scored.columns:
            continue
        series = pd.to_numeric(scored[col], errors="coerce")
        for q in [0.70, 0.75, 0.80, 0.85, 0.90, 0.925, 0.95]:
            thr = float(series.quantile(q))
            row = _slice_summary(scored, f"{col}_q{int(q*1000):03d}", series.ge(thr))
            if row and row["n"] >= min_n:
                row["threshold"] = round(thr, 6)
                rows.append(row)
    if "decision_bucket" in scored.columns:
        row = _slice_summary(scored, "bucket_exception_leader", scored["decision_bucket"].eq("exception_leader"))
        if row and row["n"] >= min_n:
            rows.append(row)
    return sorted(rows, key=lambda row: (-row["win_5d_pct"], -row["avg_5d_pct"], -row["n"]))


def _train_final_bundle(df: pd.DataFrame, clf_name: str, reg_name: str, selected_slice: Dict[str, Any] | None) -> Dict[str, Any]:
    win_pipe = _fit_pipeline(_classifier_candidates()[clf_name], df, "target_win")
    hit_pipe = _fit_pipeline(_classifier_candidates()[clf_name], df, "target_hit5")
    ret_pipe = _fit_pipeline(_regressor_candidates()[reg_name], df, "return_5d_pct")
    return {
        "segment": "kosdaq_swing_5d_admission",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features_numeric": list(NUMERIC_FEATURES),
        "features_categorical": list(CATEGORICAL_FEATURES),
        "win_model": win_pipe,
        "hit5_model": hit_pipe,
        "return_model": ret_pipe,
        "classifier": clf_name,
        "regressor": reg_name,
        "selected_slice": selected_slice,
        "target": {
            "win_5d_pct": TARGET_WIN_RATE_PCT,
            "avg_5d_pct": TARGET_AVG_RETURN_PCT,
        },
    }


def build_report(min_n: int) -> Dict[str, Any]:
    df = _prepare(_load_kosdaq_rows())
    experiments: List[Dict[str, Any]] = []
    best_target_slice: Dict[str, Any] | None = None
    best_config: Dict[str, str] | None = None
    for clf_name in _classifier_candidates():
        for reg_name in _regressor_candidates():
            scored, metadata = _build_oof_scores(df, clf_name=clf_name, reg_name=reg_name)
            slices = _evaluate_slices(scored, min_n=min_n)
            target_pass = [
                row for row in slices
                if row["win_5d_pct"] >= TARGET_WIN_RATE_PCT and row["avg_5d_pct"] >= TARGET_AVG_RETURN_PCT
            ]
            experiment = {
                "classifier": clf_name,
                "regressor": reg_name,
                "oof_rows": int(len(scored)),
                "folds": metadata["folds"],
                "best_slices": slices[:12],
                "target_pass_slices": target_pass,
            }
            experiments.append(experiment)
            for row in target_pass:
                if (
                    best_target_slice is None
                    or row["n"] > best_target_slice["n"]
                    or (row["n"] == best_target_slice["n"] and row["avg_5d_pct"] > best_target_slice["avg_5d_pct"])
                ):
                    best_target_slice = row
                    best_config = {"classifier": clf_name, "regressor": reg_name}
    model_path = None
    if best_config and best_target_slice:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        bundle = _train_final_bundle(
            df,
            clf_name=best_config["classifier"],
            reg_name=best_config["regressor"],
            selected_slice=best_target_slice,
        )
        path = MODELS_DIR / "kosdaq_swing_5d_admission.pkl"
        joblib.dump(bundle, path)
        model_path = str(path)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(df)),
        "days": int(df["trade_date"].nunique()) if not df.empty else 0,
        "min_n": int(min_n),
        "target": {
            "win_5d_pct": TARGET_WIN_RATE_PCT,
            "avg_5d_pct": TARGET_AVG_RETURN_PCT,
        },
        "best_target_slice": best_target_slice,
        "best_config": best_config,
        "saved_model_path": model_path,
        "experiments": experiments,
    }


def _write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# KOSDAQ 5D Admission Model",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- rows: `{report['rows']}`",
        f"- days: `{report['days']}`",
        f"- target: `win_5d >= 70%, avg_5d >= +5%`",
        f"- saved_model_path: `{report.get('saved_model_path') or ''}`",
        "",
    ]
    best = report.get("best_target_slice")
    if best:
        lines.extend(
            [
                "## Best Target-Passing Slice",
                "",
                f"- config: `{report.get('best_config')}`",
                f"- slice: `{best['slice']}`",
                f"- n: `{best['n']}`",
                f"- win_5d_pct: `{best['win_5d_pct']}`",
                f"- avg_5d_pct: `{best['avg_5d_pct']}`",
                f"- hit_5pct_pct: `{best['hit_5pct_pct']}`",
                "",
            ]
        )
    else:
        lines.extend(["## Best Target-Passing Slice", "", "- none", ""])
    lines.extend(["## Experiments", ""])
    for exp in report.get("experiments", []):
        lines.append(f"### {exp['classifier']} + {exp['regressor']}")
        for row in exp.get("best_slices", [])[:5]:
            lines.append(
                f"- {row['slice']}: n={row['n']}, win5={row['win_5d_pct']}%, "
                f"avg5={row['avg_5d_pct']}%, hit5={row['hit_5pct_pct']}%"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-n", type=int, default=30)
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report(min_n=args.min_n)
    json_path = REPORT_DIR / "kosdaq_5d_admission_model.json"
    md_path = REPORT_DIR / "kosdaq_5d_admission_model.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _write_markdown(report, md_path)
    print(json.dumps({"json": str(json_path), "md": str(md_path), "best_target_slice": report.get("best_target_slice")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
