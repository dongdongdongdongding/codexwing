"""Units for KIS investor amounts; preserve provider numbers in model contracts.

KIS documents investor amounts in million KRW and quantities in shares. Captured
acml_tr_pbmn instead matches the daily chart's KRW turnover: it must not receive
the investor amount multiplier. See FLOW_UNITS_AUDIT_2026-10-07.md.
"""

import math
from collections.abc import Mapping

KIS_INVESTOR_AMOUNT_UNIT = "KRW_million"
KRW_PER_MILLION = 1_000_000
FLOW_FEATURE_UNITS_VERSION = "net_million_krw_over_turnover_krw_v1"
FLOW_CACHE_UNITS = {
    "frgn_ntby": "shares", "orgn_ntby": "shares", "prsn_ntby": "shares",
    "frgn_val": KIS_INVESTOR_AMOUNT_UNIT, "orgn_val": KIS_INVESTOR_AMOUNT_UNIT,
    "acml_val": "KRW",
}
FLOW_VALUE_FIELDS = tuple(f"{side}_{days}d" for side in ("foreigner", "institution", "retail") for days in (1, 3, 10))


def canonical_flow_unit(flow, default=None):
    """Correct the legacy label only for this repo's identified KIS producers.

Those producers retained raw numbers and never converted them to won. Other
providers (notably pykrx_value) really emit KRW and must retain that unit.
"""
    unit = flow.get("flow_unit") or default
    source = flow.get("flow_source") or flow.get("source")
    if unit == "KRW" and source in {"kis_openapi", "kis_openapi_period_cache", "kis_openapi_sidecar:kis_openapi"}:
        return KIS_INVESTOR_AMOUNT_UNIT
    return unit


def net_amount_to_turnover(net_million_krw, turnover_krw):
    """Dimensionless fraction; retain the existing one-won denominator guard.

Supports scalars and pandas Series without changing their index or nulls.
"""
    return net_million_krw * KRW_PER_MILLION / (turnover_krw + 1)


def flow_metadata_for_values(row, values):
    """Preserve provenance only if its owner contains every selected flow value.

Never borrow a KIS sidecar's units for unrelated base-model values. Historical
snapshots can recover their own metadata after exact numeric agreement. No
amount or quantity is converted; unverified provenance remains explicit.
"""
    def number(value):
        try:
            n = float(value)
            return n if math.isfinite(n) else None
        except (TypeError, ValueError):
            return None

    selected = {k: number(values.get(k)) for k in FLOW_VALUE_FIELDS}
    selected = {k: v for k, v in selected.items() if v is not None}
    if not selected:
        return {"flow_source": None, "flow_unit": None, "flow_asof": None,
                "flow_warnings": ["investor_flow_missing_in_scan_archive"]}
    snapshot = row.get("feature_snapshot")
    snapshot = snapshot if isinstance(snapshot, Mapping) else {}
    for owner in (row, row.get("flow"), snapshot, snapshot.get("flow")):
        if not isinstance(owner, Mapping):
            continue
        source = owner.get("flow_source")
        unit = owner.get("flow_unit")
        if not source or source == "scan_universe_snapshot" or not unit or unit == "source_units":
            continue
        if not all(number(owner.get(k)) == v for k, v in selected.items()):
            continue
        warnings = owner.get("flow_warnings", owner.get("warnings", []))
        return {"flow_source": source, "flow_unit": canonical_flow_unit(owner),
                "flow_asof": owner.get("flow_asof"),
                "flow_warnings": list(warnings) if isinstance(warnings, (list, tuple)) else []}
    warnings = row.get("flow_warnings")
    warnings = list(warnings) if isinstance(warnings, (list, tuple)) else []
    if "flow_value_provenance_unverified" not in warnings:
        warnings.append("flow_value_provenance_unverified")
    return {"flow_source": "scan_universe_snapshot", "flow_unit": "source_units",
            "flow_asof": None, "flow_warnings": warnings}
