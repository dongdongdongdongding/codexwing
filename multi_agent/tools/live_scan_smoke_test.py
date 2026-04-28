#!/usr/bin/env python3
"""Live scan smoke test with a tiny KR universe to verify gate fixes.

Why this exists
---------------
This session's gate fixes (OOS-validated 'uncertain' override in both
quant_analysis and planner_runtime, NULL-safe lookup in upsert_scan_archive,
scan_mode in db_payload) need to be verified end-to-end. A full universe
scan takes 1-2 hours; this runs ~20 known liquid KR tickers (10 KOSPI + 10
KOSDAQ) so the gate-fix verification is fast.

Outputs
-------
- New runtime_state/shared_working/RUN-<id>/ with planner_handoff.json
- New rows in market_scan_results
- Console summary of decision distribution and top picks
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from modules import db_manager  # noqa: E402
from modules.scanner_bridge import run_legacy_agent_bridge  # noqa: E402
from modules.scanner_runtime import collect_universe_scan_candidates  # noqa: E402


# Ten liquid KOSPI + ten liquid KOSDAQ. Names omitted (not used).
TEST_TICKERS = [
    ("005930.KS", "삼성전자"),
    ("000660.KS", "SK하이닉스"),
    ("373220.KS", "LG에너지솔루션"),
    ("207940.KS", "삼성바이오로직스"),
    ("005380.KS", "현대차"),
    ("035420.KS", "NAVER"),
    ("051910.KS", "LG화학"),
    ("006400.KS", "삼성SDI"),
    ("035720.KS", "카카오"),
    ("105560.KS", "KB금융"),
    ("247540.KQ", "에코프로비엠"),
    ("086520.KQ", "에코프로"),
    ("091990.KQ", "셀트리온헬스케어"),
    ("196170.KQ", "알테오젠"),
    ("058470.KQ", "리노공업"),
    ("028300.KQ", "HLB"),
    ("293490.KQ", "카카오게임즈"),
    ("357780.KQ", "솔브레인"),
    ("141080.KQ", "리가켐바이오"),
    ("403870.KQ", "HPSP"),
]


def main() -> int:
    df = pd.DataFrame(TEST_TICKERS, columns=["Code", "Name"])
    df["Marcap"] = 0
    db = db_manager.DBManager()

    def _save(data):
        payload = dict(data or {})
        payload.setdefault("scan_mode", "SWING")
        payload.setdefault("feature_origin", "live_smoke_test")
        db.upsert_scan_result(payload)

    print(f"🔬 Live smoke scan: {len(df)} KR tickers (10 KOSPI + 10 KOSDAQ)")
    candidates = collect_universe_scan_candidates(
        df_tickers=df, market_code="KR", save_scan_result_fn=_save, logger=print,
    )
    print(f"\n✅ Scan complete: {len(candidates)} candidates")
    if not candidates:
        print("   (no candidates passed liquidity / antigrav filters)")
        return 1

    # Bridge: produces planner_handoff.json under shared_working
    run_legacy_agent_bridge(
        results=candidates,
        market="KR",
        strategy_version="smoke-test",
        model_version="phase25",
        code_version="smoke-test-v1",
        logger=print,
    )

    print(f"\nTop 5 by alpha_score:")
    sortable = sorted(
        candidates,
        key=lambda c: float(c.get("Antigrav") or c.get("alpha_score") or 0),
        reverse=True,
    )[:5]
    for c in sortable:
        sym = c.get("Ticker") or c.get("ticker")
        alpha = c.get("Antigrav") or c.get("alpha_score")
        ph25 = c.get("phase25_prob") or c.get("phase25_blended_prob")
        verdict = c.get("Verdict") or c.get("verdict")
        print(f"  {sym}: alpha={alpha} phase25={ph25} verdict={verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
