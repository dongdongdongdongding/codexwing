#!/usr/bin/env python3
"""Audit KIS touch5/dd10 research coverage across periods and feature families."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REPORT_VERSION = "kis_touch5_research_coverage_audit_v1"
REPORT_DIR = ROOT / "runtime_state/reports/learning"
DEFAULT_OUTPUT = REPORT_DIR / "kis_touch5_research_coverage_audit_20260613.json"
DEFAULT_PREPARED_CACHE = (
    REPORT_DIR / "scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl"
)
DEFAULT_LEADERBOARD = REPORT_DIR / "kis_touch5_candidate_leaderboard_20260613.json"
DEFAULT_OBJECTIVE = REPORT_DIR / "kis_touch5_research_objective_verification_20260613.json"
DEFAULT_DRAWDOWN = REPORT_DIR / "kis_touch5_dd10_drawdown_filter_research_kospi_20260101_20260610.json"
DEFAULT_ACTUAL_REPORTS = (
    REPORT_DIR / "kis_sidecar_threshold_sweep_touch5_dd10_longfold_20260101_20260610.json",
    REPORT_DIR / "kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json",
    REPORT_DIR / "kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json",
    REPORT_DIR / "kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json",
    DEFAULT_DRAWDOWN,
)
DEFAULT_PROXY_REPORTS = (
    REPORT_DIR / "kis_historical_best_effort_suite_static_master_focused_20260101_20260610.json",
    REPORT_DIR / "kis_three_stage_ev_ranker_dynamic_exit_20260101_20260610.json",
    REPORT_DIR / "kis_three_stage_ev_ranker_static_master_kospi_20260613.json",
    REPORT_DIR / "kis_three_stage_ev_ranker_static_master_kosdaq_20260613.json",
    REPORT_DIR / "kis_three_stage_ev_ranker_finaltopn_prefilter_proxy_20260101_20260610.json",
)
REQUIRED_MONTHS = ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06")
REQUIRED_MARKETS = ("KOSPI", "KOSDAQ")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip().replace("%", "").replace(",", "")
            if not text or text.lower() in {"none", "nan", "null", "-"}:
                return None
            value = text
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _round(value: Any, digits: int = 6) -> float | None:
    number = _safe_float(value)
    if number is None:
        return None
    return round(number, digits)


def _non_empty(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        return series.notna() & series.astype(str).str.strip().ne("")
    return series.notna()


def _month(value: Any) -> str | None:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return str(ts.to_period("M"))


def _date(value: Any) -> str | None:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return str(ts.date())


def _family_for_column(column: str) -> str | None:
    name = column.lower()
    if name in {
        "trade_date",
        "ticker",
        "symbol",
        "market",
        "run_id",
        "scan_id",
        "scan_mode",
        "source_ref",
    }:
        return None
    if name.startswith("close_failure_prior_"):
        return "close_failure_prior"
    if name.startswith("kis_news_") or name.startswith("kis_theme_news_") or name.startswith("theme_") or name.startswith("news_"):
        return "theme_news"
    if name.startswith("kis_financial_"):
        return "kis_financial"
    if name.startswith("kis_stock_") or name in {
        "kis_sector_code",
        "kis_sector_name",
        "kis_industry_code",
        "kis_industry_name",
    }:
        return "kis_static_master"
    if name.startswith(("kis_foreigner", "kis_institution", "kis_individual", "kis_whale")):
        return "kis_flow"
    if name.startswith("kis_"):
        return "kis_price_rank_quote"
    if any(part in name for part in ("rsi", "macd", "ma_", "volume", "momentum", "breakout", "trend", "tech", "alpha", "whale")):
        return "scanner_technical"
    return "other_scan_context"


def _feature_family_profile(data: pd.DataFrame) -> Dict[str, Any]:
    by_family: Dict[str, List[str]] = defaultdict(list)
    for column in data.columns:
        family = _family_for_column(str(column))
        if family:
            by_family[family].append(str(column))
    family_summary: Dict[str, Any] = {}
    for family, columns in sorted(by_family.items()):
        present_rows = []
        top_columns = []
        for column in columns:
            pct = float(_non_empty(data[column]).mean() * 100.0) if column in data.columns and len(data) else 0.0
            present_rows.append(pct)
            top_columns.append({"column": column, "present_pct": _round(pct, 3)})
        top_columns = sorted(top_columns, key=lambda row: float(row.get("present_pct") or 0.0), reverse=True)[:8]
        family_summary[family] = {
            "column_count": int(len(columns)),
            "avg_present_pct": _round(sum(present_rows) / len(present_rows), 3) if present_rows else 0.0,
            "top_columns": top_columns,
        }
    return family_summary


def _cache_profile(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"path": _rel(path), "status": "missing"}
    data = pd.read_pickle(path)
    if not isinstance(data, pd.DataFrame):
        return {"path": _rel(path), "status": "not_dataframe"}
    profile: Dict[str, Any] = {
        "path": _rel(path),
        "status": "loaded",
        "rows": int(len(data)),
        "columns": int(len(data.columns)),
    }
    if "trade_date" in data.columns:
        dates = pd.to_datetime(data["trade_date"], errors="coerce")
        valid_dates = dates.dropna()
        profile["date_min"] = str(valid_dates.min().date()) if not valid_dates.empty else None
        profile["date_max"] = str(valid_dates.max().date()) if not valid_dates.empty else None
        profile["unique_days"] = int(valid_dates.dt.date.nunique())
        profile["months"] = sorted({str(value) for value in valid_dates.dt.to_period("M").astype(str).tolist()})
        work = data.copy()
        work["_audit_month"] = dates.dt.to_period("M").astype(str)
    else:
        work = data.copy()
        work["_audit_month"] = "UNKNOWN"
    if "market" in work.columns:
        markets = work["market"].fillna("UNKNOWN").astype(str).str.upper()
    else:
        markets = pd.Series(["UNKNOWN"] * len(work), index=work.index)
    work["_audit_market"] = markets
    month_market: Dict[str, Dict[str, Any]] = {}
    if len(work):
        grouped = work.groupby(["_audit_month", "_audit_market"], dropna=False).size()
        for (month, market), count in grouped.items():
            month_market.setdefault(str(month), {})[str(market)] = int(count)
    profile["rows_by_month_market"] = month_market
    profile["feature_families"] = _feature_family_profile(data)
    return profile


def _extract_fold_dates(payload: Any, out: set[str]) -> None:
    if isinstance(payload, Mapping):
        if isinstance(payload.get("test_days"), Sequence) and not isinstance(payload.get("test_days"), (str, bytes, bytearray)):
            for value in payload.get("test_days") or []:
                date = _date(value)
                if date:
                    out.add(date)
        for key in ("test_start", "test_end"):
            date = _date(payload.get(key))
            if date:
                out.add(date)
        for value in payload.values():
            _extract_fold_dates(value, out)
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for value in payload:
            _extract_fold_dates(value, out)


def _report_profile(path: Path, *, basis: str) -> Dict[str, Any]:
    payload = _load_json(path)
    dates: set[str] = set()
    _extract_fold_dates(payload, dates)
    months = sorted({month for month in (_month(value) for value in dates) if month})
    decision = payload.get("decision") if isinstance(payload.get("decision"), Mapping) else {}
    return {
        "path": _rel(path),
        "basis": basis,
        "exists": path.exists(),
        "version": payload.get("version"),
        "status": payload.get("status") or decision.get("status"),
        "validation_mode": payload.get("validation_mode"),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "oos_days": len(dates),
        "oos_months": months,
    }


def _month_matrix(cache: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows_by_month_market = cache.get("rows_by_month_market") if isinstance(cache.get("rows_by_month_market"), Mapping) else {}
    matrix = []
    for month in REQUIRED_MONTHS:
        markets = rows_by_month_market.get(month) if isinstance(rows_by_month_market.get(month), Mapping) else {}
        entry = {"month": month}
        total = 0
        for market in REQUIRED_MARKETS:
            count = int(markets.get(market) or 0)
            entry[market] = count
            total += count
        entry["status"] = "usable" if total >= 1000 and all(int(entry[market]) > 0 for market in REQUIRED_MARKETS) else "missing_or_sparse"
        matrix.append(entry)
    return matrix


def _two_month_windows(month_matrix: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_month = {str(row.get("month")): row for row in month_matrix}
    windows = []
    for first, second in zip(REQUIRED_MONTHS, REQUIRED_MONTHS[1:]):
        entry = {"window": f"{first}..{second}"}
        total = 0
        for market in REQUIRED_MARKETS:
            count = int((by_month.get(first) or {}).get(market) or 0) + int((by_month.get(second) or {}).get(market) or 0)
            entry[market] = count
            total += count
        entry["status"] = "usable" if total >= 3000 and all(int(entry[market]) > 0 for market in REQUIRED_MARKETS) else "missing_or_sparse"
        windows.append(entry)
    return windows


def _best_candidate_summary(leaderboard: Mapping[str, Any], drawdown: Mapping[str, Any]) -> Dict[str, Any]:
    markets = leaderboard.get("markets") if isinstance(leaderboard.get("markets"), Mapping) else {}
    out: Dict[str, Any] = {
        "production_replacement_ready": bool((leaderboard.get("decision") or {}).get("production_replacement_ready")),
        "markets": {},
        "research_only_best": {},
    }
    for market in REQUIRED_MARKETS:
        row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        best = row.get("best_candidate") if isinstance(row.get("best_candidate"), Mapping) else {}
        identity = best.get("identity") if isinstance(best.get("identity"), Mapping) else {}
        metrics = best.get("metrics") if isinstance(best.get("metrics"), Mapping) else {}
        gate = best.get("gate") if isinstance(best.get("gate"), Mapping) else {}
        out["markets"][market] = {
            "selection_rule": identity.get("selection_rule"),
            "validation_mode": best.get("validation_mode"),
            "n": metrics.get("n"),
            "active_days": metrics.get("active_days"),
            "active_runs": metrics.get("active_runs"),
            "hit5_dd10_5d_pct": metrics.get("hit5_dd10_5d_pct"),
            "avg_5d_pct": metrics.get("avg_5d_pct"),
            "min_min_low_5d_pct": metrics.get("min_min_low_5d_pct"),
            "production_ready": bool(gate.get("production_ready")),
            "blockers": gate.get("production_blocking_reasons") or [],
        }
    best_drawdown = drawdown.get("best_production_candidate") if isinstance(drawdown.get("best_production_candidate"), Mapping) else {}
    if best_drawdown:
        identity = best_drawdown.get("identity") if isinstance(best_drawdown.get("identity"), Mapping) else {}
        metrics = best_drawdown.get("metrics") if isinstance(best_drawdown.get("metrics"), Mapping) else {}
        out["research_only_best"] = {
            "selection_rule": identity.get("selection_rule"),
            "validation_mode": identity.get("validation_mode"),
            "deployment_ready": bool(identity.get("deployment_ready")),
            "n": metrics.get("n"),
            "active_days": metrics.get("active_days"),
            "active_runs": metrics.get("active_runs"),
            "hit5_dd10_5d_pct": metrics.get("hit5_dd10_5d_pct"),
            "avg_5d_pct": metrics.get("avg_5d_pct"),
            "min_min_low_5d_pct": metrics.get("min_min_low_5d_pct"),
            "holdout_gate_pass_count": ((drawdown.get("holdout_validation") or {}).get("holdout_gate_pass_count")),
            "note": "research_sweep_only; fixed holdout gate pass is required before promotion review",
        }
    return out


def _feature_axis_status(cache: Mapping[str, Any]) -> Dict[str, Any]:
    families = cache.get("feature_families") if isinstance(cache.get("feature_families"), Mapping) else {}
    required = (
        "scanner_technical",
        "kis_price_rank_quote",
        "kis_flow",
        "kis_static_master",
        "kis_financial",
        "theme_news",
        "close_failure_prior",
    )
    return {
        family: {
            "present": family in families,
            "column_count": (families.get(family) or {}).get("column_count") if isinstance(families.get(family), Mapping) else 0,
            "avg_present_pct": (families.get(family) or {}).get("avg_present_pct") if isinstance(families.get(family), Mapping) else 0,
            "ablation_required": True,
        }
        for family in required
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    cache = _cache_profile(Path(args.prepared_cache))
    leaderboard = _load_json(Path(args.candidate_leaderboard))
    objective = _load_json(Path(args.objective_report))
    drawdown = _load_json(Path(args.drawdown_report))
    actual_reports = [_report_profile(Path(path), basis="actual_kis_sidecar") for path in args.actual_reports]
    proxy_reports = [_report_profile(Path(path), basis="historical_proxy_or_static_master") for path in args.proxy_reports]
    month_matrix = _month_matrix(cache)
    two_month = _two_month_windows(month_matrix)
    missing_actual_months = [row["month"] for row in month_matrix if row.get("status") != "usable"]
    actual_oos_months = sorted(
        {
            month
            for row in actual_reports
            for month in (row.get("oos_months") or [])
            if isinstance(month, str)
        }
    )
    feature_axis = _feature_axis_status(cache)
    decision = {
        "production_replacement_ready": bool((objective.get("decision") or {}).get("production_replacement_proven")),
        "current_best_is_shadow_only": True,
        "actual_kis_full_jan_jun_period_proven": not missing_actual_months,
        "actual_kis_oos_months": actual_oos_months,
        "missing_or_sparse_actual_kis_months": missing_actual_months,
        "monthly_slice_matrix_required": True,
        "two_month_slice_matrix_required": True,
        "feature_family_ablation_required": True,
        "rolling_prior_required": True,
        "status": "coverage_gap_blocks_production_replacement" if missing_actual_months else "coverage_ready_for_slice_research",
        "recommended_action": (
            "do not promote; run actual KIS monthly/2-month slices, feature-family ablations, and rolling-prior validation"
            if missing_actual_months
            else "run slice and feature ablation gates before promotion review"
        ),
    }
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "dummy_data_used": False,
        "decision": decision,
        "prepared_cache": cache,
        "period_coverage": {
            "required_months": list(REQUIRED_MONTHS),
            "month_market_matrix": month_matrix,
            "rolling_two_month_windows": two_month,
            "actual_kis_validation_reports": actual_reports,
            "proxy_validation_reports": proxy_reports,
        },
        "feature_family_coverage": {
            "families": cache.get("feature_families") or {},
            "ablation_status": feature_axis,
        },
        "current_best_performance": _best_candidate_summary(leaderboard, drawdown),
        "research_directions": [
            {
                "axis": "period",
                "plan": "Evaluate 2026-01..2026-06 monthly and rolling two-month windows separately; actual KIS sidecar can only claim months present in the cache.",
                "promotion_rule": "No production promotion from a rule that only works in one month or only in proxy data.",
            },
            {
                "axis": "feature_family",
                "plan": "Run all, all-minus-close_failure_prior, close_failure_prior-only, KIS price/rank/quote, KIS flow, static/financial, theme/news, and technical-only ablations.",
                "promotion_rule": "Promote only if performance survives removing a single dominant family or the dominance is intentionally documented as the model thesis.",
            },
            {
                "axis": "selection_stability",
                "plan": "Use rolling prior: choose thresholds from prior OOS folds only, then apply to the next fold.",
                "promotion_rule": "Post-hoc threshold sweep can seed research but cannot directly become production.",
            },
            {
                "axis": "operational_economics",
                "plan": "Keep the +2% buy-premium, cost model, +5% target touch, and -10% low guard in every metric.",
                "promotion_rule": "0.1% positive close is defense only, never a win.",
            },
        ],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    decision = report.get("decision") if isinstance(report.get("decision"), Mapping) else {}
    cache = report.get("prepared_cache") if isinstance(report.get("prepared_cache"), Mapping) else {}
    current = report.get("current_best_performance") if isinstance(report.get("current_best_performance"), Mapping) else {}
    markets = current.get("markets") if isinstance(current.get("markets"), Mapping) else {}
    research_best = current.get("research_only_best") if isinstance(current.get("research_only_best"), Mapping) else {}
    lines = [
        "# KIS Touch5 Research Coverage Audit",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- decision: `{decision.get('status')}`",
        f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
        f"- recommended_action: `{decision.get('recommended_action')}`",
        f"- prepared_cache: `{cache.get('path')}` rows=`{cache.get('rows')}` date=`{cache.get('date_min')}`..`{cache.get('date_max')}` unique_days=`{cache.get('unique_days')}`",
        "",
        "## Current Best",
    ]
    for market in REQUIRED_MARKETS:
        row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        lines.append(
            f"- {market}: rule=`{row.get('selection_rule')}` validation=`{row.get('validation_mode')}` "
            f"n=`{row.get('n')}` days=`{row.get('active_days')}` runs=`{row.get('active_runs')}` "
            f"hit5=`{row.get('hit5_dd10_5d_pct')}` avg5=`{row.get('avg_5d_pct')}` "
            f"min_low=`{row.get('min_min_low_5d_pct')}` blockers=`{row.get('blockers')}`"
        )
    if research_best:
        lines.append(
            f"- research_only_best: rule=`{research_best.get('selection_rule')}` n=`{research_best.get('n')}` "
            f"days=`{research_best.get('active_days')}` hit5=`{research_best.get('hit5_dd10_5d_pct')}` "
            f"avg5=`{research_best.get('avg_5d_pct')}` min_low=`{research_best.get('min_min_low_5d_pct')}` "
            f"holdout_gate_pass=`{research_best.get('holdout_gate_pass_count')}`"
        )
    lines.extend(
        [
            "",
            "## Month Matrix",
            "| month | KOSPI rows | KOSDAQ rows | status |",
            "|---|---:|---:|---|",
        ]
    )
    period = report.get("period_coverage") if isinstance(report.get("period_coverage"), Mapping) else {}
    for row in period.get("month_market_matrix") or []:
        if not isinstance(row, Mapping):
            continue
        lines.append(f"| {row.get('month')} | {row.get('KOSPI')} | {row.get('KOSDAQ')} | {row.get('status')} |")
    lines.extend(["", "## Feature Families", "| family | columns | avg_present_pct | ablation_required |", "|---|---:|---:|---|"])
    feature = report.get("feature_family_coverage") if isinstance(report.get("feature_family_coverage"), Mapping) else {}
    ablation = feature.get("ablation_status") if isinstance(feature.get("ablation_status"), Mapping) else {}
    for family, row in sorted(ablation.items()):
        if not isinstance(row, Mapping):
            continue
        lines.append(
            f"| {family} | {row.get('column_count')} | {row.get('avg_present_pct')} | {row.get('ablation_required')} |"
        )
    lines.extend(["", "## Required Research Axes"])
    for item in report.get("research_directions") or []:
        if not isinstance(item, Mapping):
            continue
        lines.append(f"- {item.get('axis')}: {item.get('plan')} promotion_rule=`{item.get('promotion_rule')}`")
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report).rstrip() + "\n", encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-cache", default=str(DEFAULT_PREPARED_CACHE))
    parser.add_argument("--candidate-leaderboard", default=str(DEFAULT_LEADERBOARD))
    parser.add_argument("--objective-report", default=str(DEFAULT_OBJECTIVE))
    parser.add_argument("--drawdown-report", default=str(DEFAULT_DRAWDOWN))
    parser.add_argument("--actual-reports", nargs="*", default=[str(path) for path in DEFAULT_ACTUAL_REPORTS])
    parser.add_argument("--proxy-reports", nargs="*", default=[str(path) for path in DEFAULT_PROXY_REPORTS])
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    output = Path(args.output)
    write_report(report, output)
    print(
        json.dumps(
            {
                "status": (report.get("decision") or {}).get("status"),
                "production_replacement_ready": (report.get("decision") or {}).get("production_replacement_ready"),
                "output": _rel(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
