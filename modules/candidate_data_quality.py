from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


DATA_QUALITY_VERSION = "candidate_data_quality_v1"


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and text.lower() not in {"none", "nan", "null", "-"}
    return True


def _first(*values: Any) -> Any:
    for value in values:
        if _present(value):
            return value
    return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _age_hours(value: Any, now: datetime) -> float | None:
    parsed = _parse_dt(value)
    if parsed is None:
        return None
    return max(0.0, (now - parsed).total_seconds() / 3600.0)


def _field_values(row: Dict[str, Any]) -> Dict[str, Any]:
    price = row.get("price") if isinstance(row.get("price"), dict) else {}
    flow = row.get("flow") if isinstance(row.get("flow"), dict) else {}
    trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
    admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
    values = {
        "entry_reference_price": _first(trade_plan.get("entry_reference_price"), row.get("entry_reference_price"), row.get("scan_entry_reference_price")),
        "current_price": _first(price.get("current_price"), row.get("current_price"), row.get("Close"), row.get("close")),
        "volume_ratio": _first(price.get("volume_ratio_20d"), row.get("volume_ratio"), row.get("volume_ratio_20d")),
        "flow_1d": _first(
            flow.get("foreigner_1d"),
            flow.get("institution_1d"),
            flow.get("retail_1d"),
            row.get("foreigner_1d"),
            row.get("institution_1d"),
            row.get("retail_1d"),
            flow.get("foreigner"),
            flow.get("institution"),
            row.get("foreigner"),
            row.get("institution"),
            row.get("foreign_flow"),
            row.get("institution_flow"),
        ),
        "calibration": _first(admission.get("policy_version"), admission.get("calibration_source"), row.get("admission_policy_version")),
    }
    market = str(_first(row.get("market"), row.get("Market")) or "").upper()
    ticker = str(_first(row.get("ticker"), row.get("Ticker"), row.get("티커")) or "").upper()
    is_kr = market in {"KOSPI", "KOSDAQ"} or ticker.endswith((".KS", ".KQ"))
    if is_kr:
        values.update(
            {
                "flow_3d": _first(
                    flow.get("foreigner_3d"),
                    flow.get("institution_3d"),
                    flow.get("retail_3d"),
                    row.get("foreigner_3d"),
                    row.get("institution_3d"),
                    row.get("retail_3d"),
                ),
                "flow_10d": _first(
                    flow.get("foreigner_10d"),
                    flow.get("institution_10d"),
                    flow.get("retail_10d"),
                    row.get("foreigner_10d"),
                    row.get("institution_10d"),
                    row.get("retail_10d"),
                ),
                "flow_asof": _first(flow.get("asof"), flow.get("as_of"), flow.get("updated_at"), row.get("flow_asof")),
            }
        )
    return values


def build_candidate_data_quality(row: Dict[str, Any], *, now: datetime | None = None) -> Dict[str, Any]:
    row = row if isinstance(row, dict) else {}
    now = now or datetime.now(timezone.utc)
    price = row.get("price") if isinstance(row.get("price"), dict) else {}
    flow = row.get("flow") if isinstance(row.get("flow"), dict) else {}
    admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
    values = _field_values(row)
    required_fields = list(values.keys())
    missing = [field for field in required_fields if not _present(values.get(field))]

    flow_asof = _first(flow.get("asof"), flow.get("as_of"), flow.get("updated_at"), row.get("flow_asof"))
    price_asof = _first(price.get("asof"), price.get("as_of"), price.get("updated_at"), row.get("price_asof"))
    calibration_asof = _first(admission.get("generated_at"), admission.get("calibration_asof"), row.get("calibration_asof"))
    stale_fields: List[str] = []
    flow_age = _age_hours(flow_asof, now)
    price_age = _age_hours(price_asof, now)
    calibration_age = _age_hours(calibration_asof, now)
    if flow_age is not None and flow_age > 24:
        stale_fields.append("flow")
    if price_age is not None and price_age > 8:
        stale_fields.append("price")
    if calibration_age is not None and calibration_age > 24 * 14:
        stale_fields.append("calibration")

    present_count = len(required_fields) - len(missing)
    present_pct = round(present_count / len(required_fields) * 100.0, 4) if required_fields else 100.0
    if "entry_reference_price" in missing or "current_price" in missing:
        level = "critical"
    elif missing or stale_fields:
        level = "warning"
    else:
        level = "ok"

    warnings = [f"missing:{field}" for field in missing]
    warnings.extend(f"stale:{field}" for field in stale_fields)
    return {
        "version": DATA_QUALITY_VERSION,
        "required_fields": required_fields,
        "required_present_pct": present_pct,
        "missing_required_fields": missing,
        "stale_fields": stale_fields,
        "flow_asof": flow_asof,
        "price_asof": price_asof,
        "calibration_asof": calibration_asof,
        "flow_age_hours": round(flow_age, 3) if flow_age is not None else None,
        "price_age_hours": round(price_age, 3) if price_age is not None else None,
        "calibration_age_hours": round(calibration_age, 3) if calibration_age is not None else None,
        "display_warning_level": level,
        "visible_warnings": warnings,
    }
