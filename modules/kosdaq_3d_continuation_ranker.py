from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd


FEATURES = ["decision_score", "alpha_score", "ml_prob", "trend_signal"]


def _default_path() -> Path:
    raw = os.getenv("AG_KOSDAQ_3D_CONTINUATION_MODEL_PATH", "models/kosdaq_3d_continuation_ranker.pkl")
    return Path(raw)


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "nan"):
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _trend_signal(value: Any) -> float:
    text = str(value or "").strip().upper()
    if text == "UP":
        return 1.0
    if text == "DOWN":
        return -1.0
    if text in {"SIDE", "NEUTRAL"}:
        return 0.0
    return 0.0


@lru_cache(maxsize=2)
def _load_bundle(path_str: str) -> Dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        return {}
    try:
        return joblib.load(path)
    except Exception:
        return {}


def load_ranker(path: Optional[str] = None) -> Dict[str, Any]:
    return _load_bundle(str(Path(path) if path else _default_path()))


def predict_continuation_overlay(
    *,
    decision_score: Any,
    alpha_score: Any,
    ml_prob: Any,
    trend: Any,
) -> Dict[str, Any]:
    bundle = load_ranker()
    if not bundle:
        return {"enabled": False, "score_adjustment": 0.0}

    decision_value = _safe_float(decision_score)
    alpha_value = _safe_float(alpha_score)
    ml_value = _safe_float(ml_prob)
    feature_count = sum(value is not None for value in [decision_value, alpha_value, ml_value])
    if feature_count < 3:
        return {"enabled": False, "score_adjustment": 0.0, "feature_count": feature_count}

    imputer = bundle.get("imputer")
    classifier = bundle.get("classifier")
    features = bundle.get("features") or FEATURES
    metrics = bundle.get("metrics") or {}
    if imputer is None or classifier is None:
        return {"enabled": False, "score_adjustment": 0.0, "feature_count": feature_count, "metrics": metrics}

    X = pd.DataFrame(
        [[decision_value, alpha_value, ml_value, _trend_signal(trend)]],
        columns=features,
    )
    try:
        transformed = imputer.transform(X)
        prob = float(classifier.predict_proba(transformed)[0][1])
    except Exception:
        return {"enabled": False, "score_adjustment": 0.0, "feature_count": feature_count, "metrics": metrics}

    auc = float(metrics.get("auc", 0.0) or 0.0)
    quality = max(0.0, min(1.0, (auc - 0.60) / 0.25))
    raw_adj = (prob - 0.5) * 36.0
    score_adjustment = max(-10.0, min(18.0, raw_adj * max(0.55, quality)))
    return {
        "enabled": bool(metrics.get("enabled", False)),
        "prob_up_3d": round(prob * 100.0, 1),
        "quality": round(quality, 3),
        "feature_count": feature_count,
        "metrics": metrics,
        "score_adjustment": round(score_adjustment, 2),
    }
