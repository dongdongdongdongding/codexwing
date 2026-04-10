from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, List
from urllib import request


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_horizon_days(value: Any, default: int = 3) -> int:
    if value is None:
        return max(1, int(default))
    text = str(value).strip().upper()
    if text.startswith("T+"):
        text = text[2:]
    if text.endswith("D"):
        text = text[:-1]
    try:
        return max(1, int(float(text)))
    except Exception:
        return max(1, int(default))


def collect_stale_fallback(
    *,
    shared_dir: Path,
    market: str,
    limit_runs: int = 200,
    max_rows: int = 30,
) -> Dict[str, Any]:
    now_dt = datetime.now(timezone.utc)
    run_dirs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")] if shared_dir.exists() else []
    run_dirs = sorted(run_dirs, key=lambda p: p.name, reverse=True)
    if limit_runs > 0:
        run_dirs = run_dirs[: int(limit_runs)]

    stale_rows: List[Dict[str, Any]] = []
    considered_runs = 0
    for run_dir in run_dirs:
        scanner_payload = _load_json(run_dir / "scanner_handoff.json")
        run_ctx = scanner_payload.get("run_context", {}) if isinstance(scanner_payload, dict) else {}
        run_market = str(run_ctx.get("market", "")).upper() if isinstance(run_ctx, dict) else ""
        if run_market and run_market != str(market).upper():
            continue
        considered_runs += 1
        outcomes_payload = _load_json(run_dir / "realized_outcomes.json")
        outcomes = outcomes_payload.get("outcomes", []) if isinstance(outcomes_payload.get("outcomes"), list) else []
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            if str(row.get("decision", "")).upper() != "FALLBACK_WATCHLIST":
                continue
            if str(row.get("status", "")).upper() != "PENDING":
                continue
            rec_dt = _parse_iso(row.get("recommended_at"))
            if rec_dt is None:
                continue
            horizon_days = _parse_horizon_days(row.get("horizon"), default=3)
            stale = now_dt >= (rec_dt + timedelta(days=horizon_days))
            if not stale:
                continue
            stale_rows.append(
                {
                    "run_id": run_dir.name,
                    "ticker": row.get("ticker"),
                    "recommended_at": row.get("recommended_at"),
                    "horizon": row.get("horizon"),
                    "priority_rank": row.get("priority_rank"),
                    "source_ref": row.get("source_ref"),
                }
            )

    stale_rows = sorted(
        stale_rows,
        key=lambda r: f"{r.get('recommended_at','')}:{r.get('run_id','')}:{r.get('ticker','')}",
    )
    return {
        "generated_at": now_dt.isoformat(),
        "market": str(market).upper(),
        "runs_considered": int(considered_runs),
        "stale_fallback_pending_count": len(stale_rows),
        "sample_rows": stale_rows[: max(1, int(max_rows))] if stale_rows else [],
    }


def _post_webhook(url: str, payload: Dict[str, Any], timeout_sec: int = 5) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url=str(url),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=max(1, int(timeout_sec))) as resp:
        code = int(getattr(resp, "status", 200) or 200)
        text = resp.read().decode("utf-8", errors="replace")
    return {"status_code": code, "response": text[:1000]}


def emit_stale_fallback_alert(
    *,
    shared_dir: Path,
    market: str,
    min_stale_count: int,
    webhook_url: str,
    limit_runs: int = 200,
    dry_run: bool = False,
) -> Dict[str, Any]:
    health = collect_stale_fallback(
        shared_dir=shared_dir,
        market=market,
        limit_runs=limit_runs,
        max_rows=20,
    )
    stale_count = int(health.get("stale_fallback_pending_count", 0) or 0)
    threshold = max(1, int(min_stale_count))
    if stale_count < threshold:
        return {
            "sent": False,
            "reason": "below_threshold",
            "threshold": threshold,
            "stale_count": stale_count,
            "health": health,
        }

    payload = {
        "event": "stale_fallback_pending_alert",
        "market": str(market).upper(),
        "threshold": threshold,
        "stale_count": stale_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "message": f"Stale fallback pending count={stale_count} exceeded threshold={threshold}.",
    }
    if not webhook_url:
        return {
            "sent": False,
            "reason": "missing_webhook_url",
            "threshold": threshold,
            "stale_count": stale_count,
            "payload": payload,
        }
    if dry_run:
        return {
            "sent": False,
            "reason": "dry_run",
            "threshold": threshold,
            "stale_count": stale_count,
            "payload": payload,
        }

    try:
        resp = _post_webhook(url=webhook_url, payload=payload, timeout_sec=6)
        return {
            "sent": True,
            "threshold": threshold,
            "stale_count": stale_count,
            "webhook_result": resp,
        }
    except Exception as e:
        return {
            "sent": False,
            "reason": "webhook_error",
            "threshold": threshold,
            "stale_count": stale_count,
            "error": str(e),
        }
