#!/usr/bin/env python3
"""Backfill US daily OHLCV and daily feature panels.

Current primary use: NASDAQ all-symbol, about 8 years of daily bars.

The tool intentionally separates:
- raw adjusted OHLCV by symbol, for resumable fetches
- feature panel parquet, for model/research use
- latest feature snapshot, for quick scoring/debugging
- JSON/MD reports, for auditability
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from pandas.errors import PerformanceWarning

warnings.filterwarnings("ignore", category=PerformanceWarning)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.quant_analysis import QuantStrategy


FEATURE_VERSION = "us_daily_price_features_v1"
DEFAULT_START = "2018-01-01"
DEFAULT_MARKET = "NASDAQ"

PRICE_FEATURES = [
    "ret_1d",
    "ret_3d",
    "ret_5d",
    "ret_10d",
    "ret_20d",
    "ret_60d",
    "ma5_dist",
    "ma20_dist",
    "ma60_dist",
    "ma120_dist",
    "ma20_slope",
    "ma60_slope",
    "rsi14",
    "rsi_slope",
    "accel",
    "consec_up",
    "dist_hi20",
    "dist_hi60",
    "dist_hi120",
    "dist_lo20",
    "dist_lo60",
    "pos20",
    "bb_pctb",
    "bb_bw",
    "atr_pct",
    "vol20",
    "close_loc",
    "gap",
    "vol_ratio",
    "vol_trend",
    "turn_z",
    "obv_slope",
    "cmf20",
]

EXTRA_DAILY_FEATURES = [
    "ma5",
    "ma10",
    "ma20",
    "ma50",
    "ma60",
    "ma120",
    "ma200",
    "ma10_dist",
    "ma50_dist",
    "ma200_dist",
    "ma200_slope",
    "ema12",
    "ema26",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr14",
    "range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "dollar_volume_ratio20",
    "dollar_volume_z60",
    "volume_z60",
    "high_low_spread_pct",
    "abs_gap",
]

RETURN_HORIZONS = [1, 3, 5, 10, 20]


@dataclass
class BackfillPaths:
    root: Path
    market: str

    @property
    def market_root(self) -> Path:
        return self.root / self.market

    @property
    def raw_dir(self) -> Path:
        return self.market_root / "raw_ohlcv"

    @property
    def report_dir(self) -> Path:
        return self.market_root / "reports"

    @property
    def universe_path(self) -> Path:
        return self.market_root / f"{self.market.lower()}_universe.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(symbol: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(symbol).strip())
    return cleaned or "UNKNOWN"


def _chunk(items: Sequence[str], size: int) -> Iterable[List[str]]:
    size = max(1, int(size))
    for idx in range(0, len(items), size):
        yield list(items[idx : idx + size])


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_md(path: Path, report: Mapping[str, Any]) -> None:
    lines = [
        f"# {report.get('market')} 일봉 피쳐 백필",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- feature_version: `{report.get('feature_version')}`",
        f"- market: `{report.get('market')}`",
        f"- start: `{report.get('start')}`",
        f"- end: `{report.get('end')}`",
        f"- universe_size: `{report.get('universe_size')}`",
        f"- fetched_symbols: `{report.get('fetched_symbols')}`",
        f"- skipped_existing_raw: `{report.get('skipped_existing_raw')}`",
        f"- failed_symbols: `{len(report.get('failed_symbols') or [])}`",
        f"- feature_symbols: `{report.get('feature_symbols')}`",
        f"- feature_rows: `{report.get('feature_rows')}`",
        f"- feature_ready_rows: `{report.get('feature_ready_rows')}`",
        f"- output_feature_path: `{report.get('output_feature_path')}`",
        f"- output_latest_path: `{report.get('output_latest_path')}`",
        f"- universe_path: `{report.get('universe_path')}`",
        "",
        "## 모델 피쳐 컬럼",
        "",
        ", ".join(f"`{c}`" for c in report.get("price_features", [])),
        "",
        "## 추가 일봉 피쳐 컬럼",
        "",
        ", ".join(f"`{c}`" for c in report.get("extra_daily_features", [])),
        "",
        "## 라벨/미래 경로 컬럼",
        "",
        ", ".join(f"`{c}`" for c in report.get("label_columns", [])),
        "",
        "## 실패 심볼 샘플",
        "",
    ]
    failed = list(report.get("failed_symbols") or [])
    if failed:
        for item in failed[:50]:
            lines.append(f"- `{item}`")
        if len(failed) > 50:
            lines.append(f"- ... {len(failed) - 50} more")
    else:
        lines.append("- 없음")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fetch_universe(market: str) -> pd.DataFrame:
    market = str(market or DEFAULT_MARKET).upper()
    try:
        import FinanceDataReader as fdr

        listing = fdr.StockListing(market)
        if isinstance(listing, pd.DataFrame) and not listing.empty:
            symbol_col = "Symbol" if "Symbol" in listing.columns else ("Code" if "Code" in listing.columns else None)
            if symbol_col:
                out = listing.copy()
                out["symbol"] = out[symbol_col].astype(str).str.strip()
                out["name"] = out.get("Name", out["symbol"]).astype(str).str.strip()
                out["market"] = market
                keep = ["symbol", "name", "market"]
                for optional in ("Sector", "Industry", "Exchange", "Market", "ETF"):
                    if optional in out.columns:
                        keep.append(optional)
                out = out[keep].dropna(subset=["symbol"])
                out = out[out["symbol"].astype(str).str.len() > 0]
                out = out.drop_duplicates(subset=["symbol"], keep="first").sort_values("symbol")
                if not out.empty:
                    return out.reset_index(drop=True)
    except Exception:
        pass

    fallback = QuantStrategy._fallback_us_tickers(market)
    if not fallback:
        return pd.DataFrame(columns=["symbol", "name", "market"])
    return pd.DataFrame(
        [{"symbol": str(sym), "name": str(name), "market": market} for sym, name in fallback.items()]
    ).sort_values("symbol").reset_index(drop=True)


def _raw_path(paths: BackfillPaths, symbol: str) -> Path:
    return paths.raw_dir / f"{_safe_filename(symbol)}.parquet"


def _extract_yfinance_frame(payload: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if payload is None or payload.empty:
        return pd.DataFrame()

    frame = pd.DataFrame()
    if isinstance(payload.columns, pd.MultiIndex):
        level0 = [str(x) for x in payload.columns.get_level_values(0)]
        level1 = [str(x) for x in payload.columns.get_level_values(1)]
        if symbol in level0:
            frame = payload[symbol].copy()
        elif symbol in level1:
            frame = payload.xs(symbol, axis=1, level=1).copy()
    else:
        frame = payload.copy()

    if frame.empty:
        return pd.DataFrame()

    col_map = {}
    for col in frame.columns:
        key = str(col).strip().lower().replace(" ", "_")
        if key in {"open", "high", "low", "close", "adj_close", "volume"}:
            col_map[col] = key
    frame = frame.rename(columns=col_map)
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(set(frame.columns)):
        return pd.DataFrame()

    out = frame[[c for c in ["open", "high", "low", "close", "adj_close", "volume"] if c in frame.columns]].copy()
    out.index = pd.to_datetime(out.index, errors="coerce")
    out = out[out.index.notna()]
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)
    out = out.sort_index()
    for col in out.columns:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["open", "high", "low", "close"], how="any")
    if out.empty:
        return pd.DataFrame()

    raw_close = out["close"].copy()
    if "adj_close" in out.columns:
        factor = out["adj_close"] / raw_close.replace(0, np.nan)
        factor = factor.replace([np.inf, -np.inf], np.nan).fillna(1.0)
    else:
        out["adj_close"] = out["close"]
        factor = pd.Series(1.0, index=out.index)

    adjusted = pd.DataFrame(index=out.index)
    adjusted["date"] = out.index.normalize()
    adjusted["symbol"] = str(symbol)
    adjusted["open"] = out["open"] * factor
    adjusted["high"] = out["high"] * factor
    adjusted["low"] = out["low"] * factor
    adjusted["close"] = out["close"] * factor
    adjusted["raw_close"] = raw_close
    adjusted["adj_close"] = out["adj_close"]
    adjusted["volume"] = out["volume"].fillna(0.0)
    adjusted["adj_factor"] = factor
    adjusted["dollar_volume"] = adjusted["close"] * adjusted["volume"]
    adjusted["source"] = "yfinance"
    return adjusted.reset_index(drop=True)


def _download_batch(symbols: Sequence[str], start: str, end: str, timeout: int) -> pd.DataFrame:
    import yfinance as yf

    return yf.download(
        list(symbols),
        start=start,
        end=end,
        auto_adjust=False,
        group_by="ticker",
        actions=False,
        threads=True,
        progress=False,
        timeout=timeout,
    )


def _download_single(symbol: str, start: str, end: str, timeout: int) -> pd.DataFrame:
    import yfinance as yf

    hist = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=False, actions=False, timeout=timeout)
    return _extract_yfinance_frame(hist, symbol)


def fetch_raw_ohlcv(
    universe: pd.DataFrame,
    paths: BackfillPaths,
    *,
    start: str,
    end: str,
    batch_size: int,
    timeout: int,
    sleep: float,
    force_raw: bool,
) -> Tuple[int, int, List[str]]:
    paths.raw_dir.mkdir(parents=True, exist_ok=True)
    symbol_to_name = dict(zip(universe["symbol"].astype(str), universe["name"].astype(str)))
    symbols = list(symbol_to_name.keys())
    to_fetch = [sym for sym in symbols if force_raw or not _raw_path(paths, sym).exists()]
    skipped = len(symbols) - len(to_fetch)
    fetched = 0
    failed: List[str] = []

    for batch_no, batch in enumerate(_chunk(to_fetch, batch_size), start=1):
        print(f"[FETCH] batch={batch_no} symbols={len(batch)} fetched={fetched} failed={len(failed)}")
        batch_payload = pd.DataFrame()
        try:
            batch_payload = _download_batch(batch, start, end, timeout)
        except Exception as exc:
            print(f"[WARN] batch download failed: {type(exc).__name__}: {exc}")

        for sym in batch:
            frame = _extract_yfinance_frame(batch_payload, sym)
            if frame.empty:
                try:
                    frame = _download_single(sym, start, end, timeout)
                except Exception:
                    frame = pd.DataFrame()
            if frame.empty:
                failed.append(sym)
                continue
            frame["name"] = symbol_to_name.get(sym, sym)
            frame["market"] = paths.market
            frame = frame[
                [
                    "date",
                    "symbol",
                    "name",
                    "market",
                    "open",
                    "high",
                    "low",
                    "close",
                    "raw_close",
                    "adj_close",
                    "volume",
                    "adj_factor",
                    "dollar_volume",
                    "source",
                ]
            ].copy()
            frame.to_parquet(_raw_path(paths, sym), index=False)
            fetched += 1
        if sleep > 0:
            time.sleep(float(sleep))

    return fetched, skipped, failed


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    down = (-delta.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / (down + 1e-9))


def _future_extreme(series: pd.Series, horizon: int, reducer: str) -> pd.Series:
    shifted = [series.shift(-i) for i in range(1, horizon + 1)]
    matrix = pd.concat(shifted, axis=1)
    if reducer == "max":
        return matrix.max(axis=1, skipna=True)
    if reducer == "min":
        return matrix.min(axis=1, skipna=True)
    raise ValueError(f"unsupported reducer={reducer}")


def _first_touch_labels(close: pd.Series, high: pd.Series, low: pd.Series, horizon: int = 5) -> pd.DataFrame:
    up_level = close * 1.05
    dn_level = close * 0.95
    up_day = pd.Series(np.nan, index=close.index, dtype="float64")
    dn_day = pd.Series(np.nan, index=close.index, dtype="float64")
    ambiguous = pd.Series(0.0, index=close.index, dtype="float64")
    for day in range(1, horizon + 1):
        hi = high.shift(-day)
        lo = low.shift(-day)
        up_hit = hi >= up_level
        dn_hit = lo <= dn_level
        up_day = up_day.mask(up_day.isna() & up_hit, float(day))
        dn_day = dn_day.mask(dn_day.isna() & dn_hit, float(day))
        ambiguous = ambiguous.mask(up_hit & dn_hit, 1.0)
    ft = ((up_day.notna()) & (dn_day.isna() | (up_day <= dn_day))).astype(float)
    no_future = close.shift(-horizon).isna()
    ft = ft.mask(no_future, np.nan)
    return pd.DataFrame(
        {
            f"ft_5_5_{horizon}d": ft,
            f"first_up_day_{horizon}d": up_day,
            f"first_down_day_{horizon}d": dn_day,
            f"first_touch_ambiguous_{horizon}d": ambiguous.mask(no_future, np.nan),
        },
        index=close.index,
    )


def compute_feature_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()
    h = raw.copy()
    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h = h.dropna(subset=["date"]).sort_values("date")
    h = h.drop_duplicates(subset=["date"], keep="last").set_index("date")
    for col in ["open", "high", "low", "close", "volume", "dollar_volume"]:
        h[col] = pd.to_numeric(h[col], errors="coerce")
    h = h.dropna(subset=["open", "high", "low", "close"], how="any")
    if h.empty:
        return pd.DataFrame()

    close, open_, high, low, volume = h["close"], h["open"], h["high"], h["low"], h["volume"].fillna(0.0)
    f = pd.DataFrame(index=h.index)
    f["date"] = h.index
    f["symbol"] = str(h["symbol"].iloc[-1])
    f["name"] = str(h["name"].iloc[-1]) if "name" in h.columns else f["symbol"]
    f["market"] = str(h["market"].iloc[-1]) if "market" in h.columns else DEFAULT_MARKET
    f["feature_version"] = FEATURE_VERSION
    f["open"] = open_
    f["high"] = high
    f["low"] = low
    f["close"] = close
    f["raw_close"] = pd.to_numeric(h.get("raw_close", close), errors="coerce")
    f["adj_close"] = pd.to_numeric(h.get("adj_close", close), errors="coerce")
    f["volume"] = volume
    f["dollar_volume"] = close * volume
    f["liq20"] = f["dollar_volume"].rolling(20).mean()
    f["liq60"] = f["dollar_volume"].rolling(60).mean()
    f["year"] = f["date"].dt.year.astype(float)
    f["month"] = f["date"].dt.month.astype(float)
    f["dayofweek"] = f["date"].dt.dayofweek.astype(float)

    for n in (1, 3, 5, 10, 20, 60):
        f[f"ret_{n}d"] = close.pct_change(n) * 100
    for n in (5, 10, 20, 50, 60, 120, 200):
        f[f"ma{n}"] = close.rolling(n).mean()
        f[f"ma{n}_dist"] = (close / f[f"ma{n}"] - 1) * 100
    f["ma20_slope"] = (close.rolling(20).mean() / close.rolling(20).mean().shift(5) - 1) * 100
    f["ma60_slope"] = (close.rolling(60).mean() / close.rolling(60).mean().shift(10) - 1) * 100
    f["ma200_slope"] = (close.rolling(200).mean() / close.rolling(200).mean().shift(20) - 1) * 100
    f["ema12"] = close.ewm(span=12, adjust=False).mean()
    f["ema26"] = close.ewm(span=26, adjust=False).mean()
    f["macd"] = f["ema12"] - f["ema26"]
    f["macd_signal"] = f["macd"].ewm(span=9, adjust=False).mean()
    f["macd_hist"] = f["macd"] - f["macd_signal"]
    f["rsi14"] = _rsi(close)
    f["rsi_slope"] = f["rsi14"] - f["rsi14"].shift(5)
    f["accel"] = close.pct_change(5) * 100 - close.pct_change(5).shift(5) * 100
    up = (close > close.shift(1)).astype(int)
    f["consec_up"] = up.groupby((up != up.shift()).cumsum()).cumsum() * up
    f["dist_hi20"] = (close / high.rolling(20).max() - 1) * 100
    f["dist_hi60"] = (close / high.rolling(60).max() - 1) * 100
    f["dist_hi120"] = (close / high.rolling(120).max() - 1) * 100
    f["dist_lo20"] = (close / low.rolling(20).min() - 1) * 100
    f["dist_lo60"] = (close / low.rolling(60).min() - 1) * 100
    f["pos20"] = (close - low.rolling(20).min()) / (high.rolling(20).max() - low.rolling(20).min() + 1e-9)
    ma20 = close.rolling(20).mean()
    sd20 = close.rolling(20).std()
    f["bb_pctb"] = (close - (ma20 - 2 * sd20)) / (4 * sd20 + 1e-9)
    f["bb_bw"] = (4 * sd20) / (ma20 + 1e-9) * 100
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    f["atr14"] = tr.rolling(14).mean()
    f["atr_pct"] = f["atr14"] / close * 100
    f["vol20"] = close.pct_change().rolling(20).std() * 100
    f["close_loc"] = (close - low) / (high - low + 1e-9)
    f["gap"] = (open_ / close.shift(1) - 1) * 100
    f["abs_gap"] = f["gap"].abs()
    f["vol_ratio"] = volume / volume.rolling(20).mean()
    f["vol_trend"] = volume.rolling(5).mean() / volume.rolling(20).mean()
    f["turn_z"] = (volume - volume.rolling(60).mean()) / (volume.rolling(60).std() + 1e-9)
    f["volume_z60"] = f["turn_z"]
    f["dollar_volume_ratio20"] = f["dollar_volume"] / f["dollar_volume"].rolling(20).mean()
    f["dollar_volume_z60"] = (f["dollar_volume"] - f["dollar_volume"].rolling(60).mean()) / (
        f["dollar_volume"].rolling(60).std() + 1e-9
    )
    f["range_pct"] = (high / low.replace(0, np.nan) - 1) * 100
    f["body_pct"] = (close / open_.replace(0, np.nan) - 1) * 100
    f["upper_wick_pct"] = (high - pd.concat([open_, close], axis=1).max(axis=1)) / close.replace(0, np.nan) * 100
    f["lower_wick_pct"] = (pd.concat([open_, close], axis=1).min(axis=1) - low) / close.replace(0, np.nan) * 100
    f["high_low_spread_pct"] = (high - low) / close.replace(0, np.nan) * 100
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    f["obv_slope"] = (obv - obv.shift(10)) / (volume.rolling(20).mean() * 10 + 1e-9)
    mfm = ((close - low) - (high - close)) / (high - low + 1e-9)
    f["cmf20"] = (mfm * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-9)

    for horizon in RETURN_HORIZONS:
        f[f"fwd_close_ret_{horizon}d"] = (close.shift(-horizon) / close - 1) * 100
        f[f"fwd_high_ret_{horizon}d"] = (_future_extreme(high, horizon, "max") / close - 1) * 100
        f[f"fwd_low_ret_{horizon}d"] = (_future_extreme(low, horizon, "min") / close - 1) * 100
        f[f"touch5_{horizon}d"] = (f[f"fwd_high_ret_{horizon}d"] >= 5.0).astype(float).mask(close.shift(-horizon).isna(), np.nan)
        f[f"touch10_{horizon}d"] = (f[f"fwd_high_ret_{horizon}d"] >= 10.0).astype(float).mask(close.shift(-horizon).isna(), np.nan)
        f[f"dd5_{horizon}d"] = (f[f"fwd_low_ret_{horizon}d"] <= -5.0).astype(float).mask(close.shift(-horizon).isna(), np.nan)
        f[f"dd10_{horizon}d"] = (f[f"fwd_low_ret_{horizon}d"] <= -10.0).astype(float).mask(close.shift(-horizon).isna(), np.nan)

    ft = _first_touch_labels(close, high, low, horizon=5)
    f = pd.concat([f, ft], axis=1)
    f["ft_5_5"] = f["ft_5_5_5d"]
    f["feature_ready"] = (~f[PRICE_FEATURES].replace([np.inf, -np.inf], np.nan).isna().any(axis=1)).astype(float)
    f = f.replace([np.inf, -np.inf], np.nan)
    return f.reset_index(drop=True)


def _label_columns() -> List[str]:
    cols: List[str] = []
    for horizon in RETURN_HORIZONS:
        cols.extend(
            [
                f"fwd_close_ret_{horizon}d",
                f"fwd_high_ret_{horizon}d",
                f"fwd_low_ret_{horizon}d",
                f"touch5_{horizon}d",
                f"touch10_{horizon}d",
                f"dd5_{horizon}d",
                f"dd10_{horizon}d",
            ]
        )
    cols.extend(["ft_5_5", "ft_5_5_5d", "first_up_day_5d", "first_down_day_5d", "first_touch_ambiguous_5d"])
    return cols


def write_feature_panel(
    universe: pd.DataFrame,
    paths: BackfillPaths,
    *,
    start: str,
    end: str,
    output_prefix: str,
    feature_batch_size: int,
) -> Dict[str, Any]:
    import pyarrow as pa
    import pyarrow.parquet as pq

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    feature_path = paths.market_root / f"{output_prefix}_{start.replace('-', '')}_{end.replace('-', '')}_{stamp}.parquet"
    tmp_feature_path = feature_path.with_name(f".{feature_path.name}.tmp")
    latest_path = paths.market_root / f"{output_prefix}_latest_{stamp}.parquet"
    latest_csv_path = paths.market_root / f"{output_prefix}_latest_{stamp}.csv"
    paths.market_root.mkdir(parents=True, exist_ok=True)

    writer: Optional[pq.ParquetWriter] = None
    schema: Optional[pa.Schema] = None
    pending: List[pd.DataFrame] = []
    latest_rows: List[pd.DataFrame] = []
    feature_symbols = 0
    feature_rows = 0
    ready_rows = 0
    failed_features: List[str] = []

    def flush() -> None:
        nonlocal writer, schema, pending
        if not pending:
            return
        batch = pd.concat(pending, ignore_index=True)
        table = pa.Table.from_pandas(batch, preserve_index=False)
        if writer is None:
            schema = table.schema
            writer = pq.ParquetWriter(tmp_feature_path, schema, compression="zstd")
        else:
            if schema is not None and not table.schema.equals(schema):
                table = table.cast(schema)
        writer.write_table(table)
        pending = []

    symbols = list(universe["symbol"].astype(str))
    for idx, sym in enumerate(symbols, start=1):
        path = _raw_path(paths, sym)
        if not path.exists():
            failed_features.append(sym)
            continue
        try:
            raw = pd.read_parquet(path)
            feat = compute_feature_frame(raw)
        except Exception:
            failed_features.append(sym)
            continue
        if feat.empty:
            failed_features.append(sym)
            continue
        feature_symbols += 1
        feature_rows += len(feat)
        ready_rows += int(pd.to_numeric(feat["feature_ready"], errors="coerce").fillna(0).sum())
        pending.append(feat)
        latest = feat.dropna(subset=["close"]).tail(1)
        if not latest.empty:
            latest_rows.append(latest)
        if len(pending) >= max(1, int(feature_batch_size)):
            flush()
        if idx % 250 == 0:
            print(f"[FEATURE] symbols={idx}/{len(symbols)} feature_rows={feature_rows}")

    flush()
    if writer is not None:
        writer.close()
        tmp_feature_path.replace(feature_path)

    latest_df = pd.concat(latest_rows, ignore_index=True) if latest_rows else pd.DataFrame()
    if not latest_df.empty:
        latest_df.to_parquet(latest_path, index=False)
        latest_df.to_csv(latest_csv_path, index=False)

    return {
        "output_feature_path": str(feature_path),
        "output_latest_path": str(latest_path) if latest_rows else None,
        "output_latest_csv_path": str(latest_csv_path) if latest_rows else None,
        "feature_symbols": feature_symbols,
        "feature_rows": feature_rows,
        "feature_ready_rows": ready_rows,
        "failed_feature_symbols": failed_features,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill NASDAQ/US daily OHLCV and price features.")
    parser.add_argument("--market", default=DEFAULT_MARKET, choices=["NASDAQ", "S&P500", "AMEX"])
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=(date.today() + timedelta(days=1)).isoformat(), help="exclusive end date for yfinance")
    parser.add_argument("--output-root", default=os.path.expanduser("~/research_cache/us_daily"))
    parser.add_argument("--output-prefix", default="daily_features")
    parser.add_argument("--batch-size", type=int, default=80)
    parser.add_argument("--feature-batch-size", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=0.1)
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument("--force-raw", action="store_true")
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--raw-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    market = str(args.market).upper()
    paths = BackfillPaths(root=Path(args.output_root).expanduser(), market=market)
    paths.market_root.mkdir(parents=True, exist_ok=True)

    universe = _fetch_universe(market)
    if universe.empty:
        raise SystemExit(f"No universe for market={market}")
    if int(args.max_symbols or 0) > 0:
        universe = universe.head(int(args.max_symbols)).copy()
    universe.to_csv(paths.universe_path, index=False)

    fetched = 0
    skipped = 0
    failed_fetch: List[str] = []
    if not bool(args.skip_fetch):
        fetched, skipped, failed_fetch = fetch_raw_ohlcv(
            universe,
            paths,
            start=str(args.start),
            end=str(args.end),
            batch_size=int(args.batch_size),
            timeout=int(args.timeout),
            sleep=float(args.sleep),
            force_raw=bool(args.force_raw),
        )
    else:
        skipped = len(universe)

    feature_info: Dict[str, Any] = {}
    if not bool(args.raw_only):
        feature_info = write_feature_panel(
            universe,
            paths,
            start=str(args.start),
            end=str(args.end),
            output_prefix=str(args.output_prefix),
            feature_batch_size=int(args.feature_batch_size),
        )

    report: Dict[str, Any] = {
        "generated_at": _utc_now(),
        "feature_version": FEATURE_VERSION,
        "market": market,
        "start": str(args.start),
        "end": str(args.end),
        "output_root": str(paths.market_root),
        "universe_path": str(paths.universe_path),
        "universe_size": int(len(universe)),
        "fetched_symbols": int(fetched),
        "skipped_existing_raw": int(skipped),
        "failed_symbols": failed_fetch,
        "price_features": PRICE_FEATURES,
        "extra_daily_features": EXTRA_DAILY_FEATURES,
        "label_columns": _label_columns(),
        **feature_info,
    }
    report.setdefault("feature_symbols", 0)
    report.setdefault("feature_rows", 0)
    report.setdefault("feature_ready_rows", 0)
    report.setdefault("failed_feature_symbols", [])

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json = paths.report_dir / f"{market.lower()}_daily_feature_backfill_{stamp}.json"
    report_md = paths.report_dir / f"{market.lower()}_daily_feature_backfill_{stamp}.md"
    _write_json(report_json, report)
    _write_md(report_md, report)
    print(
        json.dumps(
            {
                "report_json": str(report_json),
                "report_md": str(report_md),
                "universe_size": report["universe_size"],
                "fetched_symbols": report["fetched_symbols"],
                "failed_symbols": len(report["failed_symbols"]),
                "feature_symbols": report["feature_symbols"],
                "feature_rows": report["feature_rows"],
                "output_feature_path": report.get("output_feature_path"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
