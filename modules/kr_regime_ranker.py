from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd

from modules.regime_ticker_profiles import resolve_profile_regime


def _default_path() -> Path:
    raw = os.getenv("AG_KR_REGIME_RANKER_PATH", "models/kr_regime_ranker.pkl")
    return Path(raw)


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


def predict_rank_overlay(
    *,
    market_type: str,
    market_gate: str,
    alpha_score: float,
    ai_prediction: float,
    entry_price: float,
    target_price: float,
    stop_loss: float,
) -> Dict[str, Any]:
    bundle = load_ranker()
    if not bundle:
        return {"enabled": False, "score_adjustment": 0.0}

    market = "KOSPI" if str(market_type).upper() == "KOSPI" else "KOSDAQ"
    regime = resolve_profile_regime(market_gate)
    key = f"{market}:{regime}"
    model_bucket = (bundle.get("models") or {}).get(key)
    metrics = (bundle.get("metrics") or {}).get(key, {})
    if not model_bucket:
        return {"enabled": False, "metrics": metrics, "score_adjustment": 0.0, "key": key}

    stop_pct_abs = abs(((float(entry_price) - float(stop_loss)) / float(entry_price)) * 100.0) if float(entry_price) > 0 else 0.0
    target_pct = ((float(target_price) / float(entry_price)) - 1.0) * 100.0 if float(entry_price) > 0 else 0.0
    rr = target_pct / stop_pct_abs if stop_pct_abs > 0 else 0.0

    X = pd.DataFrame(
        [[float(alpha_score), float(ai_prediction), float(target_pct), float(stop_pct_abs), float(rr)]],
        columns=bundle.get("features") or ["alpha_score", "ai_prediction", "target_pct", "stop_pct_abs", "rr"],
    )

    clf = model_bucket.get("classifier")
    reg = model_bucket.get("regressor")
    prob = float(clf.predict_proba(X)[0][1]) if clf is not None else 0.5
    pred_return = float(reg.predict(X)[0]) if reg is not None else 0.0

    auc = float(metrics.get("auc", 0.0) or 0.0)
    quality = max(0.0, min(1.0, (auc - 0.55) / 0.35))
    raw_adj = ((prob - 0.5) * 30.0) + (pred_return * 0.8)
    score_adjustment = max(-18.0, min(20.0, raw_adj * max(0.35, quality)))
    return {
        "enabled": True,
        "key": key,
        "prob_up_5d": round(prob * 100.0, 1),
        "pred_return_5d": round(pred_return, 2),
        "quality": round(quality, 3),
        "metrics": metrics,
        "score_adjustment": round(score_adjustment, 1),
    }
