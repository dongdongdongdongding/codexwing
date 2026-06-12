#!/usr/bin/env python3
"""Augment historical KIS proxy caches with exact-date real KIS sidecar rows."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kis_model_features import (
    KIS_CATEGORICAL_FEATURES,
    KIS_NUMERIC_FEATURES,
    KIS_PREFILTER_CATEGORICAL_FEATURES,
    KIS_PREFILTER_NUMERIC_FEATURES,
    KIS_SIDECAR_CATEGORICAL_FEATURES,
    KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES,
    KIS_SIDECAR_MODEL_NUMERIC_FEATURES,
    KIS_THEME_NEWS_CATEGORICAL_FEATURES,
    KIS_THEME_NEWS_NUMERIC_FEATURES,
)
from multi_agent.tools.report_kis_sidecar_proxy_feature_gap import FEATURE_FAMILIES


REPORT_VERSION = "kis_sidecar_cache_exact_date_augmentation_v1"
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
DEFAULT_OUTPUT_JSON = ROOT / "runtime_state/reports/learning/kis_sidecar_cache_augmented_proxy_20260613.json"

PROVENANCE_COLUMNS = (
    "kis_sidecar_cache_augmented",
    "kis_sidecar_cache_source",
    "kis_sidecar_cache_augmented_at",
    "kis_sidecar_cache_no_dummy_data",
    "kis_sidecar_cache_leakage_policy",
)
FEATURE_COLUMNS = tuple(dict.fromkeys(list(KIS_NUMERIC_FEATURES) + list(KIS_CATEGORICAL_FEATURES)))
LEAK_TOKENS = (
    "return_1d",
    "return_3d",
    "return_5d",
    "target_hit",
    "stop_hit",
    "mfe_",
    "mae_",
    "outcome",
    "label",
    "realized",
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


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _is_leaky_column(name: str) -> bool:
    lower = str(name).lower()
    return any(token in lower for token in LEAK_TOKENS)


def _feature_columns(frame: pd.DataFrame) -> List[str]:
    return [col for col in FEATURE_COLUMNS if col in frame.columns and not _is_leaky_column(col)]


def _normalize_ticker(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text or text in {"NAN", "NONE", "NULL"}:
        return ""
    first = text.split(".")[0]
    digits = re.sub(r"\D", "", first)
    if len(digits) >= 6:
        return digits[-6:]
    if digits:
        return digits.zfill(6)
    return first


def _normalize_date_series(frame: pd.DataFrame) -> pd.Series:
    if "base_trade_date" in frame.columns:
        values = frame["base_trade_date"]
    elif "trade_date" in frame.columns:
        values = frame["trade_date"]
    else:
        return pd.Series("", index=frame.index, dtype=str)
    parsed = pd.to_datetime(values, errors="coerce")
    return parsed.dt.date.astype(str).replace("NaT", "")


def _with_join_keys(frame: pd.DataFrame, *, market: str | None = None) -> pd.DataFrame:
    out = frame.copy()
    market_values = out["market"] if "market" in out.columns else market
    if market_values is None:
        out["__join_market"] = ""
    elif isinstance(market_values, pd.Series):
        out["__join_market"] = market_values.fillna("").astype(str).str.upper()
    else:
        out["__join_market"] = str(market_values).upper()
    ticker_col = "ticker" if "ticker" in out.columns else "code" if "code" in out.columns else None
    if ticker_col is None:
        out["__join_ticker"] = ""
    else:
        out["__join_ticker"] = out[ticker_col].map(_normalize_ticker)
    out["__join_date"] = _normalize_date_series(out)
    return out


def _is_categorical_feature(col: str) -> bool:
    return col in set(KIS_CATEGORICAL_FEATURES)


def _present_mask(series: pd.Series, col: str) -> pd.Series:
    if _is_categorical_feature(col):
        values = series.fillna("").astype(str).str.strip()
        return values.ne("") & ~values.str.upper().isin({"UNKNOWN", "NAN", "NONE", "NULL"})
    return pd.to_numeric(series, errors="coerce").notna()


def _presence_count(frame: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    if not columns:
        return pd.Series(0, index=frame.index, dtype=int)
    counts = pd.Series(0, index=frame.index, dtype=int)
    for col in columns:
        counts += _present_mask(frame[col], col).astype(int)
    return counts


def _present_pct(frame: pd.DataFrame, col: str) -> float | None:
    if col not in frame.columns or frame.empty:
        return None
    return _round(float(_present_mask(frame[col], col).mean() * 100.0), 3)


def _family_coverage(frame: pd.DataFrame) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for family, cols in FEATURE_FAMILIES.items():
        rows = []
        nonzero = 0
        for col in cols:
            pct = _present_pct(frame, col)
            if pct is None:
                continue
            if pct > 0:
                nonzero += 1
            rows.append({"feature": col, "present_pct": pct})
        rows.sort(key=lambda item: float(item.get("present_pct") or 0.0), reverse=True)
        out[family] = {
            "feature_count": len(rows),
            "nonzero_features": int(nonzero),
            "top_present": rows[:12],
            "bottom_present": sorted(rows, key=lambda item: float(item.get("present_pct") or 0.0))[:12],
        }
    return out


def _coverage_delta(before: pd.DataFrame, after: pd.DataFrame) -> Dict[str, Any]:
    families: Dict[str, Any] = {}
    for family, cols in FEATURE_FAMILIES.items():
        rows = []
        for col in cols:
            before_pct = _present_pct(before, col)
            after_pct = _present_pct(after, col)
            if before_pct is None and after_pct is None:
                continue
            b = float(before_pct or 0.0)
            a = float(after_pct or 0.0)
            rows.append(
                {
                    "feature": col,
                    "before_present_pct": _round(b, 3),
                    "after_present_pct": _round(a, 3),
                    "delta_pct": _round(a - b, 3),
                }
            )
        rows.sort(key=lambda item: float(item.get("delta_pct") or 0.0), reverse=True)
        positive = [row for row in rows if float(row.get("delta_pct") or 0.0) > 0]
        families[family] = {
            "features_improved": len(positive),
            "avg_positive_delta_pct": _round(float(np.mean([row["delta_pct"] for row in positive])) if positive else 0.0, 3),
            "top_deltas": rows[:15],
        }
    return families


def _scope(frame: pd.DataFrame, *, path: Path | None = None) -> Dict[str, Any]:
    dates = _normalize_date_series(frame).replace("", np.nan).dropna()
    tickers = frame["ticker"].map(_normalize_ticker) if "ticker" in frame.columns else pd.Series(dtype=str)
    payload: Dict[str, Any] = {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "date_min": dates.min() if not dates.empty else None,
        "date_max": dates.max() if not dates.empty else None,
        "unique_days": int(dates.nunique()) if not dates.empty else 0,
        "unique_tickers": int(tickers.replace("", np.nan).dropna().nunique()) if not tickers.empty else 0,
    }
    if path is not None:
        payload["path"] = str(path)
    if "market" in frame.columns:
        payload["markets"] = {str(k): int(v) for k, v in frame["market"].astype(str).value_counts().to_dict().items()}
    return payload


def _dedupe_sidecar(sidecar: pd.DataFrame, feature_cols: Sequence[str]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    required = ["__join_market", "__join_ticker", "__join_date"]
    scoped = sidecar.loc[
        sidecar["__join_market"].ne("") & sidecar["__join_ticker"].ne("") & sidecar["__join_date"].ne("")
    ].copy()
    before = int(len(scoped))
    scoped["__feature_presence_count"] = _presence_count(scoped, feature_cols)
    scoped = scoped.sort_values(required + ["__feature_presence_count"], ascending=[True, True, True, False])
    deduped = scoped.drop_duplicates(required, keep="first")
    return deduped, {
        "input_keyed_rows": before,
        "deduped_key_rows": int(len(deduped)),
        "duplicate_key_rows_removed": int(before - len(deduped)),
        "max_feature_presence_count": int(scoped["__feature_presence_count"].max()) if not scoped.empty else 0,
    }


def augment_market_proxy(
    proxy: pd.DataFrame,
    sidecar: pd.DataFrame,
    *,
    market: str,
    generated_at: str | None = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    generated_at = generated_at or _utc_now()
    proxy_keyed = _with_join_keys(proxy, market=market)
    sidecar_keyed = _with_join_keys(sidecar)
    feature_cols = _feature_columns(sidecar_keyed)
    sidecar_deduped, dedupe_meta = _dedupe_sidecar(sidecar_keyed, feature_cols)
    sidecar_columns = ["__join_market", "__join_ticker", "__join_date", *feature_cols, "__feature_presence_count"]
    sidecar_lookup = sidecar_deduped.loc[:, sidecar_columns].copy()
    sidecar_lookup["__sidecar_cache_key_present"] = 1

    before = proxy_keyed.copy()
    merged = proxy_keyed.merge(
        sidecar_lookup,
        on=["__join_market", "__join_ticker", "__join_date"],
        how="left",
        suffixes=("", "__sidecar_cache"),
    )
    matched = merged["__sidecar_cache_key_present"].fillna(0).astype(int).eq(1)
    fill_counts: MutableMapping[str, int] = {}
    overwritten_counts: MutableMapping[str, int] = {}

    for col in feature_cols:
        side_col = f"{col}__sidecar_cache" if col in proxy_keyed.columns else col
        if side_col not in merged.columns:
            continue
        side_present = _present_mask(merged[side_col], col)
        if col not in before.columns:
            merged[col] = merged[side_col]
            fill_counts[col] = int(side_present.sum())
            overwritten_counts[col] = 0
            continue
        before_present = _present_mask(before[col].reset_index(drop=True), col)
        overwrite_mask = side_present
        overwritten_counts[col] = int((overwrite_mask & before_present).sum())
        fill_counts[col] = int((overwrite_mask & ~before_present).sum())
        merged.loc[overwrite_mask, col] = merged.loc[overwrite_mask, side_col]

    merged["kis_sidecar_cache_augmented"] = matched.astype(int)
    merged["kis_sidecar_cache_source"] = np.where(matched, "exact_ticker_date_sidecar_cache", None)
    merged["kis_sidecar_cache_augmented_at"] = np.where(matched, generated_at, None)
    merged["kis_sidecar_cache_no_dummy_data"] = np.where(matched, True, None)
    merged["kis_sidecar_cache_leakage_policy"] = np.where(matched, "exact_ticker_date_only_no_forward_fill", None)

    drop_cols = [
        col
        for col in merged.columns
        if col.startswith("__join_")
        or col == "__sidecar_cache_key_present"
        or col == "__feature_presence_count"
        or col.endswith("__sidecar_cache")
    ]
    out = merged.drop(columns=drop_cols)
    before_for_delta = before.drop(columns=[col for col in before.columns if col.startswith("__join_")])
    summary = {
        "market": market.upper(),
        "proxy_scope_before": _scope(proxy),
        "proxy_scope_after": _scope(out),
        "sidecar_dedupe": dedupe_meta,
        "matched_rows": int(matched.sum()),
        "matched_row_pct": _round(float(matched.mean() * 100.0), 3) if len(matched) else 0.0,
        "matched_days": int(merged.loc[matched, "__join_date"].nunique()),
        "matched_tickers": int(merged.loc[matched, "__join_ticker"].nunique()),
        "no_dummy_data": True,
        "leakage_policy": "exact ticker/date/market join only; no forward-fill; no backward-fill; no label columns copied",
        "feature_columns_considered": len(feature_cols),
        "feature_fill_counts_top": sorted(
            [{"feature": key, "filled_missing_values": int(value)} for key, value in fill_counts.items() if value > 0],
            key=lambda item: int(item["filled_missing_values"]),
            reverse=True,
        )[:30],
        "feature_overwrite_counts_top": sorted(
            [{"feature": key, "overwritten_existing_values": int(value)} for key, value in overwritten_counts.items() if value > 0],
            key=lambda item: int(item["overwritten_existing_values"]),
            reverse=True,
        )[:30],
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


def _default_output_cache(market: str) -> Path:
    return (
        ROOT
        / "runtime_state/reports/learning"
        / f"kis_historical_universe_sidecar_cache_augmented_prepared_{market.lower()}_20260101_20260610.pkl"
    )


def build_report(
    *,
    sidecar_cache: Path,
    proxy_caches: Mapping[str, Path],
    output_caches: Mapping[str, Path],
    matched_only_output_caches: Mapping[str, Path] | None = None,
) -> Dict[str, Any]:
    generated_at = _utc_now()
    sidecar = pd.read_pickle(sidecar_cache)
    sidecar_scope = _scope(sidecar, path=sidecar_cache)
    matched_only_output_caches = matched_only_output_caches or {}
    market_reports = []
    for market, proxy_path in proxy_caches.items():
        proxy = pd.read_pickle(proxy_path)
        augmented, summary = augment_market_proxy(proxy, sidecar, market=market, generated_at=generated_at)
        output_path = output_caches.get(market, _default_output_cache(market))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        augmented.to_pickle(output_path)
        matched_only_path = matched_only_output_caches.get(market)
        if matched_only_path is not None:
            matched_only_path.parent.mkdir(parents=True, exist_ok=True)
            matched_only = augmented[augmented["kis_sidecar_cache_augmented"].fillna(0).astype(int).eq(1)].copy()
            matched_only.to_pickle(matched_only_path)
            summary["matched_only_output_cache"] = str(matched_only_path)
            summary["matched_only_scope"] = _scope(matched_only)
        summary["input_proxy_cache"] = str(proxy_path)
        summary["output_cache"] = str(output_path)
        market_reports.append(summary)
    return {
        "version": REPORT_VERSION,
        "generated_at": generated_at,
        "objective": (
            "실제 KIS sidecar cache가 가진 flow/financial/static/news/prefilter 피쳐를 "
            "누수 없이 historical proxy 학습 캐시에 exact ticker-date 기준으로 붙여 "
            "3단 touch5_dd10 연구 입력을 개선한다."
        ),
        "dummy_data_used": False,
        "sidecar_cache": sidecar_scope,
        "markets": market_reports,
        "decision": {
            "augmented_cache_ready_for_research": True,
            "production_replacement_ready": False,
            "reason": "이 도구는 학습 입력 보강까지만 수행한다. 운영 승격은 별도 walk-forward 성능 검증과 표본 gate 통과가 필요하다.",
            "leakage_policy": "exact_ticker_date_only_no_forward_fill",
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
    lines = [
        "# KIS Sidecar Exact-Date Cache Augmentation",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- augmented_cache_ready_for_research: `{decision.get('augmented_cache_ready_for_research')}`",
        f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
        f"- leakage_policy: `{decision.get('leakage_policy')}`",
        "",
        "## Scope",
    ]
    sidecar = report.get("sidecar_cache") if isinstance(report.get("sidecar_cache"), Mapping) else {}
    lines.append(
        f"- sidecar: rows=`{sidecar.get('rows')}` days=`{sidecar.get('unique_days')}` "
        f"date=`{sidecar.get('date_min')}`..`{sidecar.get('date_max')}` tickers=`{sidecar.get('unique_tickers')}`"
    )
    lines.extend(["", "## Market Augmentation"])
    for market_report in report.get("markets") or []:
        if not isinstance(market_report, Mapping):
            continue
        lines.append(
            f"- {market_report.get('market')}: matched_rows=`{market_report.get('matched_rows')}` "
            f"matched_pct=`{market_report.get('matched_row_pct')}` days=`{market_report.get('matched_days')}` "
            f"tickers=`{market_report.get('matched_tickers')}` output=`{market_report.get('output_cache')}`"
        )
        if market_report.get("matched_only_output_cache"):
            scope = market_report.get("matched_only_scope") if isinstance(market_report.get("matched_only_scope"), Mapping) else {}
            lines.append(
                f"  - matched_only: rows=`{scope.get('rows')}` days=`{scope.get('unique_days')}` "
                f"output=`{market_report.get('matched_only_output_cache')}`"
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
    lines.extend(
        [
            "",
            "## Decision",
            f"- {decision.get('reason')}",
            "- 이 산출물은 성능 보고가 아니라, 다음 walk-forward 연구를 위한 실데이터 입력 보강 결과다.",
        ]
    )
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    output_json.with_suffix(".md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sidecar-cache", default=str(DEFAULT_SIDECAR_CACHE))
    parser.add_argument("--proxy-cache", action="append", default=list(DEFAULT_PROXY_CACHES), help="MARKET=pickle path")
    parser.add_argument("--output-cache", action="append", default=[], help="MARKET=output pickle path")
    parser.add_argument("--matched-only-output-cache", action="append", default=[], help="MARKET=matched-only output pickle path")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    proxy_caches = dict(_parse_market_path(value) for value in args.proxy_cache)
    output_caches = dict(_parse_market_path(value) for value in args.output_cache)
    matched_only_output_caches = dict(_parse_market_path(value) for value in args.matched_only_output_cache)
    report = build_report(
        sidecar_cache=Path(args.sidecar_cache),
        proxy_caches=proxy_caches,
        output_caches=output_caches,
        matched_only_output_caches=matched_only_output_caches,
    )
    write_report(report, Path(args.output_json))
    print(
        json.dumps(
            {
                "output_json": args.output_json,
                "outputs": {row.get("market"): row.get("output_cache") for row in report.get("markets") or []},
                "matched_rows": {row.get("market"): row.get("matched_rows") for row in report.get("markets") or []},
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
