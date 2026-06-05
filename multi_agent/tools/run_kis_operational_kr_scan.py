#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_openapi import KISConfig, KISOpenAPIClient, build_kis_adapter_health
from modules.kis_operational_prefilter import (
    KISOperationalPrefilterConfig,
    build_kis_operational_prefilter,
    selected_ticker_arg,
    selected_ticker_symbols,
    write_kis_operational_prefilter_report,
)


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def _kst_timestamp() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S")
    except Exception:
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def _markets(raw: str) -> List[str]:
    key = str(raw or "ALL").strip().upper()
    if key == "ALL":
        return ["KOSPI", "KOSDAQ"]
    if key in {"KOSPI", "KOSDAQ"}:
        return [key]
    raise ValueError(f"Unsupported KR market: {raw}")


def _tail_lines(lines: Sequence[str], max_lines: int = 120) -> List[str]:
    return [str(line).rstrip("\n") for line in list(lines)[-max(1, int(max_lines)) :]]


def _extract_last_json_object(text: str) -> Dict[str, Any] | None:
    decoder = json.JSONDecoder()
    starts = [idx for idx, char in enumerate(text or "") if char == "{"]
    for start in reversed(starts):
        try:
            obj, _end = decoder.raw_decode(text[start:].strip())
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("run_id") and {"result_count", "total_scans"}.issubset(obj.keys()):
            return obj
        if obj.get("tool") == "run_kis_operational_kr_scan":
            return obj
    return None


def _run_streamed(command: Sequence[str], *, env: Mapping[str, str], timeout_sec: float) -> Dict[str, Any]:
    started_epoch = time.time()
    started = time.monotonic()
    proc = subprocess.Popen(
        list(command),
        cwd=str(PROJECT_ROOT),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    timed_out = False

    def _kill_on_timeout() -> None:
        nonlocal timed_out
        timed_out = True
        proc.kill()

    timer = None
    if timeout_sec and timeout_sec > 0:
        timer = threading.Timer(float(timeout_sec), _kill_on_timeout)
        timer.daemon = True
        timer.start()

    lines: List[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
            lines.append(line.rstrip("\n"))
        returncode = proc.wait()
    finally:
        if timer is not None:
            timer.cancel()

    text = "\n".join(lines)
    return {
        "returncode": int(returncode),
        "timeout": bool(timed_out),
        "started_epoch": started_epoch,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "output_tail": _tail_lines(lines),
        "summary": _extract_last_json_object(text) or {},
    }


def _load_recent_pipeline_summary(*, market: str, started_epoch: float) -> Dict[str, Any]:
    candidates: List[tuple[float, Path]] = []
    for path in (PROJECT_ROOT / "runtime_state" / "artifacts").glob("RUN-*/scan_pipeline_summary.json"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if started_epoch and mtime < float(started_epoch) - 30.0:
            continue
        candidates.append((mtime, path))
    for _mtime, path in sorted(candidates, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("market") or "").upper() != str(market or "").upper():
            continue
        if payload.get("run_id"):
            return payload
    return {}


def _scan_env(args: argparse.Namespace) -> Dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "PYTHONUNBUFFERED": "1",
            "KIS_ENABLE_LIVE_CALLS": "1",
            "AG_KR_MARKET_DATA_PROVIDER": "kis_only",
            "AG_ENABLE_KIS_MARKET_DATA": "1",
            "AG_ENABLE_KIS_SIDECAR": "1" if args.enable_sidecar else "0",
            "AG_KIS_SIDECAR_FETCH_QUOTE": "1" if args.enable_sidecar_quote else "0",
            "AG_KIS_SIDECAR_FETCH_DAILY": "0",
            "AG_KIS_SIDECAR_FETCH_MINUTE": "0",
            "AG_KIS_SIDECAR_FETCH_FLOW": "1" if args.enable_sidecar_flow else "0",
            "AG_KIS_SIDECAR_FETCH_RANK": "1" if args.enable_sidecar_rank else "0",
            "AG_KIS_SIDECAR_FETCH_VI": "1" if args.enable_sidecar_vi else "0",
            "AG_KIS_SIDECAR_FETCH_NEWS": "1" if args.enable_sidecar_news else "0",
            "AG_KIS_SIDECAR_FETCH_STOCK_INFO": "1" if args.enable_sidecar_stock_info else "0",
            "AG_KIS_SIDECAR_FETCH_FINANCIAL": "1" if args.enable_sidecar_financial else "0",
            "KIS_LIVE_CALL_SLEEP_SEC": str(args.kis_call_sleep_sec),
            "AG_KIS_SIDECAR_CALL_SLEEP_SEC": str(args.sidecar_call_sleep_sec),
            "AG_KIS_DAILY_MAX_CHUNKS": str(args.deep_kis_daily_max_chunks),
            "MPLCONFIGDIR": str(PROJECT_ROOT / "runtime_state" / "local_short_term" / "matplotlib_cache"),
        }
    )
    return env


def _pipeline_command(args: argparse.Namespace, *, market: str, tickers: str) -> List[str]:
    return [
        sys.executable,
        "-m",
        "multi_agent.workflows.non_ui_scan_pipeline",
        "--market",
        market,
        "--profile",
        str(args.profile),
        "--max-scan",
        str(args.max_candidates_per_market),
        "--max-workers",
        str(args.workers),
        "--max-retries",
        str(args.max_retries),
        "--scan-mode",
        str(args.scan_mode).upper(),
        "--strategy-version",
        f"kis-operational-prefilter-{str(args.scan_mode).lower()}-v1",
        "--model-version",
        "phase25-kis-prefilter",
        "--code-version",
        "kis-operational-kr-scan-v1",
        "--tickers",
        tickers,
    ]


def _write_summary(summary: Mapping[str, Any]) -> Dict[str, str]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _kst_timestamp()
    market = str(summary.get("market") or "ALL").lower()
    mode = str(summary.get("scan_mode") or "SWING").lower()
    path = REPORT_DIR / f"kis_operational_scan_{market}_{mode}_{stamp}.json"
    latest = REPORT_DIR / f"kis_operational_scan_{market}_{mode}_latest.json"
    artifacts = {"json": str(path), "latest_json": str(latest)}
    serializable = dict(summary)
    serializable["artifacts"] = artifacts
    text = json.dumps(serializable, ensure_ascii=False, indent=2, default=str) + "\n"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    return artifacts


def _env_enabled(name: str, default: str = "1") -> bool:
    return str(os.getenv(name, default) or "").strip().lower() not in {"0", "false", "no", "off"}


def _compact_prefilter_candidate(row: Mapping[str, Any]) -> Dict[str, Any]:
    quote = row.get("quote") if isinstance(row.get("quote"), Mapping) else {}
    flow = row.get("flow") if isinstance(row.get("flow"), Mapping) else {}

    quote_fields: Dict[str, Any] = {}
    for key in (
        "source_status",
        "current_price",
        "day_change_pct",
        "value_traded",
        "volume",
        "prev_volume_ratio",
        "market_cap",
        "per",
        "pbr",
        "status_warning",
    ):
        value = row.get(key)
        if value is None:
            value = quote.get(key)
        if value not in (None, ""):
            quote_fields[key] = value

    flow_fields: Dict[str, Any] = {}
    for key in (
        "flow_source",
        "source_status",
        "valid",
        "flow_unit",
        "whale_score",
        "foreigner_1d",
        "institution_1d",
        "retail_1d",
        "foreigner_3d",
        "institution_3d",
        "retail_3d",
        "foreigner_10d",
        "institution_10d",
        "retail_10d",
    ):
        value = flow.get(key)
        if value not in (None, ""):
            flow_fields[key] = value

    payload = {
        "feature_origin": "kis_openapi_prefilter",
        "is_dummy_data": False,
        "market": row.get("market"),
        "ticker": row.get("ticker"),
        "code": row.get("code"),
        "name": row.get("name"),
        "sources": list(row.get("sources") or []) if isinstance(row.get("sources"), list) else [],
        "rank": dict(row.get("rank") or {}) if isinstance(row.get("rank"), Mapping) else {},
        "selection_score": row.get("selection_score"),
        "score_components": dict(row.get("score_components") or {}) if isinstance(row.get("score_components"), Mapping) else {},
        "vi_triggered": bool(row.get("vi_triggered")),
        "quote_ok": bool(row.get("quote_ok")),
        "flow_ok": bool(row.get("flow_ok")),
        "quote": quote_fields,
        "flow": flow_fields,
        "warnings": list(row.get("warnings") or []) if isinstance(row.get("warnings"), list) else [],
    }
    if row.get("reject_reason"):
        payload["reject_reason"] = row.get("reject_reason")
    return payload


def _prefilter_market_payload(prefilter: Mapping[str, Any], market: str) -> Dict[str, Any]:
    markets = prefilter.get("markets") if isinstance(prefilter.get("markets"), Mapping) else {}
    market_payload = markets.get(str(market or "").upper()) if isinstance(markets, Mapping) else {}
    market_payload = market_payload if isinstance(market_payload, Mapping) else {}
    selected = market_payload.get("selected") if isinstance(market_payload.get("selected"), list) else []
    rejected = market_payload.get("rejected_sample") if isinstance(market_payload.get("rejected_sample"), list) else []
    return {
        "tool": "kis_operational_prefilter",
        "contract_version": prefilter.get("contract_version"),
        "generated_at": prefilter.get("generated_at"),
        "market": str(market or "").upper(),
        "kis_only": True,
        "is_dummy_data": False,
        "artifacts": prefilter.get("artifacts") if isinstance(prefilter.get("artifacts"), Mapping) else {},
        "summary": {
            "seed_count": market_payload.get("seed_count"),
            "vi_seed_count": market_payload.get("vi_seed_count"),
            "quote_fetch_count": market_payload.get("quote_fetch_count"),
            "flow_fetch_count": market_payload.get("flow_fetch_count"),
            "selected_count": market_payload.get("selected_count"),
            "rejected_count": market_payload.get("rejected_count"),
        },
        "endpoint_summary": market_payload.get("endpoint_summary") or [],
        "selected_tickers": market_payload.get("selected_tickers") or [],
        "selected": [_compact_prefilter_candidate(row) for row in selected if isinstance(row, Mapping)],
        "rejected_sample": [_compact_prefilter_candidate(row) for row in rejected if isinstance(row, Mapping)],
        "warnings": list(prefilter.get("warnings") or []) if isinstance(prefilter.get("warnings"), list) else [],
    }


def _pipeline_summary_path(summary: Mapping[str, Any]) -> Path | None:
    raw_path = summary.get("scan_pipeline_summary")
    if raw_path:
        return Path(str(raw_path))
    artifact_dir = summary.get("artifact_dir")
    if artifact_dir:
        return Path(str(artifact_dir)) / "scan_pipeline_summary.json"
    return None


def _write_pipeline_summary_with_prefilter(summary: Dict[str, Any], prefilter_payload: Mapping[str, Any]) -> Path | None:
    summary["kis_operational_prefilter"] = dict(prefilter_payload)
    summary.setdefault("persistence_contract", {})
    if isinstance(summary.get("persistence_contract"), dict):
        summary["persistence_contract"]["kis_operational_prefilter"] = True
    path = _pipeline_summary_path(summary)
    if path is None:
        return None
    payload = dict(summary)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                existing.update(payload)
                payload = existing
        except Exception:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def _refresh_scan_universe_snapshot_with_prefilter(
    *,
    run_id: str,
    market: str,
    scan_mode: str,
    summary: Mapping[str, Any],
) -> Dict[str, Any]:
    if not _env_enabled("AG_SCAN_UNIVERSE_SNAPSHOT_WRITE_DB", "1"):
        return {"ok": True, "enabled": False, "reason": "disabled_by_env", "rows_built": 0, "rows_upserted": 0}
    artifact_dir_raw = str(summary.get("artifact_dir") or "").strip()
    if not artifact_dir_raw:
        return {"ok": False, "enabled": True, "reason": "artifact_dir_missing", "rows_built": 0, "rows_upserted": 0}
    artifact_dir = Path(artifact_dir_raw)
    try:
        from multi_agent.tools.backfill_scan_universe_snapshots import (
            DEFAULT_REJECT_OUTCOME_CSV,
            build_snapshot_rows,
            upsert_supabase,
        )

        reject_outcome_csv = Path(os.getenv("AG_REJECT_OUTCOME_CSV") or DEFAULT_REJECT_OUTCOME_CSV)
        limit_runs = max(1, int(os.getenv("AG_KIS_PREFILTER_SNAPSHOT_REFRESH_LIMIT_RUNS", "8")))
        rows, builder_summary = build_snapshot_rows(
            artifact_dir=artifact_dir.parent,
            shared_dir=PROJECT_ROOT / "runtime_state" / "shared_working",
            reject_outcome_csv=reject_outcome_csv,
            limit_runs=limit_runs,
            market_filter=str(market or "").upper(),
            scan_mode_filter=str(scan_mode or "SWING").upper(),
        )
        run_rows = [row for row in rows if str(row.get("run_id") or "") == str(run_id)]
        if not run_rows:
            return {
                "ok": False,
                "enabled": True,
                "reason": "no_run_rows_built",
                "rows_built": 0,
                "rows_upserted": 0,
                "builder_summary": builder_summary,
            }
        batch_size = max(1, int(os.getenv("AG_SCAN_UNIVERSE_SNAPSHOT_BATCH_SIZE", "500")))
        rows_upserted = upsert_supabase(run_rows, batch_size=batch_size)
        return {
            "ok": rows_upserted == len(run_rows),
            "enabled": True,
            "rows_built": len(run_rows),
            "rows_upserted": rows_upserted,
            "target_table": "scan_universe_snapshots",
            "builder_version": builder_summary.get("version"),
            "kis_prefilter_feature_rows": sum(
                1
                for row in run_rows
                if isinstance(row.get("feature_snapshot"), dict)
                and isinstance(row["feature_snapshot"].get("kis_operational_prefilter"), dict)
            ),
        }
    except BaseException as exc:
        return {
            "ok": False,
            "enabled": True,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "rows_built": 0,
            "rows_upserted": 0,
            "target_table": "scan_universe_snapshots",
        }


def _persist_prefilter_artifact_for_run(
    *,
    summary: Dict[str, Any],
    market: str,
    scan_mode: str,
    prefilter_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    run_id = str(summary.get("run_id") or "").strip()
    if not run_id:
        return {"ok": False, "enabled": True, "error": "run_id_missing"}
    summary_path = _write_pipeline_summary_with_prefilter(summary, prefilter_payload)
    summary_runtime_result: Dict[str, Any] = {"ok": False, "enabled": True, "rows_upserted": 0, "reason": "not_attempted"}
    try:
        from modules.runtime_artifact_store import upsert_runtime_artifact_payload

        runtime_result = upsert_runtime_artifact_payload(
            run_id=run_id,
            artifact_key="kis_operational_prefilter",
            payload=dict(prefilter_payload),
            market=market,
            scan_mode=scan_mode,
            source="kis_operational_prefilter",
            source_path=str((prefilter_payload.get("artifacts") or {}).get("json") or ""),
            metadata={
                "summary_path": str(summary_path) if summary_path else "",
                "feature_contract": "feature_snapshot.kis_operational_prefilter",
            },
        )
        summary["kis_prefilter_runtime_artifact"] = runtime_result
    except Exception as exc:
        runtime_result = {"ok": False, "enabled": True, "rows_upserted": 0, "artifact_key": "kis_operational_prefilter", "error": str(exc)}
        summary["kis_prefilter_runtime_artifact"] = runtime_result
    snapshot_result = _refresh_scan_universe_snapshot_with_prefilter(
        run_id=run_id,
        market=market,
        scan_mode=scan_mode,
        summary=summary,
    )
    summary["kis_prefilter_scan_universe_snapshot"] = snapshot_result
    summary_path = _write_pipeline_summary_with_prefilter(summary, prefilter_payload)
    try:
        from modules.runtime_artifact_store import upsert_runtime_artifact_payload

        summary_runtime_result = upsert_runtime_artifact_payload(
            run_id=run_id,
            artifact_key="scan_pipeline_summary",
            payload=summary,
            market=market,
            scan_mode=scan_mode,
            source="kis_operational_prefilter",
            source_path=str(summary_path) if summary_path else "",
            metadata={
                "summary_path": str(summary_path) if summary_path else "",
                "feature_contract": "feature_snapshot.kis_operational_prefilter",
                "refreshed_after_kis_prefilter": True,
            },
        )
    except Exception as exc:
        summary_runtime_result = {"ok": False, "enabled": True, "rows_upserted": 0, "artifact_key": "scan_pipeline_summary", "error": str(exc)}
    summary["kis_prefilter_scan_pipeline_summary_artifact"] = summary_runtime_result
    _write_pipeline_summary_with_prefilter(summary, prefilter_payload)
    return {
        "ok": bool(runtime_result.get("ok") or runtime_result.get("enabled") is False)
        and bool(snapshot_result.get("ok") or snapshot_result.get("enabled") is False)
        and bool(summary_runtime_result.get("ok") or summary_runtime_result.get("enabled") is False),
        "runtime_artifact": runtime_result,
        "scan_pipeline_summary_artifact": summary_runtime_result,
        "scan_universe_snapshot": snapshot_result,
        "summary_path": str(summary_path) if summary_path else None,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    load_dotenv()
    load_dotenv(PROJECT_ROOT / ".env.local")
    selected_markets = _markets(args.market)
    if args.allow_live_network:
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"

    config = KISConfig.from_env()
    if args.allow_live_network:
        config = replace(config, live_network_allowed=True)
    client = KISOpenAPIClient(config=config, timeout=float(args.kis_timeout_sec))
    prefilter_config = KISOperationalPrefilterConfig(
        markets=selected_markets,
        max_candidates_per_market=max(1, int(args.max_candidates_per_market)),
        rank_limit_per_source=max(1, int(args.rank_limit_per_source)),
        quote_limit_per_market=max(0, int(args.quote_limit_per_market)),
        flow_limit_per_market=max(0, int(args.flow_limit_per_market)),
        include_vi=not bool(args.disable_vi),
        fetch_flow=bool(args.fetch_flow),
        sleep_sec=max(0.0, float(args.kis_call_sleep_sec)),
        trade_date=str(args.trade_date or ""),
        exclude_status_warnings=not bool(args.allow_status_warnings),
        require_quote_activity=not bool(args.allow_zero_activity),
    )

    prefilter = build_kis_operational_prefilter(client, prefilter_config)
    stamp = _kst_timestamp()
    report_path = REPORT_DIR / f"kis_operational_prefilter_{stamp}.json"
    prefilter["artifacts"] = {"json": str(report_path), "latest_json": str(REPORT_DIR / "kis_operational_prefilter_latest.json")}
    prefilter["artifacts"] = write_kis_operational_prefilter_report(
        prefilter,
        output_path=report_path,
        latest_path=REPORT_DIR / "kis_operational_prefilter_latest.json",
    )

    market_runs: List[Dict[str, Any]] = []
    env = _scan_env(args)
    for market in selected_markets:
        tickers_with_names = selected_ticker_arg(prefilter, market)
        tickers = selected_ticker_symbols(prefilter, market)
        selected_count = len([item for item in tickers.split(",") if item.strip()])
        prefilter_market_payload = _prefilter_market_payload(prefilter, market)
        item: Dict[str, Any] = {
            "market": market,
            "selected_count": selected_count,
            "tickers": tickers,
            "tickers_with_names": tickers_with_names,
            "dry_run": bool(args.dry_run),
            "kis_prefilter": {
                "artifact_key": "kis_operational_prefilter",
                "contract_version": prefilter_market_payload.get("contract_version"),
                "selected_count": selected_count,
                "selected_tickers": prefilter_market_payload.get("selected_tickers") or [],
                "feature_contract": "feature_snapshot.kis_operational_prefilter",
            },
        }
        if selected_count <= 0:
            item["ok"] = bool(args.allow_empty_prefilter)
            item["returncode"] = 0 if args.allow_empty_prefilter else 1
            item["error"] = "no_prefilter_candidates"
            market_runs.append(item)
            continue
        command = _pipeline_command(args, market=market, tickers=tickers)
        item["command"] = command
        if args.dry_run:
            item["ok"] = True
            item["returncode"] = 0
        else:
            result = _run_streamed(command, env=env, timeout_sec=max(0.0, float(args.pipeline_timeout_sec)))
            if not isinstance(result.get("summary"), dict) or not result.get("summary", {}).get("run_id"):
                result["summary"] = _load_recent_pipeline_summary(
                    market=market,
                    started_epoch=float(result.get("started_epoch") or 0.0),
                )
            if isinstance(result.get("summary"), dict) and result["summary"].get("run_id"):
                result["kis_prefilter_persistence"] = _persist_prefilter_artifact_for_run(
                    summary=result["summary"],
                    market=market,
                    scan_mode=str(args.scan_mode).upper(),
                    prefilter_payload=prefilter_market_payload,
                )
            item.update(result)
            item["ok"] = int(result.get("returncode") or 0) == 0 and not result.get("timeout")
        market_runs.append(item)

    pipeline_summaries = [item.get("summary") for item in market_runs if isinstance(item.get("summary"), dict)]
    first_summary = next((item for item in pipeline_summaries if item.get("run_id")), {})
    summary = {
        "tool": "run_kis_operational_kr_scan",
        "run_id": first_summary.get("run_id"),
        "market": args.market.upper(),
        "scan_mode": str(args.scan_mode).upper(),
        "ok": all(bool(item.get("ok")) for item in market_runs),
        "dry_run": bool(args.dry_run),
        "kis_only": True,
        "health": build_kis_adapter_health(config=config),
        "prefilter": {
            "summary": prefilter.get("summary"),
            "artifacts": prefilter.get("artifacts"),
            "markets": {
                market: {
                    "seed_count": payload.get("seed_count"),
                    "quote_fetch_count": payload.get("quote_fetch_count"),
                    "flow_fetch_count": payload.get("flow_fetch_count"),
                    "selected_count": payload.get("selected_count"),
                    "selected_tickers": payload.get("selected_tickers"),
                    "endpoint_summary": payload.get("endpoint_summary"),
                }
                for market, payload in (prefilter.get("markets") or {}).items()
                if isinstance(payload, dict)
            },
            "warnings": prefilter.get("warnings") or [],
        },
        "market_runs": market_runs,
        "result_count": sum(
            int((item.get("summary") or {}).get("result_count") or 0)
            for item in market_runs
            if isinstance(item.get("summary"), dict)
        ),
        "total_scans": sum(int(item.get("selected_count") or 0) for item in market_runs),
    }
    summary["artifacts"] = _write_summary(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run KR operational scanner with a real KIS prefilter.")
    parser.add_argument("--market", default="ALL", choices=["ALL", "KOSPI", "KOSDAQ"])
    parser.add_argument("--scan-mode", default="SWING", choices=["SWING", "INTRADAY"])
    parser.add_argument("--profile", default=os.getenv("AG_SCAN_PROFILE", "prod"), choices=["prod", "dev"])
    parser.add_argument("--max-candidates-per-market", type=int, default=int(os.getenv("AG_KIS_PREFILTER_MAX_CANDIDATES", "80")))
    parser.add_argument("--rank-limit-per-source", type=int, default=int(os.getenv("AG_KIS_PREFILTER_RANK_LIMIT", "80")))
    parser.add_argument("--quote-limit-per-market", type=int, default=int(os.getenv("AG_KIS_PREFILTER_QUOTE_LIMIT", "0")))
    parser.add_argument("--flow-limit-per-market", type=int, default=int(os.getenv("AG_KIS_PREFILTER_FLOW_LIMIT", "0")))
    parser.add_argument("--fetch-flow", action="store_true", default=os.getenv("AG_KIS_PREFILTER_FETCH_FLOW", "0").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--disable-vi", action="store_true")
    parser.add_argument("--allow-status-warnings", action="store_true")
    parser.add_argument("--allow-zero-activity", action="store_true")
    parser.add_argument("--allow-empty-prefilter", action="store_true")
    parser.add_argument("--workers", type=int, default=int(os.getenv("AG_KIS_OPERATIONAL_SCAN_WORKERS", "4")))
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--allow-live-network", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--kis-timeout-sec", type=float, default=float(os.getenv("AG_KIS_OPERATIONAL_TIMEOUT_SEC", "8")))
    parser.add_argument("--kis-call-sleep-sec", type=float, default=float(os.getenv("KIS_LIVE_CALL_SLEEP_SEC", "0.12")))
    parser.add_argument("--sidecar-call-sleep-sec", type=float, default=float(os.getenv("AG_KIS_SIDECAR_CALL_SLEEP_SEC", "0.25")))
    parser.add_argument("--deep-kis-daily-max-chunks", type=int, default=int(os.getenv("AG_KIS_OPERATIONAL_DAILY_MAX_CHUNKS", "3")))
    parser.add_argument("--pipeline-timeout-sec", type=float, default=float(os.getenv("AG_KIS_OPERATIONAL_PIPELINE_TIMEOUT_SEC", "0")))
    parser.add_argument("--trade-date", default="")
    parser.add_argument("--enable-sidecar", action="store_true", default=os.getenv("AG_KIS_OPERATIONAL_ENABLE_SIDECAR", "1").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--enable-sidecar-quote", action="store_true", default=True)
    parser.add_argument("--enable-sidecar-flow", action="store_true", default=os.getenv("AG_KIS_OPERATIONAL_ENABLE_SIDECAR_FLOW", "1").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--enable-sidecar-rank", action="store_true", default=os.getenv("AG_KIS_OPERATIONAL_ENABLE_SIDECAR_RANK", "1").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--enable-sidecar-vi", action="store_true", default=os.getenv("AG_KIS_OPERATIONAL_ENABLE_SIDECAR_VI", "1").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--enable-sidecar-news", action="store_true", default=os.getenv("AG_KIS_OPERATIONAL_ENABLE_SIDECAR_NEWS", "1").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--enable-sidecar-stock-info", action="store_true", default=os.getenv("AG_KIS_OPERATIONAL_ENABLE_SIDECAR_STOCK_INFO", "1").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--enable-sidecar-financial", action="store_true", default=os.getenv("AG_KIS_OPERATIONAL_ENABLE_SIDECAR_FINANCIAL", "1").lower() in {"1", "true", "yes", "on"})
    args = parser.parse_args()
    try:
        summary = run(args)
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0 if summary.get("ok") else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
