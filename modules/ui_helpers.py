from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import uuid4


def compute_progress_fraction(completed_count: int, total_count: int) -> float:
    total = max(int(total_count or 0), 0)
    completed = max(int(completed_count or 0), 0)
    if total <= 0:
        return 0.0
    return min(1.0, max(0.0, completed / total))


def _to_float(value) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return numeric


def resolve_display_price(realtime_price, last_close) -> float:
    realtime = _to_float(realtime_price)
    if realtime > 0:
        return realtime
    return max(_to_float(last_close), 0.0)


def format_volume_display(volume) -> str:
    numeric = max(_to_float(volume), 0.0)
    return f"{int(round(numeric)):,}"


@dataclass
class BackgroundScanState:
    market: str
    scan_mode: str
    engine_label: str
    max_scan: int
    job_id: str = field(default_factory=lambda: uuid4().hex[:10])
    status: str = "queued"
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    total_scans: int = 0
    completed_scans: int = 0
    progress: float = 0.0
    current_symbol: str = ""
    status_line: str = "스캔을 준비 중입니다."
    error: str = ""
    results: List[Dict[str, Any]] = field(default_factory=list)
    logs: List[Dict[str, str]] = field(default_factory=list)
    scan_diagnostics: Dict[str, Any] = field(
        default_factory=lambda: {
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
    )
    bridge_info: Dict[str, Any] = field(default_factory=dict)
    regime: Dict[str, Any] = field(default_factory=dict)
    intel_data: Dict[str, Any] = field(default_factory=dict)
    planner_warning: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def append_log(self, level: str, message: str, max_items: int = 120) -> None:
        with self._lock:
            self.logs.append({"level": str(level), "message": str(message)})
            if len(self.logs) > max_items:
                self.logs = self.logs[-max_items:]

    def append_result(self, row: Dict[str, Any]) -> None:
        with self._lock:
            self.results.append(dict(row))

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "job_id": self.job_id,
                "market": self.market,
                "scan_mode": self.scan_mode,
                "engine_label": self.engine_label,
                "max_scan": self.max_scan,
                "status": self.status,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "total_scans": self.total_scans,
                "completed_scans": self.completed_scans,
                "progress": self.progress,
                "current_symbol": self.current_symbol,
                "status_line": self.status_line,
                "error": self.error,
                "results": list(self.results),
                "logs": list(self.logs),
                "scan_diagnostics": dict(self.scan_diagnostics),
                "bridge_info": dict(self.bridge_info),
                "regime": dict(self.regime),
                "intel_data": dict(self.intel_data),
                "planner_warning": self.planner_warning,
            }
