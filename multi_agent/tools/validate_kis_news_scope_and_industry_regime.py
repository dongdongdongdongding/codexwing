#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_industry_regime import build_kis_industry_regime_overlay
from modules.kis_operational_adapter import normalize_kis_news_titles, normalize_kis_stock_info
from modules.kis_openapi import KISConfig, KISOpenAPIClient, normalize_kr_stock_code


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"
DEFAULT_SYMBOLS = ("005930", "000660", "091990", "196170")
DEFAULT_INDUSTRY_CODES = (("0001", "KOSPI"), ("1001", "KOSDAQ"))


def _kst_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        return datetime.now()


def _today_yyyymmdd() -> str:
    return _kst_now().strftime("%Y%m%d")


def _parse_symbols(value: str) -> List[str]:
    symbols = []
    for part in str(value or "").replace(";", ",").split(","):
        code = normalize_kr_stock_code(part.strip())
        if code and code not in symbols:
            symbols.append(code)
    return symbols


def _parse_industry_codes(value: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for part in str(value or "").replace(";", ",").split(","):
        text = part.strip()
        if not text:
            continue
        if ":" in text:
            code, name = text.split(":", 1)
        else:
            code, name = text, ""
        code = code.strip()
        name = name.strip()
        if code:
            out.append((code, name))
    return out


def _compact_error(exc: Exception) -> Dict[str, str]:
    return {"error_type": type(exc).__name__, "error": str(exc)}


def _sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def _news_scope_rows(
    client: Any,
    *,
    symbols: Sequence[str],
    trade_date: str,
    sleep_sec: float,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for symbol in symbols:
        stock = {}
        try:
            _sleep(sleep_sec)
            stock = normalize_kis_stock_info(symbol, client.stock_info(symbol))
        except Exception as exc:
            stock = {"checked": False, "source_status": "error", "error": _compact_error(exc)}
        stock_name = str(stock.get("product_name") or "")
        try:
            _sleep(sleep_sec)
            news = normalize_kis_news_titles(
                client.news_titles(symbol=symbol, trade_date=trade_date),
                symbol=symbol,
                stock_name=stock_name,
            )
            scope = news.get("source_scope_metadata") if isinstance(news.get("source_scope_metadata"), Mapping) else {}
            rows.append(
                {
                    "ticker": symbol,
                    "stock_name": stock_name or None,
                    "stock_info": stock,
                    "news": news,
                    "source_scope": scope.get("source_scope"),
                    "source_scope_confidence": scope.get("source_scope_confidence"),
                    "promotion_blocked": bool(scope.get("promotion_blocked")),
                    "promotion_block_reason": scope.get("promotion_block_reason"),
                    "warnings": scope.get("warnings") or [],
                    "ok": True,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "ticker": symbol,
                    "stock_name": stock_name or None,
                    "stock_info": stock,
                    "ok": False,
                    "error": _compact_error(exc),
                    "promotion_blocked": True,
                    "promotion_block_reason": "KIS_NEWS_SCOPE_VALIDATION_FAILED",
                    "warnings": ["kis_news_scope_validation_failed"],
                }
            )
    return rows


def _industry_regime_rows(
    client: Any,
    *,
    industry_codes: Sequence[Tuple[str, str]],
    start_date: str,
    end_date: str,
    sleep_sec: float,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index_code, name in industry_codes:
        try:
            _sleep(sleep_sec)
            price_payload = client.industry_price(index_code=index_code)
            _sleep(sleep_sec)
            daily_payload = client.industry_daily_bars(
                index_code=index_code,
                start_date=start_date,
                end_date=end_date,
            )
            overlay = build_kis_industry_regime_overlay(
                index_code=index_code,
                industry_name=name,
                market=name,
                price_payload=price_payload,
                daily_bars_payload=daily_payload,
            )
            rows.append({"index_code": index_code, "name": name, "ok": bool(overlay.get("source_ok")), "overlay": overlay})
        except Exception as exc:
            rows.append(
                {
                    "index_code": index_code,
                    "name": name,
                    "ok": False,
                    "error": _compact_error(exc),
                    "overlay": {
                        "index_code": index_code,
                        "industry_name": name,
                        "checked": False,
                        "source_ok": False,
                        "warnings": ["kis_industry_regime_validation_failed"],
                        "no_dummy_data": True,
                    },
                }
            )
    return rows


def build_validation_report(
    client: Any,
    *,
    symbols: Sequence[str],
    trade_date: str,
    industry_codes: Sequence[Tuple[str, str]],
    industry_start_date: str,
    industry_end_date: str,
    sleep_sec: float = 0.0,
    live_network_enabled_for_run: bool = False,
    mode: str = "",
) -> Dict[str, Any]:
    news_rows = _news_scope_rows(client, symbols=symbols, trade_date=trade_date, sleep_sec=sleep_sec)
    industry_rows = _industry_regime_rows(
        client,
        industry_codes=industry_codes,
        start_date=industry_start_date,
        end_date=industry_end_date,
        sleep_sec=sleep_sec,
    )
    scope_counts: Dict[str, int] = {}
    for row in news_rows:
        scope = str(row.get("source_scope") or ("error" if not row.get("ok") else "unknown"))
        scope_counts[scope] = scope_counts.get(scope, 0) + 1
    blocked = [row for row in news_rows if row.get("promotion_blocked")]
    industry_ready = [row for row in industry_rows if row.get("ok")]
    verdict = "ready_with_symbol_specific_news"
    if blocked:
        verdict = "promotion_block_required_for_ambiguous_news"
    if not news_rows or all(not row.get("ok") for row in news_rows):
        verdict = "news_scope_validation_failed"
    return {
        "tool": "validate_kis_news_scope_and_industry_regime",
        "generated_at": _kst_now().isoformat(),
        "mode": mode,
        "live_network_enabled_for_run": bool(live_network_enabled_for_run),
        "trade_date": trade_date,
        "industry_start_date": industry_start_date,
        "industry_end_date": industry_end_date,
        "no_dummy_data": True,
        "verdict": verdict,
        "summary": {
            "symbols_checked": len(news_rows),
            "news_ok_count": sum(1 for row in news_rows if row.get("ok")),
            "news_source_scope_counts": scope_counts,
            "news_promotion_blocked_count": len(blocked),
            "industry_indices_checked": len(industry_rows),
            "industry_overlay_ready_count": len(industry_ready),
            "industry_overlay_missing_mapping_note": (
                "KIS industry_price/industry_daily_bars validate market/industry-index regime, "
                "but stock_info standard_industry_code is not an official one-to-one index_code mapping."
            ),
        },
        "news_scope_rows": news_rows,
        "industry_regime_rows": industry_rows,
    }


def _write_report(report: Mapping[str, Any], *, output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    lines = [
        "# KIS News Scope and Industry Regime Validation",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- verdict: `{report.get('verdict')}`",
        f"- no_dummy_data: `{report.get('no_dummy_data')}`",
        f"- live_network_enabled_for_run: `{report.get('live_network_enabled_for_run')}`",
        f"- symbols_checked: `{summary.get('symbols_checked')}`",
        f"- news_scope_counts: `{summary.get('news_source_scope_counts')}`",
        f"- news_promotion_blocked_count: `{summary.get('news_promotion_blocked_count')}`",
        f"- industry_overlay_ready_count: `{summary.get('industry_overlay_ready_count')}/{summary.get('industry_indices_checked')}`",
        f"- mapping_note: {summary.get('industry_overlay_missing_mapping_note')}",
    ]
    lines.extend(["", "## News Scope Rows", ""])
    for row in report.get("news_scope_rows") or []:
        if not isinstance(row, Mapping):
            continue
        news = row.get("news") if isinstance(row.get("news"), Mapping) else {}
        lines.append(
            "- "
            f"{row.get('ticker')} {row.get('stock_name') or ''}: "
            f"scope=`{row.get('source_scope') or 'error'}`, "
            f"confidence=`{row.get('source_scope_confidence')}`, "
            f"news_count=`{news.get('news_count')}`, "
            f"blocked=`{row.get('promotion_blocked')}`, "
            f"reason=`{row.get('promotion_block_reason')}`"
        )
    lines.extend(["", "## Industry Regime Rows", ""])
    for row in report.get("industry_regime_rows") or []:
        if not isinstance(row, Mapping):
            continue
        overlay = row.get("overlay") if isinstance(row.get("overlay"), Mapping) else {}
        lines.append(
            "- "
            f"{row.get('index_code')} {row.get('name') or ''}: "
            f"trend=`{overlay.get('trend')}`, "
            f"score=`{overlay.get('regime_score')}`, "
            f"change_pct=`{overlay.get('change_pct')}`, "
            f"return_5d_pct=`{overlay.get('return_5d_pct')}`, "
            f"return_20d_pct=`{overlay.get('return_20d_pct')}`, "
            f"bar_count=`{overlay.get('bar_count')}`, "
            f"source_ok=`{overlay.get('source_ok')}`"
        )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--trade-date", default=_today_yyyymmdd())
    parser.add_argument("--industry-codes", default=",".join(f"{code}:{name}" for code, name in DEFAULT_INDUSTRY_CODES))
    parser.add_argument("--industry-lookback-days", type=int, default=45)
    parser.add_argument("--mode", default=os.getenv("KIS_MODE", "paper"))
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--sleep-sec", type=float, default=float(os.getenv("KIS_LIVE_CALL_SLEEP_SEC", "0.12") or "0.12"))
    parser.add_argument("--allow-live-network", action="store_true")
    parser.add_argument("--output-json", default=str(REPORT_DIR / "kis_news_scope_industry_regime_validation.json"))
    parser.add_argument("--output-md", default=str(REPORT_DIR / "kis_news_scope_industry_regime_validation.md"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    load_dotenv()
    load_dotenv(PROJECT_ROOT / ".env.local")
    config = KISConfig.from_env()
    if args.mode:
        config = replace(config, mode=str(args.mode).lower())
    if args.allow_live_network:
        config = replace(config, live_network_allowed=True)
    symbols = _parse_symbols(args.symbols)
    industry_codes = _parse_industry_codes(args.industry_codes)
    end_dt = datetime.strptime(str(args.trade_date), "%Y%m%d")
    start_dt = end_dt - timedelta(days=max(1, int(args.industry_lookback_days)))
    client = KISOpenAPIClient(config=config, timeout=float(args.timeout))
    report = build_validation_report(
        client,
        symbols=symbols,
        trade_date=str(args.trade_date),
        industry_codes=industry_codes,
        industry_start_date=start_dt.strftime("%Y%m%d"),
        industry_end_date=end_dt.strftime("%Y%m%d"),
        sleep_sec=max(0.0, float(args.sleep_sec)),
        live_network_enabled_for_run=bool(args.allow_live_network),
        mode=config.mode,
    )
    _write_report(report, output_json=Path(args.output_json), output_md=Path(args.output_md))
    print(json.dumps({"verdict": report.get("verdict"), "summary": report.get("summary")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
