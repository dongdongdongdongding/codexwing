"""Model-lane scan dispatch — run a (market, scan_mode) scan through the SAME validated
producer that daily_ops uses, so the result tickers are 100% identical to the model's picks.

The data pipeline (KIS / FDR / px_long / KIS minute bars) is unchanged; only the selection
MODEL is swapped from the legacy admission scanner to the validated model lane:

    (KOSPI|KOSDAQ, SWING)   -> report_swing_ensemble.score_market   -> swing_ensemble
    (NASDAQ,       SWING)   -> report_nasdaq_session_edge_shadow.run_model -> nasdaq_session_edge
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
    ("KOSPI", "SWING"): "swing_candidate",   # 2026-07-06 P3 교체
    ("KOSDAQ", "SWING"): "swing_candidate",
    ("NASDAQ", "SWING"): "nasdaq_session_edge",
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
    # 은퇴 레인은 스캔조차 하지 않는다. 단일 출처는 stream_exclusion.RETIRED_LANES 다 —
    # 여기에 목록을 복제하면 두 곳이 어긋나고, 그게 F1(판정 사본이 둘)이 만든 사고 계열이다.
    try:
        from modules.stream_exclusion import RETIRED_LANES
    except ImportError:
        from stream_exclusion import RETIRED_LANES
    if bucket in RETIRED_LANES:
        out["error"] = f"lane_{RETIRED_LANES[bucket]}: {bucket}"
        out["note"] = "은퇴한 레인 — 스캔·라우팅 없음 (modules/stream_exclusion.RETIRED_LANES)"
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
            import report_nasdaq_session_edge_shadow as nas
            from report_swing_ensemble import _route_live
            args = argparse.Namespace(
                panel=os.getenv("AG_NASDAQ_SESSION_EDGE_PANEL", "latest"),
                raw_dir=os.getenv("AG_NASDAQ_SESSION_EDGE_RAW_DIR", str(nas.DEFAULT_RAW_OHLCV_DIR)),
                cache_dir=os.getenv("AG_NASDAQ_SESSION_EDGE_CACHE_DIR", str(nas.DEFAULT_CACHE_DIR)),
                out_dir=str(nas.DEFAULT_OUT_DIR),
                ledger=str(nas.DEFAULT_LEDGER),
                model_bundle=str(nas.DEFAULT_MODEL_BUNDLE),
                source_report=os.getenv("AG_NASDAQ_SESSION_EDGE_SOURCE_REPORT", ""),
                market_session=os.getenv(
                    "AG_NASDAQ_SESSION_EDGE_MARKET_SESSION",
                    os.getenv("AG_PRIMARY_SESSION_ID", "nasdaq_regular_close"),
                ),
                session_cutoff=os.getenv(
                    "AG_NASDAQ_SESSION_EDGE_SESSION_CUTOFF",
                    os.getenv("AG_PRIMARY_SESSION_CUTOFF", "16:05 America/New_York"),
                ),
                max_symbols=int(os.getenv("AG_NASDAQ_SESSION_EDGE_MAX_SYMBOLS", "120")),
                min_liq20=float(os.getenv("AG_NASDAQ_SESSION_EDGE_MIN_LIQ20", "100000000")),
                period=os.getenv("AG_NASDAQ_SESSION_EDGE_PERIOD", "60d"),
                interval=os.getenv("AG_NASDAQ_SESSION_EDGE_INTERVAL", "5m"),
                timeout=int(os.getenv("AG_NASDAQ_SESSION_EDGE_TIMEOUT", "20")),
                refresh_cache=os.getenv("AG_NASDAQ_SESSION_EDGE_REFRESH_CACHE", "0").strip() in {"1", "true", "True"},
                no_fetch=os.getenv("AG_NASDAQ_SESSION_EDGE_NO_FETCH", "0").strip() in {"1", "true", "True"},
                settle_only=False,
                settle_blocked_session=False,
                no_ledger=not bool(route),
                no_model_bundle=os.getenv("AG_NASDAQ_SESSION_EDGE_NO_MODEL_BUNDLE", "0").strip() in {"1", "true", "True"},
                dry_run=False,
            )
            report = nas.run_model(args)
            picks = list(report.get("picks") or [])
            score_key = str(report.get("score_date") or today).replace("-", "")
            run_id = f"NASDAQ-SESSION-EDGE-{score_key}"
            note = (
                "NASDAQ regular-close session edge is operator-enabled for the new-web scan lane; "
                "recent-intraday sample limits and regime validation are traced in the report."
            )
            if report.get("session_blocked"):
                note = (
                    f"NASDAQ session edge blocked for session `{report.get('market_session')}`: "
                    f"{report.get('session_block_reason')}. No live route written."
                )
            routed = 0
            if route and picks and not report.get("session_blocked"):
                routed = _route_live(
                    picks,
                    run_id,
                    rec,
                    bucket="nasdaq_session_edge",
                    decision="NASDAQ_SESSION_EDGE_BUY",
                    lane="NASDAQ_SESSION_EDGE",
                )
            out.update(
                run_id=run_id,
                picks=picks,
                routed=routed,
                note=note,
                session_contract=report.get("session_contract") or {},
                market_session=report.get("market_session"),
                session_cutoff=(report.get("session_contract") or {}).get("session_cutoff"),
                source_price_kind=(report.get("session_contract") or {}).get("source_price_kind"),
                sample_limit_warning=(report.get("session_contract") or {}).get("sample_limit_warning") or report.get("sample_limit_warning"),
                session_blocked=bool(report.get("session_blocked")),
                session_block_reason=report.get("session_block_reason") or "",
                promotion_ready=bool(report.get("promotion_ready")),
                promotion_gate=report.get("promotion_gate") or {},
                capital_status=report.get("capital_status") or "",
                promotion_note=report.get("promotion_note") or "",
            )
        elif mode == "SWING":
            # 2026-07-07: P3 교체 반영 누락 수정 — 웹/디스코드 스윙 스캔이 은퇴한 앙상블을 돌려
            # 픽 탭(8y first-touch 랭커)과 다른 종목을 라우팅하던 버그. 이제 본선 랭커를 실행.
            from report_kr_swing_candidate import score_today as swing_score
            from report_swing_ensemble import _route_live
            scored = swing_score(3)
            picks = [{"ticker": p["ticker"], "market": p["market"],
                      "p": p["p"] if p["p"] <= 1.5 else p["p"] / 100.0,
                      "entry_reference_price": p["close"], "liq억": p.get("liq_eok"),
                      "mkt_state": p.get("mkt_state")}
                     for p in scored.get("picks", []) if p.get("market") == market]
            run_id = f"SWING-CAND-{today}-{market}"
            out.update(run_id=run_id, picks=picks)
            if route and picks:
                out["routed"] = _route_live(picks, run_id, rec, bucket="swing_candidate",
                                            decision="SWING_CANDIDATE_BUY", lane="SWING_CANDIDATE")
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
