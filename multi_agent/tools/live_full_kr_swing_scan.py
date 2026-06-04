#!/usr/bin/env python3
"""Full-ML KR SWING scan — drives the production path that auto_bot uses.

Why this exists
---------------
collect_universe_scan_candidates is the light path; it does not invoke
phase25. To verify scan↔archive top-5 parity (and to surface this session's
gate fixes end-to-end), we need scan_symbol_with_retry against a real KR
universe with phase25 models loaded. This wraps that for KOSPI + KOSDAQ
liquid universe and runs the legacy bridge so planner_handoff.json gets
written.

Scope
-----
KOSPI top 100 by Marcap + KOSDAQ top 100 by Marcap. Filters out 스팩/ETF/ETN.
Each ticker goes through scan_symbol_with_retry(scan_mode='SWING'); the
results feed run_legacy_agent_bridge which produces the orchestrator + planner
handoff files under runtime_state/shared_working/RUN-<id>/.

Outputs
-------
- DB rows in market_scan_results (feature_origin='live_full_scan')
- New RUN-<id>/ with full handoff bundle
- Console summary of decisions distribution

Usage
-----
  python3 multi_agent/tools/live_full_kr_swing_scan.py [--limit 50]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from modules.scanner_bridge import run_legacy_agent_bridge  # noqa: E402
from modules.scanner_runtime import (  # noqa: E402
    SharedBackoffState,
    scan_symbol_with_retry,
)


def _noop_news(stock_name=None, ticker=None, news_text=None, intel_data=None,
                *args, **kwargs):
    return {"score_adjustment": 0.0, "reasons": []}


def _noop_rank(*args, **kwargs):
    return 0.0


def _load_kr_universe(limit_per_market: int) -> pd.DataFrame:
    """Load KOSPI + KOSDAQ liquid tickers, sorted by Marcap descending.

    KRX-DESC orders alphabetically — taking head() returns small caps that
    fail the turnover filter. Use KOSPI/KOSDAQ listing endpoints which carry
    Marcap, and filter out 스팩/ETN/ETF.
    """
    if _prefers_kis_universe():
        kis_df = _load_kis_rank_universe(limit_per_market)
        if not kis_df.empty:
            return kis_df

    import FinanceDataReader as fdr
    parts = []
    for market_label, suffix in (("KOSPI", ".KS"), ("KOSDAQ", ".KQ")):
        try:
            df = fdr.StockListing(market_label)
            if "Marcap" in df.columns:
                df = df.sort_values("Marcap", ascending=False)
            elif "Marketcap" in df.columns:
                df = df.sort_values("Marketcap", ascending=False)
            df = df[~df["Name"].str.contains("스팩|ETN|ETF", case=False, na=False)]
            df = df.head(limit_per_market).copy()
            df["Code"] = df["Code"].astype(str).str.zfill(6) + suffix
            parts.append(df[["Code", "Name"]])
        except Exception as exc:
            print(f"  ⚠️ failed to load {market_label}: {exc}")
    if not parts:
        return _load_kis_rank_universe(limit_per_market)
    return pd.concat(parts).reset_index(drop=True)


def _prefers_kis_universe() -> bool:
    raw = str(os.getenv("AG_KR_UNIVERSE_PROVIDER") or os.getenv("AG_KR_MARKET_DATA_PROVIDER") or "")
    return raw.strip().lower() in {"kis", "kis_first", "kis_rank", "kis_openapi"}


def _load_kis_rank_universe(limit_per_market: int) -> pd.DataFrame:
    """Load a small real KIS universe from domestic volume ranking endpoints."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
        load_dotenv(PROJECT_ROOT / ".env.local")
        from modules.kis_openapi import KISConfig, KISOpenAPIClient, normalize_kr_stock_code

        config = KISConfig.from_env()
        client = KISOpenAPIClient(config=config, timeout=float(os.getenv("AG_KIS_UNIVERSE_TIMEOUT_SEC", "8")))
    except Exception as exc:
        print(f"  ⚠️ failed to initialize KIS universe client: {exc}")
        return pd.DataFrame(columns=["Code", "Name"])

    parts = []
    for market_label, suffix in (("KOSPI", ".KS"), ("KOSDAQ", ".KQ")):
        try:
            payload = client.volume_rank(market=market_label)
            if payload.get("rt_cd") not in (None, "0"):
                raise RuntimeError(f"{payload.get('msg_cd')}: {payload.get('msg1') or payload.get('msg')}")
            rows = payload.get("output") or payload.get("output2") or []
            if not isinstance(rows, list):
                rows = []
            selected = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                code = normalize_kr_stock_code(row.get("mksc_shrn_iscd") or row.get("stck_shrn_iscd") or "")
                name = str(row.get("hts_kor_isnm") or row.get("prdt_name") or code).strip()
                if not code or not name:
                    continue
                selected.append({"Code": f"{code}{suffix}", "Name": name})
                if limit_per_market > 0 and len(selected) >= limit_per_market:
                    break
            if selected:
                parts.append(pd.DataFrame(selected))
            else:
                print(f"  ⚠️ KIS {market_label} volume_rank returned no usable symbols")
        except Exception as exc:
            print(f"  ⚠️ failed to load KIS {market_label} volume_rank universe: {exc}")
    if not parts:
        return pd.DataFrame(columns=["Code", "Name"])
    return pd.concat(parts).reset_index(drop=True)


def _load_requested_tickers(raw: str) -> pd.DataFrame:
    rows = []
    for item in str(raw or "").split(","):
        text = item.strip()
        if not text:
            continue
        if "=" in text:
            symbol, name = text.split("=", 1)
            symbol = symbol.strip().upper()
            name = name.strip() or symbol
        else:
            symbol = text.upper()
            name = symbol
        if not symbol:
            continue
        rows.append({"Code": symbol, "Name": name})
    return pd.DataFrame(rows, columns=["Code", "Name"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50, help="Tickers per market (default 50)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--tickers",
        default="",
        help="Optional comma-separated ticker override, with optional name as TICKER=NAME.",
    )
    args = parser.parse_args()

    df = _load_requested_tickers(args.tickers) if args.tickers else _load_kr_universe(args.limit)
    tickers_dict: Dict[str, str] = {row["Code"]: row["Name"] for _, row in df.iterrows()}
    print(f"🔬 Live full KR SWING scan: {len(tickers_dict)} tickers (KOSPI + KOSDAQ)")

    backoff = SharedBackoffState()
    market_gate = {
        "gate": "GREEN", "kospi_chg": 0.0, "kosdaq_chg": 0.0,
        "primary_chg": 0.0, "secondary_chg": 0.0,
    }

    results: List[Dict[str, Any]] = []
    start = time.time()

    reject_counter: Counter = Counter()

    def _scan_one(sym: str) -> Dict[str, Any] | None:
        try:
            return scan_symbol_with_retry(
                sym,
                tickers_dict=tickers_dict,
                is_us=False, is_amex=False, is_advanced_engine=False,
                r_status="NEUTRAL",
                intel_data=None, macro_ctx=None,
                market_gate=market_gate,
                rank_adjustment_fn=_noop_rank,
                news_adjustment_fn=_noop_news,
                backoff_state=backoff,
                max_retries=1,
                scan_mode="SWING",
                reject_reason_fn=lambda s, r: reject_counter.update([r]),
                reject_detail_fn=lambda s, m: None,
            )
        except Exception as exc:
            reject_counter.update([f"EXCEPTION:{type(exc).__name__}"])
            return None

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_scan_one, t): t for t in tickers_dict.keys()}
        done = 0
        for fut in as_completed(futures):
            done += 1
            row = fut.result()
            if row:
                results.append(row)
            if done % 10 == 0:
                elapsed = time.time() - start
                print(f"  progress: {done}/{len(futures)} candidates={len(results)} ({elapsed:.0f}s)")

    print(f"\n✅ Scan complete: {len(results)}/{len(tickers_dict)} candidates ({time.time()-start:.0f}s)")
    if reject_counter:
        print("Reject reasons (top 10):")
        for reason, count in reject_counter.most_common(10):
            print(f"  {reason}: {count}")
    if not results:
        return 1

    # Bridge to orchestrator/planner
    print("📝 Running legacy bridge for orchestrator + planner handoffs…")
    run_legacy_agent_bridge(
        results=results, market="KR",
        strategy_version="live-full-scan",
        model_version="phase25",
        code_version="live-full-v1",
        logger=print,
    )

    # Summary
    sigs = Counter(r.get("phase25_signal_direction") for r in results)
    print(f"\nphase25_signal_direction: {dict(sigs)}")
    print("\nTop 10 by alpha_score:")
    for r in sorted(results, key=lambda x: -float(x.get("Antigrav") or 0))[:10]:
        sym = r.get("Ticker") or r.get("ticker")
        alpha = r.get("Antigrav")
        ph25 = r.get("phase25_prob")
        sig = r.get("phase25_signal_direction")
        var = r.get("phase25_variant")
        oos_win = r.get("phase25_oos_win_rate_pct")
        oos_ret = r.get("phase25_oos_avg_return_pct")
        verdict = r.get("Verdict")
        print(f"  {sym}: alpha={alpha} ph25={ph25} var={var} sig={sig} oos_win={oos_win} oos_ret={oos_ret} verdict={verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
