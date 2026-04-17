"""
regime_router.py
────────────────────────────────────────────────────────────
Regime-aware model routing.

레짐별로 스코어 공식의 가중치와 임계값을 조정한다.
score_composer.compute_v3_score() 호출 전에 파라미터를 보정하는
'어댑터' 역할.

레짐 → 라우팅 전략:
  BULL            : 기본 P(+5%) 중심. hit_prob 가중 강화.
  BEAR            : 보수적. clean_hit_prob 가중 강화, MAE 패널티 강화.
  HIGH_VOL        : clean_hit_prob 최우선. 방향 불명이므로 억지 TOP-K 금지.
  THEME_EXPANSION : 테마 스코어 있는 종목 보너스, 고수익 기대.
  SIDEWAYS        : 기본값. 선별적.

각 레짐 프로파일은 score_composer.compute_v3_score() 에 전달할
파라미터 오버라이드 딕셔너리를 반환한다.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# ── 레짐별 v3_score 파라미터 오버라이드 ───────────────────────
# 키는 compute_v3_score()의 동작에 영향을 미치는 메타 설정

REGIME_PROFILES: Dict[str, Dict[str, Any]] = {
    "BULL": {
        # 추세 장 — hit_prob이 지배적, trend UP 보너스 최대
        "trend_up_boost":           1.20,   # UP 추세 배율 (기본 1.15)
        "trend_down_penalty":       0.80,   # DOWN 패널티 (기본 0.80)
        "volume_confirmed_boost":   1.10,
        "mae_penalty_scale":        1.0,    # MAE 패널티 스케일 (기본 1.0)
        "clean_hit_weight":         0.60,   # clean_hit_prob 가중 (공식 내 cqp 비율)
        "prob5_threshold":          55.0,   # Top-K 진입 임계값 — SWING(5d 기준)
        "prob5_intraday_threshold": 50.0,   # INTRADAY 임계값 (휴리스틱 prob_5 범위)
        "description": "추세 장: hit_prob + UP추세 강조. 임계값 완화.",
    },
    "BEAR": {
        # 하락 장 — clean_hit 최우선, MAE 패널티 강화, 임계값 높임
        "trend_up_boost":           1.05,
        "trend_down_penalty":       0.65,
        "volume_confirmed_boost":   1.15,
        "mae_penalty_scale":        1.8,    # MAE 패널티 1.8배 강화
        "clean_hit_weight":         0.85,   # clean_hit_prob 비중 최대
        "prob5_threshold":          63.0,   # 더 엄격한 진입 임계값 — SWING
        "prob5_intraday_threshold": 55.0,   # INTRADAY: 하락장도 적당히 엄격
        "description": "하락 장: clean_hit 최우선, MAE 패널티 강화, 임계값 상향.",
    },
    "HIGH_VOL": {
        # 급등락 장 — clean_hit 중심, 방향 확신 없으므로 UP 보너스 최소화
        "trend_up_boost":           1.08,
        "trend_down_penalty":       0.75,
        "volume_confirmed_boost":   1.20,  # 거래량 확인이 매우 중요
        "mae_penalty_scale":        2.0,   # MAE 패널티 2배
        "clean_hit_weight":         0.90,  # clean_hit_prob 최우선
        "prob5_threshold":          62.0,
        "prob5_intraday_threshold": 53.0,  # INTRADAY: 변동성 장, 적당한 게이트
        "description": "변동성 장: clean_hit + 거래량 확인 최우선, MAE 패널티 2배.",
    },
    "THEME_EXPANSION": {
        # 테마 확산 장 — 테마 스코어 높은 종목 유리, 고수익 기대
        "trend_up_boost":           1.15,
        "trend_down_penalty":       0.85,
        "volume_confirmed_boost":   1.10,
        "mae_penalty_scale":        0.8,   # 테마 장은 MAE 패널티 완화
        "clean_hit_weight":         0.65,
        "prob5_threshold":          56.0,  # 테마 모멘텀 우선 → 임계값 완화
        "prob5_intraday_threshold": 48.0,  # INTRADAY: 테마 확산 장, 더 완화
        "description": "테마 확산 장: 테마 스코어 우선, MAE 패널티 완화, 임계값 하향.",
    },
    "SIDEWAYS": {
        # 횡보 — 기본값
        "trend_up_boost":           1.12,
        "trend_down_penalty":       0.80,
        "volume_confirmed_boost":   1.10,
        "mae_penalty_scale":        1.2,
        "clean_hit_weight":         0.70,
        "prob5_threshold":          58.0,
        "prob5_intraday_threshold": 50.0,  # INTRADAY: 기본값
        "description": "횡보 장: 기본값. 선별적.",
    },
    "UNKNOWN": {
        "trend_up_boost":           1.15,
        "trend_down_penalty":       0.80,
        "volume_confirmed_boost":   1.10,
        "mae_penalty_scale":        1.0,
        "clean_hit_weight":         0.65,
        "prob5_threshold":          58.0,
        "prob5_intraday_threshold": 50.0,  # INTRADAY: 기본값
        "description": "레짐 미확인: 기본값 사용.",
    },
}


def get_regime_profile(regime: str) -> Dict[str, Any]:
    """레짐명으로 프로파일 반환. 없으면 UNKNOWN."""
    return REGIME_PROFILES.get(str(regime).upper(), REGIME_PROFILES["UNKNOWN"])


def compute_v3_score_regime_aware(
    prob_5: float,
    prob_clean: float,
    alpha_score: float,
    whale_score: float,
    real_trend: str,
    volume_confirmed: bool,
    vol_ratio: float = 1.0,
    clean_hit_prob: Optional[float] = None,
    fast_hit_prob: Optional[float] = None,  # noqa: ARG001 — reserved for future fast_hit gate
    expected_mae_pct: Optional[float] = None,
    regime: str = "UNKNOWN",
) -> Dict[str, Any]:
    """
    레짐 프로파일을 적용한 v3_score 계산.
    score_composer.compute_v3_score()를 내부적으로 호출하되,
    레짐별 파라미터로 가중치를 보정한다.
    """
    from modules.score_composer import compute_v3_score, _clamp

    profile = get_regime_profile(regime)

    # ── trend_quality 재계산 (레짐별 배율 적용) ──────────────
    trend_upper = str(real_trend or "").upper()
    if trend_upper == "UP":
        tq_override = float(profile["trend_up_boost"])
    elif trend_upper == "DOWN":
        tq_override = float(profile["trend_down_penalty"])
    else:
        tq_override = 1.00

    # ── volume_quality 재계산 ────────────────────────────────
    if volume_confirmed:
        vq_override = float(profile["volume_confirmed_boost"])
    elif float(vol_ratio or 1.0) >= 1.5:
        vq_override = float(profile["volume_confirmed_boost"]) * 0.95
    else:
        vq_override = 0.90

    # ── MAE 패널티 보정 ──────────────────────────────────────
    mae_scale = float(profile["mae_penalty_scale"])
    if expected_mae_pct is not None:
        penalty = _clamp(abs(float(expected_mae_pct)) / 10.0 * mae_scale, 0.0, 0.50)
        ra = 1.0 - penalty
    else:
        ra = 1.0

    # ── clean_hit_prob 가중 적용 ─────────────────────────────
    cqw = float(profile["clean_hit_weight"])   # 0~1 사이 비중 설정값
    if clean_hit_prob is not None:
        # 기본(0.65 비중)에서 레짐별 비중으로 선형 보간
        cqp = _clamp(float(clean_hit_prob) * cqw + 0.5 * (1 - cqw), 0.1, 0.99)
    else:
        cqp = _clamp(float(prob_clean or 50) / 100.0 * cqw + 0.5 * (1 - cqw), 0.1, 0.99)

    # ── 품질 소수 계산 ───────────────────────────────────────
    hit_prob_norm = _clamp(float(prob_5 or 0) / 100.0, 0.01, 0.99)
    quality_fraction = hit_prob_norm * cqp * tq_override * vq_override * ra

    MAX_QUALITY = 0.99 * 0.99 * 1.20 * 1.20 * 1.0
    v3_raw = (quality_fraction / MAX_QUALITY) * 100.0

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
        "regime": regime,
        "regime_profile": profile["description"],
        "hit_prob_norm": round(hit_prob_norm, 4),
        "clean_hit_prob_used": round(cqp, 4),
        "trend_quality": tq_override,
        "volume_quality": vq_override,
        "risk_adjustment": round(ra, 4),
        "prob5_threshold": profile["prob5_threshold"],
        "components": {
            "quality_fraction": round(quality_fraction, 4),
            "v3_raw": round(v3_raw, 2),
            "legacy_base": round(legacy_base, 2),
        },
    }


def get_prob5_threshold(regime: str, scan_mode: str = "SWING") -> float:
    """레짐 + 스캔 모드에 맞는 Top-K 진입 임계값 반환.

    INTRADAY 모드는 휴리스틱 prob_5 범위가 SWING보다 좁으므로
    별도 임계값(prob5_intraday_threshold)을 사용한다.
    """
    profile = get_regime_profile(regime)
    if str(scan_mode).upper() == "INTRADAY":
        return float(profile.get("prob5_intraday_threshold", 50.0))
    return float(profile.get("prob5_threshold", 58.0))
