#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_openapi import KISConfig, KISOpenAPIClient, build_kis_adapter_health, normalize_kr_stock_code
from modules.quant_analysis import QuantStrategy


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"
CORE_QUOTE_FIELDS = [
    "last_price",
    "day_change",
    "day_change_pct",
    "session_open",
    "session_high",
    "session_low",
    "volume",
    "value_traded",
    "prev_volume_ratio",
    "market_name",
    "sector_name",
    "status_code",
    "foreigner_net_qty",
    "program_net_qty",
    "market_cap",
    "per",
    "pbr",
    "high_250d",
    "low_250d",
]


def _kst_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        return datetime.now()


def _today_yyyymmdd() -> str:
    return _kst_now().strftime("%Y%m%d")


def _compact_error(exc: Exception) -> Dict[str, str]:
    return {"error_type": type(exc).__name__, "error": str(exc)}


def _row_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _market_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    ok_rows = [row for row in rows if row.get("ok")]
    error_rows = [row for row in rows if not row.get("ok")]
    missing_by_field: Dict[str, int] = {}
    for field in CORE_QUOTE_FIELDS:
        missing_by_field[field] = sum(1 for row in ok_rows if row.get(field) in (None, ""))
    return {
        "universe_count": total,
        "quote_ok_count": len(ok_rows),
        "quote_error_count": len(error_rows),
        "quote_success_rate_pct": round((len(ok_rows) / total * 100.0) if total else 0.0, 3),
        "core_field_missing_count": missing_by_field,
        "failed_tickers_sample": [
            {"ticker": row.get("ticker"), "name": row.get("name"), "error": row.get("error")}
            for row in error_rows[:20]
        ],
    }


def _output_count(payload: Mapping[str, Any]) -> int:
    output2 = payload.get("output2")
    output = payload.get("output")
    if isinstance(output2, list):
        return len(output2)
    if isinstance(output, list):
        return len(output)
    if isinstance(output2, dict):
        return 1
    if isinstance(output, dict):
        return 1
    return 0


def _call_feature(
    name: str,
    func: Callable[[], Mapping[str, Any]],
    *,
    sleep_before_sec: float = 0.0,
) -> Dict[str, Any]:
    if sleep_before_sec > 0:
        time.sleep(sleep_before_sec)
    started = time.monotonic()
    try:
        payload = func()
        return {
            "name": name,
            "ok": True,
            "elapsed_sec": round(time.monotonic() - started, 3),
            "rt_cd": payload.get("rt_cd"),
            "msg_cd": payload.get("msg_cd"),
            "row_count": _output_count(payload),
        }
    except Exception as exc:
        out = {
            "name": name,
            "ok": False,
            "elapsed_sec": round(time.monotonic() - started, 3),
        }
        out.update(_compact_error(exc))
        return out


def _load_universe(markets: Iterable[str], max_per_market: int) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Any]]:
    universe: Dict[str, Dict[str, str]] = {}
    summary: Dict[str, Any] = {}
    for market in markets:
        market_key = str(market).upper()
        started = time.monotonic()
        tickers = QuantStrategy.get_market_tickers(market_key) or {}
        original_count = len(tickers)
        if max_per_market and max_per_market > 0:
            tickers = dict(list(tickers.items())[:max_per_market])
        universe[market_key] = tickers
        summary[market_key] = {
            "original_count": original_count,
            "selected_count": len(tickers),
            "elapsed_sec": round(time.monotonic() - started, 3),
            "first_tickers": list(tickers.keys())[:5],
        }
    return universe, summary


def _parse_requested_tickers(raw: str) -> List[Tuple[Optional[str], str]]:
    requested: List[Tuple[Optional[str], str]] = []
    for part in str(raw or "").split(","):
        text = part.strip()
        if not text:
            continue
        market: Optional[str] = None
        symbol = text
        if ":" in text:
            market_part, symbol = text.split(":", 1)
            market = market_part.strip().upper() or None
        requested.append((market, symbol.strip().upper()))
    return requested


def _market_from_symbol(symbol: str) -> Optional[str]:
    upper = str(symbol or "").upper()
    if upper.endswith(".KS"):
        return "KOSPI"
    if upper.endswith(".KQ"):
        return "KOSDAQ"
    return None


def _filter_universe_for_tickers(
    universe: Mapping[str, Mapping[str, str]],
    requested: Sequence[Tuple[Optional[str], str]],
) -> Tuple[Dict[str, Dict[str, str]], List[Dict[str, str]]]:
    selected: Dict[str, Dict[str, str]] = {market: {} for market in universe}
    missing: List[Dict[str, str]] = []
    code_index: Dict[str, Dict[str, str]] = {
        market: {normalize_kr_stock_code(ticker): ticker for ticker in tickers}
        for market, tickers in universe.items()
    }

    for market_hint, symbol in requested:
        market_candidates = [market_hint] if market_hint else []
        inferred_market = _market_from_symbol(symbol)
        if inferred_market and inferred_market not in market_candidates:
            market_candidates.append(inferred_market)
        if not market_candidates:
            market_candidates = list(universe.keys())

        matched = False
        normalized_code = normalize_kr_stock_code(symbol)
        for market in market_candidates:
            tickers = universe.get(market)
            if not tickers:
                continue
            ticker = symbol if symbol in tickers else code_index.get(market, {}).get(normalized_code)
            if ticker:
                selected.setdefault(market, {})[ticker] = tickers[ticker]
                matched = True
                break
        if not matched:
            missing.append({"market": market_hint or "", "ticker": symbol})

    return selected, missing


def _refresh_universe_summary(
    universe_summary: Dict[str, Any],
    universe: Mapping[str, Mapping[str, str]],
) -> Dict[str, Any]:
    for market, tickers in universe.items():
        summary = universe_summary.setdefault(market, {})
        summary["selected_count"] = len(tickers)
        summary["first_tickers"] = list(tickers.keys())[:5]
    return universe_summary


def _quote_universe(
    client: KISOpenAPIClient,
    universe: Mapping[str, Mapping[str, str]],
    *,
    sleep_sec: float,
    retry_count: int,
    progress_every: int,
) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for market, tickers in universe.items():
        rows: List[Dict[str, Any]] = []
        items = list(tickers.items())
        for idx, (ticker, name) in enumerate(items, start=1):
            row: Dict[str, Any] = {"market": market, "ticker": ticker, "name": name}
            last_error: Optional[Exception] = None
            for attempt in range(retry_count + 1):
                try:
                    snapshot = client.quote_snapshot(ticker)
                    row.update(
                        {
                            "ok": snapshot.get("source_status") == "ok",
                            "source_status": snapshot.get("source_status"),
                        }
                    )
                    for field in CORE_QUOTE_FIELDS:
                        row[field] = _row_value(snapshot.get(field))
                    warnings = snapshot.get("warnings") or []
                    row["warnings"] = "|".join(map(str, warnings)) if warnings else ""
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt < retry_count:
                        time.sleep(max(0.2, sleep_sec * 2))
                finally:
                    if sleep_sec > 0:
                        time.sleep(sleep_sec)
            else:
                row.update({"ok": False, "source_status": "error"})
                if last_error:
                    row.update(_compact_error(last_error))
            rows.append(row)
            if progress_every > 0 and (idx % progress_every == 0 or idx == len(items)):
                print(f"[kis-universe] {market} quotes {idx}/{len(items)}", file=sys.stderr, flush=True)
        out[market] = rows
    return out


def _verify_feature_endpoints(
    client: KISOpenAPIClient,
    universe: Mapping[str, Mapping[str, str]],
    *,
    samples_per_market: int,
    sleep_sec: float,
) -> List[Dict[str, Any]]:
    today = _today_yyyymmdd()
    checks: List[Dict[str, Any]] = []
    for market, tickers in universe.items():
        samples = list(tickers.keys())[: max(0, samples_per_market)]
        for ticker in samples:
            checks.append(
                _call_feature(
                    f"{market}:{ticker}:daily_bars",
                    lambda ticker=ticker: client.daily_bars(ticker, start_date=today, end_date=today),
                    sleep_before_sec=sleep_sec,
                )
            )
            checks.append(
                _call_feature(
                    f"{market}:{ticker}:today_minute_bars",
                    lambda ticker=ticker: client.today_minute_bars(ticker, input_hour="153000"),
                    sleep_before_sec=sleep_sec,
                )
            )
            checks.append(
                _call_feature(
                    f"{market}:{ticker}:investor_flow_snapshot",
                    lambda ticker=ticker: client.investor_flow_snapshot(ticker, trade_date=today),
                    sleep_before_sec=sleep_sec,
                )
            )

        checks.append(
            _call_feature(
                f"{market}:volume_rank",
                lambda market=market: client.volume_rank(market=market),
                sleep_before_sec=sleep_sec,
            )
        )
        checks.append(
            _call_feature(
                f"{market}:fluctuation_rank",
                lambda market=market: client.fluctuation_rank(market=market),
                sleep_before_sec=sleep_sec,
            )
        )
        checks.append(
            _call_feature(
                f"{market}:volume_power_rank",
                lambda market=market: client.volume_power_rank(market=market),
                sleep_before_sec=sleep_sec,
            )
        )
        checks.append(
            _call_feature(
                f"{market}:foreign_institution_total",
                lambda market=market: client.foreign_institution_total(market=market),
                sleep_before_sec=sleep_sec,
            )
        )
        checks.append(
            _call_feature(
                f"{market}:vi_status",
                lambda market=market: client.vi_status(market=market, trade_date=today),
                sleep_before_sec=sleep_sec,
            )
        )

    checks.append(
        _call_feature("KOSPI:industry_price", lambda: client.industry_price(index_code="0001"), sleep_before_sec=sleep_sec)
    )
    checks.append(
        _call_feature("KOSDAQ:industry_price", lambda: client.industry_price(index_code="1001"), sleep_before_sec=sleep_sec)
    )
    checks.append(_call_feature("ALL:news_titles", lambda: client.news_titles(trade_date=today), sleep_before_sec=sleep_sec))
    return checks


def _write_reports(
    report: Mapping[str, Any],
    quote_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    write_latest: bool = True,
) -> Dict[str, str]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = str(report["run_id"])
    json_path = REPORT_DIR / f"kis_kr_universe_readiness_{stamp}.json"
    latest_json_path = REPORT_DIR / "kis_kr_universe_readiness_latest.json"
    csv_path = REPORT_DIR / f"kis_kr_universe_quote_rows_{stamp}.csv"
    latest_csv_path = REPORT_DIR / "kis_kr_universe_quote_rows_latest.csv"

    json_text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    if write_latest:
        latest_json_path.write_text(json_text + "\n", encoding="utf-8")

    rows = [row for market_rows in quote_rows.values() for row in market_rows]
    fieldnames = [
        "market",
        "ticker",
        "name",
        "ok",
        "source_status",
        *CORE_QUOTE_FIELDS,
        "warnings",
        "error_type",
        "error",
    ]
    csv_paths = [csv_path]
    if write_latest:
        csv_paths.append(latest_csv_path)
    for path in csv_paths:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    artifacts = {
        "json": str(json_path),
        "quote_csv": str(csv_path),
    }
    if write_latest:
        artifacts["json_latest"] = str(latest_json_path)
        artifacts["quote_csv_latest"] = str(latest_csv_path)
    return artifacts


def run(args: argparse.Namespace) -> Dict[str, Any]:
    load_dotenv()
    load_dotenv(PROJECT_ROOT / ".env.local")
    markets = [part.strip().upper() for part in args.markets.split(",") if part.strip()]
    config = KISConfig.from_env()
    if args.mode:
        config.mode = args.mode
    if args.allow_live_network:
        config.live_network_allowed = True
    client = KISOpenAPIClient(config=config, timeout=args.timeout)

    requested_tickers = _parse_requested_tickers(args.tickers)
    universe, universe_summary = _load_universe(markets, 0 if requested_tickers else args.max_per_market)
    missing_requested_tickers: List[Dict[str, str]] = []
    if requested_tickers:
        universe, missing_requested_tickers = _filter_universe_for_tickers(universe, requested_tickers)
        universe_summary = _refresh_universe_summary(universe_summary, universe)
    run_id = _kst_now().strftime("%Y%m%d_%H%M%S")
    report: Dict[str, Any] = {
        "run_id": run_id,
        "tool": "verify_kis_kr_universe_readiness",
        "dry_run": not bool(args.allow_live_network),
        "mode": config.mode,
        "markets": markets,
        "quote_sleep_sec": args.quote_sleep_sec,
        "feature_sleep_sec": args.feature_sleep_sec,
        "live_network_enabled_for_run": bool(args.allow_live_network),
        "max_per_market": args.max_per_market,
        "samples_per_market": args.samples_per_market,
        "requested_tickers": [
            {"market": market or "", "ticker": ticker} for market, ticker in requested_tickers
        ],
        "missing_requested_tickers": missing_requested_tickers,
        "write_latest": not bool(args.no_latest),
        "health": build_kis_adapter_health(config=config),
        "universe": universe_summary,
    }

    if not args.allow_live_network:
        report["quote_summary"] = {}
        report["feature_checks"] = []
        report["note"] = "Dry run only. Pass --allow-live-network to call KIS read-only endpoints."
        return report

    client.get_access_token(force=True)
    quote_rows = _quote_universe(
        client,
        universe,
        sleep_sec=max(0.0, args.quote_sleep_sec),
        retry_count=max(0, args.retry_count),
        progress_every=max(0, args.progress_every),
    )
    report["quote_summary"] = {market: _market_summary(rows) for market, rows in quote_rows.items()}
    report["feature_checks"] = _verify_feature_endpoints(
        client,
        universe,
        samples_per_market=args.samples_per_market,
        sleep_sec=max(0.0, args.feature_sleep_sec),
    )
    report["artifacts"] = _write_reports(report, quote_rows, write_latest=not bool(args.no_latest))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only KIS full KR universe readiness verification.")
    parser.add_argument("--allow-live-network", action="store_true", help="Actually call KIS read-only endpoints.")
    parser.add_argument("--markets", default="KOSPI,KOSDAQ")
    parser.add_argument("--mode", choices=["paper", "real"], default="")
    parser.add_argument("--max-per-market", type=int, default=0, help="0 means full selected universe.")
    parser.add_argument("--samples-per-market", type=int, default=3)
    parser.add_argument("--quote-sleep-sec", type=float, default=0.12)
    parser.add_argument("--feature-sleep-sec", type=float, default=0.15)
    parser.add_argument("--retry-count", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument(
        "--tickers",
        default="",
        help="Optional comma-separated retry subset, with optional market prefix such as KOSPI:005930.KS.",
    )
    parser.add_argument("--no-latest", action="store_true", help="Write timestamped artifacts without updating latest files.")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, **_compact_error(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
