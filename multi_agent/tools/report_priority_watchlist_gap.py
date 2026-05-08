#!/usr/bin/env python3
"""Diagnose recent PRIORITY_WATCHLIST disappearance from real scan archive rows."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager  # noqa: E402


OUT_JSON = PROJECT_ROOT / "runtime_state/reports/data_health/priority_watchlist_gap.json"
OUT_MD = PROJECT_ROOT / "runtime_state/reports/data_health/priority_watchlist_gap.md"


def _day(value: Any) -> str:
    text = str(value or "")
    return text[:10] if len(text) >= 10 else "unknown"


def _listify(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except Exception:
            pass
        return [value] if value else []
    return []


def _fetch_rows(days: int) -> List[Dict[str, Any]]:
    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=int(days))
    select_cols = (
        "id,created_at,market_type,scan_mode,strategy_family,decision,decision_bucket,"
        "priority_rank,decision_score,alpha_score,ml_prob,prob_clean,phase25_prob,"
        "phase25_variant,phase25_signal_direction,phase25_oos_auc,phase25_oos_win_rate_pct,"
        "phase25_oos_avg_return_pct,phase25_recommended_threshold,"
        "expected_return_1d_pct,expected_return_3d_pct,"
        "quality_flags,"
        "validation_excluded,"
        "return_3d_pct,return_5d_pct"
    )
    rows: List[Dict[str, Any]] = []
    page = 0
    page_size = 1000
    while True:
        res = (
            db.client.table("market_scan_results")
            .select(select_cols)
            .gte("created_at", start.isoformat())
            .lt("created_at", end.isoformat())
            .order("created_at", desc=False)
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
        if page > 50:
            break
    return rows


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _resolved_return_for_row(row: Dict[str, Any]) -> tuple[float | None, str]:
    variant = str(row.get("phase25_variant") or "").lower()
    market = str(row.get("market_type") or "").upper()
    mode = str(row.get("scan_mode") or "").upper()
    if "kosdaq_swing" in variant or (market == "KOSDAQ" and mode == "SWING"):
        candidates = ("return_5d_pct", "return_3d_pct")
    else:
        candidates = ("return_3d_pct", "return_5d_pct")
    for col in candidates:
        value = _safe_float(row.get(col))
        if value is not None:
            return value, col
    return None, candidates[0]


def _performance_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    returns: List[float] = []
    return_cols = Counter()
    for row in rows:
        value, col = _resolved_return_for_row(row)
        if value is None:
            continue
        returns.append(value)
        return_cols[col] += 1
    if not returns:
        return {
            "rows": len(rows),
            "resolved_rows": 0,
            "win_rate": None,
            "avg_return": None,
            "median_return": None,
            "hit_rate_5pct": None,
            "hit_rate_10pct": None,
            "return_columns": {},
        }
    sorted_returns = sorted(returns)
    resolved = len(returns)
    return {
        "rows": len(rows),
        "resolved_rows": resolved,
        "win_rate": round(100.0 * sum(v > 0 for v in returns) / resolved, 4),
        "avg_return": round(sum(returns) / resolved, 4),
        "median_return": round(sorted_returns[resolved // 2], 4),
        "hit_rate_5pct": round(100.0 * sum(v >= 5.0 for v in returns) / resolved, 4),
        "hit_rate_10pct": round(100.0 * sum(v >= 10.0 for v in returns) / resolved, 4),
        "return_columns": dict(return_cols),
    }


def build_report(days: int) -> Dict[str, Any]:
    rows = _fetch_rows(days)
    by_day: Dict[str, Counter] = defaultdict(Counter)
    by_day_market: Dict[str, Counter] = defaultdict(Counter)
    risks = Counter()
    rationales = Counter()
    priority_candidates = []
    demoted_by_segment: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        day = _day(row.get("created_at"))
        decision = str(row.get("decision") or "UNKNOWN")
        market = str(row.get("market_type") or "UNKNOWN")
        mode = str(row.get("scan_mode") or "UNKNOWN")
        by_day[day][decision] += 1
        by_day_market[f"{day}|{market}|{mode}"][decision] += 1
        for item in _listify(row.get("theme_risk")) + _listify(row.get("quality_flags")):
            risks[item] += 1
        for item in _listify(row.get("rationale")):
            if any(token in item for token in ("guard", "probation", "phase25", "priority_cap", "expected_edge")):
                rationales[item] += 1
        try:
            score = float(row.get("decision_score") or 0)
        except Exception:
            score = 0.0
        if score >= 80 and decision != "PRIORITY_WATCHLIST":
            priority_candidates.append(row)
            demoted_by_segment[f"{market}|{mode}|{decision}"].append(row)

    priority_by_day = {
        day: int(counter.get("PRIORITY_WATCHLIST", 0))
        for day, counter in sorted(by_day.items())
    }
    zero_days = [day for day, count in priority_by_day.items() if count == 0]
    last_priority_day = None
    for day, count in priority_by_day.items():
        if count > 0:
            last_priority_day = day
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": int(days),
        "rows": int(len(rows)),
        "daily_decisions": {day: dict(counter) for day, counter in sorted(by_day.items())},
        "daily_market_decisions": {key: dict(counter) for key, counter in sorted(by_day_market.items())},
        "priority_by_day": priority_by_day,
        "zero_priority_days": zero_days,
        "last_priority_day": last_priority_day,
        "top_risks": risks.most_common(30),
        "top_gate_rationales": rationales.most_common(50),
        "score_ge_80_demoted_count": len(priority_candidates),
        "score_ge_80_demoted_performance": {
            "overall": _performance_summary(priority_candidates),
            "by_segment": {
                key: _performance_summary(value)
                for key, value in sorted(demoted_by_segment.items())
            },
        },
        "score_ge_80_demoted_sample": priority_candidates[:50],
    }


def write_report(report: Dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    lines = [
        "# Priority Watchlist Gap",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- window_days: `{report['window_days']}`",
        f"- rows: `{report['rows']}`",
        f"- last_priority_day: `{report.get('last_priority_day')}`",
        f"- score_ge_80_demoted_count: `{report['score_ge_80_demoted_count']}`",
        "",
        "## Daily Decisions",
    ]
    for day, counter in report["daily_decisions"].items():
        lines.append(f"- `{day}`: {counter}")
    lines.extend(["", "## Top Risks"])
    for key, count in report["top_risks"][:20]:
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Top Gate Rationales"])
    for key, count in report["top_gate_rationales"][:30]:
        lines.append(f"- `{key}`: {count}")
    perf = report.get("score_ge_80_demoted_performance", {}).get("overall", {})
    lines.extend(
        [
            "",
            "## Score >= 80 Demoted Performance",
            f"- resolved_rows: `{perf.get('resolved_rows')}` / rows `{perf.get('rows')}`",
            f"- win_rate: `{perf.get('win_rate')}`",
            f"- avg_return: `{perf.get('avg_return')}`",
            f"- median_return: `{perf.get('median_return')}`",
            f"- hit_rate_5pct: `{perf.get('hit_rate_5pct')}`",
            f"- hit_rate_10pct: `{perf.get('hit_rate_10pct')}`",
            f"- return_columns: `{perf.get('return_columns')}`",
            "",
            "### By Segment",
        ]
    )
    for key, value in report.get("score_ge_80_demoted_performance", {}).get("by_segment", {}).items():
        if int(value.get("resolved_rows") or 0) == 0:
            continue
        lines.append(
            f"- `{key}`: n={value.get('resolved_rows')} win={value.get('win_rate')} "
            f"avg={value.get('avg_return')} median={value.get('median_return')} "
            f"hit5={value.get('hit_rate_5pct')} hit10={value.get('hit_rate_10pct')}"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=45)
    args = parser.parse_args()
    report = build_report(args.days)
    write_report(report)
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"last_priority_day={report.get('last_priority_day')}")
    print(f"score_ge_80_demoted_count={report['score_ge_80_demoted_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
