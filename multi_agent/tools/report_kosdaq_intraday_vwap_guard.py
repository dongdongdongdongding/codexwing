#!/usr/bin/env python3
"""Live KOSDAQ INTRADAY producer for the 15:00 VWAP-guard 3D +5% model.

This is the Codex lane of the Claude+Codex intraday synthesis:

- market: KOSDAQ
- scan_mode: INTRADAY
- entry: 15:00 minute-confirmed price
- model: LGBM + previous-month isotonic calibration
- gate: calibrated p>=0.80, pre-entry VWAP distance >=0, daily top2
- target: +5% touch within 3 trading days from the 15:00 entry
- return ledger: 3D close hold, MFE/MAE, touch3d_t5

It records both liquidity lanes:

- >=30eok: main edge lane
- >=100eok: tradeability lane
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "runtime_state" / "tmp" / "matplotlib"))
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env.local")
except Exception:
    pass
os.environ.setdefault("KIS_ENABLE_LIVE_CALLS", "1")

from modules.kis_operational_adapter import normalize_kis_daily_bars, normalize_kis_minute_bars  # noqa: E402
from modules.kosdaq_intraday_vwap_guard import (  # noqa: E402
    CANDIDATE_ID,
    ENTRY_INPUT_HOUR,
    MODEL_PATH,
    ROUNDTRIP_COST_PCT,
    STRATEGY_FAMILY,
    TARGET_COLUMN,
    build_feature_row,
    compute_daily_prev_context,
    compute_index_prev_context,
    live_pick_payload,
    normalize_kr_code,
    safe_float,
    score_feature_rows,
    select_vwap_guard_candidates,
)


CACHE = Path(os.path.expanduser("~/research_cache"))
REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "experimental"
LEDGER = REPORT_DIR / "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl"
REPORT_JSON = REPORT_DIR / "kosdaq_intraday_1500_3d_t5_vwap_guard_latest.json"
REPORT_MD = REPORT_DIR / "kosdaq_intraday_1500_3d_t5_vwap_guard_latest.md"


def _now_kst() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        return datetime.now()


def _trade_date_arg(value: str | None) -> str:
    text = str(value or "").strip().replace("-", "")
    if text:
        return text
    return _now_kst().strftime("%Y%m%d")


def _iso_trade_date(trade_date: str) -> str:
    parsed = pd.to_datetime(str(trade_date), format="%Y%m%d", errors="coerce")
    return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else str(trade_date)


def _load_px_cache() -> pd.DataFrame:
    path = CACHE / "px_long.parquet"
    cols = [
        "code",
        "date",
        "market",
        "close",
        "liq",
        "ret_1d",
        "ret_3d",
        "ret_5d",
        "ret_10d",
        "ret_20d",
        "ma5_dist",
        "ma20_dist",
        "ma60_dist",
        "ma20_slope",
        "rsi14",
        "rsi_slope",
        "accel",
        "consec_up",
        "dist_hi20",
        "dist_hi60",
        "pos20",
        "bb_pctb",
        "bb_bw",
        "atr_pct",
        "vol20",
        "close_loc",
        "vol_ratio",
        "vol_trend",
        "turn_z",
        "obv_slope",
        "cmf20",
        "idx_mom20",
        "idx_vol20",
    ]
    frame = pd.read_parquet(path, columns=cols)
    frame["code"] = frame["code"].astype(str).map(normalize_kr_code)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame[frame["market"].astype(str).str.upper().eq("KOSDAQ")].copy()


def _load_universe(px: pd.DataFrame, *, min_liq_eok: float, max_symbols: int = 0) -> List[str]:
    if px.empty:
        return []
    recent = px[px["date"] >= px["date"].max() - pd.Timedelta(days=90)]
    med = recent.groupby("code")["liq"].median().dropna().sort_values(ascending=False)
    codes = med[med >= min_liq_eok * 1e8].index.astype(str).tolist()
    if max_symbols and max_symbols > 0:
        codes = codes[: int(max_symbols)]
    return codes


def _cache_daily_context(px: pd.DataFrame, code: str, *, trade_date: str) -> Dict[str, Any]:
    if px.empty:
        return {}
    cutoff = pd.to_datetime(str(trade_date), format="%Y%m%d", errors="coerce")
    rows = px[px["code"].eq(normalize_kr_code(code))]
    if pd.notna(cutoff):
        rows = rows[rows["date"].dt.normalize() < cutoff.normalize()]
    if rows.empty:
        return {}
    row = rows.sort_values("date").iloc[-1]
    out: Dict[str, Any] = {
        "prev_close": safe_float(row.get("close")),
        "prev_date": pd.to_datetime(row.get("date")).strftime("%Y-%m-%d"),
        "liq_prev_eok": safe_float(row.get("liq")) / 1e8 if safe_float(row.get("liq")) is not None else None,
        "idx_mom20_prev": safe_float(row.get("idx_mom20")),
        "idx_vol20_prev": safe_float(row.get("idx_vol20")),
    }
    for col in [
        "ret_1d",
        "ret_3d",
        "ret_5d",
        "ret_10d",
        "ret_20d",
        "ma5_dist",
        "ma20_dist",
        "ma60_dist",
        "ma20_slope",
        "rsi14",
        "rsi_slope",
        "accel",
        "consec_up",
        "dist_hi20",
        "dist_hi60",
        "pos20",
        "bb_pctb",
        "bb_bw",
        "atr_pct",
        "vol20",
        "close_loc",
        "vol_ratio",
        "vol_trend",
        "turn_z",
        "obv_slope",
        "cmf20",
    ]:
        out[f"{col}_prev"] = safe_float(row.get(col))
    return out


def _cache_index_context(px: pd.DataFrame, *, trade_date: str) -> Dict[str, Any]:
    if px.empty:
        return {"idx_mom20_prev": None, "idx_vol20_prev": None}
    cutoff = pd.to_datetime(str(trade_date), format="%Y%m%d", errors="coerce")
    rows = px
    if pd.notna(cutoff):
        rows = rows[rows["date"].dt.normalize() < cutoff.normalize()]
    if rows.empty:
        return {"idx_mom20_prev": None, "idx_vol20_prev": None}
    latest_date = rows["date"].max()
    row = rows[rows["date"].eq(latest_date)].iloc[0]
    return {"idx_mom20_prev": safe_float(row.get("idx_mom20")), "idx_vol20_prev": safe_float(row.get("idx_vol20"))}


def _fdr_index_context(trade_date: str) -> Dict[str, Any]:
    try:
        import FinanceDataReader as fdr

        end = pd.to_datetime(str(trade_date), format="%Y%m%d", errors="coerce")
        start = (end - pd.Timedelta(days=180)).strftime("%Y-%m-%d") if pd.notna(end) else f"{datetime.now().year - 1}-01-01"
        frame = fdr.DataReader("KQ11", start)
        return compute_index_prev_context(pd.to_numeric(frame["Close"], errors="coerce"), trade_date=trade_date)
    except Exception:
        return {"idx_mom20_prev": None, "idx_vol20_prev": None}


def _daily_context_from_kis(client: Any, code: str, *, trade_date: str, index_context: Mapping[str, Any]) -> Dict[str, Any]:
    end = pd.to_datetime(str(trade_date), format="%Y%m%d", errors="coerce")
    start = (end - pd.Timedelta(days=420)).strftime("%Y%m%d") if pd.notna(end) else (datetime.now() - timedelta(days=420)).strftime("%Y%m%d")
    try:
        payload = client.daily_bars(code, start_date=start, end_date=trade_date, period="D", adjusted=True)
        frame = normalize_kis_daily_bars(code, payload if isinstance(payload, Mapping) else {})
        return compute_daily_prev_context(frame, trade_date=trade_date, index_context=index_context)
    except Exception:
        return {}


def _minute_hours(entry_input_hour: str) -> List[str]:
    base = [entry_input_hour, "143000", "133000", "113000", "100000"]
    out = []
    for item in base:
        text = str(item or "").zfill(6)[:6]
        if text not in out:
            out.append(text)
    return out


def _fetch_minute_frame(client: Any, code: str, *, trade_date: str, entry_input_hour: str, sleep_sec: float) -> pd.DataFrame:
    today = _now_kst().strftime("%Y%m%d")
    parts = []
    for hour in _minute_hours(entry_input_hour):
        try:
            if str(trade_date) == today and hasattr(client, "today_minute_bars"):
                payload = client.today_minute_bars(code, input_hour=hour, include_past=True)
            else:
                payload = client.daily_minute_bars(code, trade_date=trade_date, input_hour=hour, include_past=True)
            frame = normalize_kis_minute_bars(code, payload if isinstance(payload, Mapping) else {}, trade_date=trade_date)
            if not frame.empty:
                parts.append(frame)
        except Exception:
            pass
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out


def score_live_candidates(
    *,
    client: Any,
    model_bundle: Mapping[str, Any],
    trade_date: str,
    min_liq_eok: float,
    tradeability_floor_eok: float,
    max_symbols: int,
    entry_input_hour: str,
    daily_context_source: str,
    sleep_sec: float,
) -> Dict[str, Any]:
    px = _load_px_cache()
    codes = _load_universe(px, min_liq_eok=min_liq_eok, max_symbols=max_symbols)
    cache_max_date = px["date"].max().strftime("%Y-%m-%d") if not px.empty else None
    idx_context = _fdr_index_context(trade_date)
    if idx_context.get("idx_mom20_prev") is None:
        idx_context = _cache_index_context(px, trade_date=trade_date)

    feature_rows: List[Dict[str, Any]] = []
    diagnostics = {"universe": len(codes), "daily_context_ok": 0, "minute_ok": 0, "feature_ok": 0}
    for code in codes:
        cache_ctx = _cache_daily_context(px, code, trade_date=trade_date)
        daily_ctx = {}
        if daily_context_source.lower() == "kis":
            daily_ctx = _daily_context_from_kis(client, code, trade_date=trade_date, index_context=idx_context)
        if not daily_ctx:
            daily_ctx = dict(cache_ctx)
            daily_ctx.setdefault("idx_mom20_prev", idx_context.get("idx_mom20_prev"))
            daily_ctx.setdefault("idx_vol20_prev", idx_context.get("idx_vol20_prev"))
        if not daily_ctx or safe_float(daily_ctx.get("liq_prev_eok")) is None:
            continue
        diagnostics["daily_context_ok"] += 1
        if safe_float(daily_ctx.get("liq_prev_eok")) < min_liq_eok:
            continue
        minute = _fetch_minute_frame(client, code, trade_date=trade_date, entry_input_hour=entry_input_hour, sleep_sec=sleep_sec)
        if minute.empty:
            continue
        diagnostics["minute_ok"] += 1
        row = build_feature_row(code=code, daily_context=daily_ctx, minute_bars=minute, trade_date=trade_date)
        if not row:
            continue
        diagnostics["feature_ok"] += 1
        feature_rows.append(row)

    scored = score_feature_rows(feature_rows, model_bundle)
    selected = select_vwap_guard_candidates(
        scored,
        min_probability=float((model_bundle.get("selection_policy") or {}).get("min_calibrated_probability") or 0.80),
        min_pre_vwap_dist_pct=float(((model_bundle.get("selection_policy") or {}).get("entry_quality_guard") or {}).get("pre_vwap_dist_pct_min") or 0.0),
        min_liq_eok=min_liq_eok,
        tradeability_floor_eok=tradeability_floor_eok,
        top_n=int((model_bundle.get("selection_policy") or {}).get("max_picks_per_day") or 2),
    )
    run_id = "KQ-ITD-3D-T5-" + str(trade_date)
    picks = [live_pick_payload(row, rank=i, trade_date=trade_date, run_id=run_id) for i, row in enumerate(selected, start=1)]
    return {
        "trade_date": trade_date,
        "run_id": run_id,
        "cache_max_date": cache_max_date,
        "daily_context_source": daily_context_source,
        "index_context": idx_context,
        "diagnostics": diagnostics,
        "scored_rows": len(scored),
        "picks": picks,
    }


def _ledger_rows() -> List[Dict[str, Any]]:
    if not LEDGER.exists():
        return []
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except Exception:
            continue
    return rows


def _write_ledger_rows(rows: Iterable[Mapping[str, Any]]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    clean = [dict(row) for row in rows if isinstance(row, Mapping)]
    LEDGER.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in clean) + ("\n" if clean else ""), encoding="utf-8")


def record_picks(picks: Iterable[Mapping[str, Any]], *, generated_at: str) -> int:
    existing = _ledger_rows()
    incoming = []
    keys = set()
    for pick in picks:
        item = {
            "date": _iso_trade_date(str(pick.get("base_trade_date") or "")),
            "trade_date": pick.get("base_trade_date"),
            "candidate_id": CANDIDATE_ID,
            "touch3d_t5": None,
            "ret3d": None,
            "mfe3": None,
            "mae3": None,
            "resolved_at": None,
            "generated_at": generated_at,
            **dict(pick),
        }
        key = (item.get("trade_date"), item.get("ticker"), item.get("candidate_id"))
        keys.add(key)
        incoming.append(item)
    kept = [row for row in existing if (row.get("trade_date"), row.get("ticker"), row.get("candidate_id")) not in keys]
    _write_ledger_rows([*kept, *incoming])
    return len(incoming)


def resolve_pending(client: Any, *, today_trade_date: str) -> Dict[str, Any]:
    rows = _ledger_rows()
    if not rows:
        return {"resolved": 0, "touch3d_t5_pct": None, "ret3d_avg": None, "mfe3_avg": None, "mae3_avg": None}
    changed = False
    for row in rows:
        need3 = row.get("touch3d_t5") is None
        need5 = row.get("exit_t5_h5") is None
        if not need3 and not need5:
            continue
        trade_date = str(row.get("trade_date") or "").replace("-", "")
        entry = safe_float(row.get("ordered_entry_price") or row.get("entry_reference_price"))
        if not trade_date or entry is None or entry <= 0:
            continue
        try:
            age = (pd.to_datetime(today_trade_date, format="%Y%m%d") - pd.to_datetime(trade_date, format="%Y%m%d")).days
        except Exception:
            continue
        if (not need3 or age < 5) and (not need5 or age < 9):
            continue
        code = normalize_kr_code(row.get("ticker"))
        try:
            payload = client.daily_bars(code, start_date=trade_date, end_date=today_trade_date, period="D", adjusted=True)
            frame = normalize_kis_daily_bars(code, payload if isinstance(payload, Mapping) else {})
            frame.index = pd.to_datetime(frame.index)
            future_all = frame[frame.index.normalize() > pd.to_datetime(trade_date, format="%Y%m%d").normalize()]
            future = future_all.head(3)
            if need3 and age >= 5 and len(future) >= 3:
                highs = pd.to_numeric(future["High"], errors="coerce")
                lows = pd.to_numeric(future["Low"], errors="coerce")
                closes = pd.to_numeric(future["Close"], errors="coerce")
                mfe = float((highs.max() / entry - 1) * 100)
                mae = float((lows.min() / entry - 1) * 100)
                ret3 = float((closes.iloc[-1] / entry - 1) * 100)
                row["touch3d_t5"] = int(mfe >= 5.0)
                row["mfe3"] = round(mfe, 4)
                row["mae3"] = round(mae, 4)
                row["ret3d"] = round(ret3, 4)
                row["resolved_at"] = datetime.now(timezone.utc).isoformat()
                changed = True
            # observation-only exit-policy shadow (swing-main-ayu1): sell-at-touch limit
            # (gap-up fills at open) else 5d close hold. Never changes picks or contract.
            if need5 and age >= 9:
                f5 = future_all.head(5)
                if len(f5) >= 5:
                    op5 = pd.to_numeric(f5["Open"], errors="coerce")
                    hi5 = pd.to_numeric(f5["High"], errors="coerce")
                    cl5 = pd.to_numeric(f5["Close"], errors="coerce")
                    ret5 = float((cl5.iloc[-1] / entry - 1) * 100)
                    row["ret5d"] = round(ret5, 4)
                    for tp, key in ((5.0, "exit_t5_h5"), (10.0, "exit_t10_h5")):
                        tgt = entry * (1 + tp / 100.0)
                        r5 = ret5
                        for k in range(5):
                            if pd.notna(hi5.iloc[k]) and float(hi5.iloc[k]) >= tgt:
                                o = op5.iloc[k]
                                fill = max(tgt, float(o)) if pd.notna(o) and float(o) > 0 else tgt
                                r5 = (fill / entry - 1) * 100
                                break
                        row[key] = round(float(r5), 4)
                    changed = True
        except Exception:
            continue
    if changed:
        _write_ledger_rows(rows)
    resolved = [row for row in rows if row.get("touch3d_t5") is not None]
    if not resolved:
        return {"resolved": 0, "touch3d_t5_pct": None, "ret3d_avg": None, "mfe3_avg": None, "mae3_avg": None}
    out = {
        "resolved": len(resolved),
        "touch3d_t5_pct": round(float(np.mean([row["touch3d_t5"] for row in resolved]) * 100), 2),
        "ret3d_avg": round(float(np.mean([row["ret3d"] for row in resolved])), 4),
        "mfe3_avg": round(float(np.mean([row["mfe3"] for row in resolved])), 4),
        "mae3_avg": round(float(np.mean([row["mae3"] for row in resolved])), 4),
    }
    res5 = [row for row in rows if row.get("exit_t5_h5") is not None]
    if res5:
        out["exit_shadow"] = {
            "n": len(res5),
            "exit_t5_h5_avg": round(float(np.mean([row["exit_t5_h5"] for row in res5])), 4),
            "exit_t10_h5_avg": round(float(np.mean([row["exit_t10_h5"] for row in res5])), 4),
            "ret5d_avg": round(float(np.mean([row["ret5d"] for row in res5])), 4),
            "win_t10_pct": round(float(np.mean([1 if row["exit_t10_h5"] > 0.3 else 0 for row in res5]) * 100), 1),
        }
    return out


def route_live_intraday(picks: List[Dict[str, Any]], *, run_id: str, recommended_at: str) -> int:
    from modules.candidate_interpretation import build_candidate_interpretation
    from modules.db_manager import DBManager
    from modules.db_schema import build_scan_result_payload
    from modules.top_deep_report import upsert_reports_to_supabase

    db = DBManager()
    ordered = sorted(picks, key=lambda row: -float(row.get("p") or 0.0))
    written = 0
    for rank, pick in enumerate(ordered, start=1):
        src = {
            **pick,
            "run_id": run_id,
            "priority_rank": rank,
            "market_type": "KOSDAQ",
            "scan_mode": "INTRADAY",
            "recommended_at": recommended_at,
            "horizon": "3D",
            "scanner_timeframe_profile": "INTRADAY_1500",
            "feature_snapshot": {
                "candidate_id": CANDIDATE_ID,
                "entry_time_kst": "15:00",
                "pre_vwap_dist_pct": pick.get("pre_vwap_dist_pct"),
                "liquidity_lane": pick.get("liquidity_lane"),
                "tradeability_floor_pass": pick.get("tradeability_floor_pass"),
            },
        }
        payload = build_scan_result_payload(
            src,
            overrides={
                "market": "KOSDAQ",
                "recommended_at": recommended_at,
                "feature_origin": "kosdaq_intraday_1500_vwap_guard",
                "created_at": recommended_at,
            },
        )
        payload["allow_incomplete_scan_result"] = True
        db.upsert_scan_result(payload)
        written += 1

    deep_rows = []
    for rank, pick in enumerate(ordered, start=1):
        row = {
            "report_id": f"{run_id}-{pick['ticker']}",
            "report_version": 1,
            "ticker": pick["ticker"],
            "stock_name": pick["ticker"],
            "market": "KOSDAQ",
            "run_id": run_id,
            "scan_mode": "INTRADAY",
            "strategy_family": STRATEGY_FAMILY,
            "rank": rank,
            "decision": pick["decision"],
            "decision_bucket": pick["decision_bucket"],
            "signal_label": pick["decision"],
            "analysis_section": "Top5",
            "analysis_section_rank": rank,
            "buy_score": pick["p"],
            "generated_at": recommended_at,
            "entry_reference_price": pick.get("entry_reference_price"),
            "selection_alignment": {"analysis_section": "Top5", "analysis_section_rank": rank},
        }
        row["candidate_interpretation"] = build_candidate_interpretation(row)
        deep_rows.append(row)
    if deep_rows:
        upsert_reports_to_supabase(deep_rows)
    return written


def _write_report(report: Mapping[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        f"# KOSDAQ intraday 15:00 VWAP guard - {_iso_trade_date(str(report.get('trade_date') or ''))}",
        "",
        f"- candidate: `{CANDIDATE_ID}`",
        f"- production_enabled: `{report.get('production_enabled')}` | routed: `{report.get('routed')}`",
        f"- scored_rows: `{report.get('scored_rows')}` | picks: `{len(report.get('picks') or [])}`",
        f"- forward: `{report.get('forward_summary')}`",
        "",
        "| Rank | Ticker | p_cal | liq lane | ADV(억) | VWAP dist | Entry |",
        "|---:|---|---:|---|---:|---:|---:|",
    ]
    for pick in report.get("picks") or []:
        lines.append(
            f"| {pick.get('priority_rank')} | {pick.get('ticker')} | {float(pick.get('p') or 0):.3f} | "
            f"{pick.get('liquidity_lane')} | {float(pick.get('liq_prev_eok') or 0):.1f} | "
            f"{float(pick.get('pre_vwap_dist_pct') or 0):.2f}% | {float(pick.get('entry_reference_price') or 0):.2f} |"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Live KOSDAQ 15:00 intraday VWAP-guard scorer.")
    parser.add_argument("--trade-date", default="")
    parser.add_argument("--min-liq", type=float, default=30.0)
    parser.add_argument("--tradeability-liq", type=float, default=100.0)
    parser.add_argument("--max-symbols", type=int, default=int(os.getenv("AG_KOSDAQ_INTRADAY_MAX_SYMBOLS", "0") or 0))
    parser.add_argument("--entry-input-hour", default=ENTRY_INPUT_HOUR)
    parser.add_argument("--daily-context-source", choices=["cache", "kis"], default=os.getenv("AG_KOSDAQ_INTRADAY_DAILY_CONTEXT_SOURCE", "cache"))
    parser.add_argument("--sleep-sec", type=float, default=float(os.getenv("AG_KOSDAQ_INTRADAY_SLEEP_SEC", "0.03") or 0.03))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    trade_date = _trade_date_arg(args.trade_date)
    generated_at = datetime.now(timezone.utc).isoformat()
    model_bundle = joblib.load(PROJECT_ROOT / MODEL_PATH)

    from modules.kis_openapi import KISConfig, KISOpenAPIClient

    client = KISOpenAPIClient(KISConfig.from_env())
    client.get_access_token()

    score_result: Dict[str, Any]
    try:
        score_result = score_live_candidates(
            client=client,
            model_bundle=model_bundle,
            trade_date=trade_date,
            min_liq_eok=args.min_liq,
            tradeability_floor_eok=args.tradeability_liq,
            max_symbols=args.max_symbols,
            entry_input_hour=args.entry_input_hour,
            daily_context_source=args.daily_context_source,
            sleep_sec=args.sleep_sec,
        )
    except Exception as exc:
        report = {
            "generated_at": generated_at,
            "trade_date": trade_date,
            "candidate_id": CANDIDATE_ID,
            "error": repr(exc)[:500],
            "production_enabled": False,
            "routed": 0,
            "picks": [],
        }
        _write_report(report)
        print(json.dumps({"error": repr(exc)[:200]}, ensure_ascii=False))
        return 1

    picks = list(score_result.get("picks") or [])
    recorded = record_picks(picks, generated_at=generated_at)
    forward_summary = resolve_pending(client, today_trade_date=trade_date)
    production = os.getenv("AG_KOSDAQ_INTRADAY_PRODUCTION", "1").strip() not in {"0", "", "false", "False"}
    if args.dry_run:
        production = False
    routed = 0
    if production and picks:
        try:
            routed = route_live_intraday(picks, run_id=str(score_result.get("run_id") or ""), recommended_at=generated_at)
        except Exception as exc:
            routed = -1
            print(json.dumps({"route_error": repr(exc)[:240]}, ensure_ascii=False))

    report = {
        "generated_at": generated_at,
        "candidate_id": CANDIDATE_ID,
        "strategy_family": STRATEGY_FAMILY,
        "target": TARGET_COLUMN,
        "roundtrip_cost_pct": ROUNDTRIP_COST_PCT,
        "production_enabled": production,
        "routed": routed,
        "ledger_recorded": recorded,
        "forward_summary": forward_summary,
        **score_result,
    }
    _write_report(report)
    print(
        json.dumps(
            {
                "trade_date": trade_date,
                "picks": len(picks),
                "routed": routed,
                "production": production,
                "forward": forward_summary,
                "diagnostics": score_result.get("diagnostics"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

