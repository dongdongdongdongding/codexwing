"""Model-lane scan dispatch — run a (market, scan_mode) scan through the SAME validated
producer that daily_ops uses, so the result tickers are 100% identical to the model's picks.

The data pipeline (KIS / FDR / px_long / KIS minute bars) is unchanged; only the selection
MODEL is swapped from the legacy admission scanner to the validated model lane:

    (KOSPI|KOSDAQ, SWING)   -> report_swing_ensemble.score_market   -> swing_ensemble
    (KOSPI,        INTRADAY) -> report_kospi_intraday_swing.score_today -> kospi_intraday
    (KOSDAQ,       INTRADAY) -> report_kosdaq_intraday_vwap_guard.score_live_candidates
                                                              -> kosdaq_intraday_3d_t5_vwap_guard

Identical-ticker guarantee is structural: the same producer scoring function is called with the
same defaults as the producer's own ``main()``, on the same deterministic data, so it selects
the same tickers regardless of whether it ran here, in daily_ops, or from the CLI.

The legacy planner pipeline is NOT removed — it keeps running via run_kr_daily_auto_scans for
learning/validation; this dispatch only changes what a manual scan produces and shows.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_TOOLS = Path(__file__).resolve().parent.parent / "multi_agent" / "tools"


def _ensure_tools_on_path() -> None:
    p = str(_TOOLS)
    if p not in sys.path:
        sys.path.insert(0, p)


# Defaults mirror each producer's main() exactly so tickers match the daily_ops picks.
SWING_TOP_PCT = 1.0
SWING_MIN_LIQ = 100.0
KOSPI_INTRADAY_MIN_LIQ = 100.0
KOSDAQ_INTRADAY_MIN_LIQ = 30.0
KOSDAQ_INTRADAY_TRADEABILITY_LIQ = 100.0

LANE_BY_MODE = {
    ("KOSPI", "SWING"): "swing_ensemble",
    ("KOSDAQ", "SWING"): "swing_ensemble",
    ("KOSPI", "INTRADAY"): "kospi_intraday",
    ("KOSDAQ", "INTRADAY"): "kosdaq_intraday_3d_t5_vwap_guard",
}


def model_lane_for(market: str, scan_mode: str) -> str | None:
    return LANE_BY_MODE.get((str(market).upper(), str(scan_mode).upper()))


def run_model_lane_scan(market: str, scan_mode: str, *, route: bool = True) -> Dict[str, Any]:
    """Run the validated model-lane producer for (market, scan_mode) and return its picks.

    Returns {run_id, market, scan_mode, bucket, picks, routed, error}. ``picks`` are the exact
    producer picks (identical tickers to daily_ops). ``route`` writes them to the live surface
    (market_scan_results + scan_deep_reports) via the producer's own routing."""
    market = str(market).upper()
    mode = str(scan_mode).upper()
    bucket = model_lane_for(market, mode)
    out: Dict[str, Any] = {"run_id": "", "market": market, "scan_mode": mode, "bucket": bucket,
                           "picks": [], "routed": 0, "error": None}
    if bucket is None:
        out["error"] = f"unsupported market/scan_mode: {market}/{mode}"
        return out
    _ensure_tools_on_path()
    today = datetime.now().strftime("%Y%m%d")
    rec = datetime.now(timezone.utc).isoformat()
    try:
        if mode == "SWING":
            from report_swing_ensemble import score_market, _route_live
            picks = score_market(market, SWING_TOP_PCT, SWING_MIN_LIQ)
            run_id = f"SWING-ENS-{today}-{market}"
            out.update(run_id=run_id, picks=picks)
            if route and picks:
                out["routed"] = _route_live(picks, run_id, rec, bucket="swing_ensemble",
                                            decision="SWING_ENSEMBLE_BUY", lane="SWING_ENSEMBLE")
        elif market == "KOSPI":  # INTRADAY
            from report_kospi_intraday_swing import score_today
            from report_swing_ensemble import _route_live
            picks = score_today(KOSPI_INTRADAY_MIN_LIQ)
            run_id = f"KOSPI-ITD-{today}"
            out.update(run_id=run_id, picks=picks)
            if route and picks:
                out["routed"] = _route_live(picks, run_id, rec, bucket="kospi_intraday",
                                            decision="KOSPI_INTRADAY_BUY", lane="KOSPI_INTRADAY")
        else:  # KOSDAQ INTRADAY
            import joblib
            import report_kosdaq_intraday_vwap_guard as kq
            from modules.kis_openapi import KISConfig, KISOpenAPIClient
            trade_date = kq._trade_date_arg("")
            model_bundle = joblib.load(kq.PROJECT_ROOT / kq.MODEL_PATH)
            client = KISOpenAPIClient(KISConfig.from_env())
            client.get_access_token()
            score_result = kq.score_live_candidates(
                client=client, model_bundle=model_bundle, trade_date=trade_date,
                min_liq_eok=KOSDAQ_INTRADAY_MIN_LIQ, tradeability_floor_eok=KOSDAQ_INTRADAY_TRADEABILITY_LIQ,
                max_symbols=0, entry_input_hour=kq.ENTRY_INPUT_HOUR,
                daily_context_source="cache", sleep_sec=0.03,
            )
            picks = list(score_result.get("picks") or [])
            run_id = str(score_result.get("run_id") or f"KQ-ITD-3D-T5-{trade_date}")
            out.update(run_id=run_id, picks=picks)
            if route and picks:
                out["routed"] = kq.route_live_intraday(picks, run_id=run_id, recommended_at=rec)
    except Exception as exc:  # pragma: no cover - live data dependent
        out["error"] = repr(exc)[:300]
    return out
