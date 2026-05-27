#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/codex_swing_matplotlib")

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover
    LGBMClassifier = None

try:
    from catboost import CatBoostClassifier
except Exception:  # pragma: no cover
    CatBoostClassifier = None


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
DEFAULT_OUTPUT_DIR = ROOT / "runtime_state/reports/experimental"
REPORT_VERSION = "internal_retrain_sweep_v1"
ORDERED_OUTCOME_PATH_LABEL_VERSION = "scan_entry_forward_hybrid_30m_daily_stop_first_v2"

BASE_NUMERIC = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "phase25_prob",
    "phase25_shadow_prob",
    "phase25_recommended_threshold",
    "whale_score",
    "decision_score",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "loss_risk_score",
    "relative_rank_score",
    "relative_rank_pct",
    "day_return_pct",
    "conviction_score",
    "model_prob_available_count",
    "model_prob_mean",
    "low_model_prob_score",
    "low_prob_high_score",
    "expected_edge_inversion_score",
    "volume_ratio",
]

FLOW_NUMERIC = [
    "foreigner",
    "institution",
    "retail",
    "foreign_flow",
    "institution_flow",
    "retail_flow",
    "foreigner_1d",
    "institution_1d",
    "retail_1d",
    "foreigner_3d",
    "institution_3d",
    "retail_3d",
    "foreigner_10d",
    "institution_10d",
    "retail_10d",
    "whale_flow_1d",
    "whale_flow_3d",
    "whale_flow_10d",
]

REGIME_NUMERIC = [
    "regime_volatility_20d",
    "regime_breadth_pct",
    "regime_avg_chg",
    "kosdaq_chg",
]

BASE_CATEGORICAL = [
    "trend",
    "fund_status",
    "tier",
    "position",
    "market_gate",
    "scanner_timeframe_profile",
    "kr_universe_role",
    "selection_lane",
    "volume_confirmed",
    "price_band",
    "marcap_band",
    "learning_quality_tier",
    "feature_quality",
    "feature_origin",
]

THEME_CATEGORICAL = [
    "primary_theme",
    "theme_source",
    "theme_inference_status",
    "theme_routing_path",
    "theme_risk",
]

RETURN_COLS = [
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "max_high_return_5d_pct",
    "min_return_observed_pct",
    "mfe_5d_pct",
    "mae_5d_pct",
    "ordered_entry_price",
    "ordered_mfe_until_terminal_5d_pct",
    "ordered_mae_until_terminal_5d_pct",
    "ordered_mae_before_target_5d_pct",
    "outcome_path_bar_count",
]


@dataclass(frozen=True)
class LabelSpec:
    name: str
    description: str
    required_cols: Tuple[str, ...]


LABELS = [
    LabelSpec("win_1d_pos", "1D close return > 0", ("return_1d_pct",)),
    LabelSpec("win_3d_pos", "3D close return > 0", ("return_3d_pct",)),
    LabelSpec("win_5d_pos", "5D close return > 0", ("return_5d_pct",)),
    LabelSpec("clean_3d_3v3", "3D >= +3%, 1D >= -1%, no 5% stop proxy", ("return_1d_pct", "return_3d_pct", "min_return_observed_pct")),
    LabelSpec("clean_5d_5v5", "5D >= +5%, 1D >= -1%, no 5% stop proxy", ("return_1d_pct", "return_5d_pct", "min_return_observed_pct")),
    LabelSpec("target_5d_10v5", "5D high >= +10% before 5% stop proxy", ("max_high_return_5d_pct", "min_return_observed_pct")),
]

FEATURE_SETS = {
    "score_no_theme": (BASE_NUMERIC + REGIME_NUMERIC, BASE_CATEGORICAL),
    "score_flow_no_theme": (BASE_NUMERIC + REGIME_NUMERIC + FLOW_NUMERIC, BASE_CATEGORICAL),
    "score_theme": (BASE_NUMERIC + REGIME_NUMERIC + FLOW_NUMERIC, BASE_CATEGORICAL + THEME_CATEGORICAL),
    "wide_theme": (BASE_NUMERIC + REGIME_NUMERIC + FLOW_NUMERIC, BASE_CATEGORICAL + THEME_CATEGORICAL),
}

STAGE1_MODELS = ["logistic", "hist_gb", "extra_trees"]
REFINE_MODELS = ["random_forest", "xgboost", "lightgbm", "catboost"]
TOPNS = [1, 3, 5, 10]


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return str(value)


def _safe_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna("").astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def _round(value: Any, digits: int = 4) -> float | None:
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return round(result, digits)
    except Exception:
        return None


def _pct(value: Any) -> float | None:
    number = _round(value, 6)
    return round(number * 100.0, 3) if number is not None else None


def _load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    for col in sorted(set(BASE_NUMERIC + FLOW_NUMERIC + REGIME_NUMERIC + RETURN_COLS + ["priority_rank"])):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in [
        "is_dummy_data",
        "validation_excluded",
        "label_stop_loss_5pct",
        "explosive_leader_flag",
        "core_trend_flag",
        "target_before_stop_5d",
        "stop_before_target_5d",
    ]:
        if col in df.columns:
            df[f"{col}_bool"] = _safe_bool(df[col])

    ticker = df.get("ticker", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    scan_mode = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    market_col = df.get("market", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    mask = scan_mode.eq("SWING") & (ticker.str.endswith(".KS") | ticker.str.endswith(".KQ") | market_col.isin(["KOSPI", "KOSDAQ"]))
    if "is_dummy_data_bool" in df.columns:
        mask &= ~df["is_dummy_data_bool"]
    # Keep validation_excluded rows in this research sweep. Historical resolved
    # outcomes often carry this flag from older archive-quality rules; dropping
    # them here would leave mostly unresolved recent rows and make retraining
    # impossible. The flag remains available as a feature/diagnostic column.

    out = df.loc[mask].copy()
    out["market2"] = ""
    out.loc[ticker.loc[out.index].str.endswith(".KS"), "market2"] = "KOSPI"
    out.loc[ticker.loc[out.index].str.endswith(".KQ"), "market2"] = "KOSDAQ"
    out.loc[out["market2"].eq("") & market_col.loc[out.index].isin(["KOSPI", "KOSDAQ"]), "market2"] = market_col.loc[out.index]

    rec = out.get("base_trade_date", pd.Series(index=out.index, dtype=object))
    created = out.get("recommended_at", pd.Series(index=out.index, dtype=object))
    rec = rec.where(rec.notna() & rec.astype(str).str.strip().ne(""), created)
    out["trade_date"] = pd.to_datetime(rec, errors="coerce", utc=True, format="mixed").dt.strftime("%Y-%m-%d")
    out = out[out["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    # Archive rows can split scan-time features and realized outcomes across
    # sibling rows. Collapse by date/ticker with first non-null per column so a
    # training row can contain both the original feature snapshot and labels.
    if "recommended_at" not in out.columns:
        out["recommended_at"] = out["trade_date"]
    out = out.sort_values(["trade_date", "ticker", "priority_rank", "recommended_at"], na_position="last")
    out = out.groupby(["trade_date", "ticker"], as_index=False, sort=False).first()

    exact_path = pd.Series(False, index=out.index)
    if "outcome_path_label_version" in out.columns:
        exact_path = (
            out["outcome_path_label_version"]
            .fillna("")
            .astype(str)
            .eq(ORDERED_OUTCOME_PATH_LABEL_VERSION)
        )
    ordered_stop = pd.Series(False, index=out.index)
    if "stop_before_target_5d_bool" in out.columns:
        ordered_stop = out["stop_before_target_5d_bool"].fillna(False) & exact_path

    stop = ordered_stop.copy()
    proxy_stop = pd.Series(False, index=out.index)
    if "min_return_observed_pct" in out.columns:
        proxy_stop |= out["min_return_observed_pct"].le(-5.0).fillna(False)
    if "label_stop_loss_5pct_bool" in out.columns:
        proxy_stop |= out["label_stop_loss_5pct_bool"].fillna(False)
    stop |= proxy_stop & ~exact_path
    out["stop5_proxy"] = stop
    out["ordered_path_exact"] = exact_path
    out["bad_path"] = (
        stop
        | out.get("return_1d_pct", pd.Series(index=out.index)).lt(-3.0).fillna(False)
        | out.get("return_5d_pct", pd.Series(index=out.index)).lt(0.0).fillna(False)
    )
    out["exception_leader"] = (
        out.get("decision_bucket", pd.Series("", index=out.index)).fillna("").astype(str).str.lower().eq("exception_leader")
        | out.get("decision", pd.Series("", index=out.index)).fillna("").astype(str).str.upper().eq("EXCEPTION_LEADER")
    )
    return out


def _label(df: pd.DataFrame, name: str) -> Tuple[pd.Series, pd.Series]:
    stop = df.get("stop5_proxy", pd.Series(False, index=df.index)).fillna(False)
    if name == "win_1d_pos":
        valid = df["return_1d_pct"].notna()
        return df["return_1d_pct"].gt(0).fillna(False), valid
    if name == "win_3d_pos":
        valid = df["return_3d_pct"].notna()
        return df["return_3d_pct"].gt(0).fillna(False), valid
    if name == "win_5d_pos":
        valid = df["return_5d_pct"].notna()
        return df["return_5d_pct"].gt(0).fillna(False), valid
    if name == "clean_3d_3v3":
        valid = df["return_1d_pct"].notna() & df["return_3d_pct"].notna() & df["min_return_observed_pct"].notna()
        return (df["return_3d_pct"].ge(3.0) & df["return_1d_pct"].ge(-1.0) & ~stop).fillna(False), valid
    if name == "clean_5d_5v5":
        valid = df["return_1d_pct"].notna() & df["return_5d_pct"].notna() & df["min_return_observed_pct"].notna()
        return (df["return_5d_pct"].ge(5.0) & df["return_1d_pct"].ge(-1.0) & ~stop).fillna(False), valid
    if name == "target_5d_10v5":
        valid = df["max_high_return_5d_pct"].notna() & df["min_return_observed_pct"].notna()
        return (df["max_high_return_5d_pct"].ge(10.0) & ~stop).fillna(False), valid
    raise KeyError(name)


def _cohort_masks(df: pd.DataFrame) -> Dict[str, pd.Series]:
    rank = df.get("priority_rank", pd.Series(float("nan"), index=df.index))
    core = df.get("core_trend_flag_bool", pd.Series(False, index=df.index)).fillna(False)
    explosive = df.get("explosive_leader_flag_bool", pd.Series(False, index=df.index)).fillna(False)
    exception = df.get("exception_leader", pd.Series(False, index=df.index)).fillna(False)
    return {
        "all": pd.Series(True, index=df.index),
        "ranked_top20": rank.between(1, 20, inclusive="both").fillna(False),
        "top5": rank.between(1, 5, inclusive="both").fillna(False) & ~exception,
        "exception_leader": exception,
        "top5_exception": rank.between(1, 5, inclusive="both").fillna(False) | exception,
        "core_trend": core,
        "explosive_leader": explosive,
    }


def _split_days(df: pd.DataFrame, train_ratio: float) -> Tuple[pd.Series, pd.Series, str | None]:
    days = sorted(df["trade_date"].dropna().astype(str).unique().tolist())
    if len(days) < 4:
        false = pd.Series(False, index=df.index)
        return false, false, None
    cut_idx = max(1, min(len(days) - 1, int(len(days) * train_ratio)))
    cut_day = days[cut_idx]
    return df["trade_date"].astype(str).lt(cut_day), df["trade_date"].astype(str).ge(cut_day), cut_day


def _feature_columns(df: pd.DataFrame, feature_set: str) -> Tuple[List[str], List[str]]:
    numeric, categorical = FEATURE_SETS[feature_set]
    nums = [col for col in numeric if col in df.columns]
    cats = [col for col in categorical if col in df.columns]
    return nums, cats


def _make_preprocessor(numeric: Sequence[str], categorical: Sequence[str], *, scale_numeric: bool) -> ColumnTransformer:
    num_steps: List[Tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", StandardScaler()))
    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(num_steps), list(numeric)),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False, min_frequency=3)),
                    ]
                ),
                list(categorical),
            ),
        ],
        remainder="drop",
    )


def _model(name: str) -> Any | None:
    if name == "logistic":
        return LogisticRegression(max_iter=500, class_weight="balanced", solver="lbfgs")
    if name == "hist_gb":
        return HistGradientBoostingClassifier(max_iter=140, max_depth=3, learning_rate=0.06, l2_regularization=0.2, random_state=42)
    if name == "extra_trees":
        return ExtraTreesClassifier(n_estimators=220, max_depth=7, min_samples_leaf=5, class_weight="balanced", random_state=42, n_jobs=-1)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=260, max_depth=8, min_samples_leaf=4, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    if name == "xgboost" and XGBClassifier is not None:
        return XGBClassifier(
            n_estimators=180,
            max_depth=3,
            learning_rate=0.045,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
    if name == "lightgbm" and LGBMClassifier is not None:
        return LGBMClassifier(
            n_estimators=220,
            max_depth=5,
            learning_rate=0.04,
            num_leaves=24,
            subsample=0.85,
            colsample_bytree=0.85,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
            n_jobs=-1,
        )
    if name == "catboost" and CatBoostClassifier is not None:
        return CatBoostClassifier(iterations=180, depth=5, learning_rate=0.04, loss_function="Logloss", eval_metric="AUC", random_seed=42, verbose=False)
    return None


def _metrics(df: pd.DataFrame, idx: pd.Index, label: pd.Series) -> Dict[str, Any]:
    sub = df.loc[idx]
    if sub.empty:
        return {"n": 0}
    wins = label.loc[idx] if len(idx) else pd.Series(dtype=bool)
    out: Dict[str, Any] = {
        "n": int(len(sub)),
        "label_win_pct": _pct(wins.mean()) if len(wins) else None,
        "active_days": int(sub["trade_date"].nunique()) if "trade_date" in sub.columns else 0,
        "bad_path_pct": _pct(sub.get("bad_path", pd.Series(False, index=sub.index)).mean()),
        "stop5_pct": _pct(sub.get("stop5_proxy", pd.Series(False, index=sub.index)).mean()),
    }
    for horizon, col in [("1d", "return_1d_pct"), ("3d", "return_3d_pct"), ("5d", "return_5d_pct")]:
        ret = pd.to_numeric(sub.get(col, pd.Series(index=sub.index, dtype=float)), errors="coerce").dropna()
        out[f"win_{horizon}_pct"] = _pct(ret.gt(0).mean()) if len(ret) else None
        out[f"avg_{horizon}_pct"] = _round(ret.mean()) if len(ret) else None
        out[f"median_{horizon}_pct"] = _round(ret.median()) if len(ret) else None
        out[f"min_{horizon}_pct"] = _round(ret.min()) if len(ret) else None
        out[f"max_{horizon}_pct"] = _round(ret.max()) if len(ret) else None
    return out


def _daily_top_indices(df: pd.DataFrame, score: pd.Series, topn: int) -> pd.Index:
    scored = df.copy()
    scored["_score"] = score.reindex(df.index)
    chunks = []
    for _day, day_df in scored.groupby("trade_date", dropna=False):
        top = day_df.sort_values("_score", ascending=False, na_position="last").head(topn)
        if not top.empty:
            chunks.append(top.index)
    if not chunks:
        return pd.Index([])
    return chunks[0].append(chunks[1:]) if len(chunks) > 1 else chunks[0]


def _score_metrics(metrics: Dict[str, Any]) -> Tuple[int, int, float, float, float, float, float, int]:
    n = int(metrics.get("n") or 0)
    days = int(metrics.get("active_days") or 0)
    win5 = float(metrics.get("win_5d_pct") or 0.0)
    avg5 = float(metrics.get("avg_5d_pct") or -999.0)
    bad = float(metrics.get("bad_path_pct") if metrics.get("bad_path_pct") is not None else 100.0)
    stop = float(metrics.get("stop5_pct") if metrics.get("stop5_pct") is not None else 100.0)
    label_win = float(metrics.get("label_win_pct") or 0.0)
    sample_ok = 1 if n >= 10 and days >= 5 else 0
    safe_ok = 1 if bad <= 35.0 and stop <= 25.0 else 0
    return (sample_ok, safe_ok, win5, avg5, -bad, -stop, label_win, n)


def _score_result(result: Dict[str, Any]) -> Tuple[int, int, float, float, float, float, float, int, float]:
    test = result.get("test") or {}
    auc = float(result.get("auc") or 0.0)
    return (*_score_metrics(test), auc)


def _run_one(
    work: pd.DataFrame,
    *,
    market: str,
    cohort: str,
    label_name: str,
    feature_set: str,
    model_name: str,
    train_ratio: float,
    min_train: int,
    min_test: int,
    min_test_days: int,
) -> Dict[str, Any]:
    label, valid = _label(work, label_name)
    scoped = work.loc[valid].copy()
    y = label.loc[scoped.index].astype(int)
    train_mask, test_mask, cut_day = _split_days(scoped, train_ratio)
    train_idx = scoped.index[train_mask]
    test_idx = scoped.index[test_mask]
    base = {
        "market": market,
        "cohort": cohort,
        "label": label_name,
        "feature_set": feature_set,
        "model": model_name,
        "cut_day": cut_day,
        "rows": int(len(scoped)),
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "status": "skipped",
    }
    if len(train_idx) < min_train or len(test_idx) < min_test or scoped.loc[test_idx, "trade_date"].nunique() < min_test_days:
        return {**base, "skip_reason": "insufficient_split_rows"}
    if y.loc[train_idx].nunique() < 2 or y.loc[test_idx].nunique() < 2:
        return {**base, "skip_reason": "single_class_split"}

    numeric, categorical = _feature_columns(scoped, feature_set)
    if not numeric and not categorical:
        return {**base, "skip_reason": "no_features"}
    clf = _model(model_name)
    if clf is None:
        return {**base, "skip_reason": "model_unavailable"}
    scale = model_name == "logistic"
    pipe = Pipeline([("pre", _make_preprocessor(numeric, categorical, scale_numeric=scale)), ("model", clf)])

    x_train = scoped.loc[train_idx, numeric + categorical].copy()
    x_test = scoped.loc[test_idx, numeric + categorical].copy()
    for col in categorical:
        x_train[col] = x_train[col].fillna("UNKNOWN").astype(str)
        x_test[col] = x_test[col].fillna("UNKNOWN").astype(str)
    try:
        pipe.fit(x_train, y.loc[train_idx])
        train_prob = pd.Series(pipe.predict_proba(x_train)[:, 1], index=train_idx)
        test_prob = pd.Series(pipe.predict_proba(x_test)[:, 1], index=test_idx)
    except Exception as exc:
        return {**base, "skip_reason": f"{type(exc).__name__}: {exc}"}

    auc = None
    brier = None
    try:
        auc = roc_auc_score(y.loc[test_idx], test_prob)
        brier = brier_score_loss(y.loc[test_idx], test_prob)
    except Exception:
        pass

    top_results = []
    for topn in TOPNS:
        train_top = _daily_top_indices(scoped.loc[train_idx], train_prob, topn)
        test_top = _daily_top_indices(scoped.loc[test_idx], test_prob, topn)
        top_results.append(
            {
                "topn": topn,
                "train": _metrics(scoped, train_top, y),
                "test": _metrics(scoped, test_top, y),
            }
        )
    top_results.sort(key=lambda row: _score_metrics(row["test"]), reverse=True)
    best = top_results[0]
    return {
        **base,
        "status": "ok",
        "features": {"numeric": numeric, "categorical": categorical},
        "auc": _round(auc, 6),
        "brier": _round(brier, 6),
        "best_topn": best["topn"],
        "train": best["train"],
        "test": best["test"],
        "all_topn": top_results,
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def _render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Internal Retrain Candidate Sweep",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- report_version: `{report.get('report_version')}`",
        f"- input_rows: `{report.get('input_rows')}`",
        f"- prepared_rows: `{report.get('prepared_rows')}`",
        f"- completed_results: `{report.get('completed_results')}`",
        f"- skipped_results: `{report.get('skipped_results')}`",
        "",
        "## Top Holdout Candidates",
        "",
        "| Rank | Market | Cohort | Label | Feature Set | Model | TopN | Test N | Days | Label Win | 1D Win | 3D Win | 5D Win | Avg 5D | Min 5D | Max 5D | Bad Path | AUC |",
        "|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, row in enumerate(report.get("champions", [])[:60], start=1):
        test = row.get("test") or {}
        lines.append(
            "| "
            + " | ".join(
                str(v)
                for v in [
                    idx,
                    row.get("market"),
                    row.get("cohort"),
                    row.get("label"),
                    row.get("feature_set"),
                    row.get("model"),
                    row.get("best_topn"),
                    test.get("n"),
                    test.get("active_days"),
                    test.get("label_win_pct"),
                    test.get("win_1d_pct"),
                    test.get("win_3d_pct"),
                    test.get("win_5d_pct"),
                    test.get("avg_5d_pct"),
                    test.get("min_5d_pct"),
                    test.get("max_5d_pct"),
                    test.get("bad_path_pct"),
                    row.get("auc"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Baseline Reference", ""])
    for market, rows in (report.get("baselines") or {}).items():
        lines.append(f"### {market}")
        for name, payload in rows.items():
            h5 = payload.get("5d") or {}
            lines.append(
                f"- `{name}` n=`{h5.get('n')}` 5D win=`{h5.get('win_pct')}` avg=`{h5.get('avg_pct')}` "
                f"min=`{h5.get('min_pct')}` max=`{h5.get('max_pct')}` bad_path=`{payload.get('bad_path_pct')}`"
            )
    lines.extend(["", "## Notes"])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def _horizon_summary(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    values = pd.to_numeric(df.get(col, pd.Series(index=df.index, dtype=float)), errors="coerce").dropna()
    if values.empty:
        return {"n": 0}
    return {
        "n": int(len(values)),
        "win_pct": _pct(values.gt(0).mean()),
        "avg_pct": _round(values.mean()),
        "median_pct": _round(values.median()),
        "min_pct": _round(values.min()),
        "max_pct": _round(values.max()),
    }


def _baselines(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for market in ["KOSPI", "KOSDAQ"]:
        market_df = df.loc[df["market2"].eq(market)].copy()
        masks = _cohort_masks(market_df)
        out[market] = {}
        for name in ["top5", "exception_leader", "top5_exception"]:
            sub = market_df.loc[masks[name]].copy()
            out[market][name] = {
                "rows": int(len(sub)),
                "1d": _horizon_summary(sub, "return_1d_pct"),
                "3d": _horizon_summary(sub, "return_3d_pct"),
                "5d": _horizon_summary(sub, "return_5d_pct"),
                "bad_path_pct": _pct(sub.get("bad_path", pd.Series(False, index=sub.index)).mean()) if len(sub) else None,
            }
    return out


def build_sweep(
    df: pd.DataFrame,
    *,
    train_ratio: float,
    min_train: int,
    min_test: int,
    min_test_days: int,
    refine_top: int,
    checkpoint_path: Path,
    summary_path: Path,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    skipped = 0
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text("", encoding="utf-8")

    def append_result(row: Dict[str, Any]) -> None:
        nonlocal skipped
        if row.get("status") == "ok":
            results.append(row)
        else:
            skipped += 1
        with checkpoint_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")

    base_configs: List[Tuple[str, str, str, str]] = []
    for market in ["KOSPI", "KOSDAQ"]:
        market_df = df.loc[df["market2"].eq(market)].copy()
        masks = _cohort_masks(market_df)
        for cohort, mask in masks.items():
            cohort_df = market_df.loc[mask].copy()
            if len(cohort_df) < min_train + min_test:
                continue
            for label in LABELS:
                for feature_set in FEATURE_SETS:
                    base_configs.append((market, cohort, label.name, feature_set))
                    for model_name in STAGE1_MODELS:
                        append_result(
                            _run_one(
                                cohort_df,
                                market=market,
                                cohort=cohort,
                                label_name=label.name,
                                feature_set=feature_set,
                                model_name=model_name,
                                train_ratio=train_ratio,
                                min_train=min_train,
                                min_test=min_test,
                                min_test_days=min_test_days,
                            )
                        )

    stage1_ok = [row for row in results if row.get("status") == "ok"]
    stage1_ok.sort(key=_score_result, reverse=True)
    refine_configs = []
    seen = set()
    for row in stage1_ok:
        key = (row["market"], row["cohort"], row["label"], row["feature_set"])
        if key in seen:
            continue
        seen.add(key)
        refine_configs.append(key)
        if len(refine_configs) >= refine_top:
            break

    for market, cohort, label_name, feature_set in refine_configs:
        market_df = df.loc[df["market2"].eq(market)].copy()
        mask = _cohort_masks(market_df)[cohort]
        cohort_df = market_df.loc[mask].copy()
        for model_name in REFINE_MODELS:
            append_result(
                _run_one(
                    cohort_df,
                    market=market,
                    cohort=cohort,
                    label_name=label_name,
                    feature_set=feature_set,
                    model_name=model_name,
                    train_ratio=train_ratio,
                    min_train=min_train,
                    min_test=min_test,
                    min_test_days=min_test_days,
                )
            )

    champions = [row for row in results if row.get("status") == "ok"]
    champions.sort(key=_score_result, reverse=True)
    report = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_rows": int(len(df)),
        "prepared_rows": int(len(df)),
        "search_config": {
            "train_ratio": train_ratio,
            "min_train": min_train,
            "min_test": min_test,
            "min_test_days": min_test_days,
            "stage1_models": STAGE1_MODELS,
            "refine_models": REFINE_MODELS,
            "refine_top": refine_top,
            "topns": TOPNS,
            "labels": [label.__dict__ for label in LABELS],
            "feature_sets": list(FEATURE_SETS.keys()),
        },
        "completed_results": int(len(results)),
        "skipped_results": int(skipped),
        "baselines": _baselines(df),
        "champions": champions[:120],
        "notes": [
            "Internal research only; production scanner and model artifacts are unchanged.",
            "Training uses chronological split by trade_date and scan-time features only.",
            "Stage 1 searches broad combinations with fast models; stage 2 refines the best base configurations with RF/XGBoost/LightGBM/CatBoost.",
            "Candidate ranking prioritizes adequate holdout sample, safer path, 5D win rate, 5D average return, bad-path rate, stop proxy, and only then label win.",
            "Theme-inclusive feature sets are reported separately because fixed theme effects can overfit rotating market themes.",
        ],
    }
    _write_json(summary_path, report)
    summary_path.with_suffix(".md").write_text(_render_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    parser = argparse.ArgumentParser(description="Run checkpointed internal KR swing retrain candidate sweep.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--stem", default="internal_retrain_sweep")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--min-train", type=int, default=80)
    parser.add_argument("--min-test", type=int, default=20)
    parser.add_argument("--min-test-days", type=int, default=2)
    parser.add_argument("--refine-top", type=int, default=60)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = _load_dataset(Path(args.input))
    summary_path = output_dir / f"{args.stem}.json"
    checkpoint_path = output_dir / f"{args.stem}.jsonl"
    report = build_sweep(
        df,
        train_ratio=float(args.train_ratio),
        min_train=int(args.min_train),
        min_test=int(args.min_test),
        min_test_days=int(args.min_test_days),
        refine_top=int(args.refine_top),
        checkpoint_path=checkpoint_path,
        summary_path=summary_path,
    )
    best = report["champions"][0] if report.get("champions") else None
    print(
        json.dumps(
            {
                "json": str(summary_path),
                "md": str(summary_path.with_suffix(".md")),
                "jsonl": str(checkpoint_path),
                "completed_results": report.get("completed_results"),
                "skipped_results": report.get("skipped_results"),
                "best": best,
            },
            ensure_ascii=False,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
