"""Units for KIS investor amounts; preserve provider numbers in model contracts.

KIS documents investor amounts in million KRW and quantities in shares. Captured
acml_tr_pbmn instead matches the daily chart's KRW turnover: it must not receive
the investor amount multiplier. See FLOW_UNITS_AUDIT_2026-10-07.md.
"""

KIS_INVESTOR_AMOUNT_UNIT = "KRW_million"
KRW_PER_MILLION = 1_000_000
FLOW_FEATURE_UNITS_VERSION = "net_million_krw_over_turnover_krw_v1"
FLOW_CACHE_UNITS = {
    "frgn_ntby": "shares", "orgn_ntby": "shares", "prsn_ntby": "shares",
    "frgn_val": KIS_INVESTOR_AMOUNT_UNIT, "orgn_val": KIS_INVESTOR_AMOUNT_UNIT,
    "acml_val": "KRW",
}


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
