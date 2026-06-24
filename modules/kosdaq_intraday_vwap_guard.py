from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import numpy as np
import pandas as pd


CANDIDATE_ID = "kosdaq_intraday_1500_3d_t5_vwap_guard_shadow_v1"
STRATEGY_FAMILY = "KR_INTRADAY_3D_T5"
MODEL_PATH = Path("models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl")
ENTRY_TIME_KST = "15:00"
ENTRY_INPUT_HOUR = "150000"
TARGET_COLUMN = "target_touch3d_t5"
ROUNDTRIP_COST_PCT = 0.33

INTRADAY_FEATURES = [
    "gap_open_pct",
    "pre_ret_pct",
    "pre_high_pct",
    "pre_low_pct",
    "pre_range_pct",
    "pre_close_loc",
    "pre_vwap_dist_pct",
    "pre_value_vs_liq_prev_pct",
]

DAILY_PREV_FEATURES = [
    "ret_1d_prev",
    "ret_3d_prev",
    "ret_5d_prev",
    "ret_10d_prev",
    "ret_20d_prev",
    "ma5_dist_prev",
    "ma20_dist_prev",
    "ma60_dist_prev",
    "ma20_slope_prev",
    "rsi14_prev",
    "rsi_slope_prev",
    "accel_prev",
    "consec_up_prev",
    "dist_hi20_prev",
    "dist_hi60_prev",
    "pos20_prev",
    "bb_pctb_prev",
    "bb_bw_prev",
    "atr_pct_prev",
    "vol20_prev",
    "close_loc_prev",
    "vol_ratio_prev",
    "vol_trend_prev",
    "turn_z_prev",
    "obv_slope_prev",
    "cmf20_prev",
    "idx_mom20_prev",
    "idx_vol20_prev",
]

MODEL_FEATURES = INTRADAY_FEATURES + DAILY_PREV_FEATURES


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def normalize_kr_code(value: Any) -> str:
    text = str(value or "").strip().upper().replace(".KQ", "").replace(".KS", "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits.zfill(6) if digits else text


def ticker_for_kosdaq(code: Any) -> str:
    return f"{normalize_kr_code(code)}.KQ"


def liquidity_lane(liq_prev_eok: Any, *, tradeability_floor_eok: float = 100.0) -> str:
    value = safe_float(liq_prev_eok)
    if value is not None and value >= float(tradeability_floor_eok):
        return "gte100eok"
    return "gte30eok"


def _rsi(series: pd.Series, n: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    down = (-delta.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / (down + 1e-9))


def _completed_daily_frame(daily_bars: pd.DataFrame, *, trade_date: str | None = None) -> pd.DataFrame:
    if not isinstance(daily_bars, pd.DataFrame) or daily_bars.empty:
        return pd.DataFrame()
    frame = daily_bars.copy()
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()
    if trade_date:
        cutoff = pd.to_datetime(str(trade_date), format="%Y%m%d", errors="coerce")
        if pd.notna(cutoff):
            frame = frame[frame.index.normalize() < cutoff.normalize()]
    return frame.dropna(subset=["Open", "High", "Low", "Close", "Volume"], how="any")


def compute_daily_prev_context(
    daily_bars: pd.DataFrame,
    *,
    trade_date: str | None = None,
    index_context: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build the previous-completed-day context used by the 15:00 KOSDAQ model."""

    frame = _completed_daily_frame(daily_bars, trade_date=trade_date)
    if frame.empty:
        return {}

    close = pd.to_numeric(frame["Close"], errors="coerce")
    open_ = pd.to_numeric(frame["Open"], errors="coerce")
    high = pd.to_numeric(frame["High"], errors="coerce")
    low = pd.to_numeric(frame["Low"], errors="coerce")
    volume = pd.to_numeric(frame["Volume"], errors="coerce")

    feat = pd.DataFrame(index=frame.index)
    for n in (1, 3, 5, 10, 20):
        feat[f"ret_{n}d"] = close.pct_change(n) * 100
    for n in (5, 20, 60):
        feat[f"ma{n}_dist"] = (close / close.rolling(n).mean() - 1) * 100
    feat["ma20_slope"] = (close.rolling(20).mean() / close.rolling(20).mean().shift(5) - 1) * 100
    feat["rsi14"] = _rsi(close)
    feat["rsi_slope"] = feat["rsi14"] - feat["rsi14"].shift(5)
    feat["accel"] = close.pct_change(5) * 100 - close.pct_change(5).shift(5) * 100
    up = (close > close.shift(1)).astype(int)
    feat["consec_up"] = up.groupby((up != up.shift()).cumsum()).cumsum() * up
    feat["dist_hi20"] = (close / high.rolling(20).max() - 1) * 100
    feat["dist_hi60"] = (close / high.rolling(60).max() - 1) * 100
    feat["pos20"] = (close - low.rolling(20).min()) / (high.rolling(20).max() - low.rolling(20).min() + 1e-9)
    ma20 = close.rolling(20).mean()
    sd20 = close.rolling(20).std()
    feat["bb_pctb"] = (close - (ma20 - 2 * sd20)) / (4 * sd20 + 1e-9)
    feat["bb_bw"] = (4 * sd20) / (ma20 + 1e-9) * 100
    true_range = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    feat["atr_pct"] = true_range.rolling(14).mean() / close * 100
    feat["vol20"] = close.pct_change().rolling(20).std() * 100
    feat["close_loc"] = (close - low) / (high - low + 1e-9)
    feat["vol_ratio"] = volume / volume.rolling(20).mean()
    feat["vol_trend"] = volume.rolling(5).mean() / volume.rolling(20).mean()
    feat["turn_z"] = (volume - volume.rolling(60).mean()) / (volume.rolling(60).std() + 1e-9)
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    feat["obv_slope"] = (obv - obv.shift(10)) / (volume.rolling(20).mean() * 10 + 1e-9)
    mfm = ((close - low) - (high - close)) / (high - low + 1e-9)
    feat["cmf20"] = (mfm * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-9)

    latest = feat.iloc[-1]
    out: Dict[str, Any] = {f"{name}_prev": safe_float(latest.get(name)) for name in [c[:-5] for c in DAILY_PREV_FEATURES if c not in {"idx_mom20_prev", "idx_vol20_prev"}]}
    out["prev_close"] = safe_float(close.iloc[-1])
    out["prev_date"] = frame.index[-1].strftime("%Y-%m-%d")
    out["liq_prev_eok"] = safe_float((close * volume).rolling(20).mean().iloc[-1] / 1e8)
    if index_context:
        out["idx_mom20_prev"] = safe_float(index_context.get("idx_mom20_prev"))
        out["idx_vol20_prev"] = safe_float(index_context.get("idx_vol20_prev"))
    return out


def compute_index_prev_context(index_close: pd.Series, *, trade_date: str | None = None) -> Dict[str, Any]:
    if not isinstance(index_close, pd.Series) or index_close.empty:
        return {"idx_mom20_prev": None, "idx_vol20_prev": None}
    close = pd.to_numeric(index_close.copy(), errors="coerce").dropna()
    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    if trade_date:
        cutoff = pd.to_datetime(str(trade_date), format="%Y%m%d", errors="coerce")
        if pd.notna(cutoff):
            close = close[close.index.normalize() < cutoff.normalize()]
    mom = close.pct_change(20).shift(1) * 100
    vol = close.pct_change().rolling(20).std().shift(1) * 100 * np.sqrt(20)
    return {"idx_mom20_prev": safe_float(mom.iloc[-1]) if len(mom) else None, "idx_vol20_prev": safe_float(vol.iloc[-1]) if len(vol) else None}


def compute_pre_entry_features(
    minute_bars: pd.DataFrame,
    *,
    prev_close: float,
    liq_prev_eok: float,
    trade_date: str | None = None,
    entry_time: str = ENTRY_TIME_KST,
) -> Dict[str, Any]:
    if not isinstance(minute_bars, pd.DataFrame) or minute_bars.empty:
        return {}
    frame = minute_bars.copy()
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()
    if trade_date:
        day = pd.to_datetime(str(trade_date), format="%Y%m%d", errors="coerce")
        if pd.notna(day):
            frame = frame[frame.index.normalize() == day.normalize()]
    entry_ts = pd.Timestamp(entry_time).time()
    open_ts = pd.Timestamp("09:00").time()
    times = frame.index.time
    frame = frame[(times >= open_ts) & (times <= entry_ts)]
    if len(frame) < 10:
        return {}

    open_price = safe_float(frame["Open"].iloc[0])
    entry_price = safe_float(frame["Close"].iloc[-1])
    high = safe_float(pd.to_numeric(frame["High"], errors="coerce").max())
    low = safe_float(pd.to_numeric(frame["Low"], errors="coerce").min())
    volume = pd.to_numeric(frame["Volume"], errors="coerce").fillna(0)
    close = pd.to_numeric(frame["Close"], errors="coerce")
    if not open_price or not entry_price or not high or not low or low <= 0 or liq_prev_eok <= 0:
        return {}
    pre_value = float((close.ffill().fillna(0) * volume).sum())
    vwap = pre_value / (float(volume.sum()) + 1.0)
    return {
        "gap_open_pct": (open_price / prev_close - 1) * 100 if prev_close else None,
        "pre_ret_pct": (entry_price / open_price - 1) * 100,
        "pre_high_pct": (high / open_price - 1) * 100,
        "pre_low_pct": (low / open_price - 1) * 100,
        "pre_range_pct": (high / low - 1) * 100,
        "pre_close_loc": (entry_price - low) / (high - low + 1e-9),
        "pre_vwap_dist_pct": (entry_price / vwap - 1) * 100 if vwap > 0 else None,
        "pre_value_vs_liq_prev_pct": pre_value / (liq_prev_eok * 1e8) * 100,
        "entry_reference_price": entry_price,
        "entry_bar_at": frame.index[-1].isoformat(),
        "pre_bar_count": int(len(frame)),
        "pre_value_eok": pre_value / 1e8,
    }


def build_feature_row(
    *,
    code: str,
    daily_context: Mapping[str, Any],
    minute_bars: pd.DataFrame,
    trade_date: str | None = None,
) -> Dict[str, Any]:
    prev_close = safe_float(daily_context.get("prev_close"))
    liq_prev_eok = safe_float(daily_context.get("liq_prev_eok"))
    if prev_close is None or liq_prev_eok is None:
        return {}
    pre = compute_pre_entry_features(
        minute_bars,
        prev_close=prev_close,
        liq_prev_eok=liq_prev_eok,
        trade_date=trade_date,
    )
    if not pre:
        return {}
    row = {"code": normalize_kr_code(code), **pre}
    for key in DAILY_PREV_FEATURES:
        row[key] = safe_float(daily_context.get(key))
    row["prev_close"] = prev_close
    row["prev_date"] = daily_context.get("prev_date")
    row["liq_prev_eok"] = liq_prev_eok
    return row


def score_feature_rows(rows: Iterable[Mapping[str, Any]], model_bundle: Mapping[str, Any]) -> List[Dict[str, Any]]:
    model = model_bundle.get("model")
    calibrator = model_bundle.get("calibrator")
    features = list(model_bundle.get("features") or MODEL_FEATURES)
    source = [dict(row) for row in rows if isinstance(row, Mapping)]
    if not source:
        return []
    frame = pd.DataFrame(source)
    matrix = frame.reindex(columns=features).replace([np.inf, -np.inf], np.nan).clip(-1e6, 1e6).fillna(0)
    raw = model.predict_proba(matrix)[:, 1]
    calibrated = calibrator.predict(raw) if calibrator is not None else raw
    out: List[Dict[str, Any]] = []
    for item, p_raw, p_cal in zip(source, raw, calibrated):
        updated = dict(item)
        updated["p_raw"] = float(p_raw)
        updated["p_cal"] = float(p_cal)
        out.append(updated)
    return out


def select_vwap_guard_candidates(
    scored_rows: Iterable[Mapping[str, Any]],
    *,
    min_probability: float = 0.80,
    min_pre_vwap_dist_pct: float = 0.0,
    min_liq_eok: float = 30.0,
    tradeability_floor_eok: float = 100.0,
    top_n: int = 2,
) -> List[Dict[str, Any]]:
    selected = []
    for row in scored_rows:
        p_cal = safe_float(row.get("p_cal"))
        vwap_dist = safe_float(row.get("pre_vwap_dist_pct"))
        liq_prev_eok = safe_float(row.get("liq_prev_eok"))
        if p_cal is None or vwap_dist is None or liq_prev_eok is None:
            continue
        if p_cal < min_probability or vwap_dist < min_pre_vwap_dist_pct or liq_prev_eok < min_liq_eok:
            continue
        item = dict(row)
        item["liquidity_lane"] = liquidity_lane(liq_prev_eok, tradeability_floor_eok=tradeability_floor_eok)
        item["tradeability_floor_eok"] = float(tradeability_floor_eok)
        item["tradeability_floor_pass"] = bool(liq_prev_eok >= tradeability_floor_eok)
        selected.append(item)
    selected.sort(key=lambda row: (float(row.get("p_cal") or 0.0), float(row.get("liq_prev_eok") or 0.0)), reverse=True)
    return selected[: max(int(top_n), 0)]


def live_pick_payload(row: Mapping[str, Any], *, rank: int, trade_date: str, run_id: str) -> Dict[str, Any]:
    p_cal = float(row.get("p_cal") or 0.0)
    liq_prev_eok = safe_float(row.get("liq_prev_eok"))
    return {
        "ticker": ticker_for_kosdaq(row.get("code")),
        "market": "KOSDAQ",
        "scan_mode": "INTRADAY",
        "strategy_family": STRATEGY_FAMILY,
        "candidate_id": CANDIDATE_ID,
        "decision": "KOSDAQ_INTRADAY_3D_T5_BUY",
        "decision_bucket": "kosdaq_intraday_3d_t5_vwap_guard",
        "selection_lane": f"KOSDAQ_INTRADAY_1500_VWAP_GUARD_{str(row.get('liquidity_lane') or 'gte30eok').upper()}",
        "priority_rank": int(rank),
        "p": round(p_cal, 6),
        "p_raw": round(float(row.get("p_raw") or 0.0), 6),
        "ml_prob": round(p_cal * 100, 4),
        "prob_clean": round(p_cal * 100, 4),
        "liq_prev_eok": round(float(liq_prev_eok or 0.0), 4),
        "liq억": round(float(liq_prev_eok or 0.0), 1),
        "liquidity_lane": row.get("liquidity_lane"),
        "tradeability_floor_pass": bool(row.get("tradeability_floor_pass")),
        "pre_vwap_dist_pct": round(float(row.get("pre_vwap_dist_pct") or 0.0), 4),
        "pre_value_vs_liq_prev_pct": round(float(row.get("pre_value_vs_liq_prev_pct") or 0.0), 4),
        "entry_reference_price": safe_float(row.get("entry_reference_price")),
        "scan_entry_reference_price": safe_float(row.get("entry_reference_price")),
        "ordered_entry_at": row.get("entry_bar_at"),
        "ordered_entry_price": safe_float(row.get("entry_reference_price")),
        "base_trade_date": trade_date,
        "target_tp_pct": 5.0,
        "stop_sl_pct": None,
        "hold_days": 3,
        "source_ref": CANDIDATE_ID,
        "run_id": run_id,
    }
