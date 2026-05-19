from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


REPORT_VERSION = "good_stock_falling_postmortem_v1"


def _num(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "None"):
            return None
        result = float(str(value).replace("%", "").replace(",", "").strip())
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _is_high_score(row: Dict[str, Any]) -> bool:
    return any(
        (value is not None and value >= threshold)
        for value, threshold in (
            (_num(row.get("decision_score")), 70.0),
            (_num(row.get("alpha_score")), 75.0),
            (_num(row.get("relative_rank_score")), 70.0),
            (_num(row.get("buy_score")), 70.0),
        )
    )


def _is_loser(row: Dict[str, Any]) -> bool:
    returns = [_num(row.get(key)) for key in ("return_1d_pct", "return_3d_pct", "return_5d_pct")]
    mae = _num(row.get("mae_5d_pct"))
    return any(value is not None and value < 0 for value in returns) or (mae is not None and mae <= -5.0)


def classify_loser_causes(row: Dict[str, Any]) -> List[str]:
    row = row if isinstance(row, dict) else {}
    causes: List[str] = []
    day_change = _num(row.get("day_change_pct") or row.get("day_return_pct"))
    if (day_change is not None and day_change >= 8.0) or "PEAK" in _text(row.get("position")).upper():
        causes.append("price_pre_reflection")

    foreigner = _num(row.get("foreigner") or row.get("foreign_flow") or row.get("foreigner_1d"))
    institution = _num(row.get("institution") or row.get("institution_flow") or row.get("institution_1d"))
    if (foreigner is not None and foreigner < 0) and (institution is not None and institution < 0):
        causes.append("flow_deterioration")

    volume_ratio = _num(row.get("volume_ratio") or row.get("volume_ratio_20d"))
    if volume_ratio is not None and volume_ratio < 0.8:
        causes.append("volume_exhaustion")

    market_gate = _text(row.get("market_gate")).upper()
    regime_avg = _num(row.get("regime_avg_chg"))
    if market_gate in {"RED", "YELLOW"} or (regime_avg is not None and regime_avg <= -1.0):
        causes.append("market_regime_drag")

    theme_day = _num(row.get("theme_day_avg_day_return_pct"))
    theme_adj = _num(row.get("theme_score_adjustment"))
    if (theme_day is not None and theme_day < 0) or (theme_adj is not None and theme_adj < 0):
        causes.append("theme_reversal")

    stop_first = row.get("stop_before_target_5d")
    mae = _num(row.get("mae_5d_pct"))
    stop_sl = _num(row.get("stop_sl_pct"))
    if stop_first is True or (mae is not None and stop_sl is not None and mae <= stop_sl):
        causes.append("stop_path_failure")

    return causes or ["unclassified"]


def _metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    values = [_num(row.get("return_5d_pct")) for row in rows]
    clean = [value for value in values if value is not None]
    if not clean:
        return {"rows": len(rows), "return_5d_n": 0, "return_5d_win_pct": None, "return_5d_avg_pct": None}
    return {
        "rows": len(rows),
        "return_5d_n": len(clean),
        "return_5d_win_pct": round(sum(1 for value in clean if value > 0) / len(clean) * 100.0, 4),
        "return_5d_avg_pct": round(sum(clean) / len(clean), 6),
    }


def build_good_stock_falling_postmortem(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    high_score = [row for row in row_list if _is_high_score(row)]
    losers = [row for row in high_score if _is_loser(row)]
    winners = [row for row in high_score if not _is_loser(row)]
    cause_counts: Counter[str] = Counter()
    examples: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in losers:
        causes = classify_loser_causes(row)
        for cause in causes:
            cause_counts[cause] += 1
            if len(examples[cause]) < 5:
                examples[cause].append(
                    {
                        "ticker": row.get("ticker"),
                        "stock_name": row.get("stock_name"),
                        "market": row.get("market"),
                        "section": row.get("section"),
                        "return_1d_pct": _num(row.get("return_1d_pct")),
                        "return_3d_pct": _num(row.get("return_3d_pct")),
                        "return_5d_pct": _num(row.get("return_5d_pct")),
                        "mae_5d_pct": _num(row.get("mae_5d_pct")),
                    }
                )

    proposed = []
    for cause, count in cause_counts.most_common():
        share = count / len(losers) * 100.0 if losers else 0.0
        if share < 10.0:
            continue
        proposed.append(
            {
                "cause": cause,
                "loser_share_pct": round(share, 4),
                "rule_delta": f"downweight_or_warn:{cause}",
                "target_layer": "realized_expectancy_admission",
                "production_change": False,
            }
        )

    by_cause = {}
    for cause in cause_counts:
        affected = [row for row in high_score if cause in classify_loser_causes(row)]
        remaining = [row for row in high_score if cause not in classify_loser_causes(row)]
        by_cause[cause] = {
            "affected": _metrics(affected),
            "remaining_after_exclusion": _metrics(remaining),
        }

    return {
        "version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(row_list),
        "high_score_rows": len(high_score),
        "high_score_losers": len(losers),
        "high_score_winners": len(winners),
        "cause_counts": dict(cause_counts),
        "cause_examples": dict(examples),
        "metrics": {
            "high_score_all": _metrics(high_score),
            "high_score_losers": _metrics(losers),
            "high_score_winners": _metrics(winners),
            "by_cause": by_cause,
        },
        "proposed_rule_deltas": proposed,
    }
