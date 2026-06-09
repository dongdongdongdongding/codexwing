from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping


PROFILE_VERSION = "close_failure_prior_profile_v1"
DEFAULT_PROFILE_PATH = Path("runtime_state/reports/learning/close_failure_prior_profile_latest.json")

CLOSE_FAILURE_RISK_GROUPS = (
    ("ticker", "ticker"),
    ("theme", "primary_theme"),
    ("kis_theme", "kis_theme_news_primary_theme"),
    ("kis_sector", "kis_stock_sector_name"),
    ("market", "market"),
)

CLOSE_FAILURE_RISK_METRICS = (
    "touch5_n",
    "failure_rate_pct",
    "clean_defense_rate_pct",
    "stop5_rate_pct",
    "avg_close_5d_pct",
    "avg_mfe_5d_pct",
    "avg_mae_5d_pct",
    "risk_score",
)

CLOSE_FAILURE_RISK_NUMERIC = tuple(
    f"close_failure_prior_{prefix}_{metric}"
    for prefix, _column in CLOSE_FAILURE_RISK_GROUPS
    for metric in CLOSE_FAILURE_RISK_METRICS
)

CLOSE_FAILURE_RISK_CATEGORICAL = tuple(
    f"close_failure_prior_{prefix}_risk_bucket"
    for prefix, _column in CLOSE_FAILURE_RISK_GROUPS
)


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except Exception:
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _normalize_key(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "UNKNOWN"


def risk_bucket(count: float, score: float | None) -> str:
    if count < 3 or score is None or not math.isfinite(float(score)):
        return "INSUFFICIENT_HISTORY"
    if score >= 80.0:
        return "EXTREME"
    if score >= 60.0:
        return "HIGH"
    if score >= 40.0:
        return "MODERATE"
    return "LOW"


def _pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator) * 100.0, 4)


def _avg(total: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(float(total) / float(denominator), 6)


def _series_numeric(df: Any, *columns: str) -> Any:
    import pandas as pd

    for column in columns:
        if column in df.columns:
            return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(index=df.index, dtype=float)


def _series_bool(df: Any, column: str) -> Any:
    import pandas as pd

    if column not in df.columns:
        return pd.Series(False, index=df.index)
    values = df[column]
    if values.dtype == bool:
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"1", "true", "t", "yes", "y"})


def _group_profile(frame: Any, group_col: str, *, min_touch_n: int = 1) -> Dict[str, Any]:
    import pandas as pd

    if group_col not in frame.columns:
        return {"values": {}, "groups": 0}
    grouped = frame.groupby(group_col, dropna=False, sort=True)
    values: Dict[str, Any] = {}
    for key, group in grouped:
        touch_n = float(group["touch"].sum())
        if touch_n < min_touch_n:
            continue
        failure_n = float(group["failure"].sum())
        clean_n = float(group["clean"].sum())
        stop_n = float(group["stop"].sum())
        failure_rate = _pct(failure_n, touch_n)
        clean_rate = _pct(clean_n, touch_n)
        stop_rate = _pct(stop_n, touch_n)
        risk_score = None
        if failure_rate is not None and clean_rate is not None and stop_rate is not None:
            risk_score = round(max(0.0, min(100.0, failure_rate * 0.7 + stop_rate * 0.35 - clean_rate * 0.25)), 4)
        normalized = _normalize_key(key)
        values[normalized] = {
            "touch5_n": int(touch_n),
            "failure_rate_pct": failure_rate,
            "clean_defense_rate_pct": clean_rate,
            "stop5_rate_pct": stop_rate,
            "avg_close_5d_pct": _avg(float(group["close_sum"].sum()), touch_n),
            "avg_mfe_5d_pct": _avg(float(group["mfe_sum"].sum()), touch_n),
            "avg_mae_5d_pct": _avg(float(group["mae_sum"].sum()), touch_n),
            "risk_score": risk_score,
            "risk_bucket": risk_bucket(touch_n, risk_score),
            "failure_n": int(failure_n),
            "clean_defense_n": int(clean_n),
            "stop5_n": int(stop_n),
        }
    return {"values": values, "groups": len(values)}


def build_close_failure_prior_profile(df: Any, *, source_path: str = "") -> Dict[str, Any]:
    """Build runtime-safe failure priors from resolved historical outcomes.

    The profile is intentionally aggregate-only. Runtime rows never read future
    labels; they only look up historical ticker/theme/sector priors persisted
    by this profile.
    """

    import pandas as pd

    if df is None or len(df) == 0:
        return {
            "version": PROFILE_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_path": source_path,
            "rows": 0,
            "groups": {},
        }
    out = df.copy()
    return1 = _series_numeric(out, "buy_premium_return_1d_pct", "return_1d_pct")
    return5 = _series_numeric(out, "buy_premium_return_5d_pct", "return_5d_pct")
    mfe5 = _series_numeric(out, "buy_premium_max_high_return_5d_pct", "max_high_return_5d_pct")
    mae5 = _series_numeric(out, "buy_premium_min_low_return_5d_pct", "min_low_return_5d_pct")
    touch = mfe5.ge(5.0).fillna(False) & return5.notna()
    stop = touch & mae5.le(-5.0).fillna(False)
    stop = stop | (touch & _series_bool(out, "stop_before_target_5d_bool")) | (touch & _series_bool(out, "stop_before_target_5d"))
    failure = touch & return5.lt(0.0).fillna(False)
    clean = touch & return5.gt(0.0).fillna(False) & mae5.gt(-5.0).fillna(False) & return1.ge(-3.0).fillna(False)
    frame = pd.DataFrame(index=out.index)
    frame["touch"] = touch.astype(float)
    frame["failure"] = failure.astype(float)
    frame["clean"] = clean.astype(float)
    frame["stop"] = stop.astype(float)
    frame["close_sum"] = return5.where(touch, 0.0).fillna(0.0)
    frame["mfe_sum"] = mfe5.where(touch, 0.0).fillna(0.0)
    frame["mae_sum"] = mae5.where(touch, 0.0).fillna(0.0)
    for _prefix, column in CLOSE_FAILURE_RISK_GROUPS:
        if column in out.columns:
            frame[column] = out[column].fillna("UNKNOWN").astype(str).str.strip().replace("", "UNKNOWN")

    groups: Dict[str, Any] = {}
    for prefix, column in CLOSE_FAILURE_RISK_GROUPS:
        groups[prefix] = _group_profile(frame, column)

    trade_dates = out.get("trade_date") if "trade_date" in out.columns else out.get("base_trade_date")
    return {
        "version": PROFILE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_path": source_path,
        "rows": int(len(out)),
        "touch5_rows": int(touch.sum()),
        "min_trade_date": str(trade_dates.min()) if trade_dates is not None and len(trade_dates.dropna()) else None,
        "max_trade_date": str(trade_dates.max()) if trade_dates is not None and len(trade_dates.dropna()) else None,
        "entry_assumption": {"buy_premium_pct": 2.0, "target_touch_pct": 5.0, "stop_pct": -5.0},
        "groups": groups,
    }


def write_close_failure_prior_profile(profile: Mapping[str, Any], path: Path = DEFAULT_PROFILE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(profile), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


@lru_cache(maxsize=4)
def load_close_failure_prior_profile(path: str | Path = DEFAULT_PROFILE_PATH) -> Dict[str, Any]:
    profile_path = Path(path)
    if not profile_path.exists():
        return {}
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _profile_metrics(profile: Mapping[str, Any], prefix: str, key: Any) -> Dict[str, Any]:
    groups = profile.get("groups") if isinstance(profile.get("groups"), Mapping) else {}
    block = groups.get(prefix) if isinstance(groups.get(prefix), Mapping) else {}
    values = block.get("values") if isinstance(block.get("values"), Mapping) else {}
    metrics = values.get(_normalize_key(key))
    return dict(metrics) if isinstance(metrics, Mapping) else {}


def _group_values(features: Mapping[str, Any], row: Mapping[str, Any]) -> Dict[str, Any]:
    ticker = row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("Symbol") or row.get("티커")
    market = features.get("market") or row.get("market") or row.get("Market")
    return {
        "ticker": ticker,
        "theme": features.get("primary_theme") or row.get("primary_theme") or row.get("theme"),
        "kis_theme": features.get("kis_theme_news_primary_theme"),
        "kis_sector": features.get("kis_stock_sector_name") or features.get("kis_theme_news_kis_sector_name"),
        "market": str(market or "").upper().strip(),
    }


def apply_close_failure_prior_profile_to_features(
    features: Mapping[str, Any],
    *,
    row: Mapping[str, Any],
    profile: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    out = dict(features)
    profile_payload = profile if isinstance(profile, Mapping) else load_close_failure_prior_profile()
    values = _group_values(out, row)
    for prefix, _column in CLOSE_FAILURE_RISK_GROUPS:
        metrics = _profile_metrics(profile_payload, prefix, values.get(prefix))
        count = _safe_float(metrics.get("touch5_n"), 0.0) or 0.0
        for metric in CLOSE_FAILURE_RISK_METRICS:
            out[f"close_failure_prior_{prefix}_{metric}"] = metrics.get(metric)
        score = _safe_float(metrics.get("risk_score"))
        out[f"close_failure_prior_{prefix}_touch5_n"] = count
        out[f"close_failure_prior_{prefix}_risk_bucket"] = metrics.get("risk_bucket") or risk_bucket(count, score)
    return out
