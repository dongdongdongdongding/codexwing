#!/usr/bin/env python3
"""Walk-forward 98% CI release gate for KR markets.

Evaluates KOSPI/KOSDAQ promotion readiness by lane:
  - EXPLOSIVE_LEADER (1D lane): top10 daily, checks avg_1d, positive_1d, avoid_down_1d, precision_hit10
  - CORE_TREND (3D lane): top5 daily, checks avg_3d, positive_3d, avoid_down_3d, precision_hit10

Walk-forward: group by date, rank by decision_score within lane, take topN, compute daily
metric vectors, then bootstrap CI at requested confidence level (default 0.98).

Gate passes only if ALL lane checks pass.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.report_kr_top_mover_capture import _load_archive


# ---------------------------------------------------------------------------
# Lane config
# ---------------------------------------------------------------------------

LANE_CONFIG: Dict[str, Dict[str, Any]] = {
    "EXPLOSIVE_LEADER": {
        "topn": 10,
        "horizon": "1d",
        "return_col": "return_1d_pct",
        "min_active_days": 3,
        # gate thresholds (applied to bootstrap lower bound)
        "min_avg_return_lower": 0.0,
        "min_positive_lower": 0.45,
        "min_avoid_down_lower": 0.45,
        "min_precision_hit10_lower": 0.0,
    },
    "CORE_TREND": {
        "topn": 5,
        "horizon": "3d",
        "return_col": "return_3d_pct",
        "min_active_days": 3,
        "min_avg_return_lower": 0.0,
        "min_positive_lower": 0.45,
        "min_avoid_down_lower": 0.45,
        "min_precision_hit10_lower": 0.0,
    },
}


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _quantile(sorted_values: List[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = max(0.0, min(1.0, q)) * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_values[lo])
    return float(sorted_values[lo] * (1.0 - (pos - lo)) + sorted_values[hi] * (pos - lo))


def _bootstrap_ci(
    values: List[float],
    confidence: float,
    iterations: int,
    seed: int,
) -> Dict[str, float]:
    sample = [v for v in values if v is not None and not math.isnan(v)]
    if not sample:
        return {"mean": 0.0, "lower": 0.0, "upper": 0.0, "samples": 0}
    if len(sample) == 1:
        v = round(sample[0], 6)
        return {"mean": v, "lower": v, "upper": v, "samples": 1}
    rng = random.Random(seed)
    n = len(sample)
    means: List[float] = []
    for _ in range(max(200, int(iterations))):
        drawn = [sample[rng.randrange(n)] for _ in range(n)]
        means.append(sum(drawn) / n)
    means.sort()
    alpha = (1.0 - confidence) / 2.0
    return {
        "mean": round(sum(sample) / n, 6),
        "lower": round(_quantile(means, alpha), 6),
        "upper": round(_quantile(means, 1.0 - alpha), 6),
        "samples": n,
    }


def _check(condition: bool, code: str, detail: str) -> Dict[str, Any]:
    return {"code": code, "passed": bool(condition), "detail": detail}


# ---------------------------------------------------------------------------
# Walk-forward per lane
# ---------------------------------------------------------------------------

def _walkforward_lane(
    df: pd.DataFrame,
    lane: str,
    config: Dict[str, Any],
    confidence: float,
    bootstrap_iters: int,
) -> Dict[str, Any]:
    """Compute walk-forward metrics for one lane."""
    return_col = str(config["return_col"])
    topn = int(config["topn"])

    # Filter to lane rows that have a decision_score
    lane_df = df[df["kr_universe_role"] == lane].copy() if "kr_universe_role" in df.columns else df.copy()
    lane_df = lane_df.dropna(subset=["decision_score"])

    # Require return column to be present (PENDING rows may not have it)
    if return_col in lane_df.columns:
        lane_df = lane_df[lane_df[return_col].notna()]

    avg_return_daily: List[float] = []
    positive_daily: List[float] = []
    avoid_down_daily: List[float] = []
    precision_hit10_daily: List[float] = []
    active_days = 0
    total_rows = 0

    for date, day_df in lane_df.groupby("trade_date", dropna=False):
        if not str(date) or str(date) in ("nan", ""):
            continue
        ordered = day_df.sort_values("decision_score", ascending=False, na_position="last")
        top = ordered.head(topn)
        if top.empty:
            continue

        returns = pd.to_numeric(top[return_col], errors="coerce").dropna()
        if returns.empty:
            continue

        active_days += 1
        total_rows += int(len(returns))
        avg_return_daily.append(float(returns.mean()))
        positive_daily.append(float((returns > 0).mean()))
        avoid_down_daily.append(float((returns >= 0).mean()))

        if "label_hit_10pct" in top.columns:
            hits = pd.to_numeric(top["label_hit_10pct"], errors="coerce").fillna(0)
            precision_hit10_daily.append(float((hits >= 1).mean()))

    ci_avg = _bootstrap_ci(avg_return_daily, confidence, bootstrap_iters, seed=31)
    ci_positive = _bootstrap_ci(positive_daily, confidence, bootstrap_iters, seed=37)
    ci_avoid = _bootstrap_ci(avoid_down_daily, confidence, bootstrap_iters, seed=41)
    ci_hit10 = _bootstrap_ci(precision_hit10_daily, confidence, bootstrap_iters, seed=43)

    return {
        "lane": lane,
        "topn": topn,
        "horizon": str(config["horizon"]),
        "active_days": active_days,
        "total_rows": total_rows,
        "avg_return": ci_avg,
        "positive_rate": ci_positive,
        "avoid_down_rate": ci_avoid,
        "precision_hit10": ci_hit10,
    }


def _gate_checks_for_lane(
    metrics: Dict[str, Any],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    lane = str(metrics["lane"])
    min_days = int(config["min_active_days"])
    horizon = str(config["horizon"])

    checks = [
        _check(
            int(metrics["active_days"]) >= min_days,
            f"{lane}_MIN_ACTIVE_DAYS",
            f"active_days={metrics['active_days']} (min={min_days})",
        ),
        _check(
            float(metrics["avg_return"]["lower"]) >= float(config["min_avg_return_lower"]),
            f"{lane}_AVG_{horizon.upper()}_LOWER",
            f"avg_{horizon}_lower={metrics['avg_return']['lower']:+.4f}%",
        ),
        _check(
            float(metrics["positive_rate"]["lower"]) >= float(config["min_positive_lower"]),
            f"{lane}_POSITIVE_{horizon.upper()}_LOWER",
            f"positive_{horizon}_lower={metrics['positive_rate']['lower'] * 100:.2f}%",
        ),
        _check(
            float(metrics["avoid_down_rate"]["lower"]) >= float(config["min_avoid_down_lower"]),
            f"{lane}_AVOID_DOWN_{horizon.upper()}_LOWER",
            f"avoid_down_{horizon}_lower={metrics['avoid_down_rate']['lower'] * 100:.2f}%",
        ),
        _check(
            float(metrics["precision_hit10"]["lower"]) >= float(config["min_precision_hit10_lower"]),
            f"{lane}_PRECISION_HIT10_LOWER",
            f"precision_hit10_lower={metrics['precision_hit10']['lower'] * 100:.2f}%",
        ),
    ]
    return checks


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def build_report(
    df: pd.DataFrame,
    market: str,
    confidence: float,
    bootstrap_iters: int,
    lane_config: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if lane_config is None:
        lane_config = LANE_CONFIG

    lane_results: Dict[str, Any] = {}
    all_checks: List[Dict[str, Any]] = []

    for lane, config in lane_config.items():
        metrics = _walkforward_lane(df, lane, config, confidence, bootstrap_iters)
        checks = _gate_checks_for_lane(metrics, config)
        lane_results[lane] = {
            "metrics": metrics,
            "checks": checks,
            "passed": all(c["passed"] for c in checks),
        }
        all_checks.extend(checks)

    release_ready = all(c["passed"] for c in all_checks)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": str(market).upper(),
        "confidence_level": float(confidence),
        "release_ready": bool(release_ready),
        "lanes": lane_results,
        "all_checks": all_checks,
    }


# ---------------------------------------------------------------------------
# Markdown builder
# ---------------------------------------------------------------------------

def build_markdown(report: Dict[str, Any]) -> str:
    status = "PASS" if report["release_ready"] else "FAIL"
    lines = [
        f"# KR Walk-forward Release Gate ({report['market']})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- confidence_level: {report['confidence_level']:.2%}",
        f"- release_ready: **{status}**",
        "",
    ]

    for lane_name, lane_data in report.get("lanes", {}).items():
        m = lane_data["metrics"]
        lane_status = "PASS" if lane_data["passed"] else "FAIL"
        lines.extend([
            f"## Lane: {lane_name} [{lane_status}]",
            "",
            f"- topn: {m['topn']} | horizon: {m['horizon']}",
            f"- active_days: {m['active_days']} | total_rows: {m['total_rows']}",
            f"- avg_{m['horizon']}_return: mean={m['avg_return']['mean']:+.2f}%  "
            f"CI [{m['avg_return']['lower']:+.2f}%, {m['avg_return']['upper']:+.2f}%]",
            f"- positive_{m['horizon']}: mean={m['positive_rate']['mean']:.2%}  "
            f"CI [{m['positive_rate']['lower']:.2%}, {m['positive_rate']['upper']:.2%}]",
            f"- avoid_down_{m['horizon']}: mean={m['avoid_down_rate']['mean']:.2%}  "
            f"CI [{m['avoid_down_rate']['lower']:.2%}, {m['avoid_down_rate']['upper']:.2%}]",
            f"- precision_hit10: mean={m['precision_hit10']['mean']:.2%}  "
            f"CI [{m['precision_hit10']['lower']:.2%}, {m['precision_hit10']['upper']:.2%}]",
            "",
            "### Checks",
        ])
        for chk in lane_data["checks"]:
            mark = "PASS" if chk["passed"] else "FAIL"
            lines.append(f"- [{mark}] {chk['code']}: {chk['detail']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="KR walk-forward 98% CI release gate.")
    parser.add_argument("--market", choices=["KOSPI", "KOSDAQ"], required=True)
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    parser.add_argument("--confidence", type=float, default=0.98)
    parser.add_argument("--bootstrap-iters", type=int, default=4000)
    args = parser.parse_args()

    market = str(args.market).upper()
    input_path = Path(args.input_dir) / f"scan_archive_learning_dataset_{market.lower()}.csv"
    df = _load_archive(input_path)

    report = build_report(
        df=df,
        market=market,
        confidence=float(args.confidence),
        bootstrap_iters=int(args.bootstrap_iters),
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"kr_walkforward_release_gate_{market.lower()}.json"
    md_path = out_dir / f"kr_walkforward_release_gate_{market.lower()}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "market": market,
                "release_ready": report["release_ready"],
                "lane_results": {
                    lane: data["passed"] for lane, data in report["lanes"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
