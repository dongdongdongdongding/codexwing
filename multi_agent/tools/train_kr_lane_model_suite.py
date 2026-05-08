#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.inverted_signal_features import compute_low_prob_high_score_features
from multi_agent.agents.kr_quant_reranker import is_kosdaq_3d_continuation_eligible


# Evidence-based targets (archive 2026-04-22): top-pick win ceiling ≈ 66%, avg return ≈ +3.5%.
# 75%/10% was aspirational and unreachable on realized data; reset to 60%/+5% so the
# target_gap metric reflects realistic headroom.
TARGET_RETURN_PCT = 5.0
TARGET_WIN_RATE_PCT = 60.0

NUMERIC_FEATURES = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "whale_score",
    "decision_score",
    "phase25_shadow_prob",
    "phase25_recommended_threshold",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "target_horizon_days",
    "entry_reference_price",
    "explosive_eligible",
    "explosive_leader_flag",
    "core_trend_flag",
    "is_sub7",
    "trend_signal",
    "fund_pass_signal",
    "tier_rank",
    "volume_multiple",
    "textual_win_rate_pct",
    "secondary_theme_count",
    "explosive_gate_reason_count",
    "theme_present",
    "expected_return_gap_3d_1d",
    "decision_alpha_gap",
    "ml_whale_combo",
    "model_prob_available_count",
    "model_prob_mean",
    "low_model_prob_score",
    "low_prob_high_score",
    "expected_edge_inversion_score",
]

CATEGORICAL_FEATURES = [
    "scan_mode",
    "strategy_family",
    "phase25_variant",
    "phase25_shadow_variant",
    "primary_theme",
    "theme_source",
    "theme_inference_status",
    "theme_routing_path",
    "selection_lane",
    "scanner_timeframe_profile",
    "kr_universe_role",
    "trend",
    "fund_status",
    "tier",
    "position",
    "price_band",
]


@dataclass(frozen=True)
class SegmentSpec:
    key: str
    market: str
    target_col: str
    topn: int
    description: str
    role: str | None = None
    continuation_only: bool = False


SEGMENTS: List[SegmentSpec] = [
    SegmentSpec("kospi_core_1d", "KOSPI", "return_1d_pct", 10, "KOSPI core trend 1D", role="CORE_TREND"),
    SegmentSpec("kospi_core_3d", "KOSPI", "return_3d_pct", 10, "KOSPI core trend 3D", role="CORE_TREND"),
    SegmentSpec("kospi_explosive_1d", "KOSPI", "return_1d_pct", 20, "KOSPI explosive leader 1D", role="EXPLOSIVE_LEADER"),
    SegmentSpec("kosdaq_core_1d", "KOSDAQ", "return_1d_pct", 20, "KOSDAQ core trend 1D", role="CORE_TREND"),
    SegmentSpec("kosdaq_core_3d", "KOSDAQ", "return_3d_pct", 20, "KOSDAQ core trend 3D", role="CORE_TREND"),
    SegmentSpec("kosdaq_continuation_3d", "KOSDAQ", "return_3d_pct", 5, "KOSDAQ continuation 3D", role="CORE_TREND", continuation_only=True),
    SegmentSpec("kosdaq_explosive_1d", "KOSDAQ", "return_1d_pct", 20, "KOSDAQ explosive leader 1D", role="EXPLOSIVE_LEADER"),
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "nan", "None"):
            return float(default)
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return float(default)
        return result
    except Exception:
        return float(default)


def _parse_percent_text(value: Any) -> float:
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", str(value or ""))
    return _safe_float(match.group(1), 0.0) if match else 0.0


def _parse_volume_multiple(value: Any) -> float:
    match = re.search(r"x\s*(-?\d+(?:\.\d+)?)", str(value or ""), flags=re.IGNORECASE)
    return _safe_float(match.group(1), 0.0) if match else 0.0


def _tier_rank(value: Any) -> int:
    text = str(value or "").upper()
    match = re.search(r"T(\d+)", text)
    return int(match.group(1)) if match else 9


def _trend_signal(value: Any) -> int:
    text = str(value or "").upper().strip()
    if text == "UP":
        return 1
    if text == "DOWN":
        return -1
    return 0


def _fund_pass_signal(value: Any) -> int:
    text = str(value or "").upper().strip()
    if text == "PASS":
        return 1
    if text == "FAIL":
        return -1
    return 0


def _bool_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    text = str(value or "").strip().lower()
    return int(text in {"1", "true", "yes"})


def _list_len(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    text = str(value or "").strip()
    if not text or text in {"[]", "nan", "None"}:
        return 0
    return max(1, text.count(",") + 1)


def _load_market_df(market: str, input_dir: Path) -> pd.DataFrame:
    all_path = input_dir / "scan_archive_learning_dataset_all.csv"
    if all_path.exists():
        all_df = pd.read_csv(all_path, low_memory=False)
        market_key = market.upper()
        market_col = all_df.get("market")
        if market_col is not None:
            filtered = all_df[market_col.fillna("").astype(str).str.upper().eq(market_key)].copy()
        else:
            suffix = ".KS" if market_key == "KOSPI" else ".KQ"
            filtered = all_df[all_df.get("ticker", "").fillna("").astype(str).str.endswith(suffix)].copy()
        if not filtered.empty:
            filtered["market"] = market_key
            return filtered
    path = input_dir / f"scan_archive_learning_dataset_{market.lower()}.csv"
    df = pd.read_csv(path, low_memory=False)
    df["market"] = market.upper()
    return df


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "validation_excluded" in work.columns:
        raw = work["validation_excluded"]
        if raw.dtype == "object":
            excluded = raw.astype(str).str.lower().isin({"true", "1", "yes"})
        else:
            excluded = raw.astype("boolean").fillna(False)
        work = work[~excluded].copy()

    for col in [
        "alpha_score",
        "tech_score",
        "ml_prob",
        "prob_clean",
        "phase25_prob",
        "whale_score",
        "decision_score",
        "phase25_shadow_prob",
        "phase25_recommended_threshold",
        "expected_edge_score",
        "expected_return_1d_pct",
        "expected_return_3d_pct",
        "target_horizon_days",
        "entry_reference_price",
        "return_1d_pct",
        "return_3d_pct",
        "label_hit_10pct",
        "explosive_eligible",
        "explosive_leader_flag",
        "core_trend_flag",
        "is_sub7",
    ]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    work["trend_signal"] = work.get("trend", "").map(_trend_signal)
    work["fund_pass_signal"] = work.get("fund_status", "").map(_fund_pass_signal)
    work["tier_rank"] = work.get("tier", "").map(_tier_rank)
    work["volume_multiple"] = work.get("volume", "").map(_parse_volume_multiple)
    work["textual_win_rate_pct"] = work.get("win_rate", "").map(_parse_percent_text)
    work["secondary_theme_count"] = work.get("secondary_themes", []).map(_list_len)
    work["explosive_gate_reason_count"] = work.get("explosive_gate_reasons", []).map(_list_len)
    work["theme_present"] = work.get("primary_theme", "").fillna("").astype(str).ne("").astype(int)
    empty_float = pd.Series(index=work.index, dtype=float)
    expected_3d = pd.to_numeric(work.get("expected_return_3d_pct", empty_float), errors="coerce")
    expected_1d = pd.to_numeric(work.get("expected_return_1d_pct", empty_float), errors="coerce")
    decision_score = pd.to_numeric(work.get("decision_score", empty_float), errors="coerce")
    alpha_score = pd.to_numeric(work.get("alpha_score", empty_float), errors="coerce")
    ml_prob = pd.to_numeric(work.get("ml_prob", empty_float), errors="coerce")
    prob_clean = pd.to_numeric(work.get("prob_clean", empty_float), errors="coerce")
    phase25_prob = pd.to_numeric(work.get("phase25_prob", empty_float), errors="coerce")
    whale_score = pd.to_numeric(work.get("whale_score", empty_float), errors="coerce")
    work["expected_return_gap_3d_1d"] = (
        expected_3d - expected_1d
    )
    work["decision_alpha_gap"] = (
        decision_score - alpha_score
    )
    work["ml_whale_combo"] = (
        ml_prob + whale_score
    ) / 2.0
    inverted_feature_rows = [
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
    inverted_feature_df = pd.DataFrame(inverted_feature_rows, index=work.index)
    for col in [
        "model_prob_available_count",
        "model_prob_mean",
        "low_model_prob_score",
        "low_prob_high_score",
        "expected_edge_inversion_score",
    ]:
        work[col] = pd.to_numeric(inverted_feature_df[col], errors="coerce")

    trade_date = work.get("base_trade_date", work.get("recommended_at", work.get("created_at", "")))
    work["trade_date"] = pd.to_datetime(trade_date, errors="coerce").dt.strftime("%Y-%m-%d")
    created = pd.to_datetime(work.get("created_at", work.get("recommended_at", "")), errors="coerce")
    work["created_at_ts"] = created

    role = work.get("kr_universe_role", "").fillna("").astype(str).str.upper()
    if "explosive_eligible" not in work.columns:
        work["explosive_eligible"] = np.nan
    work["explosive_eligible"] = pd.to_numeric(work["explosive_eligible"], errors="coerce")
    work["explosive_leader_flag"] = pd.to_numeric(
        work.get("explosive_leader_flag", pd.Series(index=work.index, dtype=float)),
        errors="coerce",
    ).combine_first(role.eq("EXPLOSIVE_LEADER").astype(float))
    work["core_trend_flag"] = pd.to_numeric(
        work.get("core_trend_flag", pd.Series(index=work.index, dtype=float)),
        errors="coerce",
    ).combine_first(role.eq("CORE_TREND").astype(float))
    derived_sub7 = pd.to_numeric(
        work.get("entry_reference_price", pd.Series(index=work.index, dtype=float)),
        errors="coerce",
    ).le(7.0).astype(float)
    work["is_sub7"] = pd.to_numeric(
        work.get("is_sub7", pd.Series(index=work.index, dtype=float)),
        errors="coerce",
    ).combine_first(derived_sub7)
    feature_complete = pd.Series(True, index=work.index)
    for col in NUMERIC_FEATURES:
        if col not in work.columns:
            feature_complete &= False
        else:
            feature_complete &= pd.to_numeric(work[col], errors="coerce").notna()
    for col in ["scan_mode", "strategy_family", "kr_universe_role", "trend", "tier", "position"]:
        if col not in work.columns:
            feature_complete &= False
        else:
            feature_complete &= ~work[col].fillna("").astype(str).str.strip().str.lower().isin({"", "unknown", "nan", "none", "null", "missing"})
    if "inference_failed" in work.columns:
        raw = work["inference_failed"]
        failed = raw.astype(str).str.lower().isin({"true", "1", "yes"}) if raw.dtype == "object" else raw.fillna(False).astype(bool)
        feature_complete &= ~failed
    if "validation_excluded" in work.columns:
        raw = work["validation_excluded"]
        excluded = raw.astype(str).str.lower().isin({"true", "1", "yes"}) if raw.dtype == "object" else raw.fillna(False).astype(bool)
        feature_complete &= ~excluded
    if "is_dummy_data" in work.columns:
        raw = work["is_dummy_data"]
        dummy = raw.astype(str).str.lower().isin({"true", "1", "yes"}) if raw.dtype == "object" else raw.fillna(False).astype(bool)
        feature_complete &= ~dummy
    if "feature_quality" in work.columns:
        feature_complete &= work["feature_quality"].fillna("").astype(str).str.lower().isin({"", "complete"})
    work["feature_complete_core"] = feature_complete.astype(int)
    return work


def _mark_kosdaq_continuation(df: pd.DataFrame) -> pd.DataFrame:
    flags: List[int] = []
    for _, row in df.iterrows():
        gate = is_kosdaq_3d_continuation_eligible(row.to_dict())
        flags.append(int(bool(gate.get("eligible", False))))
    out = df.copy()
    out["continuation_eligible_inferred"] = flags
    return out


def _build_segment_df(df: pd.DataFrame, spec: SegmentSpec) -> pd.DataFrame:
    work = df.copy()
    if "feature_complete_core" in work.columns:
        work = work[work["feature_complete_core"].fillna(0).astype(int).eq(1)].copy()
    if spec.role:
        work = work[work["kr_universe_role"].fillna("").astype(str).str.upper().eq(spec.role)].copy()
    if spec.continuation_only:
        if "continuation_eligible_inferred" not in work.columns:
            work = _mark_kosdaq_continuation(work)
        work = work[work["continuation_eligible_inferred"].fillna(0).astype(int).eq(1)].copy()
    target = pd.to_numeric(work[spec.target_col], errors="coerce")
    work = work[target.notna()].copy()
    work["target_return_pct"] = pd.to_numeric(work[spec.target_col], errors="coerce")
    work["target_win"] = work["target_return_pct"].gt(0.0).astype(int)
    work = work[work["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    work = work.sort_values(["trade_date", "created_at_ts", "ticker"]).copy()
    return work


def _chronological_split(segment_df: pd.DataFrame, min_test_days: int = 2) -> Tuple[pd.DataFrame, pd.DataFrame]:
    unique_days = sorted(segment_df["trade_date"].dropna().astype(str).unique().tolist())
    if len(unique_days) < max(4, min_test_days + 2):
        return segment_df.iloc[0:0].copy(), segment_df.copy()
    cut = max(len(unique_days) - max(min_test_days, int(len(unique_days) * 0.3)), int(len(unique_days) * 0.7))
    cut = min(max(1, cut), len(unique_days) - min_test_days)
    train_days = set(unique_days[:cut])
    test_days = set(unique_days[cut:])
    train = segment_df[segment_df["trade_date"].isin(train_days)].copy()
    test = segment_df[segment_df["trade_date"].isin(test_days)].copy()
    return train, test


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
                        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def _model_candidates() -> Dict[str, Any]:
    candidates: Dict[str, Any] = {
        "logistic": LogisticRegression(max_iter=3000, class_weight="balanced", random_state=42),
        "random_forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=8,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=6,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "hist_gb": HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_depth=6,
            max_iter=300,
            random_state=42,
        ),
    }
    try:
        import lightgbm as lgb

        candidates["lightgbm"] = lgb.LGBMClassifier(
            n_estimators=350,
            learning_rate=0.03,
            max_depth=6,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
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
            n_estimators=350,
            learning_rate=0.03,
            max_depth=5,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
        )
    except Exception:
        pass

    try:
        from catboost import CatBoostClassifier

        candidates["catboost"] = CatBoostClassifier(
            iterations=350,
            depth=6,
            learning_rate=0.03,
            loss_function="Logloss",
            eval_metric="AUC",
            random_seed=42,
            verbose=False,
        )
    except Exception:
        pass
    return candidates


def _daily_topn_metrics(frame: pd.DataFrame, topn: int) -> Dict[str, float]:
    rows_return: List[float] = []
    rows_win: List[float] = []
    rows_hit10: List[float] = []
    active_days = 0
    for _, day_df in frame.groupby("trade_date", dropna=False):
        ordered = day_df.sort_values(["rank_score", "decision_score"], ascending=[False, False], na_position="last").head(topn)
        if ordered.empty:
            continue
        active_days += 1
        returns = pd.to_numeric(ordered["target_return_pct"], errors="coerce").dropna()
        if returns.empty:
            continue
        rows_return.append(float(returns.mean()))
        rows_win.append(float(returns.gt(0).mean()) * 100.0)
        hit = pd.to_numeric(ordered.get("label_hit_10pct", 0), errors="coerce").fillna(0.0)
        rows_hit10.append(float(hit.mean()) * 100.0)
    avg_return = float(np.mean(rows_return)) if rows_return else 0.0
    win_rate = float(np.mean(rows_win)) if rows_win else 0.0
    hit10 = float(np.mean(rows_hit10)) if rows_hit10 else 0.0
    shortfall_return = max(0.0, TARGET_RETURN_PCT - avg_return) / TARGET_RETURN_PCT
    shortfall_win = max(0.0, TARGET_WIN_RATE_PCT - win_rate) / TARGET_WIN_RATE_PCT
    target_gap = float(math.sqrt((shortfall_return ** 2) + (shortfall_win ** 2)))
    return {
        "active_days": int(active_days),
        "avg_return_pct": round(avg_return, 6),
        "win_rate_pct": round(win_rate, 6),
        "hit10_precision_pct": round(hit10, 6),
        "target_gap": round(target_gap, 6),
    }


def _evaluate_model(pipeline: Pipeline, test_df: pd.DataFrame, topn: int) -> Dict[str, Any]:
    X_test = test_df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    y_test = test_df["target_win"].astype(int)
    prob = pipeline.predict_proba(X_test)[:, 1]
    scored = test_df.copy()
    scored["rank_score"] = prob
    metrics = _daily_topn_metrics(scored, topn=topn)
    auc = roc_auc_score(y_test, prob) if len(set(y_test)) > 1 else None
    brier = brier_score_loss(y_test, prob)
    return {
        "auc": round(float(auc), 6) if auc is not None else None,
        "brier": round(float(brier), 6),
        "topn": int(topn),
        **metrics,
    }


def _fit_segment_models(spec: SegmentSpec, segment_df: pd.DataFrame, models_dir: Path) -> Dict[str, Any]:
    train_df, test_df = _chronological_split(segment_df)
    if train_df.empty or test_df.empty:
        return {
            "segment": spec.key,
            "market": spec.market,
            "description": spec.description,
            "rows": int(len(segment_df)),
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
            "days": int(segment_df["trade_date"].nunique()),
            "train_days": int(train_df["trade_date"].nunique()),
            "test_days": int(test_df["trade_date"].nunique()),
            "results": [],
            "champion": None,
            "saved_model_path": None,
        }

    X_train = train_df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    y_train = train_df["target_win"].astype(int)
    candidates = _model_candidates()
    results: List[Dict[str, Any]] = []
    bundles: Dict[str, Any] = {}

    for name, estimator in candidates.items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", _preprocessor()),
                ("model", estimator),
            ]
        )
        try:
            pipeline.fit(X_train, y_train)
            metrics = _evaluate_model(pipeline, test_df=test_df, topn=spec.topn)
            result = {
                "model": name,
                **metrics,
            }
            results.append(result)
            bundles[name] = {
                "pipeline": pipeline,
                "features_numeric": list(NUMERIC_FEATURES),
                "features_categorical": list(CATEGORICAL_FEATURES),
                "segment": spec.key,
                "market": spec.market,
                "description": spec.description,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "holdout_metrics": metrics,
                "target_col": spec.target_col,
                "topn": spec.topn,
            }
        except Exception as exc:
            results.append(
                {
                    "model": name,
                    "error": f"{type(exc).__name__}: {exc}",
                    "auc": None,
                    "brier": None,
                    "topn": spec.topn,
                    "avg_return_pct": None,
                    "win_rate_pct": None,
                    "hit10_precision_pct": None,
                    "target_gap": None,
                }
            )

    valid = [row for row in results if row.get("target_gap") is not None]
    valid.sort(
        key=lambda row: (
            float(row.get("target_gap", 999.0)),
            -float(row.get("avg_return_pct", -999.0)),
            -float(row.get("win_rate_pct", -999.0)),
            -float(row.get("auc") or 0.0),
        )
    )
    champion = valid[0] if valid else None
    saved_model_path = None
    if champion:
        model_name = str(champion["model"])
        bundle = bundles.get(model_name)
        if bundle:
            path = models_dir / f"{spec.key}__{model_name}.pkl"
            joblib.dump(bundle, path)
            saved_model_path = str(path)

    return {
        "segment": spec.key,
        "market": spec.market,
        "description": spec.description,
        "target_col": spec.target_col,
        "topn": spec.topn,
        "rows": int(len(segment_df)),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "days": int(segment_df["trade_date"].nunique()),
        "train_days": int(train_df["trade_date"].nunique()),
        "test_days": int(test_df["trade_date"].nunique()),
        "train_start": str(train_df["trade_date"].min()),
        "train_end": str(train_df["trade_date"].max()),
        "test_start": str(test_df["trade_date"].min()),
        "test_end": str(test_df["trade_date"].max()),
        "positive_rate_train": round(float(train_df["target_win"].mean()) * 100.0, 6),
        "positive_rate_test": round(float(test_df["target_win"].mean()) * 100.0, 6),
        "results": results,
        "champion": champion,
        "saved_model_path": saved_model_path,
    }


def _overall_champion(segment_reports: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    rows: List[Dict[str, Any]] = []
    for seg in segment_reports:
        champ = seg.get("champion")
        if not champ:
            continue
        rows.append(
            {
                "segment": seg["segment"],
                "market": seg["market"],
                "description": seg["description"],
                "saved_model_path": seg.get("saved_model_path"),
                **champ,
            }
        )
    if not rows:
        return None
    rows.sort(
        key=lambda row: (
            float(row.get("target_gap", 999.0)),
            -float(row.get("avg_return_pct", -999.0)),
            -float(row.get("win_rate_pct", -999.0)),
            -float(row.get("auc") or 0.0),
        )
    )
    return rows[0]


def _build_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# KR Lane Model Suite",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- target_return_pct: {payload['target_return_pct']}",
        f"- target_win_rate_pct: {payload['target_win_rate_pct']}",
        "",
    ]
    overall = payload.get("overall_champion")
    if overall:
        lines.extend(
            [
                "## Overall Champion",
                f"- segment: `{overall['segment']}`",
                f"- model: `{overall['model']}`",
                f"- avg_return_pct: `{overall['avg_return_pct']:+.2f}%`",
                f"- win_rate_pct: `{overall['win_rate_pct']:.2f}%`",
                f"- hit10_precision_pct: `{overall['hit10_precision_pct']:.2f}%`",
                f"- target_gap: `{overall['target_gap']:.4f}`",
                f"- auc: `{overall['auc']}`",
                f"- saved_model_path: `{overall['saved_model_path']}`",
                "",
            ]
        )
    for seg in payload["segments"]:
        lines.extend(
            [
                f"## {seg['segment']}",
                f"- description: `{seg['description']}`",
                f"- rows: `{seg['rows']}` | days `{seg['days']}` | holdout days `{seg['test_days']}`",
                f"- train `{seg['train_start']} -> {seg['train_end']}` | test `{seg['test_start']} -> {seg['test_end']}`",
                f"- positive_rate_train: `{seg['positive_rate_train']:.2f}%` | positive_rate_test: `{seg['positive_rate_test']:.2f}%`",
            ]
        )
        champ = seg.get("champion")
        if champ:
            lines.append(
                f"- champion: `{champ['model']}` | avg_return `{champ['avg_return_pct']:+.2f}%` | "
                f"win `{champ['win_rate_pct']:.2f}%` | hit10 `{champ['hit10_precision_pct']:.2f}%` | "
                f"target_gap `{champ['target_gap']:.4f}` | auc `{champ['auc']}`"
            )
        else:
            lines.append("- champion: `none`")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train multi-model KR lane champions from real archive data.")
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--output-dir", default="runtime_state/reports/learning")
    parser.add_argument("--models-dir", default="models/kr_lane_champions")
    args = parser.parse_args()

    input_dir = PROJECT_ROOT / str(args.input_dir)
    output_dir = PROJECT_ROOT / str(args.output_dir)
    models_dir = PROJECT_ROOT / str(args.models_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    frames = {
        "KOSPI": _prepare_df(_load_market_df("KOSPI", input_dir)),
        "KOSDAQ": _prepare_df(_load_market_df("KOSDAQ", input_dir)),
    }

    segment_reports: List[Dict[str, Any]] = []
    for spec in SEGMENTS:
        seg_df = _build_segment_df(frames[spec.market], spec)
        if len(seg_df) < 120 or seg_df["trade_date"].nunique() < 4:
            segment_reports.append(
                {
                    "segment": spec.key,
                    "market": spec.market,
                    "description": spec.description,
                    "target_col": spec.target_col,
                    "topn": spec.topn,
                    "rows": int(len(seg_df)),
                    "days": int(seg_df["trade_date"].nunique()),
                    "train_rows": 0,
                    "test_rows": 0,
                    "train_days": 0,
                    "test_days": 0,
                    "train_start": "",
                    "train_end": "",
                    "test_start": "",
                    "test_end": "",
                    "positive_rate_train": 0.0,
                    "positive_rate_test": 0.0,
                    "results": [],
                    "champion": None,
                    "saved_model_path": None,
                }
            )
            continue
        segment_reports.append(_fit_segment_models(spec, seg_df, models_dir=models_dir))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_return_pct": TARGET_RETURN_PCT,
        "target_win_rate_pct": TARGET_WIN_RATE_PCT,
        "segments": segment_reports,
        "overall_champion": _overall_champion(segment_reports),
    }

    json_path = output_dir / "kr_lane_model_suite.json"
    md_path = output_dir / "kr_lane_model_suite.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown(payload), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "overall_champion": payload["overall_champion"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
