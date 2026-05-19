from modules.execution_stop_display import build_execution_stop_display
from modules.ui_helpers import build_signal_display_rows


def test_execution_stop_display_uses_stricter_dynamic_stop_for_long():
    stop = build_execution_stop_display(
        {"ticker": "009830.KS", "entry_reference_price": 100000, "stop_sl_pct": -10},
        {"entry_reference_price": 100000, "stop_sl_pct": -5, "stop_price": 95000},
    )

    assert stop["display_stop_sl_pct"] == -5.0
    assert stop["display_stop_price"] == 95000.0
    assert stop["display_stop_source"] == "top_deep_dynamic_stricter"
    assert stop["stop_conflict"] is True


def test_execution_stop_display_uses_raw_when_raw_is_stricter():
    stop = build_execution_stop_display(
        {"ticker": "009830.KS", "entry_reference_price": 100000, "stop_sl_pct": -3},
        {"entry_reference_price": 100000, "stop_sl_pct": -8, "stop_price": 92000},
    )

    assert stop["display_stop_sl_pct"] == -3.0
    assert stop["display_stop_price"] == 97000.0
    assert stop["display_stop_source"] == "raw_scan_stricter"


def test_signal_display_rows_surface_unified_stop_contract():
    display = build_signal_display_rows(
        [
            {
                "ticker": "009830.KS",
                "entry_reference_price": 100000,
                "stop_sl_pct": -10,
                "trade_plan": {
                    "entry_reference_price": 100000,
                    "stop_sl_pct": -5,
                    "stop_price": 95000,
                },
            }
        ]
    )[0]

    assert display["sl"] == "-5%"
    assert display["stop_display_source"] == "top_deep_dynamic_stricter"
    assert display["stop_conflict"] is True
