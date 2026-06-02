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
from typing import Any, Dict, List, Sequence, Tuple

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/codex_swing_matplotlib")

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from sklearn.preprocessing import OneHotEncoder
except Exception:  # pragma: no cover
    OneHotEncoder = None

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover
    LGBMClassifier = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.db_manager import DBManager


warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

TARGET_TABLE = "scan_universe_snapshots"
REPORT_VERSION = "scan_universe_admission_challenger_v1"
REPORT_DIR = ROOT / "runtime_state" / "reports" / "learning"
MODEL_DIR = ROOT / "models" / "scan_universe_challengers"
MIN_PROMOTION_RUNS = 12
MIN_PROMOTION_DAYS = 6
MIN_PROMOTION_ROWS = 15

KR_RETURN_SANITY_BOUNDS = {
    "return_1d_pct": (-35.0, 35.0),
    "return_3d_pct": (-75.0, 130.0),
    "return_5d_pct": (-90.0, 300.0),
    "max_high_return_1d_pct": (-35.0, 35.0),
    "max_high_return_3d_pct": (-75.0, 130.0),
    "max_high_return_5d_pct": (-90.0, 300.0),
    "min_low_return_1d_pct": (-35.0, 35.0),
    "min_low_return_3d_pct": (-75.0, 130.0),
    "min_low_return_5d_pct": (-90.0, 300.0),
}

NUMERIC_FEATURES = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "day_return_pct",
    "volume_ratio",
    "turnover",
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
    "feature_coverage_score",
    "entry_reference_price",
    "priority_rank",
    "total_scans",
    "filtered_count",
]

CORE_NUMERIC = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "day_return_pct",
    "volume_ratio",
    "turnover",
    "feature_coverage_score",
    "entry_reference_price",
]

FLOW_NUMERIC = [
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

CATEGORICAL_FEATURES = [
    "market",
    "row_role",
    "passed_current_model",
    "decision",
    "decision_bucket",
    "reject_stage",
    "reject_reason",
    "primary_theme",
    "theme_source",
    "theme_inference_status",
    "kr_universe_role",
    "scanner_timeframe_profile",
    "has_actual_flow",
    "flow_consensus_buying",
    "retail_dominant",
    "dominant",
    "whale_trend",
]

GATE_CATEGORICAL = [
    "row_role",
    "passed_current_model",
    "decision",
    "decision_bucket",
    "reject_stage",
    "reject_reason",
]

THEME_CATEGORICAL = [
    "primary_theme",
    "theme_source",
    "theme_inference_status",
]

LABEL_RETURN_COLUMNS = [
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "max_high_return_1d_pct",
    "max_high_return_3d_pct",
    "max_high_return_5d_pct",
    "min_low_return_1d_pct",
    "min_low_return_3d_pct",
    "min_low_return_5d_pct",
]

PATH_COLUMNS = [
    "target_hit_1d",
    "target_hit_3d",
    "target_hit_5d",
    "stop_hit_1d",
    "stop_hit_3d",
    "stop_hit_5d",
    "target_before_stop_1d",
    "target_before_stop_3d",
    "target_before_stop_5d",
    "stop_before_target_1d",
    "stop_before_target_3d",
    "stop_before_target_5d",
    "first_touch_1d",
    "first_touch_3d",
    "first_touch_5d",
]

SELECT_COLUMNS = [
    "id",
    "snapshot_key",
    "run_id",
    "ticker",
    "stock_name",
    "market",
    "scan_mode",
    "base_trade_date",
    "scanned_at",
    "row_role",
    "passed_current_model",
    "priority_rank",
    "decision",
    "decision_bucket",
    "reject_stage",
    "reject_reason",
    "total_scans",
    "filtered_count",
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "day_return_pct",
    "volume_ratio",
    "turnover",
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
    "feature_coverage_score",
    "feature_missing_keys",
    "has_actual_flow",
    "flow_consensus_buying",
    "retail_dominant",
    "dominant",
    "whale_trend",
    "flow_source",
    "flow_warnings",
    "primary_theme",
    "theme_source",
    "theme_inference_status",
    "kr_universe_role",
    "scanner_timeframe_profile",
    "entry_reference_price",
    *LABEL_RETURN_COLUMNS,
    *PATH_COLUMNS,
]


@dataclass(frozen=True)
class LabelSpec:
    name: str
    horizon: str
    description: str


LABEL_SPECS = [
    LabelSpec("pos_1d", "1d", "1D close return > 0"),
    LabelSpec("pos_3d", "3d", "3D close return > 0"),
    LabelSpec("pos_5d", "5d", "5D close return > 0"),
    LabelSpec("clean_3d", "3d", "3D close > 0, 1D not worse than -2%, and 3D low above -5%"),
    LabelSpec("clean_5d", "5d", "5D close > 0, 1D not worse than -3%, and 5D low above -5%"),
    LabelSpec("sustain_1_3_5_lowdd", "5d", "1D/3D/5D all positive and 5D low above -5%"),
    LabelSpec("target_first_5d", "5d", "5D target touched before stop"),
    LabelSpec("target_first_sustain_5d", "5d", "5D target touched before stop, 3D and 5D closes positive"),
    LabelSpec("target_hit_no_stop_5d", "5d", "5D target hit and stop not hit"),
    LabelSpec("touch5_5d", "5d", "5D high touches entry +5% at least once"),
    LabelSpec("touch10_5d", "5d", "5D high touches entry +10% at least once"),
    LabelSpec("touch5_guard_5d", "5d", "5D high touches +5% while 5D low stays above -5%"),
    LabelSpec("touch10_guard_5d", "5d", "5D high touches +10% while 5D low stays above -5%"),
]

TOPNS = [1, 3, 5]


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return str(value)


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return round(number, digits)
    except Exception:
        return None


def _pct(value: Any) -> float | None:
    number = _round(value, 8)
    return round(number * 100.0, 4) if number is not None else None


def _metric_float(metrics_map: Dict[str, Any], key: str, default: float) -> float:
    value = metrics_map.get(key)
    if value is None:
        return default
    try:
        number = float(value)
    except Exception:
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    clean = series.astype("object").where(series.notna(), "")
    return clean.astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def _onehot_encoder() -> Any:
    if OneHotEncoder is None:
        raise RuntimeError("sklearn OneHotEncoder unavailable")
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False, min_frequency=3)
    except TypeError:  # pragma: no cover - older sklearn
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def fetch_rows(*, market: str, scan_mode: str, page_size: int) -> pd.DataFrame:
    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")
    rows: List[Dict[str, Any]] = []
    last_id = 0
    cols = ",".join(SELECT_COLUMNS)
    safe_page_size = min(max(1, int(page_size or 1000)), 1000)
    while True:
        query = db.client.table(TARGET_TABLE).select(cols).order("id").gt("id", last_id).limit(safe_page_size)
        if market != "ALL":
            query = query.eq("market", market)
        if scan_mode != "ALL":
            query = query.eq("scan_mode", scan_mode)
        batch = query.execute().data or []
        rows.extend(batch)
        if batch:
            last_id = max(int(row.get("id") or last_id) for row in batch)
        if len(batch) < safe_page_size:
            break
    return pd.DataFrame(rows)


def apply_return_sanity(df: pd.DataFrame, *, mode: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if df.empty or mode == "off":
        return df.copy(), {"mode": mode, "removed_rows": 0, "column_violations": {}}
    if mode != "kr_price_limit":
        raise ValueError(f"unknown return sanity mode: {mode}")
    mask = pd.Series(True, index=df.index)
    violations: Dict[str, int] = {}
    for col, (low, high) in KR_RETURN_SANITY_BOUNDS.items():
        if col not in df.columns:
            continue
        values = pd.to_numeric(df[col], errors="coerce")
        bad = values.notna() & (~values.between(low, high, inclusive="both"))
        violations[col] = int(bad.sum())
        mask &= ~bad
    clean = df.loc[mask].copy()
    return clean, {
        "mode": mode,
        "removed_rows": int((~mask).sum()),
        "remaining_rows": int(len(clean)),
        "column_violations": {key: value for key, value in violations.items() if value},
        "bounds": KR_RETURN_SANITY_BOUNDS,
    }


def prepare_dataset(df: pd.DataFrame, *, return_sanity: str = "kr_price_limit") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if df.empty:
        return df.copy(), {"mode": return_sanity, "removed_rows": 0}
    out = df.copy()
    ticker = out.get("ticker", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    market = out.get("market", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    scan_mode = out.get("scan_mode", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    out = out[(ticker.str.endswith(".KS") | ticker.str.endswith(".KQ") | market.isin(["KOSPI", "KOSDAQ"])) & scan_mode.eq("SWING")].copy()
    if out.empty:
        return out, {"mode": return_sanity, "removed_rows": 0}
    for col in sorted(set(NUMERIC_FEATURES + LABEL_RETURN_COLUMNS + ["priority_rank", "total_scans", "filtered_count"])):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in PATH_COLUMNS + ["passed_current_model", "has_actual_flow", "flow_consensus_buying", "retail_dominant"]:
        if col in out.columns:
            out[f"{col}_bool"] = _bool_series(out[col])
    for col in CATEGORICAL_FEATURES:
        if col not in out.columns:
            out[col] = "UNKNOWN"
        out[col] = out[col].fillna("UNKNOWN").astype(str)
    rec = out.get("base_trade_date", pd.Series(index=out.index, dtype=object))
    scanned = out.get("scanned_at", pd.Series(index=out.index, dtype=object))
    rec = rec.where(rec.notna() & rec.astype(str).str.strip().ne(""), scanned)
    out["trade_date"] = pd.to_datetime(rec, errors="coerce", utc=True).dt.strftime("%Y-%m-%d")
    out = out[out["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    if "run_id" not in out.columns:
        out["run_id"] = out["trade_date"]
    out["run_id"] = out["run_id"].fillna(out["trade_date"]).astype(str)
    if "market" not in out.columns:
        out["market"] = np.where(ticker.loc[out.index].str.endswith(".KS"), "KOSPI", "KOSDAQ")
    out.loc[out["market"].fillna("").astype(str).str.upper().eq(""), "market"] = np.where(
        ticker.loc[out.index].str.endswith(".KS"),
        "KOSPI",
        "KOSDAQ",
    )
    out["market"] = out["market"].fillna("").astype(str).str.upper()
    out["stop5_proxy"] = out.get("stop_before_target_5d_bool", pd.Series(False, index=out.index)).fillna(False)
    if "min_low_return_5d_pct" in out.columns:
        out["stop5_proxy"] |= out["min_low_return_5d_pct"].le(-5.0).fillna(False)
    out["bad_path"] = (
        out["stop5_proxy"]
        | out.get("return_1d_pct", pd.Series(index=out.index, dtype=float)).lt(-3.0).fillna(False)
        | out.get("return_5d_pct", pd.Series(index=out.index, dtype=float)).lt(0.0).fillna(False)
    )
    out, sanity = apply_return_sanity(out, mode=return_sanity)
    return out.sort_values(["trade_date", "run_id", "ticker"]).copy(), sanity


def label_series(df: pd.DataFrame, spec: LabelSpec) -> Tuple[pd.Series, pd.Series]:
    false = pd.Series(False, index=df.index)
    if spec.name == "pos_1d":
        valid = df["return_1d_pct"].notna()
        return df["return_1d_pct"].gt(0).fillna(False), valid
    if spec.name == "pos_3d":
        valid = df["return_3d_pct"].notna()
        return df["return_3d_pct"].gt(0).fillna(False), valid
    if spec.name == "pos_5d":
        valid = df["return_5d_pct"].notna()
        return df["return_5d_pct"].gt(0).fillna(False), valid
    if spec.name == "clean_3d":
        valid = df["return_1d_pct"].notna() & df["return_3d_pct"].notna() & df["min_low_return_3d_pct"].notna()
        return (
            df["return_3d_pct"].gt(0)
            & df["return_1d_pct"].ge(-2.0)
            & df["min_low_return_3d_pct"].gt(-5.0)
        ).fillna(False), valid
    if spec.name == "clean_5d":
        valid = df["return_1d_pct"].notna() & df["return_5d_pct"].notna() & df["min_low_return_5d_pct"].notna()
        return (
            df["return_5d_pct"].gt(0)
            & df["return_1d_pct"].ge(-3.0)
            & df["min_low_return_5d_pct"].gt(-5.0)
        ).fillna(False), valid
    if spec.name == "sustain_1_3_5_lowdd":
        valid = (
            df["return_1d_pct"].notna()
            & df["return_3d_pct"].notna()
            & df["return_5d_pct"].notna()
            & df["min_low_return_5d_pct"].notna()
        )
        return (
            df["return_1d_pct"].gt(0)
            & df["return_3d_pct"].gt(0)
            & df["return_5d_pct"].gt(0)
            & df["min_low_return_5d_pct"].gt(-5.0)
        ).fillna(False), valid
    if spec.name == "target_first_5d":
        valid = df.get("target_before_stop_5d").notna() & df.get("stop_before_target_5d").notna()
        return df.get("target_before_stop_5d_bool", false).fillna(False), valid
    if spec.name == "target_first_sustain_5d":
        valid = (
            df.get("target_before_stop_5d").notna()
            & df.get("stop_before_target_5d").notna()
            & df["return_3d_pct"].notna()
            & df["return_5d_pct"].notna()
        )
        return (
            df.get("target_before_stop_5d_bool", false).fillna(False)
            & df["return_3d_pct"].gt(0)
            & df["return_5d_pct"].gt(0)
        ).fillna(False), valid
    if spec.name == "target_hit_no_stop_5d":
        valid = df.get("target_hit_5d").notna() & df.get("stop_hit_5d").notna()
        return (
            df.get("target_hit_5d_bool", false).fillna(False)
            & ~df.get("stop_hit_5d_bool", false).fillna(False)
        ).fillna(False), valid
    if spec.name in {"touch5_5d", "touch10_5d", "touch5_guard_5d", "touch10_guard_5d"}:
        target = 10.0 if "10" in spec.name else 5.0
        mfe = pd.to_numeric(df.get("max_high_return_5d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        mae = pd.to_numeric(df.get("min_low_return_5d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        valid = mfe.notna()
        hit = mfe.ge(target).fillna(False)
        if "guard" in spec.name:
            valid &= mae.notna()
            hit &= mae.gt(-5.0).fillna(False)
        return hit, valid
    raise KeyError(spec.name)


def feature_sets(df: pd.DataFrame) -> Dict[str, Tuple[List[str], List[str]]]:
    core = [col for col in CORE_NUMERIC if col in df.columns]
    flow = [col for col in CORE_NUMERIC + FLOW_NUMERIC if col in df.columns]
    all_num = [col for col in NUMERIC_FEATURES if col in df.columns]
    non_gate_cats = [col for col in CATEGORICAL_FEATURES if col in df.columns and col not in set(GATE_CATEGORICAL + THEME_CATEGORICAL)]
    gate_cats = [col for col in CATEGORICAL_FEATURES if col in df.columns and col not in set(THEME_CATEGORICAL)]
    theme_cats = [col for col in CATEGORICAL_FEATURES if col in df.columns]
    return {
        "core_no_gate": (core, non_gate_cats),
        "flow_no_gate": (flow, non_gate_cats),
        "wide_no_theme": (all_num, gate_cats),
        "wide_theme": (all_num, theme_cats),
    }


def preprocessor(numeric: Sequence[str], categorical: Sequence[str], *, scale_numeric: bool) -> ColumnTransformer:
    num_steps: List[Tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", StandardScaler()))
    return ColumnTransformer(
        [
            ("num", Pipeline(num_steps), list(numeric)),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                        ("onehot", _onehot_encoder()),
                    ]
                ),
                list(categorical),
            ),
        ],
        remainder="drop",
    )


def model_candidate(name: str) -> Any | None:
    if name == "logistic":
        return LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs", random_state=42)
    if name == "hist_gb":
        return HistGradientBoostingClassifier(max_iter=160, max_depth=3, learning_rate=0.05, l2_regularization=0.2, random_state=42)
    if name == "extra_trees":
        return ExtraTreesClassifier(n_estimators=260, max_depth=8, min_samples_leaf=5, class_weight="balanced", random_state=42, n_jobs=-1)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=260, max_depth=8, min_samples_leaf=5, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
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
    return None


def split_windows(df: pd.DataFrame, *, min_train_days: int, test_days: int, max_folds: int) -> List[Tuple[set[str], set[str]]]:
    days = sorted(df["trade_date"].dropna().astype(str).unique().tolist())
    if len(days) < min_train_days + 1:
        return []
    windows: List[Tuple[set[str], set[str]]] = []
    end = len(days)
    while end > min_train_days and len(windows) < max_folds:
        start = max(min_train_days, end - test_days)
        train_days = set(days[:start])
        test = set(days[start:end])
        if train_days and test:
            windows.append((train_days, test))
        end = start
    return list(reversed(windows))


def top_indices_by_run(frame: pd.DataFrame, score: pd.Series, topn: int, *, min_score: float | None = None) -> pd.Index:
    scored = frame.copy()
    scored["_score"] = pd.to_numeric(score.reindex(frame.index), errors="coerce")
    chunks: List[pd.Index] = []
    for _run_id, run_df in scored.groupby("run_id", dropna=False):
        if min_score is not None:
            run_df = run_df[run_df["_score"].ge(min_score)]
            if run_df.empty:
                continue
        top = run_df.sort_values("_score", ascending=False, na_position="last").head(topn)
        if not top.empty:
            chunks.append(top.index)
    if not chunks:
        return pd.Index([])
    return chunks[0].append(chunks[1:]) if len(chunks) > 1 else chunks[0]


def current_top_indices(frame: pd.DataFrame, topn: int, *, include_exception: bool) -> pd.Index:
    rank = pd.to_numeric(frame.get("priority_rank", pd.Series(index=frame.index, dtype=float)), errors="coerce")
    emitted = frame.get("row_role", pd.Series("", index=frame.index)).fillna("").astype(str).eq("emitted")
    exception = (
        frame.get("decision_bucket", pd.Series("", index=frame.index)).fillna("").astype(str).str.lower().eq("exception_leader")
        | frame.get("decision", pd.Series("", index=frame.index)).fillna("").astype(str).str.upper().eq("EXCEPTION_LEADER")
    )
    mask = emitted & rank.between(1, topn, inclusive="both")
    if include_exception:
        mask |= exception
    return frame.index[mask]


def metrics(frame: pd.DataFrame, idx: pd.Index, label: pd.Series) -> Dict[str, Any]:
    sub = frame.loc[idx]
    if sub.empty:
        return {"n": 0, "active_runs": 0, "active_days": 0}
    wins = label.loc[idx].astype(bool)
    out: Dict[str, Any] = {
        "n": int(len(sub)),
        "active_runs": int(sub["run_id"].nunique()) if "run_id" in sub.columns else 0,
        "active_days": int(sub["trade_date"].nunique()) if "trade_date" in sub.columns else 0,
        "label_win_pct": _pct(wins.mean()) if len(wins) else None,
        "bad_path_pct": _pct(sub.get("bad_path", pd.Series(False, index=sub.index)).fillna(False).mean()),
        "stop5_pct": _pct(sub.get("stop5_proxy", pd.Series(False, index=sub.index)).fillna(False).mean()),
    }
    for horizon, col in [("1d", "return_1d_pct"), ("3d", "return_3d_pct"), ("5d", "return_5d_pct")]:
        ret = pd.to_numeric(sub.get(col, pd.Series(index=sub.index, dtype=float)), errors="coerce").dropna()
        out[f"win_{horizon}_pct"] = _pct(ret.gt(0).mean()) if len(ret) else None
        out[f"avg_{horizon}_pct"] = _round(ret.mean()) if len(ret) else None
        out[f"median_{horizon}_pct"] = _round(ret.median()) if len(ret) else None
        out[f"min_{horizon}_pct"] = _round(ret.min()) if len(ret) else None
        out[f"max_{horizon}_pct"] = _round(ret.max()) if len(ret) else None
    for horizon in ("1d", "3d", "5d"):
        target = sub.get(f"target_before_stop_{horizon}", pd.Series(index=sub.index, dtype=object))
        stop = sub.get(f"stop_before_target_{horizon}", pd.Series(index=sub.index, dtype=object))
        target_valid = target.notna()
        if target_valid.any():
            out[f"target_before_stop_{horizon}_pct"] = _pct(_bool_series(target.loc[target_valid]).mean())
            out[f"stop_before_target_{horizon}_pct"] = _pct(_bool_series(stop.loc[target_valid]).mean())
    mfe = pd.to_numeric(sub.get("max_high_return_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce").dropna()
    mae = pd.to_numeric(sub.get("min_low_return_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce").dropna()
    if len(mfe):
        out["hit5_5d_pct"] = _pct(mfe.ge(5.0).mean())
        out["hit10_5d_pct"] = _pct(mfe.ge(10.0).mean())
    if len(mfe) and len(mae):
        aligned = sub[["max_high_return_5d_pct", "min_low_return_5d_pct"]].apply(pd.to_numeric, errors="coerce").dropna()
        if not aligned.empty:
            out["hit5_guard_5d_pct"] = _pct((aligned["max_high_return_5d_pct"].ge(5.0) & aligned["min_low_return_5d_pct"].gt(-5.0)).mean())
            out["hit10_guard_5d_pct"] = _pct((aligned["max_high_return_5d_pct"].ge(10.0) & aligned["min_low_return_5d_pct"].gt(-5.0)).mean())
    out["avg_max_high_5d_pct"] = _round(mfe.mean()) if len(mfe) else None
    out["min_max_high_5d_pct"] = _round(mfe.min()) if len(mfe) else None
    out["max_max_high_5d_pct"] = _round(mfe.max()) if len(mfe) else None
    out["avg_min_low_5d_pct"] = _round(mae.mean()) if len(mae) else None
    out["min_min_low_5d_pct"] = _round(mae.min()) if len(mae) else None
    out["max_min_low_5d_pct"] = _round(mae.max()) if len(mae) else None
    return out


def quality_score(result_metrics: Dict[str, Any], *, topn: int) -> float:
    n = float(result_metrics.get("n") or 0)
    runs = float(result_metrics.get("active_runs") or 0)
    days = float(result_metrics.get("active_days") or 0)
    avg1 = float(result_metrics.get("avg_1d_pct") or -20.0)
    avg3 = float(result_metrics.get("avg_3d_pct") or -20.0)
    avg5 = float(result_metrics.get("avg_5d_pct") or -20.0)
    win1 = float(result_metrics.get("win_1d_pct") or 0.0)
    win3 = float(result_metrics.get("win_3d_pct") or 0.0)
    win5 = float(result_metrics.get("win_5d_pct") or 0.0)
    min1 = float(result_metrics.get("min_1d_pct") or -50.0)
    min3 = float(result_metrics.get("min_3d_pct") or -50.0)
    min5 = float(result_metrics.get("min_5d_pct") or -50.0)
    bad = float(result_metrics.get("bad_path_pct") if result_metrics.get("bad_path_pct") is not None else 100.0)
    stop = float(result_metrics.get("stop5_pct") if result_metrics.get("stop5_pct") is not None else 100.0)
    target_first = float(result_metrics.get("target_before_stop_5d_pct") or 0.0)
    hit5 = float(result_metrics.get("hit5_5d_pct") or 0.0)
    hit10 = float(result_metrics.get("hit10_5d_pct") or 0.0)
    hit5_guard = float(result_metrics.get("hit5_guard_5d_pct") or 0.0)
    hit10_guard = float(result_metrics.get("hit10_guard_5d_pct") or 0.0)
    avg_mfe = float(result_metrics.get("avg_max_high_5d_pct") or -20.0)
    min_mfe = float(result_metrics.get("min_max_high_5d_pct") or -20.0)
    sample_penalty = 0.0
    if runs < MIN_PROMOTION_RUNS:
        sample_penalty += (MIN_PROMOTION_RUNS - runs) * 18.0
    if days < MIN_PROMOTION_DAYS:
        sample_penalty += (MIN_PROMOTION_DAYS - days) * 24.0
    if n < max(MIN_PROMOTION_ROWS, topn * 8):
        sample_penalty += (max(MIN_PROMOTION_ROWS, topn * 8) - n) * 12.0
    tail_penalty = max(0.0, -5.0 - min1) * 2.5 + max(0.0, -8.0 - min3) * 1.5 + max(0.0, -12.0 - min5)
    return (
        win1 * 0.5
        + win3 * 0.8
        + win5 * 1.0
        + avg1 * 8.0
        + avg3 * 12.0
        + avg5 * 16.0
        + target_first * 0.25
        + hit5 * 0.35
        + hit10 * 0.70
        + hit5_guard * 0.45
        + hit10_guard * 0.90
        + avg_mfe * 20.0
        + min_mfe * 8.0
        - bad * 0.8
        - stop * 0.6
        - tail_penalty
        - sample_penalty
    )


def usable_features(frame: pd.DataFrame, numeric: Sequence[str], categorical: Sequence[str]) -> Tuple[List[str], List[str]]:
    usable_numeric = []
    for col in numeric:
        if col not in frame.columns:
            continue
        values = pd.to_numeric(frame[col], errors="coerce")
        if values.notna().any():
            usable_numeric.append(col)
    usable_categorical = []
    for col in categorical:
        if col not in frame.columns:
            continue
        values = frame[col].fillna("UNKNOWN").astype(str)
        if values.nunique(dropna=False) > 1:
            usable_categorical.append(col)
    return usable_numeric, usable_categorical


def run_candidate(
    work: pd.DataFrame,
    *,
    market: str,
    label_spec: LabelSpec,
    feature_name: str,
    numeric: List[str],
    categorical: List[str],
    model_name: str,
    topn: int,
    prob_threshold: float | None,
    min_train_rows: int,
    min_test_rows: int,
    min_train_days: int,
    test_days: int,
    max_folds: int,
) -> Dict[str, Any]:
    label, valid = label_series(work, label_spec)
    scoped = work.loc[valid & work["market"].eq(market)].copy()
    y = label.loc[scoped.index].astype(int)
    base = {
        "market": market,
        "label": label_spec.name,
        "label_description": label_spec.description,
        "feature_set": feature_name,
        "model": model_name,
        "topn": topn,
        "prob_threshold": _round(prob_threshold) if prob_threshold is not None else None,
        "selection_rule": f"top{topn}" if prob_threshold is None else f"top{topn}_p{prob_threshold:.2f}",
        "rows": int(len(scoped)),
        "positive_rate_pct": _pct(y.mean()) if len(y) else None,
        "status": "skipped",
    }
    if len(scoped) < min_train_rows + min_test_rows:
        return {**base, "skip_reason": "insufficient_rows"}
    if y.nunique() < 2:
        return {**base, "skip_reason": "single_class"}
    windows = split_windows(scoped, min_train_days=min_train_days, test_days=test_days, max_folds=max_folds)
    if not windows:
        return {**base, "skip_reason": "insufficient_time_windows"}
    estimator = model_candidate(model_name)
    if estimator is None:
        return {**base, "skip_reason": "model_unavailable"}
    numeric, categorical = usable_features(scoped, numeric, categorical)
    features = [col for col in numeric + categorical if col in scoped.columns]
    if not features:
        return {**base, "skip_reason": "no_features"}
    selected_indices: List[pd.Index] = []
    fold_metrics = []
    aucs = []
    briers = []
    for train_days, test_day_set in windows:
        train_idx = scoped.index[scoped["trade_date"].isin(train_days)]
        test_idx = scoped.index[scoped["trade_date"].isin(test_day_set)]
        if len(train_idx) < min_train_rows or len(test_idx) < min_test_rows:
            continue
        if y.loc[train_idx].nunique() < 2 or y.loc[test_idx].nunique() < 2:
            continue
        scale = model_name == "logistic"
        pipe = Pipeline([("pre", preprocessor(numeric, categorical, scale_numeric=scale)), ("model", estimator)])
        x_train = scoped.loc[train_idx, features].copy()
        x_test = scoped.loc[test_idx, features].copy()
        for col in categorical:
            if col in x_train.columns:
                x_train[col] = x_train[col].fillna("UNKNOWN").astype(str)
                x_test[col] = x_test[col].fillna("UNKNOWN").astype(str)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pipe.fit(x_train, y.loc[train_idx])
                prob = pd.Series(pipe.predict_proba(x_test)[:, 1], index=test_idx)
        except Exception as exc:
            return {**base, "skip_reason": f"{type(exc).__name__}: {exc}"}
        idx = top_indices_by_run(scoped.loc[test_idx], prob, topn, min_score=prob_threshold)
        if len(idx):
            selected_indices.append(idx)
        fold_m = metrics(scoped, idx, label)
        fold_m["test_days"] = sorted(test_day_set)
        fold_metrics.append(fold_m)
        try:
            aucs.append(float(roc_auc_score(y.loc[test_idx], prob)))
            briers.append(float(brier_score_loss(y.loc[test_idx], prob)))
        except Exception:
            pass
    if not selected_indices:
        return {**base, "skip_reason": "no_selected_indices"}
    idx_all = selected_indices[0].append(selected_indices[1:]) if len(selected_indices) > 1 else selected_indices[0]
    merged = metrics(scoped, idx_all, label)
    return {
        **base,
        "status": "ok",
        "folds": int(len(fold_metrics)),
        "auc_mean": _round(np.mean(aucs)) if aucs else None,
        "brier_mean": _round(np.mean(briers)) if briers else None,
        "metrics": merged,
        "fold_metrics": fold_metrics,
        "quality_score": _round(quality_score(merged, topn=topn), 6),
        "feature_columns": {"numeric": numeric, "categorical": categorical},
    }


def baseline_results(work: pd.DataFrame, *, market: str, label_spec: LabelSpec, topn: int, holdout_days: set[str]) -> List[Dict[str, Any]]:
    label, valid = label_series(work, label_spec)
    scoped = work.loc[valid & work["market"].eq(market) & work["trade_date"].isin(holdout_days)].copy()
    if scoped.empty:
        return []
    out = []
    for name, idx in [
        (f"current_top{topn}", current_top_indices(scoped, topn, include_exception=False)),
        (f"current_top{topn}_exception", current_top_indices(scoped, topn, include_exception=True)),
        (f"decision_score_top{topn}", top_indices_by_run(scoped, scoped.get("decision_score", pd.Series(index=scoped.index)), topn)),
        (f"ml_prob_top{topn}", top_indices_by_run(scoped, scoped.get("ml_prob", pd.Series(index=scoped.index)), topn)),
    ]:
        out.append({"baseline": name, "market": market, "label": label_spec.name, "topn": topn, "metrics": metrics(scoped, idx, label)})
    return out


def parse_thresholds(raw: str) -> List[float | None]:
    values: List[float | None] = [None]
    for item in str(raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        values.append(float(item))
    return values


def candidate_blocking_reasons(candidate: Dict[str, Any] | None) -> List[str]:
    if not candidate:
        return ["no_valid_challenger"]
    m = candidate.get("metrics") or {}
    reasons = []
    topn = int(candidate.get("topn") or 1)
    if int(m.get("active_runs") or 0) < MIN_PROMOTION_RUNS:
        reasons.append("active_runs_lt_12")
    if int(m.get("active_days") or 0) < MIN_PROMOTION_DAYS:
        reasons.append("active_days_lt_6")
    if int(m.get("n") or 0) < max(MIN_PROMOTION_ROWS, topn * 8):
        reasons.append("sample_too_small")
    label_name = str(candidate.get("label") or "")
    is_touch_label = label_name.startswith("touch") or label_name.startswith("target_")
    if is_touch_label:
        min_label_win = 45.0 if "10" in label_name else 65.0
        if _metric_float(m, "label_win_pct", 0.0) < min_label_win:
            reasons.append(f"label_win_lt_{int(min_label_win)}")
        if _metric_float(m, "hit5_5d_pct", 0.0) < 65.0:
            reasons.append("hit5_5d_lt_65")
        if "10" in label_name and _metric_float(m, "hit10_5d_pct", 0.0) < 35.0:
            reasons.append("hit10_5d_lt_35")
        if _metric_float(m, "avg_max_high_5d_pct", -999.0) < 5.0:
            reasons.append("avg_mfe_5d_lt_5")
        if m.get("min_max_high_5d_pct") is not None and _metric_float(m, "min_max_high_5d_pct", -999.0) < 1.5:
            reasons.append("min_mfe_5d_lt_1p5")
    else:
        if _metric_float(m, "win_3d_pct", 0.0) < 70.0:
            reasons.append("win_3d_lt_70")
        if _metric_float(m, "win_5d_pct", 0.0) < 70.0:
            reasons.append("win_5d_lt_70")
        if _metric_float(m, "avg_3d_pct", -999.0) <= 0.0:
            reasons.append("avg_3d_not_positive")
        if _metric_float(m, "avg_5d_pct", -999.0) <= 0.0:
            reasons.append("avg_5d_not_positive")
    if _metric_float(m, "min_1d_pct", -999.0) < -5.0:
        reasons.append("min_1d_below_stop")
    if m.get("min_5d_pct") is not None and _metric_float(m, "min_5d_pct", -999.0) < -12.0:
        reasons.append("min_5d_tail_below_12")
    if _metric_float(m, "stop5_pct", 100.0) > 35.0:
        reasons.append("stop5_above_35")
    return reasons


def candidate_verdict(candidate: Dict[str, Any] | None) -> Dict[str, Any]:
    reasons = candidate_blocking_reasons(candidate)
    return {"promotable": not reasons, "blocking_reasons": reasons}


def promotion_verdict(best: Dict[str, Any] | None, baselines: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not best:
        return {"promotable": False, "reason": "no_valid_challenger"}
    reasons = candidate_blocking_reasons(best)
    baseline_rows = []
    for row in baselines:
        bm = row.get("metrics") or {}
        if int(bm.get("n") or 0) <= 0:
            continue
        baseline_rows.append(
            {
                "baseline": row.get("baseline"),
                "topn": row.get("topn"),
                "win_3d_pct": bm.get("win_3d_pct"),
                "win_5d_pct": bm.get("win_5d_pct"),
                "avg_3d_pct": bm.get("avg_3d_pct"),
                "avg_5d_pct": bm.get("avg_5d_pct"),
                "min_5d_pct": bm.get("min_5d_pct"),
            }
        )
    return {
        **candidate_verdict(best),
        "blocking_reasons": reasons,
        "baseline_rows_considered": baseline_rows,
    }


def train_final_model(work: pd.DataFrame, best: Dict[str, Any], *, output_dir: Path) -> Dict[str, Any]:
    label_spec = next(item for item in LABEL_SPECS if item.name == best["label"])
    label, valid = label_series(work, label_spec)
    scoped = work.loc[valid & work["market"].eq(best["market"])].copy()
    y = label.loc[scoped.index].astype(int)
    cols = best.get("feature_columns") or {}
    numeric, categorical = usable_features(
        scoped,
        [col for col in cols.get("numeric", []) if col in scoped.columns],
        [col for col in cols.get("categorical", []) if col in scoped.columns],
    )
    features = numeric + categorical
    estimator = model_candidate(best["model"])
    if estimator is None or scoped.empty or y.nunique() < 2:
        return {"saved": False, "reason": "not_trainable"}
    pipe = Pipeline(
        [
            ("pre", preprocessor(numeric, categorical, scale_numeric=best["model"] == "logistic")),
            ("model", estimator),
        ]
    )
    x = scoped[features].copy()
    for col in categorical:
        x[col] = x[col].fillna("UNKNOWN").astype(str)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe.fit(x, y)
    output_dir.mkdir(parents=True, exist_ok=True)
    rule = str(best.get("selection_rule") or f"top{best['topn']}").replace(".", "p")
    model_path = output_dir / f"{best['market'].lower()}__{best['label']}__{best['feature_set']}__{best['model']}__{rule}.pkl"
    bundle = {
        "version": REPORT_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "target_table": TARGET_TABLE,
        "label": best["label"],
        "label_description": best.get("label_description"),
        "market": best["market"],
        "topn": best["topn"],
        "prob_threshold": best.get("prob_threshold"),
        "selection_rule": best.get("selection_rule"),
        "feature_set": best["feature_set"],
        "feature_columns": {"numeric": numeric, "categorical": categorical},
        "model_name": best["model"],
        "pipeline": pipe,
        "validation": best,
    }
    joblib.dump(bundle, model_path)
    return {"saved": True, "model_path": str(model_path), "train_rows": int(len(scoped)), "positive_rate_pct": _pct(y.mean())}


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    raw = fetch_rows(market=args.market, scan_mode=args.scan_mode, page_size=max(1, int(args.page_size)))
    data, return_sanity = prepare_dataset(raw, return_sanity=args.return_sanity)
    feature_map = feature_sets(data)
    model_names = [name.strip() for name in str(args.models).split(",") if name.strip()]
    markets = ["KOSPI", "KOSDAQ"] if args.market == "ALL" else [args.market]
    labels = {
        item.strip()
        for item in str(args.labels).split(",")
        if item.strip()
    }
    selected_specs = [spec for spec in LABEL_SPECS if not labels or spec.name in labels]
    feature_filters = {
        item.strip()
        for item in str(args.feature_sets).split(",")
        if item.strip()
    }
    topns = [int(item.strip()) for item in str(args.topns).split(",") if item.strip()]
    prob_thresholds = parse_thresholds(args.prob_thresholds)
    all_results: List[Dict[str, Any]] = []
    for market in markets:
        market_df = data[data["market"].eq(market)]
        if market_df.empty:
            continue
        for spec in selected_specs:
            for feature_name, (numeric, categorical) in feature_map.items():
                if args.no_theme and "theme" in feature_name:
                    continue
                if feature_filters and feature_name not in feature_filters:
                    continue
                for model_name in model_names:
                    for topn in topns:
                        for prob_threshold in prob_thresholds:
                            result = run_candidate(
                                data,
                                market=market,
                                label_spec=spec,
                                feature_name=feature_name,
                                numeric=numeric,
                                categorical=categorical,
                                model_name=model_name,
                                topn=topn,
                                prob_threshold=prob_threshold,
                                min_train_rows=int(args.min_train_rows),
                                min_test_rows=int(args.min_test_rows),
                                min_train_days=int(args.min_train_days),
                                test_days=int(args.test_days),
                                max_folds=int(args.max_folds),
                            )
                            all_results.append(result)
                            if len(all_results) % 25 == 0:
                                print(f"[INFO] evaluated {len(all_results)} challenger combinations", flush=True)
    ok_results = [row for row in all_results if row.get("status") == "ok"]
    for row in ok_results:
        row["promotion_candidate"] = candidate_verdict(row)
    ok_results = sorted(
        ok_results,
        key=lambda row: (
            bool((row.get("promotion_candidate") or {}).get("promotable")),
            float(row.get("quality_score") or -1e9),
        ),
        reverse=True,
    )
    best = ok_results[0] if ok_results else None
    holdout_days = set()
    if best and best.get("fold_metrics"):
        for item in best.get("fold_metrics") or []:
            holdout_days.update(str(day) for day in item.get("test_days") or [])
    baselines: List[Dict[str, Any]] = []
    if best:
        best_label = next(item for item in LABEL_SPECS if item.name == best["label"])
        for topn in topns:
            baselines.extend(baseline_results(data, market=best["market"], label_spec=best_label, topn=topn, holdout_days=holdout_days))
    verdict = promotion_verdict(best, baselines)
    final_model = (
        train_final_model(data, best, output_dir=Path(args.model_dir))
        if best and verdict.get("promotable") and not args.no_save_model
        else {"saved": False, "reason": "not_promotable" if best else "no_best"}
    )
    report = {
        "version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": TARGET_TABLE,
        "raw_rows": int(len(raw)),
        "prepared_rows": int(len(data)),
        "markets": markets,
        "scan_mode": args.scan_mode,
        "evaluated_combinations": int(len(all_results)),
        "ok_combinations": int(len(ok_results)),
        "best": best,
        "top_results": ok_results[: int(args.top_results)],
        "baselines_for_best_holdout": baselines,
        "promotion_verdict": verdict,
        "final_model": final_model,
        "selection_policy": {
            "description": "Promotable candidates are ranked ahead of sparse or blocked high-score candidates.",
            "min_active_runs": MIN_PROMOTION_RUNS,
            "min_active_days": MIN_PROMOTION_DAYS,
            "min_rows": MIN_PROMOTION_ROWS,
        },
        "data_quality": {
            "return_sanity": return_sanity,
            "rows_by_market": data.get("market", pd.Series(dtype=object)).value_counts().to_dict() if not data.empty else {},
            "rows_by_role": data.get("row_role", pd.Series(dtype=object)).value_counts().to_dict() if "row_role" in data.columns else {},
            "date_min": str(data["trade_date"].min()) if not data.empty else None,
            "date_max": str(data["trade_date"].max()) if not data.empty else None,
            "unique_runs": int(data["run_id"].nunique()) if "run_id" in data.columns else 0,
        },
    }
    return report


def _markdown(report: Dict[str, Any]) -> str:
    best = report.get("best") or {}
    m = best.get("metrics") or {}
    lines = [
        "# Scan Universe Admission Challenger",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source: `{report.get('source')}`",
        f"- prepared_rows: `{report.get('prepared_rows')}`",
        f"- evaluated_combinations: `{report.get('evaluated_combinations')}`",
        f"- ok_combinations: `{report.get('ok_combinations')}`",
        f"- final_model: `{report.get('final_model')}`",
        f"- promotion_verdict: `{report.get('promotion_verdict')}`",
        "",
        "## Best",
        f"- market: `{best.get('market')}`",
        f"- label: `{best.get('label')}`",
        f"- feature_set: `{best.get('feature_set')}`",
        f"- model: `{best.get('model')}`",
        f"- topn: `{best.get('topn')}`",
        f"- selection_rule: `{best.get('selection_rule')}`",
        f"- quality_score: `{best.get('quality_score')}`",
        f"- n / active_runs / active_days: `{m.get('n')}` / `{m.get('active_runs')}` / `{m.get('active_days')}`",
        f"- 1d win/avg/min/max: `{m.get('win_1d_pct')}` / `{m.get('avg_1d_pct')}` / `{m.get('min_1d_pct')}` / `{m.get('max_1d_pct')}`",
        f"- 3d win/avg/min/max: `{m.get('win_3d_pct')}` / `{m.get('avg_3d_pct')}` / `{m.get('min_3d_pct')}` / `{m.get('max_3d_pct')}`",
        f"- 5d win/avg/min/max: `{m.get('win_5d_pct')}` / `{m.get('avg_5d_pct')}` / `{m.get('min_5d_pct')}` / `{m.get('max_5d_pct')}`",
        f"- target_before_stop_5d_pct: `{m.get('target_before_stop_5d_pct')}`",
        f"- hit5/hit10 5d pct: `{m.get('hit5_5d_pct')}` / `{m.get('hit10_5d_pct')}`",
        f"- guarded hit5/hit10 5d pct: `{m.get('hit5_guard_5d_pct')}` / `{m.get('hit10_guard_5d_pct')}`",
        f"- 5d max-high avg/min/max: `{m.get('avg_max_high_5d_pct')}` / `{m.get('min_max_high_5d_pct')}` / `{m.get('max_max_high_5d_pct')}`",
        f"- stop5_pct / bad_path_pct: `{m.get('stop5_pct')}` / `{m.get('bad_path_pct')}`",
        "",
        "## Baselines",
    ]
    for row in report.get("baselines_for_best_holdout") or []:
        bm = row.get("metrics") or {}
        lines.append(
            f"- `{row.get('baseline')}` top{row.get('topn')}: "
            f"n={bm.get('n')}, 1d={bm.get('win_1d_pct')}%/{bm.get('avg_1d_pct')}%, "
            f"3d={bm.get('win_3d_pct')}%/{bm.get('avg_3d_pct')}%, "
            f"5d={bm.get('win_5d_pct')}%/{bm.get('avg_5d_pct')}%, "
            f"hit5={bm.get('hit5_5d_pct')}%, hit10={bm.get('hit10_5d_pct')}%, "
            f"mfe5={bm.get('avg_max_high_5d_pct')}%, min5={bm.get('min_5d_pct')}%, max5={bm.get('max_5d_pct')}%"
        )
    lines.extend(["", "## Top Results"])
    for idx, row in enumerate(report.get("top_results") or [], start=1):
        rm = row.get("metrics") or {}
        lines.append(
            f"{idx}. `{row.get('market')}` `{row.get('label')}` `{row.get('feature_set')}` "
            f"`{row.get('model')}` {row.get('selection_rule') or ('top' + str(row.get('topn')))}: "
            f"score={row.get('quality_score')}, n={rm.get('n')}, "
            f"1d={rm.get('win_1d_pct')}%/{rm.get('avg_1d_pct')}%, "
            f"3d={rm.get('win_3d_pct')}%/{rm.get('avg_3d_pct')}%, "
            f"5d={rm.get('win_5d_pct')}%/{rm.get('avg_5d_pct')}%, "
            f"hit5={rm.get('hit5_5d_pct')}%, hit10={rm.get('hit10_5d_pct')}%, "
            f"mfe5={rm.get('avg_max_high_5d_pct')}%, min5={rm.get('min_5d_pct')}%, max5={rm.get('max_5d_pct')}%"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Train and validate a full-universe KR admission challenger model.")
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="SWING")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--models", default="logistic,hist_gb,extra_trees,random_forest,xgboost,lightgbm")
    parser.add_argument("--labels", default="", help="Comma-separated label names. Empty means all labels.")
    parser.add_argument("--feature-sets", default="", help="Comma-separated feature-set names. Empty means all feature sets.")
    parser.add_argument("--topns", default="1,3,5", help="Comma-separated top-N cutoffs to evaluate.")
    parser.add_argument("--prob-thresholds", default="", help="Comma-separated probability floors. Empty means top-N without a floor.")
    parser.add_argument("--min-train-rows", type=int, default=1000)
    parser.add_argument("--min-test-rows", type=int, default=200)
    parser.add_argument("--min-train-days", type=int, default=3)
    parser.add_argument("--test-days", type=int, default=2)
    parser.add_argument("--max-folds", type=int, default=5)
    parser.add_argument("--top-results", type=int, default=20)
    parser.add_argument("--no-theme", action="store_true")
    parser.add_argument("--return-sanity", choices=["kr_price_limit", "off"], default="kr_price_limit")
    parser.add_argument("--no-save-model", action="store_true")
    parser.add_argument("--output", default=str(REPORT_DIR / "scan_universe_admission_challenger.json"))
    parser.add_argument("--model-dir", default=str(MODEL_DIR))
    args = parser.parse_args()
    report = build_report(args)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    out.with_suffix(".md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
