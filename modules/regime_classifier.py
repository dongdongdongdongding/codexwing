"""
regime_classifier.py
────────────────────────────────────────────────────────────
5-class 시장 레짐 분류기.

레짐:
  BULL            : 지수 상승 추세 + 변동성 낮음
  BEAR            : 지수 하락 추세 + 공포 지표 높음
  SIDEWAYS        : 방향 없는 횡보 + 거래량 감소
  HIGH_VOL        : 급등락 반복, VIX 높음, 방향 불명
  THEME_EXPANSION : 지수는 횡보 또는 소폭 상승이지만 테마/섹터 강한 확산

활용:
  - 같은 종목 패턴도 레짐에 따라 성공률이 다름
  - Regime Classifier 결과 → model routing (swing-main-0c7)
  - 스코어 조정, 임계값 변경, 포지션 사이즈 조정 근거

설계 원칙:
  - 규칙 기반 (rule-based) 으로 우선 구현 → 훈련 데이터 쌓으면 ML로 전환
  - 외부 API 없이 yfinance 데이터만으로 동작
  - 모듈 단독 실행 가능, 캐시 지원
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_log = logging.getLogger(__name__)

_CACHE_PATH = Path("runtime_state") / "long_term" / "context_cache" / "regime_classifier.json"
_CACHE_TTL_HOURS = 4.0

# 레짐별 스코어 조정 (score_composer.py v3_score에 곱셈 적용)
REGIME_MULTIPLIERS: Dict[str, float] = {
    "BULL":            1.10,   # 추세 장 → 공격적
    "THEME_EXPANSION": 1.05,   # 테마 확산 → 테마 종목에 유리
    "SIDEWAYS":        1.00,   # 중립
    "HIGH_VOL":        0.85,   # 변동성 장 → 보수적
    "BEAR":            0.70,   # 하락 장 → 매우 보수적
    "UNKNOWN":         1.00,
}


def _cache_load() -> Optional[Dict[str, Any]]:
    try:
        if not _CACHE_PATH.exists():
            return None
        payload = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        ts_str = payload.get("classified_at", "")
        if ts_str:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
            if age_h < _CACHE_TTL_HOURS:
                return payload
    except Exception:
        pass
    return None


def _cache_save(payload: Dict[str, Any]) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        _log.debug("regime_classifier: cache save failed: %s", exc)


def _fetch_index_data(market: str = "KR") -> Optional[Any]:
    """인덱스 OHLCV 데이터 반환 (pandas DataFrame)."""
    try:
        import yfinance as yf
        ticker_map = {
            "KR": "^KS11", "KOSPI": "^KS11", "KOSDAQ": "^KQ11",
            "US": "^GSPC", "NASDAQ": "^IXIC", "AMEX": "^XAX",
        }
        symbol = ticker_map.get(str(market).upper(), "^KS11")
        obj = yf.Ticker(symbol)
        hist = obj.history(period="6mo", interval="1d")
        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)
        return hist if not hist.empty else None
    except Exception:
        return None


def _fetch_vix() -> float:
    """VIX 최신값 반환. 실패 시 20.0 (중립) 반환."""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="5d", interval="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return 20.0


def classify_regime(market: str = "KR", force_refresh: bool = False) -> Dict[str, Any]:
    """
    시장 레짐을 분류해 반환한다.

    Returns:
        {
            "regime": str,           # BULL / BEAR / SIDEWAYS / HIGH_VOL / THEME_EXPANSION
            "confidence": float,     # 0~1
            "multiplier": float,     # 이 레짐에서 권장 score 보정 배수
            "signals": dict,         # 분류 근거
            "classified_at": str,
        }
    """
    if not force_refresh:
        cached = _cache_load()
        if cached and cached.get("market") == market:
            return cached

    signals: Dict[str, Any] = {}
    regime = "UNKNOWN"
    confidence = 0.5

    try:
        hist = _fetch_index_data(market)
        vix = _fetch_vix()
        signals["vix"] = round(vix, 2)

        if hist is None or len(hist) < 50:
            regime = "UNKNOWN"
            confidence = 0.3
        else:
            import pandas as pd
            close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
            volume = pd.to_numeric(hist["Volume"], errors="coerce").dropna()

            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma50 = float(close.rolling(50).mean().iloc[-1])
            current = float(close.iloc[-1])

            # 20일 변동성 (일간 수익률 표준편차 %)
            returns = close.pct_change().dropna()
            vol_20d = float(returns.tail(20).std() * 100)

            # 거래량 추세 (최근 5일 / 20일 평균 비율)
            vol_ratio = float(volume.tail(5).mean() / volume.tail(20).mean()) if len(volume) >= 20 else 1.0

            # 최근 20일 수익률
            ret_20d = float((current - float(close.iloc[-20])) / float(close.iloc[-20]) * 100) if len(close) >= 20 else 0.0

            signals.update({
                "current": round(current, 2),
                "ma20": round(ma20, 2),
                "ma50": round(ma50, 2),
                "vol_20d_pct": round(vol_20d, 3),
                "volume_ratio_5d_20d": round(vol_ratio, 3),
                "ret_20d_pct": round(ret_20d, 2),
            })

            # ── 분류 로직 ────────────────────────────────────
            is_uptrend    = current > ma20 > ma50
            is_downtrend  = current < ma20 < ma50
            is_high_vix   = vix > 25
            is_low_vix    = vix < 15
            is_high_vol   = vol_20d > 1.5   # 일간 변동성 1.5% 이상
            is_vol_shrink = vol_ratio < 0.8  # 거래량 감소

            if is_downtrend and (is_high_vix or vix > 22):
                regime = "BEAR"
                confidence = 0.85 if is_high_vix else 0.70

            elif is_high_vol and not is_uptrend:
                # 방향 없는 급등락
                regime = "HIGH_VOL"
                confidence = 0.75

            elif is_uptrend and is_low_vix:
                regime = "BULL"
                confidence = 0.85

            elif is_uptrend and not is_high_vix:
                # 지수는 오르는데 VIX 중간 → 테마 확산 가능성
                if ret_20d < 3.0 and not is_vol_shrink:
                    regime = "THEME_EXPANSION"
                    confidence = 0.65
                else:
                    regime = "BULL"
                    confidence = 0.70

            elif is_vol_shrink and abs(ret_20d) < 2.0:
                regime = "SIDEWAYS"
                confidence = 0.75

            else:
                # 애매한 중간 상태
                regime = "SIDEWAYS"
                confidence = 0.50

    except Exception as exc:
        _log.warning("regime_classifier: 분류 실패: %s", exc)
        regime = "UNKNOWN"
        confidence = 0.3

    result: Dict[str, Any] = {
        "market": market,
        "regime": regime,
        "confidence": round(confidence, 3),
        "multiplier": REGIME_MULTIPLIERS.get(regime, 1.0),
        "signals": signals,
        "classified_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_save(result)
    return result


def get_regime_multiplier(market: str = "KR") -> float:
    """스코어 보정 배수만 빠르게 반환. 캐시 우선."""
    try:
        result = classify_regime(market)
        return float(result.get("multiplier", 1.0))
    except Exception:
        return 1.0


if __name__ == "__main__":
    import sys
    mkt = sys.argv[1] if len(sys.argv) > 1 else "KR"
    res = classify_regime(mkt, force_refresh=True)
    print(f"\n레짐: {res['regime']}  신뢰도: {res['confidence']:.0%}  배수: {res['multiplier']}")
    print(f"근거: {res['signals']}")
