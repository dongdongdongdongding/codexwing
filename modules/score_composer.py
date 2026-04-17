"""
score_composer.py
────────────────────────────────────────────────────────────
Decision Score v3 통합 스코어 계산.

공식:
  v3 = hit_prob_norm × clean_hit_prob × trend_quality × volume_quality
       × risk_adjustment

각 항목:
  hit_prob_norm   : prob_5 를 [0, 1] 정규화 (/ 100)
  clean_hit_prob  : meta_quality_ranker의 P(clean_hit) [0, 1]
                    모델 없으면 기본값 0.65 (과거 clean_hit율 기준)
  trend_quality   : UP=1.15 / SIDE=1.0 / DOWN=0.80
  volume_quality  : volume_confirmed=True → 1.10, False → 0.90
  risk_adjustment : 1 - clamp(|expected_mae_pct| / 10, 0, 0.4)
                    expected_mae가 -5%이면 0.50 감산, -1%이면 0.10 감산

최종값은 0~100 스케일로 정규화해서 기존 decision_score와 비교 가능.
모델 미훈련 시에도 기본값으로 안전하게 동작한다.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def compute_v3_score(
    prob_5: float,
    prob_clean: float,
    alpha_score: float,
    whale_score: float,
    real_trend: str,
    volume_confirmed: bool,
    vol_ratio: float = 1.0,
    clean_hit_prob: Optional[float] = None,
    fast_hit_prob: Optional[float] = None,
    expected_mae_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Args:
        prob_5          : 5% 달성 확률 (0~100)
        prob_clean      : clean 달성 확률 (0~100)
        alpha_score     : Antigravity 점수 (0~100)
        whale_score     : 수급 점수 (0~100)
        real_trend      : "UP" / "DOWN" / "SIDE" / "SIDEWAYS"
        volume_confirmed: 거래량 확인 여부
        vol_ratio       : 거래량 비율 (평균 대비)
        clean_hit_prob  : Meta-Quality Model P(clean_hit) [0,1] — None이면 기본값 사용
        fast_hit_prob   : Meta-Quality Model P(fast_hit) [0,1]  — 참고용
        expected_mae_pct: 예상 최대 낙폭 (음수 %) — None이면 리스크 조정 생략

    Returns:
        {
            "v3_score": float,         # 0~100 스케일 통합 점수
            "hit_prob_norm": float,
            "clean_hit_prob_used": float,
            "trend_quality": float,
            "volume_quality": float,
            "risk_adjustment": float,
            "components": dict,        # 진단용 상세 분해
        }
    """
    # ── 1. hit_prob 정규화 ─────────────────────────────────
    hit_prob_norm = _clamp(float(prob_5 or 0) / 100.0, 0.01, 0.99)

    # ── 2. clean_hit_prob ──────────────────────────────────
    # 모델 없으면 prob_clean(스캐너 내부 추정)을 정규화해서 사용
    if clean_hit_prob is not None:
        cqp = _clamp(float(clean_hit_prob), 0.1, 0.99)
    else:
        cqp = _clamp(float(prob_clean or 50) / 100.0, 0.1, 0.99)

    # ── 3. trend_quality ───────────────────────────────────
    trend_upper = str(real_trend or "").upper()
    if trend_upper == "UP":
        tq = 1.15
    elif trend_upper in ("DOWN",):
        tq = 0.80
    else:
        tq = 1.00  # SIDE / SIDEWAYS / unknown

    # ── 4. volume_quality ──────────────────────────────────
    if volume_confirmed:
        vq = 1.10
    elif float(vol_ratio or 1.0) >= 1.5:
        vq = 1.05   # 확인은 안 됐지만 거래량 1.5x 이상
    else:
        vq = 0.90

    # ── 5. risk_adjustment (expected MAE 기반) ─────────────
    if expected_mae_pct is not None:
        # expected_mae_pct은 음수. -5%면 리스크 크다.
        # penalty = |mae| / 10, 최대 0.40
        penalty = _clamp(abs(float(expected_mae_pct)) / 10.0, 0.0, 0.40)
        ra = 1.0 - penalty
    else:
        ra = 1.0  # 모델 없으면 조정 없음

    # ── 6. 기본 품질 소수 계산 ─────────────────────────────
    quality_fraction = hit_prob_norm * cqp * tq * vq * ra

    # ── 7. 0~100 스케일 정규화 ─────────────────────────────
    # 이론 최대: 0.99 × 0.99 × 1.15 × 1.10 × 1.0 ≈ 1.233
    # → 100 스케일로 선형 변환
    MAX_QUALITY = 0.99 * 0.99 * 1.15 * 1.10 * 1.0
    v3_raw = (quality_fraction / MAX_QUALITY) * 100.0

    # alpha_score / whale_score를 소폭 반영 (기존 score와 연속성 유지)
    # 가중 평균: v3 70% + 기존 베이스 30%
    legacy_base = (
        float(alpha_score or 0) * 0.58
        + float(whale_score or 0) * 0.10
        + float(prob_5 or 0) * 0.20
        + float(prob_clean or 0) * 0.12
    )
    v3_blended = round(v3_raw * 0.70 + legacy_base * 0.30, 1)
    v3_score = _clamp(v3_blended, 0.0, 100.0)

    return {
        "v3_score": v3_score,
        "hit_prob_norm": round(hit_prob_norm, 4),
        "clean_hit_prob_used": round(cqp, 4),
        "fast_hit_prob": round(float(fast_hit_prob or 0), 4),
        "trend_quality": tq,
        "volume_quality": vq,
        "risk_adjustment": round(ra, 4),
        "components": {
            "quality_fraction": round(quality_fraction, 4),
            "v3_raw": round(v3_raw, 2),
            "legacy_base": round(legacy_base, 2),
        },
    }


def enrich_result_with_v3(
    result: Dict[str, Any],
    clean_hit_prob: Optional[float] = None,
    fast_hit_prob: Optional[float] = None,
    expected_mae_pct: Optional[float] = None,
    regime_multiplier: float = 1.0,
) -> Dict[str, Any]:
    """
    스캔 결과 딕셔너리에 v3_score를 추가해 반환.
    기존 decision_score는 유지하고 v3_score를 신규 필드로 추가.

    Args:
        result: scanner_services.py의 스캔 결과 딕셔너리
        clean_hit_prob / fast_hit_prob / expected_mae_pct: meta_quality_ranker 출력

    Returns:
        result에 "v3_score", "v3_detail" 필드가 추가된 딕셔너리
    """
    prob_5 = float(
        result.get("_prob_5") or result.get("ml_prob") or result.get("AI Prob", "50").replace("%", "") or 50
    )
    prob_clean = float(result.get("_prob_clean") or result.get("prob_clean") or prob_5)
    alpha_score = float(result.get("Antigrav") or result.get("alpha_score") or 50)
    whale_score = float(result.get("Whale") or result.get("whale_score") or 50)

    # trend
    trend_raw = str(result.get("Trend") or result.get("trend") or result.get("real_trend") or "")
    if "UP" in trend_raw.upper():
        real_trend = "UP"
    elif "DOWN" in trend_raw.upper():
        real_trend = "DOWN"
    else:
        real_trend = "SIDE"

    volume_confirmed = bool(result.get("Vol Confirmed") or result.get("volume_confirmed"))
    vol_ratio = float(result.get("Vol Ratio") or result.get("vol_ratio") or 1.0)

    v3 = compute_v3_score(
        prob_5=prob_5,
        prob_clean=prob_clean,
        alpha_score=alpha_score,
        whale_score=whale_score,
        real_trend=real_trend,
        volume_confirmed=volume_confirmed,
        vol_ratio=vol_ratio,
        clean_hit_prob=clean_hit_prob,
        fast_hit_prob=fast_hit_prob,
        expected_mae_pct=expected_mae_pct,
    )

    result = dict(result)
    raw_v3 = v3["v3_score"]
    # regime_multiplier 적용 후 0~100 클램프
    result["v3_score"] = round(_clamp(raw_v3 * regime_multiplier, 0.0, 100.0), 1)
    result["v3_detail"] = {**v3, "regime_multiplier": regime_multiplier}
    return result
