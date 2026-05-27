#!/usr/bin/env python3
"""Daily ordered shadow-rule watch report for KR scanner candidates.

This is a lightweight companion to the exhaustive ordered candidate search.
It refreshes cached ordered labels from the current scan archive, evaluates
known shadow/watch rules, and writes a compact report for daily automation.
It does not search new rules and does not change production scanner ranking.
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

from multi_agent.tools.experimental_admission_cycle import DEFAULT_INPUT, _load_dataset
from multi_agent.tools.experimental_kospi_ordered_candidate_search import (
    DEFAULT_CACHED_LABELS,
    DEFAULT_KOSDAQ_CACHED_LABELS,
    CURATED_RULES,
    _append_missing_cached_labels,
    _condition_to_mask,
    _feature_coverage_report,
    _metrics,
    _refresh_cached_labels_from_archive,
    add_search_columns,
    prepare_profile_rows,
    profiles_for_market,
)
from multi_agent.tools.experimental_kospi_ordered_revalidation import label_selected_rows


REPORT_VERSION = "kr_ordered_shadow_watch_v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/experimental/ordered_shadow_watch_latest.json"

EXTRA_WATCH_RULES: Tuple[Dict[str, Any], ...] = (
    {
        "rule_id": "kospi_dynamic_phase_theme_watch_10v5",
        "market": "KOSPI",
        "profile": "5D_ordered_10v5",
        "conditions": [
            "cohort=Top3",
            "phase25_prob<=38.3",
            "theme_day_strength_rank<=8",
            "theme_day_strength_score>=2.0908",
        ],
        "note": "Latest KOSPI dynamic phase/theme shadow slice; high recent test win but still small/fold-weak.",
    },
    {
        "rule_id": "kosdaq_dynamic_theme_tech_watch_5v5",
        "market": "KOSDAQ",
        "profile": "5D_ordered_5v5",
        "conditions": [
            "theme_day_avg_volume_ratio>=0.8633",
            "theme_day_avg_expected_return_1d_pct>=0.1514",
            "tech_score<=65",
            "theme_day_avg_alpha_score<=69.5321",
        ],
        "note": "Latest KOSDAQ 5v5 dynamic-theme/tech watch slice; wait for mature close-tail evidence.",
    },
)


def _default_cache_path(market: str) -> Path:
    return DEFAULT_KOSDAQ_CACHED_LABELS if str(market).upper() == "KOSDAQ" else DEFAULT_CACHED_LABELS


def _watch_rules_for_market(market: str) -> List[Dict[str, Any]]:
    market_key = str(market).upper()
    rows: List[Dict[str, Any]] = []
    for rule in CURATED_RULES:
        if market_key in {str(item).upper() for item in rule.get("markets", [])}:
            row = dict(rule)
            row["market"] = market_key
            rows.append(row)
    rows.extend(dict(rule) for rule in EXTRA_WATCH_RULES if str(rule.get("market")).upper() == market_key)
    return rows


def _prepare_labeled_rows(
    archive_df: pd.DataFrame,
    *,
    market: str,
    cached_labels_path: Path,
    labeler=label_selected_rows,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    profiles = profiles_for_market(market)
    profile_rows = prepare_profile_rows(archive_df, profiles, market=market)
    refresh: Dict[str, Any] = {
        "market": str(market).upper(),
        "cached_labels_path": str(cached_labels_path),
        "fresh_profile_rows": int(len(profile_rows)),
        "loaded_rows": 0,
        "missing_profile_rows_labeled": 0,
    }
    cache_existed = cached_labels_path.exists()
    if cache_existed:
        labeled = pd.read_csv(cached_labels_path, low_memory=False)
        refresh["loaded_rows"] = int(len(labeled))
    else:
        labeled = pd.DataFrame()
    labeled, missing_count = _append_missing_cached_labels(labeled, profile_rows, labeler=labeler)
    refresh["missing_profile_rows_labeled"] = int(missing_count)
    labeled = _refresh_cached_labels_from_archive(labeled, archive_df)
    labeled = add_search_columns(labeled)
    if missing_count > 0 or not cache_existed:
        cached_labels_path.parent.mkdir(parents=True, exist_ok=True)
        labeled.to_csv(cached_labels_path, index=False)
        refresh["cache_written"] = True
    else:
        refresh["cache_written"] = False
    refresh["final_rows"] = int(len(labeled))
    refresh["ordered_label_ready_rows"] = int(labeled.get("ordered_label_ready", pd.Series(False, index=labeled.index)).sum())
    return labeled, refresh


def _split_masks(labeled: pd.DataFrame) -> Tuple[str | None, pd.Series, pd.Series]:
    dates = sorted(labeled.get("trade_date", pd.Series(dtype=object)).fillna("").astype(str).unique().tolist())
    split_day = dates[max(1, min(len(dates) - 1, int(len(dates) * 0.58)))] if len(dates) >= 3 else None
    if split_day:
        train_mask = labeled["trade_date"].fillna("").astype(str).lt(split_day)
        test_mask = labeled["trade_date"].fillna("").astype(str).ge(split_day)
    else:
        train_mask = pd.Series(False, index=labeled.index)
        test_mask = pd.Series(False, index=labeled.index)
    return split_day, train_mask, test_mask


def _rule_mask(labeled: pd.DataFrame, rule: Dict[str, Any]) -> pd.Series:
    mask = labeled.get("candidate_id", pd.Series("", index=labeled.index)).fillna("").astype(str).eq(str(rule.get("profile") or ""))
    for condition in rule.get("conditions") or []:
        parsed = _condition_to_mask(labeled, str(condition))
        if parsed is None:
            return pd.Series(False, index=labeled.index)
        mask &= parsed.fillna(False)
    return mask.fillna(False)


def _rule_status(row: Dict[str, Any]) -> str:
    train = row.get("train") or {}
    test = row.get("test") or {}
    all_m = row.get("all") or {}
    if int(test.get("n") or 0) < 8 or int(train.get("n") or 0) < 8:
        return "watch_small_sample"
    if (
        int(all_m.get("n") or 0) >= 30
        and int(train.get("n") or 0) >= 12
        and int(test.get("n") or 0) >= 12
        and float(all_m.get("win_pct") or 0.0) >= 70.0
        and float(train.get("win_pct") or 0.0) >= 65.0
        and float(test.get("win_pct") or 0.0) >= 75.0
        and float(test.get("stop_pct") or 100.0) <= 20.0
        and float(test.get("close_loss_5pct_or_worse_pct") or 100.0) <= 10.0
    ):
        return "review_candidate"
    return "shadow_only"


def evaluate_watch_rules(labeled: pd.DataFrame, rules: Sequence[Dict[str, Any]]) -> Tuple[str | None, List[Dict[str, Any]]]:
    split_day, train_mask, test_mask = _split_masks(labeled)
    rows: List[Dict[str, Any]] = []
    for rule in rules:
        mask = _rule_mask(labeled, rule)
        row = {
            "rule_id": rule.get("rule_id"),
            "market": rule.get("market"),
            "profile": rule.get("profile"),
            "conditions": list(rule.get("conditions") or []),
            "note": rule.get("note"),
            "all": _metrics(labeled, mask),
            "train": _metrics(labeled, mask & train_mask),
            "test": _metrics(labeled, mask & test_mask),
        }
        row["status"] = _rule_status(row)
        rows.append(row)
    return split_day, rows


def build_report(input_path: Path, output_path: Path) -> Dict[str, Any]:
    archive_df = _load_dataset(input_path)
    market_payloads: List[Dict[str, Any]] = []
    for market in ("KOSPI", "KOSDAQ"):
        cached_path = _default_cache_path(market)
        labeled, refresh = _prepare_labeled_rows(archive_df, market=market, cached_labels_path=cached_path)
        split_day, rows = evaluate_watch_rules(labeled, _watch_rules_for_market(market))
        market_payloads.append(
            {
                "market": market,
                "split_day": split_day,
                "cache_refresh": refresh,
                "feature_coverage": _feature_coverage_report(labeled),
                "watch_rules": rows,
            }
        )
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "output_path": str(output_path),
        "production_scanner_changed": False,
        "markets": market_payloads,
        "notes": [
            "This report only evaluates pre-registered ordered shadow/watch rules.",
            "It refreshes ordered label caches from the current archive before evaluating metrics.",
            "review_candidate is not automatic promotion; manual release gates still apply.",
        ],
    }


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Ordered Shadow Watch",
        "",
        f"- generated_at: `{report['generated_at']}`",
        "- production_scanner_changed: `False`",
        "",
    ]
    for market in report.get("markets") or []:
        refresh = market.get("cache_refresh") or {}
        lines.extend(
            [
                f"## {market.get('market')}",
                "",
                f"- split_day: `{market.get('split_day')}`",
                (
                    "- cache: "
                    f"loaded={refresh.get('loaded_rows')} fresh={refresh.get('fresh_profile_rows')} "
                    f"missing_labeled={refresh.get('missing_profile_rows_labeled')} "
                    f"ready={refresh.get('ordered_label_ready_rows')}"
                ),
                "",
                "| Rule | Status | All | Train | Test | Conditions |",
                "|---|---|---:|---:|---:|---|",
            ]
        )
        for row in market.get("watch_rules") or []:
            all_m = row.get("all") or {}
            train = row.get("train") or {}
            test = row.get("test") or {}
            conditions = "; ".join(str(item) for item in row.get("conditions") or [])
            lines.append(
                "| "
                f"{row.get('rule_id')} | {row.get('status')} | "
                f"n={all_m.get('n')} win={all_m.get('win_pct')}% stop={all_m.get('stop_pct')}% | "
                f"n={train.get('n')} win={train.get('win_pct')}% | "
                f"n={test.get('n')} win={test.get('win_pct')}% stop={test.get('stop_pct')}% "
                f"loss5={test.get('close_loss_5pct_or_worse_pct')}% | "
                f"{conditions} |"
            )
        lines.append("")
    lines.extend(["## Notes", ""])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.input, args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_markdown(report, args.output.with_suffix(".md"))
    print(json.dumps({"json": str(args.output), "md": str(args.output.with_suffix(".md"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
