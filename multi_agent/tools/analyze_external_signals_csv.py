#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
from typing import Any, Dict, Iterable, Optional

import numpy as np
import pandas as pd
import FinanceDataReader as fdr
import yfinance as yf


KR_TZ = "Asia/Seoul"
US_TZ = "America/New_York"
HORIZONS = (1, 2, 3, 5)


def infer_market(ticker: str) -> str:
    ticker = str(ticker or "").strip().upper()
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return "US"


def market_timezone(market: str) -> str:
    return KR_TZ if market in {"KOSPI", "KOSDAQ"} else US_TZ


def benchmark_symbol(market: str) -> str:
    if market == "KOSPI":
        return "^KS11"
    if market == "KOSDAQ":
        return "^KQ11"
    return "^GSPC"


def benchmark_source_symbol(market: str) -> str:
    if market == "KOSPI":
        return "KS11"
    if market == "KOSDAQ":
        return "KQ11"
    return "US500"


def load_signals(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if df.empty:
        raise RuntimeError(f"No rows in {csv_path}")

    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df["market"] = df["ticker"].map(infer_market)
    df["local_tz"] = df["market"].map(market_timezone)
    df["scan_date_local"] = [
        ts.tz_convert(tz).date() if pd.notna(ts) else pd.NaT
        for ts, tz in zip(df["created_at"], df["local_tz"])
    ]
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["entry_price"] = pd.to_numeric(df.get("entry_price"), errors="coerce")
    df["target_price"] = pd.to_numeric(df.get("target_price"), errors="coerce")
    df["stop_loss"] = pd.to_numeric(df.get("stop_loss"), errors="coerce")
    df["alpha_score"] = pd.to_numeric(df.get("alpha_score"), errors="coerce")
    df["ai_prediction"] = pd.to_numeric(df.get("ai_prediction"), errors="coerce")
    return df


class _FetchTimeout(Exception):
    pass


def _timeout_handler(_signum: int, _frame: Any) -> None:
    raise _FetchTimeout()


def fetch_history(ticker: str, start: str, end: str, timeout_sec: int = 8) -> tuple[str, Optional[pd.DataFrame]]:
    source_ticker = str(ticker or "").strip()
    if source_ticker.endswith(".KS") or source_ticker.endswith(".KQ"):
        source_ticker = source_ticker.split(".")[0]

    previous_handler = signal.getsignal(signal.SIGALRM)
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout_sec)
        hist = fdr.DataReader(source_ticker, start, end)
        signal.alarm(0)
        if hist.empty:
            raise ValueError("empty history")
        hist = hist.copy()
        hist["trade_date"] = hist.index.date
        return ticker, hist
    except Exception:
        try:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout_sec)
            hist = yf.Ticker(ticker).history(
                start=start,
                end=end,
                auto_adjust=False,
                timeout=10,
            )
            signal.alarm(0)
            if hist.empty:
                return ticker, None
            if hist.index.tz is None:
                hist.index = hist.index.tz_localize("UTC")
            hist = hist.copy()
            hist["trade_date"] = hist.index.date
            return ticker, hist
        except Exception:
            return ticker, None
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_handler)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


def fetch_history_map(tickers: Iterable[str], start: str, end: str, max_workers: int = 16) -> Dict[str, pd.DataFrame]:
    tickers = [str(t).strip() for t in tickers if str(t).strip()]
    out: Dict[str, pd.DataFrame] = {}
    total = len(tickers)
    for idx, ticker in enumerate(tickers, start=1):
        symbol, hist = fetch_history(ticker, start, end)
        if hist is not None and not hist.empty:
            out[symbol] = hist
        if idx % 50 == 0 or idx == total:
            print(f"[history] {idx}/{total} fetched={len(out)}")
    return out


def fetch_benchmark_history_map(markets: Iterable[str], start: str, end: str) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    for market in sorted(set(markets)):
        source_symbol = benchmark_source_symbol(market)
        try:
            hist = fdr.DataReader(source_symbol, start, end)
            if hist is None or hist.empty:
                continue
            hist = hist.copy()
            hist["trade_date"] = hist.index.date
            out[benchmark_symbol(market)] = hist
        except Exception:
            continue
    return out


def compute_atr_pct(hist: pd.DataFrame, period: int = 20) -> pd.Series:
    high = pd.to_numeric(hist["High"], errors="coerce")
    low = pd.to_numeric(hist["Low"], errors="coerce")
    close = pd.to_numeric(hist["Close"], errors="coerce")
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period, min_periods=5).mean()
    return (atr / close.replace(0, np.nan)) * 100.0


def classify_regime(ret_pct: float, bull_threshold: float = 0.8, bear_threshold: float = -0.8) -> str:
    if pd.isna(ret_pct):
        return "UNKNOWN"
    if float(ret_pct) >= bull_threshold:
        return "BULL"
    if float(ret_pct) <= bear_threshold:
        return "BEAR"
    return "NEUTRAL"


def enrich_with_returns(df: pd.DataFrame, history_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for row in df.to_dict("records"):
        ticker = str(row.get("ticker") or "").strip()
        hist = history_map.get(ticker)
        for horizon in HORIZONS:
            row[f"return_{horizon}d"] = np.nan
        row["mfe_5d_pct"] = np.nan
        row["mae_5d_pct"] = np.nan
        row["atr20_pct"] = np.nan
        row["base_trade_date"] = None

        if hist is None or hist.empty or pd.isna(row.get("scan_date_local")) or pd.isna(row.get("price")):
            rows.append(row)
            continue

        scan_date = row["scan_date_local"]
        base_price = float(row["price"])
        hist = hist.copy()
        trade_dates = list(hist["trade_date"])
        eligible = hist[hist["trade_date"] >= scan_date]
        if eligible.empty:
            rows.append(row)
            continue

        base_idx = eligible.index[0]
        base_pos = hist.index.get_loc(base_idx)
        row["base_trade_date"] = hist.loc[base_idx, "trade_date"]

        atr_series = compute_atr_pct(hist)
        atr_val = atr_series.iloc[base_pos]
        row["atr20_pct"] = float(atr_val) if pd.notna(atr_val) else np.nan

        for horizon in HORIZONS:
            target_pos = base_pos + horizon
            if target_pos < len(hist):
                close_val = float(hist["Close"].iloc[target_pos])
                row[f"return_{horizon}d"] = ((close_val / base_price) - 1.0) * 100.0

        window = hist.iloc[base_pos + 1 : base_pos + 6]
        if not window.empty:
            max_high = pd.to_numeric(window["High"], errors="coerce").max()
            min_low = pd.to_numeric(window["Low"], errors="coerce").min()
            if pd.notna(max_high):
                row["mfe_5d_pct"] = ((float(max_high) / base_price) - 1.0) * 100.0
            if pd.notna(min_low):
                row["mae_5d_pct"] = ((float(min_low) / base_price) - 1.0) * 100.0

        rows.append(row)
    return pd.DataFrame(rows)


def build_benchmark_regimes(df: pd.DataFrame, benchmark_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    seen: set[tuple[str, Any]] = set()
    for market in sorted(df["market"].dropna().unique()):
        bench = benchmark_symbol(market)
        hist = benchmark_map.get(bench)
        if hist is None or hist.empty:
            continue
        close = pd.to_numeric(hist["Close"], errors="coerce")
        ret_pct = close.pct_change() * 100.0
        for idx in hist.index:
            trade_date = hist.loc[idx, "trade_date"]
            key = (market, trade_date)
            if key in seen:
                continue
            seen.add(key)
            r = float(ret_pct.loc[idx]) if pd.notna(ret_pct.loc[idx]) else np.nan
            records.append(
                {
                    "market": market,
                    "trade_date": trade_date,
                    "benchmark": bench,
                    "benchmark_ret_pct": r,
                    "regime": classify_regime(r),
                }
            )
    return pd.DataFrame(records)


def summarize_regime_performance(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (market, regime), sub in df.groupby(["market", "regime"], dropna=False):
        if sub.empty:
            continue
        payload: Dict[str, Any] = {
            "market": market,
            "regime": regime,
            "signals": int(len(sub)),
            "tickers": int(sub["ticker"].nunique()),
        }
        for horizon in HORIZONS:
            col = f"return_{horizon}d"
            valid = sub[col].dropna()
            payload[f"avg_{horizon}d_pct"] = float(valid.mean()) if not valid.empty else np.nan
            payload[f"win_{horizon}d_pct"] = float((valid > 0).mean() * 100.0) if not valid.empty else np.nan
        rows.append(payload)
    return pd.DataFrame(rows).sort_values(["market", "regime"])


def compute_ticker_policy(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker, sub in df.groupby("ticker", dropna=False):
        sub = sub.sort_values("created_at")
        market = str(sub["market"].iloc[0])
        latest = sub.iloc[-1]
        atr_med = float(pd.to_numeric(sub["atr20_pct"], errors="coerce").median()) if sub["atr20_pct"].notna().any() else np.nan
        mae_abs = pd.to_numeric(sub["mae_5d_pct"], errors="coerce").abs().dropna()
        mfe = pd.to_numeric(sub["mfe_5d_pct"], errors="coerce").dropna()
        positive_mfe = mfe[mfe > 0]
        ret5 = pd.to_numeric(sub["return_5d"], errors="coerce").dropna()

        if len(mae_abs) >= 3:
            stop_pct = float(max(mae_abs.quantile(0.60), (atr_med if pd.notna(atr_med) else 0.0) * 1.10, 2.5))
        else:
            stop_pct = float(max((atr_med if pd.notna(atr_med) else 0.0) * 1.25, 3.0))

        if len(positive_mfe) >= 3:
            safe_tp_pct = float(max(positive_mfe.quantile(0.35), stop_pct * 1.4, (atr_med if pd.notna(atr_med) else 0.0) * 1.8, 4.0))
        elif len(ret5) >= 3 and (ret5 > 0).any():
            safe_tp_pct = float(max(ret5[ret5 > 0].quantile(0.35), stop_pct * 1.4, 4.0))
        else:
            safe_tp_pct = float(max((atr_med if pd.notna(atr_med) else 0.0) * 2.0, stop_pct * 1.5, 4.5))

        stop_pct = min(stop_pct, 20.0)
        safe_tp_pct = min(max(safe_tp_pct, stop_pct * 1.25), 35.0)
        latest_price = float(latest["price"]) if pd.notna(latest["price"]) else np.nan
        rows.append(
            {
                "ticker": ticker,
                "stock_name": latest.get("stock_name"),
                "market": market,
                "signals": int(len(sub)),
                "latest_scan_date": str(latest.get("scan_date_local")),
                "latest_price": latest_price,
                "avg_1d_pct": float(pd.to_numeric(sub["return_1d"], errors="coerce").mean()),
                "avg_2d_pct": float(pd.to_numeric(sub["return_2d"], errors="coerce").mean()),
                "avg_3d_pct": float(pd.to_numeric(sub["return_3d"], errors="coerce").mean()),
                "avg_5d_pct": float(pd.to_numeric(sub["return_5d"], errors="coerce").mean()),
                "win_3d_pct": float((pd.to_numeric(sub["return_3d"], errors="coerce").dropna() > 0).mean() * 100.0),
                "win_5d_pct": float((pd.to_numeric(sub["return_5d"], errors="coerce").dropna() > 0).mean() * 100.0),
                "atr20_pct_median": atr_med,
                "mfe_5d_pct_q35": float(positive_mfe.quantile(0.35)) if len(positive_mfe) >= 1 else np.nan,
                "mae_5d_pct_q60_abs": float(mae_abs.quantile(0.60)) if len(mae_abs) >= 1 else np.nan,
                "adaptive_stop_pct": stop_pct,
                "safe_take_profit_pct": safe_tp_pct,
                "adaptive_stop_price": latest_price * (1.0 - stop_pct / 100.0) if pd.notna(latest_price) else np.nan,
                "safe_take_profit_price": latest_price * (1.0 + safe_tp_pct / 100.0) if pd.notna(latest_price) else np.nan,
                "risk_reward_ratio": safe_tp_pct / stop_pct if stop_pct > 0 else np.nan,
            }
        )

    result = pd.DataFrame(rows)
    return result.sort_values(["signals", "avg_5d_pct", "win_5d_pct"], ascending=[False, False, False])


def build_agent_summary(
    enriched: pd.DataFrame,
    regime_daily: pd.DataFrame,
    regime_perf: pd.DataFrame,
    ticker_policy: pd.DataFrame,
) -> Dict[str, Any]:
    scanner_summary = {
        "rows_loaded": int(len(enriched)),
        "unique_tickers": int(enriched["ticker"].nunique()),
        "markets": enriched["market"].value_counts(dropna=False).to_dict(),
        "signal_types": enriched["signal_type"].value_counts(dropna=False).to_dict(),
    }

    market_summary = regime_daily.groupby(["market", "regime"]).size().reset_index(name="days")
    backtest_summary = {}
    for horizon in HORIZONS:
        col = f"return_{horizon}d"
        valid = pd.to_numeric(enriched[col], errors="coerce").dropna()
        backtest_summary[f"{horizon}d_avg_return_pct"] = float(valid.mean()) if not valid.empty else np.nan
        backtest_summary[f"{horizon}d_win_rate_pct"] = float((valid > 0).mean() * 100.0) if not valid.empty else np.nan

    stable = ticker_policy[ticker_policy["signals"] >= 3].head(15)[
        ["ticker", "stock_name", "signals", "avg_5d_pct", "win_5d_pct", "adaptive_stop_pct", "safe_take_profit_pct"]
    ]
    aggregation_summary = {
        "stable_tickers_top15": stable.to_dict("records"),
    }

    planner_summary = {
        "best_regimes_5d": regime_perf.sort_values("avg_5d_pct", ascending=False).head(6).to_dict("records"),
        "worst_regimes_5d": regime_perf.sort_values("avg_5d_pct", ascending=True).head(6).to_dict("records"),
    }

    return {
        "scanner_agent": scanner_summary,
        "market_context_agent": {
            "daily_regimes": market_summary.to_dict("records"),
        },
        "backtest_learning_agent": backtest_summary,
        "aggregation_agent": aggregation_summary,
        "pm_planner_agent": planner_summary,
    }


def write_markdown_report(
    output_path: Path,
    enriched: pd.DataFrame,
    regime_perf: pd.DataFrame,
    ticker_policy: pd.DataFrame,
    agent_summary: Dict[str, Any],
) -> None:
    def _table(df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return "_no rows_"
        show = df.copy()
        for col in show.columns:
            if pd.api.types.is_float_dtype(show[col]):
                show[col] = show[col].map(lambda v: f"{v:.2f}" if pd.notna(v) else "")
        header = "| " + " | ".join(map(str, show.columns.tolist())) + " |"
        sep = "| " + " | ".join(["---"] * len(show.columns)) + " |"
        body = ["| " + " | ".join(map(str, row)) + " |" for row in show.astype(object).fillna("").values.tolist()]
        return "\n".join([header, sep] + body)

    top_regime = regime_perf.sort_values("avg_5d_pct", ascending=False).head(8)
    weak_regime = regime_perf.sort_values("avg_5d_pct", ascending=True).head(8)
    stable = ticker_policy[ticker_policy["signals"] >= 3].head(15)

    lines = [
        "# External Signals Agent Collaboration Report",
        "",
        "## Agent Roles",
        "- Scanner Agent: CSV 정규화, 시장 분류, 스캔 표본 정리",
        "- Market & News Context Agent: 일별 시장 레짐(BULL/NEUTRAL/BEAR) 라벨링",
        "- Backtest & Learning Agent: 1/2/3/5일 후행 수익률, MFE/MAE, 변동성 계산",
        "- Aggregation Agent: 티커별 적응형 손절/안전 익절 정책 생성",
        "- PM Planner Agent: 레짐별 성과와 티커 정책을 종합해 운영 해석 정리",
        "",
        "## Scanner Agent",
        f"- rows: {len(enriched):,}",
        f"- unique tickers: {enriched['ticker'].nunique():,}",
        f"- markets: {enriched['market'].value_counts(dropna=False).to_dict()}",
        "",
        "## Market Context Agent",
        "- 레짐 기준: benchmark 일간 수익률이 +0.8% 이상이면 BULL, -0.8% 이하이면 BEAR, 그 사이는 NEUTRAL",
        "",
        "## Backtest & Learning Agent",
    ]
    for horizon in HORIZONS:
        col = f"return_{horizon}d"
        valid = pd.to_numeric(enriched[col], errors="coerce").dropna()
        if valid.empty:
            continue
        lines.append(
            f"- {horizon}d avg={valid.mean():+.2f}% / win rate={(valid > 0).mean() * 100:.1f}% / samples={len(valid):,}"
        )

    lines += [
        "",
        "### Best Regime Buckets (by 5d avg return)",
        _table(top_regime),
        "",
        "### Weak Regime Buckets (by 5d avg return)",
        _table(weak_regime),
        "",
        "## Aggregation Agent",
        "- `adaptive_stop_pct`: 티커별 ATR20과 5일 내 adverse excursion(MAE) 분포를 합쳐 계산",
        "- `safe_take_profit_pct`: 티커별 positive MFE / 5일 수익률 분포를 보수적으로 반영",
        "",
        "### Stable Ticker Policies (signals >= 3)",
        _table(
            stable[
                [
                    "ticker",
                    "stock_name",
                    "signals",
                    "avg_5d_pct",
                    "win_5d_pct",
                    "adaptive_stop_pct",
                    "safe_take_profit_pct",
                    "risk_reward_ratio",
                ]
            ]
        ),
        "",
        "## PM Planner Agent",
        "- 제공된 `result_3d` 값에는 극단 outlier가 있어, 본 분석은 외부 가격 데이터로 1/2/3/5일 수익률을 다시 계산함",
        "- 상승/하락/평범장을 분리해 봐야 전략의 진짜 민감도를 볼 수 있음",
        "- 손절/익절은 고정 퍼센트보다 티커별 MAE/MFE/ATR 기반 정책이 더 안전함",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze external signals CSV with multi-agent style outputs.")
    parser.add_argument("--csv", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="runtime_state/reports/external_signals")
    parser.add_argument("--max-workers", type=int, default=16)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_signals(csv_path)
    min_date = pd.to_datetime(df["scan_date_local"]).min()
    max_date = pd.to_datetime(df["scan_date_local"]).max()
    start = (min_date - pd.Timedelta(days=40)).strftime("%Y-%m-%d")
    end = (max_date + pd.Timedelta(days=10)).strftime("%Y-%m-%d")

    tickers = sorted(df["ticker"].dropna().astype(str).unique().tolist())
    benchmarks = sorted({benchmark_symbol(market) for market in df["market"].dropna().unique()})

    history_map = fetch_history_map(tickers=tickers, start=start, end=end, max_workers=args.max_workers)
    benchmark_map = fetch_benchmark_history_map(markets=df["market"].dropna().unique().tolist(), start=start, end=end)

    regime_daily = build_benchmark_regimes(df=df, benchmark_map=benchmark_map)
    enriched = enrich_with_returns(df=df, history_map=history_map)
    if not regime_daily.empty:
        regime_daily["trade_date"] = pd.to_datetime(regime_daily["trade_date"]).dt.date
        enriched = enriched.merge(
            regime_daily[["market", "trade_date", "benchmark", "benchmark_ret_pct", "regime"]],
            left_on=["market", "base_trade_date"],
            right_on=["market", "trade_date"],
            how="left",
        ).drop(columns=["trade_date"])

    regime_perf = summarize_regime_performance(enriched)
    ticker_policy = compute_ticker_policy(enriched)
    agent_summary = build_agent_summary(enriched, regime_daily, regime_perf, ticker_policy)

    enriched_path = output_dir / "signals_rows_enriched.csv"
    regime_daily_path = output_dir / "daily_regime_summary.csv"
    regime_perf_path = output_dir / "regime_performance_summary.csv"
    ticker_policy_path = output_dir / "ticker_risk_policy.csv"
    agent_json_path = output_dir / "agent_collaboration_summary.json"
    report_md_path = output_dir / "agent_collaboration_report.md"

    enriched.to_csv(enriched_path, index=False)
    regime_daily.to_csv(regime_daily_path, index=False)
    regime_perf.to_csv(regime_perf_path, index=False)
    ticker_policy.to_csv(ticker_policy_path, index=False)
    agent_json_path.write_text(json.dumps(agent_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(report_md_path, enriched, regime_perf, ticker_policy, agent_summary)

    manifest = {
        "csv": str(csv_path),
        "outputs": {
            "enriched": str(enriched_path),
            "daily_regime_summary": str(regime_daily_path),
            "regime_performance_summary": str(regime_perf_path),
            "ticker_risk_policy": str(ticker_policy_path),
            "agent_summary_json": str(agent_json_path),
            "agent_report_md": str(report_md_path),
        },
        "fetched_histories": len(history_map),
        "benchmarks": benchmarks,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
