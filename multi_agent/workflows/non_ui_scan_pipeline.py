from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules import quant_analysis
from modules.live_scan_context import live_mode_enabled, normalize_market_key
from modules.macro_scheduler import get_macro_context
from modules.scan_integrity import write_scan_integrity_artifacts
from modules.scan_policy import compute_market_gate, compute_rank_adjustment
from modules.scanner_runtime import SharedBackoffState, run_parallel_scan, scan_symbol_with_retry
from modules.scanner_services import resolve_strategy_family, resolve_us_hard_filter_gate, resolve_us_signal_window_gate
from multi_agent.agents.orchestrator import OrchestratorAgent
from multi_agent.config.scan_profiles import apply_scan_gate_profile
from multi_agent.contracts.serialization import read_json, write_json
from multi_agent.contracts.types import RunContext
from multi_agent.storage.memory_layers import MemoryManager


def _attach_shared_working_artifacts(manifest_paths: Dict[str, Any]) -> Dict[str, Any]:
    run_dir = Path(str(manifest_paths.get("shared_working_dir", "") or ""))
    if not run_dir.exists():
        return manifest_paths
    for name in [
        "scanner_handoff",
        "aggregation_handoff",
        "backtest_handoff",
        "market_context_handoff",
        "planner_handoff",
        "profile_diagnostics",
        "postmortem_report",
        "realized_outcomes",
        "orchestrator_request",
        "orchestrator_report",
        "orchestrator_compact_summary",
    ]:
        if manifest_paths.get(name):
            continue
        path = run_dir / f"{name}.json"
        if path.exists():
            manifest_paths[name] = str(path)
    return manifest_paths


def _generate_top_deep_reports_for_run(
    *,
    results: List[Dict[str, Any]],
    manifest_paths: Dict[str, Any],
    run_id: str,
    market: str,
    scan_mode: str,
) -> Dict[str, Any]:
    if not results:
        return {"count": 0, "reason": "no_scan_results"}
    planner_path = Path(str(manifest_paths.get("planner_handoff") or ""))
    if not planner_path.exists():
        return {"count": 0, "reason": "planner_handoff_missing"}
    try:
        from modules.top_deep_report import generate_and_store_top_deep_reports
        from modules.ui_helpers import merge_profile_exception_leaders_into_planner

        planner_payload = read_json(planner_path)
        profile_path = Path(str(manifest_paths.get("profile_diagnostics") or ""))
        profile_payload = read_json(profile_path) if profile_path.exists() else {}
        planner_payload = merge_profile_exception_leaders_into_planner(planner_payload, profile_payload)
        top_n = max(1, int(os.getenv("AG_TOP_DEEP_N", "5") or 5))
        write_db = os.getenv("AG_TOP_DEEP_WRITE_DB", "1").strip() not in {"0", "false", "False"}
        return generate_and_store_top_deep_reports(
            scan_rows=results,
            planner_payload=planner_payload,
            run_id=run_id,
            market=market,
            scan_mode=str(scan_mode or "SWING").upper(),
            top_n=top_n,
            write_db=write_db,
        )
    except Exception as exc:
        return {"count": 0, "error": str(exc)}


def _parse_ticker_list(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [token.strip() for token in str(raw).split(",") if token.strip()]


def _resolve_ticker_map(market: str, tickers_raw: str | None) -> Dict[str, str]:
    manual = _parse_ticker_list(tickers_raw)
    if manual:
        return {ticker: ticker for ticker in manual}
    return quant_analysis.QuantStrategy.get_market_tickers(market) or {}


def _to_float(value: Any, default: float = -9999.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _fallback_news_adjustment(_stock_name: str, _ticker: str, _sector_hint: str, _intel_data: Any) -> Dict[str, Any]:
    return {
        "score_adjustment": 0,
        "reason": "market_intelligence_unavailable",
        "is_beneficiary": False,
        "is_victim": False,
    }


def _resolve_market_intel(
    market: str,
) -> tuple[Any, Callable[[str, str, str, Any], Dict[str, Any]]]:
    try:
        from modules import market_intelligence as mi

        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        intel = mi.get_market_intelligence(market, gemini_key, force_refresh=True)
        return intel, mi.calculate_news_adjustment
    except Exception:
        return {"source": "fallback", "key_insight": "market_intelligence import failed"}, _fallback_news_adjustment


def _write_market_intel_snapshot(memory: MemoryManager, run_id: str, market: str, intel_data: Any) -> None:
    if not isinstance(intel_data, dict):
        return
    try:
        write_json(
            memory.shared_working(run_id) / "market_intelligence_snapshot.json",
            {
                "run_id": run_id,
                "market": market,
                "generated_at": intel_data.get("timestamp"),
                "intel_data": intel_data,
            },
        )
    except Exception:
        pass


def _build_run_warnings(
    *,
    total_scans: int,
    result_count: int,
    filtered_count: int,
    worker_error_count: int,
    reject_reason_counts: Dict[str, int],
    regime: Dict[str, Any],
    macro_ctx: Dict[str, Any],
    market_gate: Dict[str, Any],
) -> List[Dict[str, str]]:
    warnings: List[Dict[str, str]] = []

    if total_scans > 0 and result_count == 0 and filtered_count == total_scans:
        top_reason = ""
        if reject_reason_counts:
            top = sorted(reject_reason_counts.items(), key=lambda x: x[1], reverse=True)[0]
            top_reason = f" Top reject reason: {top[0]} ({top[1]})."
        warnings.append(
            {
                "code": "ZERO_RESULT_ALL_FILTERED",
                "severity": "warning",
                "message": f"All scanned symbols were filtered out. Check thresholds, data quality, and market regime.{top_reason}",
            }
        )

    if worker_error_count > 0:
        warnings.append(
            {
                "code": "SCAN_WORKER_ERRORS",
                "severity": "warning",
                "message": f"Worker reported {worker_error_count} errors during scan execution.",
            }
        )

    regime_error = str(regime.get("desc", "")).strip().lower() == "error"
    macro_unavailable = (
        macro_ctx.get("vix") is None
        and macro_ctx.get("tnx") is None
        and macro_ctx.get("krw") is None
    )
    gate_msg = str(market_gate.get("msg", ""))
    gate_failed = "실패" in gate_msg or "failure" in gate_msg.lower() or "error" in gate_msg.lower()
    if regime_error and macro_unavailable and gate_failed:
        warnings.append(
            {
                "code": "NETWORK_OR_DATA_SOURCE_UNAVAILABLE",
                "severity": "high",
                "message": "Regime/macro/market gate fetches appear unavailable. Validate external data/network connectivity.",
            }
        )

    return warnings


def run_non_ui_scan_pipeline(
    *,
    market: str,
    profile: str,
    max_scan: int,
    max_workers: int,
    is_advanced_engine: bool,
    max_retries: int,
    tickers: str | None,
    force_macro_refresh: bool,
    strategy_version: str,
    model_version: str,
    code_version: str,
    scan_mode: str = "SWING",
) -> Dict[str, Any]:
    resolved_profile, applied_profile_defaults = apply_scan_gate_profile(profile)
    run_id = f"RUN-{uuid4().hex[:8].upper()}"
    context = RunContext(
        run_id=run_id,
        as_of_date=str(date.today()),
        market=market,
        strategy_version=strategy_version,
        model_version=model_version,
        code_version=code_version,
    )
    memory = MemoryManager()

    ticker_map = _resolve_ticker_map(market=market, tickers_raw=tickers)
    ticker_list = list(ticker_map.keys())
    if not ticker_list and max_scan > 0:
        raise RuntimeError(f"No tickers available for market={market}.")

    regime = quant_analysis.QuantStrategy.detect_market_regime(market)
    regime_status = str(regime.get("regime", "NEUTRAL"))

    try:
        macro_ctx = get_macro_context(
            force_refresh=force_macro_refresh or live_mode_enabled(market),
            market_group=normalize_market_key(market),
        )
    except Exception:
        macro_ctx = {"macro_state": "NORMAL", "macro_risk_score": 0, "macro_penalty": 0}

    market_gate = compute_market_gate(market)
    intel_data, news_adjustment_fn = _resolve_market_intel(market)
    _write_market_intel_snapshot(memory, run_id, market, intel_data)

    is_us = market in ["NASDAQ", "S&P500", "AMEX"]
    is_amex = market == "AMEX"
    gate_config = {
        "us_signal_window": resolve_us_signal_window_gate() if is_us else None,
        "us_hard_filter": resolve_us_hard_filter_gate() if is_us else None,
    }
    strategy_family = resolve_strategy_family("AMEX" if is_amex else ("US" if is_us else market), is_amex=is_amex)
    backoff_state = SharedBackoffState()
    diag_lock = threading.Lock()
    diagnostics: Dict[str, Any] = {
        "filtered_count": 0,
        "worker_error_count": 0,
        "executor_exception_count": 0,
        "filtered_symbols": [],
        "error_symbols": [],
        "exception_symbols": [],
        "reject_reason_counts": {},
        "reject_reasons_by_symbol": {},
        "reject_details_by_symbol": {},
    }

    def on_reject(sym: str, reason: str) -> None:
        with diag_lock:
            counts = diagnostics.setdefault("reject_reason_counts", {})
            counts[reason] = int(counts.get(reason, 0) or 0) + 1
            by_symbol = diagnostics.setdefault("reject_reasons_by_symbol", {})
            by_symbol[sym] = reason

    def on_reject_detail(sym: str, meta: Dict[str, Any]) -> None:
        with diag_lock:
            details = diagnostics.setdefault("reject_details_by_symbol", {})
            if not isinstance(details.get(sym), list):
                details[sym] = []
            if isinstance(meta, dict):
                details[sym].append(meta)

    def worker(sym: str) -> Dict[str, Any] | None:
        return scan_symbol_with_retry(
            sym=sym,
            tickers_dict=ticker_map,
            is_us=is_us,
            is_amex=is_amex,
            is_advanced_engine=is_advanced_engine,
            r_status=regime_status,
            intel_data=intel_data,
            macro_ctx=macro_ctx,
            market_gate=market_gate,
            rank_adjustment_fn=compute_rank_adjustment,
            news_adjustment_fn=news_adjustment_fn,
            backoff_state=backoff_state,
            max_retries=max_retries,
            scan_mode=str(scan_mode or "SWING").upper(),
            run_id=run_id,
            reject_reason_fn=on_reject,
            reject_detail_fn=on_reject_detail,
        )

    def on_item(i: int, total: int, sym: str, data: Dict[str, Any] | None, exc: Exception | None) -> None:
        if exc is not None:
            diagnostics["executor_exception_count"] += 1
            diagnostics["exception_symbols"].append(sym)
            print(f"[{i+1}/{total}] {sym}: ERROR {exc}")
            return
        if data is None:
            diagnostics["filtered_count"] += 1
            diagnostics["filtered_symbols"].append(sym)
            print(f"[{i+1}/{total}] {sym}: filtered")
            return
        if "error" in data:
            diagnostics["worker_error_count"] += 1
            diagnostics["error_symbols"].append(sym)
            print(f"[{i+1}/{total}] {sym}: worker_error")
            return
        print(f"[{i+1}/{total}] {sym}: pass")

    scan_result = run_parallel_scan(
        ticker_list=ticker_list,
        max_scan=max_scan,
        worker_fn=worker,
        max_workers=max_workers,
        on_item=on_item,
    )
    results = list(scan_result.get("results", []) or [])
    results = sorted(
        results,
        key=lambda row: (
            _to_float(row.get("Decision Score")),
            _to_float(row.get("Antigrav")),
        ),
        reverse=True,
    )
    total_scans = int(scan_result.get("total_scans", 0) or 0)
    run_warnings = _build_run_warnings(
        total_scans=total_scans,
        result_count=len(results),
        filtered_count=int(diagnostics.get("filtered_count", 0) or 0),
        worker_error_count=int(diagnostics.get("worker_error_count", 0) or 0)
        + int(diagnostics.get("executor_exception_count", 0) or 0),
        reject_reason_counts=diagnostics.get("reject_reason_counts", {}),
        regime=regime,
        macro_ctx=macro_ctx,
        market_gate=market_gate,
    )

    local_input_dir = memory.local_short_term("scanner_agent", run_id)
    scanner_input_path = local_input_dir / "legacy_scan_results.json"
    write_json(
        scanner_input_path,
        {
            "results": results,
            "meta": {
                "market": market,
                "regime": regime,
                "macro_ctx": macro_ctx,
                "market_gate": market_gate,
                "total_scans": total_scans,
                "error_count": int(scan_result.get("error_count", 0) or 0),
                "diagnostics": diagnostics,
                "gate_config": gate_config,
                "execution_profile": resolved_profile,
                "applied_profile_defaults": applied_profile_defaults,
                "scan_mode": str(scan_mode or "SWING").upper(),
                "strategy_family": strategy_family,
                "warnings": run_warnings,
            },
        },
    )

    orchestrator = OrchestratorAgent(
        user_request=f"Run full non-UI scan pipeline for {market} and produce planner-ready outputs.",
        market=market,
        strategy_version=strategy_version,
        model_version=model_version,
        code_version=code_version,
        scanner_input_path=str(scanner_input_path),
    )
    report_path = orchestrator.run(context=context, memory=memory)
    manifest_paths = dict(orchestrator.last_execution or {})
    manifest_paths["orchestrator_report"] = str(report_path)
    manifest_paths = _attach_shared_working_artifacts(manifest_paths)

    try:
        from multi_agent.workflows.legacy_orchestration import run_legacy_orchestration

        extra_paths = run_legacy_orchestration(str(manifest_paths.get("scanner_handoff") or scanner_input_path))
        if isinstance(extra_paths, dict):
            manifest_paths.update(extra_paths)
            manifest_paths = _attach_shared_working_artifacts(manifest_paths)
    except Exception as exc:
        manifest_paths["downstream_diagnostics_error"] = str(exc)

    top_deep_reports = _generate_top_deep_reports_for_run(
        results=results,
        manifest_paths=manifest_paths,
        run_id=run_id,
        market=market,
        scan_mode=str(scan_mode or "SWING").upper(),
    )
    if isinstance(top_deep_reports, dict) and top_deep_reports.get("local_path"):
        manifest_paths["top_deep_reports"] = str(top_deep_reports.get("local_path"))

    artifact_dir = memory.artifact_store(run_id)
    raw_json_path = artifact_dir / "raw_scan_results.json"
    write_json(
        raw_json_path,
        {
            "run_context": context.to_dict(),
            "scan_result": scan_result,
            "results_sorted": results,
            "diagnostics": diagnostics,
            "gate_config": gate_config,
            "execution_profile": resolved_profile,
            "applied_profile_defaults": applied_profile_defaults,
            "scan_mode": str(scan_mode or "SWING").upper(),
            "strategy_family": strategy_family,
            "warnings": run_warnings,
        },
    )
    try:
        import pandas as pd

        pd.DataFrame(results).to_csv(artifact_dir / "raw_scan_results.csv", index=False)
    except Exception:
        pass

    summary = {
        "run_id": run_id,
        "market": market,
        "result_count": len(results),
        "total_scans": int(scan_result.get("total_scans", 0) or 0),
        "error_count": int(scan_result.get("error_count", 0) or 0),
        "filtered_count": int(diagnostics.get("filtered_count", 0) or 0),
        "worker_error_count": int(diagnostics.get("worker_error_count", 0) or 0),
        "executor_exception_count": int(diagnostics.get("executor_exception_count", 0) or 0),
        "reject_reason_counts": diagnostics.get("reject_reason_counts", {}),
        "gate_config": gate_config,
        "execution_profile": resolved_profile,
        "applied_profile_defaults": applied_profile_defaults,
        "scan_mode": str(scan_mode or "SWING").upper(),
        "strategy_family": strategy_family,
        "warnings": run_warnings,
        "scanner_input_path": str(scanner_input_path),
        "manifest_paths": manifest_paths,
        "artifact_dir": str(artifact_dir),
        "top_deep_reports": top_deep_reports,
    }
    integrity_result = write_scan_integrity_artifacts(
        artifact_dir=artifact_dir,
        run_id=run_id,
        market=market,
        scan_mode=str(scan_mode or "SWING").upper(),
        results=results,
        total_scans=int(scan_result.get("total_scans", 0) or 0),
        diagnostics=diagnostics,
        bridge_info=manifest_paths,
        top_deep_reports=top_deep_reports,
        created_at=str(context.created_at),
    )
    if integrity_result.get("observed_factor_snapshots"):
        manifest_paths["observed_factor_snapshots"] = str(integrity_result.get("observed_factor_snapshots"))
    if integrity_result.get("scan_integrity_report"):
        manifest_paths["scan_integrity_report"] = str(integrity_result.get("scan_integrity_report"))
    summary["scan_integrity"] = integrity_result
    emit_daily_summary = os.getenv("AG_EMIT_DAILY_SUMMARY", "1").strip() not in {"0", "false", "False"}
    if emit_daily_summary:
        try:
            from multi_agent.workflows.daily_summary import build_daily_summary, write_daily_summary

            target_date = str(date.today())
            daily_summary = build_daily_summary(
                shared_dir=memory.root / "shared_working",
                target_date=target_date,
                market=market,
                limit_runs=0,
            )
            daily_paths = write_daily_summary(
                summary=daily_summary,
                output_dir=memory.root / "reports" / "daily",
                target_date=target_date,
            )
            summary["daily_summary_paths"] = daily_paths
        except Exception as e:
            summary["daily_summary_error"] = str(e)
    emit_stale_alert = os.getenv("AG_STALE_FALLBACK_ALERT_ENABLE", "1").strip() not in {"0", "false", "False"}
    if emit_stale_alert:
        try:
            from multi_agent.workflows.alerts import emit_stale_fallback_alert

            stale_alert = emit_stale_fallback_alert(
                shared_dir=memory.root / "shared_working",
                market=market,
                min_stale_count=int(os.getenv("AG_STALE_FALLBACK_ALERT_MIN", "3") or 3),
                webhook_url=str(os.getenv("AG_STALE_FALLBACK_ALERT_WEBHOOK_URL", "") or ""),
                limit_runs=int(os.getenv("AG_STALE_FALLBACK_ALERT_LIMIT_RUNS", "200") or 200),
                dry_run=os.getenv("AG_STALE_FALLBACK_ALERT_DRY_RUN", "0").strip() in {"1", "true", "True"},
            )
            summary["stale_fallback_alert"] = stale_alert
        except Exception as e:
            summary["stale_fallback_alert_error"] = str(e)
    write_json(artifact_dir / "scan_pipeline_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run non-UI scanner and route outputs into 5-agent trace pipeline.")
    parser.add_argument("--market", type=str, default="KOSPI", choices=["KOSPI", "KOSDAQ", "NASDAQ", "S&P500", "AMEX"])
    parser.add_argument(
        "--profile",
        type=str,
        default=os.getenv("AG_SCAN_PROFILE", "prod"),
        choices=["prod", "dev"],
        help="Execution profile for scan gate defaults. Explicit env vars still take priority.",
    )
    parser.add_argument("--max-scan", type=int, default=0)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--tickers", type=str, default=None, help="Comma-separated tickers. If set, market universe fetch is skipped.")
    parser.add_argument("--advanced-engine", action="store_true")
    parser.add_argument("--force-macro-refresh", action="store_true")
    parser.add_argument("--strategy-version", type=str, default="legacy-cli-v1")
    parser.add_argument("--model-version", type=str, default="legacy")
    parser.add_argument("--code-version", type=str, default="non-ui-scan-v1")
    parser.add_argument("--scan-mode", type=str, default="SWING", choices=["SWING", "INTRADAY"])
    args = parser.parse_args()

    summary = run_non_ui_scan_pipeline(
        market=args.market,
        profile=str(args.profile),
        max_scan=max(0, int(args.max_scan)),
        max_workers=max(1, int(args.max_workers)),
        is_advanced_engine=bool(args.advanced_engine),
        max_retries=max(0, int(args.max_retries)),
        tickers=args.tickers,
        force_macro_refresh=bool(args.force_macro_refresh),
        strategy_version=str(args.strategy_version),
        model_version=str(args.model_version),
        code_version=str(args.code_version),
        scan_mode=str(args.scan_mode).upper(),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
