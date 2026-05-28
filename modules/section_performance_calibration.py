from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List


SECTION_CALIBRATION_VERSION = "kr_section_performance_calibration_v1"
DEFAULT_SECTION_CALIBRATION_PATH = Path("runtime_state/reports/validation/kr_section_performance_calibration.json")


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "None"):
            return None
        result = float(str(value).replace("%", "").replace(",", "").strip())
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def normalize_market(value: Any, ticker: Any = "") -> str:
    market = str(value or "").upper().strip()
    symbol = str(ticker or "").upper().strip()
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if symbol.endswith(".KS"):
        return "KOSPI"
    if symbol.endswith(".KQ"):
        return "KOSDAQ"
    return market or "-"


def normalize_section(value: Any) -> str:
    text = str(value or "").strip()
    upper = text.upper()
    if "EXCEPTION" in upper or "익셉션" in text:
        return "Exception Leader"
    if "SHADOW" in upper or "쉐도우" in text:
        return "Shadow"
    return "Top5"


def _metrics(values: List[float]) -> Dict[str, Any]:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not clean:
        return {
            "n": 0,
            "win_pct": None,
            "avg_pct": None,
            "median_pct": None,
            "min_pct": None,
            "max_pct": None,
            "avg_win_pct": None,
            "avg_loss_pct": None,
        }
    wins = [value for value in clean if value > 0]
    losses = [value for value in clean if value <= 0]
    return {
        "n": len(clean),
        "win_pct": round(sum(1 for value in clean if value > 0) / len(clean) * 100.0, 4),
        "avg_pct": round(sum(clean) / len(clean), 6),
        "median_pct": round(float(median(clean)), 6),
        "min_pct": round(min(clean), 6),
        "max_pct": round(max(clean), 6),
        "avg_win_pct": round(sum(wins) / len(wins), 6) if wins else None,
        "avg_loss_pct": round(sum(losses) / len(losses), 6) if losses else None,
    }


def _confidence(sample_n: int) -> str:
    if sample_n >= 50:
        return "high"
    if sample_n >= 20:
        return "medium"
    if sample_n >= 8:
        return "low"
    return "small_sample"


def build_section_performance_calibration(rows: Iterable[Dict[str, Any]], *, recent_n: int = 40) -> Dict[str, Any]:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    groups: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for row in row_list:
        market = normalize_market(row.get("market"), row.get("ticker"))
        if market not in {"KOSPI", "KOSDAQ"}:
            continue
        section = normalize_section(row.get("section") or row.get("_analysis_section"))
        groups.setdefault((market, section), []).append(row)

    entries: List[Dict[str, Any]] = []
    for (market, section), group in sorted(groups.items()):
        ret3 = _metrics([_safe_float(row.get("return_3d_pct")) for row in group])
        ret5 = _metrics([_safe_float(row.get("return_5d_pct")) for row in group])
        recent_group = group[-max(int(recent_n or 0), 1) :]
        recent5 = _metrics([_safe_float(row.get("return_5d_pct")) for row in recent_group])
        stop_labels = [row.get("stop_before_target_5d") for row in group if isinstance(row.get("stop_before_target_5d"), bool)]
        sample_n = max(ret3["n"], ret5["n"])
        drift = None
        if ret5["avg_pct"] is not None and recent5["avg_pct"] is not None:
            drift = round(recent5["avg_pct"] - ret5["avg_pct"], 6)
        entries.append(
            {
                "market": market,
                "section": section,
                "sample_n": sample_n,
                "confidence": _confidence(sample_n),
                "return_3d": ret3,
                "return_5d": ret5,
                "stop_first_5d_pct": round(sum(1 for value in stop_labels if value) / len(stop_labels) * 100.0, 4) if stop_labels else None,
                "recent_window_n": recent5["n"],
                "recent_5d_avg_pct": recent5["avg_pct"],
                "recent_5d_win_pct": recent5["win_pct"],
                "recent_5d_avg_drift_pct": drift,
            }
        )
    return {
        "version": SECTION_CALIBRATION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": len(row_list),
        "recent_n": int(recent_n),
        "entries": entries,
    }


def write_section_performance_calibration(report: Dict[str, Any], path: Path = DEFAULT_SECTION_CALIBRATION_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_section_performance_calibration(path: Path = DEFAULT_SECTION_CALIBRATION_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}
