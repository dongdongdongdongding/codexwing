"""Features for regimes where model probability is anti-correlated with winners."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List


def _finite_float(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "None", "null"):
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _prob_values(values: Iterable[Any]) -> List[float]:
    out: List[float] = []
    for value in values:
        numeric = _finite_float(value)
        if numeric is None:
            continue
        out.append(max(0.0, min(100.0, numeric)))
    return out


def compute_low_prob_high_score_features(
    *,
    alpha_score: Any = None,
    tech_score: Any = None,
    ml_prob: Any = None,
    prob_clean: Any = None,
    phase25_prob: Any = None,
    expected_edge_score: Any = None,
) -> Dict[str, float]:
    """Compute explicit inverted-probability features.

    No missing probability is replaced with a fake neutral probability. Missing
    inputs produce zero signal and are represented by model_prob_available_count.
    """
    probs = _prob_values([ml_prob, prob_clean, phase25_prob])
    prob_count = len(probs)
    model_prob_mean = sum(probs) / prob_count if prob_count else 0.0

    alpha = _finite_float(alpha_score)
    tech = _finite_float(tech_score)
    score_inputs = [v for v in (alpha, tech) if v is not None]
    technical_score_mean = sum(score_inputs) / len(score_inputs) if score_inputs else 0.0

    if prob_count:
        low_model_prob_score = max(0.0, 50.0 - model_prob_mean)
        low_prob_high_score = max(0.0, technical_score_mean - model_prob_mean)
    else:
        low_model_prob_score = 0.0
        low_prob_high_score = 0.0

    edge = _finite_float(expected_edge_score)
    expected_edge_inversion_score = max(0.0, -edge) if edge is not None else 0.0

    return {
        "model_prob_available_count": float(prob_count),
        "model_prob_mean": round(float(model_prob_mean), 6),
        "low_model_prob_score": round(float(low_model_prob_score), 6),
        "low_prob_high_score": round(float(low_prob_high_score), 6),
        "expected_edge_inversion_score": round(float(expected_edge_inversion_score), 6),
    }

