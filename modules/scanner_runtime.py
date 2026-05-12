from __future__ import annotations

import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import pandas as pd

from modules import db_manager, quant_analysis
from modules.scanner_services import (
    compute_exhaustion_context,
    evaluate_active_signal_candidate,
    evaluate_app_kr_candidate,
    evaluate_intraday_candidate,
    evaluate_app_us_candidate,
    evaluate_universe_candidate,
    passes_liquidity_filter,
    resolve_liquidity_gate,
)

_DB_MANAGER_LOCK = threading.Lock()
_DB_MANAGER_SINGLETON: Optional[db_manager.DBManager] = None


def _get_db_manager() -> db_manager.DBManager:
    global _DB_MANAGER_SINGLETON
    with _DB_MANAGER_LOCK:
        if _DB_MANAGER_SINGLETON is None:
            _DB_MANAGER_SINGLETON = db_manager.DBManager()
        return _DB_MANAGER_SINGLETON


@dataclass
class SharedBackoffState:
    """Thread-safe shared backoff timestamp used by scanner workers."""

    backoff_until: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def wait_if_needed(self) -> None:
        while True:
            with self._lock:
                remaining = self.backoff_until - time.time()
            if remaining <= 0:
                return
            time.sleep(min(1.0, max(0.05, remaining)))

    def set_backoff(self, wait_secs: float) -> None:
        deadline = time.time() + max(0.0, float(wait_secs))
        with self._lock:
            if deadline > self.backoff_until:
                self.backoff_until = deadline


def scan_symbol_with_retry(
    sym: str,
    *,
    tickers_dict: Dict[str, str],
    is_us: bool,
    is_amex: bool,
    is_advanced_engine: bool,
    r_status: str,
    intel_data: Any,
    macro_ctx: Any,
    market_gate: Dict[str, Any],
    rank_adjustment_fn: Callable[..., float],
    news_adjustment_fn: Callable[..., Dict[str, Any]],
    backoff_state: SharedBackoffState,
    max_retries: int = 2,
    scan_mode: str = "SWING",
    run_id: Optional[str] = None,
    reject_reason_fn: Optional[Callable[[str, str], None]] = None,
    reject_detail_fn: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Optional[Dict[str, Any]]:
    """Run one scanner symbol with retry/backoff and return row or error payload."""

    def _reject(reason: str) -> None:
        if reject_reason_fn is None:
            return
        try:
            reject_reason_fn(sym, reason)
        except Exception:
            pass

    def _reject_detail(meta: Dict[str, Any]) -> None:
        if reject_detail_fn is None:
            return
        try:
            reject_detail_fn(sym, meta)
        except Exception:
            pass

    for worker_attempt in range(max_retries + 1):
        backoff_state.wait_if_needed()
        try:
            stock_name = tickers_dict.get(sym, sym)
            mode = str(scan_mode or "SWING").strip().upper()

            if mode == "INTRADAY":
                qs = quant_analysis.QuantStrategy(sym, is_advanced_engine=is_advanced_engine)
                qs.scan_mode = mode
                qs.strategy_family = "AMEX_MOONSHOT" if is_amex else ("US_MAIN" if is_us else "KR_CORE")
                if not qs.fetch_data(period="60d", interval="1h"):
                    _reject("INTRADAY_FETCH_FAIL")
                    return None
                outputs = evaluate_intraday_candidate(
                    sym=sym,
                    stock_name=stock_name,
                    qs=qs,
                    is_us=bool(is_us),
                    is_amex=bool(is_amex),
                    r_status=str(r_status),
                    intel_data=intel_data,
                    market_gate=market_gate,
                    news_adjustment_fn=news_adjustment_fn,
                    reject_reason_fn=lambda reason: _reject(reason),
                    reject_meta_fn=lambda meta: _reject_detail(meta),
                )
                if not outputs:
                    return None
                try:
                    if run_id:
                        outputs["db_payload"]["run_id"] = str(run_id)
                    db = _get_db_manager()
                    db.upsert_scan_result(outputs["db_payload"])
                except Exception as e:
                    print(f"Intraday Scan DB Error: {e}")
                return outputs["res_data"]

            qs = quant_analysis.QuantStrategy(sym, is_advanced_engine=is_advanced_engine)
            qs.scan_mode = mode
            qs.strategy_family = "AMEX_MOONSHOT" if is_amex else ("US_MAIN" if is_us else "KR_CORE")
            if not qs.fetch_data(period="5y"):
                _reject("FETCH_DATA_FAIL")
                return None

            qs.calculate_indicators()
            qs.check_signals()

            if qs.df is None or "Antigrav_Score" not in qs.df.columns or pd.isna(qs.df["Antigrav_Score"].iloc[-1]):
                _reject("MISSING_ANTIGRAV_SCORE")
                return None

            tech_score = int(qs.df["Antigrav_Score"].iloc[-1]) if "Antigrav_Score" in qs.df.columns else 0
            ex_ctx = compute_exhaustion_context(qs.df, is_us=is_us)
            if not ex_ctx:
                _reject("EXHAUSTION_CONTEXT_UNAVAILABLE")
                return None

            curr_c = float(ex_ctx["curr_price"])
            turnover = float(ex_ctx["turnover"])
            prev_pct_change = float(ex_ctx["prev_pct_change"])
            consec_days = int(ex_ctx["consec_days"])
            is_exhausted = bool(ex_ctx["is_exhausted"])
            exhaustion_tag = str(ex_ctx["exhaustion_tag"])

            if not passes_liquidity_filter(curr_price=curr_c, turnover=turnover, is_us=is_us, ticker=sym):
                liquidity_gate = resolve_liquidity_gate(is_us=is_us, ticker=sym)
                _reject_detail(
                    {
                        "ticker": sym,
                        "stock_name": stock_name,
                        "stage": "liquidity_gate",
                        "curr_price": round(float(curr_c), 2),
                        "turnover": round(float(turnover), 2),
                        "liquidity_market": liquidity_gate.get("market"),
                        "min_price": liquidity_gate.get("min_price"),
                        "min_turnover": liquidity_gate.get("min_turnover"),
                    }
                )
                _reject("LIQUIDITY_FILTER_FAIL")
                return None

            if is_us:
                outputs = evaluate_app_us_candidate(
                    sym=sym,
                    stock_name=stock_name,
                    qs=qs,
                    is_amex=bool(is_amex),
                    is_exhausted=bool(is_exhausted),
                    exhaustion_tag=str(exhaustion_tag),
                    prev_pct_change=float(prev_pct_change),
                    consec_days=int(consec_days),
                    r_status=str(r_status),
                    intel_data=intel_data,
                    tech_score=int(tech_score),
                    macro_ctx=macro_ctx,
                    market_gate=market_gate,
                    rank_adjustment_fn=rank_adjustment_fn,
                    news_adjustment_fn=news_adjustment_fn,
                    reject_reason_fn=lambda reason: _reject(reason),
                    reject_meta_fn=lambda meta: _reject_detail(meta),
                )
                if not outputs:
                    return None
                try:
                    if run_id:
                        outputs["db_payload"]["run_id"] = str(run_id)
                    db = _get_db_manager()
                    db.upsert_scan_result(outputs["db_payload"])
                except Exception as e:
                    print(f"US Scan DB Error: {e}")
                return outputs["res_data"]

            outputs = evaluate_app_kr_candidate(
                sym=sym,
                stock_name=stock_name,
                qs=qs,
                is_exhausted=bool(is_exhausted),
                exhaustion_tag=str(exhaustion_tag),
                prev_pct_change=float(prev_pct_change),
                consec_days=int(consec_days),
                r_status=str(r_status),
                intel_data=intel_data,
                tech_score=int(tech_score),
                market_gate=market_gate,
                macro_ctx=macro_ctx,
                rank_adjustment_fn=rank_adjustment_fn,
                news_adjustment_fn=news_adjustment_fn,
                reject_reason_fn=lambda reason: _reject(reason),
                reject_meta_fn=lambda meta: _reject_detail(meta),
            )
            if not outputs:
                return None
            try:
                if run_id:
                    outputs["db_payload"]["run_id"] = str(run_id)
                db = _get_db_manager()
                db.upsert_scan_result(outputs["db_payload"])
            except Exception as e:
                print(f"Web Scan DB Error: {e}")
            return outputs["res_data"]

        except quant_analysis.RateLimitError:
            if worker_attempt < max_retries:
                wait_secs = 25 + (worker_attempt * 10)
                print(
                    f"⏳ [RETRY {worker_attempt+1}/{max_retries}] "
                    f"Rate Limit at {sym}. Waiting {wait_secs}s then retrying..."
                )
                backoff_state.set_backoff(wait_secs)
                time.sleep(wait_secs)
                continue
            print(f"❌ {sym}: Rate Limit max retries exhausted. Skipping.")
            _reject("RATE_LIMIT_EXHAUSTED")
            return {"error": "RATE_LIMIT_EXHAUSTED", "ticker": sym}
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error {sym}: {tb}")
            return {"error": f"{str(e)} \nDETAIL: {tb}", "ticker": sym}

    return None


def run_parallel_scan(
    *,
    ticker_list: list[str],
    max_scan: int,
    worker_fn: Callable[[str], Optional[Dict[str, Any]]],
    max_workers: int = 2,
    on_item: Optional[Callable[[int, int, str, Optional[Dict[str, Any]], Optional[Exception]], None]] = None,
) -> Dict[str, Any]:
    """Run scanner workers in parallel and report item-level events via callback."""

    selected = list(ticker_list) if int(max_scan or 0) <= 0 else ticker_list[:max_scan]
    total_scans = len(selected)
    results: list[Dict[str, Any]] = []
    error_count = 0

    if total_scans == 0:
        return {"results": results, "total_scans": 0, "error_count": 0}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_fn, sym): sym for sym in selected}
        for i, future in enumerate(as_completed(futures)):
            sym = futures[future]
            data: Optional[Dict[str, Any]] = None
            exc: Optional[Exception] = None
            try:
                data = future.result()
            except Exception as e:
                exc = e
                error_count += 1

            if on_item is not None:
                on_item(i, total_scans, sym, data, exc)

            if data and "error" not in data:
                results.append(data)
            elif data and "error" in data:
                error_count += 1

    return {
        "results": results,
        "total_scans": total_scans,
        "error_count": error_count,
    }


def resolve_hourly_market_candidates(
    all_candidates: list[Dict[str, Any]],
    hour: int,
    logger: Callable[[str], None] = print,
) -> Dict[str, Any]:
    """Select hourly active candidates based on KR/US time window logic."""
    if 7 <= int(hour) < 17:
        logger("🇰🇷 KR Market Mode: Scanning KOSPI/KOSDAQ...")
        active_candidates = [
            c for c in all_candidates if ".KS" in str(c.get("ticker", "")) or ".KQ" in str(c.get("ticker", ""))
        ]
        return {
            "active_candidates": active_candidates,
            "market_status": "KR_OPEN",
            "market_name": "🇰🇷 KR Market (KOSPI/DAQ)",
        }

    logger("🇺🇸 US Market Mode: Scanning S&P500/NASDAQ...")
    active_candidates = [
        c for c in all_candidates if ".KS" not in str(c.get("ticker", "")) and ".KQ" not in str(c.get("ticker", ""))
    ]
    return {
        "active_candidates": active_candidates,
        "market_status": "US_OPEN",
        "market_name": "🇺🇸 US Market (S&P/NASDAQ)",
    }


def fetch_hourly_regime_status(
    market_status: str,
    logger: Callable[[str], None] = print,
) -> str:
    """Fetch market regime once per hourly scan (legacy behavior parity)."""
    regime_status = "NEUTRAL"
    try:
        regime_ticker = "005930.KS" if "KR" in str(market_status) else "AAPL"
        qs_regime = quant_analysis.QuantStrategy(regime_ticker)
        regime_info = qs_regime.get_advanced_regime()
        regime_status = str(regime_info.get("status", "NEUTRAL"))
        confidence = float(regime_info.get("confidence", 0.0) or 0.0)
        logger(f"🌍 Market Regime: {regime_status} (Conf: {confidence:.2f})")
    except Exception as e:
        logger(f"Regime Fetch Fail: {e}")
    return regime_status


def collect_hourly_signals(
    active_candidates: list[Dict[str, Any]],
    regime_status: str,
    save_signal_fn: Callable[..., None],
    logger: Callable[[str], None] = print,
) -> list[Dict[str, Any]]:
    """Evaluate active-watchlist candidates and collect signal payloads."""
    signals_to_report: list[Dict[str, Any]] = []

    for item in active_candidates:
        ticker = str(item.get("ticker", ""))
        if not ticker:
            continue
        stock_name = str(item.get("name", ticker))
        try:
            eval_result = evaluate_active_signal_candidate(
                ticker=ticker,
                stock_name=stock_name,
                regime_status=regime_status,
            )
            if not eval_result:
                continue
            if eval_result.get("skip_reason") == "MARKET_CRASH":
                logger(f"⚠️ Market Crash Detected ({ticker}). Skipping Buy Signal.")
                continue

            logger(str(eval_result.get("log_line", f"Signal: {ticker}")))
            save_payload = eval_result.get("save_signal_payload", {})
            if isinstance(save_payload, dict):
                save_signal_fn(**save_payload)

            signal_data = eval_result.get("signal_data")
            if isinstance(signal_data, dict):
                signals_to_report.append(signal_data)
        except Exception as e:
            logger(f"Error scanning {ticker}: {e}")

    return signals_to_report


def format_hourly_signal_message(signal_data: Dict[str, Any]) -> str:
    """Render Telegram markdown body for one top signal.

    Per-segment exit policy: derived 2026-04-28 from
    optimize_exit_policy_per_segment.py sweep over OOS picks of the live
    bundles, using a limit-buy @ -2% entry model with same-bar TP/SL and
    a hold-day forced close.

    KOSDAQ swing  : entry -2% / TP +10% / SL -10% / hold 5d
                    n=33  win 75.8%  avg +5.88%  median +10.00%
    KOSPI  swing  : entry  open / TP +20% / SL -5%  / hold 5d
                    (limit-buy @ -2% had too many no-fills in OOS)
                    n=28  win 71.4%  avg +9.08%  median +10.50%

    These targets meet the 75%/15% bar more closely than the prior fixed
    +3.5% / -3% defaults. Choice driven by ticker suffix (.KQ → KOSDAQ,
    else KOSPI/US default).
    """
    s = signal_data
    currency = str(s.get("currency", "$"))
    ticker = str(s.get("ticker") or "")
    is_kosdaq = ticker.endswith(".KQ")
    is_kr = ticker.endswith(".KS") or is_kosdaq

    if is_kosdaq:
        entry_label = "Limit Buy @ -2% (KOSDAQ)"
        tp_label = "Target (+10%)"
        sl_label = "Stop Loss (-10%)"
        hold_note = "Hold up to 5d"
    elif is_kr:
        entry_label = "Open Buy (KOSPI)"
        tp_label = "Target (+20%)"
        sl_label = "Stop Loss (-5%)"
        hold_note = "Hold up to 5d"
    else:
        entry_label = "Limit Buy @ -2%"
        tp_label = f"Target (+3.5%)"
        sl_label = "Stop Loss (-3%)"
        hold_note = "Hold 1-3d"

    return f"""
{s.get('emoji', '👀')} **{s.get('title', 'BUY')}** {s.get('emoji', '👀')}

**Stock**: {s.get('stock_name', '-')}
**Symbol**: `{s.get('ticker', '-')}`
**Price**: {currency}{float(s.get('price', 0) or 0):,.0f}

📊 **Pro Analysis**
• **Alpha Score**: {float(s.get('score', 0) or 0):.0f}/100
• **Market Regime**: {s.get('regime', '-')}
• **Quality**: {s.get('fund_note', '-')}

🎯 **Strategy: {entry_label}**
• Entry: {currency}{float(s.get('entry', 0) or 0):,.2f}
• {tp_label}: {currency}{float(s.get('target', 0) or 0):,.2f}
• {sl_label}: {currency}{float(s.get('stop_loss', 0) or 0):,.2f}
• {hold_note}
• Size: {s.get('kelly', '0%')} of Capital

*Generated by Pro-Quant Bot* 🧠
"""


def collect_universe_scan_candidates(
    df_tickers: Any,
    *,
    market_code: str = "US",
    save_scan_result_fn: Optional[Callable[[Dict[str, Any]], None]] = None,
    logger: Callable[[str], None] = print,
) -> list[Dict[str, Any]]:
    """Evaluate a universe dataframe and collect candidate rows (legacy bot parity)."""
    candidates: list[Dict[str, Any]] = []
    top_100_tickers: list[str] = []

    try:
        if "Marcap" in df_tickers.columns:
            df_sorted = df_tickers.sort_values(by="Marcap", ascending=False)
            top_100_tickers = [str(x) for x in df_sorted.head(100)["Code"].tolist()]
        else:
            top_100_tickers = [str(x) for x in df_tickers.head(100)["Code"].tolist()]
    except Exception:
        top_100_tickers = [str(x) for x in df_tickers.head(100)["Code"].tolist()]

    logger(f"💎 Identified {len(top_100_tickers)} Top Market Cap stocks.")

    count = 0
    total = len(df_tickers)
    for _idx, row in df_tickers.iterrows():
        ticker = str(row.get("Code", ""))
        name = str(row.get("Name", ticker))
        if not ticker:
            continue

        count += 1
        is_top_100 = ticker in top_100_tickers
        if count % 100 == 0:
            logger(f"Scanning {count}/{total}...")

        try:
            eval_result = evaluate_universe_candidate(
                ticker=ticker,
                name=name,
                market_code=market_code,
                is_top_100=is_top_100,
            )
            if not eval_result:
                continue

            candidate_data = eval_result.get("candidate_data")
            is_active = bool(eval_result.get("is_active"))
            if isinstance(candidate_data, dict):
                candidates.append(candidate_data)
                if is_active and save_scan_result_fn is not None:
                    save_scan_result_fn(candidate_data)
        except Exception:
            continue

    return candidates
