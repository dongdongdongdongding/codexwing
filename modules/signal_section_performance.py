from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List

from modules.ui_helpers import (
    attach_display_theme_day_metrics,
    is_exception_leader_row,
    is_kosdaq_ordered_rebound_shadow_gate_row,
    is_kospi_ordered_shadow_gate_row,
)

DEFAULT_ARCHIVE_CSV = Path("runtime_state/reports/archive/scan_archive_learning_dataset_all.csv")
DEFAULT_REPORT_DIR = Path("runtime_state/reports/trading")
DEFAULT_JSON_PATH = DEFAULT_REPORT_DIR / "signal_section_performance_daily.json"
DEFAULT_CSV_PATH = DEFAULT_REPORT_DIR / "signal_section_performance_daily.csv"
DEFAULT_MD_PATH = DEFAULT_REPORT_DIR / "signal_section_performance_daily.md"
SECTIONS = ("Shadow", "Top5", "Exception Leader")
HORIZONS = (1, 3, 5)


@dataclass(frozen=True)
class SectionMetric:
    as_of_date: str
    generated_at: str
    market: str
    section: str
    horizon_days: int
    sample_n: int
    win_n: int
    win_rate_pct: float | None
    avg_return_pct: float | None
    median_return_pct: float | None
    best_return_pct: float | None
    worst_return_pct: float | None
    latest_base_trade_date: str
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "as_of_date": self.as_of_date,
            "generated_at": self.generated_at,
            "market": self.market,
            "section": self.section,
            "horizon_days": self.horizon_days,
            "sample_n": self.sample_n,
            "win_n": self.win_n,
            "win_rate_pct": self.win_rate_pct,
            "avg_return_pct": self.avg_return_pct,
            "median_return_pct": self.median_return_pct,
            "best_return_pct": self.best_return_pct,
            "worst_return_pct": self.worst_return_pct,
            "latest_base_trade_date": self.latest_base_trade_date,
            "source": self.source,
        }


def load_archive_rows(path: Path = DEFAULT_ARCHIVE_CSV) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def classify_signal_sections(row: Dict[str, Any]) -> List[str]:
    sections: List[str] = []
    if is_kosdaq_ordered_rebound_shadow_gate_row(row) or is_kospi_ordered_shadow_gate_row(row):
        sections.append("Shadow")
    if is_exception_leader_row(row):
        sections.append("Exception Leader")
    elif _to_float(row.get("priority_rank")) is not None and 1 <= float(_to_float(row.get("priority_rank")) or 999) <= 5:
        sections.append("Top5")
    return sections


def build_section_performance_metrics(
    rows: Iterable[Dict[str, Any]],
    *,
    as_of_date: str | None = None,
    generated_at: str | None = None,
    source: str = "scan_archive_learning_dataset_all",
) -> List[Dict[str, Any]]:
    generated = generated_at or datetime.now(timezone.utc).isoformat()
    as_of = as_of_date or str(date.today())
    buckets: Dict[tuple[str, str, int], List[float]] = {}
    latest_dates: Dict[tuple[str, str, int], str] = {}
    prepared_rows = attach_display_theme_day_metrics(list(rows or []))

    for row in prepared_rows:
        market = _market(row)
        if market not in {"KOSPI", "KOSDAQ"}:
            continue
        sections = classify_signal_sections(row)
        if not sections:
            continue
        base_date = str(row.get("base_trade_date") or row.get("recommended_at") or row.get("created_at") or "")
        for section in sections:
            for horizon in HORIZONS:
                value = _to_float(row.get(f"return_{horizon}d_pct"))
                if value is None:
                    continue
                key = (market, section, horizon)
                buckets.setdefault(key, []).append(value)
                if base_date and base_date > latest_dates.get(key, ""):
                    latest_dates[key] = base_date

    metrics: List[Dict[str, Any]] = []
    for market in ("KOSPI", "KOSDAQ"):
        for section in SECTIONS:
            for horizon in HORIZONS:
                key = (market, section, horizon)
                values = buckets.get(key, [])
                win_n = sum(1 for value in values if value > 0)
                sample_n = len(values)
                metric = SectionMetric(
                    as_of_date=as_of,
                    generated_at=generated,
                    market=market,
                    section=section,
                    horizon_days=horizon,
                    sample_n=sample_n,
                    win_n=win_n,
                    win_rate_pct=round((win_n / sample_n) * 100.0, 2) if sample_n else None,
                    avg_return_pct=round(sum(values) / sample_n, 4) if sample_n else None,
                    median_return_pct=round(float(median(values)), 4) if sample_n else None,
                    best_return_pct=round(max(values), 4) if sample_n else None,
                    worst_return_pct=round(min(values), 4) if sample_n else None,
                    latest_base_trade_date=latest_dates.get(key, ""),
                    source=source,
                )
                metrics.append(metric.to_dict())
    return metrics


def write_daily_section_performance_snapshot(
    metrics: List[Dict[str, Any]],
    *,
    json_path: Path = DEFAULT_JSON_PATH,
    csv_path: Path = DEFAULT_CSV_PATH,
    md_path: Path = DEFAULT_MD_PATH,
) -> Dict[str, str]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    existing: List[Dict[str, Any]] = []
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                existing = [row for row in payload if isinstance(row, dict)]
        except Exception:
            existing = []

    snapshot_dates = {str(row.get("as_of_date") or "") for row in metrics}
    merged = [row for row in existing if str(row.get("as_of_date") or "") not in snapshot_dates]
    merged.extend(metrics)
    merged.sort(
        key=lambda row: (
            str(row.get("as_of_date") or ""),
            str(row.get("market") or ""),
            str(row.get("section") or ""),
            int(row.get("horizon_days") or 0),
        )
    )

    json_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(merged, csv_path)
    _write_markdown(metrics, md_path)
    return {"json": str(json_path), "csv": str(csv_path), "md": str(md_path)}


def build_latest_performance_markdown(metrics: List[Dict[str, Any]]) -> str:
    lines = ["# Signal Section Performance Snapshot", ""]
    for market in ("KOSPI", "KOSDAQ"):
        lines.append(f"## {market}")
        for section in SECTIONS:
            values = [row for row in metrics if row.get("market") == market and row.get("section") == section]
            if not values:
                continue
            parts = []
            for row in sorted(values, key=lambda item: int(item.get("horizon_days") or 0)):
                win = _fmt_pct(row.get("win_rate_pct"))
                avg = _fmt_signed(row.get("avg_return_pct"))
                sample = int(row.get("sample_n") or 0)
                parts.append(f"{row.get('horizon_days')}D win {win} / avg {avg} / n={sample}")
            lines.append(f"- {section}: " + " | ".join(parts))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "as_of_date",
        "generated_at",
        "market",
        "section",
        "horizon_days",
        "sample_n",
        "win_n",
        "win_rate_pct",
        "avg_return_pct",
        "median_return_pct",
        "best_return_pct",
        "worst_return_pct",
        "latest_base_trade_date",
        "source",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _write_markdown(metrics: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_latest_performance_markdown(metrics), encoding="utf-8")


def _market(row: Dict[str, Any]) -> str:
    market = str(row.get("market") or row.get("market_subtype") or row.get("market_type") or "").upper()
    ticker = str(row.get("ticker") or "").upper()
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return market


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return None
        return float(text.replace(",", "").replace("%", ""))
    except Exception:
        return None


def _fmt_pct(value: Any) -> str:
    numeric = _to_float(value)
    return "-" if numeric is None else f"{numeric:.1f}%"


def _fmt_signed(value: Any) -> str:
    numeric = _to_float(value)
    return "-" if numeric is None else f"{numeric:+.2f}%"


__all__ = [
    "DEFAULT_ARCHIVE_CSV",
    "DEFAULT_CSV_PATH",
    "DEFAULT_JSON_PATH",
    "DEFAULT_MD_PATH",
    "build_latest_performance_markdown",
    "build_section_performance_metrics",
    "classify_signal_sections",
    "load_archive_rows",
    "write_daily_section_performance_snapshot",
]
