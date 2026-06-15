"""Read the KR cohort release-gate verdict so live promotion is gate-driven.

The cohort release gate (``multi_agent/tools/report_kr_cohort_release_gate.py``) writes
``runtime_state/reports/validation/kr_cohort_release_gate_{market}.json`` daily. Live
promotion of the Exception Leader / Practical-80 cohorts reads this verdict so that
promotion is *self-limiting*: if forward performance degrades and a cohort's gate flips
to FAIL, promotion for that cohort automatically stops on the next daily refresh.

This module is intentionally tiny and side-effect free (other than an mtime cache) so it
can be imported by both the planner runtime and the legacy orchestration bridge without
creating a dependency on the tools package.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"

# mtime cache: {market: (mtime, verdict)}
_CACHE: Dict[str, Tuple[float, Dict[str, bool]]] = {}

_EMPTY: Dict[str, bool] = {"EXCEPTION_LEADER": False, "PRACTICAL_80": False, "release_ready": False}


def _report_path(market: str) -> Path:
    override = os.getenv("AG_KR_COHORT_GATE_REPORT_DIR")
    base = Path(override) if override else DEFAULT_REPORT_DIR
    return base / f"kr_cohort_release_gate_{str(market).lower()}.json"


def load_cohort_gate_pass(market: str) -> Dict[str, bool]:
    """Return which cohorts currently clear the release gate for a market.

    Returns a dict ``{"EXCEPTION_LEADER": bool, "PRACTICAL_80": bool, "release_ready": bool}``.
    Defaults to all-False on any missing/unreadable report so promotion fails safe.
    """
    market_key = str(market or "").upper()
    path = _report_path(market_key)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return dict(_EMPTY)

    cached = _CACHE.get(market_key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(_EMPTY)

    cohorts = payload.get("cohorts") if isinstance(payload.get("cohorts"), dict) else {}
    verdict = {
        "EXCEPTION_LEADER": bool(cohorts.get("EXCEPTION_LEADER", {}).get("passed", False)),
        "PRACTICAL_80": bool(cohorts.get("PRACTICAL_80", {}).get("passed", False)),
        "release_ready": bool(payload.get("release_ready", False)),
    }
    _CACHE[market_key] = (mtime, verdict)
    return verdict


def cohort_gate_passes(market: str, cohort: str) -> bool:
    """Convenience: does ``cohort`` (EXCEPTION_LEADER|PRACTICAL_80) clear the gate for ``market``?"""
    return bool(load_cohort_gate_pass(market).get(str(cohort).upper(), False))
