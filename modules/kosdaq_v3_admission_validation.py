from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List

REPORT_VERSION = "kosdaq_v3_admission_validation_v2"
DEFAULT_ARCHIVE_CSV = Path("runtime_state/reports/archive/scan_archive_learning_dataset_all.csv")
DEFAULT_REPORT_DIR = Path("runtime_state/reports/validation")
DEFAULT_JSON_PATH = DEFAULT_REPORT_DIR / "kosdaq_v3_admission_validation.json"
DEFAULT_MD_PATH = DEFAULT_REPORT_DIR / "kosdaq_v3_admission_validation.md"
HORIZONS = (1, 3, 5, 7, 14, 30)
EARLY_HARM_MIN_TOP5_SAMPLE = 10
EARLY_HARM_AVG_LAG_PCT = 5.0
EARLY_HARM_LOSS5_EXCESS_PCT = 25.0
EARLY_HARM_MAX_WIN_RATE_PCT = 30.0


@dataclass(frozen=True)
class BaselineMetric:
    sample_n: int
    avg_return_pct: float
    median_return_pct: float
    worst_return_pct: float
    loss5_rate_pct: float


PRE_ADMISSION_KOSDAQ_RANK1_5D = BaselineMetric(
    sample_n=29,
    avg_return_pct=0.98,
    median_return_pct=0.57,
    worst_return_pct=-11.07,
    loss5_rate_pct=24.14,
)


def load_archive_rows(path: Path = DEFAULT_ARCHIVE_CSV) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def is_kosdaq_v3_admission_row(row: Dict[str, Any]) -> bool:
    if _market(row) != "KOSDAQ" or _text(row.get("scan_mode")).upper() != "SWING":
        return False
    model = _text(row.get("relative_rank_model"))
    if model == "kosdaq_floor_win_relative_v5":
        return True
    payload = " ".join(_listify(row.get("rationale")) + _listify(row.get("theme_risk"))).lower()
    return "kosdaq_relative_admission_floor" in payload or "relative_admission" in payload


def is_kosdaq_v3_floor_row(row: Dict[str, Any]) -> bool:
    payload = " ".join(_listify(row.get("rationale")) + _listify(row.get("theme_risk"))).lower()
    return "kosdaq_relative_admission_floor" in payload


def build_kosdaq_v3_admission_validation_report(
    rows: Iterable[Dict[str, Any]],
    *,
    as_of_date: str | None = None,
    generated_at: str | None = None,
    min_matured_5d: int = 30,
) -> Dict[str, Any]:
    source_rows = [row for row in rows or [] if isinstance(row, dict)]
    kosdaq_swing = [row for row in source_rows if _market(row) == "KOSDAQ" and _text(row.get("scan_mode")).upper() == "SWING"]
    v3_rows = [row for row in kosdaq_swing if is_kosdaq_v3_admission_row(row)]
    floor_rows = [row for row in v3_rows if is_kosdaq_v3_floor_row(row)]
    rank1_rows = [row for row in v3_rows if _rank(row) == 1]
    top5_rows = [row for row in v3_rows if _rank(row) is not None and 1 <= int(_rank(row) or 999) <= 5]

    groups = {
        "v3_all": v3_rows,
        "v3_relative_floor": floor_rows,
        "v3_rank1": rank1_rows,
        "v3_top5": top5_rows,
    }
    group_metrics = {name: _horizon_metrics(group_rows) for name, group_rows in groups.items()}
    baseline = PRE_ADMISSION_KOSDAQ_RANK1_5D.__dict__
    rank1_5d = group_metrics["v3_rank1"]["5d"]
    top5_5d = group_metrics["v3_top5"]["5d"]
    verdict = _policy_verdict(rank1_5d, top5_5d, baseline=baseline, min_matured_5d=min_matured_5d)

    return {
        "report_version": REPORT_VERSION,
        "as_of_date": as_of_date or str(date.today()),
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "source": {
            "source_rows": len(source_rows),
            "kosdaq_swing_rows": len(kosdaq_swing),
            "v3_rows": len(v3_rows),
            "v3_relative_floor_rows": len(floor_rows),
            "latest_base_trade_date": _latest_date(v3_rows),
        },
        "baseline": {
            "pre_admission_kosdaq_rank1_5d": baseline,
        },
        "groups": group_metrics,
        "policy_verdict": verdict,
        "recent_v3_samples": _recent_samples(v3_rows, limit=20),
    }


def write_kosdaq_v3_admission_validation_report(
    report: Dict[str, Any],
    *,
    json_path: Path = DEFAULT_JSON_PATH,
    md_path: Path = DEFAULT_MD_PATH,
) -> Dict[str, str]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_kosdaq_v3_admission_validation_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


def build_kosdaq_v3_admission_validation_markdown(report: Dict[str, Any]) -> str:
    source = report.get("source") or {}
    verdict = report.get("policy_verdict") or {}
    lines = [
        "# KOSDAQ V3 Admission Forward Validation",
        "",
        f"- status: {verdict.get('status', '-')}",
        f"- action: {verdict.get('action', '-')}",
        f"- source rows: {source.get('source_rows', 0)} / KOSDAQ SWING {source.get('kosdaq_swing_rows', 0)} / v3 {source.get('v3_rows', 0)}",
        f"- relative floor rows: {source.get('v3_relative_floor_rows', 0)}",
        f"- latest base_trade_date: {source.get('latest_base_trade_date') or '-'}",
        "",
        "## 5D Baseline",
    ]
    baseline = (report.get("baseline") or {}).get("pre_admission_kosdaq_rank1_5d") or {}
    lines.append(
        f"- pre-admission rank1: n={baseline.get('sample_n')} avg={baseline.get('avg_return_pct')}% "
        f"median={baseline.get('median_return_pct')}% min={baseline.get('worst_return_pct')}% loss5={baseline.get('loss5_rate_pct')}%"
    )
    lines.extend(["", "## Group Metrics"])
    for group, horizons in (report.get("groups") or {}).items():
        h5 = horizons.get("5d") or {}
        lines.append(
            f"- {group}: 5D n={h5.get('sample_n')} win={h5.get('win_rate_pct')}% "
            f"avg={_fmt(h5.get('avg_return_pct'))} median={_fmt(h5.get('median_return_pct'))} "
            f"min={_fmt(h5.get('worst_return_pct'))} max={_fmt(h5.get('best_return_pct'))} loss5={h5.get('loss5_rate_pct')}%"
        )
    lines.extend(["", "## Verdict Reasons"])
    for reason in verdict.get("reasons") or []:
        lines.append(f"- {reason}")
    return "\n".join(lines).strip() + "\n"


def _horizon_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {f"{horizon}d": _metric([_to_float(row.get(f"return_{horizon}d_pct")) for row in rows]) for horizon in HORIZONS}


def _metric(values: List[float | None]) -> Dict[str, Any]:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    sample_n = len(clean)
    if not clean:
        return {
            "sample_n": 0,
            "win_n": 0,
            "win_rate_pct": None,
            "avg_return_pct": None,
            "median_return_pct": None,
            "best_return_pct": None,
            "worst_return_pct": None,
            "loss5_n": 0,
            "loss5_rate_pct": None,
        }
    return {
        "sample_n": sample_n,
        "win_n": sum(1 for value in clean if value > 0),
        "win_rate_pct": round(sum(1 for value in clean if value > 0) / sample_n * 100.0, 4),
        "avg_return_pct": round(sum(clean) / sample_n, 6),
        "median_return_pct": round(float(median(clean)), 6),
        "best_return_pct": round(max(clean), 6),
        "worst_return_pct": round(min(clean), 6),
        "loss5_n": sum(1 for value in clean if value <= -5.0),
        "loss5_rate_pct": round(sum(1 for value in clean if value <= -5.0) / sample_n * 100.0, 4),
    }


def _policy_verdict(
    rank1_5d: Dict[str, Any],
    top5_5d: Dict[str, Any],
    *,
    baseline: Dict[str, Any],
    min_matured_5d: int,
) -> Dict[str, Any]:
    reasons: List[str] = []
    rank1_n = int(rank1_5d.get("sample_n") or 0)
    top5_n = int(top5_5d.get("sample_n") or 0)
    if rank1_n < min_matured_5d:
        reasons.append(f"rank1 5D matured sample {rank1_n} < required {min_matured_5d}")
    if top5_n < min_matured_5d:
        reasons.append(f"top5 5D matured sample {top5_n} < required {min_matured_5d}")

    rank1_avg = _to_float(rank1_5d.get("avg_return_pct"))
    rank1_loss5 = _to_float(rank1_5d.get("loss5_rate_pct"))
    top5_avg = _to_float(top5_5d.get("avg_return_pct"))
    top5_win = _to_float(top5_5d.get("win_rate_pct"))
    top5_loss5 = _to_float(top5_5d.get("loss5_rate_pct"))
    baseline_avg = _to_float(baseline.get("avg_return_pct"))
    baseline_loss5 = _to_float(baseline.get("loss5_rate_pct"))
    improved_avg = rank1_avg is not None and baseline_avg is not None and rank1_avg > baseline_avg
    improved_loss = rank1_loss5 is not None and baseline_loss5 is not None and rank1_loss5 < baseline_loss5
    if rank1_avg is not None and baseline_avg is not None:
        reasons.append(f"rank1 avg5 {rank1_avg:.4f}% vs baseline {baseline_avg:.4f}%")
    if rank1_loss5 is not None and baseline_loss5 is not None:
        reasons.append(f"rank1 loss5 {rank1_loss5:.4f}% vs baseline {baseline_loss5:.4f}%")
    if top5_avg is not None and baseline_avg is not None:
        reasons.append(f"top5 avg5 {top5_avg:.4f}% vs baseline {baseline_avg:.4f}%")
    if top5_win is not None:
        reasons.append(f"top5 win5 {top5_win:.4f}%")
    if top5_loss5 is not None and baseline_loss5 is not None:
        reasons.append(f"top5 loss5 {top5_loss5:.4f}% vs baseline {baseline_loss5:.4f}%")

    early_harm_reasons = _early_harm_reasons(
        top5_n=top5_n,
        top5_avg=top5_avg,
        top5_win=top5_win,
        top5_loss5=top5_loss5,
        baseline_avg=baseline_avg,
        baseline_loss5=baseline_loss5,
    )
    if rank1_n < min_matured_5d and top5_n < min_matured_5d and early_harm_reasons:
        return {
            "status": "negative_early_evidence",
            "action": "keep_disabled_or_retune",
            "reasons": reasons + early_harm_reasons,
        }

    if rank1_n >= min_matured_5d and improved_avg and improved_loss:
        return {"status": "pass", "action": "keep_or_consider_tune_up", "reasons": reasons}
    if rank1_n >= min_matured_5d and not (improved_avg or improved_loss):
        return {"status": "fail", "action": "rollback_or_retune", "reasons": reasons}
    return {"status": "insufficient_sample", "action": "continue_forward_validation", "reasons": reasons}


def _early_harm_reasons(
    *,
    top5_n: int,
    top5_avg: float | None,
    top5_win: float | None,
    top5_loss5: float | None,
    baseline_avg: float | None,
    baseline_loss5: float | None,
) -> List[str]:
    if top5_n < EARLY_HARM_MIN_TOP5_SAMPLE:
        return []
    reasons: List[str] = []
    if top5_avg is not None and baseline_avg is not None and top5_avg <= baseline_avg - EARLY_HARM_AVG_LAG_PCT:
        reasons.append(
            f"early harm guard: top5 avg5 lags baseline by at least {EARLY_HARM_AVG_LAG_PCT:.1f}pp"
        )
    if top5_loss5 is not None and baseline_loss5 is not None and top5_loss5 >= baseline_loss5 + EARLY_HARM_LOSS5_EXCESS_PCT:
        reasons.append(
            f"early harm guard: top5 loss5 exceeds baseline by at least {EARLY_HARM_LOSS5_EXCESS_PCT:.1f}pp"
        )
    if top5_win is not None and top5_win <= EARLY_HARM_MAX_WIN_RATE_PCT:
        reasons.append(f"early harm guard: top5 win5 <= {EARLY_HARM_MAX_WIN_RATE_PCT:.1f}%")
    return reasons


def _recent_samples(rows: List[Dict[str, Any]], *, limit: int) -> List[Dict[str, Any]]:
    samples = []
    for row in sorted(rows, key=lambda item: (_date_key(item), _text(item.get("ticker"))), reverse=True)[:limit]:
        samples.append(
            {
                "base_trade_date": _date_key(row),
                "run_id": _text(row.get("run_id")),
                "ticker": _text(row.get("ticker")),
                "stock_name": _text(row.get("stock_name")),
                "priority_rank": _rank(row),
                "decision": _text(row.get("decision")),
                "relative_rank_model": _text(row.get("relative_rank_model")),
                "return_1d_pct": _to_float(row.get("return_1d_pct")),
                "return_3d_pct": _to_float(row.get("return_3d_pct")),
                "return_5d_pct": _to_float(row.get("return_5d_pct")),
            }
        )
    return samples


def _market(row: Dict[str, Any]) -> str:
    market = _text(row.get("market") or row.get("market2") or row.get("market_type")).upper()
    ticker = _text(row.get("ticker")).upper()
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    if ticker.endswith(".KS"):
        return "KOSPI"
    return market


def _rank(row: Dict[str, Any]) -> int | None:
    value = _to_float(row.get("priority_rank"))
    return int(value) if value is not None else None


def _latest_date(rows: List[Dict[str, Any]]) -> str:
    values = [_date_key(row) for row in rows if _date_key(row)]
    return max(values) if values else ""


def _date_key(row: Dict[str, Any]) -> str:
    return _text(row.get("base_trade_date") or row.get("recommended_at") or row.get("created_at"))[:10]


def _listify(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except Exception:
            pass
        return [text]
    return []


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        number = float(str(value).replace(",", "").replace("%", ""))
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _fmt(value: Any) -> str:
    number = _to_float(value)
    return "-" if number is None else f"{number:+.2f}%"


__all__ = [
    "DEFAULT_ARCHIVE_CSV",
    "DEFAULT_JSON_PATH",
    "DEFAULT_MD_PATH",
    "PRE_ADMISSION_KOSDAQ_RANK1_5D",
    "build_kosdaq_v3_admission_validation_markdown",
    "build_kosdaq_v3_admission_validation_report",
    "is_kosdaq_v3_admission_row",
    "is_kosdaq_v3_floor_row",
    "load_archive_rows",
    "write_kosdaq_v3_admission_validation_report",
]
