#!/usr/bin/env python3
"""
retrain_ml.py  —  Phase 25 ML Retraining Pipeline (Resolved Outcome v2)
=======================================================================

핵심 변화:
  - yfinance로 3일 수익률을 다시 계산하지 않음
  - Supabase `market_scan_results` / `agent_realized_outcomes`에 이미 저장된
    realized return을 직접 사용
  - 미래 수익률로 시장 레짐을 역추정하던 누출성 proxy 제거
  - 시장/모드별 분리 연구 결과를 함께 저장

기본 저장:
  - 호환용 글로벌 모델: models/phase25_model.pkl
  - 세그먼트 모델: models/phase25_kospi_swing.pkl, models/phase25_kosdaq_swing.pkl,
    models/phase25_kospi_intraday.pkl, models/phase25_kosdaq_intraday.pkl
  - 각 세그먼트는 학습 검증 AUC<0.5인 경우 signal_direction="invert" 로 저장되어
    추론 시 확률을 1-p 로 반전한다 (KOSDAQ 신호 반전 발견 2026-04-25).
  - 리포트: runtime_state/reports/learning/retrain_v2_report.json|md
"""

import json
import os
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager
from modules.horizon_policy import horizon_days_from_return_col, resolve_horizon_policy
from modules.loss_risk_features import compute_loss_risk_features


def _pct_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _parse_vol(value):
    try:
        return float(str(value).replace("✅", "").replace("⚠️", "").replace("x", "").strip())
    except Exception:
        return np.nan


def _infer_submarket(ticker: str, market_type: str, strategy_family: str) -> str:
    t = str(ticker or "").upper()
    mt = str(market_type or "").upper()
    sf = str(strategy_family or "").upper()
    if t.endswith(".KS"):
        return "KOSPI"
    if t.endswith(".KQ"):
        return "KOSDAQ"
    if mt == "AMEX" or sf == "AMEX_MOONSHOT":
        return "AMEX"
    if mt == "US":
        return "NASDAQ"
    if mt == "KR":
        return "KR"
    return mt or "UNKNOWN"


def load_scan_archive() -> pd.DataFrame:
    """Load enriched scan archive from Supabase with pagination."""
    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")

    select_cols = (
        "id,run_id,ticker,stock_name,created_at,market_type,scan_mode,strategy_family,"
        "priority_rank,decision,decision_bucket,outcome_status,"
        "alpha_score,tech_score,ml_prob,prob_clean,whale_score,trend,tier,volume,volume_ratio,volume_confirmed,position,"
        "strategy,decision_score,fund_status,entry_reference_price,inference_failed,"
        "feature_origin,feature_quality,feature_completeness,feature_missing_fields,"
        "market_gate,scanner_timeframe_profile,kr_universe_role,selection_lane,rationale,theme_risk,"
        "validation_excluded,validation_excluded_reason,is_dummy_data,"
        "return_close_pct,return_1d_pct,return_2d_pct,return_3d_pct,return_5d_pct,return_7d_pct"
    )

    rows = []
    page = 0
    page_size = 1000
    while True:
        res = (
            db.client.table("market_scan_results")
            .select(select_cols)
            .order("created_at", desc=False)
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        print(f"  로드: {len(rows)} 레코드", end="\r")
        if len(batch) < page_size:
            break
        page += 1

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("market_scan_results is empty.")

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True).dt.tz_convert(None)
    df["scan_date"] = df["created_at"].dt.date
    df["scan_mode"] = df.get("scan_mode", "SWING").fillna("SWING").astype(str).str.upper()
    df["strategy_family"] = df.get("strategy_family", "").fillna("").astype(str)
    df["market_subtype"] = [
        _infer_submarket(ticker, market_type, strategy_family)
        for ticker, market_type, strategy_family in zip(
            df.get("ticker", pd.Series(dtype=str)),
            df.get("market_type", pd.Series(dtype=str)),
            df.get("strategy_family", pd.Series(dtype=str)),
        )
    ]

    # Deduplicate: outcome sync appends rows each run rather than updating, so the
    # same (run_id, ticker, scan_mode, priority_rank) key can have a scan row (with
    # alpha/volume/tech/whale features but no returns) AND an outcome-sync stub (with
    # returns + outcome_status but empty scan-time features). Earlier logic sorted by
    # _return_present and kept last → it always picked the stub and threw the scan
    # row's features away. Now: keep the scan row as the feature-bearing base and
    # overlay returns + outcome_status from any stub in the same group.
    sort_cols = ["created_at", "id"] if "id" in df.columns else ["created_at"]
    df = df.sort_values(sort_cols)

    # Build dedup key: run_id preferred, fallback to scan_date.
    if "run_id" in df.columns:
        df["_dedup_run"] = df["run_id"].fillna(df["scan_date"].astype(str))
    else:
        df["_dedup_run"] = df["scan_date"].astype(str)

    dedup_key = [c for c in ["_dedup_run", "ticker", "scan_mode", "priority_rank"] if c in df.columns]

    alpha_num = pd.to_numeric(df.get("alpha_score", pd.Series(index=df.index)), errors="coerce")
    df["_has_alpha"] = alpha_num.gt(0).astype(int)
    # _has_return: ANY return horizon present, not just 3d. Earlier check on
    # return_3d_pct alone excluded outcome stubs that only carry 5d/7d returns
    # (KOSDAQ SWING uses 5d label) — they then never made it into the overlay
    # set so scanner peers stayed unlabeled.
    return_horizons = [c for c in ("return_close_pct","return_1d_pct","return_2d_pct","return_3d_pct","return_5d_pct","return_7d_pct") if c in df.columns]
    if return_horizons:
        df["_has_return"] = df[return_horizons].notna().any(axis=1).astype(int)
    else:
        df["_has_return"] = 0

    # Base pick: rows with scan-time features (alpha > 0). _has_alpha is the top
    # sort key so alpha-bearing rows always sort last (0s then 1s) and survive
    # keep="last". sort_cols act as the tie-breaker within the same alpha tier, so
    # among multiple scan rows we keep the newest. Fallback when a group has no
    # alpha row at all: newest stub wins and we still label it from returns.
    base = (
        df.sort_values(["_has_alpha"] + sort_cols)
        .drop_duplicates(subset=dedup_key, keep="last")
        .set_index(dedup_key)
    )

    # Overlay cols from the newest return-bearing row (stub or full scan row).
    # Also overlay outcome_status from any RESOLVED stub — base may be a scanner
    # row with outcome_status=NULL even though a sibling outcome-sync stub holds
    # outcome_status='RESOLVED'. Without this overlay, _is_resolved() drops the
    # row from training. Same for volume_ratio/volume_confirmed (outcome stubs
    # carry the values that backfill produced, not the original scanner row).
    overlay_cols = [
        c for c in [
            "return_close_pct", "return_1d_pct", "return_2d_pct",
            "return_3d_pct", "return_5d_pct", "return_7d_pct",
            "outcome_status",
            "volume_ratio", "volume_confirmed",
        ] if c in df.columns
    ]
    if overlay_cols:
        # 1) Returns/outcome from any stub or scan row that carries them.
        overlay = (
            df[df["_has_return"].eq(1)]
            .sort_values(sort_cols)
            .drop_duplicates(subset=dedup_key, keep="last")
            .set_index(dedup_key)[overlay_cols]
        )
        for col in overlay_cols:
            base[col] = base[col].where(base[col].notna(), overlay[col])
        # 2) outcome_status separately: any RESOLVED row in the group wins, even
        # if that row had no return (e.g. EXPIRED stub overwritten by RESOLVED
        # peer). This fixes the case where scanner_full row has outcome=NULL and
        # outcome_sync_partial stub has outcome=RESOLVED but no peer was matched.
        if "outcome_status" in df.columns:
            resolved_overlay = (
                df[df["outcome_status"].fillna("").str.upper().eq("RESOLVED")]
                .sort_values(sort_cols)
                .drop_duplicates(subset=dedup_key, keep="last")
                .set_index(dedup_key)[["outcome_status"]]
            )
            base["outcome_status"] = base["outcome_status"].where(
                base["outcome_status"].fillna("").str.upper().eq("RESOLVED"),
                resolved_overlay["outcome_status"],
            )

    df = base.reset_index().drop(columns=["_dedup_run", "_has_alpha", "_has_return"], errors="ignore")

    # Cross-group fill on (ticker, scan_date, scan_mode, priority_rank): when an
    # outcome_sync stub lives in run_id=A and the scanner_full peer lives in
    # run_id=B, the dedup above leaves both as separate rows. Each is missing
    # what the other has (alpha vs return/outcome). Without this pass, KOSDAQ
    # SWING training set drops to ~530 rows even though the DB holds 9,560
    # labeled candidates. We backfill missing fields cross-group, then drop
    # rows that still have neither alpha nor returns.
    cross_key = [c for c in ("ticker", "scan_date", "scan_mode", "priority_rank") if c in df.columns]
    if cross_key:
        cross_overlay_cols = [
            c for c in (
                "alpha_score", "tech_score", "ml_prob", "whale_score",
                "prob_clean",
                "tier", "trend", "position", "volume", "volume_ratio",
                "volume_confirmed", "decision_score", "fund_status",
                "market_gate", "scanner_timeframe_profile", "kr_universe_role", "selection_lane",
                "return_close_pct", "return_1d_pct", "return_2d_pct",
                "return_3d_pct", "return_5d_pct", "return_7d_pct",
                "outcome_status", "feature_origin",
            ) if c in df.columns
        ]
        if cross_overlay_cols:
            sub_sort = [c for c in ("created_at", "id") if c in df.columns]
            for col in cross_overlay_cols:
                source_cols = cross_key + [col] + [c for c in sub_sort if c not in cross_key and c != col]
                source = (
                    df.loc[df[col].notna(), source_cols]
                    .sort_values(sub_sort)
                    .drop_duplicates(subset=cross_key, keep="last")
                )
                if source.empty:
                    continue
                lookup = source.set_index(cross_key)[col]
                idx = pd.MultiIndex.from_frame(df[cross_key])
                filler = lookup.reindex(idx).values
                df[col] = df[col].where(df[col].notna(), filler)

    df = _derive_features_from_archive(df)
    before_count = len(rows)
    print(f"\n✅ 총 {len(df):,} 레코드 (중복 제거 후, 원본 {before_count:,}행) — derived {sum(c in df.columns for c in FEATURE_COLS)}/{len(FEATURE_COLS)} feature columns")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in [
        "alpha_score",
        "tech_score",
        "ml_prob",
        "whale_score",
        "decision_score",
        "entry_reference_price",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    volume_from_text = df.get("volume", pd.Series(index=df.index, dtype=object)).apply(_parse_vol)
    if "volume_ratio" in df.columns:
        df["vol_float"] = pd.to_numeric(df["volume_ratio"], errors="coerce").combine_first(volume_from_text)
    else:
        df["vol_float"] = volume_from_text
    if "volume_confirmed" in df.columns:
        vol_confirmed = df["volume_confirmed"]
        if vol_confirmed.dtype == "object":
            df["vol_confirmed"] = vol_confirmed.astype(str).str.lower().isin({"true", "1", "yes"}).astype(int)
        else:
            df["vol_confirmed"] = vol_confirmed.fillna(False).astype(int)
    else:
        df["vol_confirmed"] = df.get("volume", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.startswith("✅").astype(int)
    df["vol_gt25x"] = (df["vol_float"] > 2.5).astype(int)
    df["vol_18_25x"] = ((df["vol_float"] > 1.8) & (df["vol_float"] <= 2.5)).astype(int)
    df["vol_08_18x"] = ((df["vol_float"] >= 0.8) & (df["vol_float"] <= 1.8)).astype(int)
    df["vol_lt05x"] = (df["vol_float"] < 0.5).astype(int)

    pos = df.get("position", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    strat = df.get("strategy", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    trend = df.get("trend", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.upper()
    tier = df.get("tier", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    fund = df.get("fund_status", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)

    df["is_rising"] = pos.str.contains("Rising", na=False).astype(int)
    df["is_peak"] = pos.str.contains("Peak", na=False).astype(int)
    df["is_resting"] = pos.str.contains("Resting", na=False).astype(int)
    df["is_bottom"] = pos.str.contains("Bottom", na=False).astype(int)

    df["is_uptrend"] = trend.eq("UP").astype(int)
    df["is_downtrend"] = trend.eq("DOWN").astype(int)
    df["is_sideways"] = trend.eq("SIDEWAYS").astype(int)

    df["is_overheat"] = strat.str.contains("단기과열|Overheat|Exhaustion", case=False, na=False).astype(int)
    df["is_rsidiv"] = strat.str.contains("RSI_DIV", na=False).astype(int)
    df["is_obvdiv"] = strat.str.contains("OBV_DIV", na=False).astype(int)
    df["is_momentum"] = strat.str.contains("Momentum", na=False).astype(int)
    df["is_contract"] = strat.str.contains("공급계약|계약|수주", na=False).astype(int)
    df["is_breakout"] = strat.str.contains("돌파|Breakout|Continuation", case=False, na=False).astype(int)

    df["tier_t0"] = tier.str.contains("⚡", na=False).astype(int)
    df["tier_t1"] = tier.str.contains("🏆", na=False).astype(int)
    df["tier_t2"] = tier.str.contains("⭐", na=False).astype(int)
    df["fund_positive"] = fund.str.contains("양호|Positive|Strong", case=False, na=False).astype(int)

    price = pd.to_numeric(df["entry_reference_price"], errors="coerce")
    df["is_sub7"] = price.gt(0) & price.le(7)
    df["price_7_15"] = price.gt(7) & price.le(15)
    df["price_gt15"] = price.gt(15)
    df["is_sub7"] = df["is_sub7"].astype(int)
    df["price_7_15"] = df["price_7_15"].astype(int)
    df["price_gt15"] = df["price_gt15"].astype(int)

    market_subtype = df["market_subtype"].fillna("UNKNOWN").astype(str)
    df["is_kospi"] = market_subtype.eq("KOSPI").astype(int)
    df["is_kosdaq"] = market_subtype.eq("KOSDAQ").astype(int)
    df["is_nasdaq"] = market_subtype.eq("NASDAQ").astype(int)
    df["is_amex"] = market_subtype.eq("AMEX").astype(int)
    df["scan_intraday"] = df["scan_mode"].eq("INTRADAY").astype(int)
    df["scan_swing"] = df["scan_mode"].eq("SWING").astype(int)

    fam = df["strategy_family"].str.upper()
    df["fam_kr_core"] = fam.eq("KR_CORE").astype(int)
    df["fam_us_main"] = fam.eq("US_MAIN").astype(int)
    df["fam_amex_moonshot"] = fam.eq("AMEX_MOONSHOT").astype(int)

    # Decision bucket one-hots: learning segment mixes picked / watchlist /
    # exception_leader rows with very different distributions (picked is the
    # real production path; exception_leader is 70% of rows and lacks
    # tech/whale/vol entirely). Without this signal the model blends three
    # populations into one mean.
    bucket = df.get("decision_bucket", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.lower()
    df["is_picked"] = bucket.eq("picked").astype(int)
    df["is_watchlist"] = bucket.eq("watchlist").astype(int)
    df["is_exception_leader"] = bucket.eq("exception_leader").astype(int)

    df["peak_x_highvol"] = df["is_peak"] * df["vol_gt25x"]
    df["overheat_x_uptrend"] = df["is_overheat"] * df["is_uptrend"]
    df["sub7_x_breakout"] = df["is_sub7"] * df["is_breakout"]

    # Market cap band: derive only from a real archive value. Missing market cap is
    # intentionally excluded from FEATURE_COLS so it cannot become a dummy midpoint.
    if "marcap_band" in df.columns:
        df["marcap_band"] = pd.to_numeric(df["marcap_band"], errors="coerce").fillna(2).astype(int)
    elif "marcap" in df.columns:
        mc = pd.to_numeric(df["marcap"], errors="coerce")
        df["marcap_band"] = pd.cut(
            mc,
            bins=[0, 300e9, 1e12, 5e12, 20e12, float("inf")],
            labels=[0, 1, 2, 3, 4],
            right=False,
        ).cat.add_categories([2]).fillna(2).astype(int)
    else:
        df["marcap_band"] = np.nan

    marcap = pd.to_numeric(df["marcap_band"], errors="coerce")
    df["marcap_micro"] = marcap.eq(0).fillna(False).astype(int)
    df["marcap_small"] = marcap.eq(1).fillna(False).astype(int)
    df["marcap_mid"] = marcap.eq(2).fillna(False).astype(int)
    df["marcap_large"] = marcap.eq(3).fillna(False).astype(int)
    df["marcap_mega"] = marcap.eq(4).fillna(False).astype(int)

    role = df.get("kr_universe_role", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.upper()
    role = role.where(role.ne(""))
    role = role.fillna(
        pd.Series(
            np.where(df["is_kospi"].eq(1), "CORE_TREND", np.where(df["is_kosdaq"].eq(1), "EXPLOSIVE_LEADER", "")),
            index=df.index,
        )
    )
    df["role_core_trend"] = role.eq("CORE_TREND").astype(int)
    df["role_explosive_leader"] = role.eq("EXPLOSIVE_LEADER").astype(int)
    df["role_transitional"] = role.eq("TRANSITIONAL").astype(int)
    df["role_reject_risk"] = role.eq("REJECT_RISK").astype(int)

    risk_rows = [
        compute_loss_risk_features(
            market_subtype=row.get("market_subtype"),
            alpha_score=row.get("alpha_score"),
            tech_score=row.get("tech_score"),
            whale_score=row.get("whale_score"),
            ml_prob=row.get("ml_prob"),
            prob_clean=row.get("prob_clean"),
            volume_ratio=row.get("volume_ratio"),
            volume_confirmed=row.get("volume_confirmed"),
            position=row.get("position"),
            tier=row.get("tier"),
            trend=row.get("trend"),
        )
        for _, row in df.iterrows()
    ]
    risk_df = pd.DataFrame(risk_rows, index=df.index)
    for col in LOSS_RISK_FEATURE_COLS:
        df[col] = pd.to_numeric(risk_df[col], errors="coerce").fillna(0.0)

    return df


_OHLCV_CACHE: Dict[str, "pd.DataFrame"] = {}
_INDEX_CACHE: Dict[str, "pd.DataFrame"] = {}


def _fetch_index_window(index_symbol: str, scan_dt: "datetime") -> Optional["pd.DataFrame"]:
    """Fetch ~45 days of index OHLCV ending at scan_dt. Cached per (symbol, date)."""
    try:
        import yfinance as yf
    except ImportError:
        return None
    cache_key = f"{index_symbol}|{scan_dt.date().isoformat()}"
    if cache_key in _INDEX_CACHE:
        return _INDEX_CACHE[cache_key]
    end = scan_dt + timedelta(days=1)
    start = scan_dt - timedelta(days=70)
    try:
        hist = yf.Ticker(index_symbol).history(start=start, end=end, auto_adjust=False)
    except Exception:
        _INDEX_CACHE[cache_key] = None
        return None
    if hist is None or hist.empty or len(hist) < 5:
        _INDEX_CACHE[cache_key] = None
        return None
    _INDEX_CACHE[cache_key] = hist
    return hist


def _fetch_ohlcv_window(ticker: str, scan_dt: "datetime") -> Optional["pd.DataFrame"]:
    """Fetch ~45 trading days ending at scan_dt for engineered features.

    Cached per ticker for the full retrain run — many rows share the same
    ticker. Pure pre-scan: never returns bars after scan_dt.
    """
    try:
        import yfinance as yf
    except ImportError:
        return None
    cache_key = f"{ticker}|{scan_dt.date().isoformat()}"
    if cache_key in _OHLCV_CACHE:
        return _OHLCV_CACHE[cache_key]
    end = scan_dt + timedelta(days=1)
    start = scan_dt - timedelta(days=70)
    try:
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    except Exception:
        _OHLCV_CACHE[cache_key] = None
        return None
    if hist is None or hist.empty or len(hist) < 5:
        _OHLCV_CACHE[cache_key] = None
        return None
    _OHLCV_CACHE[cache_key] = hist
    return hist


def _safe_ratio(num: float, den: float, default: float = 0.0) -> float:
    try:
        if den is None or den == 0:
            return default
        return float(num) / float(den)
    except Exception:
        return default


def derive_ohlcv_features(df: pd.DataFrame, *, target_mask: Optional[pd.Series] = None,
                            verbose: bool = True) -> pd.DataFrame:
    """Add scan-time OHLCV-derived features to df.

    All features are computed strictly from bars on or before scan_date — never
    leaks future returns. Designed for KOSDAQ swing where the model collapsed
    onto alpha_score (importance 489) because no leading indicators were in
    FEATURE_COLS. Adds:
      - prev_pct_change_1d / 5d  : trailing return over 1d / 5d (mean-reversion)
      - gap_open_pct             : open vs prev close (overnight gap)
      - volatility_5d / 20d      : stdev of daily returns (regime)
      - obv_slope_5d             : OBV linear slope last 5 bars (accumulation)
      - rsi_14                   : 14-day Wilder RSI (overbought/oversold)
      - atr_pct_14               : 14-day ATR / close (volatility-normalized)

    target_mask: only fetch OHLCV for these rows (cost control). Others get NaN.
    """
    horizons = ["prev_pct_change_1d", "prev_pct_change_5d", "gap_open_pct",
                "volatility_5d", "volatility_20d", "obv_slope_5d",
                "rsi_14", "atr_pct_14",
                "kospi_index_5d_return", "kosdaq_index_5d_return",
                "kosdaq_kospi_spread_5d",
                "kospi_momentum_score", "kosdaq_low_vol_score"]
    for col in horizons:
        if col not in df.columns:
            df[col] = np.nan

    if target_mask is None:
        target_mask = pd.Series(True, index=df.index)

    rows_to_process = df[target_mask & df["ticker"].notna() & df["scan_date"].notna()]
    if rows_to_process.empty:
        return df
    if verbose:
        print(f"  Fetching OHLCV for {len(rows_to_process):,} rows (cached per ticker+date)")

    processed = 0
    fetched = 0
    failed = 0
    for idx, row in rows_to_process.iterrows():
        ticker = str(row["ticker"])
        scan_d = row["scan_date"]
        if hasattr(scan_d, "year"):
            scan_dt = datetime(scan_d.year, scan_d.month, scan_d.day)
        else:
            try:
                scan_dt = datetime.fromisoformat(str(scan_d)[:10])
            except Exception:
                failed += 1
                continue
        hist = _fetch_ohlcv_window(ticker, scan_dt)
        processed += 1
        if hist is None:
            failed += 1
            continue
        fetched += 1
        try:
            closes = pd.to_numeric(hist["Close"], errors="coerce").dropna()
            opens = pd.to_numeric(hist["Open"], errors="coerce").dropna()
            highs = pd.to_numeric(hist["High"], errors="coerce")
            lows = pd.to_numeric(hist["Low"], errors="coerce")
            vols = pd.to_numeric(hist["Volume"], errors="coerce").fillna(0)
            if len(closes) < 2:
                continue
            last_close = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2])
            df.at[idx, "prev_pct_change_1d"] = round((last_close / prev_close - 1) * 100, 4)
            if len(closes) >= 6:
                df.at[idx, "prev_pct_change_5d"] = round((last_close / float(closes.iloc[-6]) - 1) * 100, 4)
            if len(opens) >= 1 and len(closes) >= 2:
                last_open = float(opens.iloc[-1])
                df.at[idx, "gap_open_pct"] = round((last_open / prev_close - 1) * 100, 4)
            daily_ret = closes.pct_change().dropna()
            if len(daily_ret) >= 5:
                df.at[idx, "volatility_5d"] = round(float(daily_ret.tail(5).std()) * 100, 4)
            if len(daily_ret) >= 20:
                df.at[idx, "volatility_20d"] = round(float(daily_ret.tail(20).std()) * 100, 4)
            if len(closes) >= 5:
                close_diff = closes.diff().fillna(0)
                obv = (np.sign(close_diff) * vols).cumsum()
                obv_tail = obv.tail(5)
                if len(obv_tail) >= 5 and obv_tail.std() > 0:
                    x = np.arange(len(obv_tail))
                    slope = float(np.polyfit(x, obv_tail.values, 1)[0])
                    df.at[idx, "obv_slope_5d"] = round(slope / max(abs(obv_tail.mean()), 1e-9), 6)
            if len(closes) >= 15:
                delta = closes.diff().dropna()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                if loss.iloc[-1] > 0:
                    rs = gain.iloc[-1] / loss.iloc[-1]
                    df.at[idx, "rsi_14"] = round(100 - 100 / (1 + rs), 2)
                else:
                    df.at[idx, "rsi_14"] = 100.0
            if len(closes) >= 15:
                tr = pd.concat([
                    (highs - lows).abs(),
                    (highs - closes.shift(1)).abs(),
                    (lows - closes.shift(1)).abs(),
                ], axis=1).max(axis=1)
                atr = tr.rolling(14).mean().iloc[-1]
                if pd.notna(atr) and last_close > 0:
                    df.at[idx, "atr_pct_14"] = round(float(atr) / last_close * 100, 4)
            # Market regime: KOSPI/KOSDAQ index 5d returns and the spread between
            # them. Index data shared across all KR rows for the same scan date,
            # so cache hit rate is 1 fetch per unique scan_date per index.
            kospi_hist = _fetch_index_window("^KS11", scan_dt)
            kosdaq_hist = _fetch_index_window("^KQ11", scan_dt)
            kospi_5d = kosdaq_5d = None
            if kospi_hist is not None and len(kospi_hist) >= 6:
                kc = pd.to_numeric(kospi_hist["Close"], errors="coerce").dropna()
                if len(kc) >= 6:
                    kospi_5d = round((float(kc.iloc[-1]) / float(kc.iloc[-6]) - 1) * 100, 4)
                    df.at[idx, "kospi_index_5d_return"] = kospi_5d
            if kosdaq_hist is not None and len(kosdaq_hist) >= 6:
                qc = pd.to_numeric(kosdaq_hist["Close"], errors="coerce").dropna()
                if len(qc) >= 6:
                    kosdaq_5d = round((float(qc.iloc[-1]) / float(qc.iloc[-6]) - 1) * 100, 4)
                    df.at[idx, "kosdaq_index_5d_return"] = kosdaq_5d
            if kospi_5d is not None and kosdaq_5d is not None:
                df.at[idx, "kosdaq_kospi_spread_5d"] = round(kosdaq_5d - kospi_5d, 4)
            # Composite scores from winner_pattern_research (2026-05-06).
            # KOSPI swing winners are momentum-driven; KOSDAQ swing winners
            # are low-vol surges. Both composites are computed for every row;
            # is_kospi / is_kosdaq one-hots let the model use the right one.
            rsi_v = df.at[idx, "rsi_14"]
            mom5_v = df.at[idx, "prev_pct_change_5d"]
            if pd.notna(rsi_v) and pd.notna(mom5_v):
                df.at[idx, "kospi_momentum_score"] = round(float(rsi_v) + float(mom5_v) * 2.0, 4)
            vol20_v = df.at[idx, "volatility_20d"]
            atr_v = df.at[idx, "atr_pct_14"]
            if pd.notna(vol20_v) and pd.notna(atr_v):
                df.at[idx, "kosdaq_low_vol_score"] = round(-(float(vol20_v) + float(atr_v)), 4)
        except Exception:
            continue
        if verbose and processed % 200 == 0:
            print(f"    progress: {processed}/{len(rows_to_process)} fetched={fetched} failed={failed}")

    if verbose:
        print(f"  OHLCV done: fetched={fetched} failed={failed} cached_keys={len(_OHLCV_CACHE)}")
    return df


LOSS_RISK_FEATURE_COLS = [
    "alpha_prob_gap",
    "tech_prob_gap",
    "whale_prob_gap",
    "model_prob_disagreement",
    "low_prob_high_alpha_risk",
    "clean_prob_high_alpha_risk",
    "model_prob_disagreement_risk",
    "weak_volume_high_alpha_risk",
    "chase_low_prob_risk",
    "kosdaq_tier_chase_risk",
    "kosdaq_clean_chase_risk",
    "uptrend_low_support_risk",
    "missing_core_trace_risk",
    "loss_risk_score",
]


FEATURE_COLS = [
    "alpha_score",
    # "tech_score" removed: exact duplicate of alpha_score at inference time
    # "ml_prob" removed 2026-04-22: circular reference (phase25 model consuming its own upstream prediction → 50-fallback leakage at inference)
    # "whale_score" removed: 0% fill rate in RESOLVED rows — always NaN→0 noise
    # "decision_score" removed: circular reference (alpha*0.58 + ml_prob*0.32 → stored as feature for same model)
    # "vol_float" removed 2026-04-25: continuous volume_ratio is 0% filled in RESOLVED
    # rows. The four discrete buckets below carry the same information when
    # vol_float is known and silently encode "0 across all four = missing"
    # when it isn't. Keeping vol_float as a feature would drop 90% of usable
    # training rows on the NaN gate.
    "vol_confirmed",
    "vol_gt25x",
    "vol_18_25x",
    "vol_08_18x",
    "vol_lt05x",
    "is_rising",
    "is_peak",
    "is_resting",
    "is_bottom",
    "is_uptrend",
    "is_downtrend",
    "is_sideways",
    "is_overheat",
    "is_rsidiv",
    "is_obvdiv",
    "is_momentum",
    "is_contract",
    "is_breakout",
    "tier_t0",
    "tier_t1",
    "tier_t2",
    "fund_positive",
    "is_sub7",
    "price_7_15",
    "price_gt15",
    "marcap_micro",
    "marcap_small",
    "marcap_mid",
    "marcap_large",
    "marcap_mega",
    "role_core_trend",
    "role_explosive_leader",
    "role_transitional",
    "role_reject_risk",
    "is_kospi",
    "is_kosdaq",
    "is_nasdaq",
    "is_amex",
    "scan_intraday",
    "scan_swing",
    "fam_kr_core",
    "fam_us_main",
    "fam_amex_moonshot",
    "is_picked",
    "is_watchlist",
    "is_exception_leader",
    "peak_x_highvol",
    "overheat_x_uptrend",
    "sub7_x_breakout",
    *LOSS_RISK_FEATURE_COLS,
    # OHLCV-derived leading indicators added 2026-04-28 to break alpha_score
    # monoculture in KOSDAQ swing (alpha importance was 489 vs second-place 78).
    # All computed strictly from bars on or before scan_date — no leakage.
    "prev_pct_change_1d",
    "prev_pct_change_5d",
    "gap_open_pct",
    "volatility_5d",
    "volatility_20d",
    "obv_slope_5d",
    "rsi_14",
    "atr_pct_14",
    # Market regime indicators added 2026-04-28: KR index returns and the
    # KOSDAQ-KOSPI spread. KOSDAQ swing is highly regime-dependent — the +5%
    # threshold positive rate swings between fold 1 (val_win=0%) and fold 2
    # (val_win=72%) precisely because KOSDAQ market regime changed between
    # those time windows. These features tell the model what regime it's in.
    "kospi_index_5d_return",
    "kosdaq_index_5d_return",
    "kosdaq_kospi_spread_5d",
    # Composite features added 2026-05-06 from winner_pattern_research findings:
    #   KOSPI swing winners (5d ≥+10%): rsi_14 ↑ AND prev_pct_change_5d ↑
    #     replicated cohens_d 0.40/0.37 disc→val.
    #   KOSDAQ swing winners (5d ≥+10%): volatility_20d ↓ AND atr_pct_14 ↓
    #     (low-vol surge pattern), replicated d -0.47/-0.41.
    # is_kospi/is_kosdaq one-hots route the model to the right composite.
    "kospi_momentum_score",
    "kosdaq_low_vol_score",
    # marcap_band itself stays excluded; the model consumes explicit one-hot
    # bands above so missing real market-cap data remains all-zero.
]


@dataclass
class SegmentSpec:
    name: str
    model_path: str
    return_col: str
    positive_threshold: float
    min_rows: int
    min_positive: int
    filter_fn: object
    description: str
    signal_direction: str = "auto"


def _is_resolved(df: pd.DataFrame) -> pd.Series:
    """Only train on RESOLVED outcomes — PENDING rows have no real labels yet."""
    if "outcome_status" in df.columns:
        return df["outcome_status"].fillna("").str.upper().eq("RESOLVED")
    return pd.Series(True, index=df.index)


def _has_features(df: pd.DataFrame) -> pd.Series:
    """Require columns that actually feed FEATURE_COLS before training.

    tech_score/whale_score/volume_ratio/decision_score were dropped from
    FEATURE_COLS (leakage / noise / circular). Gating on them blocked >99% of
    KR archive rows that have valid alpha_score + engineered fields. Now we
    only require what the model actually consumes.
    """
    mask = pd.Series(True, index=df.index)
    for col in ["alpha_score"]:
        if col not in df.columns:
            return pd.Series(False, index=df.index)
        mask &= pd.to_numeric(df[col], errors="coerce").notna()
    # vol_float / volume_ratio dropped from gate 2026-04-25: 0% filled in
    # RESOLVED rows (outcome-sync path never wrote them). Requiring them blocked
    # all training. Discrete vol_* flags absorb the "missing" case as zeros.
    # trend/tier dropped from gate: derived flags (is_uptrend, tier_t0..) already
    # encode missingness as 0 in engineer_features. Requiring them blocked >80%
    # of historical archive rows that have alpha_score + returns but lack the
    # tier emoji string.
    if "inference_failed" in df.columns:
        mask &= ~df["inference_failed"].fillna(False).astype(bool)
    # validation_excluded / feature_quality dropped from gate 2026-04-25:
    # historical export tagged 100% of KR SWING RESOLVED rows as
    # validation_excluded=True / feature_quality=incomplete because volume_ratio
    # was always missing. That flag now blocks every row that has a real label
    # — exactly the data we need to train on.
    if "is_dummy_data" in df.columns:
        raw = df["is_dummy_data"]
        dummy = raw.astype(str).str.lower().isin({"true", "1", "yes"}) if raw.dtype == "object" else raw.fillna(False).astype(bool)
        mask &= ~dummy
    return mask


# 2026-05-08 (swing-main-01i): horizon 진단 quintile 분석 결과 단일-segment
# 4개 모델은 모두 production에서 신호를 못 만든다 — phase25_kospi_swing 정렬
# +0.6pp(무용), phase25_kosdaq_swing -14.2pp(INVERTED), phase25_kospi_intraday
# 학습 표본 부족, phase25_kosdaq_intraday raw_auc 0.27(random 미만, 4월 inverted
# 운영 사례). 통합 모델(phase25_kr_*_xgboost) 정렬 +8~+15pp 작동.
# 환경변수 AG_PHASE25_DISABLE_SEGMENTS=0이면 옛 동작 복원 (rollback용).
import os as _os_for_segments
_DISABLE_SINGLE_SEGMENTS = _os_for_segments.getenv(
    "AG_PHASE25_DISABLE_SEGMENTS", "1"
).strip() not in ("0", "", "false", "False")

_BASE_SEGMENTS = [
    SegmentSpec(
        name="phase25_global",
        model_path="models/phase25_model.pkl",
        return_col="return_3d_pct",
        positive_threshold=5.0,
        min_rows=300,
        min_positive=60,
        filter_fn=lambda df: _is_resolved(df) & _has_features(df) & df["return_3d_pct"].notna(),
        description="Global compatibility model using realized 3D >= +5%.",
    ),
]

_SINGLE_SEGMENT_SPECS = [
    SegmentSpec(
        name="phase25_kospi_swing",
        model_path="models/phase25_kospi_swing.pkl",
        return_col=str(resolve_horizon_policy("KOSPI", "SWING")["return_col"]),
        positive_threshold=5.0,
        min_rows=300,
        min_positive=60,
        filter_fn=lambda df: _is_resolved(df) & _has_features(df) & df["market_subtype"].eq("KOSPI") & df["scan_mode"].eq("SWING") & df[str(resolve_horizon_policy("KOSPI", "SWING")["return_col"])].notna(),
        description="KOSPI swing model: large-cap momentum-persistent (signals directionally correct).",
    ),
    SegmentSpec(
        name="phase25_kosdaq_swing",
        model_path="models/phase25_kosdaq_swing.pkl",
        return_col=str(resolve_horizon_policy("KOSDAQ", "SWING")["return_col"]),
        positive_threshold=5.0,
        min_rows=300,
        min_positive=60,
        filter_fn=lambda df: _is_resolved(df) & _has_features(df) & df["market_subtype"].eq("KOSDAQ") & df["scan_mode"].eq("SWING") & df[str(resolve_horizon_policy("KOSDAQ", "SWING")["return_col"])].notna(),
        description="KOSDAQ swing model: small/mid-cap, mean-reverting at 3d (median +0.7%) but trends emerge at 5d (median +3.1%, mean +5.0%). Switched horizon 3d→5d so the model targets the timeframe where KOSDAQ surge signals actually materialize; 42% positive rate at +5% threshold is a balanced binary.",
    ),
    SegmentSpec(
        name="phase25_kospi_intraday",
        model_path="models/phase25_kospi_intraday.pkl",
        return_col="return_1d_pct",
        positive_threshold=0.0,
        min_rows=300,
        min_positive=60,
        filter_fn=lambda df: _is_resolved(df) & _has_features(df) & df["market_subtype"].eq("KOSPI") & df["scan_mode"].eq("INTRADAY") & df["return_1d_pct"].notna(),
        description="KOSPI intraday model using next-day positive return.",
    ),
    SegmentSpec(
        name="phase25_kosdaq_intraday",
        model_path="models/phase25_kosdaq_intraday.pkl",
        return_col="return_1d_pct",
        positive_threshold=0.0,
        min_rows=300,
        min_positive=60,
        filter_fn=lambda df: _is_resolved(df) & _has_features(df) & df["market_subtype"].eq("KOSDAQ") & df["scan_mode"].eq("INTRADAY") & df["return_1d_pct"].notna(),
        description="KOSDAQ intraday model using next-day positive return (auto-inverts when val AUC<0.5).",
    ),
]

SEGMENTS = list(_BASE_SEGMENTS) + ([] if _DISABLE_SINGLE_SEGMENTS else list(_SINGLE_SEGMENT_SPECS))


def _choose_model_backend():
    try:
        import lightgbm as lgb

        return "lgb", lgb
    except Exception:
        try:
            from xgboost import XGBClassifier  # noqa: F401

            return "xgb", None
        except Exception:
            return "rf", None


def _fit_model(X_train_s, y_train, backend):
    pos_ratio = max(float(y_train.mean()), 1e-6)
    class_weight = max((1 - pos_ratio) / pos_ratio, 1.0)
    if backend == "lgb":
        import lightgbm as lgb

        # Conservative config for small segments (300~500 rows). Earlier settings
        # (n_estimators=400, num_leaves=31, no regularization) overfit and produced
        # OOS AUC=0.38 with CV fold variance 0.18~0.32. Tightened trees, added L1/L2,
        # and row/col subsampling to force the model toward the signals that actually
        # generalize across time windows.
        model = lgb.LGBMClassifier(
            n_estimators=200,
            learning_rate=0.03,
            max_depth=4,
            num_leaves=15,
            min_child_samples=20,
            reg_alpha=0.1,
            reg_lambda=1.0,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=5,
            scale_pos_weight=class_weight,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    elif backend == "xgb":
        from xgboost import XGBClassifier

        model = XGBClassifier(
            n_estimators=200,
            learning_rate=0.03,
            max_depth=3,
            min_child_weight=5,
            reg_alpha=0.1,
            reg_lambda=1.0,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=class_weight,
            random_state=42,
            n_jobs=-1,
            eval_metric="auc",
        )
    else:
        from sklearn.ensemble import RandomForestClassifier

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            class_weight={0: 1, 1: class_weight},
            random_state=42,
            n_jobs=-1,
        )
    model.fit(X_train_s, y_train)
    return model


def _threshold_sweep(prob, ret, target):
    rows = []
    for th in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60]:
        mask = prob >= th
        picks = int(mask.sum())
        if picks == 0:
            rows.append({"threshold": th, "picks": 0, "avg_return": None, "win_rate": None, "hit_rate": None})
            continue
        rows.append(
            {
                "threshold": th,
                "picks": picks,
                "avg_return": float(ret[mask].mean()),
                "win_rate": float((ret[mask] > 0).mean() * 100),
                "hit_rate": float((target[mask] == 1).mean() * 100),
            }
        )
    viable = [row for row in rows if row["picks"] >= 10 and row["avg_return"] is not None]
    best = max(viable, key=lambda row: (row["avg_return"], row["hit_rate"])) if viable else None
    return rows, best


def _walk_forward_cv(X: pd.DataFrame, y: pd.Series, ret: pd.Series, backend: str, n_folds: int = 3) -> List[dict]:
    """Expanding-window walk-forward CV: fold k trains on [0, start_k) and
    validates on [start_k, end_k). Each fold grows the training window,
    simulating production retraining where the model is updated as new
    data accumulates. Returns per-fold AUC to detect instability.
    """
    results = []
    n = len(X)
    initial_train = int(n * 0.55)
    val_block = max(50, (n - initial_train) // n_folds)
    for k in range(n_folds):
        train_end = initial_train + k * val_block
        val_end = min(train_end + val_block, n)
        if train_end >= val_end or train_end <= 0 or val_end > n:
            continue
        X_tr, y_tr = X.iloc[:train_end], y.iloc[:train_end]
        X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
        ret_val = ret.iloc[train_end:val_end]
        if y_tr.nunique() < 2 or y_val.nunique() < 2:
            continue
        scaler_k = StandardScaler()
        X_tr_s = scaler_k.fit_transform(X_tr)
        X_val_s = scaler_k.transform(X_val)
        model_k = _fit_model(X_tr_s, y_tr, backend)
        prob_k = model_k.predict_proba(X_val_s)[:, 1]
        try:
            auc_k = float(roc_auc_score(y_val, prob_k))
        except Exception:
            auc_k = float("nan")
        results.append({
            "fold": k,
            "train_size": int(len(X_tr)),
            "val_size": int(len(X_val)),
            "auc": auc_k,
            "val_win_rate": float((ret_val.to_numpy()[prob_k >= 0.5] > 0).mean() * 100) if (prob_k >= 0.5).any() else None,
        })
    return results


def train_segment(df_all: pd.DataFrame, spec: SegmentSpec, backend: str):
    segment_df = df_all[spec.filter_fn(df_all)].copy()
    if segment_df.empty:
        return {"name": spec.name, "status": "skipped", "reason": "no_rows"}

    segment_df = segment_df.sort_values("created_at").copy()
    segment_df["target"] = (pd.to_numeric(segment_df[spec.return_col], errors="coerce") >= spec.positive_threshold).astype(int)

    total_rows = len(segment_df)
    positive_rows = int(segment_df["target"].sum())
    if total_rows < spec.min_rows:
        return {"name": spec.name, "status": "skipped", "reason": "insufficient_rows", "rows": total_rows}
    if positive_rows < spec.min_positive:
        return {"name": spec.name, "status": "skipped", "reason": "insufficient_positive_rows", "rows": total_rows, "positives": positive_rows}

    feat_cols = [col for col in FEATURE_COLS if col in segment_df.columns]
    X = segment_df[feat_cols].apply(pd.to_numeric, errors="coerce")
    complete_x = ~X.isna().any(axis=1)
    if not complete_x.all():
        segment_df = segment_df.loc[complete_x].copy()
        X = X.loc[complete_x].copy()
        total_rows = len(segment_df)
        positive_rows = int(segment_df["target"].sum())
        if len(segment_df) < spec.min_rows:
            return {"name": spec.name, "status": "skipped", "reason": "feature_na_rows_removed", "rows": int(len(segment_df))}
        if positive_rows < spec.min_positive:
            return {"name": spec.name, "status": "skipped", "reason": "feature_na_positive_rows_removed", "rows": total_rows, "positives": positive_rows}
    y = segment_df["target"].astype(int)
    ret_series = pd.to_numeric(segment_df[spec.return_col], errors="coerce")

    # OOS holdout: last 15% is never seen during CV, used only for final eval.
    # Guards against silent regression when walk-forward CV folds all fall in
    # a benign regime.
    oos_idx = int(len(segment_df) * 0.85)
    X_dev, X_oos = X.iloc[:oos_idx], X.iloc[oos_idx:]
    y_dev, y_oos = y.iloc[:oos_idx], y.iloc[oos_idx:]
    ret_dev, ret_oos = ret_series.iloc[:oos_idx], ret_series.iloc[oos_idx:]

    cv_folds = _walk_forward_cv(X_dev, y_dev, ret_dev, backend, n_folds=3)

    # Walk-forward CV median is the most stable signal-direction reading: a
    # single val split can land either side of 0.5 in a borderline market.
    cv_aucs = [float(f.get("auc")) for f in cv_folds if f.get("auc") is not None and not pd.isna(f.get("auc"))]
    cv_median_auc = float(pd.Series(cv_aucs).median()) if cv_aucs else float("nan")

    split_idx = int(len(X_dev) * 0.7)
    if split_idx <= 0 or split_idx >= len(X_dev):
        return {"name": spec.name, "status": "skipped", "reason": "invalid_split", "rows": total_rows}

    X_train, X_val = X_dev.iloc[:split_idx], X_dev.iloc[split_idx:]
    y_train, y_val = y_dev.iloc[:split_idx], y_dev.iloc[split_idx:]
    ret_val = ret_dev.iloc[split_idx:]

    if y_train.nunique() < 2 or y_val.nunique() < 2:
        return {"name": spec.name, "status": "skipped", "reason": "single_class_validation", "rows": total_rows}

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    model = _fit_model(X_train_s, y_train, backend)
    y_prob_raw = model.predict_proba(X_val_s)[:, 1]
    raw_auc = float(roc_auc_score(y_val, y_prob_raw))

    # Signal direction: 'auto' uses walk-forward CV median AUC with a gray zone.
    # < 0.45 invert / > 0.55 normal / in between → 'uncertain' (downstream gates
    # must refuse to publish picks from an uncertain model). The 0.5±0.05 band
    # exists because a 0.531 CV median (KOSDAQ 2026-04-26) is statistically
    # indistinguishable from a coin flip and was previously routed to 'normal',
    # putting an unreliable model into production.
    if spec.signal_direction in ("invert", "normal", "uncertain"):
        signal_direction = spec.signal_direction
    else:
        # 2026-05-08 강화: cv_median_auc 단독 결정은 KOSDAQ INTRADAY 사례에서
        # 위험을 노출했다. raw_auc=0.274 / cv_median=0.579 일 때 normal로
        # 분류돼 운영 AVOID로 4월 726행을 차단했고 forward 결과가 win 78%로
        # 정확히 inverted였다. 두 지표가 크게 갈리면 모델 자체가 불안정한
        # 신호이므로 둘 다 0.55를 넘어야 normal, 하나라도 0.45 미만이면
        # invert, 나머지는 uncertain으로 한다. cv가 NaN이면 raw_auc로만 판정.
        if pd.isna(cv_median_auc):
            min_auc = max_auc = raw_auc
        else:
            min_auc = min(raw_auc, cv_median_auc)
            max_auc = max(raw_auc, cv_median_auc)
        if min_auc < 0.45:
            signal_direction = "invert"
        elif min_auc > 0.55:
            signal_direction = "normal"
        else:
            signal_direction = "uncertain"

    y_prob = (1.0 - y_prob_raw) if signal_direction == "invert" else y_prob_raw
    y_pred = (y_prob >= 0.5).astype(int)
    auc = float(roc_auc_score(y_val, y_prob))
    report = classification_report(y_val, y_pred, target_names=["negative", "positive"], output_dict=True)
    sweep_rows, best_row = _threshold_sweep(y_prob, ret_val.to_numpy(), y_val.to_numpy())

    # OOS evaluation: retrain scaler on full dev, then eval on oos slice.
    oos_summary = None
    if len(X_oos) >= 20 and y_oos.nunique() >= 2:
        try:
            scaler_final = StandardScaler()
            X_dev_s = scaler_final.fit_transform(X_dev)
            X_oos_s = scaler_final.transform(X_oos)
            model_final = _fit_model(X_dev_s, y_dev, backend)
            prob_oos_raw = model_final.predict_proba(X_oos_s)[:, 1]
            prob_oos = (1.0 - prob_oos_raw) if signal_direction == "invert" else prob_oos_raw
            oos_auc = float(roc_auc_score(y_oos, prob_oos))
            top_mask = prob_oos >= (best_row or {}).get("threshold", 0.5)
            oos_summary = {
                "size": int(len(X_oos)),
                "auc": oos_auc,
                "picks": int(top_mask.sum()),
                "win_rate_pct": float((ret_oos.to_numpy()[top_mask] > 0).mean() * 100) if top_mask.any() else None,
                "avg_return_pct": float(ret_oos.to_numpy()[top_mask].mean()) if top_mask.any() else None,
            }
        except Exception as e:
            oos_summary = {"error": str(e)}

    model_payload = {
        "model": model,
        "scaler": scaler,
        "features": feat_cols,
        "trained_at": datetime.now().isoformat(),
        "auc": auc,
        "raw_auc": raw_auc,
        "cv_median_auc": cv_median_auc,
        "signal_direction": signal_direction,
        "oos_auc": (oos_summary or {}).get("auc") if oos_summary else None,
        "oos_win_rate_pct": (oos_summary or {}).get("win_rate_pct") if oos_summary else None,
        "oos_avg_return_pct": (oos_summary or {}).get("avg_return_pct") if oos_summary else None,
        "segment": spec.name,
        "return_col": spec.return_col,
        "target_horizon_days": horizon_days_from_return_col(spec.return_col),
        "positive_threshold": spec.positive_threshold,
        "recommended_probability_threshold": (best_row or {}).get("threshold", 0.5),
        "description": spec.description,
    }
    os.makedirs(Path(spec.model_path).parent, exist_ok=True)
    joblib.dump(model_payload, spec.model_path)

    try:
        importances = getattr(model, "feature_importances_", None)
        feature_importance = (
            sorted(
                [{"feature": f, "importance": float(i)} for f, i in zip(feat_cols, importances)],
                key=lambda row: -row["importance"],
            )[:15]
            if importances is not None
            else []
        )
    except Exception:
        feature_importance = []

    return {
        "name": spec.name,
        "status": "trained",
        "rows": total_rows,
        "positives": positive_rows,
        "negative": int(total_rows - positive_rows),
        "return_col": spec.return_col,
        "target_horizon_days": horizon_days_from_return_col(spec.return_col),
        "positive_threshold": spec.positive_threshold,
        "auc": auc,
        "raw_auc": raw_auc,
        "cv_median_auc": cv_median_auc,
        "signal_direction": signal_direction,
        "accuracy": float(report["accuracy"]),
        "positive_precision": float(report["positive"]["precision"]),
        "positive_recall": float(report["positive"]["recall"]),
        "recommended_probability_threshold": (best_row or {}).get("threshold"),
        "threshold_sweep": sweep_rows,
        "best_threshold_row": best_row,
        "feature_importance_top15": feature_importance,
        "model_path": spec.model_path,
        "description": spec.description,
        "walk_forward_cv": cv_folds,
        "oos_holdout": oos_summary,
    }


def _report_md(report):
    lines = ["# Retrain V2 Report", ""]
    lines.append(f"- generated_at: `{report['generated_at']}`")
    lines.append(f"- execution_status: `{report.get('execution_status', 'unknown')}`")
    lines.append(f"- rows_loaded: `{report['rows_loaded']}`")
    lines.append(f"- backend: `{report['backend']}`")
    if report.get("last_successful_model_train_at"):
        lines.append(f"- last_successful_model_train_at: `{report.get('last_successful_model_train_at')}`")
    if report.get("defer_reason"):
        lines.append(f"- defer_reason: `{report.get('defer_reason')}`")
    lines.append("")
    lines.append("## Segment Results")
    for row in report["segments"]:
        lines.append(f"- `{row['name']}`: `{row['status']}`")
        if row["status"] != "trained":
            reason = row.get("reason", "unknown")
            lines.append(f"  reason: `{reason}`")
            continue
        lines.append(f"  rows={row['rows']} positives={row['positives']} auc={row['auc']:.4f} acc={row['accuracy']:.4f}")
        best = row.get("best_threshold_row")
        if best:
            lines.append(
                f"  best_th={best['threshold']:.2f} picks={best['picks']} avg_return={best['avg_return']:+.2f}% "
                f"win_rate={best['win_rate']:.1f}% hit_rate={best['hit_rate']:.1f}%"
            )
    return "\n".join(lines) + "\n"


def _existing_model_snapshot() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for spec in SEGMENTS:
        path = PROJECT_ROOT / spec.model_path
        if not path.exists():
            continue
        stat = path.stat()
        rows.append(
            {
                "name": spec.name,
                "model_path": spec.model_path,
                "exists": True,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size_bytes": int(stat.st_size),
            }
        )
    return rows


def _latest_existing_model_time(snapshot: List[Dict[str, Any]]) -> Optional[str]:
    mtimes = [str(row.get("mtime")) for row in snapshot if row.get("mtime")]
    return max(mtimes) if mtimes else None


def _derive_features_from_archive(df: pd.DataFrame) -> pd.DataFrame:
    """Derive the FEATURE_COLS one-hot/bucket columns from archive raw fields.

    The training CSV holds raw archive columns (tier, position, trend,
    volume_ratio, market, scan_mode, strategy_family, decision_bucket,
    entry_reference_price, surge, context, marcap_band, is_sub7, price_band)
    while inference (modules/quant_analysis.py) derives 41 binary/bucket
    features at runtime. Without this step, training sees only alpha_score +
    is_sub7 (2/41), which produced raw_auc=0.473 on KOSDAQ swing — the model
    had nothing to learn from.

    Definitions here MUST mirror the inference derivation in quant_analysis.py
    around lines 1604–1803. Any drift creates silent train/serve skew.
    """
    out = df.copy()

    def _str_col(name: str, default: str = "") -> pd.Series:
        s = out.get(name)
        if s is None:
            return pd.Series([default] * len(out), index=out.index, dtype=str)
        return s.fillna(default).astype(str)

    def _num_col(name: str) -> pd.Series:
        s = out.get(name)
        if s is None:
            return pd.Series([float("nan")] * len(out), index=out.index, dtype=float)
        return pd.to_numeric(s, errors="coerce")

    tier = _str_col("tier")
    position = _str_col("position")
    trend = _str_col("trend").str.upper()
    surge_text = _str_col("surge")
    context_text = _str_col("context")
    market = _str_col("market").str.upper()
    market_type = _str_col("market_type").str.upper()
    scan_mode = _str_col("scan_mode").str.upper()
    strategy_family = _str_col("strategy_family").str.upper()
    decision_bucket = _str_col("decision_bucket").str.lower()
    price_band_str = _str_col("price_band").str.lower()
    ticker = _str_col("ticker")

    is_kospi_t = ticker.str.endswith(".KS")
    is_kosdaq_t = ticker.str.endswith(".KQ") | (ticker.str.match(r"^\d+$") & ~is_kospi_t)

    out["is_kospi"] = (is_kospi_t | (market == "KOSPI")).astype(int)
    out["is_kosdaq"] = (is_kosdaq_t | (market == "KOSDAQ")).astype(int)
    out["is_nasdaq"] = ((market_type != "KR") & (strategy_family != "AMEX_MOONSHOT")).astype(int)
    out["is_amex"] = (strategy_family == "AMEX_MOONSHOT").astype(int)

    out["scan_intraday"] = (scan_mode == "INTRADAY").astype(int)
    out["scan_swing"] = (scan_mode == "SWING").astype(int)

    out["fam_kr_core"] = (strategy_family == "KR_CORE").astype(int)
    out["fam_us_main"] = (strategy_family == "US_MAIN").astype(int)
    out["fam_amex_moonshot"] = (strategy_family == "AMEX_MOONSHOT").astype(int)

    out["is_picked"] = (decision_bucket == "picked").astype(int)
    out["is_watchlist"] = (decision_bucket == "watchlist").astype(int)
    out["is_exception_leader"] = (decision_bucket == "exception_leader").astype(int)

    out["is_rising"] = position.str.contains("Rising", na=False).astype(int)
    out["is_peak"] = position.str.contains("Peak", na=False).astype(int)
    out["is_resting"] = position.str.contains("Resting", na=False).astype(int)
    out["is_bottom"] = position.str.contains("Bottom", na=False).astype(int)
    out["is_sideways"] = (
        (out["is_rising"] == 0)
        & (out["is_peak"] == 0)
        & (out["is_resting"] == 0)
        & (out["is_bottom"] == 0)
    ).astype(int)

    out["is_uptrend"] = (trend == "UP").astype(int)
    out["is_downtrend"] = (trend == "DOWN").astype(int)

    out["tier_t0"] = tier.str.contains("T0", na=False).astype(int)
    out["tier_t1"] = tier.str.contains("T1", na=False).astype(int)
    out["tier_t2"] = tier.str.contains("T2", na=False).astype(int)

    vr = _num_col("volume_ratio")
    vc = out.get("volume_confirmed")
    if vc is None:
        vc_int = pd.Series([0] * len(out), index=out.index, dtype=int)
    else:
        vc_int = vc.map({True: 1, False: 0, "True": 1, "False": 0, 1: 1, 0: 0}).fillna(
            (vr >= 1.2).astype(int)
        ).astype(int)
    out["vol_confirmed"] = vc_int
    out["vol_gt25x"] = (vr > 2.5).fillna(False).astype(int)
    out["vol_18_25x"] = ((vr > 1.8) & (vr <= 2.5)).fillna(False).astype(int)
    out["vol_08_18x"] = ((vr >= 0.8) & (vr <= 1.8)).fillna(False).astype(int)
    out["vol_lt05x"] = (vr < 0.5).fillna(False).astype(int)

    out["is_overheat"] = ((vr >= 2.5).fillna(False) | (out["is_peak"] == 1)).astype(int)
    out["is_momentum"] = ((out["is_uptrend"] == 1) & (out["is_bottom"] == 0)).astype(int)
    out["is_breakout"] = (
        surge_text.str.contains("Breakout", na=False)
        | surge_text.str.contains("돌파", na=False)
        | surge_text.str.contains("Continuation", na=False)
        | (out["is_rising"] == 1)
    ).astype(int)
    out["is_contract"] = (
        surge_text.str.contains("계약", na=False)
        | surge_text.str.contains("수주", na=False)
        | context_text.str.contains("계약", na=False)
        | context_text.str.contains("수주", na=False)
    ).astype(int)

    out["is_rsidiv"] = pd.Series([0] * len(out), index=out.index, dtype=int)
    out["is_obvdiv"] = pd.Series([0] * len(out), index=out.index, dtype=int)

    fund_status = _str_col("fund_status").str.lower()
    out["fund_positive"] = fund_status.str.contains("good|positive|pass|양호|통과|호재", regex=True, na=False).astype(int)

    erp = _num_col("entry_reference_price")
    is_sub7_csv = _num_col("is_sub7")
    derived_sub7 = ((erp > 0) & (erp <= 7.0)).astype(int)
    out["is_sub7"] = is_sub7_csv.fillna(derived_sub7).astype(int)
    derived_715 = ((erp > 7.0) & (erp <= 15.0)).astype(int)
    derived_gt15 = (erp > 15.0).astype(int)
    out["price_7_15"] = derived_715
    out["price_gt15"] = derived_gt15
    pb_sub7 = price_band_str.eq("sub_7")
    pb_715 = price_band_str.eq("p7_15") | price_band_str.eq("7_15")
    pb_gt15 = price_band_str.eq("gt_15")
    out.loc[pb_sub7, "is_sub7"] = 1
    out.loc[pb_715, "price_7_15"] = 1
    out.loc[pb_gt15, "price_gt15"] = 1

    marcap = _num_col("marcap_band")
    out["marcap_micro"] = marcap.eq(0).fillna(False).astype(int)
    out["marcap_small"] = marcap.eq(1).fillna(False).astype(int)
    out["marcap_mid"] = marcap.eq(2).fillna(False).astype(int)
    out["marcap_large"] = marcap.eq(3).fillna(False).astype(int)
    out["marcap_mega"] = marcap.eq(4).fillna(False).astype(int)

    kr_role = _str_col("kr_universe_role").str.upper()
    kr_role = kr_role.where(kr_role.ne(""))
    kr_role = kr_role.fillna(
        pd.Series(
            np.where(out["is_kospi"].eq(1), "CORE_TREND", np.where(out["is_kosdaq"].eq(1), "EXPLOSIVE_LEADER", "")),
            index=out.index,
        )
    )
    out["role_core_trend"] = (kr_role == "CORE_TREND").astype(int)
    out["role_explosive_leader"] = (kr_role == "EXPLOSIVE_LEADER").astype(int)
    out["role_transitional"] = (kr_role == "TRANSITIONAL").astype(int)
    out["role_reject_risk"] = (kr_role == "REJECT_RISK").astype(int)

    out["peak_x_highvol"] = ((out["is_peak"] == 1) & ((vr > 2.5).fillna(False))).astype(int)
    out["overheat_x_uptrend"] = ((out["is_overheat"] == 1) & (out["is_uptrend"] == 1)).astype(int)
    out["sub7_x_breakout"] = ((out["is_sub7"] == 1) & (out["is_breakout"] == 1)).astype(int)

    market_subtype = np.where(out["is_kospi"].eq(1), "KOSPI", np.where(out["is_kosdaq"].eq(1), "KOSDAQ", market))
    risk_rows = [
        compute_loss_risk_features(
            market_subtype=market_subtype[i],
            alpha_score=out["alpha_score"].iloc[i] if "alpha_score" in out.columns else None,
            tech_score=out["tech_score"].iloc[i] if "tech_score" in out.columns else None,
            whale_score=out["whale_score"].iloc[i] if "whale_score" in out.columns else None,
            ml_prob=out["ml_prob"].iloc[i] if "ml_prob" in out.columns else None,
            prob_clean=out["prob_clean"].iloc[i] if "prob_clean" in out.columns else None,
            volume_ratio=out["volume_ratio"].iloc[i] if "volume_ratio" in out.columns else None,
            volume_confirmed=out["volume_confirmed"].iloc[i] if "volume_confirmed" in out.columns else None,
            position=position.iloc[i],
            tier=tier.iloc[i],
            trend=trend.iloc[i],
        )
        for i in range(len(out))
    ]
    risk_df = pd.DataFrame(risk_rows, index=out.index)
    for col in LOSS_RISK_FEATURE_COLS:
        out[col] = pd.to_numeric(risk_df[col], errors="coerce").fillna(0.0)

    return out


def _load_from_csv(path: str) -> pd.DataFrame:
    """Load enriched scan archive from a flat CSV export (smoke-test path).

    Expects the columns produced by export_scan_archive_learning_dataset.py.
    Mirrors the post-load shape of load_scan_archive(): created_at parsed,
    market_subtype inferred, scan_mode upper-cased.
    """
    print(f"  CSV에서 로드: {path}")
    df = pd.read_csv(path, low_memory=False)
    if df.empty:
        raise SystemExit(f"CSV is empty: {path}")
    df["created_at"] = pd.to_datetime(df.get("created_at"), errors="coerce", utc=True).dt.tz_convert(None)
    df["scan_date"] = df["created_at"].dt.date
    df["scan_mode"] = df.get("scan_mode", "SWING").fillna("SWING").astype(str).str.upper()
    df["strategy_family"] = df.get("strategy_family", "").fillna("").astype(str)
    df["market_subtype"] = [
        _infer_submarket(ticker, market_type, strategy_family)
        for ticker, market_type, strategy_family in zip(
            df.get("ticker", pd.Series(dtype=str)),
            df.get("market_type", pd.Series(dtype=str)),
            df.get("strategy_family", pd.Series(dtype=str)),
        )
    ]
    df = _derive_features_from_archive(df)
    print(f"  ✅ 총 {len(df):,} 레코드 (CSV) — derived {sum(c in df.columns for c in FEATURE_COLS)}/{len(FEATURE_COLS)} feature columns")
    return df


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase25 ML retrain pipeline")
    parser.add_argument(
        "--from-csv",
        dest="from_csv",
        default=None,
        help="Load archive from a CSV export instead of Supabase (smoke-test).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Phase 25 ML Retraining Pipeline (Resolved Outcome v2)")
    print("=" * 60)

    if args.from_csv:
        print(f"\n[1/3] CSV에서 enriched scan archive 로드...")
        df = _load_from_csv(args.from_csv)
    else:
        print("\n[1/3] DB에서 enriched scan archive 로드...")
        df = load_scan_archive()

    print("\n[2/3] 피처 엔지니어링...")
    df_feat = engineer_features(df)

    # OHLCV-derived features for KR rows that will reach training. Cost-controlled
    # to KR + RESOLVED + alpha-bearing rows so we don't pay yfinance for stubs
    # that get filtered out anyway. Cached per (ticker, scan_date) so repeat
    # tickers across days only fetch once per date.
    if "market_subtype" in df_feat.columns:
        kr_mask = df_feat["market_subtype"].isin(["KOSPI", "KOSDAQ"])
        kr_mask &= df_feat.get("outcome_status", pd.Series(index=df_feat.index)).fillna("").str.upper().eq("RESOLVED")
        kr_mask &= pd.to_numeric(df_feat.get("alpha_score", pd.Series(index=df_feat.index)), errors="coerce").notna()
        if kr_mask.any():
            print(f"  OHLCV feature derivation for {int(kr_mask.sum()):,} KR rows…")
            df_feat = derive_ohlcv_features(df_feat, target_mask=kr_mask, verbose=True)
    print(f"  사용 가능한 피처: {[col for col in FEATURE_COLS if col in df_feat.columns]}")

    backend, _ = _choose_model_backend()
    print(f"\n[3/3] 세그먼트별 모델 훈련... backend={backend}")
    segment_reports = []
    for spec in SEGMENTS:
        result = train_segment(df_feat, spec, backend)
        segment_reports.append(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    generated_at = datetime.now().isoformat()
    existing_models_before = _existing_model_snapshot()
    trained = [row for row in segment_reports if row.get("status") == "trained"]
    if trained:
        execution_status = "trained"
        defer_reason = None
        last_successful_model_train_at = generated_at
    else:
        execution_status = "deferred_not_failed"
        defer_reason = "NO_DUMMY_FEATURE_COMPLETE_SAMPLE_SHORTAGE"
        last_successful_model_train_at = _latest_existing_model_time(existing_models_before)

    report = {
        "generated_at": generated_at,
        "execution_status": execution_status,
        "defer_reason": defer_reason,
        "last_successful_model_train_at": last_successful_model_train_at,
        "rows_loaded": int(len(df_feat)),
        "backend": backend,
        "segments": segment_reports,
        "existing_models_preserved": existing_models_before,
        "no_dummy_policy": {
            "enabled": True,
            "behavior": "Rows with missing real scan-time features are excluded instead of imputed with zero or neutral probabilities.",
            "deferred_runs_exit_successfully": True,
        },
    }
    report_dir = PROJECT_ROOT / "runtime_state" / "reports" / "learning"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / "retrain_v2_report.json"
    report_md = report_dir / "retrain_v2_report.md"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(_report_md(report), encoding="utf-8")

    if trained:
        primary = next((row for row in trained if row["name"] == "phase25_global"), trained[0])
        print("\n" + "=" * 60)
        print(f"  primary model: {primary['name']}  auc={primary['auc']:.4f}")
        print(f"  model path: {primary['model_path']}")
        print(f"  report path: {report_json}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("  execution status: deferred_not_failed")
        print("  reason: feature-complete no-dummy samples are below segment thresholds")
        print("  existing models were preserved; no dummy model was trained")
        print(f"  report path: {report_json}")
        print("=" * 60)


if __name__ == "__main__":
    main()
