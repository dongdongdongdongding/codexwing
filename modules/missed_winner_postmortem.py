from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple


POSTMORTEM_VERSION = "kr_missed_winner_postmortem_v1"
HORIZONS = (1, 3, 5)
THRESHOLDS = (5.0, 10.0)


def _num(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "None"):
            return None
        numeric = float(str(value).replace(",", "").replace("%", "").strip())
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except Exception:
        return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _ticker(row: Dict[str, Any]) -> str:
    return _text(row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커")).upper()


def _market(row: Dict[str, Any]) -> str:
    market = _text(row.get("market") or row.get("market_subtype") or row.get("Market")).upper()
    ticker = _ticker(row)
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return market or "-"


def _return_for(row: Dict[str, Any], horizon: int) -> float | None:
    return _num(row.get(f"return_{horizon}d_pct"))


def _rank(row: Dict[str, Any]) -> float | None:
    return _num(row.get("priority_rank") or row.get("rank") or row.get("Rank"))


def _is_top5(row: Dict[str, Any]) -> bool:
    rank = _rank(row)
    return rank is not None and 1 <= rank <= 5


def _is_exception(row: Dict[str, Any]) -> bool:
    marker = " ".join(
        _text(row.get(key)).upper()
        for key in ("decision", "decision_bucket", "selection_lane", "strategy", "rationale")
    )
    return "EXCEPTION" in marker


def _missing_theme(row: Dict[str, Any]) -> bool:
    theme = _text(row.get("primary_theme") or row.get("테마") or row.get("Theme"))
    status = _text(row.get("theme_inference_status")).lower()
    return not theme or status in {"failed", "missing", "unknown"}


def _data_missing(row: Dict[str, Any]) -> bool:
    completeness = _num(row.get("feature_completeness"))
    if completeness is not None and completeness < 0.75:
        return True
    quality = _text(row.get("feature_quality") or row.get("data_quality_level")).lower()
    return quality in {"low", "missing", "stale", "critical"}


def _liquidity_weak(row: Dict[str, Any]) -> bool:
    volume_ratio = _num(row.get("volume_ratio"))
    amount = _num(row.get("turnover") or row.get("trading_value"))
    if volume_ratio is not None and volume_ratio < 0.8:
        return True
    if amount is not None and amount < 10_000_000_000:
        return True
    reasons = " ".join(str(item).upper() for item in row.get("reject_reasons", []) if item)
    return "LIQUIDITY" in reasons


def _score_miss(row: Dict[str, Any]) -> bool:
    if _is_top5(row):
        return False
    score = _num(row.get("decision_score") or row.get("Decision Score") or row.get("score"))
    relative = _num(row.get("relative_rank_score"))
    return score is None or score < 80 or (relative is not None and relative < 65)


def _no_prior_signal(row: Dict[str, Any]) -> bool:
    signal_fields = (
        row.get("decision_score"),
        row.get("prob_clean"),
        row.get("phase25_prob"),
        row.get("expected_edge_score"),
        row.get("volume_ratio"),
    )
    return all(_num(value) is None for value in signal_fields)


def classify_missed_winner(row: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if not bool(row.get("emitted", True)):
        reasons.append("filter_miss")
    if _score_miss(row):
        reasons.append("score_miss")
    if _data_missing(row):
        reasons.append("data_miss")
    if _missing_theme(row):
        reasons.append("theme_miss")
    if _liquidity_weak(row):
        reasons.append("liquidity_miss")
    if _no_prior_signal(row):
        reasons.append("no_prior_signal")
    return reasons or ["uncategorized"]


def build_reject_rows_from_diagnostics(diagnostic_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in diagnostic_rows or []:
        if not isinstance(item, dict):
            continue
        run_id = _text(item.get("run_id"))
        market = _text(item.get("market")).upper()
        base_trade_date = _text(item.get("base_trade_date") or item.get("as_of_date") or item.get("created_at"))[:10]
        details = item.get("reject_details_by_symbol") if isinstance(item.get("reject_details_by_symbol"), dict) else {}
        reasons_by_symbol = item.get("reject_reasons_by_symbol") if isinstance(item.get("reject_reasons_by_symbol"), dict) else {}
        for ticker, detail_list in details.items():
            detail = (detail_list or [{}])[-1] if isinstance(detail_list, list) else detail_list
            detail = detail if isinstance(detail, dict) else {}
            rows.append(
                {
                    **detail,
                    "run_id": run_id,
                    "ticker": _text(ticker).upper(),
                    "market": market or detail.get("liquidity_market"),
                    "base_trade_date": base_trade_date,
                    "emitted": False,
                    "reject_stage": detail.get("stage"),
                    "reject_reasons": reasons_by_symbol.get(ticker) or [],
                    "outcome_available": False,
                }
            )
    return rows


def attach_reject_outcomes(reject_rows: List[Dict[str, Any]], outcome_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    outcome_index = {
        (_text(row.get("run_id")), _ticker(row)): row
        for row in outcome_rows or []
        if isinstance(row, dict) and _ticker(row)
    }
    merged: List[Dict[str, Any]] = []
    for row in reject_rows:
        key = (_text(row.get("run_id")), _ticker(row))
        outcome = outcome_index.get(key) or {}
        available = False
        if outcome:
            available = _truthy(outcome.get("outcome_available")) or any(
                _num(outcome.get(f"return_{horizon}d_pct")) is not None for horizon in HORIZONS
            )
        merged.append({**row, **outcome, "emitted": False, "outcome_available": available})
    return merged


def _cohort_key(row: Dict[str, Any], horizon: int, threshold: float) -> Tuple[str, int, float]:
    return (_market(row), int(horizon), float(threshold))


def build_missed_winner_postmortem(
    emitted_rows: Iterable[Dict[str, Any]],
    *,
    reject_rows: Iterable[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    source_rows: List[Dict[str, Any]] = []
    for row in emitted_rows or []:
        if isinstance(row, dict):
            source_rows.append({**row, "emitted": True, "outcome_available": True})
    source_rows.extend([row for row in reject_rows or [] if isinstance(row, dict)])

    metrics: Dict[str, Dict[str, Any]] = {}
    reason_counts: Dict[Tuple[str, int, float], Counter] = defaultdict(Counter)
    examples: Dict[Tuple[str, int, float], List[Dict[str, Any]]] = defaultdict(list)

    for market in ("KOSPI", "KOSDAQ"):
        for horizon in HORIZONS:
            for threshold in THRESHOLDS:
                winners = [
                    row
                    for row in source_rows
                    if _market(row) == market and (_return_for(row, horizon) is not None and _return_for(row, horizon) >= threshold)
                ]
                top5 = [row for row in winners if bool(row.get("emitted", True)) and _is_top5(row)]
                emitted = [row for row in winners if bool(row.get("emitted", True))]
                exception = [row for row in winners if bool(row.get("emitted", True)) and _is_exception(row)]
                missed = [row for row in winners if row not in top5]
                key = (market, horizon, threshold)
                for row in missed:
                    for reason in classify_missed_winner(row):
                        reason_counts[key][reason] += 1
                    if len(examples[key]) < 8:
                        examples[key].append(
                            {
                                "ticker": _ticker(row),
                                "stock_name": row.get("stock_name") or row.get("name"),
                                "return_pct": _return_for(row, horizon),
                                "priority_rank": _rank(row),
                                "emitted": bool(row.get("emitted", True)),
                                "reasons": classify_missed_winner(row),
                            }
                        )
                total = len(winners)
                metrics[f"{market}_{horizon}d_plus{int(threshold)}"] = {
                    "market": market,
                    "horizon_days": horizon,
                    "threshold_pct": threshold,
                    "winner_count": total,
                    "top5_capture_count": len(top5),
                    "top5_capture_rate_pct": round(len(top5) / total * 100.0, 4) if total else None,
                    "missed_rate_pct": round((total - len(top5)) / total * 100.0, 4) if total else None,
                    "emitted_capture_count": len(emitted),
                    "emitted_capture_rate_pct": round(len(emitted) / total * 100.0, 4) if total else None,
                    "exception_capture_count": len(exception),
                    "miss_reason_counts": dict(reason_counts[key]),
                    "missed_examples": examples[key],
                }

    reject_list = [row for row in source_rows if not bool(row.get("emitted", True))]
    reject_outcome_gap = sum(1 for row in reject_list if not row.get("outcome_available"))
    proposed = _proposed_changes(reason_counts, reject_rows=reject_list)
    return {
        "version": POSTMORTEM_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": len(source_rows),
        "emitted_rows": sum(1 for row in source_rows if row.get("emitted")),
        "reject_rows": len(reject_list),
        "reject_rows_without_outcomes": reject_outcome_gap,
        "metrics": metrics,
        "proposed_rule_changes": proposed,
        "data_limitations": _data_limitations(reject_list),
    }


def _proposed_changes(reason_counts: Dict[Tuple[str, int, float], Counter], *, reject_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    total = Counter()
    for counter in reason_counts.values():
        total.update(counter)
    changes = []
    mapping = {
        "filter_miss": "Persist rejected-symbol forward outcomes and add a reject-recovery candidate lane before changing production ranking.",
        "score_miss": "Backtest a winner-retention reranker for high-return-but-low-rank rows; compare against Top5 before promotion.",
        "theme_miss": "Require dynamic theme fill before planner ranking; missing theme should be an explicit low-confidence trace, not silent neutral.",
        "liquidity_miss": "Split liquidity misses by turnover percentile; do not relax hard liquidity until reject winners have outcome proof.",
        "data_miss": "Block promotion of any model slice where critical feature completeness is below 75%.",
        "no_prior_signal": "Add pre-scan data capture for prior volume/price/news signals because current features had no observable early marker.",
    }
    for reason, count in total.most_common():
        changes.append({"reason": reason, "count": int(count), "proposal": mapping.get(reason, "Review repeated miss pattern before production change.")})
    missing_reject_outcomes = sum(1 for row in reject_rows if not row.get("outcome_available"))
    if missing_reject_outcomes:
        changes.insert(
            0,
            {
                "reason": "reject_outcome_gap",
                "count": missing_reject_outcomes,
                "proposal": "Current artifacts store reject reasons but not forward returns; full-universe missed-winner proof requires rejected-symbol outcome backfill.",
            },
        )
    return changes[:10]


def _data_limitations(reject_rows: List[Dict[str, Any]]) -> List[str]:
    if not reject_rows:
        return ["No reject diagnostics were supplied; report only measures emitted candidate misses."]
    if all(not row.get("outcome_available") for row in reject_rows):
        return ["Reject diagnostics exist, but rejected symbols have no forward return outcomes in current local artifacts."]
    return []


__all__ = [
    "HORIZONS",
    "POSTMORTEM_VERSION",
    "THRESHOLDS",
    "attach_reject_outcomes",
    "build_missed_winner_postmortem",
    "build_reject_rows_from_diagnostics",
    "classify_missed_winner",
]
