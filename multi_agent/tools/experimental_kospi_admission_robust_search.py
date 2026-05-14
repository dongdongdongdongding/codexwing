#!/usr/bin/env python3
"""KOSPI-only robust admission search for target-touch candidates.

This tool is shadow-only. It searches KOSPI admission rules across multiple
time splits, then re-evaluates unique candidates on rolling forward folds.
Production scanner ranking is not changed by this script.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.experimental_admission_cycle import (
    DEFAULT_INPUT,
    LabelProfile,
    _condition_candidates,
    _decision_masks,
    _label_series,
    _load_dataset,
    _metrics,
    _search_rules,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/experimental/kospi_admission_robust_search.json"
REPORT_VERSION = "kospi_admission_robust_search_v1"

KOSPI_PROFILES: Tuple[LabelProfile, ...] = (
    LabelProfile("5D_clean_8v4", 5, 8.0, 4.0, 2.0, "mfe_without_stop_proxy"),
    LabelProfile("5D_clean_10v5", 5, 10.0, 5.0, 2.0, "mfe_without_stop_proxy"),
    LabelProfile("5D_clean_12v5", 5, 12.0, 5.0, 2.4, "mfe_without_stop_proxy"),
    LabelProfile("5D_clean_15v5", 5, 15.0, 5.0, 3.0, "mfe_without_stop_proxy"),
    LabelProfile("3D_close_5v3_no_5d_stop", 3, 5.0, 3.0, 1.67, "close_and_no_stop_proxy"),
)

KOSPI_COHORTS = ("Top1", "Top3", "Top5", "Exception Leader", "Top5+Exception")

SEED_CANDIDATES: Tuple[Dict[str, Any], ...] = (
    {
        "market": "KOSPI",
        "cohort": "Top3",
        "profile": "5D_clean_10v5",
        "conditions": ["prob_clean<=31.8", "decision_score>=100", "explosive_leader_flag=0"],
        "split_cut_day": "seed_from_admission_cycle_70pct",
        "train": {"win_rate_pct": 66.667, "n": 21},
        "test": {"win_rate_pct": 88.889, "n": 9},
    },
    {
        "market": "KOSPI",
        "cohort": "Top3",
        "profile": "5D_clean_10v5",
        "conditions": ["prob_clean<=31.8", "decision_score>=93.26", "explosive_leader_flag=0"],
        "split_cut_day": "seed_from_admission_cycle_70pct",
        "train": {"win_rate_pct": 62.5, "n": 24},
        "test": {"win_rate_pct": 88.889, "n": 9},
    },
)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _condition_map(df: pd.DataFrame, base_mask: pd.Series, *, max_conditions: int) -> Dict[str, pd.Series]:
    return {name: mask for name, mask in _condition_candidates(df, base_mask, max_conditions=max_conditions)}


def _mask_for_conditions(
    df: pd.DataFrame,
    *,
    base_mask: pd.Series,
    conditions: List[str],
    condition_map: Dict[str, pd.Series],
) -> pd.Series | None:
    mask = base_mask.copy()
    for condition in conditions:
        if condition == "BASE":
            continue
        cond = condition_map.get(condition)
        if cond is None:
            cond = _parse_condition(df, condition)
        if cond is None:
            return None
        mask &= cond
    return mask


def _parse_condition(df: pd.DataFrame, condition: str) -> pd.Series | None:
    match = re.match(r"^([A-Za-z0-9_]+)(<=|>=|=)(.+)$", str(condition))
    if not match:
        return None
    col, op, raw_value = match.groups()
    if col not in df.columns:
        return None
    raw_value = raw_value.strip()
    if op in {"<=", ">="}:
        threshold = _safe_float(raw_value)
        if threshold is None:
            return None
        numeric = pd.to_numeric(df[col], errors="coerce")
        return numeric.le(threshold).fillna(False) if op == "<=" else numeric.ge(threshold).fillna(False)
    numeric_value = _safe_float(raw_value)
    if numeric_value is not None:
        numeric = pd.to_numeric(df[col], errors="coerce")
        return numeric.eq(numeric_value).fillna(False)
    return df[col].fillna("").astype(str).eq(raw_value)


def _rolling_folds(df: pd.DataFrame, *, folds: int, min_train_days: int) -> List[Dict[str, Any]]:
    days = sorted(df["trade_date"].dropna().astype(str).unique().tolist())
    if len(days) < min_train_days + folds:
        return []
    start = min_train_days
    remaining = days[start:]
    if not remaining:
        return []
    fold_size = max(1, math.ceil(len(remaining) / folds))
    out: List[Dict[str, Any]] = []
    for idx in range(folds):
        test_days = remaining[idx * fold_size : (idx + 1) * fold_size]
        if not test_days:
            continue
        train_days = [day for day in days if day < test_days[0]]
        if len(train_days) < min_train_days:
            continue
        train_mask = df["trade_date"].isin(train_days)
        test_mask = df["trade_date"].isin(test_days)
        out.append(
            {
                "fold": idx + 1,
                "train_start": train_days[0],
                "train_end": train_days[-1],
                "test_start": test_days[0],
                "test_end": test_days[-1],
                "train_mask": train_mask,
                "test_mask": test_mask,
            }
        )
    return out


def _evaluate_candidate(
    df: pd.DataFrame,
    *,
    candidate: Dict[str, Any],
    base_mask: pd.Series,
    condition_map: Dict[str, pd.Series],
    profile: LabelProfile,
    folds: List[Dict[str, Any]],
    min_fold_test: int,
) -> Dict[str, Any] | None:
    mask = _mask_for_conditions(
        df,
        base_mask=base_mask,
        conditions=list(candidate.get("conditions") or []),
        condition_map=condition_map,
    )
    if mask is None:
        return None
    label, valid = _label_series(df, profile)
    fold_rows: List[Dict[str, Any]] = []
    total_n = 0
    total_wins = 0.0
    for fold in folds:
        test_metrics = _metrics(df, mask & fold["test_mask"], label, valid)
        train_metrics = _metrics(df, mask & fold["train_mask"], label, valid)
        if int(test_metrics.get("n") or 0) < min_fold_test:
            continue
        wins = (float(test_metrics.get("win_rate_pct") or 0.0) / 100.0) * int(test_metrics.get("n") or 0)
        total_n += int(test_metrics.get("n") or 0)
        total_wins += wins
        fold_rows.append(
            {
                "fold": fold["fold"],
                "train_range": [fold["train_start"], fold["train_end"]],
                "test_range": [fold["test_start"], fold["test_end"]],
                "train": train_metrics,
                "test": test_metrics,
            }
        )
    if not fold_rows or total_n <= 0:
        return None
    fold_wins = [float(row["test"].get("win_rate_pct") or 0.0) for row in fold_rows]
    fold_stops = [float(row["test"].get("stop5_pct") or 0.0) for row in fold_rows]
    avg_returns = [float(row["test"].get("avg_return_5d_pct") or 0.0) for row in fold_rows]
    weighted_win = round((total_wins / total_n) * 100.0, 3)
    return {
        "market": "KOSPI",
        "cohort": candidate.get("cohort"),
        "profile": candidate.get("profile"),
        "conditions": candidate.get("conditions"),
        "source_split_cut_day": candidate.get("split_cut_day"),
        "source_train": candidate.get("train"),
        "source_test": candidate.get("test"),
        "fold_count": len(fold_rows),
        "fold_test_n_total": total_n,
        "fold_weighted_win_pct": weighted_win,
        "fold_min_win_pct": round(min(fold_wins), 3),
        "fold_median_win_pct": round(float(median(fold_wins)), 3),
        "fold_max_stop5_pct": round(max(fold_stops), 3),
        "fold_avg_return_5d_pct": round(sum(avg_returns) / len(avg_returns), 4),
        "folds": fold_rows,
        "label_profile": asdict(profile),
    }


def _candidate_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        row.get("market"),
        row.get("cohort"),
        row.get("profile"),
        tuple(row.get("conditions") or []),
    )


def build_report(
    df: pd.DataFrame,
    *,
    train_ratios: List[float],
    max_depth: int,
    beam_width: int,
    min_train: int,
    min_test: int,
    max_conditions: int,
    top_per_split: int,
    rolling_folds: int,
    min_train_days: int,
    min_fold_test: int,
) -> Dict[str, Any]:
    kospi = df[df["market2"].eq("KOSPI")].copy()
    market_mask = df["market2"].eq("KOSPI")
    cohort_masks = _decision_masks(df)
    raw_candidates: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for seed in SEED_CANDIDATES:
        raw_candidates.setdefault(_candidate_key(seed), dict(seed))

    for ratio in train_ratios:
        for cohort in KOSPI_COHORTS:
            base_mask = market_mask & cohort_masks[cohort]
            for profile in KOSPI_PROFILES:
                rows = _search_rules(
                    df,
                    profile=profile,
                    market="KOSPI",
                    cohort=cohort,
                    base_mask=base_mask,
                    max_depth=max_depth,
                    beam_width=beam_width,
                    min_train=min_train,
                    min_test=min_test,
                    max_conditions=max_conditions,
                    train_ratio=ratio,
                )
                for row in rows[:top_per_split]:
                    row = dict(row)
                    row["search_train_ratio"] = ratio
                    raw_candidates.setdefault(_candidate_key(row), row)

    folds = _rolling_folds(kospi, folds=rolling_folds, min_train_days=min_train_days)
    robust_rows: List[Dict[str, Any]] = []
    for candidate in raw_candidates.values():
        cohort = str(candidate.get("cohort"))
        profile_name = str(candidate.get("profile"))
        profile = next((p for p in KOSPI_PROFILES if p.name == profile_name), None)
        if profile is None or cohort not in cohort_masks:
            continue
        base_mask = market_mask & cohort_masks[cohort]
        condition_map = _condition_map(df, base_mask, max_conditions=max_conditions)
        evaluated = _evaluate_candidate(
            df,
            candidate=candidate,
            base_mask=base_mask,
            condition_map=condition_map,
            profile=profile,
            folds=folds,
            min_fold_test=min_fold_test,
        )
        if evaluated is not None:
            robust_rows.append(evaluated)

    robust_rows.sort(
        key=lambda row: (
            float(row.get("fold_weighted_win_pct") or 0.0),
            float(row.get("fold_min_win_pct") or 0.0),
            float(row.get("fold_avg_return_5d_pct") or -999.0),
            int(row.get("fold_test_n_total") or 0),
        ),
        reverse=True,
    )
    stable_70 = [
        row
        for row in robust_rows
        if float(row.get("fold_weighted_win_pct") or 0.0) >= 70.0
        and float(row.get("fold_min_win_pct") or 0.0) >= 50.0
        and int(row.get("fold_count") or 0) >= 2
        and int(row.get("fold_test_n_total") or 0) >= min_test
    ]
    strict_70 = [
        row
        for row in stable_70
        if float(row.get("fold_min_win_pct") or 0.0) >= 70.0
        and float(row.get("fold_max_stop5_pct") or 100.0) <= 15.0
    ]
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow_only_not_production",
        "input_rows": int(len(df)),
        "kospi_rows": int(len(kospi)),
        "raw_candidate_count": len(raw_candidates),
        "evaluated_candidate_count": len(robust_rows),
        "search_config": {
            "train_ratios": train_ratios,
            "max_depth": max_depth,
            "beam_width": beam_width,
            "min_train": min_train,
            "min_test": min_test,
            "max_conditions": max_conditions,
            "top_per_split": top_per_split,
            "rolling_folds": rolling_folds,
            "min_train_days": min_train_days,
            "min_fold_test": min_fold_test,
        },
        "fold_ranges": [
            {
                "fold": fold["fold"],
                "train_start": fold["train_start"],
                "train_end": fold["train_end"],
                "test_start": fold["test_start"],
                "test_end": fold["test_end"],
            }
            for fold in folds
        ],
        "champions": robust_rows[:100],
        "stable_70pct_candidates": stable_70[:50],
        "strict_70pct_candidates": strict_70[:50],
        "notes": [
            "KOSPI-only shadow search. Production scanner logic is unchanged.",
            "Rules are searched on multiple simple train/test ratios, then rechecked on rolling time folds.",
            "Primary theme is not used as a condition because fixed themes rotate and overfit.",
            "Archive labels are still proxy labels; any production candidate must be revalidated with ordered OHLCV path labels.",
        ],
    }


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# KOSPI Admission Robust Search",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- mode: `{report.get('mode')}`",
        f"- kospi_rows: `{report.get('kospi_rows')}`",
        f"- raw_candidate_count: `{report.get('raw_candidate_count')}`",
        f"- evaluated_candidate_count: `{report.get('evaluated_candidate_count')}`",
        f"- config: `{report.get('search_config')}`",
        "",
        "## Strict 70pct Candidates",
        "",
    ]
    strict = report.get("strict_70pct_candidates") if isinstance(report.get("strict_70pct_candidates"), list) else []
    if strict:
        for row in strict[:20]:
            lines.append(
                f"- `{row.get('cohort')}` / `{row.get('profile')}`: "
                f"weighted `{row.get('fold_weighted_win_pct')}`%, min_fold `{row.get('fold_min_win_pct')}`%, "
                f"n=`{row.get('fold_test_n_total')}`, stop_max `{row.get('fold_max_stop5_pct')}`%, "
                f"conditions={row.get('conditions')}"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Stable 70pct Candidates", ""])
    stable = report.get("stable_70pct_candidates") if isinstance(report.get("stable_70pct_candidates"), list) else []
    if stable:
        for row in stable[:30]:
            lines.append(
                f"- `{row.get('cohort')}` / `{row.get('profile')}`: "
                f"weighted `{row.get('fold_weighted_win_pct')}`%, min_fold `{row.get('fold_min_win_pct')}`%, "
                f"median `{row.get('fold_median_win_pct')}`%, n=`{row.get('fold_test_n_total')}`, "
                f"avg5 `{row.get('fold_avg_return_5d_pct')}`%, stop_max `{row.get('fold_max_stop5_pct')}`%, "
                f"conditions={row.get('conditions')}"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Top Champions", ""])
    headers = ["rank", "cohort", "profile", "folds", "n", "weighted_win", "min_win", "median_win", "avg5", "max_stop", "conditions"]
    champions = report.get("champions") if isinstance(report.get("champions"), list) else []
    if champions:
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for idx, row in enumerate(champions[:30], start=1):
            values = [
                idx,
                row.get("cohort"),
                row.get("profile"),
                row.get("fold_count"),
                row.get("fold_test_n_total"),
                row.get("fold_weighted_win_pct"),
                row.get("fold_min_win_pct"),
                row.get("fold_median_win_pct"),
                row.get("fold_avg_return_5d_pct"),
                row.get("fold_max_stop5_pct"),
                "<br>".join(row.get("conditions") or []),
            ]
            lines.append("| " + " | ".join(str(value) for value in values) + " |")
    else:
        lines.append("No champions.")
    lines.extend(["", "## Fold Ranges"])
    for fold in report.get("fold_ranges") or []:
        lines.append(
            f"- fold `{fold['fold']}`: train `{fold['train_start']}` to `{fold['train_end']}`, "
            f"test `{fold['test_start']}` to `{fold['test_end']}`"
        )
    lines.extend(["", "## Notes"])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--train-ratios", default="0.55,0.6,0.65,0.7,0.75")
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--beam-width", type=int, default=150)
    parser.add_argument("--min-train", type=int, default=20)
    parser.add_argument("--min-test", type=int, default=8)
    parser.add_argument("--max-conditions", type=int, default=180)
    parser.add_argument("--top-per-split", type=int, default=80)
    parser.add_argument("--rolling-folds", type=int, default=4)
    parser.add_argument("--min-train-days", type=int, default=8)
    parser.add_argument("--min-fold-test", type=int, default=4)
    args = parser.parse_args()

    train_ratios = [float(item.strip()) for item in str(args.train_ratios).split(",") if item.strip()]
    df = _load_dataset(Path(args.input))
    report = build_report(
        df,
        train_ratios=train_ratios,
        max_depth=int(args.max_depth),
        beam_width=int(args.beam_width),
        min_train=int(args.min_train),
        min_test=int(args.min_test),
        max_conditions=int(args.max_conditions),
        top_per_split=int(args.top_per_split),
        rolling_folds=int(args.rolling_folds),
        min_train_days=int(args.min_train_days),
        min_fold_test=int(args.min_fold_test),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, output.with_suffix(".md"))
    print(
        json.dumps(
            {
                "output": str(output),
                "raw_candidates": report["raw_candidate_count"],
                "evaluated": report["evaluated_candidate_count"],
                "stable_70pct": len(report["stable_70pct_candidates"]),
                "strict_70pct": len(report["strict_70pct_candidates"]),
                "best": report["champions"][0] if report["champions"] else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
