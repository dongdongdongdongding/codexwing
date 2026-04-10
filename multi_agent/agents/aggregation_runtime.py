from __future__ import annotations

from collections import Counter
from statistics import mean, median, pstdev
from typing import Any, Dict, List, Tuple

from multi_agent.contracts.types import AggregationHandoff, RunContext, WarningItem


def extract_reason_value(reasons: List[str], keys: List[str]) -> str:
    for item in reasons:
        text = str(item)
        for key in keys:
            prefix = f"{key}:"
            if text.startswith(prefix):
                return text.split(":", 1)[1].strip() or "UNKNOWN"
    return "UNKNOWN"


def score_stats(scores: List[float]) -> Dict[str, float]:
    if not scores:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": round(float(mean(scores)), 3),
        "median": round(float(median(scores)), 3),
        "std": round(float(pstdev(scores)) if len(scores) > 1 else 0.0, 3),
        "min": round(float(min(scores)), 3),
        "max": round(float(max(scores)), 3),
    }


def build_aggregation_handoff(
    context: RunContext,
    candidates: List[Dict[str, Any]],
) -> Tuple[AggregationHandoff, Dict[str, float]]:
    total = len(candidates)
    scores = [float(c.get("score", 0.0) or 0.0) for c in candidates]
    weak_count = sum(1 for s in scores if s < 55.0)
    weak_ratio = (weak_count / total) if total else 1.0

    strategy_counter: Counter[str] = Counter()
    trend_counter: Counter[str] = Counter()
    theme_counter: Counter[str] = Counter()
    theme_rows: Dict[str, List[Dict[str, Any]]] = {}
    for cand in candidates:
        reasons = cand.get("reasons", []) if isinstance(cand.get("reasons"), list) else []
        snap = cand.get("feature_snapshot", {}) if isinstance(cand.get("feature_snapshot"), dict) else {}
        theme_context = cand.get("theme_context", {}) if isinstance(cand.get("theme_context"), dict) else {}
        leader_metrics = cand.get("leader_metrics", {}) if isinstance(cand.get("leader_metrics"), dict) else {}
        if not theme_context and isinstance(snap.get("theme_context"), dict):
            theme_context = snap.get("theme_context", {})
        if not leader_metrics and isinstance(snap.get("leader_metrics"), dict):
            leader_metrics = snap.get("leader_metrics", {})
        strategy = extract_reason_value(reasons, ["Strategy", "전략"])
        trend = str(snap.get("trend") or extract_reason_value(reasons, ["Trend", "추세"]) or "UNKNOWN")
        strategy_counter[strategy] += 1
        trend_counter[trend] += 1
        primary_theme = str(theme_context.get("primary_theme") or "").strip()
        if primary_theme and primary_theme.lower() != "unclassified":
            theme_counter[primary_theme] += 1
            theme_rows.setdefault(primary_theme, []).append(
                {
                    "ticker": str(cand.get("ticker") or "UNKNOWN"),
                    "score": float(cand.get("score", 0.0) or 0.0),
                    "leader_score": float(leader_metrics.get("leader_score", 0.0) or 0.0),
                    "theme_strength_score": float(theme_context.get("theme_strength_score", 0.0) or 0.0),
                    "theme_direction": str(theme_context.get("theme_direction") or "NEUTRAL"),
                }
            )

    top_strategy = "UNKNOWN"
    top_strategy_count = 0
    if strategy_counter:
        top_strategy, top_strategy_count = strategy_counter.most_common(1)[0]

    concentration = {
        "candidate_count": total,
        "weak_candidate_count": weak_count,
        "weak_candidate_ratio": round(weak_ratio, 3),
        "top_strategy": top_strategy,
        "top_strategy_share": round((top_strategy_count / total) if total else 0.0, 3),
        "strategy_distribution": dict(strategy_counter),
        "trend_distribution": dict(trend_counter),
        "theme_distribution": dict(theme_counter),
    }

    clusters = []
    for tag, count in strategy_counter.most_common(3):
        clusters.append(
            {
                "cluster_type": "strategy_tag",
                "label": tag,
                "count": count,
                "share": round(count / total, 3) if total else 0.0,
            }
        )

    leaderboard = []
    for theme_name, count in theme_counter.most_common(5):
        rows = sorted(theme_rows.get(theme_name, []), key=lambda row: (row["leader_score"], row["score"]), reverse=True)
        leader_ticker = rows[0]["ticker"] if rows else "UNKNOWN"
        theme_strength_score = max((row["theme_strength_score"] for row in rows), default=0.0)
        breadth_score = min(100.0, count * 12.0)
        concentration_score = max((row["leader_score"] for row in rows), default=0.0)
        clusters.append(
            {
                "cluster_type": "theme",
                "theme_name": theme_name,
                "member_count": count,
                "leader_ticker": leader_ticker,
                "theme_strength_score": round(theme_strength_score, 1),
                "concentration_score": round(concentration_score, 1),
                "breadth_score": round(breadth_score, 1),
                "notes": [f"top_direction={rows[0]['theme_direction']}" if rows else "no_rows"],
            }
        )
        leaderboard.append(
            {
                "theme_name": theme_name,
                "leader_ticker": leader_ticker,
                "theme_strength_score": round(theme_strength_score, 1),
                "member_count": count,
                "top_members": rows[:3],
            }
        )

    notes = [
        f"Total candidates: {total}",
        f"Weak-score candidates (<55): {weak_count} ({weak_ratio:.1%})",
        f"Top strategy cluster: {top_strategy} ({top_strategy_count}/{total if total else 1})",
    ]
    if theme_counter:
        top_theme, top_theme_count = theme_counter.most_common(1)[0]
        notes.append(f"Top theme cluster: {top_theme} ({top_theme_count}/{total if total else 1})")

    warnings: List[WarningItem] = []
    if total == 0:
        warnings.append(
            WarningItem(
                code="NO_CANDIDATES",
                message="Scanner produced zero candidates. Investigate filter coupling or data fetch failures.",
                severity="error",
            )
        )
    if weak_ratio >= 0.5 and total > 0:
        warnings.append(
            WarningItem(
                code="HIGH_WEAK_RATIO",
                message=f"Weak candidate ratio is high ({weak_ratio:.1%}).",
                severity="warning",
            )
        )
    if total > 0 and (top_strategy_count / total) >= 0.7:
        warnings.append(
            WarningItem(
                code="STRATEGY_CONCENTRATION",
                message=f"Candidates are concentrated in one strategy tag ({top_strategy}).",
                severity="warning",
            )
        )

    handoff = AggregationHandoff(
        run_context=context,
        concentration=concentration,
        clusters=clusters,
        leaderboard=leaderboard,
        quality_notes=notes,
        warnings=warnings,
    )
    return handoff, {"weak_ratio": weak_ratio, "candidate_count": float(total), "score_mean": score_stats(scores)["mean"]}
