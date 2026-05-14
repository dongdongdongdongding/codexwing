from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from .commands import FULL_KR_SCAN_MAX

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JOB_DIR = Path("runtime_state/discord_jobs")
ARTIFACT_DIR = Path("runtime_state/artifacts")
LOCK_PATH = JOB_DIR / "full_kr_scan.lock"


@dataclass(frozen=True)
class DiscordScanJob:
    job_id: str
    market: str
    log_path: Path
    started_at: str


@dataclass
class DiscordScanLock:
    path: Path = LOCK_PATH
    acquired: bool = False

    def try_acquire(self, *, job_id: str, market: str) -> bool:
        self.path = _lock_path_for_market(self.path, market)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._clear_stale_lock()
        payload = {
            "job_id": job_id,
            "market": market,
            "pid": os.getpid(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        self.acquired = True
        return True

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        self.acquired = False

    def _clear_stale_lock(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            pid = int(payload.get("pid") or 0)
        except Exception:
            pid = 0
        if pid > 0 and _pid_exists(pid):
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def _lock_path_for_market(path: Path, market: str) -> Path:
    """Scope the scan lock by market so KOSPI and KOSDAQ can run in parallel."""
    market_key = str(market or "").upper()
    if market_key not in {"KOSPI", "KOSDAQ"}:
        return path
    stem = path.stem
    if stem.upper().endswith(f"_{market_key}"):
        return path
    return path.with_name(f"{stem}_{market_key}{path.suffix}")


def create_scan_job(market: str) -> DiscordScanJob:
    normalized_market = str(market or "").upper()
    if normalized_market not in {"KOSPI", "KOSDAQ"}:
        raise ValueError(f"Unsupported Discord scan market: {market}")
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    job_id = f"DS-{uuid4().hex[:8].upper()}"
    return DiscordScanJob(
        job_id=job_id,
        market=normalized_market,
        log_path=JOB_DIR / f"{job_id}_{normalized_market}.log",
        started_at=datetime.now(timezone.utc).isoformat(),
    )


def build_scan_command(job: DiscordScanJob) -> List[str]:
    return [
        sys.executable,
        "-m",
        "multi_agent.workflows.non_ui_scan_pipeline",
        "--market",
        job.market,
        "--profile",
        "prod",
        "--max-scan",
        str(FULL_KR_SCAN_MAX),
        "--max-workers",
        "4",
        "--max-retries",
        "1",
        "--scan-mode",
        "SWING",
        "--strategy-version",
        "discord-full-kr-v1",
        "--model-version",
        "legacy",
        "--code-version",
        "discord-scan-executor-v1",
    ]


async def run_scan_job(job: DiscordScanJob) -> Dict[str, Any]:
    return await asyncio.to_thread(_run_scan_job_sync, job)


def _run_scan_job_sync(job: DiscordScanJob) -> Dict[str, Any]:
    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    cmd = build_scan_command(job)
    with job.log_path.open("w", encoding="utf-8") as log:
        log.write(f"[{job.started_at}] Starting Discord scan job {job.job_id} {job.market}\n")
        log.write("Command: " + " ".join(cmd) + "\n\n")
        log.flush()
        completed = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        log.write(f"\n[{datetime.now(timezone.utc).isoformat()}] Exit code: {completed.returncode}\n")

    output = _tail_text(job.log_path, max_chars=200_000)
    summary = _extract_last_json_object(output)
    if summary is None:
        summary = _load_recent_artifact_summary(job)
    if summary is None:
        summary = {}
    summary["discord_job"] = {
        "job_id": job.job_id,
        "market": job.market,
        "started_at": job.started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "returncode": completed.returncode,
        "log_path": str(job.log_path),
    }
    return summary


def _load_recent_artifact_summary(job: DiscordScanJob) -> Dict[str, Any] | None:
    started_at = _parse_iso_timestamp(job.started_at)
    candidates: List[tuple[float, Path]] = []
    for path in ARTIFACT_DIR.glob("RUN-*/scan_pipeline_summary.json"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if started_at is not None and mtime < started_at.timestamp() - 30:
            continue
        candidates.append((mtime, path))

    for _mtime, path in sorted(candidates, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("market") or "").upper() != job.market:
            continue
        if payload.get("run_id"):
            return payload
    return None


def _parse_iso_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _tail_text(path: Path, *, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _extract_last_json_object(text: str) -> Dict[str, Any] | None:
    decoder = json.JSONDecoder()
    starts = [idx for idx, char in enumerate(text) if char == "{"]
    for start in reversed(starts):
        candidate = text[start:].strip()
        try:
            obj, end = decoder.raw_decode(candidate)
        except Exception:
            continue
        if isinstance(obj, dict) and (
            obj.get("run_id") or {"market", "result_count", "total_scans"}.issubset(obj.keys())
        ):
            return obj
    return None


__all__ = [
    "DiscordScanJob",
    "DiscordScanLock",
    "build_scan_command",
    "create_scan_job",
    "run_scan_job",
]
