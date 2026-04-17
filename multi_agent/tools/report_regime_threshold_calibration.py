#!/usr/bin/env python3
"""
report_regime_threshold_calibration.py
────────────────────────────────────────────────────────────
레짐별 최적 prob5_threshold 및 calibration 리포트.

각 레짐(BULL/BEAR/HIGH_VOL/THEME_EXPANSION/SIDEWAYS)에서
어떤 prob5 임계값이 실제 Top5 정확도를 가장 높이는지 분석한다.

출력:
  runtime_state/reports/validation/regime_threshold_calibration.json
  runtime_state/reports/validation/regime_threshold_calibration.md

사용:
  python multi_agent/tools/report_regime_threshold_calibration.py
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
THRESHOLDS_TO_TEST = [50.0, 53.0, 55.0, 58.0, 60.0, 63.0, 65.0]
TOPN = 5
MATURE_DAYS = 5   # 결과 성숙 기간


def _load_supabase_outcomes(market: str = "KR", limit: int = 2000) -> List[Dict]:
    """Supabase market_scan_results에서 realized_return이 있는 행 로드."""
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
        res = (
            client.table("market_scan_results")
            .select("ml_prob,decision_score,return_5d_pct,return_3d_pct,return_1d_pct,scan_mode,market_type,recommended_at,created_at")
            .not_.is_("return_5d_pct", "null")
            .lt("recommended_at", cutoff)
            .order("recommended_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        print(f"  WARNING: Supabase 로드 실패: {exc}")
        return []


def _assign_mock_regime(row: Dict) -> str:
    """
    실제 레짐 분류기 없이 스캔 날짜 기반으로 임시 레짐 부여.
    실제 운영에선 regime_classifier 결과를 스캔 시 저장해야 함.
    여기서는 return_5d_pct 분포로 시장 상황을 역추정한다.
    """
    r5 = float(row.get("return_5d_pct") or 0)
    # 단순 프록시: 평균 5일 수익률로 레짐 추정
    if r5 > 5:
        return "BULL"
    elif r5 < -5:
        return "BEAR"
    else:
        return "SIDEWAYS"


def _precision_at_n(rows: List[Dict], prob_col: str, threshold: float,
                    return_col: str, n: int) -> Dict[str, Any]:
    """threshold 이상 종목 중 상위 N개의 양수 수익률 비율."""
    above = [r for r in rows if float(r.get(prob_col) or 0) >= threshold]
    above_sorted = sorted(above, key=lambda r: float(r.get(prob_col) or 0), reverse=True)
    topn = above_sorted[:n]
    if not topn:
        return {"n": 0, "precision": None, "avg_return": None}
    positive = sum(1 for r in topn if float(r.get(return_col) or 0) > 0)
    avg_ret = sum(float(r.get(return_col) or 0) for r in topn) / len(topn)
    return {
        "n": len(topn),
        "n_above_threshold": len(above),
        "precision": round(positive / len(topn) * 100, 1),
        "avg_return": round(avg_ret, 3),
    }


def run_calibration(market: str = "KR") -> Dict[str, Any]:
    print(f"\n{'=' * 60}")
    print(f"  Regime Threshold Calibration Report")
    print(f"  Market: {market}  |  {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'=' * 60}")

    print("\n[1/3] 데이터 로드 중...")
    rows = _load_supabase_outcomes(market)
    if not rows:
        print("  데이터 없음 — Supabase 연결 또는 mature 데이터 부족")
        # 샘플 리포트만 생성
        rows = []

    print(f"  로드된 행: {len(rows)}")

    # 레짐별 분류 (mock)
    regime_groups: Dict[str, List[Dict]] = {}
    for row in rows:
        regime = _assign_mock_regime(row)
        regime_groups.setdefault(regime, []).append(row)

    print(f"\n[2/3] 레짐별 threshold 스캔")
    print(f"{'─' * 60}")

    results: Dict[str, Any] = {}
    return_col = "return_5d_pct" if market in ("KR", "KOSPI", "KOSDAQ") else "return_3d_pct"

    for regime, regime_rows in sorted(regime_groups.items()):
        print(f"\n  [{regime}]  n={len(regime_rows)}")
        best_thr = 58.0
        best_prec = 0.0
        thr_results = []

        for thr in THRESHOLDS_TO_TEST:
            metrics = _precision_at_n(regime_rows, "ml_prob", thr, return_col, TOPN)
            prec = metrics.get("precision")
            avg_r = metrics.get("avg_return")
            n_top = metrics.get("n", 0)
            icon = "★" if (prec and prec > best_prec) else " "
            print(f"    {icon} thr={thr:.0f}%  top{TOPN}={n_top}  prec={prec}%  avg={avg_r}%")
            thr_results.append({"threshold": thr, **metrics})
            if prec and prec > best_prec:
                best_prec = prec
                best_thr = thr

        results[regime] = {
            "n_rows": len(regime_rows),
            "best_threshold": best_thr,
            "best_precision": best_prec,
            "threshold_sweep": thr_results,
        }

    # 현재 regime_router.py 설정과 비교
    from modules.regime_router import REGIME_PROFILES
    print(f"\n[3/3] 현재 설정 vs 데이터 권장값 비교")
    print(f"{'─' * 60}")
    print(f"  {'레짐':<20} {'현재 임계값':>12} {'데이터 권장값':>14} {'차이':>8}")
    print(f"  {'─'*56}")

    recommendations: Dict[str, Dict] = {}
    for regime, data in results.items():
        current = REGIME_PROFILES.get(regime, {}).get("prob5_threshold", 58.0)
        recommended = data.get("best_threshold", current)
        diff = recommended - current
        icon = "↑" if diff > 0 else ("↓" if diff < 0 else "=")
        print(f"  {regime:<20} {current:>12.1f}% {recommended:>14.1f}% {diff:>+7.1f}% {icon}")
        recommendations[regime] = {
            "current_threshold": current,
            "recommended_threshold": recommended,
            "change": round(diff, 1),
            "data_precision": data.get("best_precision"),
            "n_rows": data.get("n_rows", 0),
        }

    output = {
        "generated_at": datetime.now().isoformat(),
        "market": market,
        "n_total_rows": len(rows),
        "return_col": return_col,
        "topn": TOPN,
        "mature_days": MATURE_DAYS,
        "regime_results": results,
        "recommendations": recommendations,
        "note": (
            "임시 레짐 분류(return_5d_pct 기반)이며 실제 레짐 분류기 결과와 다를 수 있음. "
            "regime_classifier.py 결과를 스캔 시 저장하면 더 정확한 calibration 가능."
        ) if rows else "데이터 없음 — Supabase mature 데이터 필요",
    }

    # 저장
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "regime_threshold_calibration.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    md_lines = [
        f"# Regime Threshold Calibration — {market}",
        f"Generated: {output['generated_at'][:16]}  |  n={len(rows)} rows",
        "",
        "## 권장 임계값",
        "| 레짐 | 현재 | 권장 | 변화 | 근거 정밀도 |",
        "|------|------|------|------|-------------|",
    ]
    for regime, rec in recommendations.items():
        md_lines.append(
            f"| {regime} | {rec['current_threshold']}% | {rec['recommended_threshold']}% "
            f"| {rec['change']:+.1f}% | {rec['data_precision']}% |"
        )
    md_path = REPORT_DIR / "regime_threshold_calibration.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\n  저장: {json_path}")
    print(f"{'=' * 60}\n")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default="KR")
    args = parser.parse_args()
    run_calibration(args.market)
