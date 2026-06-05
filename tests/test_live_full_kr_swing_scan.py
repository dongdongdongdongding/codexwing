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


def test_kis_rank_universe_skips_non_numeric_rank_codes(monkeypatch):
    class FakeKISClient:
        def __init__(self, *args, **kwargs):
            pass

        def volume_rank(self, *, market="ALL"):
            return {
                "rt_cd": "0",
                "output": [
                    {"mksc_shrn_iscd": "0134X0", "hts_kor_isnm": "스팩"},
                    {"mksc_shrn_iscd": "090360", "hts_kor_isnm": "로보스타"},
                ],
            }

    monkeypatch.setattr("modules.kis_openapi.KISOpenAPIClient", FakeKISClient)

    frame = scan._load_kis_rank_universe(5)

    assert "0134X0.KS" not in set(frame["Code"])
    assert "0134X0.KQ" not in set(frame["Code"])
    assert set(frame["Code"]) == {"090360.KS", "090360.KQ"}
