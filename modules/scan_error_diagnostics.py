"""Bounded scan failure evidence without credentials or source-code tracebacks."""
from __future__ import annotations

import os
import re
import traceback
from pathlib import Path


def safe_error_message(value: object) -> str:
    message = str(value)
    # Exceptions may embed request URLs/headers or configured credentials.
    for name, secret in os.environ.items():
        if len(secret) >= 8 and re.search(r"TOKEN|SECRET|PASSWORD|API_?KEY|APPKEY|APPSECRET|SERVICE_ROLE", name, re.I):
            message = message.replace(secret, "[redacted]")
    message = re.sub(r"https?://[^\s<>]+", "[url]", message)
    message = re.sub(r"(?i)\b(Bearer|Basic)\s+[^\s,;'\"]+", r"\1 [redacted]", message)
    message = re.sub(r"(?i)([\"']?(?:authorization|access_token|refresh_token|api_key|apikey|appkey|appsecret|password|secret)[\"']?\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;}]+)", r"\1[redacted]", message)
    return " ".join(message.split())[:1000]


def scan_error_detail(error: object, *, attempts: int | None = None) -> dict:
    detail = {
        "error_type": type(error).__name__ if isinstance(error, BaseException) else "WorkerError",
        "message": safe_error_message(error),
    }
    if attempts is not None:
        detail["attempts"] = attempts
    if isinstance(error, BaseException):
        detail["frames"] = [
            {"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
            for f in traceback.extract_tb(error.__traceback__)[-8:]
        ]
    return detail


def record_scan_error(diagnostics: dict, symbol: str, *, data: dict | None = None,
                      exc: BaseException | None = None) -> dict:
    """Persist one failure alongside the existing count/symbol contracts."""
    kind = "executor" if exc is not None else "worker"
    count_key = "executor_exception_count" if exc is not None else "worker_error_count"
    symbols_key = "exception_symbols" if exc is not None else "error_symbols"
    diagnostics[count_key] = diagnostics.get(count_key, 0) + 1
    diagnostics.setdefault(symbols_key, []).append(symbol)
    if exc is not None:
        detail = scan_error_detail(exc)
    else:
        payload = data or {}
        detail = dict(payload.get("error_detail") or
                      scan_error_detail(payload.get("error", "unknown worker error")))
    detail["message"] = safe_error_message(detail.get("message", ""))
    detail["stage"] = kind
    diagnostics.setdefault("errors_by_symbol", {}).setdefault(symbol, []).append(detail)
    return detail
