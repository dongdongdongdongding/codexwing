#!/usr/bin/env python3
"""Augment historical KIS proxy caches with non-leaky static KIS stock info."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kis_model_features import KIS_CATEGORICAL_FEATURES, KIS_NUMERIC_FEATURES
from multi_agent.tools.augment_kis_historical_proxy_with_sidecar_cache import (
    _coverage_delta,
    _normalize_ticker,
    _present_mask,
    _round,
    _scope,
    _with_join_keys,
)


REPORT_VERSION = "kis_static_sidecar_master_augmentation_v1"
DEFAULT_SIDECAR_CACHE = (
    ROOT
    / "runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl"
)
DEFAULT_PROXY_CACHES = (
    "KOSPI="
    + str(ROOT / "runtime_state/reports/learning/kis_historical_universe_prefilter_proxy_prepared_kospi_20260101_20260610.pkl"),
    "KOSDAQ="
    + str(ROOT / "runtime_state/reports/learning/kis_historical_universe_prefilter_proxy_prepared_kosdaq_20260101_20260610.pkl"),
)
DEFAULT_OUTPUT_JSON = ROOT / "runtime_state/reports/learning/kis_static_sidecar_master_augmented_proxy_20260613.json"

STATIC_FEATURE_COLUMNS = tuple(
    dict.fromkeys(
        [
            "kis_stock_market_code",
            "kis_stock_market_name",
            "kis_stock_type",
            "kis_stock_listed_date",
            "kis_stock_status_code",
            "kis_stock_sector_name",
            "kis_stock_standard_industry_code",
            "kis_stock_listed_shares",
            "kis_stock_capital_amount",
            "kis_stock_par_value",
            "kis_stock_kospi200_item",
            "kis_stock_trade_stop",
            "kis_stock_admin_item",
            "kis_theme_news_standard_industry_code",
        ]
    )
)
UNKNOWN_TEXT = {"", "UNKNOWN", "NAN", "NONE", "NULL", "<NA>"}
PROVENANCE_COLUMNS = (
    "kis_static_sidecar_master_augmented",
    "kis_static_sidecar_master_source",
    "kis_static_sidecar_master_augmented_at",
    "kis_static_sidecar_master_no_dummy_data",
    "kis_static_sidecar_master_leakage_policy",
    "kis_static_sidecar_master_feature_count",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return round(number, 6)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _is_categorical(col: str) -> bool:
    return col in set(KIS_CATEGORICAL_FEATURES)


def _canonical_value(col: str, value: Any) -> Any:
    if value is None:
        return None
    if _is_categorical(col):
        text = str(value).strip()
        return None if text.upper() in UNKNOWN_TEXT else text
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)


def _valid_values(series: pd.Series, col: str) -> List[Any]:
    values: List[Any] = []
    for raw in series.tolist():
        value = _canonical_value(col, raw)
        if value is not None:
            values.append(value)
    return values


def _stable_unique(values: Sequence[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for value in values:
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _default_output_cache(market: str) -> Path:
    return (
        ROOT
        / "runtime_state/reports/learning"
        / f"kis_historical_universe_static_sidecar_master_augmented_prepared_{market.lower()}_20260101_20260610.pkl"
    )


def build_static_master(
    sidecar: pd.DataFrame,
    *,
    static_columns: Sequence[str] = STATIC_FEATURE_COLUMNS,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    keyed = _with_join_keys(sidecar)
    columns = [col for col in static_columns if col in keyed.columns and col in set(KIS_NUMERIC_FEATURES) | set(KIS_CATEGORICAL_FEATURES)]
    rows: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    keyed = keyed[keyed["__join_market"].ne("") & keyed["__join_ticker"].ne("")]
    for (market, ticker), group in keyed.groupby(["__join_market", "__join_ticker"], dropna=False):
        row: Dict[str, Any] = {"__join_market": market, "__join_ticker": ticker}
        feature_count = 0
        for col in columns:
            unique = _stable_unique(_valid_values(group[col], col))
            if len(unique) == 1:
                row[col] = unique[0]
                feature_count += 1
            elif len(unique) > 1:
                conflicts.append({"market": market, "ticker": ticker, "feature": col, "unique_count": len(unique)})
        if feature_count:
            row["__static_feature_count"] = feature_count
            rows.append(row)
    master = pd.DataFrame(rows)
    summary = {
        "version": REPORT_VERSION,
        "input_rows": int(len(sidecar)),
        "keyed_rows": int(len(keyed)),
        "master_rows": int(len(master)),
        "master_markets": master["__join_market"].value_counts().to_dict() if not master.empty else {},
        "static_columns_considered": columns,
        "conflict_count": int(len(conflicts)),
        "conflict_examples": conflicts[:20],
        "no_dummy_data": True,
        "source": "real_kis_sidecar_cache_static_stock_info",
        "leakage_policy": "ticker_static_stock_info_only; no flow/news/vi/rank/financial values; fill missing only",
    }
    return master, summary


def augment_market_proxy_with_static_master(
    proxy: pd.DataFrame,
    master: pd.DataFrame,
    *,
    market: str,
    generated_at: str | None = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    generated_at = generated_at or _utc_now()
    proxy_keyed = _with_join_keys(proxy, market=market)
    before = proxy_keyed.copy()
    feature_cols = [
        col
        for col in STATIC_FEATURE_COLUMNS
        if col in master.columns and col in set(KIS_NUMERIC_FEATURES) | set(KIS_CATEGORICAL_FEATURES)
    ]
    lookup_cols = ["__join_market", "__join_ticker", "__static_feature_count", *feature_cols]
    lookup = master.loc[:, [col for col in lookup_cols if col in master.columns]].copy()
    merged = proxy_keyed.merge(
        lookup,
        on=["__join_market", "__join_ticker"],
        how="left",
        suffixes=("", "__static_master"),
    )
    master_matched = merged.get("__static_feature_count", pd.Series(0, index=merged.index)).fillna(0).astype(float).gt(0)
    row_fill_count = pd.Series(0, index=merged.index, dtype=int)
    fill_counts: MutableMapping[str, int] = {}
    matched_value_counts: MutableMapping[str, int] = {}

    for col in feature_cols:
        master_col = f"{col}__static_master" if col in before.columns else col
        if master_col not in merged.columns:
            continue
        master_present = _present_mask(merged[master_col], col)
        matched_value_counts[col] = int(master_present.sum())
        if col not in before.columns:
            merged[col] = merged[master_col]
            fill_mask = master_present
        else:
            before_present = _present_mask(before[col].reset_index(drop=True), col)
            fill_mask = master_present & ~before_present
            merged.loc[fill_mask, col] = merged.loc[fill_mask, master_col]
        fill_counts[col] = int(fill_mask.sum())
        row_fill_count += fill_mask.astype(int)

    augmented = row_fill_count.gt(0)
    merged["kis_static_sidecar_master_augmented"] = augmented.astype(int)
    merged["kis_static_sidecar_master_source"] = np.where(augmented, "real_kis_sidecar_static_master", None)
    merged["kis_static_sidecar_master_augmented_at"] = np.where(augmented, generated_at, None)
    merged["kis_static_sidecar_master_no_dummy_data"] = np.where(augmented, True, None)
    merged["kis_static_sidecar_master_leakage_policy"] = np.where(
        augmented,
        "ticker_static_stock_info_only_fill_missing_no_forward_price_or_flow",
        None,
    )
    merged["kis_static_sidecar_master_feature_count"] = np.where(augmented, row_fill_count, 0)

    drop_cols = [
        col
        for col in merged.columns
        if col.startswith("__join_") or col == "__static_feature_count" or col.endswith("__static_master")
    ]
    out = merged.drop(columns=drop_cols)
    before_for_delta = before.drop(columns=[col for col in before.columns if col.startswith("__join_")])
    summary = {
        "market": market.upper(),
        "proxy_scope_before": _scope(proxy),
        "proxy_scope_after": _scope(out),
        "master_matched_rows": int(master_matched.sum()),
        "master_matched_row_pct": _round(float(master_matched.mean() * 100.0), 3) if len(master_matched) else 0.0,
        "augmented_rows": int(augmented.sum()),
        "augmented_row_pct": _round(float(augmented.mean() * 100.0), 3) if len(augmented) else 0.0,
        "no_dummy_data": True,
        "leakage_policy": "ticker static stock_info only; fills missing cells only; no flow/news/VI/rank/financial copied",
        "feature_columns_considered": feature_cols,
        "feature_fill_counts_top": sorted(
            [{"feature": key, "filled_missing_values": int(value)} for key, value in fill_counts.items() if value > 0],
            key=lambda item: int(item["filled_missing_values"]),
            reverse=True,
        ),
        "matched_value_counts_top": sorted(
            [{"feature": key, "matched_real_values": int(value)} for key, value in matched_value_counts.items() if value > 0],
            key=lambda item: int(item["matched_real_values"]),
            reverse=True,
        ),
        "coverage_delta": _coverage_delta(before_for_delta, out),
    }
    return out, summary


def _parse_market_path(value: str) -> Tuple[str, Path]:
    if "=" not in value:
        raise ValueError(f"expected MARKET=PATH, got {value!r}")
    market, raw_path = value.split("=", 1)
    market = market.strip().upper()
    if not market:
        raise ValueError(f"empty market in {value!r}")
    return market, Path(raw_path)


def build_report(
    *,
    sidecar_cache: Path,
    proxy_caches: Mapping[str, Path],
    output_caches: Mapping[str, Path],
) -> Dict[str, Any]:
    generated_at = _utc_now()
    sidecar = pd.read_pickle(sidecar_cache)
    master, master_summary = build_static_master(sidecar)
    market_reports: List[Dict[str, Any]] = []
    for market, proxy_path in proxy_caches.items():
        proxy = pd.read_pickle(proxy_path)
        augmented, summary = augment_market_proxy_with_static_master(proxy, master, market=market, generated_at=generated_at)
        output_path = output_caches.get(market, _default_output_cache(market))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        augmented.to_pickle(output_path)
        summary["input_proxy_cache"] = str(proxy_path)
        summary["output_cache"] = str(output_path)
        market_reports.append(summary)
    return {
        "version": REPORT_VERSION,
        "generated_at": generated_at,
        "objective": (
            "Build a non-leaky static KIS stock-info master from real sidecar cache and widen historical proxy feature parity "
            "without fabricating flow, news, VI, rank, or financial values."
        ),
        "dummy_data_used": False,
        "sidecar_cache": _scope(sidecar, path=sidecar_cache),
        "static_master": master_summary,
        "markets": market_reports,
        "decision": {
            "augmented_cache_ready_for_research": True,
            "production_replacement_ready": False,
            "reason": "static stock-info parity is an input-quality improvement only; promotion still requires walk-forward performance gates.",
            "leakage_policy": master_summary["leakage_policy"],
        },
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def render_markdown(report: Mapping[str, Any]) -> str:
    decision = report.get("decision") if isinstance(report.get("decision"), Mapping) else {}
    master = report.get("static_master") if isinstance(report.get("static_master"), Mapping) else {}
    lines = [
        "# KIS Static Sidecar Master Augmentation",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
        f"- leakage_policy: `{decision.get('leakage_policy')}`",
        "",
        "## Static Master",
        f"- master_rows: `{master.get('master_rows')}`",
        f"- conflict_count: `{master.get('conflict_count')}`",
        f"- columns: `{master.get('static_columns_considered')}`",
        "",
        "## Market Augmentation",
    ]
    for market_report in report.get("markets") or []:
        if not isinstance(market_report, Mapping):
            continue
        lines.append(
            f"- {market_report.get('market')}: matched_rows=`{market_report.get('master_matched_rows')}` "
            f"augmented_rows=`{market_report.get('augmented_rows')}` "
            f"augmented_pct=`{market_report.get('augmented_row_pct')}` output=`{market_report.get('output_cache')}`"
        )
    lines.extend(["", "## Top Coverage Deltas"])
    for market_report in report.get("markets") or []:
        if not isinstance(market_report, Mapping):
            continue
        lines.append(f"### {market_report.get('market')}")
        lines.append("| family | improved_features | avg_positive_delta_pct | top_delta |")
        lines.append("|---|---:|---:|---|")
        coverage_delta = market_report.get("coverage_delta") if isinstance(market_report.get("coverage_delta"), Mapping) else {}
        for family, payload in coverage_delta.items():
            if not isinstance(payload, Mapping):
                continue
            top = (payload.get("top_deltas") or [{}])[0]
            top_desc = (
                f"`{top.get('feature')}` {top.get('before_present_pct')} -> "
                f"{top.get('after_present_pct')} (+{top.get('delta_pct')})"
                if isinstance(top, Mapping) and top.get("feature")
                else "-"
            )
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(family),
                        _fmt(payload.get("features_improved")),
                        _fmt(payload.get("avg_positive_delta_pct")),
                        top_desc,
                    ]
                )
                + " |"
            )
    lines.extend(["", "## Decision", f"- {decision.get('reason')}"])
    return "\n".join(lines) + "\n"


def write_report(report: Mapping[str, Any], output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    output_json.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sidecar-cache", default=str(DEFAULT_SIDECAR_CACHE))
    parser.add_argument("--proxy-cache", action="append", default=list(DEFAULT_PROXY_CACHES), help="MARKET=pickle path")
    parser.add_argument("--output-cache", action="append", default=[], help="MARKET=output pickle path")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    proxy_caches = dict(_parse_market_path(value) for value in args.proxy_cache)
    output_caches = dict(_parse_market_path(value) for value in args.output_cache)
    report = build_report(
        sidecar_cache=Path(args.sidecar_cache),
        proxy_caches=proxy_caches,
        output_caches=output_caches,
    )
    write_report(report, Path(args.output_json))
    print(
        json.dumps(
            {
                "output_json": args.output_json,
                "outputs": {row.get("market"): row.get("output_cache") for row in report.get("markets") or []},
                "augmented_rows": {row.get("market"): row.get("augmented_rows") for row in report.get("markets") or []},
                "decision": report.get("decision"),
            },
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
