#!/usr/bin/env python3
"""Walk-forward cohort release gate for KR markets (principled 95% CI).

Why this exists
---------------
The role-lane release gate (``report_kr_walkforward_release_gate.py``) evaluates
``kr_universe_role`` lanes (EXPLOSIVE_LEADER / CORE_TREND). The forward sweep showed
the durable KOSPI alpha lives in *different* slices:

  - Exception Leader  : ``decision_bucket == exception_leader`` (or decision == EXCEPTION_LEADER)
  - Practical 80 Gate : scan-time practical_entry_gate level in {pass, near, small_sample}

Those cohorts are not measured by the role-lane gate at all, so simply lowering the
role-lane confidence cannot promote them. This tool gates *those cohorts* under the
same walk-forward bootstrap-CI machinery at a principled confidence (default 0.95),
so we can verify empirically whether they clear a promotion bar BEFORE any planner
exposure wiring.

It reuses the stats helpers (``_bootstrap_ci``, ``_check``) and the archive loader so
there is a single source of truth for the confidence-interval math. It does not touch
the production role-lane gate, the planner, or any live selection path.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.report_kr_walkforward_release_gate import _bootstrap_ci, _check
from modules.practical_entry_gate import evaluate_practical_entry_gate


# ---------------------------------------------------------------------------
# Universe loader
# ---------------------------------------------------------------------------
# IMPORTANT: we deliberately do NOT drop validation_excluded rows here.
# validation_excluded means "excluded from ML training" (reason is FEATURE_MISSING /
# ML_INFERENCE_FAILED), NOT "invalid realized outcome". The Exception Leader cohort
# (KR explosive-leader bypass) is ~100% validation_excluded by construction because it
# bypasses the normal feature/ML path -- but its realized forward returns are genuine.
# Dropping these rows would erase the very cohort we are gating. This loader mirrors the
# universe of report_scan_cohort_performance._load_rows so the gate measures the same rows.

_NUMERIC_COLS = [
    "decision_score", "return_1d_pct", "return_3d_pct", "return_5d_pct",
    "max_high_return_5d_pct", "min_return_observed_pct", "label_hit_10pct",
]


def _load_cohort_rows(path: Path, market: str) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    for col in _NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = _restrict_to_market(df, market)
    # trade_date for walk-forward daily grouping
    if "base_trade_date" in df.columns:
        trade_date = df["base_trade_date"].astype(str).str[:10]
    else:
        trade_date = pd.Series("", index=df.index, dtype="object")
    if "recommended_at" in df.columns:
        fallback = df["recommended_at"].astype(str).str[:10]
        trade_date = trade_date.where(trade_date.ne("") & trade_date.ne("nan"), fallback)
    df["trade_date"] = trade_date
    return df


# ---------------------------------------------------------------------------
# Cohort definitions
# ---------------------------------------------------------------------------

def _exception_leader_mask(df: pd.DataFrame) -> pd.Series:
    bucket = df.get("decision_bucket", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    decision = df.get("decision", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    return bucket.eq("exception_leader") | decision.eq("EXCEPTION_LEADER")


def _restrict_to_market(df: pd.DataFrame, market: str) -> pd.DataFrame:
    """Match the cohort report universe: SWING + KR suffix + non-dummy, split by suffix.

    KOSPI tickers end in ``.KS``, KOSDAQ in ``.KQ``. This mirrors
    ``report_scan_cohort_performance._load_rows`` so the gate measures the exact same
    rows the forward cohort numbers were computed on.
    """
    ticker = df.get("ticker", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    scan_mode = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    suffix = ".KS" if str(market).upper() == "KOSPI" else ".KQ"
    mask = scan_mode.eq("SWING") & ticker.str.endswith(suffix)
    if "is_dummy_data" in df.columns:
        is_dummy = df["is_dummy_data"].map(
            lambda v: str(v).strip().lower() in ("1", "true", "t", "yes")
        )
        mask &= ~is_dummy.fillna(False)
    return df.loc[mask].copy()


def _practical_80_levels() -> list:
    """Levels counted as Practical-80. `watch` is the only theme level that survived OOS in the
    2026-05 regime-shift test (n=13, 69% win, +24% avg) while pass/near/small_sample vanished, so
    it is included by default (toggle AG_PRACTICAL80_INCLUDE_WATCH=0 to revert)."""
    base = ["pass", "near", "small_sample"]
    if os.getenv("AG_PRACTICAL80_INCLUDE_WATCH", "1").strip() not in ("0", "", "false", "False"):
        base.append("watch")
    return base


def _practical_80_mask(df: pd.DataFrame) -> pd.Series:
    levels = [
        str((evaluate_practical_entry_gate(row) or {}).get("level") or "")
        for row in df.to_dict("records")
    ]
    series = pd.Series(levels, index=df.index)
    return series.isin(_practical_80_levels())


# 5D horizon: the cohort alpha (and the 75%/15% target) lives on the 5-day path.
COHORT_CONFIG: Dict[str, Dict[str, Any]] = {
    "EXCEPTION_LEADER": {
        "mask": _exception_leader_mask,
        "horizon": "5d",
        "return_col": "return_5d_pct",
    },
    "PRACTICAL_80": {
        "mask": _practical_80_mask,
        "horizon": "5d",
        "return_col": "return_5d_pct",
    },
}


# ---------------------------------------------------------------------------
# Walk-forward per cohort
# ---------------------------------------------------------------------------

def _walkforward_cohort(
    df: pd.DataFrame,
    cohort: str,
    config: Dict[str, Any],
    thresholds: Dict[str, float],
    confidence: float,
    bootstrap_iters: int,
) -> Dict[str, Any]:
    return_col = str(config["return_col"])
    mask_fn: Callable[[pd.DataFrame], pd.Series] = config["mask"]

    work = df.copy()
    if return_col not in work.columns:
        work[return_col] = pd.NA
    work = work[mask_fn(work)].copy()
    work = work[pd.to_numeric(work[return_col], errors="coerce").notna()]

    avg_return_daily: List[float] = []
    positive_daily: List[float] = []
    avoid_down_daily: List[float] = []
    hit10_daily: List[float] = []
    active_days = 0
    total_rows = 0

    for date, day_df in work.groupby("trade_date", dropna=False):
        if not str(date) or str(date) in ("nan", "") or len(str(date)) < 8:
            continue
        returns = pd.to_numeric(day_df[return_col], errors="coerce").dropna()
        if returns.empty:
            continue
        active_days += 1
        total_rows += int(len(returns))
        avg_return_daily.append(float(returns.mean()))
        positive_daily.append(float((returns > 0).mean()))
        avoid_down_daily.append(float((returns >= 0).mean()))

        if "max_high_return_5d_pct" in day_df.columns:
            mh = pd.to_numeric(day_df["max_high_return_5d_pct"], errors="coerce").dropna()
            if not mh.empty:
                hit10_daily.append(float((mh >= 10.0).mean()))
        elif "label_hit_10pct" in day_df.columns:
            h = pd.to_numeric(day_df["label_hit_10pct"], errors="coerce").fillna(0)
            hit10_daily.append(float((h >= 1).mean()))

    ci_avg = _bootstrap_ci(avg_return_daily, confidence, bootstrap_iters, seed=131)
    ci_positive = _bootstrap_ci(positive_daily, confidence, bootstrap_iters, seed=137)
    ci_avoid = _bootstrap_ci(avoid_down_daily, confidence, bootstrap_iters, seed=141)
    ci_hit10 = _bootstrap_ci(hit10_daily, confidence, bootstrap_iters, seed=143)

    horizon = str(config["horizon"]).upper()
    # EV + tail gate philosophy (locked by operator decision): the hard promotion gate is
    #   sample sufficiency + expected-value (avg return lower bound clears friction) + tail
    #   safety (avoid_down lower bound). Raw win-rate (positive_rate) and hit10 are REPORTED
    #   but are NOT hard gates -- consistent with the EV-over-hit-rate thesis (a cohort that
    #   lets winners run can be highly profitable at <50% raw win-rate).
    checks = [
        {**_check(
            active_days >= int(thresholds["min_active_days"]),
            f"{cohort}_MIN_ACTIVE_DAYS",
            f"active_days={active_days} (min={int(thresholds['min_active_days'])})",
        ), "gate": True},
        {**_check(
            float(ci_avg["lower"]) >= float(thresholds["min_avg_return_lower"]),
            f"{cohort}_AVG_{horizon}_LOWER",
            f"avg_{config['horizon']}_lower={ci_avg['lower']:+.4f}% (min={thresholds['min_avg_return_lower']:+.2f}%)",
        ), "gate": True},
        {**_check(
            float(ci_avoid["lower"]) >= float(thresholds["min_avoid_down_lower"]),
            f"{cohort}_AVOID_DOWN_{horizon}_LOWER",
            f"avoid_down_{config['horizon']}_lower={ci_avoid['lower'] * 100:.2f}% (min={thresholds['min_avoid_down_lower'] * 100:.0f}%)",
        ), "gate": True},
        {**_check(
            float(ci_positive["lower"]) >= float(thresholds["min_positive_lower"]),
            f"{cohort}_POSITIVE_{horizon}_LOWER",
            f"positive_{config['horizon']}_lower={ci_positive['lower'] * 100:.2f}% (min={thresholds['min_positive_lower'] * 100:.0f}%)",
        ), "gate": False},
        {**_check(
            float(ci_hit10["lower"]) >= float(thresholds["min_precision_hit10_lower"]),
            f"{cohort}_HIT10_{horizon}_LOWER",
            f"hit10_{config['horizon']}_lower={ci_hit10['lower'] * 100:.2f}%",
        ), "gate": False},
    ]

    gate_checks = [c for c in checks if c.get("gate")]
    return {
        "cohort": cohort,
        "horizon": str(config["horizon"]),
        "active_days": active_days,
        "total_rows": total_rows,
        "avg_return": ci_avg,
        "positive_rate": ci_positive,
        "avoid_down_rate": ci_avoid,
        "hit10_rate": ci_hit10,
        "checks": checks,
        "passed": all(c["passed"] for c in gate_checks),
    }


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------

def build_report(
    df: pd.DataFrame,
    market: str,
    confidence: float,
    bootstrap_iters: int,
    thresholds: Dict[str, float],
) -> Dict[str, Any]:
    cohorts: Dict[str, Any] = {}
    for name, config in COHORT_CONFIG.items():
        cohorts[name] = _walkforward_cohort(
            df, name, config, thresholds, confidence, bootstrap_iters
        )

    release_ready = all(c["passed"] for c in cohorts.values())
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": str(market).upper(),
        "confidence_level": float(confidence),
        "thresholds": thresholds,
        "release_ready": bool(release_ready),
        "cohorts": cohorts,
    }


def build_markdown(report: Dict[str, Any]) -> str:
    status = "PASS" if report["release_ready"] else "FAIL"
    lines = [
        f"# KR Cohort Release Gate ({report['market']})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- confidence_level: {report['confidence_level']:.2%}",
        f"- release_ready: **{status}**",
        f"- thresholds: {json.dumps(report['thresholds'], ensure_ascii=False)}",
        "",
    ]
    for name, c in report.get("cohorts", {}).items():
        cstatus = "PASS" if c["passed"] else "FAIL"
        h = c["horizon"]
        lines.extend([
            f"## Cohort: {name} [{cstatus}]",
            "",
            f"- active_days: {c['active_days']} | total_rows: {c['total_rows']}",
            f"- avg_{h}_return: mean={c['avg_return']['mean']:+.2f}%  "
            f"CI [{c['avg_return']['lower']:+.2f}%, {c['avg_return']['upper']:+.2f}%]",
            f"- positive_{h}: mean={c['positive_rate']['mean']:.2%}  "
            f"CI [{c['positive_rate']['lower']:.2%}, {c['positive_rate']['upper']:.2%}]",
            f"- avoid_down_{h}: mean={c['avoid_down_rate']['mean']:.2%}  "
            f"CI [{c['avoid_down_rate']['lower']:.2%}, {c['avoid_down_rate']['upper']:.2%}]",
            f"- hit10_{h}: mean={c['hit10_rate']['mean']:.2%}  "
            f"CI [{c['hit10_rate']['lower']:.2%}, {c['hit10_rate']['upper']:.2%}]",
            "",
            "### Checks (GATE = hard promotion gate, info = reported only)",
        ])
        for chk in c["checks"]:
            mark = "PASS" if chk["passed"] else "FAIL"
            kind = "GATE" if chk.get("gate") else "info"
            lines.append(f"- [{mark}][{kind}] {chk['code']}: {chk['detail']}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="KR cohort walk-forward release gate (principled CI).")
    parser.add_argument("--market", choices=["KOSPI", "KOSDAQ"], required=True)
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--input-stem", default="scan_archive_learning_dataset_all",
                        help="combined archive stem; market is split by KR ticker suffix")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--bootstrap-iters", type=int, default=4000)
    parser.add_argument("--min-active-days", type=int, default=12)
    # Promotion bar (applied to bootstrap LOWER bound, i.e. true at `confidence`):
    parser.add_argument("--min-avg-return-lower", type=float, default=0.4,
                        help="min 5D avg return lower bound (pct); 0.4 ~ clears KR round-trip friction")
    parser.add_argument("--min-positive-lower", type=float, default=0.50,
                        help="min positive-rate lower bound (fraction); 0.50 = majority wins")
    parser.add_argument("--min-avoid-down-lower", type=float, default=0.50)
    parser.add_argument("--min-precision-hit10-lower", type=float, default=0.0)
    args = parser.parse_args()

    thresholds = {
        "min_active_days": int(args.min_active_days),
        "min_avg_return_lower": float(args.min_avg_return_lower),
        "min_positive_lower": float(args.min_positive_lower),
        "min_avoid_down_lower": float(args.min_avoid_down_lower),
        "min_precision_hit10_lower": float(args.min_precision_hit10_lower),
    }

    market = str(args.market).upper()
    input_path = Path(args.input_dir) / f"{args.input_stem}.csv"
    df = _load_cohort_rows(input_path, market)

    report = build_report(
        df=df,
        market=market,
        confidence=float(args.confidence),
        bootstrap_iters=int(args.bootstrap_iters),
        thresholds=thresholds,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"kr_cohort_release_gate_{market.lower()}.json"
    md_path = out_dir / f"kr_cohort_release_gate_{market.lower()}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(json.dumps({
        "json_path": str(json_path),
        "md_path": str(md_path),
        "market": market,
        "confidence": float(args.confidence),
        "release_ready": report["release_ready"],
        "cohorts": {name: c["passed"] for name, c in report["cohorts"].items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
