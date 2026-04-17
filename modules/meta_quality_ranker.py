"""
meta_quality_ranker.py
────────────────────────────────────────────────────────────
스캔 시 Meta-Quality 점수를 추론한다.

P(clean_hit): 손절 근처 없이 깔끔하게 목표 도달할 확률
P(fast_hit):  1~3일 내 빠르게 목표 도달할 확률

모델이 없으면 중립값(0.5)을 반환해 기존 스코어에 영향을 주지 않는다.
모델은 build_meta_quality_model.py로 훈련 후 models/meta_quality/에 저장된다.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

_MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "meta_quality"
_FEATURES = [
    "alpha_score",
    "vol_ratio",
    "atr_pct",
    "price_to_ma20",
    "price_to_ma50",
]

_loaded: dict = {}  # target → {"model": ..., "features": [...]}


def _load_model(target: str) -> Optional[dict]:
    if target in _loaded:
        return _loaded[target]
    path = _MODEL_DIR / f"meta_quality_{target}.pkl"
    if not path.exists():
        return None
    try:
        import joblib
        bundle = joblib.load(path)
        _loaded[target] = bundle
        return bundle
    except Exception as exc:
        _log.warning("meta_quality_ranker: 모델 로드 실패 (%s): %s", target, exc)
        return None


def predict_meta_quality(
    alpha_score: float,
    vol_ratio: float,
    atr_pct: float,          # ATR / entry_price * 100
    price_to_ma20: float,    # close / MA20
    price_to_ma50: float,    # close / MA50
) -> dict:
    """
    Returns:
        {
            "clean_hit_prob": float,   # 0~1
            "fast_hit_prob":  float,   # 0~1
            "model_available": bool,
        }
    """
    row = {
        "alpha_score":   float(alpha_score or 0),
        "vol_ratio":     float(vol_ratio or 1),
        "atr_pct":       float(atr_pct or 0),
        "price_to_ma20": float(price_to_ma20 or 1),
        "price_to_ma50": float(price_to_ma50 or 1),
    }

    result = {
        "clean_hit_prob":  0.5,
        "fast_hit_prob":   0.5,
        "expected_mae_pct": None,   # None = 모델 없음
        "model_available": False,
    }

    import numpy as np

    # ── 분류: clean_hit, fast_hit ──
    for target, key in (("clean_hit", "clean_hit_prob"), ("fast_hit", "fast_hit_prob")):
        bundle = _load_model(target)
        if bundle is None:
            continue
        try:
            feats = bundle.get("features", _FEATURES)
            X = np.array([[row.get(f, 0.0) for f in feats]])
            prob = float(bundle["model"].predict_proba(X)[0][1])
            result[key] = round(prob, 4)
            result["model_available"] = True
        except Exception as exc:
            _log.debug("meta_quality_ranker: 추론 실패 (%s): %s", target, exc)

    # ── 회귀: Expected MAE (음수, 낙폭) ──
    mae_bundle = _load_model("expected_mae")
    if mae_bundle is not None:
        try:
            feats = mae_bundle.get("features", _FEATURES)
            X = np.array([[row.get(f, 0.0) for f in feats]])
            pred_mae = float(mae_bundle["model"].predict(X)[0])
            result["expected_mae_pct"] = round(pred_mae, 3)
            result["model_available"] = True
        except Exception as exc:
            _log.debug("meta_quality_ranker: MAE 추론 실패: %s", exc)

    # ── 리스크 조정 점수 ──────────────────────────────────────
    # risk_adjusted_quality = clean_hit_prob / max(|expected_mae|, 0.5)
    # 높을수록: 깔끔하게 도달할 확률은 높고, 낙폭은 작은 이상적 셋업
    if result["expected_mae_pct"] is not None:
        abs_mae = max(abs(result["expected_mae_pct"]), 0.5)
        result["risk_adjusted_quality"] = round(result["clean_hit_prob"] / abs_mae, 4)
    else:
        result["risk_adjusted_quality"] = None

    return result
