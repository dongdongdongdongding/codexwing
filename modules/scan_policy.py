from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd

from modules.live_scan_context import live_mode_enabled, normalize_market_key
from modules.market_data import get_history


def _last_two_valid_closes(df: pd.DataFrame) -> tuple[float | None, float | None]:
    if df is None or df.empty or "Close" not in df.columns:
        return None, None
    closes = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if len(closes) < 2:
        return None, None
    prev_close = float(closes.iloc[-2])
    latest_close = float(closes.iloc[-1])
    return prev_close, latest_close


def _latest_hourly_session_change(symbol: str) -> Tuple[float | None, pd.Timestamp | None]:
    intraday = get_history(symbol, period="5d", interval="1h")
    if intraday.empty or len(intraday) < 2 or "Close" not in intraday.columns:
        return None, None
    intraday = intraday.copy()
    intraday["trade_date"] = pd.to_datetime(intraday.index).date
    grouped = pd.to_numeric(intraday.groupby("trade_date")["Close"].last(), errors="coerce").dropna()
    if len(grouped) < 2:
        return None, None
    latest_date = pd.Timestamp(grouped.index[-1])
    latest_close = float(grouped.iloc[-1])
    prev_close = float(grouped.iloc[-2])
    if prev_close == 0:
        return None, latest_date
    return (latest_close - prev_close) / prev_close * 100.0, latest_date


def _latest_session_change_detail(symbol: str, market: str) -> Dict[str, Any]:
    daily = get_history(symbol, period="10d", interval="1d")
    prev_close, latest_close = _last_two_valid_closes(daily)
    daily_valid_last_date = None
    daily_has_nan_tail = False
    if daily is not None and not daily.empty and "Close" in daily.columns:
        daily_close = pd.to_numeric(daily["Close"], errors="coerce")
        daily_has_nan_tail = bool(pd.isna(daily_close.iloc[-1]))
        valid_daily = daily_close.dropna()
        if not valid_daily.empty:
            daily_valid_last_date = pd.Timestamp(valid_daily.index[-1]).normalize()

    hourly_change, hourly_latest_date = _latest_hourly_session_change(symbol)

    # Prefer hourly session data when the market is open, or when daily data is stale / missing
    # the latest completed session (common for KRX index feeds around close-to-next-open windows).
    should_prefer_hourly = bool(live_mode_enabled(market))
    if hourly_change is not None and hourly_latest_date is not None:
        if daily_has_nan_tail:
            should_prefer_hourly = True
        elif daily_valid_last_date is None:
            should_prefer_hourly = True
        elif hourly_latest_date.normalize() > daily_valid_last_date:
            should_prefer_hourly = True
    if should_prefer_hourly and hourly_change is not None:
        return {
            "change_pct": float(hourly_change),
            "source": "hourly_fallback" if not live_mode_enabled(market) else "hourly_live",
            "session_date": str(hourly_latest_date.date()) if hourly_latest_date is not None else "",
        }

    if prev_close not in (None, 0) and latest_close is not None:
        daily_change = float((latest_close - prev_close) / prev_close * 100)
        return {
            "change_pct": daily_change,
            "source": "daily",
            "session_date": str(daily_valid_last_date.date()) if daily_valid_last_date is not None else "",
        }
    return {"change_pct": 0.0, "source": "fallback_zero", "session_date": ""}


def _latest_session_change(symbol: str, market: str) -> float:
    return float(_latest_session_change_detail(symbol, market).get("change_pct", 0.0) or 0.0)


def _gate_benchmarks(market: str) -> Dict[str, Any]:
    key = str(market or "KOSPI").upper()
    if key in {"KOSPI", "KOSDAQ", "KR"}:
        return {
            "region": "KR",
            "labels": ("KOSPI", "KOSDAQ"),
            "symbols": ("^KS11", "^KQ11"),
        }
    if key == "NASDAQ":
        return {
            "region": "US",
            "labels": ("NASDAQ", "S&P500"),
            "symbols": ("^IXIC", "^GSPC"),
        }
    if key == "S&P500":
        return {
            "region": "US",
            "labels": ("S&P500", "NASDAQ"),
            "symbols": ("^GSPC", "^IXIC"),
        }
    if key == "AMEX":
        return {
            "region": "US",
            "labels": ("AMEX", "NASDAQ"),
            "symbols": ("^XAX", "^IXIC"),
        }
    return {
        "region": "US",
        "labels": ("S&P500", "NASDAQ"),
        "symbols": ("^GSPC", "^IXIC"),
    }


def compute_market_gate(market: str = "KOSPI") -> Dict[str, Any]:
    """Market gate aligned to the selected market's regional benchmarks."""
    try:
        config = _gate_benchmarks(market)
        region = str(config.get("region") or "KR")
        primary_label, secondary_label = config["labels"]
        primary_symbol, secondary_symbol = config["symbols"]

        primary_detail = _latest_session_change_detail(primary_symbol, region)
        secondary_detail = _latest_session_change_detail(secondary_symbol, region)
        primary_chg = float(primary_detail.get("change_pct", 0.0) or 0.0)
        secondary_chg = float(secondary_detail.get("change_pct", 0.0) or 0.0)
        avg_chg = (primary_chg + secondary_chg) / 2
        live_tag = "장중" if live_mode_enabled(region) else "종가"
        source_parts = [
            str(primary_detail.get("source") or "unknown"),
            str(secondary_detail.get("source") or "unknown"),
        ]
        source_text = " / ".join(source_parts)
        if avg_chg <= -1.5:
            gate = "RED"
            msg = (
                f"{live_tag} 하락장 경보: {primary_label} {primary_chg:+.2f}% / {secondary_label} {secondary_chg:+.2f}% "
                f"— 신규 매수 자제 [{source_text}]"
            )
        elif avg_chg <= -0.5:
            gate = "YELLOW"
            msg = (
                f"{live_tag} 시장 주의: {primary_label} {primary_chg:+.2f}% / {secondary_label} {secondary_chg:+.2f}% "
                f"— 고확신 종목만 [{source_text}]"
            )
        else:
            gate = "GREEN"
            msg = (
                f"{live_tag} 시장 정상: {primary_label} {primary_chg:+.2f}% / {secondary_label} {secondary_chg:+.2f}% "
                f"— 스캔 조건 양호 [{source_text}]"
            )
        return {
            "gate": gate,
            "region": region,
            "selected_market": str(market or "").upper(),
            "primary_label": primary_label,
            "secondary_label": secondary_label,
            "primary_chg": primary_chg,
            "secondary_chg": secondary_chg,
            "msg": msg,
            "live_mode": bool(live_mode_enabled(region)),
            "primary_source": primary_detail.get("source"),
            "secondary_source": secondary_detail.get("source"),
            "primary_session_date": primary_detail.get("session_date"),
            "secondary_session_date": secondary_detail.get("session_date"),
            "theme_exception_allowance": gate in {"YELLOW", "RED"},
            # Backward-compatible KR keys used by older summaries.
            "kospi_chg": primary_chg if primary_label == "KOSPI" else 0.0,
            "kosdaq_chg": secondary_chg if secondary_label == "KOSDAQ" else 0.0,
        }
    except Exception as exc:
        return {
            "gate": "GREEN",
            "region": str(market or "KOSPI").upper(),
            "selected_market": str(market or "").upper(),
            "primary_chg": 0.0,
            "secondary_chg": 0.0,
            "kospi_chg": 0.0,
            "kosdaq_chg": 0.0,
            "msg": f"시장 데이터 로딩 실패: {exc}",
        }


def compute_rank_adjustment(
    real_trend: str,
    position: str,
    strategy_tag: str,
    tier: str,
    whale_score: float,
    vol_ratio: float,
    volume_confirmed: bool | None = None,
    macro_ctx: Dict[str, Any] | None = None,
    consec_days: int = 0,
) -> float:
    """Decision Score v2 rank adjustment favoring durable movers over late chases."""
    rank_adjust = 0.0

    is_peak = bool(position and "Peak" in position)
    is_rising = bool(position and "Rising" in position)
    is_resting = bool(position and "Resting" in position)
    is_overheat = bool(
        strategy_tag and any(tag in strategy_tag for tag in ["과열", "Overheat", "Exhaustion"])
    )
    is_rsidiv = bool(strategy_tag and "RSI_DIV" in strategy_tag)
    is_obvdiv = bool(strategy_tag and "OBV_DIV" in strategy_tag)
    tier_text = str(tier or "")
    volume_ok = bool(volume_confirmed) if volume_confirmed is not None else float(vol_ratio) >= 1.0
    leader_context = bool(
        strategy_tag
        and any(tag in strategy_tag for tag in ("Profile:POSITIVE", "주도주 하이패스", "ContextTailwind"))
    )
    strong_peak_leader = bool(
        is_peak
        and is_overheat
        and volume_ok
        and float(vol_ratio) >= 2.5
        and any(marker in tier_text for marker in ("T0", "T1"))
        and (float(whale_score) >= 60.0 or leader_context)
    )

    if real_trend == "UP":
        rank_adjust += 6
    elif real_trend == "DOWN":
        rank_adjust -= 8

    if is_rising:
        rank_adjust += 5
    if is_resting:
        rank_adjust += 1

    if is_peak:
        rank_adjust -= 10

    if is_overheat:
        rank_adjust -= 8

    if volume_ok:
        rank_adjust += 4
    else:
        rank_adjust -= 5

    if whale_score >= 60:
        rank_adjust += 3
    elif whale_score >= 50:
        rank_adjust += 1

    if "T3" in tier_text:
        rank_adjust -= 4
    elif "T2" in tier_text:
        rank_adjust += 5 if volume_ok else -3
    elif any(marker in tier_text for marker in ("T0", "T1")):
        rank_adjust += 5

    if strong_peak_leader:
        # Preserve room for genuine explosive leaders instead of flattening them as late chases.
        rank_adjust += 12

    if consec_days >= 3 and real_trend == "UP" and is_rising and volume_ok and not is_peak:
        rank_adjust += 2

    if is_rsidiv:
        rank_adjust -= 8
    elif is_obvdiv and not is_overheat:
        rank_adjust -= 4

    if macro_ctx:
        penalty = float(macro_ctx.get("macro_penalty", 0) or 0)
        rank_adjust -= min(penalty, 8)

    return rank_adjust
