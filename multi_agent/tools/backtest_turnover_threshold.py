#!/usr/bin/env python3
"""
Backtest: Current vs Conservative-Relaxed turnover threshold comparison.

Groups:
  KOSPI:
    A (current)   : Amount >= 100B  (AG_KOSPI_MIN_TURNOVER = 10_000_000_000)
    B (new add)   : Amount  30B~100B
    C (excluded)  : Amount < 30B

  KOSDAQ:
    A (current)   : Amount >= 70B   (AG_KOSDAQ_MIN_TURNOVER = 7_000_000_000)
    B (new add)   : Amount  10B~70B
    C (excluded)  : Amount < 10B

Per group, samples N stocks, fetches 60 trading days of OHLCV,
then computes:
  - avg 1D, 3D, 5D returns
  - positive hit rate (>0%)
  - big-mover rate (>5% in 1D, >10% in 3D)
  - daily top-3 precision: on each day, picks top-3 by volume surge
    and checks subsequent 1D/3D return

Run: python3 multi_agent/tools/backtest_turnover_threshold.py
"""
from __future__ import annotations

import json
import math
import random
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── config ────────────────────────────────────────────────────────────────────

SAMPLE_PER_GROUP = 60       # 그룹당 샘플 종목 수
LOOKBACK_DAYS = 60          # 가격 데이터 lookback (거래일 기준 ~3달)
MIN_DATA_ROWS = 30          # 최소 데이터 행 수
RANDOM_SEED = 42

THRESHOLDS = {
    "KOSPI": {
        "A_label": "Current  (≥100억)",  "A_min": 10_000_000_000, "A_max": None,
        "B_label": "New-add  (30~100억)", "B_min":  3_000_000_000, "B_max": 10_000_000_000,
        "C_label": "Excluded (<30억)",   "C_min":  0,              "C_max":  3_000_000_000,
    },
    "KOSDAQ": {
        "A_label": "Current  (≥70억)",   "A_min":  7_000_000_000, "A_max": None,
        "B_label": "New-add  (10~70억)", "B_min":  1_000_000_000, "B_max":  7_000_000_000,
        "C_label": "Excluded (<10억)",   "C_min":  0,              "C_max":  1_000_000_000,
    },
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe(v: Any, default: float = 0.0) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _fetch_ohlcv(ticker_fdr: str, days: int) -> Optional[pd.DataFrame]:
    """Fetch OHLCV via FinanceDataReader. ticker_fdr = bare 6-digit code."""
    try:
        import FinanceDataReader as fdr
        end = datetime.today()
        start = end - timedelta(days=int(days * 1.8))
        df = fdr.DataReader(ticker_fdr, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df is None or df.empty:
            return None
        df = df.dropna(subset=["Close"])
        if len(df) < MIN_DATA_ROWS:
            return None
        return df.tail(days)
    except Exception:
        return None


def _compute_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """1D/3D/5D returns + big-mover rates from OHLCV df."""
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float)

    ret_1d = close.pct_change(1).dropna() * 100
    ret_3d = close.pct_change(3).dropna() * 100
    ret_5d = close.pct_change(5).dropna() * 100

    avg_vol20 = volume.rolling(20, min_periods=5).mean()
    vol_ratio = (volume / avg_vol20.replace(0, np.nan)).dropna()

    # 거래량 급등 상위 일에 다음날 수익률
    if len(vol_ratio) >= 5 and len(ret_1d) >= 5:
        surge_days_idx = vol_ratio.nlargest(max(3, len(vol_ratio) // 5)).index
        fwd_rets = []
        for idx in surge_days_idx:
            pos = df.index.get_loc(idx)
            if pos + 1 < len(close):
                fwd = (float(close.iloc[pos + 1]) / float(close.iloc[pos]) - 1) * 100
                fwd_rets.append(fwd)
        surge_fwd_1d = float(np.mean(fwd_rets)) if fwd_rets else 0.0
    else:
        surge_fwd_1d = 0.0

    return {
        "avg_1d": float(ret_1d.mean()) if len(ret_1d) else 0.0,
        "avg_3d": float(ret_3d.mean()) if len(ret_3d) else 0.0,
        "avg_5d": float(ret_5d.mean()) if len(ret_5d) else 0.0,
        "positive_1d": float((ret_1d > 0).mean()) if len(ret_1d) else 0.0,
        "positive_3d": float((ret_3d > 0).mean()) if len(ret_3d) else 0.0,
        "big_up_5pct_1d": float((ret_1d >= 5.0).mean()) if len(ret_1d) else 0.0,
        "big_up_10pct_3d": float((ret_3d >= 10.0).mean()) if len(ret_3d) else 0.0,
        "vol_surge_fwd_1d": surge_fwd_1d,
        "rows": len(df),
    }


def _group_metrics(tickers: List[str], suffix: str, lookback: int) -> Dict[str, Any]:
    """Compute aggregated metrics for a list of tickers. FDR uses bare 6-digit codes."""
    all_metrics: List[Dict[str, Any]] = []
    failed = 0
    for t in tickers:
        # FDR DataReader takes bare code (no .KS/.KQ suffix)
        fdr_ticker = t
        df = _fetch_ohlcv(fdr_ticker, lookback)
        if df is None:
            failed += 1
            continue
        m = _compute_metrics(df)
        all_metrics.append(m)

    if not all_metrics:
        return {"n": 0, "failed": failed}

    def _avg(key: str) -> float:
        vals = [m[key] for m in all_metrics if isinstance(m.get(key), (int, float))]
        return round(float(np.mean(vals)), 4) if vals else 0.0

    return {
        "n": len(all_metrics),
        "failed": failed,
        "avg_1d_pct": _avg("avg_1d"),
        "avg_3d_pct": _avg("avg_3d"),
        "avg_5d_pct": _avg("avg_5d"),
        "positive_1d_rate": _avg("positive_1d"),
        "positive_3d_rate": _avg("positive_3d"),
        "big_up_5pct_1d_rate": _avg("big_up_5pct_1d"),
        "big_up_10pct_3d_rate": _avg("big_up_10pct_3d"),
        "vol_surge_fwd_1d_pct": _avg("vol_surge_fwd_1d"),
    }


def run_backtest(market: str) -> Dict[str, Any]:
    import FinanceDataReader as fdr

    thr = THRESHOLDS[market]
    suffix = ".KS" if market == "KOSPI" else ".KQ"
    mkt_key = "KOSPI" if market == "KOSPI" else "KOSDAQ"

    print(f"\n[{market}] Loading listing...", flush=True)
    listing = fdr.StockListing(mkt_key)
    listing = listing.copy()
    listing["Code"] = listing["Code"].astype(str).str.zfill(6)
    listing["Amount"] = pd.to_numeric(listing["Amount"], errors="coerce").fillna(0)

    # Exclude ETF/ETN/preferred (코드 끝 0이 아닌 것 제외 - 우선주 5, ETF 0XX9XX 등)
    listing = listing[listing["Code"].str.endswith("0") | listing["Code"].str.endswith("5")]
    # 거래소 ETF 필터 (종목명에 'ETF','ETN','인버스','레버리지','선물' 포함 제외)
    etf_mask = listing["Name"].str.contains("ETF|ETN|인버스|레버리지|선물|스팩|SPAC", na=False, case=False)
    listing = listing[~etf_mask]

    rng = random.Random(RANDOM_SEED)

    groups = {}
    for g in ("A", "B", "C"):
        gmin = thr[f"{g}_min"]
        gmax = thr[f"{g}_max"]
        if gmax is None:
            mask = listing["Amount"] >= gmin
        else:
            mask = (listing["Amount"] >= gmin) & (listing["Amount"] < gmax)
        codes = listing.loc[mask, "Code"].tolist()
        sampled = rng.sample(codes, min(SAMPLE_PER_GROUP, len(codes)))
        groups[g] = {
            "label": thr[f"{g}_label"],
            "total_in_universe": len(codes),
            "sampled": len(sampled),
            "codes": sampled,
        }
        print(f"  {thr[f'{g}_label']}: universe={len(codes)}, sampled={len(sampled)}", flush=True)

    results = {}
    for g, info in groups.items():
        label = info["label"]
        print(f"  [{market}] Fetching {info['sampled']} tickers for {label}...", flush=True)
        metrics = _group_metrics(info["codes"], suffix, LOOKBACK_DAYS)
        results[g] = {**info, **metrics}
        avg1d = metrics.get("avg_1d_pct") or 0.0
        big1d = (metrics.get("big_up_5pct_1d_rate") or 0.0) * 100
        big3d = (metrics.get("big_up_10pct_3d_rate") or 0.0) * 100
        print(f"    → n={metrics.get('n')}, avg_1d={avg1d:+.2f}%  "
              f"big_up_5pct_1d={big1d:.1f}%  "
              f"big_up_10pct_3d={big3d:.1f}%", flush=True)

    return {
        "market": market,
        "lookback_days": LOOKBACK_DAYS,
        "sample_per_group": SAMPLE_PER_GROUP,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "groups": results,
    }


def build_markdown(reports: List[Dict[str, Any]]) -> str:
    lines = [
        "# 거래대금 기준 완화 비교 백테스트",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- lookback: {LOOKBACK_DAYS} trading days",
        f"- sample_per_group: {SAMPLE_PER_GROUP}",
        "",
        "## 분석 방법",
        "- 그룹별 무작위 샘플링 → 60거래일 OHLCV 수집",
        "- avg 1D/3D/5D return, positive hit rate, big-mover 빈도 비교",
        "- vol_surge_fwd_1d: 해당 종목의 거래량 급등일 다음날 평균 수익률",
        "",
    ]

    for report in reports:
        market = report["market"]
        lines.append(f"## {market}")
        lines.append("")
        lines.append(f"| 구분 | 유니버스 | 샘플 | avg_1D | avg_3D | avg_5D | positive_1D | big_up_5%_1D | big_up_10%_3D | surge_fwd_1D |")
        lines.append(f"|------|----------|------|--------|--------|--------|-------------|--------------|---------------|--------------|")
        for g, info in report["groups"].items():
            label = info["label"]
            n = info.get("n", 0)
            lines.append(
                f"| {label} | {info['total_in_universe']} | {n} "
                f"| {info.get('avg_1d_pct', 0):+.2f}% "
                f"| {info.get('avg_3d_pct', 0):+.2f}% "
                f"| {info.get('avg_5d_pct', 0):+.2f}% "
                f"| {info.get('positive_1d_rate', 0)*100:.1f}% "
                f"| {info.get('big_up_5pct_1d_rate', 0)*100:.1f}% "
                f"| {info.get('big_up_10pct_3d_rate', 0)*100:.1f}% "
                f"| {info.get('vol_surge_fwd_1d_pct', 0):+.2f}% |"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    out_dir = PROJECT_ROOT / "runtime_state" / "reports" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    reports = []
    for market in ("KOSPI", "KOSDAQ"):
        report = run_backtest(market)
        reports.append(report)

    combined = {"generated_at": datetime.now(timezone.utc).isoformat(), "reports": reports}
    json_path = out_dir / "backtest_turnover_threshold.json"
    md_path = out_dir / "backtest_turnover_threshold.md"
    json_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(reports), encoding="utf-8")
    print(f"\n[DONE] {json_path}")
    print(f"[DONE] {md_path}")
    print(json.dumps(combined, ensure_ascii=False, indent=2)[:500])


if __name__ == "__main__":
    main()
