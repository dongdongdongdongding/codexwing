import json
import sys
import types

import pandas as pd

from multi_agent.tools import report_kospi_normal_pead_shadow as shadow


def test_resolve_pending_retries_missing_primary_panel_capw(tmp_path, monkeypatch):
    ledger = tmp_path / "kospi_normal_pead_shadow_ledger.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "date": "2026-06-01",
                "ticker": "005930.KS",
                "panel_capw_excess": None,
                "ks11_excess": 1.23,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(shadow, "LEDGER", ledger)
    monkeypatch.setattr(shadow, "_capw_market_return", lambda start: 4.0)

    def fake_data_reader(ticker, start):
        return pd.DataFrame({"Close": [100, 101, 102, 103, 104, 110]})

    monkeypatch.setitem(
        sys.modules,
        "FinanceDataReader",
        types.SimpleNamespace(DataReader=fake_data_reader),
    )

    summary = shadow.resolve_pending("2026-06-15")

    saved = json.loads(ledger.read_text(encoding="utf-8").strip())
    assert saved["panel_capw_excess"] == 5.4
    assert saved["ks11_excess"] == 1.23
    assert summary["resolved"] == 1
    assert summary["panel_capw_excess_avg"] == 5.4
