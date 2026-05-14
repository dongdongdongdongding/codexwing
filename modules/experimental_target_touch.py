"""Internal shadow testbed for target-before-stop win-rate definitions.

This module is intentionally not wired into production scanner ranking. It
defines the experimental outcome contract we want to validate before any
admission/rerank changes:

    Within N trading days, did price touch the target before touching stop?

Use it for offline labels, shadow reports, and regression tests only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import math
from typing import Any, Dict, Iterable, List, Sequence


EXPERIMENT_VERSION = "target_before_stop_shadow_v1"


@dataclass(frozen=True)
class TargetTouchPolicy:
    horizon_days: int = 5
    target_pct: float = 5.0
    stop_pct: float = 5.0
    include_entry_day: bool = False
    same_bar_policy: str = "stop_first"


def _safe_float(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def _bar_date(row: Dict[str, Any]) -> date | None:
    for key in ("date", "trade_date", "Date", "timestamp"):
        parsed = _parse_date(row.get(key))
        if parsed is not None:
            return parsed
    return None


def _normalize_bars(
    ohlcv_rows: Iterable[Dict[str, Any]],
    *,
    base_date: Any = None,
    include_entry_day: bool = False,
) -> List[Dict[str, Any]]:
    cutoff = _parse_date(base_date)
    rows: List[Dict[str, Any]] = []
    for idx, row in enumerate(ohlcv_rows or []):
        if not isinstance(row, dict):
            continue
        high = _safe_float(row.get("high") or row.get("High"))
        low = _safe_float(row.get("low") or row.get("Low"))
        close = _safe_float(row.get("close") or row.get("Close"))
        trade_date = _bar_date(row)
        if high is None or low is None:
            continue
        if cutoff is not None and trade_date is not None:
            if include_entry_day:
                if trade_date < cutoff:
                    continue
            elif trade_date <= cutoff:
                continue
        rows.append(
            {
                "date": trade_date.isoformat() if trade_date else str(row.get("date") or row.get("Date") or idx),
                "high": high,
                "low": low,
                "close": close,
                "_order": idx,
            }
        )
    rows.sort(key=lambda item: (item["date"], item["_order"]))
    return rows


def compute_target_before_stop_label(
    ohlcv_rows: Iterable[Dict[str, Any]],
    *,
    entry_price: Any,
    policy: TargetTouchPolicy | None = None,
    base_date: Any = None,
) -> Dict[str, Any]:
    """Compute the experimental target-before-stop label from forward OHLCV.

    Same-bar target and stop touches cannot be ordered with daily OHLCV. The
    default is deliberately conservative: stop first.
    """
    policy = policy or TargetTouchPolicy()
    entry = _safe_float(entry_price)
    warnings: List[str] = []
    if entry is None or entry <= 0:
        return {
            "label_version": EXPERIMENT_VERSION,
            "policy": asdict(policy),
            "entry_price": entry,
            "target_before_stop": None,
            "stop_before_target": None,
            "terminal_status": "invalid_entry_price",
            "warnings": ["invalid_entry_price"],
        }

    bars = _normalize_bars(
        ohlcv_rows,
        base_date=base_date,
        include_entry_day=bool(policy.include_entry_day),
    )[: max(0, int(policy.horizon_days))]
    if not bars:
        return {
            "label_version": EXPERIMENT_VERSION,
            "policy": asdict(policy),
            "entry_price": round(entry, 6),
            "target_before_stop": None,
            "stop_before_target": None,
            "terminal_status": "insufficient_forward_bars",
            "warnings": ["insufficient_forward_bars"],
        }

    target_price = entry * (1.0 + float(policy.target_pct) / 100.0)
    stop_price = entry * (1.0 - float(policy.stop_pct) / 100.0)
    mfe_pct: float | None = None
    mae_pct: float | None = None
    target_hit_at = None
    stop_hit_at = None
    terminal_status = "no_touch"
    target_before_stop: bool | None = False
    stop_before_target = False

    for bar in bars:
        high_ret = ((float(bar["high"]) / entry) - 1.0) * 100.0
        low_ret = ((float(bar["low"]) / entry) - 1.0) * 100.0
        mfe_pct = high_ret if mfe_pct is None else max(mfe_pct, high_ret)
        mae_pct = low_ret if mae_pct is None else min(mae_pct, low_ret)
        target_hit = float(bar["high"]) >= target_price
        stop_hit = float(bar["low"]) <= stop_price
        if target_hit and stop_hit:
            target_hit_at = str(bar["date"])
            stop_hit_at = str(bar["date"])
            warnings.append("same_bar_target_and_stop_touch")
            if str(policy.same_bar_policy).lower() == "target_first":
                terminal_status = "same_bar_target_first"
                target_before_stop = True
                stop_before_target = False
            else:
                terminal_status = "same_bar_stop_first"
                target_before_stop = False
                stop_before_target = True
            break
        if target_hit:
            target_hit_at = str(bar["date"])
            terminal_status = "target_before_stop"
            target_before_stop = True
            stop_before_target = False
            break
        if stop_hit:
            stop_hit_at = str(bar["date"])
            terminal_status = "stop_before_target"
            target_before_stop = False
            stop_before_target = True
            break

    return {
        "label_version": EXPERIMENT_VERSION,
        "policy": asdict(policy),
        "entry_price": round(entry, 6),
        "target_price": round(target_price, 6),
        "stop_price": round(stop_price, 6),
        "bars_observed": len(bars),
        "mfe_pct": round(float(mfe_pct), 6) if mfe_pct is not None else None,
        "mae_pct": round(float(mae_pct), 6) if mae_pct is not None else None,
        "target_hit_at": target_hit_at,
        "stop_hit_at": stop_hit_at,
        "target_before_stop": target_before_stop,
        "stop_before_target": stop_before_target,
        "terminal_status": terminal_status,
        "warnings": warnings,
    }


def derive_proxy_label_from_archive_row(
    row: Dict[str, Any],
    *,
    policy: TargetTouchPolicy | None = None,
) -> Dict[str, Any]:
    """Derive a shadow proxy from existing archive columns.

    This is weaker than OHLCV path-order labeling. If stop order is unavailable
    it returns ``target_before_stop=None`` and exposes a target-touch-only proxy
    so we do not accidentally treat incomplete data as production truth.
    """
    policy = policy or TargetTouchPolicy()
    high_touch = _safe_bool(row.get("hit_5pct_within_5d"))
    max_high = _safe_float(row.get("max_high_return_5d_pct") or row.get("max_return_observed_pct"))
    mae = _safe_float(row.get("mae_5d_low_pct") or row.get("min_return_observed_pct"))
    close_return = _safe_float(row.get(f"return_{int(policy.horizon_days)}d_pct") or row.get("return_5d_pct"))

    target_touch = high_touch if high_touch is not None else (max_high is not None and max_high >= policy.target_pct)
    stop_touch = None if mae is None else mae <= -abs(float(policy.stop_pct))
    target_before_stop = None
    stop_before_target = None
    status = "proxy_target_touch_only"
    warnings = ["stop_order_unavailable"]

    if target_touch is False and stop_touch is True:
        target_before_stop = False
        stop_before_target = True
        status = "proxy_stop_only"
        warnings = ["target_order_unavailable"]
    elif target_touch is False and stop_touch is False:
        target_before_stop = False
        stop_before_target = False
        status = "proxy_no_touch"
        warnings = []
    elif target_touch is True and stop_touch is False:
        status = "proxy_target_touch_no_stop_touch"
        warnings = ["target_order_unavailable"]
    elif target_touch is True and stop_touch is True:
        status = "proxy_target_and_stop_touch_order_unknown"
        warnings = ["target_stop_order_unavailable"]

    return {
        "label_version": EXPERIMENT_VERSION,
        "policy": asdict(policy),
        "target_touch_proxy": target_touch,
        "stop_touch_proxy": stop_touch,
        "target_before_stop": target_before_stop,
        "stop_before_target": stop_before_target,
        "terminal_status": status,
        "mfe_pct": max_high,
        "mae_pct": mae,
        "close_return_pct": close_return,
        "warnings": warnings,
    }


def summarize_shadow_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    group_keys: Sequence[str] = ("market", "scan_mode", "decision_bucket"),
    min_samples: int = 1,
) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        key = tuple(str(row.get(k) or "").strip() or "-" for k in group_keys)
        groups.setdefault(key, []).append(row)

    summaries: List[Dict[str, Any]] = []
    for key, group in groups.items():
        if len(group) < max(1, int(min_samples)):
            continue
        target_labels = [r.get("target_before_stop") for r in group if isinstance(r.get("target_before_stop"), bool)]
        target_proxy = [r.get("target_touch_proxy") for r in group if isinstance(r.get("target_touch_proxy"), bool)]
        stops = [r.get("stop_touch_proxy") for r in group if isinstance(r.get("stop_touch_proxy"), bool)]
        close_returns = [_safe_float(r.get("close_return_pct")) for r in group]
        mfe = [_safe_float(r.get("mfe_pct")) for r in group]
        mae = [_safe_float(r.get("mae_pct")) for r in group]

        def _avg(values: List[float | None]) -> float | None:
            clean = [float(v) for v in values if v is not None]
            return round(sum(clean) / len(clean), 6) if clean else None

        row = {name: key[idx] for idx, name in enumerate(group_keys)}
        row.update(
            {
                "n": len(group),
                "ordered_label_n": len(target_labels),
                "target_before_stop_win_pct": (
                    round(sum(1 for v in target_labels if v) / len(target_labels) * 100.0, 4)
                    if target_labels
                    else None
                ),
                "target_touch_proxy_n": len(target_proxy),
                "target_touch_proxy_pct": (
                    round(sum(1 for v in target_proxy if v) / len(target_proxy) * 100.0, 4)
                    if target_proxy
                    else None
                ),
                "stop_touch_proxy_n": len(stops),
                "stop_touch_proxy_pct": (
                    round(sum(1 for v in stops if v) / len(stops) * 100.0, 4) if stops else None
                ),
                "avg_close_return_pct": _avg(close_returns),
                "avg_mfe_pct": _avg(mfe),
                "avg_mae_pct": _avg(mae),
                "label_version": EXPERIMENT_VERSION,
            }
        )
        summaries.append(row)
    summaries.sort(key=lambda r: (str(r.get("market")), str(r.get("scan_mode")), str(r.get("decision_bucket"))))
    return summaries
