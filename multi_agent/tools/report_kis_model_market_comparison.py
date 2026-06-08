#!/usr/bin/env python3
"""Build a KOSPI/KOSDAQ comparison report for production Top-N vs KIS challenger.

This report intentionally uses completed challenger artifacts instead of running
another full Supabase scan. It is for operator review, not model promotion.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kis_model_gate import evaluate_kis_model_gate

REPORT_VERSION = "kis_model_market_comparison_v2_kis_gate"
DEFAULT_OUTPUT = ROOT / "runtime_state" / "reports" / "learning" / "kis_model_market_comparison.json"
DEFAULT_SOURCES = {
    "KOSPI": ROOT
    / "runtime_state"
    / "reports"
    / "learning"
    / "scan_universe_admission_challenger_after_full_kis_sidecar_backfill.json",
    "KOSDAQ": ROOT
    / "runtime_state"
    / "reports"
    / "learning"
    / "scan_universe_admission_challenger_kosdaq_after_20260526_27_backfill.json",
}
HORIZONS = ("1d", "3d", "5d")
BASELINES = ("current_top1", "current_top3", "current_top5")


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _metric_subset(metrics: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "n": metrics.get("n"),
        "active_days": metrics.get("active_days"),
        "active_runs": metrics.get("active_runs"),
    }
    for horizon in HORIZONS:
        out[f"win_{horizon}_pct"] = metrics.get(f"win_{horizon}_pct")
        out[f"avg_{horizon}_pct"] = metrics.get(f"avg_{horizon}_pct")
        out[f"min_{horizon}_pct"] = metrics.get(f"min_{horizon}_pct")
        out[f"max_{horizon}_pct"] = metrics.get(f"max_{horizon}_pct")
    out["avg_max_high_5d_pct"] = metrics.get("avg_max_high_5d_pct")
    out["min_min_low_5d_pct"] = metrics.get("min_min_low_5d_pct")
    out["max_min_low_5d_pct"] = metrics.get("max_min_low_5d_pct")
    out["bad_path_pct"] = metrics.get("bad_path_pct")
    out["stop5_pct"] = metrics.get("stop5_pct")
    out["target_before_stop_5d_pct"] = metrics.get("target_before_stop_5d_pct")
    out["stop_before_target_5d_pct"] = metrics.get("stop_before_target_5d_pct")
    out["hit5_5d_pct"] = metrics.get("hit5_5d_pct")
    out["hit10_5d_pct"] = metrics.get("hit10_5d_pct")
    out["hit5_guard_5d_pct"] = metrics.get("hit5_guard_5d_pct")
    out["hit10_guard_5d_pct"] = metrics.get("hit10_guard_5d_pct")
    return out


def _model_identity(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "market": row.get("market"),
        "label": row.get("label"),
        "feature_set": row.get("feature_set"),
        "model": row.get("model"),
        "topn": row.get("topn"),
        "prob_threshold": row.get("prob_threshold"),
        "selection_rule": row.get("selection_rule"),
        "quality_score": row.get("quality_score"),
        "promotion_candidate": row.get("promotion_candidate"),
        "risk_gate": row.get("risk_gate"),
    }


def _path_text(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _baseline_rows(report: Dict[str, Any], market: str) -> List[Dict[str, Any]]:
    rows = report.get("baselines_for_best_kis_holdout") or report.get("baselines_for_best_holdout") or []
    out = []
    for row in rows if isinstance(rows, list) else []:
        if row.get("market") != market or row.get("baseline") not in BASELINES:
            continue
        out.append(
            {
                "kind": "existing_production",
                "market": market,
                "name": row.get("baseline"),
                "label": row.get("label"),
                "topn": row.get("topn"),
                "metrics": _metric_subset(row.get("metrics") or {}),
            }
        )
    return out


def build_report(sources: Dict[str, Path]) -> Dict[str, Any]:
    markets: Dict[str, Any] = {}
    warnings: List[str] = []
    for market, path in sources.items():
        report = _load_json(path)
        best_kis = report.get("best_kis") or {}
        if best_kis.get("market") != market:
            warnings.append(f"{market}: best_kis market mismatch or missing in {path}")
        identity = _model_identity(best_kis)
        metrics = _metric_subset(best_kis.get("metrics") or {})
        kis_model_gate = evaluate_kis_model_gate(identity=identity, metrics=metrics, market=market)
        markets[market] = {
            "source_path": _path_text(path),
            "source_generated_at": report.get("generated_at"),
            "source_raw_rows": report.get("raw_rows"),
            "source_prepared_rows": report.get("prepared_rows"),
            "source_evaluated_combinations": report.get("evaluated_combinations"),
            "source_ok_combinations": report.get("ok_combinations"),
            "current_kis_model": {
                "kind": "current_kis_challenger",
                "identity": identity,
                "metrics": metrics,
                "kis_model_gate": kis_model_gate,
            },
            "existing_production_baselines": _baseline_rows(report, market),
        }
    return {
        "version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "horizons": list(HORIZONS),
        "metric_contract": "2d is intentionally excluded; report uses completed 1d/3d/5d scan_universe outcome labels only.",
        "markets": markets,
        "warnings": warnings,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _metric_line(metrics: Dict[str, Any]) -> str:
    chunks = []
    for horizon in HORIZONS:
        chunks.append(
            f"{horizon} 승률/평균/최저/최고 "
            f"{_fmt(metrics.get(f'win_{horizon}_pct'))}%/"
            f"{_fmt(metrics.get(f'avg_{horizon}_pct'))}%/"
            f"{_fmt(metrics.get(f'min_{horizon}_pct'))}%/"
            f"{_fmt(metrics.get(f'max_{horizon}_pct'))}%"
        )
    return "; ".join(chunks)


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# KIS Model Market Comparison",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- metric_contract: `{report.get('metric_contract')}`",
        "",
    ]
    for market, payload in (report.get("markets") or {}).items():
        current = payload.get("current_kis_model") or {}
        ident = current.get("identity") or {}
        metrics = current.get("metrics") or {}
        kis_gate = current.get("kis_model_gate") or {}
        lines.extend(
            [
                f"## {market}",
                f"- source: `{payload.get('source_path')}`",
                f"- source_generated_at: `{payload.get('source_generated_at')}`",
                f"- current_kis: `{ident.get('label')}` / `{ident.get('feature_set')}` / `{ident.get('model')}` / `{ident.get('selection_rule')}`",
                f"- current_kis sample: n=`{metrics.get('n')}`, active_days=`{metrics.get('active_days')}`, active_runs=`{metrics.get('active_runs')}`",
                f"- current_kis returns: {_metric_line(metrics)}",
                f"- current_kis 5d path: avg_max_high=`{_fmt(metrics.get('avg_max_high_5d_pct'))}%`, min_low=`{_fmt(metrics.get('min_min_low_5d_pct'))}%`, max_low=`{_fmt(metrics.get('max_min_low_5d_pct'))}%`",
                f"- kis_model_gate: status=`{kis_gate.get('status')}`, production_ready=`{kis_gate.get('production_ready')}`, shadow_display_allowed=`{kis_gate.get('shadow_display_allowed')}`, risk_review_required=`{kis_gate.get('risk_review_required')}`",
                f"- kis_model_gate blockers: `{kis_gate.get('production_blocking_reasons') or []}`",
                "",
                "| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |",
                "|---|---:|---:|---|---|---|---|",
            ]
        )
        for row in payload.get("existing_production_baselines") or []:
            m = row.get("metrics") or {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("name")),
                        _fmt(m.get("n")),
                        _fmt(m.get("active_days")),
                        f"{_fmt(m.get('win_1d_pct'))}%/{_fmt(m.get('avg_1d_pct'))}%/{_fmt(m.get('min_1d_pct'))}%/{_fmt(m.get('max_1d_pct'))}%",
                        f"{_fmt(m.get('win_3d_pct'))}%/{_fmt(m.get('avg_3d_pct'))}%/{_fmt(m.get('min_3d_pct'))}%/{_fmt(m.get('max_3d_pct'))}%",
                        f"{_fmt(m.get('win_5d_pct'))}%/{_fmt(m.get('avg_5d_pct'))}%/{_fmt(m.get('min_5d_pct'))}%/{_fmt(m.get('max_5d_pct'))}%",
                        f"{_fmt(m.get('avg_max_high_5d_pct'))}%/{_fmt(m.get('min_min_low_5d_pct'))}%",
                    ]
                )
                + " |"
            )
        lines.append("")
    if report.get("warnings"):
        lines.extend(["## Warnings", *[f"- {item}" for item in report["warnings"]], ""])
    return "\n".join(lines)


def write_report(report: Dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    output.with_suffix(".md").write_text(_markdown(report), encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kospi-source", default=str(DEFAULT_SOURCES["KOSPI"]))
    parser.add_argument("--kosdaq-source", default=str(DEFAULT_SOURCES["KOSDAQ"]))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = build_report(
        {
            "KOSPI": Path(args.kospi_source),
            "KOSDAQ": Path(args.kosdaq_source),
        }
    )
    write_report(report, Path(args.output))
    print(json.dumps({"output": str(args.output), "markets": sorted(report["markets"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
