from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from multi_agent.tools import save_kis_shadow_admission_models as tool


def test_save_shadow_bundle_updates_current_alias(monkeypatch, tmp_path: Path) -> None:
    model_dir = tmp_path / "models"
    model_path = model_dir / "kosdaq__touch5_dd10_5d__kis_sidecar_failure_risk_augmented__lightgbm__top2_p0p50_tail0p90.pkl"

    def fake_train_final_model(data, best, *, output_dir):  # noqa: ANN001
        output_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "market": best["market"],
                "label": best["label"],
                "feature_set": best["feature_set"],
                "model_name": best["model"],
                "topn": best["topn"],
                "prob_threshold": best["prob_threshold"],
                "tail_risk_prob_threshold": best["tail_risk_prob_threshold"],
                "selection_rule": best["selection_rule"],
                "validation": {"metrics": best["metrics"]},
            },
            model_path,
        )
        return {"saved": True, "model_path": str(model_path), "train_rows": 10}

    monkeypatch.setattr(tool, "train_final_model", fake_train_final_model)
    monkeypatch.setattr(tool, "_example_exit_policy", lambda best: {"target_tp_pct": 5.0, "stop_sl_pct": -10.0, "hold_days": 5})
    best = {
        "market": "KOSDAQ",
        "label": "touch5_dd10_5d",
        "feature_set": "kis_sidecar_failure_risk_augmented",
        "model": "lightgbm",
        "topn": 2,
        "prob_threshold": 0.5,
        "tail_risk_prob_threshold": 0.9,
        "selection_rule": "top2_p0.50_tail0.90",
        "metrics": {"n": 40, "hit5_dd10_5d_pct": 100.0},
        "kis_model_gate": {"status": "shadow_ready", "shadow_display_allowed": True},
        "_source_report": "source.json",
    }

    result = tool._save_shadow_bundle(pd.DataFrame({"x": [1]}), best, model_dir=model_dir, profile_path=tmp_path / "profile.json")

    alias_path = tool._alias_path(model_dir, "KOSDAQ")
    assert result["alias_model_path"] == str(alias_path)
    assert alias_path.exists()
    model_bundle = joblib.load(model_path)
    alias_bundle = joblib.load(alias_path)
    assert alias_bundle["selection_rule"] == model_bundle["selection_rule"] == "top2_p0.50_tail0.90"
    assert alias_bundle["validation"]["metrics"]["hit5_dd10_5d_pct"] == 100.0
    assert alias_bundle["kis_model_gate"]["status"] == "shadow_ready"
