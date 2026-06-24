from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPORT_VERSION = "intraday_candidate_registry_v1"
DEFAULT_OUTPUT_DIR = Path("runtime_state/reports/experimental")
DEFAULT_JSON_PATH = DEFAULT_OUTPUT_DIR / "intraday_candidate_registry_latest.json"
DEFAULT_MD_PATH = DEFAULT_OUTPUT_DIR / "intraday_candidate_registry_latest.md"


def build_intraday_candidate_registry(
    *,
    as_of_date: str | None = None,
    generated_at: str | None = None,
) -> Dict[str, Any]:
    """Return traceable INTRADAY-only promotion/research candidates.

    These entries are not live production promotions. They are a registry for
    scanner/planner candidates whose evidence was produced from minute-bar
    features, so scan_mode must remain INTRADAY even when the validation label
    is 5D.
    """

    candidates = [_kospi_0905_5d_shadow(), _kosdaq_1400_3d_t5_shadow(), _kosdaq_tail_guard_research()]
    return {
        "report_version": REPORT_VERSION,
        "as_of_date": as_of_date or str(date.today()),
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "scope": {
            "scan_mode": "INTRADAY",
            "production_enabled": False,
            "swing_contamination_allowed": False,
            "note": "Minute-bar candidates only. Do not route these through SWING gates.",
        },
        "candidates": candidates,
        "summary": {
            "total": len(candidates),
            "shadow_candidates": sum(1 for row in candidates if row.get("status") == "shadow_candidate"),
            "research_only": sum(1 for row in candidates if row.get("status") == "research_only"),
            "production_enabled": 0,
        },
    }


def write_intraday_candidate_registry(
    report: Dict[str, Any],
    *,
    json_path: Path = DEFAULT_JSON_PATH,
    md_path: Path = DEFAULT_MD_PATH,
) -> Dict[str, str]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_intraday_candidate_registry_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


def build_intraday_candidate_registry_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = [
        "# Intraday Candidate Registry",
        "",
        f"- Version: `{report.get('report_version', REPORT_VERSION)}`",
        f"- Scope: `{(report.get('scope') or {}).get('scan_mode', 'INTRADAY')}`",
        f"- Production enabled: `{(report.get('scope') or {}).get('production_enabled', False)}`",
        f"- Swing contamination allowed: `{(report.get('scope') or {}).get('swing_contamination_allowed', False)}`",
        "",
        "## Candidates",
    ]
    for row in report.get("candidates") or []:
        validation = row.get("validation") or {}
        guard = row.get("promotion_guard") or {}
        lines.extend(
            [
                "",
                f"### {row.get('candidate_id')}",
                "",
                f"- Status: `{row.get('status')}`",
                f"- Segment: `{row.get('market')}` / `{row.get('scan_mode')}` / `{row.get('strategy_family')}`",
                f"- Entry: `{row.get('entry_policy')}`",
                f"- Horizon: `{row.get('target_horizon_days')}D`",
                f"- Liquidity floor: `{row.get('liquidity_floor_eok')}eok`",
                (
                    "- Validation: "
                    f"n={validation.get('n')}, days={validation.get('days')}, months={validation.get('months')}, "
                    f"{_validation_metric_text(validation)}"
                ),
                f"- Promotion guard: `{guard.get('status')}` - {guard.get('reason')}",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _kospi_0905_5d_shadow() -> Dict[str, Any]:
    return {
        "candidate_id": "kospi_intraday_0905_5d_t10s5_shadow_v1",
        "status": "shadow_candidate",
        "market": "KOSPI",
        "scan_mode": "INTRADAY",
        "strategy_family": "KR_INTRADAY_5D",
        "candidate_family": "intraday_confirmed_5d_path",
        "entry_policy": "09:05 minute-confirmed entry",
        "entry_time_kst": "09:05",
        "target_horizon_days": 5,
        "liquidity_floor_eok": 100,
        "model_family": "OOS ensemble: LGBM + ExtraTrees, label=t10_s5",
        "exit_contract": {
            "primary_return_col": "exit5d_ret_t10_s5",
            "target_tp_pct": 10.0,
            "stop_sl_pct": -5.0,
            "hold_days": 5,
            "cost_pct": 0.28,
        },
        "validation": {
            "source": "/private/tmp/intraday_kospi100_0905_t10_ensemble_verify.json",
            "sample": "KOSPI >=100eok, OOS months, top5_q55, t10_s5",
            "n": 421,
            "days": 101,
            "months": 10,
            "net_avg_pct": 2.299,
            "net_ci_pct": [1.794, 3.137],
            "excess_avg_pct": 1.272,
            "excess_ci_pct": [0.925, 2.217],
            "win_pct": 62.71,
            "day_win_pct": 78.22,
            "target_first_pct": 21.6,
            "stop_first_pct": 15.2,
            "months_pos": 10,
        },
        "promotion_guard": {
            "status": "shadow_only",
            "reason": "Daily-basket win clears 75%, but per-pick win is below 75% and stop-first is near the 15% guard. Needs forward ledger before production.",
            "production_enabled": False,
        },
    }


def _kosdaq_1400_3d_t5_shadow() -> Dict[str, Any]:
    return {
        "candidate_id": "kosdaq_intraday_1400_3d_t5_lgbm_shadow_v1",
        "status": "shadow_candidate",
        "market": "KOSDAQ",
        "scan_mode": "INTRADAY",
        "strategy_family": "KR_INTRADAY_3D_T5",
        "candidate_family": "intraday_confirmed_3d_touch5",
        "entry_policy": "14:00 minute-confirmed entry, daily top5 if calibrated probability >=75%",
        "entry_time_kst": "14:00",
        "target_horizon_days": 3,
        "liquidity_floor_eok": 30,
        "model_family": "LGBM classifier + previous-month isotonic calibration",
        "model_artifact": "models/kr_intraday_3d_t5/kosdaq_liq30_1400_lgbm_isotonic.pkl",
        "selection_policy": {
            "min_calibrated_probability": 0.75,
            "max_picks_per_day": 5,
            "probability_target": "touch +5% within 3 trading days from the 14:00 entry price",
        },
        "exit_contract": {
            "primary_return_col": "target_touch3d_t5",
            "target_tp_pct": 5.0,
            "stop_sl_pct": None,
            "hold_days": 3,
            "cost_pct": 0.33,
        },
        "validation": {
            "source": "/private/tmp/intraday_3d_t5_calibrated_lgbm_scan.json",
            "sample": "KOSDAQ >=30eok, 14:00, calibrated p>=75%, top5 per day",
            "n": 218,
            "days": 91,
            "months": 8,
            "hit_pct": 81.7,
            "hit_ci_pct": [76.6, 86.2],
            "day_hit_pct": 93.4,
            "avg_pred_pct": 88.2,
            "mfe3_avg_pct": 19.3,
            "mae3_avg_pct": -9.2,
            "close3_avg_pct": 3.6,
            "stop2_touch_pct": 78.4,
            "months_hit_ge_70": 7,
        },
        "promotion_guard": {
            "status": "shadow_only",
            "reason": "Meets the 3D +5% target-touch probability goal, but stop/drawdown incidence is high. Forward ledger must track target-touch and drawdown separately before production.",
            "production_enabled": False,
        },
    }


def _kosdaq_tail_guard_research() -> Dict[str, Any]:
    return {
        "candidate_id": "kosdaq_intraday_tail_guard_research_v1",
        "status": "research_only",
        "market": "KOSDAQ",
        "scan_mode": "INTRADAY",
        "strategy_family": "KR_INTRADAY_5D",
        "candidate_family": "intraday_tail_guard_5d_path",
        "entry_policy": "11:30 minute-confirmed entry with nostop/MAE guard",
        "entry_time_kst": "11:30",
        "target_horizon_days": 5,
        "liquidity_floor_eok": 30,
        "model_family": "OOS LGBM return model + tail-risk guard",
        "exit_contract": {
            "primary_return_col": "exit5d_ret_t10_s5",
            "target_tp_pct": 10.0,
            "stop_sl_pct": -5.0,
            "hold_days": 5,
            "cost_pct": 0.33,
        },
        "validation": {
            "source": "/private/tmp/kosdaq_intraday_tail_guard_focused_search.json",
            "sample": "KOSDAQ >=30eok, 11:30 combo top2, nostop_q=0.9, mae_q=0.7",
            "n": 174,
            "days": 101,
            "months": 9,
            "net_avg_pct": 1.08,
            "net_ci_pct": [0.358, 1.908],
            "excess_avg_pct": 1.19,
            "excess_ci_pct": [0.59, 1.85],
            "win_pct": 49.4,
            "day_win_pct": 50.5,
            "target_first_pct": 17.2,
            "stop_first_pct": 17.8,
            "months_pos": 5,
        },
        "promotion_guard": {
            "status": "research_only",
            "reason": "Tail guard lowers stop-first, but win/day-win stay near 50%; not an operating promotion candidate.",
            "production_enabled": False,
        },
    }


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "-"


def _validation_metric_text(validation: Dict[str, Any]) -> str:
    if "hit_pct" in validation:
        return (
            f"hit={_fmt(validation.get('hit_pct'))}%, "
            f"hit_ci=[{_fmt((validation.get('hit_ci_pct') or [None, None])[0])},"
            f"{_fmt((validation.get('hit_ci_pct') or [None, None])[1])}]%, "
            f"day_hit={_fmt(validation.get('day_hit_pct'))}%, "
            f"avg_pred={_fmt(validation.get('avg_pred_pct'))}%, "
            f"stop2_touch={_fmt(validation.get('stop2_touch_pct'))}%"
        )
    return (
        f"net={_fmt(validation.get('net_avg_pct'))}%, "
        f"excess={_fmt(validation.get('excess_avg_pct'))}%, "
        f"win={_fmt(validation.get('win_pct'))}%, "
        f"day_win={_fmt(validation.get('day_win_pct'))}%, "
        f"stop_first={_fmt(validation.get('stop_first_pct'))}%"
    )


__all__ = [
    "REPORT_VERSION",
    "build_intraday_candidate_registry",
    "build_intraday_candidate_registry_markdown",
    "write_intraday_candidate_registry",
]
