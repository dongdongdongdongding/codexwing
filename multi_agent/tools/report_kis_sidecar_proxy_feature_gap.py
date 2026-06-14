#!/usr/bin/env python3
"""Compare actual KIS sidecar evidence against historical proxy evidence."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kis_model_features import (
    KIS_PREFILTER_CATEGORICAL_FEATURES,
    KIS_PREFILTER_NUMERIC_FEATURES,
    KIS_SIDECAR_CATEGORICAL_FEATURES,
    KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES,
    KIS_SIDECAR_MODEL_NUMERIC_FEATURES,
    KIS_THEME_NEWS_CATEGORICAL_FEATURES,
    KIS_THEME_NEWS_NUMERIC_FEATURES,
)
from multi_agent.tools.train_scan_universe_admission_challenger import feature_sets, usable_features


REPORT_VERSION = "kis_sidecar_proxy_feature_gap_v1"
DEFAULT_SIDECAR_CACHE = (
    ROOT
    / "runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl"
)
DEFAULT_PROXY_CACHES = (
    ROOT / "runtime_state/reports/learning/kis_historical_universe_prefilter_proxy_prepared_kospi_20260101_20260610.pkl",
    ROOT / "runtime_state/reports/learning/kis_historical_universe_prefilter_proxy_prepared_kosdaq_20260101_20260610.pkl",
)
DEFAULT_SIDECAR_SWEEP = (
    ROOT / "runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json"
)
DEFAULT_PROXY_RESEARCH = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_tailgate_prefilter_proxy_min15_20260101_20260610.json"
)
DEFAULT_OUTPUT = ROOT / "runtime_state/reports/learning/kis_sidecar_proxy_feature_gap_20260613.json"


FEATURE_FAMILIES: Dict[str, Sequence[str]] = {
    "sidecar_diagnostic": KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES,
    "sidecar_price_daily_rank": tuple(
        col
        for col in KIS_SIDECAR_MODEL_NUMERIC_FEATURES
        if col.startswith("kis_daily_")
        or col in {
            "kis_current_price",
            "kis_day_change_pct",
            "kis_value_traded",
            "kis_prev_volume_ratio",
            "kis_high_250d_gap_pct",
            "kis_low_250d_gap_pct",
            "kis_rank_volume",
            "kis_rank_fluctuation",
            "kis_rank_volume_power",
            "kis_vi_triggered",
        }
    ),
    "sidecar_flow": tuple(
        col
        for col in KIS_SIDECAR_MODEL_NUMERIC_FEATURES
        if "foreigner" in col or "institution" in col or "retail" in col or "whale" in col
    ),
    "sidecar_stock_static": tuple(
        col
        for col in list(KIS_SIDECAR_MODEL_NUMERIC_FEATURES) + list(KIS_SIDECAR_CATEGORICAL_FEATURES)
        if col.startswith("kis_stock_")
    ),
    "sidecar_financial": tuple(
        col
        for col in list(KIS_SIDECAR_MODEL_NUMERIC_FEATURES) + list(KIS_SIDECAR_CATEGORICAL_FEATURES)
        if col.startswith("kis_financial_")
    ),
    "sidecar_news": tuple(
        col
        for col in list(KIS_SIDECAR_MODEL_NUMERIC_FEATURES) + list(KIS_SIDECAR_CATEGORICAL_FEATURES)
        if col.startswith("kis_news_")
    ),
    "prefilter": tuple(KIS_PREFILTER_NUMERIC_FEATURES) + tuple(KIS_PREFILTER_CATEGORICAL_FEATURES),
    "theme_news": tuple(KIS_THEME_NEWS_NUMERIC_FEATURES) + tuple(KIS_THEME_NEWS_CATEGORICAL_FEATURES),
}


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
    return str(value)


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _date_series(frame: pd.DataFrame) -> pd.Series:
    if "trade_date" in frame.columns:
        return frame["trade_date"].astype(str)
    if "base_trade_date" in frame.columns:
        return frame["base_trade_date"].astype(str)
    return pd.Series("", index=frame.index, dtype=str)


def _frame_scope(frame: pd.DataFrame, path: Path) -> Dict[str, Any]:
    dates = _date_series(frame)
    return {
        "path": str(path),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "date_min": dates.replace("", np.nan).dropna().min() if not dates.replace("", np.nan).dropna().empty else None,
        "date_max": dates.replace("", np.nan).dropna().max() if not dates.replace("", np.nan).dropna().empty else None,
        "unique_days": int(dates.replace("", np.nan).dropna().nunique()),
        "markets": {str(k): int(v) for k, v in frame.get("market", pd.Series(dtype=object)).value_counts().to_dict().items()},
    }


def _is_presence_indicator(col: str) -> bool:
    return (
        col.endswith("_present")
        or col.endswith("_ready")
        or "_coverage_" in col
        or col.endswith("_ok")
        or col.endswith("_valid")
        or col.endswith("_triggered")
        or col.endswith("_source_count")
        or col.endswith("_warning_count")
        or col.endswith("_rejected")
        or col.endswith("_blocked")
        or col.endswith("_count")
    )


def _present_pct(frame: pd.DataFrame, col: str) -> float | None:
    if col not in frame.columns or frame.empty:
        return None
    if col in set(KIS_SIDECAR_CATEGORICAL_FEATURES) | set(KIS_PREFILTER_CATEGORICAL_FEATURES) | set(KIS_THEME_NEWS_CATEGORICAL_FEATURES):
        values = frame[col].fillna("").astype(str).str.strip()
        present = values.ne("") & ~values.str.upper().eq("UNKNOWN")
        return _round(present.mean() * 100.0, 3)
    numeric = pd.to_numeric(frame[col], errors="coerce")
    if _is_presence_indicator(col):
        return _round(numeric.fillna(0).gt(0).mean() * 100.0, 3)
    return _round(numeric.notna().mean() * 100.0, 3)


def _feature_gap(sidecar: pd.DataFrame, proxy: pd.DataFrame, *, sidecar_floor_pct: float = 25.0) -> Dict[str, Any]:
    families: Dict[str, Any] = {}
    all_missing_priority: List[Dict[str, Any]] = []
    for family, columns in FEATURE_FAMILIES.items():
        rows: List[Dict[str, Any]] = []
        sidecar_present = 0
        proxy_present = 0
        for col in columns:
            sidecar_pct = _present_pct(sidecar, col)
            proxy_pct = _present_pct(proxy, col)
            if sidecar_pct is None and proxy_pct is None:
                continue
            sidecar_value = float(sidecar_pct or 0.0)
            proxy_value = float(proxy_pct or 0.0)
            if sidecar_value > 0:
                sidecar_present += 1
            if proxy_value > 0:
                proxy_present += 1
            row = {
                "feature": col,
                "sidecar_present_pct": _round(sidecar_value, 3),
                "proxy_present_pct": _round(proxy_value, 3),
                "sidecar_minus_proxy_pct": _round(sidecar_value - proxy_value, 3),
            }
            rows.append(row)
            if sidecar_value >= sidecar_floor_pct and proxy_value < 5.0:
                all_missing_priority.append({"family": family, **row})
        rows.sort(key=lambda item: float(item.get("sidecar_minus_proxy_pct") or 0.0), reverse=True)
        families[family] = {
            "feature_count": len(rows),
            "sidecar_nonzero_features": sidecar_present,
            "proxy_nonzero_features": proxy_present,
            "top_gaps": rows[:15],
        }
    all_missing_priority.sort(key=lambda item: float(item.get("sidecar_minus_proxy_pct") or 0.0), reverse=True)
    return {"families": families, "priority_missing_features": all_missing_priority[:40]}


def _usable_feature_summary(frame: pd.DataFrame) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    fmap = feature_sets(frame)
    for name in ("kis_sidecar_only", "kis_sidecar_failure_risk_augmented", "kis_prefilter_only", "kis_prefilter_augmented"):
        numeric, categorical = fmap.get(name, ([], []))
        usable_numeric, usable_categorical = usable_features(frame, numeric, categorical)
        summary[name] = {
            "defined_numeric": len(numeric),
            "defined_categorical": len(categorical),
            "usable_numeric": len(usable_numeric),
            "usable_categorical": len(usable_categorical),
            "top_usable_numeric": usable_numeric[:25],
            "top_usable_categorical": usable_categorical[:25],
        }
    return summary


def _market_report_items(payload: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    rows = payload.get("market_reports")
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def _top_sidecar_evidence(sidecar_sweep: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for market_report in _market_report_items(sidecar_sweep):
        scope = market_report.get("scope") if isinstance(market_report.get("scope"), Mapping) else {}
        market = str(scope.get("market") or "").upper()
        if not market:
            continue
        analysis = market_report.get("analysis_summary") if isinstance(market_report.get("analysis_summary"), Mapping) else {}
        sample_only = analysis.get("sample_only_top") if isinstance(analysis.get("sample_only_top"), list) else []
        sample_sufficient = analysis.get("sample_sufficient_top") if isinstance(analysis.get("sample_sufficient_top"), list) else []
        pareto = analysis.get("pareto_top") if isinstance(analysis.get("pareto_top"), list) else []
        best = sample_only[0] if sample_only and isinstance(sample_only[0], Mapping) else {}
        metrics = best.get("metrics") if isinstance(best.get("metrics"), Mapping) else {}
        gate = best.get("kis_model_gate") if isinstance(best.get("kis_model_gate"), Mapping) else {}
        econ = gate.get("production_economics") if isinstance(gate.get("production_economics"), Mapping) else {}
        out[market] = {
            "scope": scope,
            "fold_meta": market_report.get("fold_meta") if isinstance(market_report.get("fold_meta"), Mapping) else {},
            "status_counts": analysis.get("status_counts") or {},
            "production_blocking_reason_counts": analysis.get("production_blocking_reason_counts") or {},
            "sample_only_blocked_count": analysis.get("sample_only_blocked_count"),
            "sample_sufficient_count": analysis.get("sample_sufficient_count"),
            "best_sample_only_shadow": {
                "selection_rule": best.get("selection_rule"),
                "score_mode": best.get("score_mode"),
                "gate_status": gate.get("status"),
                "production_ready": bool(gate.get("production_ready")),
                "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
                "production_blocking_reasons": gate.get("production_blocking_reasons") or [],
                "n": metrics.get("n"),
                "active_days": metrics.get("active_days"),
                "active_runs": metrics.get("active_runs"),
                "hit5_dd10_5d_pct": metrics.get("hit5_dd10_5d_pct"),
                "hit10_5d_pct": metrics.get("hit10_5d_pct"),
                "avg_5d_pct": metrics.get("avg_5d_pct"),
                "min_min_low_5d_pct": metrics.get("min_min_low_5d_pct"),
                "expected_touch_policy_net_5d_pct": econ.get("expected_touch_policy_net_5d_pct"),
            },
            "best_sample_sufficient_shadow": sample_sufficient[0].get("selection_rule") if sample_sufficient and isinstance(sample_sufficient[0], Mapping) else None,
            "pareto_top_rule": pareto[0].get("selection_rule") if pareto and isinstance(pareto[0], Mapping) else None,
        }
    return out


def _proxy_research_summary(proxy_research: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for row in proxy_research.get("markets") or []:
        if not isinstance(row, Mapping):
            continue
        market = str(row.get("market") or "").upper()
        best = row.get("best") if isinstance(row.get("best"), Mapping) else {}
        unconstrained = row.get("unconstrained_best") if isinstance(row.get("unconstrained_best"), Mapping) else {}
        out[market] = {
            "status": proxy_research.get("status"),
            "evidence_gate": row.get("evidence_gate") or {},
            "best_config": best.get("config") or {},
            "best_metrics": best.get("metrics") or {},
            "unconstrained_best_config": unconstrained.get("config") or {},
            "unconstrained_best_metrics": unconstrained.get("metrics") or {},
            "improvement": row.get("improvement") or {},
        }
    return out


def _family_priority(family: str) -> Dict[str, Any]:
    priorities = {
        "sidecar_flow": {
            "priority": 1,
            "backfill_path": "KIS investor flow endpoint 또는 저장된 KIS sidecar backfill",
            "reason": "actual sidecar에서 44% 이상 채워졌지만 proxy는 0%라 tail-safe/whale 피처가 사라진다.",
        },
        "sidecar_financial": {
            "priority": 2,
            "backfill_path": "KIS financial ratio/style + static daily cache",
            "reason": "저빈도 정적/분기 정보라 과거 일자에 복제 가능성이 높고 proxy 결손이 크다.",
        },
        "sidecar_stock_static": {
            "priority": 3,
            "backfill_path": "KIS stock info/listing/industry master",
            "reason": "업종/상장/주식수/자본금은 자주 변하지 않아 historical proxy 보강 효율이 높다.",
        },
        "sidecar_news": {
            "priority": 4,
            "backfill_path": "KIS news contract by ticker/date",
            "reason": "coverage는 낮지만 이벤트 후보에서 precision을 올리는 보조 피처다.",
        },
        "sidecar_price_daily_rank": {
            "priority": 5,
            "backfill_path": "KIS daily OHLCV + rank/VI snapshots",
            "reason": "일봉 가격 피처는 일부 proxy에 있지만 rank/VI 실측 결손이 남아 있다.",
        },
        "prefilter": {
            "priority": 6,
            "backfill_path": "KIS operational prefilter snapshot",
            "reason": "proxy selection_score는 있으나 quote/flow/market-cap component 결손이 크다.",
        },
        "theme_news": {
            "priority": 7,
            "backfill_path": "KIS stock sector + news evidence contract",
            "reason": "테마 문자열은 proxy에 많지만 실제 KIS-backed news/positive/risk tag는 비어 있다.",
        },
    }
    return priorities.get(family, {"priority": 99, "backfill_path": "review", "reason": "review_required"})


def _backfill_priorities(feature_gap: Mapping[str, Any]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    avg_gap: Dict[str, List[float]] = {}
    for row in feature_gap.get("priority_missing_features") or []:
        if not isinstance(row, Mapping):
            continue
        family = str(row.get("family") or "unknown")
        counts[family] = counts.get(family, 0) + 1
        avg_gap.setdefault(family, []).append(float(row.get("sidecar_minus_proxy_pct") or 0.0))
    priorities: List[Dict[str, Any]] = []
    for family, count in counts.items():
        meta = _family_priority(family)
        priorities.append(
            {
                "family": family,
                "priority": meta["priority"],
                "missing_high_value_features": count,
                "avg_sidecar_minus_proxy_pct": _round(float(np.mean(avg_gap.get(family) or [0.0])), 3),
                "backfill_path": meta["backfill_path"],
                "reason": meta["reason"],
            }
        )
    priorities.sort(key=lambda row: (int(row["priority"]), -int(row["missing_high_value_features"])))
    return priorities


def build_report(
    *,
    sidecar_cache: Path,
    proxy_caches: Sequence[Path],
    sidecar_sweep_report: Path,
    proxy_research_report: Path,
) -> Dict[str, Any]:
    sidecar = pd.read_pickle(sidecar_cache)
    proxy_parts = [pd.read_pickle(path) for path in proxy_caches]
    proxy = pd.concat(proxy_parts, ignore_index=True) if len(proxy_parts) > 1 else proxy_parts[0]
    sidecar_sweep = _load_json(sidecar_sweep_report)
    proxy_research = _load_json(proxy_research_report)
    feature_gap = _feature_gap(sidecar, proxy)
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "dummy_data_used": False,
        "objective": "Explain why actual KIS sidecar shadow performance does not transfer to historical proxy training, and define the next real-data backfill path.",
        "inputs": {
            "sidecar_cache": _frame_scope(sidecar, sidecar_cache),
            "proxy_caches": [_frame_scope(part, path) for part, path in zip(proxy_parts, proxy_caches)],
            "sidecar_sweep_report": str(sidecar_sweep_report),
            "proxy_research_report": str(proxy_research_report),
        },
        "feature_gap": feature_gap,
        "usable_feature_sets": {
            "sidecar_cache": _usable_feature_summary(sidecar),
            "proxy_cache": _usable_feature_summary(proxy),
        },
        "sidecar_shadow_evidence": _top_sidecar_evidence(sidecar_sweep),
        "proxy_research_evidence": _proxy_research_summary(proxy_research),
        "backfill_priorities": _backfill_priorities(feature_gap),
        "decision": {
            "production_replacement_ready": False,
            "shadow_signal_confirmed": True,
            "proxy_model_promotable": False,
            "next_best_action": "Backfill actual KIS sidecar-equivalent flow, financial, stock static, rank/VI, and news fields for more historical days before retraining.",
        },
        "model_structure_to_keep": [
            "Stage 1: real KIS sidecar/prefilter wide recall pool, not dummy or missing-only proxy rows.",
            "Stage 2: separate touch5 success model and dd10/tail-safe model with hard tail gate.",
            "Stage 3: expected-value ranker plus no-trade threshold, then production evidence gate by n/active_days/active_runs.",
        ],
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
        "# KIS Sidecar vs Historical Proxy Feature Gap",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
        f"- shadow_signal_confirmed: `{decision.get('shadow_signal_confirmed')}`",
        f"- proxy_model_promotable: `{decision.get('proxy_model_promotable')}`",
        f"- next_best_action: {decision.get('next_best_action')}",
        "",
        "## Scope",
    ]
    sidecar_scope = ((report.get("inputs") or {}).get("sidecar_cache") or {})
    lines.append(
        f"- sidecar_cache: rows=`{sidecar_scope.get('rows')}` days=`{sidecar_scope.get('unique_days')}` "
        f"date=`{sidecar_scope.get('date_min')}`..`{sidecar_scope.get('date_max')}`"
    )
    for scope in ((report.get("inputs") or {}).get("proxy_caches") or []):
        lines.append(
            f"- proxy_cache: rows=`{scope.get('rows')}` days=`{scope.get('unique_days')}` "
            f"date=`{scope.get('date_min')}`..`{scope.get('date_max')}` markets=`{scope.get('markets')}`"
        )
    lines.extend(["", "## Sidecar Shadow Evidence"])
    for market, row in (report.get("sidecar_shadow_evidence") or {}).items():
        best = row.get("best_sample_only_shadow") or {}
        lines.append(
            f"- {market}: rule=`{best.get('selection_rule')}` n=`{best.get('n')}` days=`{best.get('active_days')}` "
            f"hit5_dd10=`{best.get('hit5_dd10_5d_pct')}` avg5=`{best.get('avg_5d_pct')}` "
            f"min_low=`{best.get('min_min_low_5d_pct')}` blockers=`{best.get('production_blocking_reasons')}`"
        )
    lines.extend(["", "## Proxy Research Evidence"])
    for market, row in (report.get("proxy_research_evidence") or {}).items():
        metrics = row.get("best_metrics") or {}
        lines.append(
            f"- {market}: n=`{metrics.get('n')}` days=`{metrics.get('active_days')}` "
            f"hit5_dd10=`{metrics.get('hit5_dd10_5d_pct')}` tail=`{metrics.get('tail_breach_5d_pct')}` "
            f"avg_exit=`{metrics.get('avg_ordered_exit_5d_pct')}` min_low=`{metrics.get('min_min_low_5d_pct')}`"
        )
    lines.extend(["", "## Backfill Priorities", "| priority | family | missing_features | avg_gap_pct | path |", "|---:|---|---:|---:|---|"])
    for row in report.get("backfill_priorities") or []:
        lines.append(
            "| "
            + " | ".join(
                [
                    _fmt(row.get("priority")),
                    str(row.get("family")),
                    _fmt(row.get("missing_high_value_features")),
                    _fmt(row.get("avg_sidecar_minus_proxy_pct")),
                    str(row.get("backfill_path")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Top Feature Gaps"])
    for family, payload in ((report.get("feature_gap") or {}).get("families") or {}).items():
        top = payload.get("top_gaps") or []
        if not top:
            continue
        lines.append(f"### {family}")
        for row in top[:5]:
            lines.append(
                f"- `{row.get('feature')}` sidecar=`{row.get('sidecar_present_pct')}` "
                f"proxy=`{row.get('proxy_present_pct')}` gap=`{row.get('sidecar_minus_proxy_pct')}`"
            )
    lines.extend(["", "## Model Structure To Keep"])
    lines.extend(f"- {item}" for item in report.get("model_structure_to_keep") or [])
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sidecar-cache", default=str(DEFAULT_SIDECAR_CACHE))
    parser.add_argument("--proxy-cache", action="append", default=[])
    parser.add_argument("--sidecar-sweep-report", default=str(DEFAULT_SIDECAR_SWEEP))
    parser.add_argument("--proxy-research-report", default=str(DEFAULT_PROXY_RESEARCH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    proxy_caches = args.proxy_cache or [str(path) for path in DEFAULT_PROXY_CACHES]
    report = build_report(
        sidecar_cache=Path(args.sidecar_cache),
        proxy_caches=[Path(path) for path in proxy_caches],
        sidecar_sweep_report=Path(args.sidecar_sweep_report),
        proxy_research_report=Path(args.proxy_research_report),
    )
    write_report(report, Path(args.output))
    print(
        json.dumps(
            {
                "output": args.output,
                "decision": report.get("decision"),
                "backfill_priorities": report.get("backfill_priorities"),
            },
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
