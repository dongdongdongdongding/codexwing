"""Model-lane scan dispatch — run a (market, scan_mode) scan through the SAME validated
producer that daily_ops uses, so the result tickers are 100% identical to the model's picks.

The data pipeline (KIS / FDR / px_long / KIS minute bars) is unchanged; only the selection
MODEL is swapped from the legacy admission scanner to the validated model lane:

    (KOSPI|KOSDAQ, SWING)   -> report_swing_ensemble.score_market   -> swing_ensemble
    (NASDAQ,       SWING)   -> report_nasdaq_daily_edge_shadow.run_model -> nasdaq_swing_daily_edge
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

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

_TOOLS = Path(__file__).resolve().parent.parent / "multi_agent" / "tools"
_KST = timezone(timedelta(hours=9))

# Intraday feature windows: the validated models compute end-of-window features (KOSPI uses the
# full session incl. close & late30_ret vs 15:00; KOSDAQ uses up to the 15:00 entry). Before the
# window closes those features are incomplete, so an earlier scan would yield invalid picks. This
# is a model-design constraint, not a data-fetch limit. (HH, MM) the model becomes valid in KST.
INTRADAY_VALID_AFTER = {"KOSPI": (15, 30), "KOSDAQ": (15, 0)}


def _ensure_tools_on_path() -> None:
    p = str(_TOOLS)
    if p not in sys.path:
        sys.path.insert(0, p)


def model_lane_scan_enabled() -> bool:
    """When on (default), a KR scan runs the validated model-lane producer instead of the legacy
    admission scanner. Shared by the web app and the Discord bot."""
    return os.getenv("AG_SCAN_MODEL_LANE", "1").strip() not in {"0", "false", "False", ""}


def _intraday_window_block(market: str) -> str | None:
    """Return a user message if an intraday scan is run before its feature window closes, else None.
    Override with AG_INTRADAY_IGNORE_WINDOW=1 (e.g. for replay on a past trade_date)."""
    if os.getenv("AG_INTRADAY_IGNORE_WINDOW", "0").strip() in {"1", "true", "True"}:
        return None
    req = INTRADAY_VALID_AFTER.get(market)
    if not req:
        return None
    now = datetime.now(_KST)
    if (now.hour, now.minute) < req:
        label = "코스피 15:30(마감)" if market == "KOSPI" else "코스닥 15:00"
        return (f"장중 모델은 {label} 이후에 유효합니다 (현재 {now:%H:%M} KST). 그 전에는 일중 피처"
                f"(종가·late30·VWAP 등)가 미완성이라 무효 픽이 나옵니다. 마감 후 다시 스캔하세요.")
    return None


# Defaults mirror each producer's main() exactly so tickers match the daily_ops picks.
SWING_TOP_PCT = 1.0
SWING_MIN_LIQ = 100.0
KOSPI_INTRADAY_MIN_LIQ = 100.0
KOSDAQ_INTRADAY_MIN_LIQ = 30.0
KOSDAQ_INTRADAY_TRADEABILITY_LIQ = 100.0

LANE_BY_MODE = {
    ("KOSPI", "SWING"): "swing_ensemble",
    ("KOSDAQ", "SWING"): "swing_ensemble",
    ("NASDAQ", "SWING"): "nasdaq_swing_daily_edge",
    ("KOSPI", "INTRADAY"): "kospi_intraday",
    ("KOSDAQ", "INTRADAY"): "kosdaq_intraday_3d_t5_vwap_guard",
}


def model_lane_for(market: str, scan_mode: str) -> str | None:
    return LANE_BY_MODE.get((str(market).upper(), str(scan_mode).upper()))


def _latest_stored_picks(bucket: str, market: str = "") -> Dict[str, Any]:
    """Latest stored picks for a lane from scan_deep_reports (the last complete session's
    daily_ops output). Used pre-market / mid-session so an intraday scan surfaces the last valid
    signal instead of re-running on incomplete intraday data."""
    try:
        from modules.db_manager import DBManager
        db = DBManager()
        if not db.client:
            return {"run_id": "", "picks": [], "generated_at": ""}
        q = db.client.table("scan_deep_reports").select(
            "ticker,run_id,buy_score,generated_at,candidate_interpretation,trade_plan"
        ).eq("decision_bucket", bucket)
        if market:
            q = q.eq("market", market.upper())
        rows = q.order("generated_at", desc=True).limit(20).execute().data or []
        if not rows:
            return {"run_id": "", "picks": [], "generated_at": ""}
        latest_run = str(rows[0].get("run_id") or "")
        picks = []
        for r in rows:
            if str(r.get("run_id") or "") != latest_run:
                continue
            ci = r.get("candidate_interpretation") if isinstance(r.get("candidate_interpretation"), dict) else {}
            tp = r.get("trade_plan") if isinstance(r.get("trade_plan"), dict) else {}
            picks.append({"ticker": r.get("ticker"), "p": float(r.get("buy_score") or 0.0),
                          "entry_reference_price": ci.get("entry_reference_price") or tp.get("entry_reference_price")})
        return {"run_id": latest_run, "picks": picks, "generated_at": str(rows[0].get("generated_at") or "")}
    except Exception:
        return {"run_id": "", "picks": [], "generated_at": ""}


def run_model_lane_scan(market: str, scan_mode: str, *, route: bool = True) -> Dict[str, Any]:
    """Run the validated model-lane producer for (market, scan_mode) and return its picks.

    Returns {run_id, market, scan_mode, bucket, picks, routed, error}. ``picks`` are the exact
    producer picks (identical tickers to daily_ops). ``route`` writes them to the live surface
    (market_scan_results + scan_deep_reports) via the producer's own routing."""
    market = str(market).upper()
    mode = str(scan_mode).upper()
    bucket = model_lane_for(market, mode)
    out: Dict[str, Any] = {"run_id": "", "market": market, "scan_mode": mode, "bucket": bucket,
                           "picks": [], "routed": 0, "error": None, "stale_session": False, "note": None}
    if bucket is None:
        out["error"] = f"unsupported market/scan_mode: {market}/{mode}"
        return out
    if mode == "INTRADAY":
        block = _intraday_window_block(market)
        if block:
            # Window not complete (pre-market / mid-session): re-running would score incomplete
            # intraday features. Surface the last complete session's stored picks instead — the
            # same signal /signals shows, valid until the next close run.
            stored = _latest_stored_picks(bucket, market)
            out.update(picks=stored.get("picks") or [], run_id=stored.get("run_id") or "",
                       stale_session=True,
                       note=f"{block.split('.')[0]}. 최신 완성 세션({stored.get('generated_at', '')[:10]}) 신호를 표시합니다.")
            return out
        # Intraday producers need live KIS minute bars. The web app runs with
        # KIS_ENABLE_LIVE_CALLS=0 (lightweight browsing); enable it just for this scan, matching
        # how run_daily_ops invokes the producers (KIS_ENABLE_LIVE_CALLS=1).
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
    _ensure_tools_on_path()
    today = datetime.now().strftime("%Y%m%d")
    rec = datetime.now(timezone.utc).isoformat()
    try:
        if market == "NASDAQ" and mode == "SWING":
            import argparse
            import report_nasdaq_daily_edge_shadow as nas
            args = argparse.Namespace(
                panel=os.getenv("AG_NASDAQ_SWING_PANEL", "latest"),
                out_dir=str(nas.DEFAULT_OUT_DIR),
                ledger=str(nas.DEFAULT_LEDGER),
                model_bundle=str(nas.DEFAULT_MODEL_BUNDLE),
                market_session=os.getenv(
                    "AG_NASDAQ_SWING_MARKET_SESSION",
                    os.getenv("AG_PRIMARY_SESSION_ID", "manual_eod_latest"),
                ),
                session_cutoff=os.getenv(
                    "AG_NASDAQ_SWING_SESSION_CUTOFF",
                    os.getenv("AG_PRIMARY_SESSION_CUTOFF", ""),
                ),
                source_price_kind=os.getenv("AG_NASDAQ_SWING_SOURCE_PRICE_KIND", "daily_eod_close"),
                allow_non_final_session=os.getenv(
                    "AG_NASDAQ_SWING_ALLOW_NON_FINAL_SESSION", "0"
                ).strip() in {"1", "true", "True"},
                score_date="",
                min_price=1.0,
                research_liq_floor=10_000_000.0,
                cost_pct=0.20,
                embargo_days=20,
                min_train_rows=int(os.getenv("AG_NASDAQ_SWING_MIN_TRAIN_ROWS", "100000")),
                max_train_rows=int(os.getenv("AG_NASDAQ_SWING_MAX_TRAIN_ROWS", "160000")),
                lgbm_estimators=int(os.getenv("AG_NASDAQ_SWING_LGBM_ESTIMATORS", "110")),
                seed=20260629,
                settle_only=False,
                no_ledger=not bool(route),
                no_model_bundle=os.getenv("AG_NASDAQ_SWING_NO_MODEL_BUNDLE", "0").strip() in {"1", "true", "True"},
                dry_run=False,
            )
            report = nas.run_model(args)
            picks = list(report.get("picks") or [])
            run_id = f"NASDAQ-SWING-EDGE-{str(report.get('score_date') or today).replace('-', '')}"
            note = "NASDAQ SWING model lane is forward-shadow only; no live recommendation routing."
            if report.get("session_blocked"):
                note = (
                    f"NASDAQ SWING EOD model blocked for session `{report.get('market_session')}`: "
                    f"{report.get('session_block_reason')}. Existing ledger settlement only."
                )
            out.update(
                run_id=run_id,
                picks=picks,
                routed=0,
                note=note,
                session_contract=report.get("session_contract") or {},
                market_session=report.get("market_session"),
                session_cutoff=report.get("session_cutoff"),
                source_price_kind=report.get("source_price_kind"),
                freshness_status=report.get("freshness_status"),
                finality_status=report.get("finality_status"),
                session_blocked=bool(report.get("session_blocked")),
                session_block_reason=report.get("session_block_reason") or "",
            )
        elif mode == "SWING":
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
