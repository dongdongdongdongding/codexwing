#!/usr/bin/env python3
"""Track pinned feature-combination watch candidates.

This report is deliberately narrower than the feature-combination miner. The
miner searches for new rules; this file tracks specific near-miss candidates
that must mature forward before any production scanner change is considered.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.run_internal_retrain_sweep import (
    DEFAULT_INPUT,
    _cohort_masks,
    _json_default,
    _label,
    _load_dataset,
    _metrics,
    _split_days,
)


REPORT_VERSION = "feature_combo_watchlist_v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/experimental/feature_combo_watchlist_latest.json"

WATCH_RULES: Tuple[Dict[str, Any], ...] = (
    {
        "rule_id": "kospi_exact_path_low_alpha_low_ml_top5_exception",
        "issue_id": "swing-main-n7og",
        "market": "KOSPI",
        "scope": "top5_exception",
        "quality_scope": "exact_path",
        "horizon": "5d",
        "train_ratio": 0.65,
        "conditions": [
            {"feature": "alpha_score", "op": "<=", "value": 67.0},
            {"feature": "ml_prob", "op": "<=", "value": 30.45},
        ],
        "gate": {
            "min_train_n": 18,
            "min_train_days": 6,
            "min_train_win_5d_pct": 70.0,
            "min_test_n": 8,
            "min_test_days": 5,
            "min_test_win_5d_pct": 75.0,
            "min_test_avg_5d_pct": 5.0,
            "max_test_bad_path_pct": 25.0,
            "max_test_stop5_pct": 10.0,
        },
        "note": "Relaxed exact-path near-miss found on 2026-05-27; forward-track only.",
    },
)


def _bool_series(value: pd.Series) -> pd.Series:
    if value.dtype == bool:
        return value.fillna(False)
    return value.fillna("").astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def _condition_mask(df: pd.DataFrame, condition: Dict[str, Any]) -> Tuple[pd.Series, str | None]:
    feature = str(condition.get("feature") or "").strip()
    op = str(condition.get("op") or "").strip()
    value = condition.get("value")
    if feature not in df.columns:
        return pd.Series(False, index=df.index), feature
    series = pd.to_numeric(df[feature], errors="coerce")
    threshold = float(value)
    if op == "<=":
        return series.le(threshold).fillna(False), None
    if op == ">=":
        return series.ge(threshold).fillna(False), None
    if op == "==":
        return df[feature].fillna("").astype(str).eq(str(value)), None
    raise ValueError(f"unsupported operator for watch rule: {op}")


def _apply_quality_scope(df: pd.DataFrame, quality_scope: str) -> pd.DataFrame:
    scope = str(quality_scope or "all").strip().lower()
    if scope in {"", "all"}:
        return df
    if scope in {"exact_path", "ordered_path_exact"}:
        if "ordered_path_exact" not in df.columns:
            return df.iloc[0:0].copy()
        return df.loc[_bool_series(df["ordered_path_exact"])].copy()
    raise ValueError(f"unsupported quality_scope: {quality_scope}")


def _gate_check(name: str, actual: Any, expected: str, passed: bool) -> Dict[str, Any]:
    return {"name": name, "actual": actual, "expected": expected, "passed": bool(passed)}


def _status(metrics: Dict[str, Any], train: Dict[str, Any], test: Dict[str, Any], gate: Dict[str, Any], missing: Sequence[str]) -> Tuple[str, List[Dict[str, Any]]]:
    if missing:
        return "blocked_missing_feature", [_gate_check("missing_features", sorted(set(missing)), "none", False)]
    checks = [
        _gate_check("train_n", train.get("n"), f">={gate.get('min_train_n')}", int(train.get("n") or 0) >= int(gate.get("min_train_n") or 0)),
        _gate_check("train_days", train.get("active_days"), f">={gate.get('min_train_days')}", int(train.get("active_days") or 0) >= int(gate.get("min_train_days") or 0)),
        _gate_check(
            "train_win_5d",
            train.get("win_5d_pct"),
            f">={gate.get('min_train_win_5d_pct')}%",
            float(train.get("win_5d_pct") or 0.0) >= float(gate.get("min_train_win_5d_pct") or 0.0),
        ),
        _gate_check("test_n", test.get("n"), f">={gate.get('min_test_n')}", int(test.get("n") or 0) >= int(gate.get("min_test_n") or 0)),
        _gate_check("test_days", test.get("active_days"), f">={gate.get('min_test_days')}", int(test.get("active_days") or 0) >= int(gate.get("min_test_days") or 0)),
        _gate_check(
            "test_win_5d",
            test.get("win_5d_pct"),
            f">={gate.get('min_test_win_5d_pct')}%",
            float(test.get("win_5d_pct") or 0.0) >= float(gate.get("min_test_win_5d_pct") or 0.0),
        ),
        _gate_check(
            "test_avg_5d",
            test.get("avg_5d_pct"),
            f">={gate.get('min_test_avg_5d_pct')}%",
            float(test.get("avg_5d_pct") or -999.0) >= float(gate.get("min_test_avg_5d_pct") or 0.0),
        ),
        _gate_check(
            "test_bad_path",
            test.get("bad_path_pct"),
            f"<={gate.get('max_test_bad_path_pct')}%",
            float(test.get("bad_path_pct") if test.get("bad_path_pct") is not None else 100.0) <= float(gate.get("max_test_bad_path_pct") or 100.0),
        ),
        _gate_check(
            "test_stop5",
            test.get("stop5_pct"),
            f"<={gate.get('max_test_stop5_pct')}%",
            float(test.get("stop5_pct") if test.get("stop5_pct") is not None else 100.0) <= float(gate.get("max_test_stop5_pct") or 100.0),
        ),
    ]
    if all(item["passed"] for item in checks):
        return "review_candidate", checks
    if int(test.get("n") or 0) < int(gate.get("min_test_n") or 0) or int(test.get("active_days") or 0) < int(gate.get("min_test_days") or 0):
        return "watch_insufficient_forward_sample", checks
    if int(metrics.get("n") or 0) == 0:
        return "watch_no_current_matches", checks
    return "watch_failed_current_gate", checks


def evaluate_watch_rules(df: pd.DataFrame, rules: Sequence[Dict[str, Any]] = WATCH_RULES) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rule in rules:
        market = str(rule.get("market") or "").upper()
        scoped = df.loc[df.get("market2", pd.Series("", index=df.index)).fillna("").astype(str).str.upper().eq(market)].copy()
        scoped = _apply_quality_scope(scoped, str(rule.get("quality_scope") or "all"))
        masks = _cohort_masks(scoped)
        scope_name = str(rule.get("scope") or "all")
        scope_mask = masks.get(scope_name, pd.Series(False, index=scoped.index)).fillna(False)
        scoped = scoped.loc[scope_mask].copy()
        split_train, split_test, cut_day = _split_days(scoped, float(rule.get("train_ratio") or 0.65))
        selected = pd.Series(True, index=scoped.index)
        missing: List[str] = []
        for condition in rule.get("conditions") or []:
            mask, missing_feature = _condition_mask(scoped, condition)
            if missing_feature:
                missing.append(missing_feature)
            selected &= mask.fillna(False)
        selected_idx = scoped.index[selected.fillna(False)]
        label, _valid = _label(scoped, "win_5d_pos")
        all_metrics = _metrics(scoped, selected_idx, label)
        train_metrics = _metrics(scoped, selected_idx.intersection(scoped.index[split_train.fillna(False)]), label)
        test_metrics = _metrics(scoped, selected_idx.intersection(scoped.index[split_test.fillna(False)]), label)
        status, checks = _status(all_metrics, train_metrics, test_metrics, dict(rule.get("gate") or {}), missing)
        rows.append(
            {
                "rule_id": rule.get("rule_id"),
                "issue_id": rule.get("issue_id"),
                "market": market,
                "scope": scope_name,
                "quality_scope": rule.get("quality_scope") or "all",
                "horizon": rule.get("horizon") or "5d",
                "cut_day": cut_day,
                "conditions": list(rule.get("conditions") or []),
                "missing_features": sorted(set(missing)),
                "all": all_metrics,
                "train": train_metrics,
                "test": test_metrics,
                "gate_checks": checks,
                "status": status,
                "note": rule.get("note"),
            }
        )
    return rows


def build_report(input_path: Path = DEFAULT_INPUT) -> Dict[str, Any]:
    df = _load_dataset(input_path)
    rows = evaluate_watch_rules(df)
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "production_scanner_changed": False,
        "rules": rows,
        "summary": {
            "rule_count": len(rows),
            "review_candidate_count": sum(1 for row in rows if row.get("status") == "review_candidate"),
            "insufficient_forward_sample_count": sum(1 for row in rows if row.get("status") == "watch_insufficient_forward_sample"),
        },
        "notes": [
            "Pinned candidate tracking only; this report does not search new rules.",
            "review_candidate still requires manual release review before scanner changes.",
        ],
    }


def _metric_text(metric: Dict[str, Any]) -> str:
    if not metric or not metric.get("n"):
        return "n=0"
    return (
        f"n={metric.get('n')} days={metric.get('active_days')} "
        f"win5={metric.get('win_5d_pct')}% avg5={metric.get('avg_5d_pct')}% "
        f"min5={metric.get('min_5d_pct')}% bad={metric.get('bad_path_pct')}% stop={metric.get('stop5_pct')}%"
    )


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Feature Combo Watchlist",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        "- production_scanner_changed: `False`",
        f"- review_candidate_count: `{report.get('summary', {}).get('review_candidate_count')}`",
        "",
        "| Rule | Issue | Status | Market | Scope | All | Train | Test | Conditions |",
        "|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in report.get("rules") or []:
        conditions = "; ".join(
            f"{item.get('feature')} {item.get('op')} {item.get('value')}"
            for item in row.get("conditions") or []
            if isinstance(item, dict)
        )
        lines.append(
            "| "
            f"{row.get('rule_id')} | {row.get('issue_id')} | {row.get('status')} | "
            f"{row.get('market')} | {row.get('scope')} / {row.get('quality_scope')} | "
            f"{_metric_text(row.get('all') or {})} | "
            f"{_metric_text(row.get('train') or {})} | "
            f"{_metric_text(row.get('test') or {})} | "
            f"{conditions} |"
        )
    lines.extend(["", "## Gate Checks", ""])
    for row in report.get("rules") or []:
        lines.append(f"### {row.get('rule_id')}")
        for check in row.get("gate_checks") or []:
            mark = "PASS" if check.get("passed") else "FAIL"
            lines.append(f"- {check.get('name')}: `{mark}` actual `{check.get('actual')}` expected `{check.get('expected')}`")
        lines.append("")
    lines.extend(["## Notes", ""])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Track pinned feature-combination watch candidates.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output_path = Path(args.output)
    report = build_report(Path(args.input))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    md_path = output_path.with_suffix(".md")
    write_markdown(report, md_path)
    print(json.dumps({"json_path": str(output_path), "md_path": str(md_path), "rules": len(report.get("rules") or [])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
