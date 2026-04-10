from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from multi_agent.workflows.outcome_buckets import (
    MEASURED_OUTCOME_BUCKETS,
    finalize_bucket_stats,
    init_bucket_stats,
    resolve_outcome_bucket,
)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _parse_iso_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except Exception:
            pass
        try:
            return date.fromisoformat(text[:10])
        except Exception:
            return None
    return None


def _count_outcome_status(rows: List[Dict[str, Any]], status: str) -> int:
    target = str(status).upper()
    count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).upper() == target:
            count += 1
    return count


def _count_fallback_rows(rows: List[Dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("decision", "")).upper() == "FALLBACK_WATCHLIST":
            count += 1
    return count


def _update_bucket_stats(stats: Dict[str, Dict[str, Any]], row: Dict[str, Any]) -> None:
    bucket = resolve_outcome_bucket(row)
    if bucket not in MEASURED_OUTCOME_BUCKETS:
        return
    status = str(row.get("status", "")).upper()
    bucket_row = stats[bucket]
    bucket_row["total"] += 1
    if status == "RESOLVED":
        bucket_row["resolved"] += 1
    elif status == "EXPIRED":
        bucket_row["expired"] += 1
    elif status == "PENDING":
        bucket_row["pending"] += 1


def _init_return_bucket_stats() -> Dict[str, Dict[str, Dict[str, float]]]:
    return {
        bucket: {
            (f"{horizon}d" if isinstance(horizon, int) else str(horizon)): {
                "samples": 0,
                "avg_return_pct": 0.0,
                "win_rate_pct": 0.0,
            }
            for horizon in ("30m", "1h", "close", 1, 2, 3, 5, 7)
        }
        for bucket in MEASURED_OUTCOME_BUCKETS
    }


def _update_return_bucket_stats(stats: Dict[str, Dict[str, Dict[str, float]]], row: Dict[str, Any]) -> None:
    bucket = resolve_outcome_bucket(row)
    if bucket not in MEASURED_OUTCOME_BUCKETS:
        return
    bucket_stats = stats[bucket]
    for horizon in ("30m", "1h", "close", 1, 2, 3, 5, 7):
        key = f"return_{horizon}d_pct" if isinstance(horizon, int) else (f"return_{horizon}_pct")
        try:
            value = row.get(key)
            if value is None or value == "":
                continue
            ret = float(value)
        except Exception:
            continue
        horizon_key = f"{horizon}d" if isinstance(horizon, int) else str(horizon)
        horizon_row = bucket_stats[horizon_key]
        horizon_row.setdefault("_values", [])
        horizon_row["_values"].append(ret)


def _finalize_return_bucket_stats(stats: Dict[str, Dict[str, Dict[str, float]]]) -> Dict[str, Dict[str, Dict[str, float]]]:
    for bucket in MEASURED_OUTCOME_BUCKETS:
        bucket_stats = stats.get(bucket, {})
        for horizon in ("30m", "1h", "close", 1, 2, 3, 5, 7):
            horizon_key = f"{horizon}d" if isinstance(horizon, int) else str(horizon)
            horizon_row = bucket_stats.get(horizon_key, {})
            values = horizon_row.pop("_values", [])
            samples = len(values)
            horizon_row["samples"] = int(samples)
            horizon_row["avg_return_pct"] = round(sum(values) / samples, 4) if samples > 0 else 0.0
            horizon_row["win_rate_pct"] = round((sum(1 for v in values if v > 0) / samples) * 100.0, 2) if samples > 0 else 0.0
            bucket_stats[horizon_key] = horizon_row
        stats[bucket] = bucket_stats
    return stats


def _extract_warning_codes(payload: Dict[str, Any], key: str = "warnings") -> List[str]:
    items = payload.get(key, [])
    if not isinstance(items, list):
        return []
    codes: List[str] = []
    for item in items:
        if isinstance(item, dict):
            code = str(item.get("code", "")).strip()
            if code:
                codes.append(code)
    return codes


def _resolve_run_date(scanner_payload: Dict[str, Any], profile_payload: Dict[str, Any]) -> Optional[date]:
    run_ctx = scanner_payload.get("run_context", {})
    if isinstance(run_ctx, dict):
        as_of_date = _parse_iso_date(run_ctx.get("as_of_date"))
        if as_of_date is not None:
            return as_of_date
        created_at = _parse_iso_date(run_ctx.get("created_at"))
        if created_at is not None:
            return created_at
    generated_at = _parse_iso_date(profile_payload.get("generated_at"))
    if generated_at is not None:
        return generated_at
    return None


def build_daily_summary(
    *,
    shared_dir: Path,
    target_date: str,
    market: str | None = None,
    limit_runs: int = 0,
) -> Dict[str, Any]:
    target = date.fromisoformat(str(target_date))
    market_filter = str(market or "").upper().strip()

    run_dirs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")] if shared_dir.exists() else []
    run_dirs = sorted(run_dirs, key=lambda p: p.name)
    if limit_runs > 0:
        run_dirs = run_dirs[-int(limit_runs) :]

    runs: List[Dict[str, Any]] = []
    warning_counter: Counter[str] = Counter()
    market_counts: Dict[str, int] = {}
    profile_counts: Dict[str, int] = {}
    total_candidates = 0
    total_decisions = 0
    total_watchlist = 0
    total_fallback_watchlist = 0
    total_outcomes = 0
    total_pending = 0
    total_resolved = 0
    total_expired = 0
    overall_bucket_stats = init_bucket_stats()
    overall_return_bucket_stats = _init_return_bucket_stats()

    for run_dir in run_dirs:
        scanner_payload = _load_json(run_dir / "scanner_handoff.json")
        if not scanner_payload:
            continue
        profile_payload = _load_json(run_dir / "profile_diagnostics.json")
        run_date = _resolve_run_date(scanner_payload, profile_payload)
        if run_date != target:
            continue

        run_ctx = scanner_payload.get("run_context", {})
        if not isinstance(run_ctx, dict):
            run_ctx = {}
        run_market = str(run_ctx.get("market", "")).upper()
        if market_filter and run_market != market_filter:
            continue

        planner_payload = _load_json(run_dir / "planner_handoff.json")
        backtest_payload = _load_json(run_dir / "backtest_handoff.json")
        market_payload = _load_json(run_dir / "market_context_handoff.json")
        outcomes_payload = _load_json(run_dir / "realized_outcomes.json")
        outcomes = outcomes_payload.get("outcomes", []) if isinstance(outcomes_payload.get("outcomes"), list) else []

        candidates = scanner_payload.get("candidates", []) if isinstance(scanner_payload.get("candidates"), list) else []
        decisions = planner_payload.get("decisions", []) if isinstance(planner_payload.get("decisions"), list) else []
        watchlist = planner_payload.get("watchlist", []) if isinstance(planner_payload.get("watchlist"), list) else []

        pending = _count_outcome_status(outcomes, "PENDING")
        resolved = _count_outcome_status(outcomes, "RESOLVED")
        expired = _count_outcome_status(outcomes, "EXPIRED")
        fallback_rows = _count_fallback_rows(outcomes)
        run_bucket_stats = init_bucket_stats()
        run_return_bucket_stats = _init_return_bucket_stats()
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            _update_bucket_stats(overall_bucket_stats, row)
            _update_bucket_stats(run_bucket_stats, row)
            _update_return_bucket_stats(overall_return_bucket_stats, row)
            _update_return_bucket_stats(run_return_bucket_stats, row)

        warning_codes: List[str] = []
        warning_codes.extend(_extract_warning_codes(scanner_payload, key="warnings"))
        warning_codes.extend(_extract_warning_codes(backtest_payload, key="warnings"))
        warning_codes.extend(_extract_warning_codes(market_payload, key="warnings"))
        warning_codes.extend(_extract_warning_codes(planner_payload, key="global_warnings"))
        warning_counter.update(warning_codes)

        current_profile = str(profile_payload.get("current_profile", "unknown")).lower()
        if not current_profile:
            current_profile = "unknown"

        market_counts[run_market] = int(market_counts.get(run_market, 0)) + 1
        profile_counts[current_profile] = int(profile_counts.get(current_profile, 0)) + 1
        total_candidates += len(candidates)
        total_decisions += len(decisions)
        total_watchlist += len(watchlist)
        total_fallback_watchlist += int(fallback_rows)
        total_outcomes += len(outcomes)
        total_pending += int(pending)
        total_resolved += int(resolved)
        total_expired += int(expired)
        finalize_bucket_stats(run_bucket_stats)
        _finalize_return_bucket_stats(run_return_bucket_stats)

        runs.append(
            {
                "run_id": run_dir.name,
                "market": run_market,
                "profile": current_profile,
                "candidate_count": len(candidates),
                "decision_count": len(decisions),
                "watchlist_count": len(watchlist),
                "fallback_outcome_count": int(fallback_rows),
                "outcomes_total": len(outcomes),
                "pending": int(pending),
                "resolved": int(resolved),
                "expired": int(expired),
                "bucket_breakdown": run_bucket_stats,
                "return_bucket_breakdown": run_return_bucket_stats,
                "warning_codes": warning_codes,
            }
        )

    top_warning_codes = [
        {"code": code, "count": int(count)} for code, count in warning_counter.most_common(10)
    ]
    finalize_bucket_stats(overall_bucket_stats)
    _finalize_return_bucket_stats(overall_return_bucket_stats)
    inferred_market: Optional[str] = None
    if market_filter:
        inferred_market = market_filter
    elif len(market_counts) == 1:
        inferred_market = next(iter(market_counts.keys()), None)
    bucket_counts = {
        bucket: int(((overall_bucket_stats.get(bucket, {}) or {}).get("total", 0) or 0))
        for bucket in MEASURED_OUTCOME_BUCKETS
    }
    outcome_status_counts = {
        "total": int(total_outcomes),
        "pending": int(total_pending),
        "resolved": int(total_resolved),
        "expired": int(total_expired),
        "closure_rate_pct": round(((total_resolved + total_expired) / total_outcomes * 100.0), 2)
        if total_outcomes > 0
        else 0.0,
    }
    return {
        "target_date": target.isoformat(),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "market": inferred_market,
        "total_runs": len(runs),
        "market_counts": market_counts,
        "profile_counts": profile_counts,
        "total_candidates": int(total_candidates),
        "total_decisions": int(total_decisions),
        "total_watchlist": int(total_watchlist),
        "total_fallback_watchlist_outcomes": int(total_fallback_watchlist),
        "outcomes": outcome_status_counts,
        "outcome_status_counts": outcome_status_counts,
        "bucket_counts": bucket_counts,
        "outcome_bucket_breakdown": overall_bucket_stats,
        "return_bucket_breakdown": overall_return_bucket_stats,
        "top_warning_codes": top_warning_codes,
        "runs": runs,
    }


def render_daily_summary_markdown(summary: Dict[str, Any]) -> str:
    outcomes = summary.get("outcomes", {}) if isinstance(summary.get("outcomes"), dict) else {}
    lines: List[str] = []
    lines.append(f"# Daily Agent Summary ({summary.get('target_date')})")
    lines.append("")
    lines.append(f"- Total runs: {summary.get('total_runs', 0)}")
    lines.append(f"- Markets: {summary.get('market_counts', {})}")
    lines.append(f"- Profiles: {summary.get('profile_counts', {})}")
    lines.append(f"- Total candidates: {summary.get('total_candidates', 0)}")
    lines.append(f"- Total decisions: {summary.get('total_decisions', 0)}")
    lines.append(f"- Total watchlist entries: {summary.get('total_watchlist', 0)}")
    lines.append(f"- Fallback watchlist outcomes: {summary.get('total_fallback_watchlist_outcomes', 0)}")
    bucket_breakdown = (
        summary.get("outcome_bucket_breakdown", {})
        if isinstance(summary.get("outcome_bucket_breakdown"), dict)
        else {}
    )
    if bucket_breakdown:
        lines.append("")
        lines.append("## Outcome Buckets")
        for bucket in MEASURED_OUTCOME_BUCKETS:
            row = bucket_breakdown.get(bucket, {}) if isinstance(bucket_breakdown.get(bucket), dict) else {}
            lines.append(
                f"- {bucket}: total={row.get('total', 0)} "
                f"(P={row.get('pending', 0)}, R={row.get('resolved', 0)}, E={row.get('expired', 0)}) "
                f"closure={row.get('closure_rate_pct', 0.0)}%"
            )
    return_bucket_breakdown = (
        summary.get("return_bucket_breakdown", {})
        if isinstance(summary.get("return_bucket_breakdown"), dict)
        else {}
    )
    if return_bucket_breakdown:
        lines.append("")
        lines.append("## Return Performance")
        for bucket in MEASURED_OUTCOME_BUCKETS:
            bucket_row = return_bucket_breakdown.get(bucket, {})
            if not isinstance(bucket_row, dict):
                continue
            perf_parts: List[str] = []
            for horizon in ("30m", "1h", "close", 1, 2, 3, 5, 7):
                horizon_key = f"{horizon}d" if isinstance(horizon, int) else str(horizon)
                horizon_row = bucket_row.get(horizon_key, {})
                if not isinstance(horizon_row, dict):
                    continue
                horizon_label = f"{horizon}d" if isinstance(horizon, int) else str(horizon)
                perf_parts.append(
                    f"{horizon_label} avg={horizon_row.get('avg_return_pct', 0.0):+.2f}% "
                    f"/ win={horizon_row.get('win_rate_pct', 0.0):.1f}% "
                    f"/ n={int(horizon_row.get('samples', 0) or 0)}"
                )
            lines.append(f"- {bucket}: " + " | ".join(perf_parts))
    delta = summary.get("delta_vs_prev_day", {}) if isinstance(summary.get("delta_vs_prev_day"), dict) else {}
    if delta:
        lines.append("")
        lines.append("## Delta vs Previous Day")
        for key in [
            "total_runs",
            "total_candidates",
            "total_decisions",
            "total_watchlist",
            "total_fallback_watchlist_outcomes",
            "bucket_picked_total",
            "bucket_watchlist_total",
            "bucket_exception_leader_total",
            "outcomes_total",
            "outcomes_pending",
            "outcomes_resolved",
            "outcomes_expired",
            "outcomes_closure_rate_pct",
        ]:
            if key in delta:
                lines.append(f"- {key}: {delta.get(key)}")
    lines.append("")
    lines.append("## Outcomes")
    lines.append(f"- Total: {outcomes.get('total', 0)}")
    lines.append(f"- Pending: {outcomes.get('pending', 0)}")
    lines.append(f"- Resolved: {outcomes.get('resolved', 0)}")
    lines.append(f"- Expired: {outcomes.get('expired', 0)}")
    lines.append(f"- Closure rate (%): {outcomes.get('closure_rate_pct', 0.0)}")
    lines.append("")
    lines.append("## Top Warning Codes")
    top = summary.get("top_warning_codes", [])
    if isinstance(top, list) and top:
        for row in top:
            if isinstance(row, dict):
                lines.append(f"- {row.get('code')}: {row.get('count')}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Run Breakdown")
    runs = summary.get("runs", [])
    if isinstance(runs, list) and runs:
        for row in runs:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"- {row.get('run_id')} | {row.get('market')} | {row.get('profile')} | "
                f"cand={row.get('candidate_count')} dec={row.get('decision_count')} "
                f"out={row.get('outcomes_total')} (P={row.get('pending')}, R={row.get('resolved')}, E={row.get('expired')})"
            )
    else:
        lines.append("- no runs")
    lines.append("")
    lines.append(f"_Generated at: {summary.get('generated_at')}_")
    return "\n".join(lines)


def write_daily_summary(
    *,
    summary: Dict[str, Any],
    output_dir: Path,
    target_date: str,
    market: str | None = None,
) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    market_suffix = ""
    if str(market or "").strip():
        market_suffix = f"_{str(market).strip().upper()}"
    try:
        d = date.fromisoformat(str(target_date))
        prev_date = (d - timedelta(days=1)).isoformat()
    except Exception:
        prev_date = ""
    if prev_date:
        prev_path = output_dir / f"daily_summary_{prev_date}{market_suffix}.json"
        prev_summary = _load_json(prev_path) if prev_path.exists() else {}
        if prev_summary:
            prev_out = prev_summary.get("outcomes", {}) if isinstance(prev_summary.get("outcomes"), dict) else {}
            cur_out = summary.get("outcomes", {}) if isinstance(summary.get("outcomes"), dict) else {}
            cur_buckets = (
                summary.get("outcome_bucket_breakdown", {})
                if isinstance(summary.get("outcome_bucket_breakdown"), dict)
                else {}
            )
            prev_buckets = (
                prev_summary.get("outcome_bucket_breakdown", {})
                if isinstance(prev_summary.get("outcome_bucket_breakdown"), dict)
                else {}
            )
            summary["delta_vs_prev_day"] = {
                "base_date": prev_date,
                "total_runs": int(summary.get("total_runs", 0) or 0) - int(prev_summary.get("total_runs", 0) or 0),
                "total_candidates": int(summary.get("total_candidates", 0) or 0)
                - int(prev_summary.get("total_candidates", 0) or 0),
                "total_decisions": int(summary.get("total_decisions", 0) or 0)
                - int(prev_summary.get("total_decisions", 0) or 0),
                "total_watchlist": int(summary.get("total_watchlist", 0) or 0)
                - int(prev_summary.get("total_watchlist", 0) or 0),
                "total_fallback_watchlist_outcomes": int(summary.get("total_fallback_watchlist_outcomes", 0) or 0)
                - int(prev_summary.get("total_fallback_watchlist_outcomes", 0) or 0),
                "bucket_picked_total": int(((cur_buckets.get("picked", {}) or {}).get("total", 0) or 0))
                - int(((prev_buckets.get("picked", {}) or {}).get("total", 0) or 0)),
                "bucket_watchlist_total": int(((cur_buckets.get("watchlist", {}) or {}).get("total", 0) or 0))
                - int(((prev_buckets.get("watchlist", {}) or {}).get("total", 0) or 0)),
                "bucket_exception_leader_total": int(
                    ((cur_buckets.get("exception_leader", {}) or {}).get("total", 0) or 0)
                )
                - int(((prev_buckets.get("exception_leader", {}) or {}).get("total", 0) or 0)),
                "outcomes_total": int(cur_out.get("total", 0) or 0) - int(prev_out.get("total", 0) or 0),
                "outcomes_pending": int(cur_out.get("pending", 0) or 0) - int(prev_out.get("pending", 0) or 0),
                "outcomes_resolved": int(cur_out.get("resolved", 0) or 0) - int(prev_out.get("resolved", 0) or 0),
                "outcomes_expired": int(cur_out.get("expired", 0) or 0) - int(prev_out.get("expired", 0) or 0),
                "outcomes_closure_rate_pct": round(
                    float(cur_out.get("closure_rate_pct", 0.0) or 0.0)
                    - float(prev_out.get("closure_rate_pct", 0.0) or 0.0),
                    2,
                ),
            }

    json_path = output_dir / f"daily_summary_{target_date}{market_suffix}.json"
    md_path = output_dir / f"daily_summary_{target_date}{market_suffix}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, sort_keys=True)
    with md_path.open("w", encoding="utf-8") as f:
        f.write(render_daily_summary_markdown(summary))
    return {
        "json_path": str(json_path),
        "md_path": str(md_path),
    }
