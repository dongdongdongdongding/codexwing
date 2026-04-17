#!/usr/bin/env python3
"""
report_intraday_signal_correlation.py
────────────────────────────────────────────────────────────
INTRADAY 스캔 신호와 1일 수익률 간의 상관관계 분석.

KOSPI/KOSDAQ INTRADAY Top5 정확도 갭(-30%, -12%)을 해소하기 위해
어떤 신호가 실제 1d 수익과 상관있는지 파악한다.

분석 항목:
  - decision_score 버킷별 1d 수익
  - breakout 유무별 1d 수익
  - vol_ratio 버킷별 1d 수익
  - trend(UP/SIDE/DOWN)별 1d 수익
  - market(KOSPI/KOSDAQ) × 신호 교차 분석

출력:
  runtime_state/reports/validation/intraday_signal_correlation.json
  runtime_state/reports/validation/intraday_signal_correlation.md

사용:
  python multi_agent/tools/report_intraday_signal_correlation.py
  python multi_agent/tools/report_intraday_signal_correlation.py --market KOSPI
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "runtime_state" / "reports" / "validation"
MATURE_DAYS = 2    # INTRADAY는 1d 수익이 더 빨리 성숙
HISTORY_DAYS = 60  # 최대 60일치


def _load_intraday_rows(market: Optional[str] = None, limit: int = 3000) -> List[Dict]:
    """Supabase에서 INTRADAY 행 로드 (return_1d_pct 있는 행만)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(".env.local")
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            return []
        client = create_client(url, key)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=MATURE_DAYS)).isoformat()
        since = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).isoformat()
        q = (
            client.table("market_scan_results")
            .select(
                "ticker,market_type,scan_mode,decision_score,ml_prob,alpha_score,"
                "return_1d_pct,return_3d_pct,recommended_at,"
                "trend,tier,strategy,expected_edge_score,expected_return_1d_pct"
            )
            .eq("scan_mode", "INTRADAY")
            .not_.is_("return_1d_pct", "null")
            .lt("recommended_at", cutoff)
            .gt("recommended_at", since)
            .order("recommended_at", desc=True)
            .limit(limit)
        )
        if market:
            q = q.eq("market_type", market.upper())
        res = q.execute()
        return res.data or []
    except Exception as exc:
        print(f"  WARNING: Supabase 로드 실패: {exc}")
        return []


def _bucket_stats(rows: List[Dict], return_col: str = "return_1d_pct") -> Dict[str, Any]:
    """기본 통계 계산."""
    if not rows:
        return {"n": 0, "pos_rate": None, "avg_return": None, "median_return": None}
    returns = [float(r.get(return_col) or 0) for r in rows]
    positive = sum(1 for v in returns if v > 0)
    return {
        "n": len(returns),
        "pos_rate": round(positive / len(returns) * 100, 1),
        "avg_return": round(sum(returns) / len(returns), 3),
        "median_return": round(sorted(returns)[len(returns) // 2], 3),
        "p75_return": round(sorted(returns)[int(len(returns) * 0.75)], 3) if len(returns) >= 4 else None,
    }



def run_correlation(market: Optional[str] = None) -> Dict[str, Any]:
    mkt_label = market or "ALL"
    print(f"\n{'=' * 65}")
    print(f"  INTRADAY Signal Correlation Report")
    print(f"  Market: {mkt_label}  |  {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'=' * 65}")

    print("\n[1/5] 데이터 로드 중...")
    rows = _load_intraday_rows(market)
    if not rows:
        print("  데이터 없음 — Supabase 연결 또는 INTRADAY mature 데이터 부족")
        return {"error": "no_data", "market": mkt_label}
    print(f"  로드된 행: {len(rows)}")

    # ── 1. decision_score 버킷 ────────────────────────────────
    print("\n[2/5] Decision Score 버킷별 1d 수익")
    print(f"  {'버킷':<25} {'n':>5} {'양수율':>8} {'평균':>8} {'중앙값':>8}")
    print(f"  {'─'*56}")
    ds_buckets = [
        (lambda r: "90+" if float(r.get("decision_score") or 0) >= 90 else
                   "80-90" if float(r.get("decision_score") or 0) >= 80 else
                   "70-80" if float(r.get("decision_score") or 0) >= 70 else
                   "60-70" if float(r.get("decision_score") or 0) >= 60 else "<60"),
        ["90+", "80-90", "70-80", "60-70", "<60"],
    ]
    ds_analysis = {}
    for bucket in ds_buckets[1]:
        bucket_rows = [r for r in rows if (
            (bucket == "90+" and float(r.get("decision_score") or 0) >= 90) or
            (bucket == "80-90" and 80 <= float(r.get("decision_score") or 0) < 90) or
            (bucket == "70-80" and 70 <= float(r.get("decision_score") or 0) < 80) or
            (bucket == "60-70" and 60 <= float(r.get("decision_score") or 0) < 70) or
            (bucket == "<60" and float(r.get("decision_score") or 0) < 60)
        )]
        stats = _bucket_stats(bucket_rows)
        ds_analysis[bucket] = stats
        n = stats["n"]
        pr = f"{stats['pos_rate']}%" if stats["pos_rate"] is not None else "N/A"
        av = f"{stats['avg_return']}%" if stats["avg_return"] is not None else "N/A"
        md = f"{stats['median_return']}%" if stats["median_return"] is not None else "N/A"
        print(f"  {bucket:<25} {n:>5} {pr:>8} {av:>8} {md:>8}")

    # ── 2. alpha_score 버킷 (vol_ratio는 Supabase 미저장) ────────
    print("\n[3/5] Alpha Score 버킷별 1d 수익")
    print(f"  {'버킷':<25} {'n':>5} {'양수율':>8} {'평균':>8} {'중앙값':>8}")
    print(f"  {'─'*56}")
    vol_analysis = {}
    for bucket, lo, hi in [("≥80", 80, 999), ("70-80", 70, 80),
                            ("60-70", 60, 70), ("50-60", 50, 60),
                            ("<50", 0, 50)]:
        bucket_rows = [r for r in rows if lo <= float(r.get("alpha_score") or 0) < hi]
        stats = _bucket_stats(bucket_rows)
        vol_analysis[bucket] = stats
        n = stats["n"]
        pr = f"{stats['pos_rate']}%" if stats["pos_rate"] is not None else "N/A"
        av = f"{stats['avg_return']}%" if stats["avg_return"] is not None else "N/A"
        md = f"{stats['median_return']}%" if stats["median_return"] is not None else "N/A"
        print(f"  {bucket:<25} {n:>5} {pr:>8} {av:>8} {md:>8}")

    # ── 3. trend 방향 ─────────────────────────────────────────
    print("\n[4/5] Trend 방향별 1d 수익")
    print(f"  {'방향':<25} {'n':>5} {'양수율':>8} {'평균':>8} {'중앙값':>8}")
    print(f"  {'─'*56}")
    trend_analysis = {}
    for trend in ["UP", "SIDE", "SIDEWAYS", "DOWN"]:
        bucket_rows = [r for r in rows if str(r.get("trend") or "").upper() == trend]
        stats = _bucket_stats(bucket_rows)
        trend_analysis[trend] = stats
        n = stats["n"]
        pr = f"{stats['pos_rate']}%" if stats["pos_rate"] is not None else "N/A"
        av = f"{stats['avg_return']}%" if stats["avg_return"] is not None else "N/A"
        md = f"{stats['median_return']}%" if stats["median_return"] is not None else "N/A"
        print(f"  {trend:<25} {n:>5} {pr:>8} {av:>8} {md:>8}")

    # ── 4. market × trend 교차 ────────────────────────────────
    print("\n[5/5] Market × Trend 교차 분석 (Top5 시뮬레이션)")
    print(f"  {'Segment':<30} {'n':>5} {'양수율':>8} {'평균':>8}")
    print(f"  {'─'*50}")
    cross_analysis = {}
    markets = list(set(str(r.get("market_type") or "?") for r in rows))
    for mkt in sorted(markets):
        mkt_rows = [r for r in rows if str(r.get("market_type") or "") == mkt]
        # 전체
        stats = _bucket_stats(mkt_rows)
        cross_analysis[f"{mkt}:ALL"] = stats
        pr = f"{stats['pos_rate']}%" if stats["pos_rate"] is not None else "N/A"
        av = f"{stats['avg_return']}%" if stats["avg_return"] is not None else "N/A"
        print(f"  {mkt+':ALL':<30} {stats['n']:>5} {pr:>8} {av:>8}")

        # Top5 by decision_score per run date
        run_dates = sorted(set(str(r.get("recommended_at") or "")[:10] for r in mkt_rows))
        top5_rows: List[Dict] = []
        for date in run_dates:
            day_rows = [r for r in mkt_rows if str(r.get("recommended_at") or "")[:10] == date]
            day_rows.sort(key=lambda r: float(r.get("decision_score") or 0), reverse=True)
            top5_rows.extend(day_rows[:5])
        stats5 = _bucket_stats(top5_rows)
        cross_analysis[f"{mkt}:TOP5_DS"] = stats5
        pr5 = f"{stats5['pos_rate']}%" if stats5["pos_rate"] is not None else "N/A"
        av5 = f"{stats5['avg_return']}%" if stats5["avg_return"] is not None else "N/A"
        print(f"  {mkt+':TOP5_by_DS':<30} {stats5['n']:>5} {pr5:>8} {av5:>8}")

        # UP trend only Top5
        up_rows = [r for r in mkt_rows if "UP" in str(r.get("trend") or "").upper()]
        up_top5: List[Dict] = []
        for date in run_dates:
            day_rows = [r for r in up_rows if str(r.get("recommended_at") or "")[:10] == date]
            day_rows.sort(key=lambda r: float(r.get("decision_score") or 0), reverse=True)
            up_top5.extend(day_rows[:5])
        stats_up = _bucket_stats(up_top5)
        cross_analysis[f"{mkt}:TOP5_UP"] = stats_up
        pr_up = f"{stats_up['pos_rate']}%" if stats_up["pos_rate"] is not None else "N/A"
        av_up = f"{stats_up['avg_return']}%" if stats_up["avg_return"] is not None else "N/A"
        print(f"  {mkt+':TOP5_UP_trend':<30} {stats_up['n']:>5} {pr_up:>8} {av_up:>8}")

    # ── 권장 신호 정리 ─────────────────────────────────────────
    print(f"\n{'=' * 65}")

    # 가장 성과 좋은 버킷 찾기
    best_ds = max(ds_analysis.items(), key=lambda kv: kv[1].get("pos_rate") or 0)
    best_alpha = max(vol_analysis.items(), key=lambda kv: kv[1].get("pos_rate") or 0)
    best_trend = max(trend_analysis.items(), key=lambda kv: kv[1].get("pos_rate") or 0)

    recommendations = {
        "best_decision_score_bucket": {"bucket": best_ds[0], **best_ds[1]},
        "best_alpha_score_bucket": {"bucket": best_alpha[0], **best_alpha[1]},
        "best_trend": {"trend": best_trend[0], **best_trend[1]},
        "overall_n": len(rows),
        "note": (
            f"가장 높은 양수율 버킷: DS={best_ds[0]}({best_ds[1].get('pos_rate')}%), "
            f"Alpha={best_alpha[0]}({best_alpha[1].get('pos_rate')}%), "
            f"Trend={best_trend[0]}({best_trend[1].get('pos_rate')}%)."
        )
    }
    print(f"  권장: {recommendations['note']}")

    output = {
        "generated_at": datetime.now().isoformat(),
        "market": mkt_label,
        "n_rows": len(rows),
        "mature_days": MATURE_DAYS,
        "history_days": HISTORY_DAYS,
        "decision_score_analysis": ds_analysis,
        "vol_ratio_analysis": vol_analysis,
        "trend_analysis": trend_analysis,
        "cross_analysis": cross_analysis,
        "recommendations": recommendations,
    }

    # 저장
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{market.lower()}" if market else ""
    json_path = REPORT_DIR / f"intraday_signal_correlation{suffix}.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    md_lines = [
        f"# INTRADAY Signal Correlation — {mkt_label}",
        f"Generated: {output['generated_at'][:16]}  |  n={len(rows)} rows",
        "",
        "## Decision Score 버킷별 1d 수익",
        "| 버킷 | n | 양수율 | 평균수익 | 중앙값 |",
        "|------|---|--------|----------|--------|",
    ]
    for bucket, stats in ds_analysis.items():
        md_lines.append(
            f"| {bucket} | {stats['n']} | {stats.get('pos_rate')}% | "
            f"{stats.get('avg_return')}% | {stats.get('median_return')}% |"
        )
    md_lines += [
        "",
        "## Alpha Score 버킷별 1d 수익",
        "| 버킷 | n | 양수율 | 평균수익 | 중앙값 |",
        "|------|---|--------|----------|--------|",
    ]
    for bucket, stats in vol_analysis.items():
        md_lines.append(
            f"| {bucket} | {stats['n']} | {stats.get('pos_rate')}% | "
            f"{stats.get('avg_return')}% | {stats.get('median_return')}% |"
        )
    md_lines += [
        "",
        "## Trend 방향별 1d 수익",
        "| 방향 | n | 양수율 | 평균수익 | 중앙값 |",
        "|------|---|--------|----------|--------|",
    ]
    for trend, stats in trend_analysis.items():
        md_lines.append(
            f"| {trend} | {stats['n']} | {stats.get('pos_rate')}% | "
            f"{stats.get('avg_return')}% | {stats.get('median_return')}% |"
        )
    md_lines += [
        "",
        "## 권장",
        recommendations["note"],
    ]
    md_path = REPORT_DIR / f"intraday_signal_correlation{suffix}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\n  저장: {json_path}")
    print(f"{'=' * 65}\n")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default=None, help="KOSPI / KOSDAQ / None(전체)")
    args = parser.parse_args()
    run_correlation(args.market)
