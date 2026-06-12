from __future__ import annotations

from typing import Any

import numpy as np


class LightGBMStopAdjustedScorer:
    """Runtime scorer for success probability minus hard-stop risk."""

    def __init__(self, success_model: Any, stop_model: Any, *, stop_penalty_lambda: float) -> None:
        self.success_model = success_model
        self.stop_model = stop_model
        self.stop_penalty_lambda = float(stop_penalty_lambda)

    def predict(self, frame: Any) -> np.ndarray:
        success = self.success_model.predict_proba(frame)[:, 1]
        stop = self.stop_model.predict_proba(frame)[:, 1]
        return success - (self.stop_penalty_lambda * stop)
