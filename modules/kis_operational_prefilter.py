from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from modules.kis_openapi import normalize_kr_stock_code
from modules.kis_operational_adapter import (
    normalize_kis_flow_for_whale_contract,
    normalize_kis_quote_for_operational_fields,
)


KIS_OPERATIONAL_PREFILTER_VERSION = "kis_operational_prefilter_v1"
BLOCKED_STATUS_WARNINGS = {
    "management_stock",
    "investment_risk",
    "investment_warning",
    "investment_caution",
    "trading_halt",
    "short_term_overheated",
}


@dataclass(frozen=True)
class KISOperationalPrefilterConfig:
    markets: Sequence[str] = ("KOSPI", "KOSDAQ")
    max_candidates_per_market: int = 80
    rank_limit_per_source: int = 80
    quote_limit_per_market: int = 0
    flow_limit_per_market: int = 0
    include_vi: bool = True
    fetch_flow: bool = False
    sleep_sec: float = 0.12
    trade_date: str = ""
    exclude_status_warnings: bool = True
    require_quote_activity: bool = True


def _now_iso() -> str:
    return datetime.now().isoformat()


def _market_key(market: str) -> str:
    key = str(market or "").strip().upper()
    if key in {"KOSPI", "KS"}:
        return "KOSPI"
    if key in {"KOSDAQ", "KQ"}:
        return "KOSDAQ"
    return key or "KOSPI"


def _market_suffix(market: str) -> str:
    return ".KQ" if _market_key(market) == "KOSDAQ" else ".KS"


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        number = float(text)
        return number if number == number else None
    except Exception:
        return None


def _to_int(value: Any) -> Optional[int]:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)


def _first_present(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _output_rows(payload: Mapping[str, Any] | None) -> List[Dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    for key in ("output2", "output", "Output", "output1"):
        value = payload.get(key)
        if isinstance(value, list):
            return [dict(row) for row in value if isinstance(row, Mapping)]
        if isinstance(value, Mapping):
            return [dict(value)]
    return []


def _rank_value(row: Mapping[str, Any], fallback: int) -> int:
    rank = _to_int(_first_present(row, "data_rank", "rank", "rn", "seq", "순위"))
    return int(rank) if rank is not None and rank > 0 else int(fallback)


def _row_code(row: Mapping[str, Any]) -> str:
    return normalize_kr_stock_code(
        str(
            _first_present(
                row,
                "mksc_shrn_iscd",
                "stck_shrn_iscd",
                "isu_cd",
                "pdno",
                "ticker",
                "iscd",
            )
            or ""
        )
    )


def _is_common_stock_code(code: str) -> bool:
    text = str(code or "").strip()
    return bool(text.isdigit() and len(text) == 6)


def _row_name(row: Mapping[str, Any], code: str) -> str:
    return str(_first_present(row, "hts_kor_isnm", "prdt_name", "name", "isu_nm") or code).strip()


def _rank_points(rank: Optional[int], *, weight: float) -> float:
    if rank is None or rank <= 0:
        return 0.0
    return max(0.0, 110.0 - float(rank)) * float(weight)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _quote_score_components(quote: Mapping[str, Any]) -> Dict[str, float]:
    components: Dict[str, float] = {}
    value_traded = _to_float(quote.get("value_traded"))
    if value_traded is not None and value_traded > 0:
        components["value_traded"] = _clamp(math.log10(max(value_traded, 1.0) / 100_000_000.0) * 8.0, 0.0, 40.0)

    prev_volume_ratio = _to_float(quote.get("prev_volume_ratio") or quote.get("volume_ratio"))
    if prev_volume_ratio is not None and prev_volume_ratio > 0:
        components["prev_volume_ratio"] = _clamp(prev_volume_ratio / 10.0, 0.0, 25.0)

    day_change_pct = _to_float(quote.get("day_change_pct"))
    if day_change_pct is not None:
        components["day_change_pct"] = _clamp(day_change_pct * 2.0, -18.0, 28.0)

    market_cap = _to_float(quote.get("market_cap"))
    if market_cap is not None and market_cap > 0:
        components["market_cap"] = _clamp(math.log10(max(market_cap, 1.0)) - 4.0, 0.0, 16.0)

    status_warning = str(quote.get("status_warning") or "").strip()
    if status_warning:
        components["status_warning_penalty"] = -60.0
    return components


def _flow_score_components(flow: Mapping[str, Any]) -> Dict[str, float]:
    whale_score = _to_float(flow.get("whale_score"))
    if whale_score is None:
        return {}
    return {"whale_score": _clamp((whale_score - 50.0) * 0.45, -25.0, 25.0)}


def _has_quote_activity(candidate: Mapping[str, Any]) -> bool:
    volume = _to_float(candidate.get("volume"))
    value_traded = _to_float(candidate.get("value_traded"))
    if volume is not None and volume > 0:
        return True
    if value_traded is not None and value_traded > 0:
        return True
    quote = candidate.get("quote") if isinstance(candidate.get("quote"), Mapping) else {}
    quote_volume = _to_float(quote.get("volume"))
    quote_value = _to_float(quote.get("value_traded"))
    return bool((quote_volume is not None and quote_volume > 0) or (quote_value is not None and quote_value > 0))


def _candidate_score(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    ranks = candidate.get("rank") if isinstance(candidate.get("rank"), Mapping) else {}
    components = {
        "volume_rank": _rank_points(_to_int(ranks.get("volume_rank")), weight=1.0),
        "fluctuation_rank": _rank_points(_to_int(ranks.get("fluctuation_rank")), weight=0.75),
        "volume_power_rank": _rank_points(_to_int(ranks.get("volume_power_rank")), weight=0.85),
    }
    if candidate.get("vi_triggered"):
        components["vi_triggered"] = 8.0
    quote = candidate.get("quote") if isinstance(candidate.get("quote"), Mapping) else {}
    components.update(_quote_score_components(quote))
    flow = candidate.get("flow") if isinstance(candidate.get("flow"), Mapping) else {}
    components.update(_flow_score_components(flow))
    score = round(sum(float(value) for value in components.values()), 4)
    return {"selection_score": score, "score_components": components}


def _merge_rank_row(
    candidates: MutableMapping[str, Dict[str, Any]],
    *,
    market: str,
    source: str,
    row: Mapping[str, Any],
    fallback_rank: int,
) -> None:
    code = _row_code(row)
    if not _is_common_stock_code(code):
        return
    ticker = f"{code}{_market_suffix(market)}"
    item = candidates.setdefault(
        ticker,
        {
            "market": _market_key(market),
            "ticker": ticker,
            "code": code,
            "name": _row_name(row, code),
            "sources": [],
            "rank": {},
            "rank_raw": {},
            "feature_origin": "kis_openapi_prefilter",
            "is_dummy_data": False,
        },
    )
    if source not in item["sources"]:
        item["sources"].append(source)
    rank = _rank_value(row, fallback_rank)
    item["rank"][source] = rank
    item["rank_raw"][source] = dict(row)
    if not item.get("name") or item.get("name") == item.get("code"):
        item["name"] = _row_name(row, code)


def _merge_vi_rows(
    candidates: MutableMapping[str, Dict[str, Any]],
    *,
    market: str,
    payload: Mapping[str, Any] | None,
) -> int:
    rows = _output_rows(payload)
    count = 0
    for row in rows:
        code = _row_code(row)
        if not _is_common_stock_code(code):
            continue
        ticker = f"{code}{_market_suffix(market)}"
        item = candidates.setdefault(
            ticker,
            {
                "market": _market_key(market),
                "ticker": ticker,
                "code": code,
                "name": _row_name(row, code),
                "sources": [],
                "rank": {},
                "rank_raw": {},
                "feature_origin": "kis_openapi_prefilter",
                "is_dummy_data": False,
            },
        )
        if "vi_status" not in item["sources"]:
            item["sources"].append("vi_status")
        item["vi_triggered"] = True
        item["vi_raw"] = dict(row)
        count += 1
    return count


def _call_endpoint(name: str, fn: Callable[[], Mapping[str, Any]]) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        payload = fn()
        return {
            "name": name,
            "ok": True,
            "elapsed_sec": round(time.monotonic() - started, 3),
            "payload": dict(payload) if isinstance(payload, Mapping) else {},
            "row_count": len(_output_rows(payload if isinstance(payload, Mapping) else {})),
            "rt_cd": payload.get("rt_cd") if isinstance(payload, Mapping) else None,
            "msg_cd": payload.get("msg_cd") if isinstance(payload, Mapping) else None,
        }
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "elapsed_sec": round(time.monotonic() - started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "payload": {},
            "row_count": 0,
        }


def _sleep_if_needed(seconds: float) -> None:
    if seconds > 0:
        time.sleep(float(seconds))


def _quote_candidate(client: Any, candidate: MutableMapping[str, Any], *, sleep_sec: float) -> None:
    _sleep_if_needed(sleep_sec)
    try:
        quote = client.quote_snapshot(str(candidate.get("ticker") or candidate.get("code") or ""))
        normalized = normalize_kis_quote_for_operational_fields(quote)
        candidate["quote"] = normalized
        candidate["quote_ok"] = normalized.get("source_status") == "ok" and normalized.get("current_price") is not None
        for key in (
            "current_price",
            "day_change_pct",
            "value_traded",
            "volume",
            "prev_volume_ratio",
            "market_cap",
            "per",
            "pbr",
            "status_warning",
        ):
            if normalized.get(key) is not None:
                candidate[key] = normalized.get(key)
    except Exception as exc:
        candidate["quote_ok"] = False
        candidate.setdefault("warnings", []).append(f"quote_snapshot_failed:{type(exc).__name__}:{exc}")


def _flow_candidate(client: Any, candidate: MutableMapping[str, Any], *, trade_date: str, sleep_sec: float) -> None:
    _sleep_if_needed(sleep_sec)
    try:
        flow = client.investor_flow_snapshot(str(candidate.get("ticker") or candidate.get("code") or ""), trade_date=trade_date)
        normalized = normalize_kis_flow_for_whale_contract(flow)
        candidate["flow"] = normalized
        candidate["flow_ok"] = bool(normalized.get("valid"))
        if normalized.get("whale_score") is not None:
            candidate["whale_score"] = normalized.get("whale_score")
    except Exception as exc:
        candidate["flow_ok"] = False
        candidate.setdefault("warnings", []).append(f"investor_flow_failed:{type(exc).__name__}:{exc}")


def _trade_date(value: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    return datetime.now().strftime("%Y%m%d")


def build_kis_operational_prefilter(client: Any, config: KISOperationalPrefilterConfig) -> Dict[str, Any]:
    markets = [_market_key(market) for market in config.markets if str(market or "").strip()]
    report: Dict[str, Any] = {
        "tool": "kis_operational_prefilter",
        "contract_version": KIS_OPERATIONAL_PREFILTER_VERSION,
        "generated_at": _now_iso(),
        "kis_only": True,
        "config": {
            "markets": markets,
            "max_candidates_per_market": int(config.max_candidates_per_market),
            "rank_limit_per_source": int(config.rank_limit_per_source),
            "quote_limit_per_market": int(config.quote_limit_per_market),
            "flow_limit_per_market": int(config.flow_limit_per_market),
            "include_vi": bool(config.include_vi),
            "fetch_flow": bool(config.fetch_flow),
            "sleep_sec": float(config.sleep_sec),
            "trade_date": _trade_date(config.trade_date),
            "exclude_status_warnings": bool(config.exclude_status_warnings),
            "require_quote_activity": bool(config.require_quote_activity),
        },
        "markets": {},
        "warnings": [],
    }

    for market in markets:
        endpoint_results = [
            _call_endpoint(f"{market}:volume_rank", lambda market=market: client.volume_rank(market=market)),
            _call_endpoint(f"{market}:fluctuation_rank", lambda market=market: client.fluctuation_rank(market=market)),
            _call_endpoint(f"{market}:volume_power_rank", lambda market=market: client.volume_power_rank(market=market)),
        ]
        if config.include_vi:
            endpoint_results.append(
                _call_endpoint(
                    f"{market}:vi_status",
                    lambda market=market: client.vi_status(market=market, trade_date=_trade_date(config.trade_date)),
                )
            )

        candidates: Dict[str, Dict[str, Any]] = {}
        source_map = {
            "volume_rank": endpoint_results[0],
            "fluctuation_rank": endpoint_results[1],
            "volume_power_rank": endpoint_results[2],
        }
        rank_limit = max(1, int(config.rank_limit_per_source))
        for source, result in source_map.items():
            for idx, row in enumerate(_output_rows(result.get("payload")), start=1):
                if idx > rank_limit:
                    break
                _merge_rank_row(candidates, market=market, source=source, row=row, fallback_rank=idx)

        vi_count = 0
        if config.include_vi and len(endpoint_results) > 3:
            vi_count = _merge_vi_rows(candidates, market=market, payload=endpoint_results[3].get("payload"))

        seed_rows = []
        for item in candidates.values():
            item.update(_candidate_score(item))
            seed_rows.append(item)
        seed_rows = sorted(seed_rows, key=lambda row: float(row.get("selection_score") or 0.0), reverse=True)

        max_candidates = max(1, int(config.max_candidates_per_market))
        quote_limit = int(config.quote_limit_per_market)
        if quote_limit <= 0:
            quote_limit = max_candidates * 2
        quote_targets = seed_rows[: max(max_candidates, quote_limit)]
        for item in quote_targets:
            _quote_candidate(client, item, sleep_sec=max(0.0, float(config.sleep_sec)))

        if config.fetch_flow:
            flow_limit = int(config.flow_limit_per_market)
            if flow_limit <= 0:
                flow_limit = max_candidates
            for item in quote_targets[:flow_limit]:
                _flow_candidate(
                    client,
                    item,
                    trade_date=_trade_date(config.trade_date),
                    sleep_sec=max(0.0, float(config.sleep_sec)),
                )

        selected_pool = []
        rejected = []
        for item in seed_rows:
            item.update(_candidate_score(item))
            status_warning = str(item.get("status_warning") or "").strip()
            if config.exclude_status_warnings and status_warning in BLOCKED_STATUS_WARNINGS:
                rejected.append({**item, "reject_reason": f"status_warning:{status_warning}"})
                continue
            if config.require_quote_activity and not item.get("quote_ok"):
                rejected.append({**item, "reject_reason": "quote_snapshot_missing"})
                continue
            if config.require_quote_activity and not _has_quote_activity(item):
                rejected.append({**item, "reject_reason": "quote_activity_missing"})
                continue
            selected_pool.append(item)
        selected = sorted(selected_pool, key=lambda row: float(row.get("selection_score") or 0.0), reverse=True)[
            :max_candidates
        ]
        market_payload = {
            "market": market,
            "endpoint_summary": [
                {key: value for key, value in result.items() if key != "payload"} for result in endpoint_results
            ],
            "seed_count": len(seed_rows),
            "vi_seed_count": vi_count,
            "quote_fetch_count": len(quote_targets),
            "flow_fetch_count": sum(1 for row in quote_targets if row.get("flow") is not None),
            "selected_count": len(selected),
            "rejected_count": len(rejected),
            "selected_tickers": [str(row.get("ticker")) for row in selected],
            "selected": selected,
            "rejected_sample": rejected[:20],
        }
        if not selected:
            report["warnings"].append(f"{market}:no_prefilter_candidates_selected")
        report["markets"][market] = market_payload

    report["summary"] = {
        "market_count": len(markets),
        "selected_total": sum(int(item.get("selected_count") or 0) for item in report["markets"].values()),
        "seed_total": sum(int(item.get("seed_count") or 0) for item in report["markets"].values()),
        "quote_fetch_total": sum(int(item.get("quote_fetch_count") or 0) for item in report["markets"].values()),
        "flow_fetch_total": sum(int(item.get("flow_fetch_count") or 0) for item in report["markets"].values()),
    }
    return report


def selected_ticker_arg(report: Mapping[str, Any], market: str) -> str:
    market_payload = (report.get("markets") or {}).get(_market_key(market)) if isinstance(report.get("markets"), Mapping) else {}
    selected = market_payload.get("selected") if isinstance(market_payload, Mapping) else []
    parts = []
    for row in selected if isinstance(selected, list) else []:
        if not isinstance(row, Mapping):
            continue
        ticker = str(row.get("ticker") or "").strip()
        if not ticker:
            continue
        name = str(row.get("name") or ticker).strip()
        parts.append(f"{ticker}={name}")
    return ",".join(parts)


def selected_ticker_symbols(report: Mapping[str, Any], market: str) -> str:
    market_payload = (report.get("markets") or {}).get(_market_key(market)) if isinstance(report.get("markets"), Mapping) else {}
    selected = market_payload.get("selected") if isinstance(market_payload, Mapping) else []
    tickers = []
    for row in selected if isinstance(selected, list) else []:
        if not isinstance(row, Mapping):
            continue
        ticker = str(row.get("ticker") or "").strip()
        if ticker:
            tickers.append(ticker)
    return ",".join(tickers)


def write_kis_operational_prefilter_report(
    report: Mapping[str, Any],
    *,
    output_path: Path,
    latest_path: Optional[Path] = None,
) -> Dict[str, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n"
    output_path.write_text(text, encoding="utf-8")
    paths = {"json": str(output_path)}
    if latest_path is not None:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(text, encoding="utf-8")
        paths["latest_json"] = str(latest_path)
    return paths


__all__ = [
    "KIS_OPERATIONAL_PREFILTER_VERSION",
    "KISOperationalPrefilterConfig",
    "build_kis_operational_prefilter",
    "selected_ticker_arg",
    "selected_ticker_symbols",
    "write_kis_operational_prefilter_report",
]
