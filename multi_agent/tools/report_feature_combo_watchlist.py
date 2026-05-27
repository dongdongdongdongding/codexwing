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
MAX_REFINEMENT_CANDIDATES = 8

REFINEMENT_EXCLUDED_FEATURES = {
    "id",
    "ticker",
    "stock_name",
    "created_at",
    "recommended_at",
    "outcome_recorded_at",
    "base_trade_date",
    "source_ref",
    "rationale",
    "strategy",
    "is_dummy_data",
    "validation_excluded",
    "priority_rank",
    "entry_reference_price",
    "scan_entry_reference_price",
    "return_1d_pct",
    "return_2d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_7d_pct",
    "return_14d_pct",
    "return_30d_pct",
    "return_10m_pct",
    "return_30m_pct",
    "return_1h_pct",
    "return_close_pct",
    "latest_return_pct",
    "max_high_return_5d_pct",
    "max_return_observed_pct",
    "min_return_observed_pct",
    "mfe_intraday_pct",
    "mae_intraday_pct",
    "mfe_5d_pct",
    "mae_5d_pct",
    "hit_5pct_within_5d",
    "hit_5pct_within_5d_at",
    "target_before_stop_5d",
    "stop_before_target_5d",
    "target_hit_at_5d",
    "stop_hit_at_5d",
    "label_hit_5pct_within_5d",
    "label_win_close",
    "label_win_1d",
    "label_win_3d",
    "label_hit_5pct",
    "label_hit_10pct",
    "label_hit_20pct",
    "label_hit_50pct",
    "label_hit_100pct",
    "label_stop_loss_3pct",
    "label_stop_loss_5pct",
    "outcome_status",
    "outcome_path_terminal_status",
    "outcome_path_label_version",
    "outcome_path_bar_count",
    "outcome_path_source",
    "outcome_path_warnings",
    "performance_updated_at",
    "target_definition",
    "target_return_source",
    "ordered_entry_at",
    "ordered_entry_price",
    "ordered_target_hit_at",
    "ordered_stop_hit_at",
    "ordered_mfe_until_terminal_5d_pct",
    "ordered_mae_until_terminal_5d_pct",
    "ordered_mae_before_target_5d_pct",
    "ordered_path_exact",
    "stop5_proxy",
    "bad_path",
}

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


def _with_path_breakdown(df: pd.DataFrame, idx: pd.Index, metrics: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(metrics)
    sub = df.loc[idx]
    if sub.empty:
        out.update({"early_drop_1d_pct": None, "loss_5d_pct": None, "avg_min_path_pct": None, "min_path_pct": None})
        return out
    ret1 = pd.to_numeric(sub.get("return_1d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce")
    ret5 = pd.to_numeric(sub.get("return_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce")
    min_path = pd.to_numeric(sub.get("min_return_observed_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce")
    out["early_drop_1d_pct"] = round(float(ret1.lt(-3.0).mean() * 100.0), 3) if ret1.notna().any() else None
    out["loss_5d_pct"] = round(float(ret5.lt(0.0).mean() * 100.0), 3) if ret5.notna().any() else None
    out["avg_min_path_pct"] = round(float(min_path.mean()), 4) if min_path.notna().any() else None
    out["min_path_pct"] = round(float(min_path.min()), 4) if min_path.notna().any() else None
    return out


def _metric_float(metric: Dict[str, Any], key: str, default: float) -> float:
    value = metric.get(key)
    try:
        if value is None:
            return default
        result = float(value)
        if result != result:
            return default
        return result
    except Exception:
        return default


def _eligible_feature(feature: str, base_condition_features: Sequence[str]) -> bool:
    if feature in REFINEMENT_EXCLUDED_FEATURES:
        return False
    if feature in set(base_condition_features):
        return False
    if feature.endswith("_bool"):
        return False
    if feature.startswith("label_") or feature.startswith("return_"):
        return False
    return True


def _candidate_numeric_features(df: pd.DataFrame, base_condition_features: Sequence[str]) -> List[str]:
    cols: List[str] = []
    for col in df.columns:
        if not _eligible_feature(str(col), base_condition_features):
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.notna().sum() >= 8 and numeric.nunique(dropna=True) >= 2:
            cols.append(str(col))
    return cols


def _candidate_categorical_features(df: pd.DataFrame, base_condition_features: Sequence[str]) -> List[str]:
    cols: List[str] = []
    for col in df.columns:
        if not _eligible_feature(str(col), base_condition_features):
            continue
        if col in _candidate_numeric_features(df[[col]], []):
            continue
        values = df[col].fillna("").astype(str).str.strip()
        nunique = values.loc[values.ne("")].nunique(dropna=True)
        if 2 <= nunique <= 24:
            cols.append(str(col))
    return cols


def _condition_label(condition: Dict[str, Any]) -> str:
    return f"{condition.get('feature')} {condition.get('op')} {condition.get('value')}"


def _refinement_status(train: Dict[str, Any], test: Dict[str, Any]) -> str:
    train_n = int(train.get("n") or 0)
    test_n = int(test.get("n") or 0)
    test_days = int(test.get("active_days") or 0)
    train_win = _metric_float(train, "win_5d_pct", 0.0)
    test_win = _metric_float(test, "win_5d_pct", 0.0)
    test_avg = _metric_float(test, "avg_5d_pct", -999.0)
    test_bad = _metric_float(test, "bad_path_pct", 100.0)
    test_stop = _metric_float(test, "stop5_pct", 100.0)
    if (
        train_n >= 12
        and test_n >= 8
        and test_days >= 5
        and train_win >= 70.0
        and test_win >= 75.0
        and test_avg >= 5.0
        and test_bad <= 25.0
        and test_stop <= 10.0
    ):
        return "strict_refinement_candidate"
    if (
        train_n >= 8
        and test_n >= 5
        and test_days >= 4
        and train_win >= 70.0
        and test_win >= 75.0
        and test_avg >= 5.0
        and test_bad <= 25.0
        and test_stop <= 10.0
    ):
        return "watch_refinement_candidate"
    return "diagnostic_only"


def _score_refinement(base_test: Dict[str, Any], train: Dict[str, Any], test: Dict[str, Any]) -> float:
    base_bad = _metric_float(base_test, "bad_path_pct", 100.0)
    base_drop = _metric_float(base_test, "early_drop_1d_pct", 100.0)
    bad_improvement = base_bad - _metric_float(test, "bad_path_pct", 100.0)
    drop_improvement = base_drop - _metric_float(test, "early_drop_1d_pct", 100.0)
    return round(
        bad_improvement * 3.0
        + drop_improvement * 2.0
        + _metric_float(test, "win_5d_pct", 0.0) * 0.25
        + _metric_float(test, "avg_5d_pct", -20.0) * 0.5
        - max(0.0, 70.0 - _metric_float(train, "win_5d_pct", 0.0))
        + min(10.0, float(test.get("n") or 0)),
        4,
    )


def _refinement_candidates(
    scoped: pd.DataFrame,
    *,
    selected_idx: pd.Index,
    train_base_idx: pd.Index,
    test_base_idx: pd.Index,
    label: pd.Series,
    base_test: Dict[str, Any],
    base_condition_features: Sequence[str],
) -> List[Dict[str, Any]]:
    if len(selected_idx) == 0 or len(train_base_idx) == 0 or len(test_base_idx) == 0:
        return []
    predicates: List[Tuple[Dict[str, Any], pd.Series]] = []
    train_selected = scoped.loc[train_base_idx]
    for feature in _candidate_numeric_features(scoped.loc[selected_idx], base_condition_features):
        values = pd.to_numeric(train_selected.get(feature, pd.Series(dtype=float)), errors="coerce").astype(float).dropna()
        if len(values) < 6:
            continue
        thresholds = {
            round(float(value), 4)
            for value in values.quantile([0.25, 0.5, 0.75]).dropna().tolist()
            if value == value
        }
        if feature in {"day_return_pct", "volume_ratio", "expected_edge_score", "loss_risk_score"}:
            thresholds.update(float(value) for value in [0.0, 1.0, 1.5, 2.0] if values.min() <= value <= values.max())
        numeric = pd.to_numeric(scoped[feature], errors="coerce").astype(float)
        for threshold in sorted(thresholds):
            predicates.append(({"feature": feature, "op": "<=", "value": threshold}, numeric.le(threshold).fillna(False)))
            predicates.append(({"feature": feature, "op": ">=", "value": threshold}, numeric.ge(threshold).fillna(False)))
    for feature in _candidate_categorical_features(scoped.loc[selected_idx], base_condition_features):
        train_values = scoped.loc[train_base_idx, feature].fillna("").astype(str).str.strip()
        for value, count in train_values.value_counts().items():
            if not value or value.lower() in {"nan", "none", "unknown"}:
                continue
            if int(count) < 4:
                continue
            predicates.append(({"feature": feature, "op": "==", "value": value}, scoped[feature].fillna("").astype(str).str.strip().eq(value)))

    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for condition, mask in predicates:
        key = json.dumps(condition, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        refined_idx = selected_idx[mask.reindex(selected_idx).fillna(False).to_numpy(dtype=bool)]
        train_idx = refined_idx.intersection(train_base_idx)
        test_idx = refined_idx.intersection(test_base_idx)
        if len(train_idx) < 6 or len(test_idx) < 4:
            continue
        train = _with_path_breakdown(scoped, train_idx, _metrics(scoped, train_idx, label))
        test = _with_path_breakdown(scoped, test_idx, _metrics(scoped, test_idx, label))
        if _metric_float(test, "bad_path_pct", 100.0) > _metric_float(base_test, "bad_path_pct", 100.0):
            continue
        if _metric_float(test, "early_drop_1d_pct", 100.0) > _metric_float(base_test, "early_drop_1d_pct", 100.0):
            continue
        bad_improvement = _metric_float(base_test, "bad_path_pct", 100.0) - _metric_float(test, "bad_path_pct", 100.0)
        drop_improvement = _metric_float(base_test, "early_drop_1d_pct", 100.0) - _metric_float(test, "early_drop_1d_pct", 100.0)
        if bad_improvement <= 0.0 and drop_improvement <= 0.0:
            continue
        if _metric_float(test, "win_5d_pct", 0.0) < 70.0 or _metric_float(test, "avg_5d_pct", -999.0) < 0.0:
            continue
        status = _refinement_status(train, test)
        rows.append(
            {
                "condition": condition,
                "condition_label": _condition_label(condition),
                "status": status,
                "score": _score_refinement(base_test, train, test),
                "train": train,
                "test": test,
            }
        )
    rows.sort(key=lambda row: (row.get("status") == "strict_refinement_candidate", row.get("status") == "watch_refinement_candidate", row.get("score") or -999.0), reverse=True)
    return rows[:MAX_REFINEMENT_CANDIDATES]


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
        train_idx = selected_idx.intersection(scoped.index[split_train.fillna(False)])
        test_idx = selected_idx.intersection(scoped.index[split_test.fillna(False)])
        all_metrics = _with_path_breakdown(scoped, selected_idx, _metrics(scoped, selected_idx, label))
        train_metrics = _with_path_breakdown(scoped, train_idx, _metrics(scoped, train_idx, label))
        test_metrics = _with_path_breakdown(scoped, test_idx, _metrics(scoped, test_idx, label))
        status, checks = _status(all_metrics, train_metrics, test_metrics, dict(rule.get("gate") or {}), missing)
        refinements = _refinement_candidates(
            scoped,
            selected_idx=selected_idx,
            train_base_idx=train_idx,
            test_base_idx=test_idx,
            label=label,
            base_test=test_metrics,
            base_condition_features=[str(item.get("feature")) for item in rule.get("conditions") or [] if isinstance(item, dict)],
        )
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
                "refinement_candidates": refinements,
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
            "strict_refinement_candidate_count": sum(
                1
                for row in rows
                for item in row.get("refinement_candidates") or []
                if item.get("status") == "strict_refinement_candidate"
            ),
            "watch_refinement_candidate_count": sum(
                1
                for row in rows
                for item in row.get("refinement_candidates") or []
                if item.get("status") == "watch_refinement_candidate"
            ),
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
        f"min5={metric.get('min_5d_pct')}% bad={metric.get('bad_path_pct')}% "
        f"drop1d={metric.get('early_drop_1d_pct')}% loss5={metric.get('loss_5d_pct')}% "
        f"stop={metric.get('stop5_pct')}%"
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
    lines.extend(["## Refinement Candidates", ""])
    for row in report.get("rules") or []:
        lines.append(f"### {row.get('rule_id')}")
        candidates = row.get("refinement_candidates") or []
        if not candidates:
            lines.append("- 추가 refinement 후보 없음")
            lines.append("")
            continue
        lines.extend(
            [
                "| Condition | Status | Score | Train | Test |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for item in candidates:
            lines.append(
                "| "
                f"{item.get('condition_label')} | {item.get('status')} | {item.get('score')} | "
                f"{_metric_text(item.get('train') or {})} | {_metric_text(item.get('test') or {})} |"
            )
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
