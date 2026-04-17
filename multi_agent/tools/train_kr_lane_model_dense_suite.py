#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrain_ml import FEATURE_COLS, _infer_submarket, engineer_features

try:
    from catboost import CatBoostClassifier
except Exception:  # pragma: no cover
    CatBoostClassifier = None


TARGET_RETURN_PCT = 10.0
TARGET_WIN_RATE_PCT = 75.0

SEGMENTS = [
    ("kospi_core_1d", "KOSPI", "CORE_TREND", "return_1d_pct", 10),
    ("kospi_core_3d", "KOSPI", "CORE_TREND", "return_3d_pct", 10),
    ("kospi_explosive_1d", "KOSPI", "EXPLOSIVE_LEADER", "return_1d_pct", 20),
    ("kosdaq_core_1d", "KOSDAQ", "CORE_TREND", "return_1d_pct", 20),
    ("kosdaq_core_3d", "KOSDAQ", "CORE_TREND", "return_3d_pct", 20),
    ("kosdaq_explosive_1d", "KOSDAQ", "EXPLOSIVE_LEADER", "return_1d_pct", 20),
]


def _target_gap(avg_return: float, win_rate: float) -> float:
    shortfall_return = max(0.0, TARGET_RETURN_PCT - float(avg_return)) / TARGET_RETURN_PCT
    shortfall_win = max(0.0, TARGET_WIN_RATE_PCT - float(win_rate)) / TARGET_WIN_RATE_PCT
    return float(math.sqrt((shortfall_return ** 2) + (shortfall_win ** 2)))


def _load_market(market: str, input_dir: Path) -> pd.DataFrame:
    path = input_dir / f"scan_archive_learning_dataset_{market.lower()}.csv"
    df = pd.read_csv(path, low_memory=False)
    df["market_subtype"] = [
        _infer_submarket(ticker, market_type, strategy_family)
        for ticker, market_type, strategy_family in zip(
            df.get("ticker", pd.Series(dtype="object")),
            df.get("market_type", pd.Series(dtype="object")),
            df.get("strategy_family", pd.Series(dtype="object")),
        )
    ]
    df = engineer_features(df)
    trade_date = pd.to_datetime(df.get("base_trade_date", df.get("recommended_at")), errors="coerce")
    df["trade_date"] = trade_date.dt.strftime("%Y-%m-%d")
    return df


def _split_days(days: List[str]) -> tuple[set[str], set[str]]:
    if len(days) < 4:
        return set(days), set()
    train_cut = max(1, int(len(days) * 0.6))
    test_start = max(2, int(len(days) * 0.8))
    return set(days[:train_cut]), set(days[test_start:])


def _daily_metrics(df: pd.DataFrame, score_col: str, topn: int, return_col: str) -> Dict[str, float]:
    avg_rows: List[float] = []
    win_rows: List[float] = []
    hit_rows: List[float] = []
    days = 0
    for _, day_df in df.groupby("trade_date", dropna=False):
        top = day_df.sort_values(score_col, ascending=False, na_position="last").head(topn)
        if top.empty:
            continue
        r = pd.to_numeric(top[return_col], errors="coerce").dropna()
        if r.empty:
            continue
        days += 1
        avg_rows.append(float(r.mean()))
        win_rows.append(float(r.gt(0).mean()) * 100.0)
        hit = pd.to_numeric(top.get("label_hit_10pct", 0), errors="coerce").fillna(0.0)
        hit_rows.append(float(hit.mean()) * 100.0)
    avg_return = float(np.mean(avg_rows)) if avg_rows else 0.0
    win_rate = float(np.mean(win_rows)) if win_rows else 0.0
    return {
        "active_days": int(days),
        "avg_return_pct": round(avg_return, 6),
        "win_rate_pct": round(win_rate, 6),
        "hit10_precision_pct": round(float(np.mean(hit_rows)) if hit_rows else 0.0, 6),
        "target_gap": round(_target_gap(avg_return, win_rate), 6),
    }


def _models() -> Dict[str, Any]:
    models: Dict[str, Any] = {
        "hist_gb": HistGradientBoostingClassifier(max_depth=6, learning_rate=0.05, max_iter=300, random_state=42),
        "random_forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=8,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
    }
    if CatBoostClassifier is not None:
        models["catboost"] = CatBoostClassifier(
            iterations=350,
            depth=6,
            learning_rate=0.03,
            loss_function="Logloss",
            eval_metric="AUC",
            random_seed=42,
            verbose=False,
        )
    return models


def _run_segment(df: pd.DataFrame, segment_key: str, market: str, role: str, return_col: str, topn: int, models_dir: Path) -> Dict[str, Any]:
    work = df[df["kr_universe_role"].fillna("").astype(str).eq(role)].copy()
    work = work[pd.to_numeric(work[return_col], errors="coerce").notna()].copy()
    work = work[work["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    days = sorted(work["trade_date"].dropna().astype(str).unique().tolist())
    train_days, test_days = _split_days(days)
    train = work[work["trade_date"].isin(train_days)].copy()
    test = work[work["trade_date"].isin(test_days)].copy()

    base = {
        "segment": segment_key,
        "market": market,
        "role": role,
        "return_col": return_col,
        "topn": topn,
        "rows": int(len(work)),
        "days": int(len(days)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_days": int(len(train_days)),
        "test_days": int(len(test_days)),
        "results": [],
        "champion": None,
        "saved_model_path": None,
    }
    if len(train) < 100 or len(test) < 50 or len(test_days) == 0:
        return base

    feat_cols = [col for col in FEATURE_COLS if col in work.columns]
    X_train = train[feat_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    X_test = test[feat_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y_train = pd.to_numeric(train[return_col], errors="coerce").gt(0).astype(int)
    y_test = pd.to_numeric(test[return_col], errors="coerce").gt(0).astype(int)

    results: List[Dict[str, Any]] = []
    bundles: Dict[str, Any] = {}
    for name, model in _models().items():
        try:
            model.fit(X_train, y_train)
            prob = model.predict_proba(X_test)[:, 1]
            scored = test.copy()
            scored["rank_score"] = prob
            metrics = _daily_metrics(scored, "rank_score", topn=topn, return_col=return_col)
            auc = roc_auc_score(y_test, prob) if len(set(y_test)) > 1 else None
            brier = brier_score_loss(y_test, prob)
            row = {
                "model": name,
                "auc": round(float(auc), 6) if auc is not None else None,
                "brier": round(float(brier), 6),
                **metrics,
            }
            results.append(row)
            bundles[name] = {
                "model": model,
                "features": feat_cols,
                "segment": segment_key,
                "market": market,
                "role": role,
                "return_col": return_col,
                "topn": topn,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "metrics": row,
                "feature_mode": "dense_engineered",
            }
        except Exception as exc:
            results.append({"model": name, "error": f"{type(exc).__name__}: {exc}"})

    valid = [row for row in results if row.get("target_gap") is not None]
    valid.sort(key=lambda row: (float(row["target_gap"]), -float(row["avg_return_pct"]), -float(row["win_rate_pct"]), -float(row.get("auc") or 0.0)))
    champion = valid[0] if valid else None
    saved_path = None
    if champion:
        model_name = champion["model"]
        bundle = bundles.get(model_name)
        if bundle:
            path = models_dir / f"{segment_key}__dense__{model_name}.pkl"
            joblib.dump(bundle, path)
            saved_path = str(path)

    base["results"] = results
    base["champion"] = champion
    base["saved_model_path"] = saved_path
    return base


def _build_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# KR Dense Lane Model Suite",
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
        lines.append(f"## {seg['segment']}")
        lines.append(f"- rows: `{seg['rows']}` | days `{seg['days']}` | holdout days `{seg['test_days']}`")
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
    parser = argparse.ArgumentParser(description="Train dense-engineered KR lane model suite.")
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
        "KOSPI": _load_market("KOSPI", input_dir),
        "KOSDAQ": _load_market("KOSDAQ", input_dir),
    }

    segments = [
        _run_segment(frames[market], key, market, role, return_col, topn, models_dir)
        for key, market, role, return_col, topn in SEGMENTS
    ]
    valid = []
    for seg in segments:
        champ = seg.get("champion")
        if champ:
            valid.append({**champ, "segment": seg["segment"], "market": seg["market"], "saved_model_path": seg["saved_model_path"]})
    valid.sort(key=lambda row: (float(row["target_gap"]), -float(row["avg_return_pct"]), -float(row["win_rate_pct"]), -float(row.get("auc") or 0.0)))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_return_pct": TARGET_RETURN_PCT,
        "target_win_rate_pct": TARGET_WIN_RATE_PCT,
        "segments": segments,
        "overall_champion": valid[0] if valid else None,
    }

    json_path = output_dir / "kr_lane_model_dense_suite.json"
    md_path = output_dir / "kr_lane_model_dense_suite.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown(payload), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "overall_champion": payload["overall_champion"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
