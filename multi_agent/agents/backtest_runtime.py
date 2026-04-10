from __future__ import annotations

from datetime import datetime
import os
from statistics import mean
from typing import Any, Dict, List

from multi_agent.agents.aggregation_runtime import score_stats
from multi_agent.contracts.types import BacktestHandoff, RunContext, WarningItem


def _parse_percent(value: Any) -> float:
    try:
        s = str(value).strip().replace("%", "")
        return float(s)
    except Exception:
        return 0.0


def _parse_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        try:
            return float(str(value).strip())
        except Exception:
            return 0.0


def _parse_int(value: Any) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def _resolve_benchmark_ticker(market: str) -> str:
    m = str(market or "").upper()
    if m in {"KOSPI", "KOSDAQ", "KR", "KOREA"}:
        return "^KS11"
    if m in {"S&P500", "SP500", "US500"}:
        return "^GSPC"
    return "SPY"


def _load_backtest_params() -> Dict[str, float]:
    defaults = {
        "ATR_stop_mult": 1.2,
        "ATR_target_mult": 2.5,
        "Vol_mult": 1.0,
        "alpha_threshold": 40.0,
    }
    try:
        import json
        from pathlib import Path

        path = Path("optimal_params.json")
        if not path.exists():
            return defaults
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return defaults
        return {
            "ATR_stop_mult": float(payload.get("ATR_stop_mult", defaults["ATR_stop_mult"])),
            "ATR_target_mult": float(payload.get("ATR_target_mult", defaults["ATR_target_mult"])),
            "Vol_mult": float(payload.get("Vol_mult", defaults["Vol_mult"])),
            "alpha_threshold": float(payload.get("alpha_threshold", defaults["alpha_threshold"])),
        }
    except Exception:
        return defaults


def _build_regime_windows(
    benchmark_df: Any,
    min_days: int = 20,
) -> Dict[str, Dict[str, Any]]:
    windows: Dict[str, Dict[str, Any]] = {}
    try:
        import pandas as pd

        if benchmark_df is None or benchmark_df.empty or "Close" not in benchmark_df.columns:
            return windows
        df = benchmark_df.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            return windows
        if len(df) < 60:
            return windows

        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma50"] = df["Close"].rolling(50).mean()

        def _label(row: Any) -> str:
            c = float(row.get("Close", 0.0) or 0.0)
            ma20 = float(row.get("ma20", 0.0) or 0.0)
            ma50 = float(row.get("ma50", 0.0) or 0.0)
            if c > ma20 and ma20 > ma50:
                return "BULL"
            if c < ma20 and ma20 < ma50:
                return "BEAR"
            return "NEUTRAL"

        df = df.dropna(subset=["ma20", "ma50"]).copy()
        if df.empty:
            return windows
        df["regime"] = df.apply(_label, axis=1)
        df["group"] = (df["regime"] != df["regime"].shift(1)).cumsum()

        for _, g in df.groupby("group"):
            if g.empty:
                continue
            regime = str(g["regime"].iloc[0])
            days = len(g)
            if days < int(min_days):
                continue
            start = g.index[0]
            end = g.index[-1]
            prev = windows.get(regime)
            if prev is None or str(end) > str(prev.get("end", "")):
                windows[regime] = {
                    "start": start.strftime("%Y-%m-%d"),
                    "end": end.strftime("%Y-%m-%d"),
                    "days": int(days),
                }
    except Exception:
        return {}
    return windows


def _collect_regime_sliced_backtest_sample(
    context: RunContext,
    candidates: List[Dict[str, Any]],
    max_tickers: int,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "unavailable",
        "benchmark": None,
        "windows": {},
        "slices": [],
        "summary": {},
        "errors": [],
        "params": {},
    }
    period = str(os.getenv("AG_REAL_BACKTEST_REGIME_PERIOD", "2y") or "2y")
    min_days = _parse_int(os.getenv("AG_REAL_BACKTEST_REGIME_MIN_DAYS", "20"))
    min_tradeful_regimes = _parse_int(os.getenv("AG_REAL_BACKTEST_REGIME_MIN_TRADEFUL", "2"))
    if min_days <= 0:
        min_days = 20
    if min_tradeful_regimes <= 0:
        min_tradeful_regimes = 2

    selected = sorted(candidates, key=lambda x: float(x.get("score", 0.0) or 0.0), reverse=True)[:max_tickers]
    tickers = [str(c.get("ticker") or "").strip() for c in selected if str(c.get("ticker") or "").strip()]
    if not tickers:
        result["errors"] = ["NO_TICKERS"]
        return result

    try:
        from modules.market_data import get_history
        import backtest_framework as bf
    except Exception as e:
        result["errors"] = [f"IMPORT_FAIL:{e}"]
        return result

    benchmark = _resolve_benchmark_ticker(context.market)
    result["benchmark"] = benchmark

    benchmark_df = get_history(benchmark, period=period, interval="1d")
    if benchmark_df is None or benchmark_df.empty:
        result["errors"] = [f"BENCHMARK_FETCH_FAIL:{benchmark}"]
        return result

    windows = _build_regime_windows(benchmark_df=benchmark_df, min_days=min_days)
    result["windows"] = windows
    if not windows:
        result["errors"] = ["NO_REGIME_WINDOWS"]
        return result

    data: Dict[str, Any] = {}
    for ticker in tickers:
        try:
            df = get_history(ticker, period=period, interval="1d")
            if df is None or df.empty or len(df) < 80:
                result["errors"].append(f"{ticker}:FETCH_OR_LENGTH_FAIL")
                continue
            df2 = bf._calc_indicators(df.copy())
            if df2 is None or df2.empty or len(df2) < 40:
                result["errors"].append(f"{ticker}:INDICATOR_FAIL")
                continue
            data[ticker] = df2
        except Exception as e:
            result["errors"].append(f"{ticker}:{e}")

    if not data:
        result["errors"].append("NO_TICKER_DATA_READY")
        return result

    params = _load_backtest_params()
    result["params"] = params
    slices: List[Dict[str, Any]] = []
    for regime in ["BULL", "NEUTRAL", "BEAR"]:
        w = windows.get(regime)
        if not w:
            continue
        try:
            metrics = bf._backtest_period(
                data=data,
                start=w["start"],
                end=w["end"],
                atrs=float(params["ATR_stop_mult"]),
                atrt=float(params["ATR_target_mult"]),
                volm=float(params["Vol_mult"]),
                alpha_thr=float(params["alpha_threshold"]),
            )
            slices.append(
                {
                    "regime": regime,
                    "start": w["start"],
                    "end": w["end"],
                    "days": int(w["days"]),
                    "n_trades": _parse_int(metrics.get("n_trades", 0)),
                    "win_rate_pct": _parse_float(metrics.get("win_rate", 0)),
                    "avg_pnl_pct": _parse_float(metrics.get("avg_pnl", 0)),
                    "profit_factor": _parse_float(metrics.get("profit_factor", 0)),
                }
            )
        except Exception as e:
            result["errors"].append(f"{regime}:BACKTEST_FAIL:{e}")

    if not slices:
        result["status"] = "partial"
        return result

    tradeful = [s for s in slices if int(s.get("n_trades", 0)) > 0]
    if tradeful:
        best = max(tradeful, key=lambda x: _parse_float(x.get("avg_pnl_pct", 0.0)))
        worst = min(tradeful, key=lambda x: _parse_float(x.get("avg_pnl_pct", 0.0)))
    else:
        best = {}
        worst = {}

    result["slices"] = slices
    result["summary"] = {
        "selected_tickers": tickers,
        "ticker_count": len(tickers),
        "data_ready_ticker_count": len(data),
        "regimes_tested": len(slices),
        "regimes_with_trades": len(tradeful),
        "min_tradeful_regimes": int(min_tradeful_regimes),
        "total_trades": int(sum(_parse_int(s.get("n_trades", 0)) for s in slices)),
        "best_regime_by_avg_pnl": best.get("regime"),
        "worst_regime_by_avg_pnl": worst.get("regime"),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    if len(tradeful) >= int(min_tradeful_regimes):
        result["status"] = "real"
    elif len(tradeful) >= 1:
        result["status"] = "low_sample"
    else:
        result["status"] = "low_sample_no_trades"
    return result


def _collect_real_backtest_sample(
    candidates: List[Dict[str, Any]],
    max_tickers: int,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    errors: List[str] = []
    selected = sorted(candidates, key=lambda x: float(x.get("score", 0.0) or 0.0), reverse=True)[:max_tickers]

    try:
        from modules import quant_analysis
    except Exception as e:
        return {"rows": rows, "errors": [f"IMPORT_FAIL:{e}"], "selected_count": len(selected)}

    for cand in selected:
        ticker = str(cand.get("ticker") or "UNKNOWN")
        try:
            qs = quant_analysis.QuantStrategy(ticker, is_advanced_engine=True)
            if not qs.fetch_data(period="1y"):
                errors.append(f"{ticker}:FETCH_FAIL")
                continue
            qs.calculate_indicators()
            qs.check_signals()
            stats = qs.backtest() or {}
            rows.append(
                {
                    "ticker": ticker,
                    "win_rate_pct": _parse_percent(stats.get("Win Rate", "0%")),
                    "profit_factor": _parse_float(stats.get("Profit Factor", 0)),
                    "total_return_pct": _parse_percent(stats.get("Total Return", "0%")),
                    "total_trades": _parse_int(stats.get("Total Trades", 0)),
                }
            )
        except Exception as e:
            errors.append(f"{ticker}:{e}")

    return {"rows": rows, "errors": errors, "selected_count": len(selected)}


def build_backtest_handoff(
    context: RunContext,
    candidates: List[Dict[str, Any]],
    weak_ratio: float,
) -> BacktestHandoff:
    scores = [float(c.get("score", 0.0) or 0.0) for c in candidates]
    total = len(scores)
    stats = score_stats(scores)
    sample_bucket = "small" if total < 20 else ("medium" if total < 80 else "large")

    enable_real = os.getenv("AG_ENABLE_REAL_BACKTEST_HANDOFF", "1").strip() not in {"0", "false", "False"}
    max_real_tickers = _parse_int(os.getenv("AG_REAL_BACKTEST_MAX_TICKERS", "5"))
    if max_real_tickers <= 0:
        max_real_tickers = 5

    real_sample = {"rows": [], "errors": [], "selected_count": 0}
    regime_sample = {"status": "unknown", "errors": ["SKIPPED"]}
    if enable_real and total > 0:
        real_sample = _collect_real_backtest_sample(candidates=candidates, max_tickers=max_real_tickers)
        regime_sample = _collect_regime_sliced_backtest_sample(
            context=context,
            candidates=candidates,
            max_tickers=max_real_tickers,
        )

    rows = real_sample.get("rows", []) if isinstance(real_sample, dict) else []
    errors = real_sample.get("errors", []) if isinstance(real_sample, dict) else []
    selected_count = int(real_sample.get("selected_count", 0)) if isinstance(real_sample, dict) else 0

    warnings: List[WarningItem] = []
    if rows:
        wr_values = [float(r.get("win_rate_pct", 0.0) or 0.0) for r in rows]
        pf_values = [float(r.get("profit_factor", 0.0) or 0.0) for r in rows]
        ret_values = [float(r.get("total_return_pct", 0.0) or 0.0) for r in rows]
        trade_values = [int(r.get("total_trades", 0) or 0) for r in rows]

        total_trades_sum = int(sum(trade_values))
        avg_trades = (total_trades_sum / len(rows)) if rows else 0.0
        low_trade_rows = sum(1 for v in trade_values if int(v) < 3)
        low_trade_ratio = (low_trade_rows / len(rows)) if rows else 1.0
        trade_bucket = "small" if total_trades_sum < 20 else ("medium" if total_trades_sum < 80 else "large")
        confidence_penalty = 0.15 if total_trades_sum < 20 else (0.08 if total_trades_sum < 80 else 0.0)

        diagnostics = {
            "mode": "quantstrategy_backtest_sampled",
            "candidate_count": total,
            "sample_size_bucket": sample_bucket,
            "score_stats": stats,
            "weak_candidate_ratio": round(weak_ratio, 3),
            "expectancy_proxy": round((stats["mean"] - 50.0) / 50.0, 3),
            "real_backtest": {
                "tested_tickers": len(rows),
                "selected_tickers": selected_count,
                "coverage_ratio": round((len(rows) / total), 3) if total else 0.0,
                "mean_win_rate_pct": round(float(mean(wr_values)) if wr_values else 0.0, 3),
                "mean_profit_factor": round(float(mean(pf_values)) if pf_values else 0.0, 3),
                "mean_total_return_pct": round(float(mean(ret_values)) if ret_values else 0.0, 3),
                "total_trades_sum": total_trades_sum,
                "avg_trades_per_ticker": round(avg_trades, 3),
                "low_trade_ratio": round(low_trade_ratio, 3),
                "sample_rows": rows,
            },
        }
        regime_sensitivity = {
            "status": regime_sample.get("status", "unknown"),
            "benchmark": regime_sample.get("benchmark"),
            "windows": regime_sample.get("windows", {}),
            "slices": regime_sample.get("slices", []),
            "summary": regime_sample.get("summary", {}),
            "errors": regime_sample.get("errors", []),
            "source": "backtest_framework._backtest_period + market_data provider",
        }
        calibration = {
            "status": "mixed",
            "confidence_penalty": confidence_penalty,
            "trade_sample_bucket": trade_bucket,
            "reason": "Confidence penalized by realized trade count in sampled real backtests.",
        }

        warnings.append(
            WarningItem(
                code="REAL_BACKTEST_PARTIAL",
                message=f"Sampled real backtests executed for {len(rows)} tickers (selected={selected_count}).",
                severity="info",
            )
        )
        if low_trade_ratio >= 0.5:
            warnings.append(
                WarningItem(
                    code="LOW_TRADE_DEPTH",
                    message=f"Backtest trade depth is weak (low-trade ratio={low_trade_ratio:.1%}).",
                    severity="warning",
                )
            )
        if errors:
            warnings.append(
                WarningItem(
                    code="REAL_BACKTEST_PARTIAL_FAILURE",
                    message=f"Some real backtest sampling failed ({len(errors)} tickers).",
                    severity="warning",
                )
            )
        regime_status = str(regime_sample.get("status", "unknown"))
        if regime_status in {"partial", "unavailable", "unknown"}:
            warnings.append(
                WarningItem(
                    code="REGIME_BACKTEST_INCOMPLETE",
                    message="Regime-sliced backtest diagnostics are incomplete for this run.",
                    severity="warning",
                )
            )
        elif regime_status in {"low_sample", "low_sample_no_trades"}:
            summary = regime_sample.get("summary", {}) if isinstance(regime_sample.get("summary"), dict) else {}
            trades = _parse_int(summary.get("total_trades", 0))
            warnings.append(
                WarningItem(
                    code="REGIME_BACKTEST_LOW_SAMPLE",
                    message=f"Regime diagnostics exist but trade depth is low (total_trades={trades}).",
                    severity="warning",
                )
            )
        else:
            warnings.append(
                WarningItem(
                    code="REGIME_BACKTEST_READY",
                    message="Regime-sliced backtest diagnostics are attached.",
                    severity="info",
                )
            )
    else:
        confidence_penalty = 0.15 if total < 20 else (0.08 if total < 80 else 0.0)
        diagnostics = {
            "mode": "proxy_from_scanner_handoff",
            "candidate_count": total,
            "sample_size_bucket": sample_bucket,
            "score_stats": stats,
            "weak_candidate_ratio": round(weak_ratio, 3),
            "expectancy_proxy": round((stats["mean"] - 50.0) / 50.0, 3),
            "real_backtest": {
                "tested_tickers": 0,
                "selected_tickers": selected_count,
                "errors": errors[:10],
            },
        }
        regime_sensitivity = {
            "status": regime_sample.get("status", "unknown"),
            "benchmark": regime_sample.get("benchmark"),
            "windows": regime_sample.get("windows", {}),
            "slices": regime_sample.get("slices", []),
            "summary": regime_sample.get("summary", {}),
            "errors": regime_sample.get("errors", []),
            "source": "backtest_framework._backtest_period + market_data provider",
        }
        calibration = {
            "status": "proxy_only",
            "confidence_penalty": confidence_penalty,
            "reason": "Sample-size and realized-outcome linkage are incomplete.",
        }

        warnings.append(
            WarningItem(
                code="PROXY_BACKTEST_ONLY",
                message="Backtest handoff is proxy-only in this stage; connect real diagnostics next.",
                severity="warning",
            )
        )
        if total < 20:
            warnings.append(
                WarningItem(
                    code="SMALL_SAMPLE",
                    message=f"Sample size is small ({total} candidates).",
                    severity="warning",
                )
            )

    return BacktestHandoff(
        run_context=context,
        diagnostics=diagnostics,
        regime_sensitivity=regime_sensitivity,
        calibration=calibration,
        warnings=warnings,
    )
