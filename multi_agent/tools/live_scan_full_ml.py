#!/usr/bin/env python3
"""Full-ML smoke scan: drives scan_symbol_with_retry the same way auto_bot does.

Why this exists
---------------
collect_universe_scan_candidates is the light path — it skips the phase25
model. To verify this session's gate fixes end-to-end (model bundle ->
quant_analysis -> planner reliability gate -> WATCHLIST emission), we need
the full path that auto_bot's hourly job uses. This wraps scan_symbol_with_retry
for a small ticker set.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scanner_runtime import SharedBackoffState, scan_symbol_with_retry  # noqa: E402


TEST_TICKERS = {
    # KOSPI
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
    "035420.KS": "NAVER",
    "005380.KS": "현대차",
    "051910.KS": "LG화학",
    # KOSDAQ
    "247540.KQ": "에코프로비엠",
    "086520.KQ": "에코프로",
    "058470.KQ": "리노공업",
    "028300.KQ": "HLB",
    "403870.KQ": "HPSP",
}


def _noop_news(*args, **kwargs):
    return {"score_adjustment": 0.0, "reasons": []}


def _noop_rank(*args, **kwargs):
    return 0.0


def main() -> int:
    backoff = SharedBackoffState()
    market_gate = {"gate": "GREEN", "kospi_chg": 0.0, "kosdaq_chg": 0.0,
                    "primary_chg": 0.0, "secondary_chg": 0.0}
    results = []
    for sym, name in TEST_TICKERS.items():
        print(f"--- {sym} {name} ---")
        try:
            row = scan_symbol_with_retry(
                sym,
                tickers_dict=TEST_TICKERS,
                is_us=False,
                is_amex=False,
                is_advanced_engine=False,
                r_status="NEUTRAL",
                intel_data=None,
                macro_ctx=None,
                market_gate=market_gate,
                rank_adjustment_fn=_noop_rank,
                news_adjustment_fn=_noop_news,
                backoff_state=backoff,
                max_retries=0,
                scan_mode="SWING",
                reject_reason_fn=lambda s, r: print(f"  reject: {r}"),
                reject_detail_fn=lambda s, m: None,
            )
            if row:
                results.append(row)
                print(f"  ✅ alpha={row.get('Antigrav')} ph25={row.get('phase25_prob')} variant={row.get('phase25_variant')} sig_dir={row.get('phase25_signal_direction')} verdict={row.get('Verdict')}")
            else:
                print(f"  ⛔ no row")
        except Exception as exc:
            print(f"  💥 exception: {exc}")

    print()
    print(f"=== Summary: {len(results)}/{len(TEST_TICKERS)} produced rows ===")
    for r in sorted(results, key=lambda x: -float(x.get("Antigrav") or 0))[:10]:
        ph25 = r.get("phase25_prob")
        sig = r.get("phase25_signal_direction")
        oos_auc = r.get("phase25_oos_auc")
        oos_win = r.get("phase25_oos_win_rate_pct")
        oos_ret = r.get("phase25_oos_avg_return_pct")
        print(f"  {r.get('Ticker')}: alpha={r.get('Antigrav')} ph25={ph25} sig={sig} oos_auc={oos_auc} win={oos_win} ret={oos_ret} verdict={r.get('Verdict')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
