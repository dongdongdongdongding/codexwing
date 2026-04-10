from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict


def _sanitize_for_json(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize_for_json(v) for v in value]
    return value


def write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_payload = _sanitize_for_json(payload)
    with path.open("w", encoding="utf-8") as f:
        json.dump(safe_payload, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    return path


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
