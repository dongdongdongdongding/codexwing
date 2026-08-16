from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

HORIZONS = (1, 2, 3, 5, 7, 14, 30)
INTRADAY_MINUTE_HORIZONS = ((10, "return_10m_pct"), (30, "return_30m_pct"), (60, "return_1h_pct"))
KR_TZ = ZoneInfo("Asia/Seoul")
US_TZ = ZoneInfo("America/New_York")
SWING_TOUCH_TARGET_PCT = 5.0
SWING_TOUCH_WINDOW_DAYS = 5
SWING_TARGET_LABEL_VERSION = "forward_high_within_5d_v1"
OUTCOME_PATH_LABEL_VERSION = "scan_entry_forward_hybrid_30m_daily_stop_first_v2"
OUTCOME_PATH_HORIZON_SESSIONS = 5

try:
    import FinanceDataReader as fdr  # type: ignore
except Exception:  # pragma: no cover
    fdr = None


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)


def _parse_iso(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _infer_market(row: Dict[str, Any], run_market: str = "") -> str:
    ticker = str(row.get("ticker") or "").upper()
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return str(run_market or "NASDAQ").upper()


def _market_tz(market: str) -> ZoneInfo:
    return KR_TZ if market in {"KOSPI", "KOSDAQ"} else US_TZ


def _recommended_trade_date(row: Dict[str, Any], market: str) -> Optional[datetime.date]:
    rec_dt = _parse_iso(row.get("recommended_at"))
    if rec_dt is None:
        base_trade_date = str(row.get("base_trade_date") or "").strip()
        if base_trade_date:
            try:
                return datetime.fromisoformat(base_trade_date[:10]).date()
            except Exception:
                return None
        return None
    return rec_dt.astimezone(_market_tz(market)).date()


def _fetch_history(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    source_ticker = str(ticker or "").strip()
    if not source_ticker:
        return None
    if (source_ticker.endswith(".KS") or source_ticker.endswith(".KQ")) and fdr is not None:
        try:
            hist = fdr.DataReader(source_ticker.split(".")[0], start, end)
            if hist is not None and not hist.empty:
                hist = hist.copy()
                hist["trade_date"] = hist.index.date
                return hist
        except Exception:
            pass
    try:
        hist = yf.Ticker(source_ticker).history(start=start, end=end, auto_adjust=False, timeout=10)
        if hist is None or hist.empty:
            return None
        hist = hist.copy()
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC")
        hist["trade_date"] = hist.index.date
        return hist
    except Exception:
        return None


_INTRADAY_FETCH_FAILURES: Dict[str, int] = {"isoformat_parse": 0, "empty_response": 0, "other_exc": 0}


def _fetch_intraday_history(ticker: str, start_dt: datetime, end_dt: datetime, interval: str = "30m") -> Optional[pd.DataFrame]:
    """Fetch intraday bars. yfinance.history() rejects ISO 8601 strings with
    'unconverted data remains: T00:00:00+00:00' — the prior implementation
    passed start_dt.isoformat() and silently fell into the bare except below,
    producing 0% intraday label fill across 9.7k+ RESOLVED rows. Pass the
    datetime objects directly (yfinance accepts them) and surface the failure
    mode so silent regressions cannot hide again.
    """
    source_ticker = str(ticker or "").strip()
    if not source_ticker:
        return None
    try:
        hist = yf.Ticker(source_ticker).history(
            start=start_dt,
            end=end_dt,
            interval=interval,
            auto_adjust=False,
            timeout=10,
            prepost=False,
        )
        if hist is None or hist.empty:
            _INTRADAY_FETCH_FAILURES["empty_response"] += 1
            return None
        hist = hist.copy()
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC")
        return hist.sort_index()
    except Exception as exc:
        msg = str(exc)
        if "unconverted data remains" in msg:
            _INTRADAY_FETCH_FAILURES["isoformat_parse"] += 1
        else:
            _INTRADAY_FETCH_FAILURES["other_exc"] += 1
        return None


def _iter_runs(shared_dir: Path, run_ids: List[str], limit_runs: int) -> List[Path]:
    if run_ids:
        return [shared_dir / rid for rid in run_ids if (shared_dir / rid).exists()]
    runs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")] if shared_dir.exists() else []
    # 2026-08-16 수리: 정렬키가 p.name 이었다. RUN-<랜덤16진수>에는 시간 정보가 없어
    #   runs[-limit:] 가 "최근 N개"가 아니라 이름이 RUN-FF… 쪽인 고정된 임의 N개였다.
    #   그 결과 대부분의 RUN 에서 return_{h}d_pct 가 한 번도 계산되지 않았고, 정산기는
    #   해결 근거가 없어 HORIZON_ELAPSED_NO_RESOLUTION 으로 만료시켰다 —
    #   **7,171건 만료의 상류가 여기다.** update_realized_outcomes.py 와 같은 수정이며,
    #   두 도구가 같은 RUN 집합을 봐야 지표→정산 사슬이 끊기지 않는다.
    runs = sorted(runs, key=lambda p: p.stat().st_mtime)
    if limit_runs > 0:
        runs = runs[-limit_runs:]
    return runs


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        out = float(value)
        if pd.isna(out):
            return None
        return out
    except Exception:
        return None


def _interval_minutes(interval: str) -> int:
    text = str(interval or "").strip().lower()
    if text.endswith("m"):
        try:
            return max(1, int(text[:-1]))
        except Exception:
            return 30
    if text.endswith("h"):
        try:
            return max(1, int(text[:-1]) * 60)
        except Exception:
            return 60
    return 30


def _load_scan_entry_reference_map(run_id: str) -> Dict[str, float]:
    """Recover scan-time planned entry prices from the generated deep report.

    `entry_reference_price` is intentionally overwritten with the realized
    base close for daily outcome labels. Same-day 30m/1h path labels must stay
    anchored to the price shown to the operator at scan time.
    """
    report_path = PROJECT_ROOT / "runtime_state" / "reports" / "top_deep" / f"{run_id}.json"
    if not report_path.exists():
        return {}
    try:
        with report_path.open("r", encoding="utf-8") as f:
            reports = json.load(f)
    except Exception:
        return {}
    if not isinstance(reports, list):
        return {}

    out: Dict[str, float] = {}
    for report in reports:
        if not isinstance(report, dict):
            continue
        ticker = str(report.get("ticker") or "").strip()
        trade_plan = report.get("trade_plan") if isinstance(report.get("trade_plan"), dict) else {}
        entry = _safe_float(trade_plan.get("entry_reference_price"))
        if ticker and entry is not None and entry > 0:
            out[ticker] = round(float(entry), 6)
    return out


def _apply_scan_entry_reference(row: Dict[str, Any], scan_entry_map: Dict[str, float]) -> bool:
    if row.get("scan_entry_reference_price") not in (None, ""):
        return False
    ticker = str(row.get("ticker") or "").strip()
    entry = scan_entry_map.get(ticker)
    if entry is None:
        return False
    row["scan_entry_reference_price"] = entry
    return True


def _target_stop_policy(row: Dict[str, Any]) -> tuple[float, float]:
    target = _safe_float(row.get("target_tp_pct"))
    stop = _safe_float(row.get("stop_sl_pct"))
    if target is None or target <= 0:
        target = 5.0
    if stop is None or stop == 0:
        stop = 5.0
    return float(target), abs(float(stop))


def _entry_price_for_path(row: Dict[str, Any]) -> Optional[float]:
    entry = _safe_float(row.get("scan_entry_reference_price"))
    if entry is None:
        entry = _safe_float(row.get("entry_reference_price"))
    return entry if entry is not None and entry > 0 else None


def _post_scan_intraday_context(
    row: Dict[str, Any],
    market: str,
    interval: str = "30m",
    intraday_hist: Optional[pd.DataFrame] = None,
    fetch_if_missing: bool = True,
) -> Optional[Dict[str, Any]]:
    rec_dt = _parse_iso(row.get("recommended_at"))
    entry_price = _entry_price_for_path(row)
    if rec_dt is None or entry_price is None:
        return None

    market_tz = _market_tz(market)
    rec_local = rec_dt.astimezone(market_tz)
    if intraday_hist is None and fetch_if_missing:
        start_dt = rec_local.astimezone(timezone.utc) - timedelta(hours=2)
        end_dt = (rec_local + timedelta(days=2)).astimezone(timezone.utc)
        intraday_hist = _fetch_intraday_history(
            str(row.get("ticker") or ""),
            start_dt=start_dt,
            end_dt=end_dt,
            interval=interval,
        )
    if intraday_hist is None or intraday_hist.empty:
        return {
            "rec_local": rec_local,
            "entry_price": entry_price,
            "same_day": pd.DataFrame(),
            "after_scan": pd.DataFrame(),
            "warnings": ["intraday_history_unavailable" if fetch_if_missing else "intraday_history_not_supplied"],
        }

    hist = intraday_hist.copy()
    if hist.index.tz is None:
        hist.index = hist.index.tz_localize("UTC")
    local_idx = hist.index.tz_convert(market_tz)
    hist["local_ts"] = local_idx
    hist["local_bar_end"] = hist["local_ts"] + timedelta(minutes=_interval_minutes(interval))
    same_day = hist[local_idx.date == rec_local.date()].copy()
    after_scan = same_day[same_day["local_ts"] >= rec_local].copy()

    warnings: List[str] = []
    if after_scan.empty:
        warnings.append("post_scan_intraday_empty")

    return {
        "rec_local": rec_local,
        "entry_price": entry_price,
        "same_day": same_day,
        "after_scan": after_scan,
        "warnings": warnings,
    }


def _fetch_intraday_for_outcome_row(
    row: Dict[str, Any],
    market: str,
    interval: str = "30m",
) -> Optional[pd.DataFrame]:
    rec_dt = _parse_iso(row.get("recommended_at"))
    if rec_dt is None or _entry_price_for_path(row) is None:
        return None
    market_tz = _market_tz(market)
    rec_local = rec_dt.astimezone(market_tz)
    # yfinance minute bars are availability-limited. Avoid long empty network
    # calls for older archive rows; daily OHLC still provides conservative labels.
    if rec_local.date() < (datetime.now(market_tz).date() - timedelta(days=58)):
        return None
    start_dt = rec_local.astimezone(timezone.utc) - timedelta(hours=2)
    end_dt = (rec_local + timedelta(days=2)).astimezone(timezone.utc)
    return _fetch_intraday_history(
        str(row.get("ticker") or ""),
        start_dt=start_dt,
        end_dt=end_dt,
        interval=interval,
    )


def _compute_intraday_row_returns(
    row: Dict[str, Any],
    market: str,
    interval: str = "30m",
    intraday_hist: Optional[pd.DataFrame] = None,
) -> bool:
    """Fill same-day minute-horizon returns for any recommendation row.

    These columns are not an INTRADAY-strategy-only concept. KR SWING Top/
    Shadow/Exception candidates also need 30m/1h/close path labels so severe
    post-scan drops can become regression data. Missing or immature minute bars
    never clear an existing non-null value.
    """
    context = _post_scan_intraday_context(row, market, interval=interval, intraday_hist=intraday_hist)
    if not context:
        return False
    changed = False

    rec_local = context["rec_local"]
    entry_price = float(context["entry_price"])
    same_day = context["same_day"]
    after_scan = context["after_scan"]
    if not same_day.empty:
        for minutes, key in INTRADAY_MINUTE_HORIZONS:
            target_dt = rec_local + timedelta(minutes=minutes)
            eligible = same_day[same_day["local_bar_end"] >= target_dt]
            value = None
            if not eligible.empty:
                close_val = _safe_float(eligible["Close"].iloc[0])
                if close_val is not None and entry_price > 0:
                    value = round(((close_val / entry_price) - 1.0) * 100.0, 6)
            if value is not None and row.get(key) != value:
                row[key] = value
                changed = True

        close_rows = same_day.sort_values("local_ts")
        close_value = None
        if not close_rows.empty:
            close_val = _safe_float(close_rows["Close"].iloc[-1])
            if close_val is not None and entry_price > 0:
                close_value = round(((close_val / entry_price) - 1.0) * 100.0, 6)
        if close_value is not None and row.get("return_close_pct") != close_value:
            row["return_close_pct"] = close_value
            changed = True
        if not after_scan.empty:
            high_series = pd.to_numeric(after_scan["High"], errors="coerce") if "High" in after_scan.columns else pd.Series(dtype="float")
            low_series = pd.to_numeric(after_scan["Low"], errors="coerce") if "Low" in after_scan.columns else pd.Series(dtype="float")
            if not high_series.dropna().empty:
                mfe_intraday = round(((float(high_series.max()) / entry_price) - 1.0) * 100.0, 6)
                if row.get("mfe_intraday_pct") != mfe_intraday:
                    row["mfe_intraday_pct"] = mfe_intraday
                    changed = True
            if not low_series.dropna().empty:
                mae_intraday = round(((float(low_series.min()) / entry_price) - 1.0) * 100.0, 6)
                if row.get("mae_intraday_pct") != mae_intraday:
                    row["mae_intraday_pct"] = mae_intraday
                    changed = True

    if changed:
        row["performance_updated_at"] = datetime.now(timezone.utc).isoformat()
    return changed


def _compute_row_returns(row: Dict[str, Any], hist: pd.DataFrame, market: str) -> bool:
    trade_date = _recommended_trade_date(row, market)
    if trade_date is None or hist is None or hist.empty:
        return False
    eligible = hist[hist["trade_date"] >= trade_date]
    if eligible.empty:
        return False
    base_idx = eligible.index[0]
    base_pos = int(hist.index.get_loc(base_idx))
    base_close = pd.to_numeric(hist["Close"], errors="coerce").iloc[base_pos]
    if pd.isna(base_close) or float(base_close) <= 0:
        return False

    changed = False
    original_entry = _safe_float(row.get("entry_reference_price"))
    if original_entry is not None and row.get("scan_entry_reference_price") in (None, ""):
        row["scan_entry_reference_price"] = round(float(original_entry), 6)
        changed = True
    base_trade_date = str(hist.loc[base_idx, "trade_date"])
    if row.get("base_trade_date") != base_trade_date:
        row["base_trade_date"] = base_trade_date
        changed = True
    if row.get("entry_reference_price") != round(float(base_close), 6):
        row["entry_reference_price"] = round(float(base_close), 6)
        changed = True

    closes = pd.to_numeric(hist["Close"], errors="coerce")
    highs = pd.to_numeric(hist["High"], errors="coerce") if "High" in hist.columns else pd.Series(dtype="float")
    for horizon in HORIZONS:
        key = f"return_{horizon}d_pct"
        target_pos = base_pos + horizon
        value = None
        if target_pos < len(hist):
            close_val = closes.iloc[target_pos]
            if pd.notna(close_val) and float(base_close) > 0:
                value = round(((float(close_val) / float(base_close)) - 1.0) * 100.0, 6)
        if row.get(key) != value:
            row[key] = value
            changed = True

    high_touch_value = None
    high_touch_hit = None
    high_touch_date = None
    target_pos = base_pos + SWING_TOUCH_WINDOW_DAYS
    if (
        str(row.get("scan_mode", "SWING")).upper() == "SWING"
        and not highs.empty
        and target_pos < len(hist)
    ):
        forward = highs.iloc[base_pos + 1 : target_pos + 1].dropna()
        if len(forward) == SWING_TOUCH_WINDOW_DAYS:
            max_high = float(forward.max())
            high_touch_value = round(((max_high / float(base_close)) - 1.0) * 100.0, 6)
            high_touch_hit = bool(high_touch_value >= SWING_TOUCH_TARGET_PCT)
            if high_touch_hit:
                hit_positions = forward[forward >= float(base_close) * (1.0 + SWING_TOUCH_TARGET_PCT / 100.0)]
                if not hit_positions.empty:
                    high_touch_date = str(hist.loc[hit_positions.index[0], "trade_date"])
    for key, value in (
        ("max_high_return_5d_pct", high_touch_value),
        ("hit_5pct_within_5d", high_touch_hit),
        ("hit_5pct_within_5d_at", high_touch_date),
        (
            "swing_target_label_version",
            SWING_TARGET_LABEL_VERSION if high_touch_value is not None else None,
        ),
    ):
        if key not in row or row.get(key) != value:
            row[key] = value
            changed = True

    latest_close = closes.iloc[-1] if len(closes) > 0 else None
    latest_trade_date = hist["trade_date"].iloc[-1] if len(hist) > 0 else None
    latest_return = None
    if latest_close is not None and pd.notna(latest_close) and float(base_close) > 0:
        latest_return = round(((float(latest_close) / float(base_close)) - 1.0) * 100.0, 6)
    if row.get("latest_return_pct") != latest_return:
        row["latest_return_pct"] = latest_return
        changed = True
    latest_trade_date_str = str(latest_trade_date) if latest_trade_date is not None else None
    if row.get("latest_trade_date") != latest_trade_date_str:
        row["latest_trade_date"] = latest_trade_date_str
        changed = True
    if changed:
        row["performance_updated_at"] = datetime.now(timezone.utc).isoformat()
    return changed


def _path_float_ret(value: Any, entry: float) -> Optional[float]:
    numeric = _safe_float(value)
    if numeric is None or entry <= 0:
        return None
    return ((float(numeric) / float(entry)) - 1.0) * 100.0


def _compute_path_risk_labels(
    row: Dict[str, Any],
    hist: pd.DataFrame,
    market: str,
    intraday_hist: Optional[pd.DataFrame] = None,
) -> bool:
    trade_date = _recommended_trade_date(row, market)
    entry = _entry_price_for_path(row)
    if trade_date is None or entry is None or entry <= 0 or hist is None or hist.empty:
        return False
    eligible = hist[hist["trade_date"] > trade_date].copy()
    if "High" not in hist.columns or "Low" not in hist.columns:
        return False

    intraday_context = _post_scan_intraday_context(
        row,
        market,
        intraday_hist=intraday_hist,
        fetch_if_missing=False,
    )
    intraday_after_scan = (
        intraday_context.get("after_scan", pd.DataFrame())
        if isinstance(intraday_context, dict)
        else pd.DataFrame()
    )
    path_bars: List[Dict[str, Any]] = []
    warnings: List[str] = []
    source_parts: List[str] = []
    session_count = 0
    if isinstance(intraday_context, dict):
        warnings.extend([str(w) for w in intraday_context.get("warnings", []) if str(w)])
    if not intraday_after_scan.empty:
        source_parts.append("intraday_30m")
        session_count += 1
        for _, bar in intraday_after_scan.sort_values("local_ts").iterrows():
            high = _safe_float(bar.get("High"))
            low = _safe_float(bar.get("Low"))
            close = _safe_float(bar.get("Close"))
            if high is None or low is None:
                continue
            bar_end = bar.get("local_bar_end")
            bar_start = bar.get("local_ts")
            at_value = bar_end.isoformat() if hasattr(bar_end, "isoformat") else str(bar_end)
            path_bars.append(
                {
                    "at": at_value,
                    "date": str(at_value)[:10],
                    "high": high,
                    "low": low,
                    "close": close,
                    "source": "intraday_30m",
                    "bar_start": bar_start.isoformat() if hasattr(bar_start, "isoformat") else str(bar_start),
                }
            )

    daily_needed = max(0, OUTCOME_PATH_HORIZON_SESSIONS - session_count)
    forward_daily = eligible.iloc[:daily_needed]
    if not forward_daily.empty:
        source_parts.append("daily_ohlc")
        session_count += len(forward_daily)
        for _, bar in forward_daily.iterrows():
            high = _safe_float(bar.get("High"))
            low = _safe_float(bar.get("Low"))
            close = _safe_float(bar.get("Close"))
            if high is None or low is None:
                continue
            bar_date = str(bar.get("trade_date") or "")[:10]
            path_bars.append(
                {
                    "at": bar_date,
                    "date": bar_date,
                    "high": high,
                    "low": low,
                    "close": close,
                    "source": "daily_ohlc",
                }
            )

    if not path_bars:
        values = {
            "mfe_5d_pct": None,
            "mae_5d_pct": None,
            "target_before_stop_5d": None,
            "stop_before_target_5d": None,
            "target_hit_at_5d": None,
            "stop_hit_at_5d": None,
            "ordered_entry_at": row.get("recommended_at"),
            "ordered_entry_price": round(float(entry), 6),
            "ordered_target_hit_at": None,
            "ordered_stop_hit_at": None,
            "ordered_mfe_until_terminal_5d_pct": None,
            "ordered_mae_until_terminal_5d_pct": None,
            "ordered_mae_before_target_5d_pct": None,
            "outcome_path_bar_count": 0,
            "outcome_path_source": "unavailable",
            "outcome_path_warnings": warnings or ["post_entry_path_unavailable"],
            "outcome_path_terminal_status": "insufficient_forward_bars",
            "outcome_path_label_version": None,
        }
    else:
        target_pct, stop_pct = _target_stop_policy(row)
        target_price = float(entry) * (1.0 + target_pct / 100.0)
        stop_price = float(entry) * (1.0 - stop_pct / 100.0)
        high_rets = [_path_float_ret(bar.get("high"), float(entry)) for bar in path_bars]
        low_rets = [_path_float_ret(bar.get("low"), float(entry)) for bar in path_bars]
        high_rets_clean = [float(v) for v in high_rets if v is not None]
        low_rets_clean = [float(v) for v in low_rets if v is not None]
        if not high_rets_clean or not low_rets_clean:
            return False
        mfe = round(max(high_rets_clean), 6)
        mae = round(min(low_rets_clean), 6)
        target_hit_at = None
        stop_hit_at = None
        target_before_stop = False
        stop_before_target = False
        terminal = "no_touch"
        terminal_highs: List[float] = []
        terminal_lows: List[float] = []
        ordered_mae_before_target = None
        for bar in path_bars:
            high_val = _safe_float(bar.get("high"))
            low_val = _safe_float(bar.get("low"))
            high_ret = _path_float_ret(high_val, float(entry))
            low_ret = _path_float_ret(low_val, float(entry))
            if high_ret is not None:
                terminal_highs.append(high_ret)
            if low_ret is not None:
                terminal_lows.append(low_ret)
            bar_at = str(bar.get("at") or bar.get("date") or "")
            target_hit = high_val is not None and high_val >= target_price
            stop_hit = low_val is not None and low_val <= stop_price
            if target_hit and stop_hit:
                target_hit_at = bar_at
                stop_hit_at = bar_at
                stop_before_target = True
                terminal = "same_bar_stop_first"
                warnings.append("same_bar_target_and_stop_touch")
                break
            if stop_hit:
                stop_hit_at = bar_at
                stop_before_target = True
                terminal = "stop_before_target"
                break
            if target_hit:
                target_hit_at = bar_at
                target_before_stop = True
                terminal = "target_before_stop"
                ordered_mae_before_target = round(min(terminal_lows), 6) if terminal_lows else None
                break
        if terminal == "no_touch" and session_count < OUTCOME_PATH_HORIZON_SESSIONS:
            target_before_stop = None
            stop_before_target = None
            terminal = "insufficient_forward_bars"
        terminal_mfe = round(max(terminal_highs), 6) if terminal_highs else None
        terminal_mae = round(min(terminal_lows), 6) if terminal_lows else None
        source = "+".join(dict.fromkeys(source_parts)) if source_parts else "daily_ohlc"
        target_hit_date = str(target_hit_at)[:10] if target_hit_at else None
        stop_hit_date = str(stop_hit_at)[:10] if stop_hit_at else None
        values = {
            "mfe_5d_pct": mfe,
            "mae_5d_pct": mae,
            "target_before_stop_5d": target_before_stop,
            "stop_before_target_5d": stop_before_target,
            "target_hit_at_5d": target_hit_date,
            "stop_hit_at_5d": stop_hit_date,
            "ordered_entry_at": row.get("recommended_at"),
            "ordered_entry_price": round(float(entry), 6),
            "ordered_target_hit_at": target_hit_at,
            "ordered_stop_hit_at": stop_hit_at,
            "ordered_mfe_until_terminal_5d_pct": terminal_mfe,
            "ordered_mae_until_terminal_5d_pct": terminal_mae,
            "ordered_mae_before_target_5d_pct": ordered_mae_before_target,
            "outcome_path_bar_count": len(path_bars),
            "outcome_path_source": source,
            "outcome_path_warnings": warnings,
            "outcome_path_terminal_status": terminal,
            "outcome_path_label_version": OUTCOME_PATH_LABEL_VERSION,
        }

    changed = False
    for key, value in values.items():
        if key not in row or row.get(key) != value:
            row[key] = value
            changed = True
    if changed:
        row["performance_updated_at"] = datetime.now(timezone.utc).isoformat()
    return changed


def run_update(
    shared_dir: Path,
    run_ids: List[str],
    limit_runs: int,
    dry_run: bool,
    scan_mode_filter: str = "ALL",
) -> Dict[str, Any]:
    targets = _iter_runs(shared_dir=shared_dir, run_ids=run_ids, limit_runs=limit_runs)
    ticker_windows: Dict[str, Dict[str, Any]] = {}
    run_payloads: List[tuple[Path, Dict[str, Any], str]] = []

    for run_dir in targets:
        payload = _load_json(run_dir / "realized_outcomes.json")
        if not payload:
            continue
        scanner_payload = _load_json(run_dir / "scanner_handoff.json")
        run_ctx = scanner_payload.get("run_context", {}) if isinstance(scanner_payload.get("run_context"), dict) else {}
        run_market = str(run_ctx.get("market", "")).upper()
        summary = scanner_payload.get("summary", {}) if isinstance(scanner_payload.get("summary"), dict) else {}
        input_meta = summary.get("input_meta", {}) if isinstance(summary.get("input_meta"), dict) else {}
        run_scan_mode = str(input_meta.get("scan_mode") or summary.get("scan_mode") or "SWING").upper()
        run_payloads.append((run_dir, payload, run_market, run_scan_mode))
        for row in payload.get("outcomes", []):
            if not isinstance(row, dict):
                continue
            effective_scan_mode = str(row.get("scan_mode") or run_scan_mode or "SWING").upper()
            if row.get("scan_mode") != effective_scan_mode:
                row["scan_mode"] = effective_scan_mode
            if scan_mode_filter != "ALL" and effective_scan_mode != scan_mode_filter:
                continue
            if row.get("scan_mode") != run_scan_mode and not row.get("scan_mode"):
                row["scan_mode"] = run_scan_mode
            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue
            market = _infer_market(row, run_market=run_market)
            trade_date = _recommended_trade_date(row, market)
            if trade_date is None:
                continue
            state = ticker_windows.setdefault(
                ticker,
                {
                    "market": market,
                    "start": trade_date,
                    "end": trade_date + timedelta(days=40),
                },
            )
            if trade_date < state["start"]:
                state["start"] = trade_date
            if trade_date + timedelta(days=40) > state["end"]:
                state["end"] = trade_date + timedelta(days=40)

    history_map: Dict[str, pd.DataFrame] = {}
    for ticker, state in ticker_windows.items():
        hist = _fetch_history(
            ticker=ticker,
            start=(state["start"] - timedelta(days=7)).isoformat(),
            end=(max(state["end"], datetime.now().date() + timedelta(days=2))).isoformat(),
        )
        if hist is not None and not hist.empty:
            history_map[ticker] = hist
    intraday_cache: Dict[tuple, Optional[pd.DataFrame]] = {}

    stats = {
        "runs_seen": len(targets),
        "runs_with_file": 0,
        "rows_seen": 0,
        "rows_updated": 0,
        "daily_rows_updated": 0,
        "intraday_rows_attempted": 0,
        "intraday_rows_updated": 0,
        "rows_without_daily_history": 0,
        "files_updated": 0,
        "tickers_with_history": len(history_map),
        "db_rows_upserted": 0,
        "scan_archive_rows_synced": 0,
        "post_scan_ledger_rows_upserted": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "scan_mode_filter": scan_mode_filter,
        "run_stats": [],
    }
    db = None
    try:
        from modules.db_manager import DBManager

        db = DBManager()
    except Exception:
        db = None

    for run_dir, payload, run_market, run_scan_mode in run_payloads:
        outcomes = payload.get("outcomes", []) if isinstance(payload.get("outcomes"), list) else []
        if not outcomes:
            continue
        scan_entry_map = _load_scan_entry_reference_map(run_dir.name)
        stats["runs_with_file"] += 1
        changed = False
        updated_rows = 0
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            effective_scan_mode = str(row.get("scan_mode") or run_scan_mode or "SWING").upper()
            if scan_mode_filter != "ALL" and effective_scan_mode != scan_mode_filter:
                continue
            stats["rows_seen"] += 1
            ticker = str(row.get("ticker") or "").strip()
            market = _infer_market(row, run_market=run_market)
            hist = history_map.get(ticker)
            row_changed = _apply_scan_entry_reference(row, scan_entry_map)
            rec_dt = _parse_iso(row.get("recommended_at"))
            rec_key = None
            if rec_dt is not None:
                rec_key = (
                    ticker,
                    market,
                    rec_dt.astimezone(_market_tz(market)).date().isoformat(),
                )
            if rec_key is not None and rec_key in intraday_cache:
                intraday_hist = intraday_cache[rec_key]
            else:
                intraday_hist = _fetch_intraday_for_outcome_row(row, market)
                if rec_key is not None:
                    intraday_cache[rec_key] = intraday_hist
            if hist is None:
                stats["rows_without_daily_history"] += 1
            elif _compute_row_returns(row, hist, market):
                row_changed = True
                stats["daily_rows_updated"] += 1
            if hist is not None and _compute_path_risk_labels(row, hist, market, intraday_hist=intraday_hist):
                row_changed = True
            stats["intraday_rows_attempted"] += 1
            if _compute_intraday_row_returns(row, market, intraday_hist=intraday_hist):
                row_changed = True
                stats["intraday_rows_updated"] += 1
            if row_changed:
                changed = True
                updated_rows += 1
                stats["rows_updated"] += 1

        if changed and not dry_run:
            payload["summary"] = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
            payload["summary"]["performance_last_updated_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(run_dir / "realized_outcomes.json", payload)
            try:
                from modules.post_scan_outcome_ledger import write_run_post_scan_ledger

                write_run_post_scan_ledger(run_dir=run_dir, outcomes=outcomes)
            except Exception:
                pass
            stats["files_updated"] += 1
        if not dry_run and db is not None and getattr(db, "client", None) is not None:
            try:
                db.save_agent_run_summary(
                    {
                        "run_id": run_dir.name,
                        "market": run_market,
                        "strategy_version": "outcome-return-sync",
                        "model_version": "outcome-return-sync",
                        "code_version": "outcome-return-sync",
                        "artifact_refs": {},
                    }
                )
            except Exception:
                pass
            try:
                stats["db_rows_upserted"] += int(db.save_agent_realized_outcomes(run_dir.name, outcomes) or 0)
            except Exception:
                pass
            try:
                stats["scan_archive_rows_synced"] += int(db.upsert_scan_archive_outcomes(run_dir.name, run_market, outcomes) or 0)
            except Exception:
                pass
            try:
                ledger_payload = _load_json(run_dir / "post_scan_outcome_ledger.json")
                ledger_rows = ledger_payload.get("rows", []) if isinstance(ledger_payload.get("rows"), list) else []
                if ledger_rows and hasattr(db, "save_post_scan_outcome_ledger"):
                    stats["post_scan_ledger_rows_upserted"] += int(db.save_post_scan_outcome_ledger(run_dir.name, ledger_rows) or 0)
            except Exception:
                pass
        stats["run_stats"].append({"run_id": run_dir.name, "updated_rows": updated_rows, "changed": changed})

    stats["intraday_fetch_failures"] = dict(_INTRADAY_FETCH_FAILURES)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Update realized outcome rows with 1/2/3/5/7/14/30 day return metrics.")
    parser.add_argument("--shared-dir", type=str, default="runtime_state/shared_working")
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--limit-runs", type=int, default=200)
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="ALL")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_update(
        shared_dir=Path(args.shared_dir),
        run_ids=list(args.run_id or []),
        limit_runs=int(args.limit_runs),
        dry_run=bool(args.dry_run),
        scan_mode_filter=str(args.scan_mode).upper(),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
