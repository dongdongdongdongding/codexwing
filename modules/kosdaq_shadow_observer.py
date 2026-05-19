from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List

from modules.ui_helpers import is_kosdaq_ordered_rebound_shadow_gate_row

REPORT_VERSION = "kosdaq_ordered_rebound_shadow_observer_v1"
DEFAULT_SOURCE_CSV = Path("runtime_state/reports/experimental/kosdaq_ordered_candidate_search_latest.rows.csv")
DEFAULT_OUTPUT_DIR = Path("runtime_state/reports/validation")
DEFAULT_JSON_PATH = DEFAULT_OUTPUT_DIR / "kosdaq_shadow_observer.json"
DEFAULT_MD_PATH = DEFAULT_OUTPUT_DIR / "kosdaq_shadow_observer.md"
GATE_PROFILE = "5D_ordered_5v5"
GATE_DESCRIPTION = "KOSDAQ 5D_ordered_5v5 · volume_ratio<=1.23 · trend=DOWN · selection_lane=1d"


@dataclass(frozen=True)
class PromotionGuardrails:
    min_ready_n: int = 50
    min_win_rate_pct: float = 70.0
    max_stop_first_pct: float = 20.0
    min_trade_dates: int = 10
    min_theme_count: int = 3


def load_observer_rows(path: Path = DEFAULT_SOURCE_CSV) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def is_kosdaq_ordered_rebound_observer_row(row: Dict[str, Any]) -> bool:
    """Issue-tracked KOSDAQ ordered rebound observer gate.

    This is intentionally separate from the current display shadow gate. The
    issue requires daily observation of the ordered testbed candidate without
    changing production ranking or the scanner's admission logic.
    """
    if _market(row) != "KOSDAQ":
        return False
    if _text(row.get("candidate_id")) != GATE_PROFILE:
        return False
    volume_ratio = _to_float(row.get("volume_ratio"))
    if volume_ratio is None or volume_ratio > 1.23:
        return False
    if _text(row.get("trend")).upper() != "DOWN":
        return False
    return _text(row.get("selection_lane")).lower() == "1d"


def build_kosdaq_shadow_observer_report(
    rows: Iterable[Dict[str, Any]],
    *,
    as_of_date: str | None = None,
    generated_at: str | None = None,
    guardrails: PromotionGuardrails | None = None,
) -> Dict[str, Any]:
    guard = guardrails or PromotionGuardrails()
    source_rows = list(rows or [])
    observer_rows = [row for row in source_rows if is_kosdaq_ordered_rebound_observer_row(row)]
    ready_rows = [row for row in observer_rows if _truthy(row.get("ordered_label_ready"))]
    display_shadow_rows = [row for row in source_rows if _market(row) == "KOSDAQ" and is_kosdaq_ordered_rebound_shadow_gate_row(row)]
    display_overlap = [
        row for row in observer_rows if is_kosdaq_ordered_rebound_shadow_gate_row(row)
    ]

    ordered_summary = _ordered_summary(ready_rows)
    horizon_metrics = {f"{horizon}d": _return_summary(ready_rows, f"return_{horizon}d_pct") for horizon in (1, 3, 5)}
    trade_dates = sorted({_trade_date(row) for row in observer_rows if _trade_date(row)})
    themes = sorted({_text(row.get("primary_theme") or row.get("primary_theme_archive")) for row in observer_rows if _text(row.get("primary_theme") or row.get("primary_theme_archive"))})
    recent_daily = _daily_summaries(ready_rows)[-10:]
    recent_samples = _recent_samples(observer_rows, limit=15)

    guardrail_results = _promotion_guardrail_results(
        ordered_summary=ordered_summary,
        horizon_metrics=horizon_metrics,
        distinct_trade_dates=len(trade_dates),
        distinct_themes=len(themes),
        guard=guard,
    )
    production_ready = all(item["passed"] for item in guardrail_results)
    promotion_status = "candidate_for_human_review" if production_ready else "shadow_observe"

    return {
        "report_version": REPORT_VERSION,
        "as_of_date": as_of_date or str(date.today()),
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "gate": {
            "profile": GATE_PROFILE,
            "description": GATE_DESCRIPTION,
            "production_enabled": False,
        },
        "source": {
            "source_rows": len(source_rows),
            "observer_rows": len(observer_rows),
            "ready_rows": len(ready_rows),
            "latest_trade_date": trade_dates[-1] if trade_dates else "",
            "distinct_trade_dates": len(trade_dates),
            "distinct_themes": len(themes),
        },
        "ordered_summary": ordered_summary,
        "horizon_metrics": horizon_metrics,
        "promotion": {
            "status": promotion_status,
            "production_ready": production_ready,
            "guardrails": [guard.__dict__],
            "checks": guardrail_results,
            "note": "관찰 리포트 전용이다. 통과해도 스캔 랭킹 자동 교체는 하지 않는다.",
        },
        "display_gate_alignment": {
            "current_display_shadow_rows": len(display_shadow_rows),
            "observer_rows_also_in_display_shadow": len(display_overlap),
            "observer_display_overlap_pct": _pct(len(display_overlap), len(observer_rows)),
            "warning": (
                "현재 UI KOSDAQ Shadow 조건과 이슈 관찰 조건이 다르다."
                if observer_rows and len(display_overlap) < len(observer_rows)
                else ""
            ),
        },
        "daily": recent_daily,
        "recent_samples": recent_samples,
    }


def write_kosdaq_shadow_observer_report(
    report: Dict[str, Any],
    *,
    json_path: Path = DEFAULT_JSON_PATH,
    md_path: Path = DEFAULT_MD_PATH,
) -> Dict[str, str]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_kosdaq_shadow_observer_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


def build_kosdaq_shadow_observer_markdown(report: Dict[str, Any]) -> str:
    source = report.get("source") or {}
    ordered = report.get("ordered_summary") or {}
    horizons = report.get("horizon_metrics") or {}
    promotion = report.get("promotion") or {}
    alignment = report.get("display_gate_alignment") or {}

    lines = [
        "# KOSDAQ Ordered Rebound Shadow Observer",
        "",
        f"- Gate: {report.get('gate', {}).get('description', GATE_DESCRIPTION)}",
        f"- Status: {promotion.get('status', '-')}",
        f"- Rows: observer {source.get('observer_rows', 0)} / ready {source.get('ready_rows', 0)} / source {source.get('source_rows', 0)}",
        f"- Coverage: dates {source.get('distinct_trade_dates', 0)} / themes {source.get('distinct_themes', 0)} / latest {source.get('latest_trade_date', '') or '-'}",
        (
            "- Ordered: "
            f"win {ordered.get('win_rate_pct', '-')}% "
            f"({ordered.get('win_n', 0)}/{ordered.get('ready_n', 0)}) / "
            f"stop-first {ordered.get('stop_first_pct', '-')}% "
            f"({ordered.get('stop_n', 0)}/{ordered.get('ready_n', 0)}) / "
            f"MFE {ordered.get('avg_mfe_pct', '-')}% / MAE {ordered.get('avg_mae_pct', '-')}%"
        ),
        "- Returns: "
        + " | ".join(
            f"{key} win {value.get('win_rate_pct', '-')}% avg {_fmt_signed(value.get('avg_return_pct'))} worst {_fmt_signed(value.get('worst_return_pct'))} n={value.get('sample_n', 0)}"
            for key, value in sorted(horizons.items())
        ),
        (
            "- Display alignment: "
            f"current UI shadow rows {alignment.get('current_display_shadow_rows', 0)}, "
            f"observer overlap {alignment.get('observer_rows_also_in_display_shadow', 0)} "
            f"({alignment.get('observer_display_overlap_pct', '-')}%)"
        ),
        "",
        "## Promotion Checks",
    ]
    for check in promotion.get("checks") or []:
        mark = "PASS" if check.get("passed") else "FAIL"
        lines.append(f"- {mark}: {check.get('name')} = {check.get('actual')} / required {check.get('required')}")
    warning = alignment.get("warning")
    if warning:
        lines.extend(["", f"## Warning", f"- {warning}"])
    lines.extend(["", "## Recent Daily"])
    for row in report.get("daily") or []:
        lines.append(
            f"- {row.get('trade_date')}: n={row.get('ready_n')} "
            f"win={row.get('win_rate_pct')}% stop={row.get('stop_first_pct')}% "
            f"avg5={_fmt_signed(row.get('avg_return_5d_pct'))}"
        )
    return "\n".join(lines).strip() + "\n"


def _ordered_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    ready_n = len(rows)
    win_n = sum(1 for row in rows if _truthy(row.get("ordered_win")) or _truthy(row.get("ordered_target_before_stop")))
    stop_n = sum(1 for row in rows if _truthy(row.get("ordered_stop")) or _truthy(row.get("ordered_stop_before_target")))
    mfe_values = [_to_float(row.get("ordered_mfe_pct")) for row in rows]
    mae_values = [_to_float(row.get("ordered_mae_pct")) for row in rows]
    mfe_values = [value for value in mfe_values if value is not None]
    mae_values = [value for value in mae_values if value is not None]
    return {
        "ready_n": ready_n,
        "win_n": win_n,
        "stop_n": stop_n,
        "win_rate_pct": _pct(win_n, ready_n),
        "stop_first_pct": _pct(stop_n, ready_n),
        "avg_mfe_pct": _round(sum(mfe_values) / len(mfe_values)) if mfe_values else None,
        "avg_mae_pct": _round(sum(mae_values) / len(mae_values)) if mae_values else None,
        "median_mfe_pct": _round(float(median(mfe_values))) if mfe_values else None,
        "median_mae_pct": _round(float(median(mae_values))) if mae_values else None,
    }


def _return_summary(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    values = [_to_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    sample_n = len(values)
    win_n = sum(1 for value in values if value > 0)
    return {
        "sample_n": sample_n,
        "win_n": win_n,
        "win_rate_pct": _pct(win_n, sample_n),
        "avg_return_pct": _round(sum(values) / sample_n) if values else None,
        "median_return_pct": _round(float(median(values))) if values else None,
        "best_return_pct": _round(max(values)) if values else None,
        "worst_return_pct": _round(min(values)) if values else None,
    }


def _daily_summaries(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        day = _trade_date(row)
        if day:
            grouped.setdefault(day, []).append(row)
    daily = []
    for day, day_rows in sorted(grouped.items()):
        ordered = _ordered_summary(day_rows)
        returns_5d = _return_summary(day_rows, "return_5d_pct")
        daily.append(
            {
                "trade_date": day,
                "ready_n": ordered["ready_n"],
                "win_rate_pct": ordered["win_rate_pct"],
                "stop_first_pct": ordered["stop_first_pct"],
                "avg_return_5d_pct": returns_5d["avg_return_pct"],
            }
        )
    return daily


def _promotion_guardrail_results(
    *,
    ordered_summary: Dict[str, Any],
    horizon_metrics: Dict[str, Dict[str, Any]],
    distinct_trade_dates: int,
    distinct_themes: int,
    guard: PromotionGuardrails,
) -> List[Dict[str, Any]]:
    ready_n = int(ordered_summary.get("ready_n") or 0)
    win_rate = _to_float(ordered_summary.get("win_rate_pct")) or 0.0
    stop_rate = _to_float(ordered_summary.get("stop_first_pct")) or 100.0
    avg_return_5d = _to_float((horizon_metrics.get("5d") or {}).get("avg_return_pct")) or 0.0
    avg_mfe = _to_float(ordered_summary.get("avg_mfe_pct")) or 0.0
    avg_mae = abs(_to_float(ordered_summary.get("avg_mae_pct")) or 0.0)
    return [
        _check("ready_sample", ready_n, f">={guard.min_ready_n}", ready_n >= guard.min_ready_n),
        _check("ordered_win_rate", win_rate, f">={guard.min_win_rate_pct}", win_rate >= guard.min_win_rate_pct),
        _check("ordered_stop_first", stop_rate, f"<{guard.max_stop_first_pct}", stop_rate < guard.max_stop_first_pct),
        _check("date_diversity", distinct_trade_dates, f">={guard.min_trade_dates}", distinct_trade_dates >= guard.min_trade_dates),
        _check("theme_diversity", distinct_themes, f">={guard.min_theme_count}", distinct_themes >= guard.min_theme_count),
        _check("positive_5d_expectancy", avg_return_5d, ">0", avg_return_5d > 0),
        _check("mfe_beats_mae", _round(avg_mfe - avg_mae), ">0", avg_mfe > avg_mae),
    ]


def _check(name: str, actual: Any, required: str, passed: bool) -> Dict[str, Any]:
    return {"name": name, "actual": actual, "required": required, "passed": bool(passed)}


def _recent_samples(rows: List[Dict[str, Any]], *, limit: int) -> List[Dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: (_trade_date(row), _text(row.get("ticker"))), reverse=True)
    samples = []
    for row in sorted_rows[: max(limit, 0)]:
        samples.append(
            {
                "trade_date": _trade_date(row),
                "ticker": _text(row.get("ticker")),
                "stock_name": _text(row.get("stock_name")),
                "volume_ratio": _round(row.get("volume_ratio")),
                "trend": _text(row.get("trend")),
                "selection_lane": _text(row.get("selection_lane")),
                "ordered_win": _truthy(row.get("ordered_win")),
                "ordered_stop": _truthy(row.get("ordered_stop")),
                "return_5d_pct": _round(row.get("return_5d_pct")),
            }
        )
    return samples


def _market(row: Dict[str, Any]) -> str:
    market = _text(row.get("market") or row.get("market2") or row.get("market_type")).upper()
    ticker = _text(row.get("ticker")).upper()
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    if ticker.endswith(".KS"):
        return "KOSPI"
    return market


def _trade_date(row: Dict[str, Any]) -> str:
    return _text(row.get("trade_date") or row.get("base_trade_date") or row.get("recommended_at") or row.get("created_at"))[:10]


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _text(value).lower()
    return text in {"1", "true", "yes", "y", "on"}


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return None
        number = float(text.replace(",", "").replace("%", ""))
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _round(value: Any, digits: int = 4) -> float | None:
    number = _to_float(value)
    return round(number, digits) if number is not None else None


def _pct(numerator: int, denominator: int) -> float | None:
    return round((numerator / denominator) * 100.0, 4) if denominator else None


def _fmt_signed(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "-"
    return f"{number:+.2f}%"


__all__ = [
    "DEFAULT_JSON_PATH",
    "DEFAULT_MD_PATH",
    "DEFAULT_SOURCE_CSV",
    "GATE_DESCRIPTION",
    "GATE_PROFILE",
    "PromotionGuardrails",
    "build_kosdaq_shadow_observer_markdown",
    "build_kosdaq_shadow_observer_report",
    "is_kosdaq_ordered_rebound_observer_row",
    "load_observer_rows",
    "write_kosdaq_shadow_observer_report",
]
