#!/usr/bin/env python3
"""Ordered OHLCV revalidation for KOSPI admission candidates.

This is an internal testbed only. It replays selected KOSPI admission rules
against actual daily OHLCV order using the target-before-stop shadow contract.
It does not change production scanner ranking or UI behavior.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.experimental_target_touch import TargetTouchPolicy, compute_target_before_stop_label
from multi_agent.tools.experimental_admission_cycle import DEFAULT_INPUT, _decision_masks, _load_dataset
from multi_agent.tools.experimental_kospi_admission_robust_search import _parse_condition

try:
    import FinanceDataReader as fdr  # type: ignore
except Exception:  # pragma: no cover
    fdr = None


REPORT_VERSION = "kospi_ordered_ohlcv_revalidation_v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/experimental/kospi_admission_ordered_revalidation.json"


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    description: str
    cohort: str
    target_pct: float
    stop_pct: float
    horizon_days: int
    condition_groups: Tuple[Tuple[str, ...], ...]
    source_proxy: Dict[str, Any]


@dataclass(frozen=True)
class OrderedRefinementSpec:
    refinement_id: str
    description: str
    conditions: Tuple[str, ...]
    split_date: str = "2026-04-24"


CANDIDATES: Tuple[CandidateSpec, ...] = (
    CandidateSpec(
        candidate_id="strict_top5_core_8v4",
        description="Strict KOSPI Top5 core-trend rule from robust proxy search.",
        cohort="Top5",
        target_pct=8.0,
        stop_pct=4.0,
        horizon_days=5,
        condition_groups=(
            ("prob_clean<=31.3", "decision_score>=100", "kr_universe_role=CORE_TREND"),
            ("prob_clean<=31.3", "decision_score>=100", "core_trend_flag=1"),
        ),
        source_proxy={
            "fold_weighted_win_pct": 78.947,
            "fold_min_win_pct": 71.429,
            "fold_test_n_total": 19,
            "fold_avg_return_5d_pct": 8.5147,
        },
    ),
    CandidateSpec(
        candidate_id="high_upside_top3_10v5",
        description="Higher target Top3 rule; strong proxy average return but weaker fold floor.",
        cohort="Top3",
        target_pct=10.0,
        stop_pct=5.0,
        horizon_days=5,
        condition_groups=(("prob_clean<=31.8", "decision_score>=100", "explosive_leader_flag=0"),),
        source_proxy={
            "fold_weighted_win_pct": 78.947,
            "fold_min_win_pct": 62.5,
            "fold_test_n_total": 19,
            "fold_avg_return_5d_pct": 10.303,
        },
    ),
    CandidateSpec(
        candidate_id="strict_top5_low_ml_10v5",
        description="Strict Top5 low-ML-prob rule that passed 10v5 proxy search.",
        cohort="Top5",
        target_pct=10.0,
        stop_pct=5.0,
        horizon_days=5,
        condition_groups=(("ml_prob<=20.84", "prob_clean<=35.225", "decision_score>=92"),),
        source_proxy={
            "fold_weighted_win_pct": 73.684,
            "fold_min_win_pct": 71.429,
            "fold_test_n_total": 19,
            "fold_avg_return_5d_pct": 6.2038,
        },
    ),
)

ORDERED_REFINEMENTS: Tuple[OrderedRefinementSpec, ...] = (
    OrderedRefinementSpec(
        refinement_id="ordered_high_upside_top3_prob_band_10v5",
        description="Adds a lower prob_clean band inside the high-upside Top3 candidate.",
        conditions=("candidate_id=high_upside_top3_10v5", "prob_clean>=28.1"),
    ),
    OrderedRefinementSpec(
        refinement_id="ordered_prob_floor_core_route",
        description="Cross-candidate diagnostic slice; useful signal, but can duplicate ticker-date rows.",
        conditions=("prob_clean>=28.1", "theme_routing_path=core_only"),
    ),
)


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _round(value: Any, digits: int = 4) -> float | None:
    number = _safe_float(value)
    return round(number, digits) if number is not None else None


def _candidate_mask(df: pd.DataFrame, spec: CandidateSpec) -> pd.Series:
    cohort_masks = _decision_masks(df)
    base = cohort_masks.get(spec.cohort)
    if base is None:
        return pd.Series(False, index=df.index)
    out = pd.Series(False, index=df.index)
    for group in spec.condition_groups:
        mask = base.copy()
        for condition in group:
            parsed = _parse_condition(df, condition)
            if parsed is None:
                mask = pd.Series(False, index=df.index)
                break
            mask &= parsed.fillna(False)
        out |= mask
    return out.fillna(False)


def select_candidate_rows(df: pd.DataFrame, specs: Iterable[CandidateSpec] = CANDIDATES) -> pd.DataFrame:
    rows: List[pd.DataFrame] = []
    kospi = df[df.get("market2", pd.Series("", index=df.index)).eq("KOSPI")].copy()
    for spec in specs:
        mask = _candidate_mask(kospi, spec)
        sub = kospi.loc[mask].copy()
        if sub.empty:
            continue
        sub["candidate_id"] = spec.candidate_id
        sub["candidate_description"] = spec.description
        sub["candidate_cohort"] = spec.cohort
        sub["target_pct"] = float(spec.target_pct)
        sub["stop_pct"] = float(spec.stop_pct)
        sub["horizon_days"] = int(spec.horizon_days)
        sub["source_proxy"] = json.dumps(spec.source_proxy, ensure_ascii=False)
        rows.append(sub)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    sort_cols = [col for col in ["candidate_id", "trade_date", "ticker", "run_id", "id"] if col in out.columns]
    out = out.sort_values(sort_cols, na_position="last")
    return out.drop_duplicates(["candidate_id", "trade_date", "ticker"], keep="first").reset_index(drop=True)


def _fetch_kr_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    if fdr is None:
        return pd.DataFrame()
    code = str(ticker).split(".")[0]
    try:
        hist = fdr.DataReader(code, start, end)
    except Exception:
        return pd.DataFrame()
    if hist is None or hist.empty:
        return pd.DataFrame()
    hist = hist.copy()
    hist["trade_date"] = [d.date().isoformat() for d in hist.index]
    return hist.reset_index(drop=True)


def _history_to_bars(hist: pd.DataFrame) -> List[Dict[str, Any]]:
    bars: List[Dict[str, Any]] = []
    for _, row in hist.iterrows():
        bars.append(
            {
                "date": row.get("trade_date"),
                "high": _safe_float(row.get("High")),
                "low": _safe_float(row.get("Low")),
                "close": _safe_float(row.get("Close")),
            }
        )
    return bars


def _signal_entry(hist: pd.DataFrame, scan_date: str) -> Dict[str, Any]:
    trade_dates = hist.get("trade_date", pd.Series(dtype=object)).fillna("").astype(str).tolist()
    for pos, trade_date in enumerate(trade_dates):
        if trade_date >= scan_date:
            close = _safe_float(hist.iloc[pos].get("Close"))
            return {"entry_price": close, "entry_date": trade_date, "entry_pos": pos}
    return {"entry_price": None, "entry_date": None, "entry_pos": None}


def label_selected_rows(selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty:
        return selected.copy()
    outputs: List[pd.DataFrame] = []
    for ticker, group in selected.groupby("ticker", sort=False):
        dates = sorted(str(d) for d in group["trade_date"].dropna().astype(str).unique() if len(str(d)) >= 10)
        out = group.copy()
        for col in [
            "ordered_target_before_stop",
            "ordered_stop_before_target",
            "ordered_terminal_status",
            "ordered_target_hit_at",
            "ordered_stop_hit_at",
            "ordered_bars_observed",
            "ordered_mfe_pct",
            "ordered_mae_pct",
            "ordered_entry_price",
            "ordered_entry_date",
            "archive_entry_divergence_pct",
            "ordered_warnings",
        ]:
            out[col] = None
        if not dates:
            outputs.append(out)
            continue
        start = (date.fromisoformat(dates[0]) - timedelta(days=7)).isoformat()
        end = (date.fromisoformat(dates[-1]) + timedelta(days=21)).isoformat()
        hist = _fetch_kr_history(str(ticker), start, end)
        if hist.empty:
            out["ordered_terminal_status"] = "history_unavailable"
            outputs.append(out)
            continue
        bars = _history_to_bars(hist)
        for idx, row in out.iterrows():
            scan_date = str(row.get("trade_date") or "")[:10]
            entry = _signal_entry(hist, scan_date)
            entry_price = _safe_float(entry.get("entry_price"))
            if entry_price is None or entry_price <= 0:
                out.at[idx, "ordered_terminal_status"] = "invalid_signal_close_entry"
                out.at[idx, "ordered_warnings"] = ["invalid_signal_close_entry"]
                continue
            target_pct = float(row.get("target_pct") or 0.0)
            stop_pct = float(row.get("stop_pct") or 0.0)
            horizon = int(row.get("horizon_days") or 5)
            label = compute_target_before_stop_label(
                bars,
                entry_price=entry_price,
                base_date=entry.get("entry_date") or scan_date,
                policy=TargetTouchPolicy(
                    horizon_days=horizon,
                    target_pct=target_pct,
                    stop_pct=stop_pct,
                    include_entry_day=False,
                    same_bar_policy="stop_first",
                ),
            )
            archive_entry = _safe_float(row.get("entry_reference_price"))
            divergence = None
            if archive_entry is not None and archive_entry > 0:
                divergence = ((archive_entry / entry_price) - 1.0) * 100.0
            out.at[idx, "ordered_target_before_stop"] = label.get("target_before_stop")
            out.at[idx, "ordered_stop_before_target"] = label.get("stop_before_target")
            out.at[idx, "ordered_terminal_status"] = label.get("terminal_status")
            out.at[idx, "ordered_target_hit_at"] = label.get("target_hit_at")
            out.at[idx, "ordered_stop_hit_at"] = label.get("stop_hit_at")
            out.at[idx, "ordered_bars_observed"] = label.get("bars_observed")
            out.at[idx, "ordered_mfe_pct"] = label.get("mfe_pct")
            out.at[idx, "ordered_mae_pct"] = label.get("mae_pct")
            out.at[idx, "ordered_entry_price"] = _round(entry_price, 6)
            out.at[idx, "ordered_entry_date"] = entry.get("entry_date")
            out.at[idx, "archive_entry_divergence_pct"] = _round(divergence, 4)
            out.at[idx, "ordered_warnings"] = label.get("warnings") or []
        outputs.append(out)
    return pd.concat(outputs, ignore_index=True)


def _mean_numeric(df: pd.DataFrame, col: str) -> float | None:
    if col not in df.columns:
        return None
    series = pd.to_numeric(df[col], errors="coerce")
    return _round(series.mean(), 4) if series.notna().any() else None


def summarize_labeled(labeled: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if labeled.empty:
        return rows
    for candidate_id, sub in labeled.groupby("candidate_id", sort=False):
        valid = sub["ordered_target_before_stop"].isin([True, False])
        valid_sub = sub.loc[valid].copy()
        wins = valid_sub["ordered_target_before_stop"].eq(True)
        stops = valid_sub["ordered_stop_before_target"].eq(True)
        no_touch = valid_sub["ordered_terminal_status"].eq("no_touch")
        same_bar = valid_sub["ordered_terminal_status"].fillna("").astype(str).str.startswith("same_bar")
        source_proxy = {}
        proxy_text = str(sub["source_proxy"].dropna().iloc[0]) if sub["source_proxy"].notna().any() else "{}"
        try:
            source_proxy = json.loads(proxy_text)
        except Exception:
            source_proxy = {}
        rows.append(
            {
                "candidate_id": candidate_id,
                "description": str(sub["candidate_description"].dropna().iloc[0]),
                "cohort": str(sub["candidate_cohort"].dropna().iloc[0]),
                "target_pct": _round(sub["target_pct"].dropna().iloc[0]),
                "stop_pct": _round(sub["stop_pct"].dropna().iloc[0]),
                "horizon_days": int(sub["horizon_days"].dropna().iloc[0]),
                "selected_rows": int(len(sub)),
                "ordered_labeled_rows": int(len(valid_sub)),
                "insufficient_or_missing_rows": int(len(sub) - len(valid_sub)),
                "unique_tickers": int(sub["ticker"].nunique()),
                "ordered_target_before_stop_pct": _round(wins.mean() * 100.0) if len(valid_sub) else None,
                "ordered_stop_before_target_pct": _round(stops.mean() * 100.0) if len(valid_sub) else None,
                "ordered_no_touch_pct": _round(no_touch.mean() * 100.0) if len(valid_sub) else None,
                "ordered_same_bar_pct": _round(same_bar.mean() * 100.0) if len(valid_sub) else None,
                "avg_ordered_mfe_pct": _mean_numeric(valid_sub, "ordered_mfe_pct"),
                "avg_ordered_mae_pct": _mean_numeric(valid_sub, "ordered_mae_pct"),
                "avg_archive_return_5d_pct": _mean_numeric(valid_sub, "return_5d_pct"),
                "avg_archive_max_high_5d_pct": _mean_numeric(valid_sub, "max_high_return_5d_pct"),
                "avg_archive_min_return_observed_pct": _mean_numeric(valid_sub, "min_return_observed_pct"),
                "source_proxy": source_proxy,
                "terminal_status_counts": valid_sub["ordered_terminal_status"].fillna("UNKNOWN").value_counts().to_dict(),
            }
        )
    return sorted(rows, key=lambda row: (-(row.get("ordered_target_before_stop_pct") or 0.0), -row["ordered_labeled_rows"]))


def _mask_for_conditions(df: pd.DataFrame, conditions: Iterable[str]) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for condition in conditions:
        parsed = _parse_condition(df, str(condition))
        if parsed is None:
            return pd.Series(False, index=df.index)
        mask &= parsed.fillna(False)
    return mask.fillna(False)


def _ordered_metrics(sub: pd.DataFrame) -> Dict[str, Any]:
    valid = sub[sub["ordered_target_before_stop"].isin([True, False])].copy()
    if valid.empty:
        return {
            "n": 0,
            "target_before_stop_pct": None,
            "stop_before_target_pct": None,
            "no_touch_pct": None,
            "avg_mfe_pct": None,
            "avg_mae_pct": None,
        }
    wins = valid["ordered_target_before_stop"].eq(True)
    stops = valid["ordered_stop_before_target"].eq(True)
    no_touch = valid["ordered_terminal_status"].eq("no_touch")
    return {
        "n": int(len(valid)),
        "target_before_stop_pct": _round(wins.mean() * 100.0),
        "stop_before_target_pct": _round(stops.mean() * 100.0),
        "no_touch_pct": _round(no_touch.mean() * 100.0),
        "avg_mfe_pct": _mean_numeric(valid, "ordered_mfe_pct"),
        "avg_mae_pct": _mean_numeric(valid, "ordered_mae_pct"),
    }


def evaluate_ordered_refinements(
    labeled: pd.DataFrame,
    specs: Iterable[OrderedRefinementSpec] = ORDERED_REFINEMENTS,
) -> List[Dict[str, Any]]:
    if labeled.empty:
        return []
    rows: List[Dict[str, Any]] = []
    trade_date = labeled.get("trade_date", pd.Series("", index=labeled.index)).fillna("").astype(str)
    for spec in specs:
        mask = _mask_for_conditions(labeled, spec.conditions)
        sub = labeled.loc[mask].copy()
        train = sub[trade_date.loc[sub.index].lt(spec.split_date)]
        test = sub[trade_date.loc[sub.index].ge(spec.split_date)]
        rows.append(
            {
                "refinement_id": spec.refinement_id,
                "description": spec.description,
                "conditions": list(spec.conditions),
                "split_date": spec.split_date,
                "all": _ordered_metrics(sub),
                "train_before_split": _ordered_metrics(train),
                "test_from_split": _ordered_metrics(test),
                "unique_ticker_dates": int(sub[["ticker", "trade_date"]].drop_duplicates().shape[0])
                if {"ticker", "trade_date"}.issubset(sub.columns)
                else int(len(sub)),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -(row["test_from_split"].get("target_before_stop_pct") or 0.0),
            -(row["all"].get("target_before_stop_pct") or 0.0),
            -(row["all"].get("n") or 0),
        ),
    )


def _examples(labeled: pd.DataFrame, limit: int = 20) -> List[Dict[str, Any]]:
    if labeled.empty:
        return []
    cols = [
        "candidate_id",
        "trade_date",
        "ticker",
        "stock_name",
        "priority_rank",
        "decision_score",
        "prob_clean",
        "ml_prob",
        "kr_universe_role",
        "ordered_entry_price",
        "ordered_target_before_stop",
        "ordered_terminal_status",
        "ordered_mfe_pct",
        "ordered_mae_pct",
        "ordered_target_hit_at",
        "ordered_stop_hit_at",
        "return_5d_pct",
    ]
    out = labeled[[col for col in cols if col in labeled.columns]].copy()
    out = out.sort_values(["candidate_id", "trade_date", "ticker"], na_position="last").head(limit)
    return out.where(pd.notna(out), None).to_dict(orient="records")


def build_report(input_path: Path) -> Tuple[Dict[str, Any], pd.DataFrame]:
    df = _load_dataset(input_path)
    selected = select_candidate_rows(df)
    labeled = label_selected_rows(selected)
    report = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "input_rows": int(len(df)),
        "kospi_rows": int(df.get("market2", pd.Series("", index=df.index)).eq("KOSPI").sum()),
        "entry_policy": "signal_day_close_from_same_ohlcv_source",
        "label_policy": asdict(
            TargetTouchPolicy(
                horizon_days=5,
                target_pct=0.0,
                stop_pct=0.0,
                include_entry_day=False,
                same_bar_policy="stop_first",
            )
        )
        | {"target_pct": "candidate_specific", "stop_pct": "candidate_specific"},
        "candidate_specs": [asdict(spec) for spec in CANDIDATES],
        "selected_rows": int(len(selected)),
        "ordered_labeled_rows": int(labeled["ordered_target_before_stop"].isin([True, False]).sum()) if not labeled.empty else 0,
        "summary": summarize_labeled(labeled),
        "ordered_refinements": evaluate_ordered_refinements(labeled),
        "examples": _examples(labeled),
        "notes": [
            "This report revalidates archive-discovered candidate rules using ordered daily OHLCV.",
            "Same-day target and stop cannot be ordered with daily bars; stop_first is used conservatively.",
            "The signal-day close from FinanceDataReader is used as entry to avoid archive entry-reference drift.",
            "Rows without enough forward bars remain selected but are excluded from ordered win-rate denominators.",
        ],
    }
    return report, labeled


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# KOSPI Ordered OHLCV Revalidation",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- input_rows: `{report['input_rows']}`",
        f"- kospi_rows: `{report['kospi_rows']}`",
        f"- selected_rows: `{report['selected_rows']}`",
        f"- ordered_labeled_rows: `{report['ordered_labeled_rows']}`",
        f"- entry_policy: `{report['entry_policy']}`",
        f"- same_bar_policy: `stop_first`",
        "",
        "## Candidate Results",
        "",
    ]
    if not report["summary"]:
        lines.append("- none")
    for row in report["summary"]:
        proxy = row.get("source_proxy") or {}
        lines.append(
            f"- `{row['candidate_id']}`: n={row['ordered_labeled_rows']}/{row['selected_rows']}, "
            f"ordered_win={row['ordered_target_before_stop_pct']}%, "
            f"stop_first={row['ordered_stop_before_target_pct']}%, "
            f"no_touch={row['ordered_no_touch_pct']}%, "
            f"avg_mfe={row['avg_ordered_mfe_pct']}%, avg_mae={row['avg_ordered_mae_pct']}%, "
            f"proxy_win={proxy.get('fold_weighted_win_pct')}%, proxy_min_fold={proxy.get('fold_min_win_pct')}%"
        )
    lines.extend(["", "## Interpretation", ""])
    for row in report["summary"]:
        win = row.get("ordered_target_before_stop_pct")
        n = row.get("ordered_labeled_rows") or 0
        if win is not None and win >= 70.0 and n >= 10:
            verdict = "usable shadow candidate"
        elif win is not None and win >= 60.0:
            verdict = "promising but not release-grade"
        else:
            verdict = "not validated by ordered OHLCV"
        lines.append(f"- `{row['candidate_id']}`: {verdict}")
    lines.extend(["", "## Ordered Refinement Candidates", ""])
    if not report.get("ordered_refinements"):
        lines.append("- none")
    for row in report.get("ordered_refinements") or []:
        all_m = row["all"]
        tr = row["train_before_split"]
        te = row["test_from_split"]
        lines.append(
            f"- `{row['refinement_id']}`: conditions={row['conditions']}, "
            f"all n={all_m['n']} win={all_m['target_before_stop_pct']}%, "
            f"train n={tr['n']} win={tr['target_before_stop_pct']}%, "
            f"test n={te['n']} win={te['target_before_stop_pct']}%, "
            f"test_stop={te['stop_before_target_pct']}%, "
            f"unique_ticker_dates={row['unique_ticker_dates']}"
        )
    lines.extend(["", "## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report, labeled = build_report(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path = args.output.with_suffix(".md")
    csv_path = args.output.with_suffix(".rows.csv")
    write_markdown(report, md_path)
    if not labeled.empty:
        labeled.to_csv(csv_path, index=False)
    print(json.dumps({"json": str(args.output), "md": str(md_path), "rows_csv": str(csv_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
