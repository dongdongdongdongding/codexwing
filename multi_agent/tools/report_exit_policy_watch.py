#!/usr/bin/env python3
"""Report tactical exit-policy watch lanes from the operational optimizer.

This report deliberately does not promote scanner logic. It separates candidates
that fail close-hold promotion gates from candidates whose exact target/stop
path looks strong enough to forward-track as a tactical exit-policy lane.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_OPTIMIZER_REPORTS = [
    Path("runtime_state/reports/experimental/operational_admission_optimizer_latest.json"),
    Path("runtime_state/reports/experimental/operational_admission_optimizer_kosdaq_theme_latest.json"),
]
DEFAULT_COHORT_REPORT = Path("runtime_state/reports/validation/scan_cohort_performance.json")
DEFAULT_OUTPUT_DIR = Path("runtime_state/reports/experimental")
REPORT_VERSION = "exit_policy_watch_v1"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
        if number != number:
            return default
        return number
    except Exception:
        return default


def _round(value: Any, digits: int = 4) -> float | None:
    number = _safe_float(value)
    return round(number, digits) if number is not None else None


def _fmt_pct(value: Any, *, signed: bool = True) -> str:
    number = _safe_float(value)
    if number is None:
        return "-"
    sign = "+" if signed and number >= 0 else ""
    return f"{sign}{number:.2f}%"


def _baseline_rows(cohort_report: Dict[str, Any], market: str) -> List[Dict[str, Any]]:
    market_payload = ((cohort_report.get("markets") or {}).get(market) or {})
    cohorts = market_payload.get("cohorts") if isinstance(market_payload.get("cohorts"), dict) else {}
    rows: List[Dict[str, Any]] = []
    for name in ["Top5", "Exception Leader", "Practical 80 Gate"]:
        cohort = cohorts.get(name) if isinstance(cohorts.get(name), dict) else {}
        h5 = ((cohort.get("horizons") or {}).get("5D") or {})
        path = cohort.get("path") or {}
        if not h5:
            continue
        rows.append(
            {
                "cohort": name,
                "n": h5.get("n"),
                "win_5d_pct": h5.get("win_pct"),
                "avg_5d_pct": h5.get("avg_pct"),
                "min_5d_pct": h5.get("min_pct"),
                "max_5d_pct": h5.get("max_pct"),
                "bad_path_pct": path.get("bad_path_pct"),
                "clean_riser_pct": path.get("clean_riser_pct"),
            }
        )
    return rows


def _combine_optimizer_reports(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    combined: Dict[str, Any] = {
        "generated_at": None,
        "evaluated_policies": 0,
        "top_policies": [],
        "source_reports": [],
    }
    by_key: Dict[tuple[Any, ...], Dict[str, Any]] = {}
    for report in reports:
        if not report:
            continue
        combined["source_reports"].append(
            {
                "generated_at": report.get("generated_at"),
                "evaluated_policies": report.get("evaluated_policies"),
                "promotable_count": report.get("promotable_count"),
            }
        )
        if report.get("generated_at"):
            combined["generated_at"] = report.get("generated_at")
        combined["evaluated_policies"] = int(combined.get("evaluated_policies") or 0) + int(report.get("evaluated_policies") or 0)
        for policy in report.get("top_policies") or []:
            if not isinstance(policy, dict):
                continue
            label_profile = policy.get("label_profile") if isinstance(policy.get("label_profile"), dict) else {}
            key = (
                policy.get("market"),
                policy.get("cohort"),
                label_profile.get("name"),
                policy.get("policy_type"),
                policy.get("model"),
                policy.get("feature_set"),
                policy.get("topn"),
            )
            by_key[key] = policy
    combined["top_policies"] = list(by_key.values())
    return combined


def _watch_state(row: Dict[str, Any], *, min_n: int, min_days: int, min_net_avg_pct: float) -> str:
    if int(row.get("n") or 0) < min_n or int(row.get("days") or 0) < min_days:
        return "FORWARD_TRACK_SMALL_SAMPLE"
    if _safe_float(row.get("net_exit_avg_5d_pct"), -999.0) < min_net_avg_pct:
        return "FORWARD_TRACK_LOW_NET_AVG"
    return "EXIT_POLICY_READY_REVIEW"


def _state_rank(state: Any) -> int:
    return {
        "EXIT_POLICY_READY_REVIEW": 3,
        "FORWARD_TRACK_LOW_NET_AVG": 2,
        "FORWARD_TRACK_SMALL_SAMPLE": 1,
    }.get(str(state or ""), 0)


def build_report(
    optimizer_report: Dict[str, Any],
    cohort_report: Dict[str, Any],
    *,
    friction_pct: float = 0.35,
    min_n: int = 80,
    min_days: int = 20,
    min_net_avg_pct: float = 3.0,
) -> Dict[str, Any]:
    policies = optimizer_report.get("top_policies") if isinstance(optimizer_report.get("top_policies"), list) else []
    watch_rows: List[Dict[str, Any]] = []
    blocked_rows: List[Dict[str, Any]] = []
    for policy in policies:
        if not isinstance(policy, dict):
            continue
        promotion = policy.get("promotion") if isinstance(policy.get("promotion"), dict) else {}
        metrics = policy.get("metrics") if isinstance(policy.get("metrics"), dict) else {}
        exit_win = _safe_float(metrics.get("win_ordered_exit_5d_pct"), 0.0) or 0.0
        gross_avg = _safe_float(metrics.get("avg_ordered_exit_5d_pct"), -999.0)
        exit_min = _safe_float(metrics.get("min_ordered_exit_5d_pct"), -999.0)
        stop_first = _safe_float(metrics.get("stop_before_target_5d_pct"), 100.0)
        exit_metric_candidate = bool(exit_win >= 80.0 and gross_avg >= 3.0 and exit_min >= -5.0 and stop_first <= 10.0)
        if not promotion.get("exit_policy_watch") and not (
            exit_metric_candidate and "path_warning_gate" in set(promotion.get("failed_checks") or [])
        ):
            continue
        label_profile = policy.get("label_profile") if isinstance(policy.get("label_profile"), dict) else {}
        net_avg = gross_avg - friction_pct if gross_avg is not None else None
        row = {
            "market": policy.get("market"),
            "cohort": policy.get("cohort"),
            "label": label_profile.get("name"),
            "policy_type": policy.get("policy_type"),
            "model": policy.get("model"),
            "feature_set": policy.get("feature_set"),
            "topn": policy.get("topn"),
            "n": metrics.get("n"),
            "days": metrics.get("active_days"),
            "label_win_pct": metrics.get("label_win_pct"),
            "close_avg_5d_pct": metrics.get("avg_5d_pct"),
            "close_min_5d_pct": metrics.get("min_5d_pct"),
            "target_before_stop_5d_pct": metrics.get("target_before_stop_5d_pct"),
            "stop_before_target_5d_pct": metrics.get("stop_before_target_5d_pct"),
            "ordered_path_label_version": metrics.get("ordered_path_label_version"),
            "outcome_path_sources": metrics.get("outcome_path_sources") or {},
            "outcome_path_warning_pct": metrics.get("outcome_path_warning_pct"),
            "exit_policy_target_pct": metrics.get("exit_policy_target_pct"),
            "exit_policy_stop_pct": metrics.get("exit_policy_stop_pct"),
            "exit_win_5d_pct": metrics.get("win_ordered_exit_5d_pct"),
            "gross_exit_avg_5d_pct": metrics.get("avg_ordered_exit_5d_pct"),
            "net_exit_avg_5d_pct": _round(net_avg),
            "exit_min_5d_pct": metrics.get("min_ordered_exit_5d_pct"),
            "failed_checks": list(promotion.get("failed_checks") or []),
            "quality_score": policy.get("quality_score"),
        }
        if promotion.get("exit_policy_watch"):
            row["state"] = _watch_state(row, min_n=min_n, min_days=min_days, min_net_avg_pct=min_net_avg_pct)
            watch_rows.append(row)
        else:
            row["state"] = "BLOCKED_PATH_WARNING"
            blocked_rows.append(row)
    watch_rows.sort(
        key=lambda item: (
            _state_rank(item.get("state")),
            int(item.get("n") or 0),
            int(item.get("days") or 0),
            _safe_float(item.get("net_exit_avg_5d_pct"), -999.0),
            _safe_float(item.get("exit_win_5d_pct"), -999.0),
            _safe_float(item.get("quality_score"), -999.0),
        ),
        reverse=True,
    )
    blocked_rows.sort(
        key=lambda item: (
            int(item.get("n") or 0),
            int(item.get("days") or 0),
            _safe_float(item.get("outcome_path_warning_pct"), 100.0) * -1.0,
            _safe_float(item.get("net_exit_avg_5d_pct"), -999.0),
        ),
        reverse=True,
    )
    markets = sorted({str(row.get("market") or "") for row in watch_rows if row.get("market")})
    markets = sorted(set(markets) | {str(row.get("market") or "") for row in blocked_rows if row.get("market")})
    baselines = {market: _baseline_rows(cohort_report, market) for market in markets}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_version": REPORT_VERSION,
        "friction_pct": friction_pct,
        "min_n": min_n,
        "min_days": min_days,
        "min_net_avg_pct": min_net_avg_pct,
        "optimizer_generated_at": optimizer_report.get("generated_at"),
        "optimizer_evaluated_policies": optimizer_report.get("evaluated_policies"),
        "watch_count": len(watch_rows),
        "blocked_path_warning_count": len(blocked_rows),
        "ready_review_count": sum(1 for row in watch_rows if row.get("state") == "EXIT_POLICY_READY_REVIEW"),
        "watch_rows": watch_rows,
        "blocked_path_warning_rows": blocked_rows,
        "baselines": baselines,
        "notes": [
            "EXIT-WATCH is not a production scanner replacement.",
            "Close-hold failures remain visible through failed_checks and close_avg/min fields.",
            "Net exit average subtracts configured friction_pct for fees/slippage/tax approximation.",
        ],
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Exit Policy Watch",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- report_version: `{report.get('report_version')}`",
        f"- optimizer_generated_at: `{report.get('optimizer_generated_at')}`",
        f"- friction_pct: `{report.get('friction_pct')}`",
        f"- watch_count: `{report.get('watch_count')}`",
        f"- blocked_path_warning_count: `{report.get('blocked_path_warning_count')}`",
        f"- ready_review_count: `{report.get('ready_review_count')}`",
        "",
        "## Watch Rows",
        "",
        "| Rank | State | Market | Cohort | Label | Model | TopN | N | Days | Target | Stop | Exit Win | Net Exit Avg | Exit Min | Close Avg5 | Close Min5 | Stop First | Path Warn | Failed Checks |",
        "|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, row in enumerate(report.get("watch_rows") or [], start=1):
        lines.append(
            "| "
            + " | ".join(
                str(value)
                for value in [
                    rank,
                    row.get("state"),
                    row.get("market"),
                    row.get("cohort"),
                    row.get("label"),
                    row.get("model"),
                    row.get("topn"),
                    row.get("n"),
                    row.get("days"),
                    _fmt_pct(row.get("exit_policy_target_pct")),
                    _fmt_pct(row.get("exit_policy_stop_pct")),
                    _fmt_pct(row.get("exit_win_5d_pct"), signed=False),
                    _fmt_pct(row.get("net_exit_avg_5d_pct")),
                    _fmt_pct(row.get("exit_min_5d_pct")),
                    _fmt_pct(row.get("close_avg_5d_pct")),
                    _fmt_pct(row.get("close_min_5d_pct")),
                    _fmt_pct(row.get("stop_before_target_5d_pct"), signed=False),
                    _fmt_pct(row.get("outcome_path_warning_pct"), signed=False),
                    ",".join(str(item) for item in (row.get("failed_checks") or [])) or "-",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Blocked By Path Warning", ""])
    lines.append("| Rank | Market | Cohort | Label | Model | TopN | N | Days | Exit Win | Net Exit Avg | Path Warn | Failed Checks |")
    lines.append("|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|")
    for rank, row in enumerate((report.get("blocked_path_warning_rows") or [])[:30], start=1):
        lines.append(
            "| "
            + " | ".join(
                str(value)
                for value in [
                    rank,
                    row.get("market"),
                    row.get("cohort"),
                    row.get("label"),
                    row.get("model"),
                    row.get("topn"),
                    row.get("n"),
                    row.get("days"),
                    _fmt_pct(row.get("exit_win_5d_pct"), signed=False),
                    _fmt_pct(row.get("net_exit_avg_5d_pct")),
                    _fmt_pct(row.get("outcome_path_warning_pct"), signed=False),
                    ",".join(str(item) for item in (row.get("failed_checks") or [])) or "-",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Baselines", ""])
    for market, rows in (report.get("baselines") or {}).items():
        lines.extend([f"### {market}", "", "| Cohort | N | Win5 | Avg5 | Min5 | Max5 | Bad Path | Clean Riser |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
        for row in rows:
            lines.append(
                "| "
                + " | ".join(
                    str(value)
                    for value in [
                        row.get("cohort"),
                        row.get("n"),
                        _fmt_pct(row.get("win_5d_pct"), signed=False),
                        _fmt_pct(row.get("avg_5d_pct")),
                        _fmt_pct(row.get("min_5d_pct")),
                        _fmt_pct(row.get("max_5d_pct")),
                        _fmt_pct(row.get("bad_path_pct"), signed=False),
                        _fmt_pct(row.get("clean_riser_pct"), signed=False),
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.extend(["## Notes"])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report tactical exit-policy watch lanes.")
    parser.add_argument("--optimizer-report", action="append", default=None)
    parser.add_argument("--cohort-report", default=str(DEFAULT_COHORT_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--stem", default="exit_policy_watch_latest")
    parser.add_argument("--friction-pct", type=float, default=0.35)
    parser.add_argument("--min-n", type=int, default=80)
    parser.add_argument("--min-days", type=int, default=20)
    parser.add_argument("--min-net-avg-pct", type=float, default=3.0)
    args = parser.parse_args()

    optimizer_paths = [Path(item) for item in (args.optimizer_report or [str(path) for path in DEFAULT_OPTIMIZER_REPORTS])]
    optimizer = _combine_optimizer_reports([_load_json(path) for path in optimizer_paths])
    cohort = _load_json(Path(args.cohort_report))
    report = build_report(
        optimizer,
        cohort,
        friction_pct=float(args.friction_pct),
        min_n=int(args.min_n),
        min_days=int(args.min_days),
        min_net_avg_pct=float(args.min_net_avg_pct),
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{args.stem}.json"
    md_path = out_dir / f"{args.stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "md": str(md_path), "watch_count": report["watch_count"], "ready_review_count": report["ready_review_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
