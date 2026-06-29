#!/usr/bin/env python3
"""Build a recent NASDAQ session panel and search session-aware swing edges.

yfinance only exposes recent intraday bars, so this is explicitly a short-window
shadow research tool. It separates premarket, regular-open, regular-close, and
afterhours entries instead of treating all NASDAQ scans as one EOD signal.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.research_nasdaq_daily_edge import DEFAULT_PANEL
from multi_agent.tools.research_nasdaq_production_edge import (
    PROMOTION_GATE_THRESHOLDS,
    evaluate_nasdaq_promotion_gate,
)

REPORT_VERSION = "nasdaq_session_edge_search_v1"
DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"
DEFAULT_CACHE_DIR = DEFAULT_OUT_DIR / "nasdaq_session_5m_cache"
DEFAULT_RAW_OHLCV_DIR = Path("/Users/dongdong/research_cache/us_daily/NASDAQ/raw_ohlcv")
SESSION_MODES = ("premarket", "regular_open", "regular_close", "afterhours")

DAILY_CONTEXT_COLUMNS = [
    "date",
    "symbol",
    "name",
    "close",
    "liq20",
    "liq60",
    "feature_ready",
    "ret_5d",
    "ret_20d",
    "ret_60d",
    "atr_pct",
    "vol20",
    "vol_ratio",
    "rsi14",
    "ma60_slope",
    "ma200_slope",
    "dist_hi20",
    "dist_hi120",
]


@dataclass(frozen=True)
class SessionWindow:
    mode: str
    start_minute: int
    end_minute: int


WINDOWS = {
    "premarket": SessionWindow("premarket", 4 * 60, 9 * 60 + 30),
    "regular_open": SessionWindow("regular_open", 9 * 60 + 30, 10 * 60 + 30),
    "regular_close": SessionWindow("regular_close", 9 * 60 + 30, 16 * 60),
    "afterhours": SessionWindow("afterhours", 16 * 60, 20 * 60),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except Exception:
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _round(value: Any, digits: int = 6) -> Optional[float]:
    out = _finite(value)
    return None if out is None else round(out, digits)


def _mean_ci(values: pd.Series) -> List[Optional[float]]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return [None, None]
    if len(clean) < 2:
        value = round(float(clean.mean()), 6)
        return [value, value]
    mean = float(clean.mean())
    se = float(clean.std(ddof=1) / math.sqrt(len(clean)))
    return [round(mean - 1.96 * se, 6), round(mean + 1.96 * se, 6)]


def _read_daily_context(path: Path) -> pd.DataFrame:
    try:
        import pyarrow.parquet as pq

        available = set(pq.ParquetFile(path).schema.names)
        columns = [col for col in DAILY_CONTEXT_COLUMNS if col in available]
    except Exception:
        columns = DAILY_CONTEXT_COLUMNS
    df = pd.read_parquet(path, columns=columns)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    for col in [c for c in df.columns if c not in {"date", "symbol", "name"}]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "name" not in df.columns:
        df["name"] = df["symbol"]
    df = df.dropna(subset=["date", "symbol", "close", "liq20"])
    df = df[df.get("feature_ready", 1).eq(1)].copy()
    df = df.sort_values(["symbol", "date"], kind="mergesort")
    df["prev_daily_close"] = df.groupby("symbol", observed=True)["close"].shift(1)
    return df


def select_symbols(daily: pd.DataFrame, max_symbols: int, min_liq20: float) -> List[str]:
    latest_date = daily["date"].max()
    latest = daily[daily["date"].eq(latest_date) & daily["liq20"].ge(float(min_liq20))].copy()
    latest = latest.sort_values("liq20", ascending=False, kind="mergesort")
    return [str(sym) for sym in latest["symbol"].head(int(max_symbols)).tolist()]


def _fetch_yfinance_5m(symbol: str, *, period: str, interval: str, timeout: int) -> pd.DataFrame:
    import yfinance as yf

    hist = yf.Ticker(symbol).history(
        period=period,
        interval=interval,
        prepost=True,
        auto_adjust=False,
        actions=False,
        timeout=timeout,
    )
    if hist is None or hist.empty:
        return pd.DataFrame()
    return hist


def load_or_fetch_intraday(
    symbol: str,
    *,
    cache_dir: Path,
    period: str,
    interval: str,
    timeout: int,
    refresh: bool,
    fetch: bool,
) -> Tuple[pd.DataFrame, str, Optional[str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{symbol}.parquet"
    if cache_path.exists() and not refresh:
        try:
            return pd.read_parquet(cache_path), "cache", None
        except Exception as exc:
            if not fetch:
                return pd.DataFrame(), "cache_error", str(exc)
    if not fetch:
        return pd.DataFrame(), "missing_cache", "cache file missing and fetch disabled"
    try:
        frame = _fetch_yfinance_5m(symbol, period=period, interval=interval, timeout=timeout)
        if not frame.empty:
            frame.to_parquet(cache_path, index=True)
        return frame, "yfinance", None
    except Exception as exc:
        return pd.DataFrame(), "fetch_error", str(exc)


def _minute_of_day(ts: pd.Series) -> pd.Series:
    return ts.dt.hour * 60 + ts.dt.minute


def _slice_window(frame: pd.DataFrame, window: SessionWindow) -> pd.DataFrame:
    return frame[frame["minute"].ge(window.start_minute) & frame["minute"].lt(window.end_minute)]


def _session_stats(frame: pd.DataFrame) -> Optional[Dict[str, float]]:
    if frame.empty:
        return None
    frame = frame.sort_values("ny_ts", kind="mergesort")
    close = pd.to_numeric(frame["Close"], errors="coerce")
    high = pd.to_numeric(frame["High"], errors="coerce")
    low = pd.to_numeric(frame["Low"], errors="coerce")
    volume = pd.to_numeric(frame["Volume"], errors="coerce").fillna(0.0)
    open_ = pd.to_numeric(frame["Open"], errors="coerce")
    if close.dropna().empty or open_.dropna().empty:
        return None
    dollar_volume = float((close.ffill().fillna(0.0) * volume).sum())
    session_low = float(low.min())
    session_high = float(high.max())
    range_pct = ((session_high / session_low) - 1.0) * 100.0 if session_low > 0 else np.nan
    close_loc = (float(close.iloc[-1]) - session_low) / (session_high - session_low) if session_high > session_low else 0.5
    return {
        "open": float(open_.iloc[0]),
        "high": session_high,
        "low": session_low,
        "close": float(close.iloc[-1]),
        "volume": float(volume.sum()),
        "dollar_volume": dollar_volume,
        "range_pct": float(range_pct),
        "close_loc": float(close_loc),
        "bars": int(len(frame)),
    }


def _daily_lookup(daily: pd.DataFrame, symbols: Sequence[str]) -> Dict[Tuple[str, pd.Timestamp], Dict[str, Any]]:
    subset = daily[daily["symbol"].isin(symbols)].copy()
    out: Dict[Tuple[str, pd.Timestamp], Dict[str, Any]] = {}
    for row in subset.to_dict("records"):
        out[(str(row["symbol"]), pd.Timestamp(row["date"]).normalize())] = row
    return out


def _load_raw_daily(symbol: str, raw_dir: Path) -> pd.DataFrame:
    path = raw_dir / f"{symbol}.parquet"
    if not path.exists():
        return pd.DataFrame()
    raw = pd.read_parquet(path)
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce").dt.normalize()
    for col in ("open", "high", "low", "close", "volume"):
        if col in raw.columns:
            raw[col] = pd.to_numeric(raw[col], errors="coerce")
    return raw.dropna(subset=["date", "close"]).sort_values("date", kind="mergesort")


def _ordered_first_touch(window: pd.DataFrame, entry_price: float) -> Tuple[float, float]:
    target = entry_price * 1.05
    stop = entry_price * 0.95
    ambiguous = 0.0
    for _, row in window.iterrows():
        hit_stop = _finite(row.get("low")) is not None and float(row["low"]) <= stop
        hit_target = _finite(row.get("high")) is not None and float(row["high"]) >= target
        if hit_stop and hit_target:
            ambiguous = 1.0
            return 0.0, ambiguous
        if hit_stop:
            return 0.0, ambiguous
        if hit_target:
            return 1.0, ambiguous
    return 0.0, ambiguous


def _outcome_from_raw_daily(
    raw: pd.DataFrame,
    date: pd.Timestamp,
    *,
    entry_price: float,
    include_current_date: bool,
) -> Optional[Dict[str, float]]:
    if raw.empty or not math.isfinite(float(entry_price)) or entry_price <= 0:
        return None
    dates = list(raw["date"])
    date = pd.Timestamp(date).normalize()
    matches = [idx for idx, value in enumerate(dates) if value == date]
    if not matches:
        return None
    start = matches[0] if include_current_date else matches[0] + 1
    window = raw.iloc[start : start + 5].copy()
    if len(window) < 5:
        return None
    first3 = window.iloc[:3]
    close3 = float(first3.iloc[-1]["close"])
    close5 = float(window.iloc[-1]["close"])
    high3 = float(first3["high"].max())
    high5 = float(window["high"].max())
    low3 = float(first3["low"].min())
    low5 = float(window["low"].min())
    ft55, ambiguous = _ordered_first_touch(window, float(entry_price))
    return {
        "fwd_close_ret_3d": ((close3 / entry_price) - 1.0) * 100.0,
        "fwd_close_ret_5d": ((close5 / entry_price) - 1.0) * 100.0,
        "fwd_high_ret_3d": ((high3 / entry_price) - 1.0) * 100.0,
        "fwd_high_ret_5d": ((high5 / entry_price) - 1.0) * 100.0,
        "fwd_low_ret_3d": ((low3 / entry_price) - 1.0) * 100.0,
        "fwd_low_ret_5d": ((low5 / entry_price) - 1.0) * 100.0,
        "touch5_3d": float(((high3 / entry_price) - 1.0) >= 0.05),
        "touch5_5d": float(((high5 / entry_price) - 1.0) >= 0.05),
        "dd5_3d": float(((low3 / entry_price) - 1.0) <= -0.05),
        "dd5_5d": float(((low5 / entry_price) - 1.0) <= -0.05),
        "ft_5_5": ft55,
        "same_day_touch_stop_ambiguous": ambiguous,
    }


def aggregate_symbol_sessions(
    symbol: str,
    intraday: pd.DataFrame,
    *,
    daily_rows: Mapping[Tuple[str, pd.Timestamp], Mapping[str, Any]],
    raw_daily: pd.DataFrame,
) -> List[Dict[str, Any]]:
    if intraday.empty:
        return []
    frame = intraday.copy()
    if "Datetime" in frame.columns:
        frame = frame.set_index("Datetime")
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame[frame.index.notna()].copy()
    if frame.empty:
        return []
    if frame.index.tz is None:
        ny_ts = frame.index.tz_localize("UTC").tz_convert("America/New_York")
    else:
        ny_ts = frame.index.tz_convert("America/New_York")
    frame["ny_ts"] = pd.Series(ny_ts, index=frame.index)
    frame["date"] = frame["ny_ts"].dt.normalize().dt.tz_localize(None)
    frame["minute"] = _minute_of_day(frame["ny_ts"])

    rows: List[Dict[str, Any]] = []
    for date, group in frame.groupby("date", observed=True):
        date = pd.Timestamp(date).normalize()
        context = daily_rows.get((symbol, date))
        if not context:
            continue
        prev_close = _finite(context.get("prev_daily_close"))
        if prev_close is None or prev_close <= 0:
            continue
        pre = _session_stats(_slice_window(group, WINDOWS["premarket"]))
        open60 = _session_stats(_slice_window(group, WINDOWS["regular_open"]))
        regular = _session_stats(_slice_window(group, WINDOWS["regular_close"]))
        after = _session_stats(_slice_window(group, WINDOWS["afterhours"]))
        session_map = {
            "premarket": pre,
            "regular_open": open60,
            "regular_close": regular,
            "afterhours": after,
        }
        regular_volume = (regular or {}).get("volume") or 0.0
        regular_close = (regular or {}).get("close")
        for mode, stats in session_map.items():
            if not stats:
                continue
            if mode == "premarket":
                entry = stats["close"]
                session_ret = ((entry / prev_close) - 1.0) * 100.0
                anchor_ret = session_ret
                include_current = True
            elif mode == "regular_open":
                entry = stats["close"]
                session_ret = ((entry / stats["open"]) - 1.0) * 100.0
                anchor_ret = ((entry / prev_close) - 1.0) * 100.0
                include_current = True
            elif mode == "regular_close":
                entry = stats["close"]
                session_ret = ((entry / stats["open"]) - 1.0) * 100.0
                anchor_ret = ((entry / prev_close) - 1.0) * 100.0
                include_current = False
            else:
                if regular_close is None or regular_close <= 0:
                    continue
                entry = stats["close"]
                session_ret = ((entry / float(regular_close)) - 1.0) * 100.0
                anchor_ret = ((entry / prev_close) - 1.0) * 100.0
                include_current = False
            outcome = _outcome_from_raw_daily(
                raw_daily,
                date,
                entry_price=float(entry),
                include_current_date=include_current,
            )
            if not outcome:
                continue
            row: Dict[str, Any] = {
                "date": date,
                "symbol": symbol,
                "name": context.get("name") or symbol,
                "session_mode": mode,
                "entry_price": float(entry),
                "prev_daily_close": float(prev_close),
                "session_ret": float(session_ret),
                "anchor_ret": float(anchor_ret),
                "session_range_pct": stats["range_pct"],
                "session_close_loc": stats["close_loc"],
                "session_volume": stats["volume"],
                "session_dollar_volume": stats["dollar_volume"],
                "session_volume_share_regular": (
                    float(stats["volume"] / regular_volume) if regular_volume and regular_volume > 0 else np.nan
                ),
                "session_bars": stats["bars"],
                "liq20": _finite(context.get("liq20")),
                "liq60": _finite(context.get("liq60")),
                "ret_5d": _finite(context.get("ret_5d")),
                "ret_20d": _finite(context.get("ret_20d")),
                "ret_60d": _finite(context.get("ret_60d")),
                "atr_pct": _finite(context.get("atr_pct")),
                "vol_ratio": _finite(context.get("vol_ratio")),
                "rsi14": _finite(context.get("rsi14")),
                "ma60_slope": _finite(context.get("ma60_slope")),
                "ma200_slope": _finite(context.get("ma200_slope")),
                "dist_hi20": _finite(context.get("dist_hi20")),
                "dist_hi120": _finite(context.get("dist_hi120")),
                **outcome,
            }
            rows.append(row)
    return rows


def build_session_panel(
    *,
    daily: pd.DataFrame,
    symbols: Sequence[str],
    cache_dir: Path,
    raw_dir: Path,
    period: str,
    interval: str,
    timeout: int,
    refresh: bool,
    fetch: bool,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    daily_rows = _daily_lookup(daily, symbols)
    rows: List[Dict[str, Any]] = []
    fetch_stats = {"symbols_requested": len(symbols), "sources": {}, "errors": {}}
    for symbol in symbols:
        intraday, source, error = load_or_fetch_intraday(
            symbol,
            cache_dir=cache_dir,
            period=period,
            interval=interval,
            timeout=timeout,
            refresh=refresh,
            fetch=fetch,
        )
        fetch_stats["sources"][source] = int(fetch_stats["sources"].get(source, 0)) + 1
        if error:
            fetch_stats["errors"][symbol] = error[:500]
            continue
        raw_daily = _load_raw_daily(symbol, raw_dir)
        if raw_daily.empty:
            fetch_stats["errors"][symbol] = "missing_raw_daily"
            continue
        rows.extend(aggregate_symbol_sessions(symbol, intraday, daily_rows=daily_rows, raw_daily=raw_daily))
    panel = pd.DataFrame(rows)
    if not panel.empty:
        panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.normalize()
        panel = panel.dropna(subset=["date", "symbol", "session_mode", "entry_price", "fwd_close_ret_5d"])
    fetch_stats["rows"] = int(len(panel))
    fetch_stats["symbols_with_rows"] = int(panel["symbol"].nunique()) if not panel.empty else 0
    fetch_stats["date_min"] = str(panel["date"].min().date()) if not panel.empty else None
    fetch_stats["date_max"] = str(panel["date"].max().date()) if not panel.empty else None
    return panel, fetch_stats


def add_ranks_and_alpha(panel: pd.DataFrame) -> pd.DataFrame:
    if panel.empty:
        return panel.copy()
    out = panel.copy()
    out["liq_bucket"] = (
        out.groupby(["date", "session_mode"], observed=True)["liq20"].rank(pct=True, ascending=True).fillna(0.0) * 5
    ).clip(0, 4).astype(int)
    base = out.groupby(["date", "session_mode", "liq_bucket"], observed=True)["fwd_close_ret_5d"].mean()
    out = out.join(base.rename("base_session_liq_ret5"), on=["date", "session_mode", "liq_bucket"])
    out["alpha5_session_liq"] = out["fwd_close_ret_5d"] - out["base_session_liq_ret5"]
    out["alpha5_net"] = out["alpha5_session_liq"] - 0.20

    rank_cols = [
        "session_ret",
        "anchor_ret",
        "session_range_pct",
        "session_close_loc",
        "session_dollar_volume",
        "session_volume_share_regular",
        "liq20",
        "ret_5d",
        "ret_20d",
        "ret_60d",
        "atr_pct",
        "vol_ratio",
        "rsi14",
        "ma60_slope",
        "ma200_slope",
        "dist_hi20",
        "dist_hi120",
    ]
    group = [out["date"], out["session_mode"]]
    for col in rank_cols:
        if col not in out.columns:
            continue
        rank = pd.to_numeric(out[col], errors="coerce").groupby(group).rank(pct=True, ascending=True)
        out[f"r_{col}"] = rank
        out[f"ir_{col}"] = 1.0 - rank

    def r(col: str) -> pd.Series:
        return pd.to_numeric(out[col], errors="coerce").fillna(0.0) if col in out.columns else pd.Series(0.0, index=out.index)

    out["score_session_momentum"] = (
        r("r_session_ret")
        + r("r_session_dollar_volume")
        + r("r_session_close_loc")
        + r("r_ret_20d")
        + r("r_ma200_slope")
    )
    out["score_session_calm_strength"] = (
        r("r_session_ret")
        + r("r_session_dollar_volume")
        + r("r_session_close_loc")
        + r("ir_session_range_pct")
        + r("r_ret_60d")
    )
    out["score_session_reversal"] = (
        r("ir_session_ret")
        + r("r_session_dollar_volume")
        + r("r_ret_20d")
        + r("r_ma200_slope")
        + r("ir_rsi14")
    )
    out["score_liquid_open_drive"] = (
        r("r_anchor_ret")
        + r("r_session_dollar_volume")
        + r("r_liq20")
        + r("r_vol_ratio")
        + r("r_dist_hi20")
    )
    return out


def _condition_specs() -> List[Tuple[str, str, Tuple[Tuple[str, float], ...]]]:
    raw: List[Tuple[str, str, Sequence[Tuple[str, float]]]] = [
        ("premarket_gap_volume", "premarket", [("r_session_ret", 0.70), ("r_session_dollar_volume", 0.70)]),
        ("premarket_calm_gap", "premarket", [("r_session_ret", 0.70), ("ir_session_range_pct", 0.50)]),
        ("premarket_reversal_volume", "premarket", [("ir_session_ret", 0.70), ("r_session_dollar_volume", 0.70)]),
        ("regular_open_drive", "regular_open", [("r_session_ret", 0.70), ("r_session_dollar_volume", 0.70)]),
        ("regular_open_liquid_drive", "regular_open", [("r_anchor_ret", 0.70), ("r_liq20", 0.70)]),
        ("regular_close_strength", "regular_close", [("r_session_ret", 0.70), ("r_session_close_loc", 0.70)]),
        ("regular_close_liquid_trend", "regular_close", [("r_session_ret", 0.60), ("r_liq20", 0.70), ("r_ret_20d", 0.60)]),
        (
            "regular_close_strength_liq_trend",
            "regular_close",
            [("r_session_ret", 0.55), ("r_session_close_loc", 0.65), ("r_liq20", 0.75), ("r_ret_20d", 0.75)],
        ),
        (
            "regular_close_strength_liq_ma200",
            "regular_close",
            [("r_session_ret", 0.55), ("r_session_close_loc", 0.65), ("r_liq20", 0.75), ("r_ma200_slope", 0.55)],
        ),
        (
            "regular_close_core_close_ma200",
            "regular_close",
            [("r_liq20", 0.70), ("r_ret_20d", 0.60), ("r_session_close_loc", 0.65), ("r_ma200_slope", 0.55)],
        ),
        (
            "regular_close_core_close_trend",
            "regular_close",
            [("r_liq20", 0.70), ("r_ret_20d", 0.75), ("r_session_close_loc", 0.65)],
        ),
        (
            "regular_close_core_ma200",
            "regular_close",
            [("r_liq20", 0.70), ("r_ret_20d", 0.60), ("r_ma200_slope", 0.65)],
        ),
        ("afterhours_positive_volume", "afterhours", [("r_session_ret", 0.70), ("r_session_dollar_volume", 0.70)]),
        ("afterhours_calm_positive", "afterhours", [("r_session_ret", 0.70), ("ir_session_range_pct", 0.50)]),
        ("afterhours_reversal_volume", "afterhours", [("ir_session_ret", 0.70), ("r_session_dollar_volume", 0.70)]),
    ]
    return [(name, mode, tuple(specs)) for name, mode, specs in raw]


def _mask(frame: pd.DataFrame, specs: Sequence[Tuple[str, float]]) -> np.ndarray:
    mask = np.ones(len(frame), dtype=bool)
    for col, threshold in specs:
        if col not in frame.columns:
            return np.zeros(len(frame), dtype=bool)
        mask &= pd.to_numeric(frame[col], errors="coerce").ge(float(threshold)).to_numpy()
    return mask


def _ranked_pick(frame: pd.DataFrame, score_col: str, topn: int) -> pd.DataFrame:
    if frame.empty:
        return frame
    ranked = (
        frame.sort_values(["date", score_col], ascending=[True, False], kind="mergesort")
        .assign(_rank=lambda data: data.groupby("date", observed=True).cumcount() + 1)
    )
    return ranked[ranked["_rank"].le(int(topn))].drop(columns=["_rank"])


def metric_block(frame: pd.DataFrame) -> Dict[str, Any]:
    if frame.empty:
        return {"n": 0, "days": 0, "symbols": 0, "annual": []}
    out: Dict[str, Any] = {
        "n": int(len(frame)),
        "days": int(frame["date"].nunique()),
        "symbols": int(frame["symbol"].nunique()),
        "ret5": _round(frame["fwd_close_ret_5d"].mean()),
        "ret5_ci95": _mean_ci(frame["fwd_close_ret_5d"]),
        "ret5_pos_rate": _round(pd.to_numeric(frame["fwd_close_ret_5d"], errors="coerce").gt(0.0).mean()),
        "alpha5_net_cost_0_2": _round(frame["alpha5_net"].mean()),
        "alpha5_net_cost_0_2_ci95": _mean_ci(frame["alpha5_net"]),
        "alpha5_net_cost_0_2_pos_rate": _round(pd.to_numeric(frame["alpha5_net"], errors="coerce").gt(0.0).mean()),
        "touch3": _round(frame["touch5_3d"].mean()),
        "touch3_ci95": _mean_ci(frame["touch5_3d"]),
        "ft55": _round(frame["ft_5_5"].mean()),
        "ft55_ci95": _mean_ci(frame["ft_5_5"]),
        "dd3": _round(frame["dd5_3d"].mean()),
        "dd3_ci95": _mean_ci(frame["dd5_3d"]),
        "same_day_touch_stop_ambiguous": _round(frame["same_day_touch_stop_ambiguous"].mean()),
    }
    annual = []
    years = pd.to_datetime(frame["date"], errors="coerce").dt.year
    for year, group in frame.assign(year=years).groupby("year", observed=True):
        item = {
            "year": int(year),
            "n": int(len(group)),
            "days": int(group["date"].nunique()),
            "ret5": _round(group["fwd_close_ret_5d"].mean()),
            "ret5_pos_rate": _round(pd.to_numeric(group["fwd_close_ret_5d"], errors="coerce").gt(0.0).mean()),
            "alpha5_net_0_2": _round(group["alpha5_net"].mean()),
            "alpha5_net_0_2_pos_rate": _round(pd.to_numeric(group["alpha5_net"], errors="coerce").gt(0.0).mean()),
            "touch3": _round(group["touch5_3d"].mean()),
            "ft55": _round(group["ft_5_5"].mean()),
            "dd3": _round(group["dd5_3d"].mean()),
        }
        annual.append(item)
    out["annual"] = annual
    out["years_alpha5_net_0_2_pos"] = int(sum((row.get("alpha5_net_0_2") or 0.0) > 0.0 for row in annual))
    return out


def recent_shadow_gate(metrics: Mapping[str, Any]) -> Dict[str, Any]:
    thresholds = dict(PROMOTION_GATE_THRESHOLDS)
    thresholds.update({"min_n": 35.0, "min_days": 15.0, "min_years_alpha5_net_0_2_pos": 1.0})
    gate = evaluate_nasdaq_promotion_gate(metrics, thresholds=thresholds)
    gate["gate_version"] = "nasdaq_session_recent_shadow_gate_v1"
    gate["capital_status"] = "research_shadow_recent_intraday_only"
    if gate.get("promotion_ready"):
        gate["status"] = "recent_shadow_candidate_not_production"
    return gate


def search_edges(panel: pd.DataFrame, *, topn_values: Sequence[int]) -> List[Dict[str, Any]]:
    score_cols = [
        "score_session_momentum",
        "score_session_calm_strength",
        "score_session_reversal",
        "score_liquid_open_drive",
    ]
    results: List[Dict[str, Any]] = []
    for condition_name, mode, condition_specs in _condition_specs():
        mode_frame = panel[panel["session_mode"].eq(mode)]
        base = mode_frame[_mask(mode_frame, condition_specs)]
        if len(base) < 40 or base["date"].nunique() < 15:
            continue
        for score_col in score_cols:
            if score_col not in base.columns:
                continue
            for topn in topn_values:
                picks = _ranked_pick(base, score_col, int(topn))
                if len(picks) < 20 or picks["date"].nunique() < 10:
                    continue
                metrics = metric_block(picks)
                shadow_gate = recent_shadow_gate(metrics)
                promotion_gate = evaluate_nasdaq_promotion_gate(metrics)
                selection_key = (
                    float(metrics.get("ret5") or 0.0)
                    + float(metrics.get("alpha5_net_cost_0_2") or 0.0)
                    + 4.0 * float(metrics.get("ret5_pos_rate") or 0.0)
                    + 3.0 * float(metrics.get("alpha5_net_cost_0_2_pos_rate") or 0.0)
                    + 2.0 * float(metrics.get("touch3") or 0.0)
                    + 2.0 * float(metrics.get("ft55") or 0.0)
                    - 2.0 * float(metrics.get("dd3") or 0.0)
                )
                results.append(
                    {
                        "condition": condition_name,
                        "session_mode": mode,
                        "condition_specs": list(condition_specs),
                        "score": score_col,
                        "topn": int(topn),
                        "selection_key": round(selection_key, 6),
                        "metrics": metrics,
                        "recent_shadow_gate": shadow_gate,
                        "promotion_gate": promotion_gate,
                        "recent_shadow_ready": bool(shadow_gate.get("promotion_ready")),
                        "promotion_ready": bool(promotion_gate.get("promotion_ready")),
                        "promotion_blocking_reasons": list(promotion_gate.get("blocking_reasons") or []),
                    }
                )
    return sorted(results, key=lambda row: float(row.get("selection_key") or -999.0), reverse=True)


def _fmt_pct(value: Any) -> str:
    numeric = _finite(value)
    return "-" if numeric is None else f"{numeric:.2%}"


def _fmt_num(value: Any) -> str:
    numeric = _finite(value)
    return "-" if numeric is None else f"{numeric:+.3f}"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_md(path: Path, report: Mapping[str, Any]) -> None:
    lines = [
        "# NASDAQ Session Edge Search",
        "",
        f"- report_version: `{report.get('report_version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- panel_path: `{report.get('panel_path')}`",
        f"- max_symbols: `{report.get('max_symbols')}`",
        f"- period: `{report.get('period')}` interval `{report.get('interval')}`",
        f"- data_limit: `{report.get('data_limit')}`",
        f"- unsupported_session_warning: `{report.get('unsupported_session_warning')}`",
        "",
        "## Summary",
        "",
        f"- rows: `{report.get('rows')}`",
        f"- symbols: `{report.get('symbols')}`",
        f"- date_range: `{report.get('date_min')}` ~ `{report.get('date_max')}`",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- recent_shadow_ready_count: `{report.get('recent_shadow_ready_count')}`",
        f"- promotion_ready_count: `{report.get('promotion_ready_count')}`",
        f"- fetch_stats: `{report.get('fetch_stats')}`",
        "",
        "## Session Coverage",
        "",
    ]
    for row in report.get("session_coverage", []):
        lines.append(
            f"- `{row.get('session_mode')}` rows `{row.get('rows')}` days `{row.get('days')}` symbols `{row.get('symbols')}` "
            f"ret5 `{_fmt_num(row.get('ret5'))}%` win `{_fmt_pct(row.get('ret5_pos_rate'))}` "
            f"touch `{_fmt_pct(row.get('touch3'))}` ft `{_fmt_pct(row.get('ft55'))}` dd `{_fmt_pct(row.get('dd3'))}`"
        )
    lines.extend(["", "## Top Candidates", ""])
    for row in report.get("top_candidates", [])[:30]:
        metrics = row.get("metrics") or {}
        lines.append(
            f"- `{row.get('session_mode')}` `{row.get('condition')}` / `{row.get('score')}` top{row.get('topn')} "
            f"n `{metrics.get('n')}` days `{metrics.get('days')}` symbols `{metrics.get('symbols')}` "
            f"ret5 `{_fmt_num(metrics.get('ret5'))}%` win `{_fmt_pct(metrics.get('ret5_pos_rate'))}` "
            f"net `{_fmt_num(metrics.get('alpha5_net_cost_0_2'))}%` net_win `{_fmt_pct(metrics.get('alpha5_net_cost_0_2_pos_rate'))}` "
            f"touch `{_fmt_pct(metrics.get('touch3'))}` ft `{_fmt_pct(metrics.get('ft55'))}` dd `{_fmt_pct(metrics.get('dd3'))}` "
            f"recent_shadow `{'PASS' if row.get('recent_shadow_ready') else 'BLOCK'}` production `{'PASS' if row.get('promotion_ready') else 'BLOCK'}`"
        )
        reasons = row.get("promotion_blocking_reasons") or []
        if reasons:
            lines.append(f"  - production_blockers: `{', '.join(str(reason) for reason in reasons[:8])}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build recent NASDAQ session panel and search session-aware edges.")
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_OHLCV_DIR))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--max-symbols", type=int, default=120)
    parser.add_argument("--min-liq20", type=float, default=100_000_000.0)
    parser.add_argument("--period", default="60d")
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--topn", default="1,2,3,5")
    parser.add_argument("--max-output-candidates", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    panel_path = Path(args.panel).expanduser()
    daily = _read_daily_context(panel_path)
    symbols = select_symbols(daily, max_symbols=int(args.max_symbols), min_liq20=float(args.min_liq20))
    session_panel, fetch_stats = build_session_panel(
        daily=daily,
        symbols=symbols,
        cache_dir=Path(args.cache_dir),
        raw_dir=Path(args.raw_dir),
        period=str(args.period),
        interval=str(args.interval),
        timeout=int(args.timeout),
        refresh=bool(args.refresh_cache),
        fetch=not bool(args.no_fetch),
    )
    session_panel = add_ranks_and_alpha(session_panel)
    topn_values = [int(value) for value in str(args.topn).split(",") if value.strip()]
    results = search_edges(session_panel, topn_values=topn_values) if not session_panel.empty else []
    session_coverage = []
    for mode, group in session_panel.groupby("session_mode", observed=True) if not session_panel.empty else []:
        block = metric_block(group)
        session_coverage.append({"session_mode": mode, "rows": block["n"], **block})
    limit = max(1, int(args.max_output_candidates))
    report = {
        "report_version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "panel_path": str(panel_path),
        "raw_dir": str(Path(args.raw_dir)),
        "cache_dir": str(Path(args.cache_dir)),
        "max_symbols": int(args.max_symbols),
        "min_liq20": float(args.min_liq20),
        "period": str(args.period),
        "interval": str(args.interval),
        "data_limit": "yfinance_recent_intraday_only; 5m bars are approximately 60 calendar days",
        "unsupported_session_warning": (
            "This source covers 04:00-20:00 America/New_York premarket/regular/afterhours. "
            "20:00-04:00 overnight/day-market bars are not present and require a separate provider."
        ),
        "rows": int(len(session_panel)),
        "symbols": int(session_panel["symbol"].nunique()) if not session_panel.empty else 0,
        "date_min": str(session_panel["date"].min().date()) if not session_panel.empty else None,
        "date_max": str(session_panel["date"].max().date()) if not session_panel.empty else None,
        "fetch_stats": fetch_stats,
        "session_coverage": session_coverage,
        "candidate_count": int(len(results)),
        "recent_shadow_ready_count": int(sum(1 for row in results if row.get("recent_shadow_ready"))),
        "promotion_ready_count": int(sum(1 for row in results if row.get("promotion_ready"))),
        "top_candidates": results[:limit],
        "promotion_gate_thresholds": dict(PROMOTION_GATE_THRESHOLDS),
    }
    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"nasdaq_session_edge_search_{stamp}.json"
    md_path = out_dir / f"nasdaq_session_edge_search_{stamp}.md"
    _write_json(json_path, report)
    _write_md(md_path, report)
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "rows": report["rows"],
                "symbols": report["symbols"],
                "candidate_count": report["candidate_count"],
                "recent_shadow_ready_count": report["recent_shadow_ready_count"],
                "promotion_ready_count": report["promotion_ready_count"],
                "top_candidate": report["top_candidates"][0] if report["top_candidates"] else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
