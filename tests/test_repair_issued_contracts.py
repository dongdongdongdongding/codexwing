from multi_agent.tools.repair_issued_contracts import changes

KEY = ("SWING-CAND-20261001", "002990.KS")
ISSUED = {KEY: {"date": "2026-10-01", "ticker": KEY[1], "close": 12270,
                "p": .75, "contract_h": 10, "contract_tp": .05}}


def test_archive_keeps_outcomes_but_excludes_stale_reference_labels():
    old = {"run_id": KEY[0], "ticker": KEY[1], "entry_reference_price": 12320,
           "return_1d_pct": 4.2}
    patch = changes("market_scan_results", old, ISSUED)
    assert patch["entry_reference_price"] == 12270
    assert patch["hold_days"] == 10
    assert patch["validation_excluded"] is True
    assert "return_1d_pct" not in patch
    assert old["entry_reference_price"] == 12320
    assert changes("market_scan_results", {**old, **patch}, ISSUED) == {}


def test_unissued_row_is_preserved_and_excluded():
    patch = changes("market_scan_results", {"run_id": KEY[0], "ticker": "other"}, ISSUED)
    assert patch == {"validation_excluded": True, "validation_excluded_reason": "not_in_frozen_issued_ledger"}


def test_deep_preserves_existing_gate_exclusion_and_unrelated_fields():
    old = {"run_id": KEY[0], "ticker": KEY[1],
           "candidate_interpretation": {"stream_excluded": True, "stream_excluded_reason": "gate"},
           "price": {"last": 12320, "day_change_pct": 1.2}}
    patch = changes("scan_deep_reports", old, ISSUED)
    assert patch["candidate_interpretation"]["stream_excluded"] is True
    assert patch["candidate_interpretation"]["stream_excluded_reason"] == "gate"
    assert patch["price"]["day_change_pct"] == 1.2
    assert patch["trade_plan"]["hold_days"] == 10
    assert patch["realized_expectancy_admission"] == {}
    assert changes("scan_deep_reports", {**old, **patch}, ISSUED) == {}
