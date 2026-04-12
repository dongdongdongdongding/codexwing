from __future__ import annotations

import math
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models" / "kr_lane_champions"

CHAMPION_REGISTRY: Dict[str, Dict[str, Any]] = {
    # KOSPI core 1D: xgboost, AUC=0.589, win=80%, avg=3.1% — activated
    "kospi_core_1d": {
        "path": MODELS_DIR / "kospi_core_1d__xgboost.pkl",
        "enabled": True,
        "deployment": "active",
        "max_abs_adjustment": 3.0,
        "min_prob_edge": 0.10,
        "min_feature_evidence": 6,
    },
    # KOSPI core 3D: switched from catboost (AUC=0.36) to lightgbm (AUC=0.72, win=90%, avg=8.8%) — activated
    "kospi_core_3d": {
        "path": MODELS_DIR / "kospi_core_3d__lightgbm.pkl",
        "enabled": True,
        "deployment": "active",
        "max_abs_adjustment": 4.5,
        "min_prob_edge": 0.12,
        "min_feature_evidence": 7,
    },
    # KOSDAQ core 3D: hist_gb trained on 2 active days only — predictions inverted on test data, keep shadow
    "kosdaq_core_3d": {
        "path": MODELS_DIR / "kosdaq_core_3d__hist_gb.pkl",
        "enabled": True,
        "deployment": "shadow",
        "max_abs_adjustment": 0.0,
        "min_prob_edge": 0.10,
        "min_feature_evidence": 7,
    },
    # KOSDAQ explosive 1D: catboost, win=67.5%, avg=0.47% — downgraded to shadow (insufficient edge)
    "kosdaq_explosive_1d": {
        "path": MODELS_DIR / "kosdaq_explosive_1d__dense__catboost.pkl",
        "enabled": True,
        "deployment": "shadow",
        "max_abs_adjustment": 0.0,
        "min_prob_edge": 0.08,
        "min_feature_evidence": 6,
    },
    "kosdaq_core_1d": {
        "path": MODELS_DIR / "kosdaq_core_1d__logistic.pkl",
        "enabled": False,
        "deployment": "disabled",
        "max_abs_adjustment": 0.0,
        "min_prob_edge": 1.0,
        "min_feature_evidence": 999,
    },
}


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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _text(value).upper()


def _bool_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    return int(_text(value).lower() in {"1", "true", "yes"})


def _parse_volume_multiple(value: Any) -> float:
    text = _text(value).lower().replace("x", "").replace("✅", "").replace("⚠️", "").strip()
    try:
        return float(text)
    except Exception:
        return 0.0


def _parse_percent_text(value: Any) -> float:
    text = _text(value).replace("%", "").strip()
    try:
        return float(text)
    except Exception:
        return 0.0


def _tier_rank(value: Any) -> int:
    text = _upper(value)
    if "T0" in text:
        return 0
    if "T1" in text:
        return 1
    if "T2" in text:
        return 2
    if "T3" in text:
        return 3
    return 9


def _trend_signal(value: Any) -> int:
    text = _upper(value)
    if text == "UP":
        return 1
    if text == "DOWN":
        return -1
    return 0


def _fund_signal(value: Any) -> int:
    text = _upper(value)
    if text == "PASS":
        return 1
    if text == "FAIL":
        return -1
    return 0


def _get_feature(candidate: Dict[str, Any], key: str, default: Any = None) -> Any:
    if key in candidate and candidate.get(key) not in (None, ""):
        return candidate.get(key)
    snapshot = candidate.get("feature_snapshot", {}) if isinstance(candidate.get("feature_snapshot"), dict) else {}
    if key in snapshot and snapshot.get(key) not in (None, ""):
        return snapshot.get(key)
    return default


def _engineered_row(candidate: Dict[str, Any], market: str) -> Dict[str, Any]:
    market = _upper(market)
    role = _upper(_get_feature(candidate, "kr_universe_role"))
    scan_mode = _upper(_get_feature(candidate, "scan_mode"))
    strategy_family = _upper(_get_feature(candidate, "strategy_family", "KR_CORE" if market in {"KOSPI", "KOSDAQ"} else ""))
    entry_reference_price = _safe_float(_get_feature(candidate, "entry_reference_price", _get_feature(candidate, "current_price")), 0.0)
    alpha_score = _safe_float(_get_feature(candidate, "alpha_score"), 0.0)
    tech_score = _safe_float(_get_feature(candidate, "tech_score", alpha_score), alpha_score)
    ml_prob = _safe_float(_get_feature(candidate, "prob_5", _get_feature(candidate, "ml_prob")), 0.0)
    whale_score = _safe_float(_get_feature(candidate, "whale_score"), 0.0)
    decision_score = _safe_float(_get_feature(candidate, "decision_score", _get_feature(candidate, "score")), 0.0)
    volume_multiple = _parse_volume_multiple(_get_feature(candidate, "volume"))
    position = _text(_get_feature(candidate, "position"))
    trend = _upper(_get_feature(candidate, "real_trend", _get_feature(candidate, "trend")))
    strategy = _text(_get_feature(candidate, "strategy"))
    tier = _text(_get_feature(candidate, "tier"))
    fund_status = _text(_get_feature(candidate, "fund_status"))

    is_rising = int("Rising" in position)
    is_peak = int("Peak" in position)
    is_resting = int("Resting" in position)
    is_bottom = int("Bottom" in position)
    is_uptrend = int(trend == "UP")
    is_downtrend = int(trend == "DOWN")
    is_sideways = int(trend not in {"UP", "DOWN"})
    is_overheat = int(("단기과열" in strategy) or volume_multiple >= 2.5 or is_peak)
    is_rsidiv = int("RSI_DIV" in strategy)
    is_obvdiv = int("OBV_DIV" in strategy)
    is_momentum = int("Momentum" in strategy or (is_uptrend and not is_bottom))
    is_contract = int(any(token in strategy for token in ["공급계약", "계약", "수주"]))
    is_breakout = int(any(token in strategy for token in ["돌파", "Breakout", "Continuation"]) or is_rising)
    tier_rank = _tier_rank(tier)
    tier_t0 = int(tier_rank == 0)
    tier_t1 = int(tier_rank == 1)
    tier_t2 = int(tier_rank == 2)
    fund_positive = int(_fund_signal(fund_status) > 0)
    is_sub7 = int(entry_reference_price > 0 and entry_reference_price <= 7.0)
    price_7_15 = int(entry_reference_price > 7.0 and entry_reference_price <= 15.0)
    price_gt15 = int(entry_reference_price > 15.0)

    expected_return_1d_pct = _safe_float(_get_feature(candidate, "expected_return_1d_pct"), 0.0)
    expected_return_3d_pct = _safe_float(_get_feature(candidate, "expected_return_3d_pct"), 0.0)

    return {
        "alpha_score": alpha_score,
        "tech_score": tech_score,
        "ml_prob": ml_prob,
        "whale_score": whale_score,
        "decision_score": decision_score,
        "vol_float": volume_multiple,
        "vol_confirmed": int(volume_multiple >= 1.2),
        "vol_gt25x": int(volume_multiple > 2.5),
        "vol_18_25x": int(1.8 < volume_multiple <= 2.5),
        "vol_08_18x": int(0.8 <= volume_multiple <= 1.8),
        "vol_lt05x": int(volume_multiple < 0.5),
        "is_rising": is_rising,
        "is_peak": is_peak,
        "is_resting": is_resting,
        "is_bottom": is_bottom,
        "is_uptrend": is_uptrend,
        "is_downtrend": is_downtrend,
        "is_sideways": is_sideways,
        "is_overheat": is_overheat,
        "is_rsidiv": is_rsidiv,
        "is_obvdiv": is_obvdiv,
        "is_momentum": is_momentum,
        "is_contract": is_contract,
        "is_breakout": is_breakout,
        "tier_t0": tier_t0,
        "tier_t1": tier_t1,
        "tier_t2": tier_t2,
        "fund_positive": fund_positive,
        "is_sub7": is_sub7,
        "price_7_15": price_7_15,
        "price_gt15": price_gt15,
        "is_kospi": int(market == "KOSPI"),
        "is_kosdaq": int(market == "KOSDAQ"),
        "is_nasdaq": 0,
        "is_amex": 0,
        "scan_intraday": int(scan_mode == "INTRADAY"),
        "scan_swing": int(scan_mode == "SWING"),
        "fam_kr_core": int(strategy_family == "KR_CORE"),
        "fam_us_main": int(strategy_family == "US_MAIN"),
        "fam_amex_moonshot": int(strategy_family == "AMEX_MOONSHOT"),
        "peak_x_highvol": int(is_peak and volume_multiple > 2.5),
        "overheat_x_uptrend": int(is_overheat and is_uptrend),
        "sub7_x_breakout": int(is_sub7 and is_breakout),
        "phase25_shadow_prob": _safe_float(_get_feature(candidate, "phase25_shadow_prob"), 0.0),
        "phase25_recommended_threshold": _safe_float(_get_feature(candidate, "phase25_recommended_threshold"), 0.0),
        "expected_edge_score": _safe_float(_get_feature(candidate, "expected_edge_score"), 0.0),
        "expected_return_1d_pct": expected_return_1d_pct,
        "expected_return_3d_pct": expected_return_3d_pct,
        "target_horizon_days": _safe_float(_get_feature(candidate, "target_horizon_days", 1 if scan_mode == "INTRADAY" else 3), 3.0),
        "entry_reference_price": entry_reference_price,
        "explosive_eligible": _bool_int(_get_feature(candidate, "explosive_eligible", int(role == "EXPLOSIVE_LEADER"))),
        "explosive_leader_flag": int(role == "EXPLOSIVE_LEADER"),
        "core_trend_flag": int(role == "CORE_TREND"),
        "trend_signal": _trend_signal(trend),
        "fund_pass_signal": _fund_signal(fund_status),
        "tier_rank": tier_rank,
        "volume_multiple": volume_multiple,
        "textual_win_rate_pct": _parse_percent_text(_get_feature(candidate, "win_rate")),
        "secondary_theme_count": len(_get_feature(candidate, "secondary_themes", []) or []) if isinstance(_get_feature(candidate, "secondary_themes", []), list) else 0,
        "explosive_gate_reason_count": len(_get_feature(candidate, "explosive_gate_reasons", []) or []) if isinstance(_get_feature(candidate, "explosive_gate_reasons", []), list) else 0,
        "theme_present": int(_text(_get_feature(candidate, "primary_theme")) != ""),
        "expected_return_gap_3d_1d": expected_return_3d_pct - expected_return_1d_pct,
        "decision_alpha_gap": decision_score - alpha_score,
        "ml_whale_combo": (ml_prob + whale_score) / 2.0,
        "scan_mode": scan_mode or "UNKNOWN",
        "strategy_family": strategy_family or "UNKNOWN",
        "phase25_variant": _text(_get_feature(candidate, "phase25_variant")) or "UNKNOWN",
        "phase25_shadow_variant": _text(_get_feature(candidate, "phase25_shadow_variant")) or "UNKNOWN",
        "primary_theme": _text(_get_feature(candidate, "primary_theme")) or "UNKNOWN",
        "theme_source": _text(_get_feature(candidate, "theme_source")) or "UNKNOWN",
        "theme_inference_status": _text(_get_feature(candidate, "theme_inference_status")) or "UNKNOWN",
        "theme_routing_path": _text(_get_feature(candidate, "theme_routing_path", _get_feature(candidate, "routing_path"))) or "UNKNOWN",
        "selection_lane": _text(_get_feature(candidate, "selection_lane")) or "UNKNOWN",
        "scanner_timeframe_profile": _text(_get_feature(candidate, "scanner_timeframe_profile")) or "UNKNOWN",
        "kr_universe_role": role or "UNKNOWN",
        "trend": trend or "UNKNOWN",
        "fund_status": fund_status or "UNKNOWN",
        "tier": tier or "UNKNOWN",
        "position": position or "UNKNOWN",
        "price_band": "le_7" if is_sub7 else ("7_15" if price_7_15 else ("gt_15" if price_gt15 else "unknown")),
    }


def _feature_evidence_count(row: Dict[str, Any]) -> int:
    strong_numeric = [
        "alpha_score",
        "tech_score",
        "ml_prob",
        "decision_score",
        "volume_multiple",
        "expected_return_1d_pct",
        "expected_return_3d_pct",
        "expected_edge_score",
        "phase25_shadow_prob",
        "phase25_recommended_threshold",
    ]
    strong_text = [
        "scan_mode",
        "strategy_family",
        "phase25_variant",
        "primary_theme",
        "theme_routing_path",
        "kr_universe_role",
        "trend",
        "position",
    ]
    evidence = 0
    for key in strong_numeric:
        value = row.get(key)
        if isinstance(value, (int, float)) and not math.isnan(float(value)) and float(value) != 0.0:
            evidence += 1
    for key in strong_text:
        value = _upper(row.get(key))
        if value and value != "UNKNOWN":
            evidence += 1
    return evidence


def _segment_for(market: str, role: str, horizon: str) -> Optional[str]:
    market_name = _upper(market)
    role_name = _upper(role)
    horizon_name = _text(horizon).lower()
    if market_name == "KOSPI" and role_name == "CORE_TREND" and horizon_name == "1d":
        return "kospi_core_1d"
    if market_name == "KOSPI" and role_name == "CORE_TREND" and horizon_name == "3d":
        return "kospi_core_3d"
    if market_name == "KOSDAQ" and role_name == "CORE_TREND" and horizon_name == "3d":
        return "kosdaq_core_3d"
    if market_name == "KOSDAQ" and role_name == "EXPLOSIVE_LEADER" and horizon_name == "1d":
        return "kosdaq_explosive_1d"
    if market_name == "KOSDAQ" and role_name == "CORE_TREND" and horizon_name == "1d":
        return "kosdaq_core_1d"
    return None


@lru_cache(maxsize=16)
def _load_bundle(path_str: str) -> Dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        return {}
    try:
        loaded = joblib.load(path)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def predict_lane_overlay(candidate: Dict[str, Any], market: str, horizon: str) -> Dict[str, Any]:
    role = _upper(_get_feature(candidate, "kr_universe_role"))
    segment = _segment_for(market, role, horizon)
    if not segment:
        return {"enabled": False, "segment": None, "score_adjustment": 0.0}

    registry = CHAMPION_REGISTRY.get(segment) or {}
    if not registry.get("enabled", False):
        return {"enabled": False, "segment": segment, "score_adjustment": 0.0, "reason": "DISABLED_SEGMENT"}
    deployment = str(registry.get("deployment") or "active").lower()
    if deployment != "active":
        return {
            "enabled": False,
            "segment": segment,
            "score_adjustment": 0.0,
            "deployment": deployment,
            "reason": f"DEPLOYMENT_{deployment.upper()}",
        }

    bundle = _load_bundle(str(registry["path"]))
    if not bundle:
        return {"enabled": False, "segment": segment, "score_adjustment": 0.0, "reason": "MODEL_NOT_FOUND"}

    row = _engineered_row(candidate, market)
    feature_evidence = _feature_evidence_count(row)
    min_feature_evidence = int(registry.get("min_feature_evidence", 0) or 0)
    if feature_evidence < min_feature_evidence:
        return {
            "enabled": False,
            "segment": segment,
            "score_adjustment": 0.0,
            "deployment": deployment,
            "feature_evidence": feature_evidence,
            "reason": f"FEATURE_EVIDENCE_LT_{min_feature_evidence}",
        }
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Skipping features without any observed values")
            if "pipeline" in bundle:
                features_numeric = list(bundle.get("features_numeric", []) or [])
                features_categorical = list(bundle.get("features_categorical", []) or [])
                cols = features_numeric + features_categorical
                X = pd.DataFrame([{col: row.get(col) for col in cols}])
                prob = float(bundle["pipeline"].predict_proba(X)[0][1])
                metrics = dict(bundle.get("holdout_metrics", {}) or {})
            else:
                features = list(bundle.get("features", []) or [])
                X = pd.DataFrame([{col: row.get(col, 0.0) for col in features}]).apply(pd.to_numeric, errors="coerce").fillna(0.0)
                prob = float(bundle["model"].predict_proba(X)[0][1])
                metrics = dict(bundle.get("metrics", {}) or {})
    except Exception as exc:
        return {
            "enabled": False,
            "segment": segment,
            "score_adjustment": 0.0,
            "reason": f"PREDICT_ERROR:{type(exc).__name__}",
        }

    avg_return = _safe_float(metrics.get("avg_return_pct"), 0.0)
    win_rate = _safe_float(metrics.get("win_rate_pct"), 0.0)
    target_gap = _safe_float(metrics.get("target_gap"), 1.0)
    quality = max(0.15, min(1.0, 1.0 - target_gap))
    prob_edge = abs(prob - 0.5)
    min_prob_edge = float(registry.get("min_prob_edge", 0.0) or 0.0)
    if prob_edge < min_prob_edge:
        return {
            "enabled": False,
            "segment": segment,
            "score_adjustment": 0.0,
            "deployment": deployment,
            "feature_evidence": feature_evidence,
            "prob_up": round(prob * 100.0, 1),
            "quality": round(quality, 4),
            "reason": f"PROB_EDGE_LT_{min_prob_edge:.2f}",
        }
    max_abs = float(registry.get("max_abs_adjustment", 0.0) or 0.0)
    raw_adjustment = (prob - 0.5) * max_abs * 2.0
    if avg_return > 0.0 and win_rate >= 75.0:
        raw_adjustment += 0.8
    score_adjustment = max(-max_abs, min(max_abs, raw_adjustment * quality))
    return {
        "enabled": True,
        "segment": segment,
        "model_name": str(metrics.get("model") or bundle.get("segment") or segment),
        "prob_up": round(prob * 100.0, 1),
        "avg_return_pct": round(avg_return, 4),
        "win_rate_pct": round(win_rate, 4),
        "target_gap": round(target_gap, 6),
        "quality": round(quality, 4),
        "deployment": deployment,
        "feature_evidence": feature_evidence,
        "score_adjustment": round(score_adjustment, 2),
    }
