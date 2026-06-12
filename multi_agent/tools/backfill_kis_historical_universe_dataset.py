#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kis_historical_universe_dataset import (
    DEFAULT_STOP_PCT,
    DEFAULT_TARGET_PCT,
    KIS_HISTORICAL_UNIVERSE_VERSION,
    InstrumentRecord,
    build_historical_rows_for_symbol,
    date_range,
    enrich_historical_rows_with_prefilter,
    load_instrument_records,
    market_counts,
    normalize_history_frame,
    required_fetch_start,
)
from modules.kis_openapi import KISConfig, KISOpenAPIClient
from modules.market_data import _fetch_kis_daily_history
from modules.operational_candidate_scoring import DEFAULT_BUY_PREMIUM_PCT
from multi_agent.tools.train_scan_universe_admission_challenger import (
    _dataset_cache_signature,
    prepare_dataset,
    write_prepared_dataset_cache,
)


DEFAULT_INSTRUMENT_MASTER = ROOT / "runtime_state" / "long_term" / "instrument_master" / "KR.json"
DEFAULT_PRICE_CACHE_DIR = ROOT / "runtime_state" / "long_term" / "kis_historical_prices"
DEFAULT_REPORT = ROOT / "runtime_state" / "reports" / "learning" / "kis_historical_universe_dataset.json"
DEFAULT_RAW_PKL = ROOT / "runtime_state" / "reports" / "learning" / "kis_historical_universe_raw.pkl"
DEFAULT_PREPARED_CACHE = ROOT / "runtime_state" / "reports" / "learning" / "kis_historical_universe_prepared.pkl"


def _load_local_env() -> None:
    for env_path in (ROOT / ".env", ROOT / ".env.local"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _date_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return pd.to_datetime(text).date().isoformat()
    except Exception:
        return ""


def _price_cache_path(cache_dir: Path, symbol: str) -> Path:
    safe = str(symbol).replace("/", "_").replace(":", "_")
    return cache_dir / f"{safe}.csv"


def _load_cached_history(path: Path, *, fetch_start: str, required_end: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path, parse_dates=["Date"]).set_index("Date")
    except Exception:
        return pd.DataFrame()
    frame = normalize_history_frame(frame)
    if frame.empty:
        return pd.DataFrame()
    if frame.index.min() > pd.Timestamp(fetch_start) or frame.index.max() < pd.Timestamp(required_end):
        return pd.DataFrame()
    return frame


def _write_cached_history(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = normalize_history_frame(frame)
    if out.empty:
        return
    out.reset_index(names="Date").to_csv(path, index=False)


def _fetch_one(
    record: InstrumentRecord,
    *,
    fetch_start: str,
    fetch_end: str,
    cache_required_end: str,
    min_base_date: str,
    max_base_date: str,
    price_cache_dir: Path,
    refresh_prices: bool,
    timeout: float,
    target_pct: float,
    stop_pct: float,
    buy_premium_pct: float,
    min_prior_bars: int,
) -> Dict[str, Any]:
    cache_path = _price_cache_path(price_cache_dir, record.symbol)
    history = pd.DataFrame()
    cache_hit = False
    if not refresh_prices:
        history = _load_cached_history(cache_path, fetch_start=fetch_start, required_end=cache_required_end)
        cache_hit = not history.empty
    if history.empty:
        config = KISConfig.from_env()
        client = KISOpenAPIClient(config=config, timeout=timeout)
        history = _fetch_kis_daily_history(
            client,
            record.symbol,
            start=datetime.fromisoformat(fetch_start),
            end=datetime.fromisoformat(fetch_end),
            period="D",
        )
        _write_cached_history(cache_path, history)
    rows = build_historical_rows_for_symbol(
        record,
        history,
        min_base_date=min_base_date,
        max_base_date=max_base_date,
        target_pct=target_pct,
        stop_pct=stop_pct,
        buy_premium_pct=buy_premium_pct,
        min_prior_bars=min_prior_bars,
    )
    hist = normalize_history_frame(history)
    return {
        "symbol": record.symbol,
        "market": record.market,
        "cache_hit": cache_hit,
        "history_rows": int(len(hist)),
        "history_min": hist.index.min().date().isoformat() if not hist.empty else None,
        "history_max": hist.index.max().date().isoformat() if not hist.empty else None,
        "built_rows": len(rows),
        "rows": rows,
        "error": "",
    }


def _select_records(records: Sequence[InstrumentRecord], *, markets: Sequence[str], max_tickers: int) -> List[InstrumentRecord]:
    wanted = {str(market).upper() for market in markets}
    selected = [record for record in records if record.market in wanted]
    if max_tickers and max_tickers > 0:
        selected = selected[: int(max_tickers)]
    return selected


def _as_bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    return frame[column].fillna(False).astype(bool)


def _label_summary(frame: pd.DataFrame, *, target_pct: float, stop_pct: float, buy_premium_pct: float) -> Dict[str, Any]:
    if frame.empty:
        return {
            "rows": 0,
            "valid_buy_premium_5d_rows": 0,
            "overall": {},
            "by_market": {},
            "by_market_month": {},
        }

    work = frame.copy()
    if "market" not in work.columns:
        work["market"] = "UNKNOWN"
    work["base_month"] = pd.to_datetime(work.get("base_trade_date"), errors="coerce").dt.strftime("%Y-%m")
    valid = work[
        work.get("buy_premium_max_high_return_5d_pct").notna()
        & work.get("buy_premium_min_low_return_5d_pct").notna()
    ].copy()

    def summarize(group: pd.DataFrame) -> Dict[str, Any]:
        if group.empty:
            return {
                "rows": 0,
                "hit5_dd10_5d_pct": None,
                "hit5_5d_pct": None,
                "hit10_5d_pct": None,
                "stop5_pct": None,
                "avg_close_5d_pct": None,
                "avg_mfe_5d_pct": None,
                "min_low_5d_pct": None,
                "max_high_5d_pct": None,
            }
        n = float(len(group))
        max_high_5d = pd.to_numeric(group.get("buy_premium_max_high_return_5d_pct"), errors="coerce")
        min_low_5d = pd.to_numeric(group.get("buy_premium_min_low_return_5d_pct"), errors="coerce")
        close_5d = pd.to_numeric(group.get("buy_premium_return_5d_pct"), errors="coerce")
        target_before_stop = _as_bool_series(group, "buy_premium_target_before_stop_5d")
        target_hit = _as_bool_series(group, "buy_premium_target_hit_5d")
        hit10 = max_high_5d >= 10.0
        stop_hit = _as_bool_series(group, "buy_premium_stop_hit_5d")
        return {
            "rows": int(len(group)),
            "hit5_dd10_5d_pct": round(float(target_before_stop.sum()) / n * 100.0, 4),
            "hit5_5d_pct": round(float(target_hit.sum()) / n * 100.0, 4),
            "hit10_5d_pct": round(float(hit10.fillna(False).sum()) / n * 100.0, 4),
            "stop5_pct": round(float(stop_hit.sum()) / n * 100.0, 4),
            "avg_close_5d_pct": round(float(close_5d.mean()), 6),
            "avg_mfe_5d_pct": round(float(max_high_5d.mean()), 6),
            "min_low_5d_pct": round(float(min_low_5d.min()), 6),
            "max_high_5d_pct": round(float(max_high_5d.max()), 6),
        }

    by_market = {str(market): summarize(group) for market, group in valid.groupby("market", dropna=False)}
    by_market_month: Dict[str, Dict[str, Any]] = {}
    for (market, month), group in valid.groupby(["market", "base_month"], dropna=False):
        if not month or str(month) == "NaT":
            continue
        by_market_month.setdefault(str(market), {})[str(month)] = summarize(group)

    return {
        "rows": int(len(work)),
        "valid_buy_premium_5d_rows": int(len(valid)),
        "target_pct": float(target_pct),
        "stop_pct": float(stop_pct),
        "buy_premium_pct": float(buy_premium_pct),
        "overall": summarize(valid),
        "by_market": dict(sorted(by_market.items())),
        "by_market_month": {
            market: dict(sorted(months.items())) for market, months in sorted(by_market_month.items())
        },
    }


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    lines = [
        "# KIS Historical Universe Dataset",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- version: `{report.get('version')}`",
        f"- min_base_date: `{report.get('min_base_date')}`",
        f"- max_base_date: `{report.get('max_base_date')}`",
        f"- fetch_start: `{report.get('fetch_start')}`",
        f"- fetch_end: `{report.get('fetch_end')}`",
        f"- cache_required_end: `{report.get('cache_required_end')}`",
        f"- no_dummy_data: `{report.get('no_dummy_data')}`",
        f"- selected_tickers: `{report.get('selected_tickers')}`",
        f"- successful_tickers: `{report.get('successful_tickers')}`",
        f"- failed_tickers: `{report.get('failed_tickers')}`",
        f"- raw_rows: `{report.get('raw_rows')}`",
        f"- prepared_rows: `{report.get('prepared_rows')}`",
        f"- raw_date_range: `{report.get('raw_date_range')}`",
        f"- raw_market_counts: `{report.get('raw_market_counts')}`",
        f"- prepared_market_counts: `{report.get('prepared_market_counts')}`",
        f"- raw_pkl: `{report.get('raw_pkl')}`",
        f"- raw_csv: `{report.get('raw_csv')}`",
        f"- prepared_cache: `{report.get('prepared_cache')}`",
        f"- price_cache_dir: `{report.get('price_cache_dir')}`",
        f"- historical_prefilter_summary: `{report.get('historical_prefilter_summary')}`",
        f"- label_summary: `{report.get('label_summary')}`",
        "",
        "## Failures",
    ]
    for item in report.get("failure_examples") or []:
        lines.append(f"- `{item.get('symbol')}` `{item.get('market')}`: {item.get('error')}")
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _cache_signature(min_base_date: str, max_base_date: str, *, market: str, return_sanity: str) -> Dict[str, Any]:
    filters = {
        "market": market,
        "scan_mode": "SWING",
        "page_size": 1000,
        "min_id": 0,
        "max_id": 0,
        "base_date": "",
        "min_base_date": min_base_date,
        "max_base_date": max_base_date,
        "limit": 0,
        "client_filter": False,
        "max_fetch_chunks": 0,
    }
    return _dataset_cache_signature(filters, return_sanity=return_sanity)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a real KIS daily OHLCV historical universe dataset for KR model learning.")
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--min-base-date", default="2026-01-01")
    parser.add_argument("--max-base-date", default="2026-06-10")
    parser.add_argument("--lookback-days", type=int, default=180)
    parser.add_argument("--forward-days", type=int, default=10)
    parser.add_argument("--max-tickers", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--sleep-sec", type=float, default=0.0)
    parser.add_argument("--kis-call-sleep-sec", type=float, default=0.08)
    parser.add_argument("--kis-max-chunks", type=int, default=6)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--refresh-prices", action="store_true")
    parser.add_argument("--target-pct", type=float, default=DEFAULT_TARGET_PCT)
    parser.add_argument("--stop-pct", type=float, default=DEFAULT_STOP_PCT)
    parser.add_argument("--buy-premium-pct", type=float, default=DEFAULT_BUY_PREMIUM_PCT)
    parser.add_argument("--min-prior-bars", type=int, default=20)
    parser.add_argument("--historical-prefilter-rank-limit", type=int, default=80)
    parser.add_argument("--historical-prefilter-max-candidates", type=int, default=80)
    parser.add_argument("--return-sanity", choices=["kr_price_limit", "off"], default="kr_price_limit")
    parser.add_argument("--instrument-master", default=str(DEFAULT_INSTRUMENT_MASTER))
    parser.add_argument("--price-cache-dir", default=str(DEFAULT_PRICE_CACHE_DIR))
    parser.add_argument("--raw-pkl", default=str(DEFAULT_RAW_PKL))
    parser.add_argument("--raw-csv", default="")
    parser.add_argument("--prepared-cache", default=str(DEFAULT_PREPARED_CACHE))
    parser.add_argument("--output", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    _load_local_env()
    if args.live:
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
    os.environ.setdefault("KIS_MODE", "real")
    os.environ["AG_KIS_DAILY_MAX_CHUNKS"] = str(max(1, int(args.kis_max_chunks or 1)))
    os.environ["KIS_LIVE_CALL_SLEEP_SEC"] = str(max(0.0, float(args.kis_call_sleep_sec or 0.0)))

    min_base_date = _date_text(args.min_base_date)
    max_base_date = _date_text(args.max_base_date)
    if not min_base_date or not max_base_date:
        raise SystemExit("min/max base date are required")
    fetch_start = required_fetch_start(min_base_date, lookback_days=int(args.lookback_days or 0))
    fetch_end = (pd.Timestamp(max_base_date) + pd.Timedelta(days=max(0, int(args.forward_days or 0)))).date().isoformat()
    cache_required_end = min(fetch_end, max_base_date)
    markets = ["KOSPI", "KOSDAQ"] if args.market == "ALL" else [args.market]
    records = load_instrument_records(Path(args.instrument_master), markets=markets)
    selected = _select_records(records, markets=markets, max_tickers=int(args.max_tickers or 0))
    price_cache_dir = Path(args.price_cache_dir)
    rows: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    started = time.perf_counter()

    def submit(record: InstrumentRecord) -> Dict[str, Any]:
        try:
            if args.sleep_sec:
                time.sleep(max(0.0, float(args.sleep_sec)))
            return _fetch_one(
                record,
                fetch_start=fetch_start,
                fetch_end=fetch_end,
                cache_required_end=cache_required_end,
                min_base_date=min_base_date,
                max_base_date=max_base_date,
                price_cache_dir=price_cache_dir,
                refresh_prices=bool(args.refresh_prices),
                timeout=float(args.timeout),
                target_pct=float(args.target_pct),
                stop_pct=float(args.stop_pct),
                buy_premium_pct=float(args.buy_premium_pct),
                min_prior_bars=int(args.min_prior_bars or 0),
            )
        except Exception as exc:
            return {
                "symbol": record.symbol,
                "market": record.market,
                "cache_hit": False,
                "history_rows": 0,
                "built_rows": 0,
                "rows": [],
                "error": str(exc),
            }

    workers = max(1, int(args.workers or 1))
    if workers == 1:
        for idx, record in enumerate(selected, start=1):
            result = submit(record)
            results.append(result)
            rows.extend(result.get("rows") or [])
            if idx % 25 == 0 or idx == len(selected):
                print(f"[INFO] {idx}/{len(selected)} tickers processed rows={len(rows)} failures={sum(1 for item in results if item.get('error'))}", flush=True)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(submit, record): record for record in selected}
            for idx, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results.append(result)
                rows.extend(result.get("rows") or [])
                if idx % 25 == 0 or idx == len(selected):
                    print(f"[INFO] {idx}/{len(selected)} tickers processed rows={len(rows)} failures={sum(1 for item in results if item.get('error'))}", flush=True)

    historical_prefilter_summary = enrich_historical_rows_with_prefilter(
        rows,
        rank_limit=int(args.historical_prefilter_rank_limit or 0),
        max_candidates_per_market=int(args.historical_prefilter_max_candidates or 0),
    )
    raw_df = pd.DataFrame(rows)
    raw_pkl = Path(args.raw_pkl)
    raw_pkl.parent.mkdir(parents=True, exist_ok=True)
    raw_df.to_pickle(raw_pkl)
    raw_csv = Path(args.raw_csv) if str(args.raw_csv or "").strip() else None
    if raw_csv:
        raw_csv.parent.mkdir(parents=True, exist_ok=True)
        raw_for_csv = raw_df.copy()
        if "feature_snapshot" in raw_for_csv.columns:
            raw_for_csv["feature_snapshot"] = raw_for_csv["feature_snapshot"].map(
                lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, Mapping) else value
            )
        raw_for_csv.to_csv(raw_csv, index=False)

    prepared_started = time.perf_counter()
    prepared, sanity = prepare_dataset(raw_df, return_sanity=args.return_sanity)
    prepared_elapsed = round(time.perf_counter() - prepared_started, 3)
    prepared_cache_path = Path(args.prepared_cache)
    cache_info = write_prepared_dataset_cache(
        prepared_cache_path,
        signature=_cache_signature(min_base_date, max_base_date, market=args.market, return_sanity=args.return_sanity),
        data=prepared,
        raw_rows=len(raw_df),
        return_sanity=sanity,
    )
    cache_info["prepare_elapsed_sec"] = prepared_elapsed

    failures = [item for item in results if item.get("error")]
    report = {
        "version": KIS_HISTORICAL_UNIVERSE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "no_dummy_data": True,
        "source": "kis_openapi_daily_bars",
        "instrument_master": str(Path(args.instrument_master)),
        "price_cache_dir": str(price_cache_dir),
        "min_base_date": min_base_date,
        "max_base_date": max_base_date,
        "fetch_start": fetch_start,
        "fetch_end": fetch_end,
        "cache_required_end": cache_required_end,
        "market": args.market,
        "selected_tickers": len(selected),
        "successful_tickers": sum(1 for item in results if not item.get("error") and int(item.get("history_rows") or 0) > 0),
        "failed_tickers": len(failures),
        "empty_or_unusable_tickers": sum(1 for item in results if not item.get("error") and int(item.get("built_rows") or 0) == 0),
        "raw_rows": int(len(raw_df)),
        "prepared_rows": int(len(prepared)),
        "raw_date_range": date_range(rows),
        "raw_market_counts": market_counts(rows),
        "prepared_market_counts": market_counts(prepared.to_dict(orient="records")),
        "return_sanity": sanity,
        "label_summary": _label_summary(
            prepared,
            target_pct=float(args.target_pct),
            stop_pct=float(args.stop_pct),
            buy_premium_pct=float(args.buy_premium_pct),
        ),
        "target_pct": float(args.target_pct),
        "stop_pct": float(args.stop_pct),
        "buy_premium_pct": float(args.buy_premium_pct),
        "min_prior_bars": int(args.min_prior_bars or 0),
        "historical_prefilter_summary": historical_prefilter_summary,
        "raw_pkl": str(raw_pkl),
        "raw_csv": str(raw_csv) if raw_csv else "",
        "prepared_cache": cache_info,
        "cache_signature_training_args": {
            "market": args.market,
            "scan_mode": "SWING",
            "min_base_date": min_base_date,
            "max_base_date": max_base_date,
            "page_size": 1000,
            "max_fetch_chunks": 0,
            "return_sanity": args.return_sanity,
        },
        "failure_examples": [
            {"symbol": item.get("symbol"), "market": item.get("market"), "error": item.get("error")}
            for item in failures[:20]
        ],
        "ticker_summaries": [
            {
                "symbol": item.get("symbol"),
                "market": item.get("market"),
                "cache_hit": item.get("cache_hit"),
                "history_rows": item.get("history_rows"),
                "history_min": item.get("history_min"),
                "history_max": item.get("history_max"),
                "built_rows": item.get("built_rows"),
                "error": item.get("error"),
            }
            for item in results[:200]
        ],
    }
    output = Path(args.output)
    _write_report(output, report)
    print(json.dumps({key: report[key] for key in ["raw_rows", "prepared_rows", "failed_tickers", "raw_date_range", "raw_market_counts", "prepared_cache"]}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["raw_rows"] > 0 and report["prepared_rows"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
