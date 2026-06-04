from __future__ import annotations

import sys

from multi_agent.tools import live_full_kr_swing_scan as scan


def test_allow_empty_results_returns_success_for_completed_empty_scan(monkeypatch):
    monkeypatch.setattr(scan, "scan_symbol_with_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live_full_kr_swing_scan.py",
            "--workers",
            "1",
            "--tickers",
            "005930.KS=Samsung",
            "--allow-empty-results",
        ],
    )

    assert scan.main() == 0


def test_empty_results_still_fail_without_allow_empty_option(monkeypatch):
    monkeypatch.setattr(scan, "scan_symbol_with_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live_full_kr_swing_scan.py",
            "--workers",
            "1",
            "--tickers",
            "005930.KS=Samsung",
        ],
    )

    assert scan.main() == 1
