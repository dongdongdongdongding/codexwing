#!/usr/bin/env python3
"""No-write KR INTRADAY model viability report.

This is an internal test-bed report. It evaluates whether current INTRADAY
archive labels can support a model candidate without writing or replacing any
production model artifact.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrain_ml import FEATURE_COLS, engineer_features

DEFAULT_INPUT = PROJECT_ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/learning/kr_intraday_model_viability.json"
RETURN_COLS = ("return_1d_pct", "return_3d_pct", "return_5d_pct")
MIN_ROWS = 300
MIN_POSITIVES = 60
MIN_VALIDATION_PICKS = 10
PROMOTION_MIN_AUC = 0.56
PROMOTION_MIN_WIN_PCT = 70.0
PROMOTION_MIN_AVG_PCT = 1.0
PROMOTION_MAX_MIN_LOSS_PCT = -5.0


def _derive_market_subtype(df: pd.DataFrame) -> pd.Series:
    ticker = df.get("ticker", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    market = df.get("market", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    market_type = df.get("market_type", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    out = pd.Series("UNKNOWN", index=df.index, dtype="object")
    out = out.mask(ticker.str.endswith(".KS"), "KOSPI")
    out = out.mask(ticker.str.endswith(".KQ"), "KOSDAQ")
    out = out.mask(out.eq("UNKNOWN") & market.isin(["KOSPI", "KOSDAQ"]), market)
    out = out.mask(out.eq("UNKNOWN") & market_type.isin(["KOSPI", "KOSDAQ"]), market_type)
    return out


def load_feature_frame(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise SystemExit(f"input not found: {input_path}")
    df = pd.read_csv(input_path, low_memory=False)
    df["market_subtype"] = _derive_market_subtype(df)
    scan_mode = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    df["scan_mode"] = scan_mode
    if "is_dummy_data" in df.columns:
        dummy = df["is_dummy_data"].fillna("").astype(str).str.lower().isin({"1", "true", "yes"})
        df = df.loc[~dummy].copy()
    date_source = df.get("recommended_at", pd.Series(index=df.index, dtype=object))
    if "created_at" in df.columns:
        created = df["created_at"]
        date_source = date_source.where(date_source.notna() & date_source.astype(str).str.len().gt(0), created)
    df["sort_time"] = pd.to_datetime(date_source, errors="coerce", utc=True)
    return engineer_features(df)


def _candidate_models() -> Dict[str, Any]:
    return {
        "logistic": LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42),
        "rf": RandomForestClassifier(n_estimators=400, max_depth=8, class_weight="balanced", random_state=42, n_jobs=1),
        "extratrees": ExtraTreesClassifier(n_estimators=400, max_depth=8, class_weight="balanced", random_state=42, n_jobs=1),
        "histgb": HistGradientBoostingClassifier(max_depth=5, learning_rate=0.05, max_iter=240, random_state=42),
    }


def _threshold_sweep(prob: np.ndarray, returns: np.ndarray, target: np.ndarray) -> Tuple[List[Dict[str, Any]], Dict[str, Any] | None]:
    rows: List[Dict[str, Any]] = []
    for th in np.arange(0.50, 0.96, 0.05):
        mask = prob >= float(th)
        values = returns[mask]
        if values.size == 0:
            rows.append({"threshold": round(float(th), 2), "picks": 0, "win_pct": None, "avg_pct": None, "min_pct": None, "max_pct": None, "hit_pct": None})
            continue
        rows.append(
            {
                "threshold": round(float(th), 2),
                "picks": int(values.size),
                "win_pct": round(float(np.mean(values > 0) * 100.0), 4),
                "avg_pct": round(float(np.mean(values)), 4),
                "min_pct": round(float(np.min(values)), 4),
                "max_pct": round(float(np.max(values)), 4),
                "hit_pct": round(float(np.mean(target[mask] == 1) * 100.0), 4),
            }
        )
    viable = [row for row in rows if int(row.get("picks") or 0) >= MIN_VALIDATION_PICKS and row.get("avg_pct") is not None]
    if not viable:
        return rows, None
    best = max(viable, key=lambda row: (float(row.get("win_pct") or 0), float(row.get("avg_pct") or -999), int(row.get("picks") or 0)))
    return rows, best


def _fit_predict(name: str, model: Any, x_train: pd.DataFrame, x_val: pd.DataFrame, y_train: pd.Series) -> np.ndarray:
    if name == "logistic":
        scaler = StandardScaler()
        x_train = scaler.fit_transform(x_train)
        x_val = scaler.transform(x_val)
    model.fit(x_train, y_train)
    if hasattr(model, "predict_proba"):
        return model.predict_proba(x_val)[:, 1]
    raw = model.decision_function(x_val)
    return 1.0 / (1.0 + np.exp(-raw))


def evaluate_segment(df: pd.DataFrame, *, market: str, return_col: str) -> Dict[str, Any]:
    seg = df[
        df["market_subtype"].eq(market)
        & df["scan_mode"].eq("INTRADAY")
        & pd.to_numeric(df.get(return_col), errors="coerce").notna()
    ].copy()
    seg = seg.sort_values("sort_time", na_position="first").reset_index(drop=True)
    returns = pd.to_numeric(seg.get(return_col), errors="coerce")
    target = returns.gt(0).astype(int)
    payload: Dict[str, Any] = {
        "market": market,
        "return_col": return_col,
        "rows": int(len(seg)),
        "positives": int(target.sum()),
        "positive_rate_pct": round(float(target.mean() * 100.0), 4) if len(target) else None,
        "ready": bool(len(seg) >= MIN_ROWS and int(target.sum()) >= MIN_POSITIVES),
        "models": [],
    }
    if not payload["ready"]:
        payload["warning"] = "insufficient_rows_or_positives"
        return payload

    feat_cols = [col for col in FEATURE_COLS if col in seg.columns]
    x = seg[feat_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    split_idx = max(1, min(len(seg) - 1, int(len(seg) * 0.7)))
    x_train, x_val = x.iloc[:split_idx], x.iloc[split_idx:]
    y_train, y_val = target.iloc[:split_idx], target.iloc[split_idx:]
    returns_val = returns.iloc[split_idx:].to_numpy()
    payload["train_rows"] = int(len(x_train))
    payload["validation_rows"] = int(len(x_val))
    payload["feature_count"] = int(len(feat_cols))
    payload["validation_positive_rate_pct"] = round(float(y_val.mean() * 100.0), 4)

    for name, model in _candidate_models().items():
        try:
            prob = _fit_predict(name, model, x_train, x_val, y_train)
            pred = (prob >= 0.5).astype(int)
            auc = None
            if len(set(y_val.tolist())) > 1:
                auc = round(float(roc_auc_score(y_val, prob)), 6)
            sweep, best = _threshold_sweep(prob, returns_val, y_val.to_numpy())
            payload["models"].append(
                {
                    "model": name,
                    "auc": auc,
                    "accuracy": round(float(accuracy_score(y_val, pred)), 6),
                    "best_threshold_row": best,
                    "threshold_sweep": sweep,
                }
            )
        except Exception as exc:
            payload["models"].append({"model": name, "error": str(exc)})
    payload["best_model"] = _best_model(payload["models"])
    payload["promotion_gate"] = _promotion_gate(payload["best_model"])
    return payload


def _best_model(models: Iterable[Dict[str, Any]]) -> Dict[str, Any] | None:
    viable = [row for row in models if row.get("best_threshold_row")]
    if not viable:
        return None
    return max(
        viable,
        key=lambda row: (
            float((row.get("best_threshold_row") or {}).get("win_pct") or 0),
            float((row.get("best_threshold_row") or {}).get("avg_pct") or -999),
            float(row.get("auc") or 0),
        ),
    )


def _promotion_gate(best_model: Dict[str, Any] | None) -> Dict[str, Any]:
    if not best_model:
        return {"pass": False, "reasons": ["no_viable_threshold"]}
    best = best_model.get("best_threshold_row") or {}
    reasons: List[str] = []
    auc = best_model.get("auc")
    win_pct = best.get("win_pct")
    avg_pct = best.get("avg_pct")
    min_pct = best.get("min_pct")
    if auc is None or float(auc) < PROMOTION_MIN_AUC:
        reasons.append(f"auc_below_{PROMOTION_MIN_AUC}")
    if win_pct is None or float(win_pct) < PROMOTION_MIN_WIN_PCT:
        reasons.append(f"win_below_{PROMOTION_MIN_WIN_PCT}")
    if avg_pct is None or float(avg_pct) < PROMOTION_MIN_AVG_PCT:
        reasons.append(f"avg_below_{PROMOTION_MIN_AVG_PCT}")
    if min_pct is None or float(min_pct) < PROMOTION_MAX_MIN_LOSS_PCT:
        reasons.append(f"min_loss_below_{PROMOTION_MAX_MIN_LOSS_PCT}")
    return {
        "pass": not reasons,
        "reasons": reasons,
        "thresholds": {
            "min_auc": PROMOTION_MIN_AUC,
            "min_win_pct": PROMOTION_MIN_WIN_PCT,
            "min_avg_pct": PROMOTION_MIN_AVG_PCT,
            "max_min_loss_pct": PROMOTION_MAX_MIN_LOSS_PCT,
        },
    }


def build_report(input_path: Path) -> Dict[str, Any]:
    df = load_feature_frame(input_path)
    segments = [evaluate_segment(df, market=market, return_col=return_col) for market in ("KOSPI", "KOSDAQ") for return_col in RETURN_COLS]
    return {
        "report_version": "kr_intraday_model_viability_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "min_rows": MIN_ROWS,
        "min_positives": MIN_POSITIVES,
        "promotion_thresholds": {
            "min_auc": PROMOTION_MIN_AUC,
            "min_win_pct": PROMOTION_MIN_WIN_PCT,
            "min_avg_pct": PROMOTION_MIN_AVG_PCT,
            "max_min_loss_pct": PROMOTION_MAX_MIN_LOSS_PCT,
        },
        "segments": segments,
        "notes": [
            "No production model files are written by this report.",
            "Targets are simple positive close-return labels for viability only; promotion still requires forward observation and ordered path risk labels.",
        ],
    }


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# KR INTRADAY Model Viability",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- min_rows: `{report['min_rows']}` · min_positives: `{report['min_positives']}`",
        "",
        "| Market | Horizon | Rows | Positives | Ready | Promotion | Best |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for seg in report.get("segments") or []:
        best = seg.get("best_model") or {}
        best_row = best.get("best_threshold_row") or {}
        if best_row:
            best_text = (
                f"{best.get('model')} th={best_row.get('threshold')} "
                f"picks={best_row.get('picks')} win={best_row.get('win_pct')}% "
                f"avg={best_row.get('avg_pct')}% min={best_row.get('min_pct')}% max={best_row.get('max_pct')}%"
            )
        else:
            best_text = seg.get("warning") or "-"
        gate = seg.get("promotion_gate") or {}
        promotion_text = "PASS" if gate.get("pass") else "FAIL"
        if gate.get("reasons"):
            promotion_text += " " + ",".join(gate.get("reasons") or [])
        horizon = str(seg.get("return_col") or "").replace("return_", "").replace("_pct", "").upper()
        lines.append(
            f"| {seg.get('market')} | {horizon} | {seg.get('rows')} | {seg.get('positives')} | {seg.get('ready')} | {promotion_text} | {best_text} |"
        )
    lines.extend(["", "## Notes", ""])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_markdown(report, args.output.with_suffix(".md"))
    print(json.dumps({"json": str(args.output), "md": str(args.output.with_suffix(".md"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
