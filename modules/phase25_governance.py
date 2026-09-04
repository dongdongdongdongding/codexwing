"""phase25 모델 번들의 출하 자격 판정 — 단일 지점.

두 게이트가 있고 방향이 반대다:
  · `phase25_oos_validates`   = **승격** 게이트. `uncertain` 모델을 `normal` 로 올린다.
  · `phase25_weak_oos_reasons`= **중립화** 게이트. 약한 모델의 기여를 50으로 죽인다.

2026-09-03 (FINDING_2026-09-03_serving_models_stale.md) — 이 모듈은 **한 번도 발동한 적이 없었다.**

  실제로 서빙되던 번들(`phase25_kr_swing_logistic`, `phase25_kr_intraday_xgboost`)에는
  `oos_auc`/`oos_win_rate_pct`/`oos_avg_return_pct` 도 `signal_direction` 도 **아예 없었다.**
  `None` 이 들어오면 `if auc is not None and auc < ...` 가 통째로 건너뛰어져
  `weak_reasons` 가 빈 리스트가 되고 → **중립화가 안 걸린다.** 방향도 `.get(...,"normal")`
  기본값으로 떨어져 뒤집기가 불가능했다. 즉 **없는 값이 「보류」가 아니라 「통과」로 떨어졌다.**
  발동 대상은 메타데이터를 가진 세그먼트 번들뿐이었는데 그건 최후 폴백이라 선택되지 않았다.

  같은 시기 실측: INTRADAY 통합 라인이 shadow 에서 −13.2pp (p=3.3e-03) 로 뒤집혀 있었고
  서빙 모델 auc 는 **0.478 — 무작위 미만**이었다. 잡을 장치가 구조적으로 꺼져 있었다.

  → 지금은 **fail-closed** 다. 메타데이터가 없으면 판정을 보류하고 중립화한다
    (`modules/stream_exclusion.py` 가 게이트 리더에서 같은 방향으로 고친 것과 같은 계열이다).

또 하나: **분모를 아무도 안 적었다.** 세 트레이너 전부 홀드아웃 픽 수(`picks`)를 계산해놓고
payload 에서 버렸다. 그래서 승률 78%가 19건 중 15건이어도 승격 게이트를 통과했다.
[H1] 실측: `oos_picks` 가 시드만 바꿔 19↔266 으로 흔들린다. 이제 `oos_n` 을 요구한다.
"""
from __future__ import annotations

import math
import os
from typing import Any, List, Optional


OOS_VALIDATE_MIN_AUC = 0.55
OOS_VALIDATE_MIN_WIN_RATE_PCT = 70.0
OOS_VALIDATE_MIN_AVG_RETURN_PCT = 5.0

# 승격 게이트의 분모 하한. 임의값이 아니라 **이 게이트가 주장하는 크기에서 유도**한다:
# 승률 70%(기준선 ~50%)를 2σ 로 가르려면 2·sqrt(0.25/n) < 0.20 → n > 25.
# 여유를 둬 30 으로 한다. 이보다 적으면 「승격할 만큼 봤다」고 말할 수 없다.
OOS_VALIDATE_MIN_PICKS = 30

# 2026-09-04 운영자 결정: 중립화는 **리프트**로 판정한다(기준선이 있을 때).
#
# 근거: `phase25_prob` 은 매매 결정이 아니라 **순위 기울기**다. 순위에 필요한 것은
# 판별력이고, 절대 시장 방향은 이미 시장약세 게이트가 본다 — 절대 수익으로 또 거르면
# 같은 것을 두 번 센다. 실측이 그 차이를 드러냈다(2026-09-03, 정직 분할 70/15/15):
#   SWING    기준선 win 34.7% / −4.33%  →  픽 42.3% / −1.76%  =  **리프트 +7.6pp / +2.21pp**
#   INTRADAY 기준선 win 37.6% / −0.88%  →  픽 37.9% / −0.86%  =  **리프트 +0.3pp / +0.02pp**
# 절대 임계값만 보면 **둘 다 탈락**이라 「판별하는 모델」과 「기준선을 복제하는 모델」이
# 구분되지 않았다. 구분되지 않으면 게이트가 정보를 안 주는 것과 같다(규율 16: 자를 맞춰라).
#
# 리프트 하한은 **표본에서 유도한다** — 승률 리프트는 표준오차 1개분을 넘어야 한다.
# 0 초과만 요구하면 잡음이 절반은 통과한다. n=527 이면 1SE=2.2pp(SWING +7.6 통과),
# n=2079 이면 1SE=1.1pp(INTRADAY +0.3 탈락).
OOS_LIFT_WIN_SE_MULT = 1.0

# 기준선이 없는 번들은 옛 절대 기준으로 판정한다(하위호환 — 리프트를 못 재면 느슨해지면 안 된다).
WEAK_OOS_MIN_AUC = 0.50
WEAK_OOS_MIN_WIN_RATE_PCT = 60.0
WEAK_OOS_MIN_AVG_RETURN_PCT = 0.0

# 번들이 반드시 실어야 하는 판정 필드. 하나라도 없으면 출하 자격을 판정할 수 없다.
REQUIRED_OOS_FIELDS = ("oos_auc", "oos_win_rate_pct", "oos_avg_return_pct", "oos_n")

# 방향 판정 회색지대 (retrain_ml.py:1050-1075 에서 이관 — 원문 규칙 그대로다).
DIRECTION_INVERT_BELOW = 0.45
DIRECTION_NORMAL_ABOVE = 0.55


def require_oos_metadata() -> bool:
    """롤백 스위치. 기본 ON(fail-closed).

    `AG_PHASE25_REQUIRE_OOS_META=0` 으로 2026-09-03 이전 동작(메타데이터 부재 = 통과)으로
    되돌린다. 되돌리면 **판정 불가 모델이 조용히 출하된다** — 임시 조치로만 써라.
    """
    return os.environ.get("AG_PHASE25_REQUIRE_OOS_META", "1").strip() not in ("0", "", "false", "False")


def phase25_signal_direction(raw_auc: Any, cv_median_auc: Any) -> str:
    """`normal` / `invert` / `uncertain` 판정 — **세 트레이너의 단일 자**.

    retrain_ml.py 안에만 있던 규칙을 그대로 옮긴 것이다. 원문 주석의 근거:
      2026-04-26 KOSDAQ INTRADAY 가 raw_auc 0.274 / cv_median 0.579 인데 `normal` 로
      분류돼 운영 AVOID 로 4월 726행을 차단했고, forward 는 win 78% 로 **정확히 inverted**였다.
      두 지표가 크게 갈리면 모델 자체가 불안정하므로 **둘 다** 0.55 를 넘어야 `normal`,
      하나라도 0.45 미만이면 `invert`, 나머지는 `uncertain`.

    `evaluate_kr_{swing,intraday}_models.py` 는 이 판정을 아예 안 해서 `signal_direction`
    없는 번들을 만들었고, 그게 위 fail-open 의 절반이었다.
    """
    raw = _float_or_none(raw_auc)
    if raw is None:
        return "uncertain"
    cv = _float_or_none(cv_median_auc)
    min_auc = raw if cv is None else min(raw, cv)
    if min_auc < DIRECTION_INVERT_BELOW:
        return "invert"
    if min_auc > DIRECTION_NORMAL_ABOVE:
        return "normal"
    return "uncertain"


def phase25_missing_oos_fields(bundle: Any) -> List[str]:
    """번들에서 빠진 판정 필드. 진단·경보용이며 판정 자체는 아래 두 함수가 한다."""
    if not isinstance(bundle, dict):
        return list(REQUIRED_OOS_FIELDS)
    missing = [f for f in REQUIRED_OOS_FIELDS if _float_or_none(bundle.get(f)) is None]
    if not str(bundle.get("signal_direction") or "").strip():
        missing.append("signal_direction")
    return missing


def phase25_oos_validates(
    *,
    oos_auc: Any,
    oos_win_rate_pct: Any,
    oos_avg_return_pct: Any,
    oos_n: Any = None,
) -> bool:
    """**승격** 게이트: `uncertain` → `normal`.

    2026-09-03: `oos_n` 을 요구한다. 분모 없이 승률만 보면 픽 몇 건짜리 홀드아웃이
    100% 승률로 승격을 통과한다(원 주석의 근거 자체가 「15% 홀드아웃에서 win 78%」였는데
    그 15% 가 몇 건인지는 아무도 안 적었다).
    """
    auc = _float_or_none(oos_auc)
    win = _float_or_none(oos_win_rate_pct)
    avg = _float_or_none(oos_avg_return_pct)
    n = _float_or_none(oos_n)
    if require_oos_metadata() and (n is None or n < OOS_VALIDATE_MIN_PICKS):
        return False
    return (
        auc is not None
        and auc >= OOS_VALIDATE_MIN_AUC
        and win is not None
        and win >= OOS_VALIDATE_MIN_WIN_RATE_PCT
        and avg is not None
        and avg >= OOS_VALIDATE_MIN_AVG_RETURN_PCT
    )


def phase25_weak_oos_reasons(
    *,
    oos_auc: Any,
    oos_win_rate_pct: Any,
    oos_avg_return_pct: Any,
    oos_n: Any = None,
    signal_direction: Any = None,
    oos_baseline_win_rate_pct: Any = None,
    oos_baseline_avg_return_pct: Any = None,
) -> List[str]:
    """**중립화** 게이트: 사유가 하나라도 있으면 이 모델의 기여를 50 으로 죽인다.

    2026-09-03 이전에는 값이 `None` 이면 해당 검사를 **건너뛰었다**. 그래서 메타데이터가
    통째로 없는 번들이 사유 0건으로 통과했다. 지금은 부재 자체가 사유다(fail-closed).
    """
    reasons: List[str] = []
    auc = _float_or_none(oos_auc)
    win = _float_or_none(oos_win_rate_pct)
    avg = _float_or_none(oos_avg_return_pct)
    n = _float_or_none(oos_n)

    if require_oos_metadata():
        absent = [
            name
            for name, value in (
                ("oos_auc", auc),
                ("oos_win_rate_pct", win),
                ("oos_avg_return_pct", avg),
            )
            if value is None
        ]
        # 분모는 **승격 게이트에서만** 요구한다(`phase25_oos_validates`).
        # 중립화까지 분모를 요구하면 번들을 직접 못 보는 소비자(planner_runtime 은 DB 행
        # 스냅샷을 읽는다)가 전부 걸린다. 거기에 분모를 실으려면 원장 스키마를 건드려야 하는데
        # 그건 정지점이고, 애초에 작은 표본이 위험해지는 지점은 **승격**이다 —
        # 분모를 못 보면 승격이 False 로 닫히므로 그 경로도 fail-closed 다.
        if not str(signal_direction or "").strip():
            absent.append("signal_direction")
        if absent:
            # 판정 불가 = 보류. 「값이 없다」를 「문제가 없다」로 읽지 않는다.
            reasons.append("oos_meta_missing:" + ",".join(absent))
        elif n is not None and n < OOS_VALIDATE_MIN_PICKS:
            reasons.append(f"oos_n={int(n)}<{OOS_VALIDATE_MIN_PICKS}")

    # 무작위 미만은 기준선과 무관하게 고장이다 — 리프트 판정보다 먼저 본다.
    if auc is not None and auc < WEAK_OOS_MIN_AUC:
        reasons.append(f"oos_auc={auc:.3f}<{WEAK_OOS_MIN_AUC:.2f}")

    base_win = _float_or_none(oos_baseline_win_rate_pct)
    base_ret = _float_or_none(oos_baseline_avg_return_pct)
    if base_win is not None and base_ret is not None and win is not None and avg is not None:
        lift_win = win - base_win
        lift_ret = avg - base_ret
        se_win = 100.0 * math.sqrt(0.25 / n) if n and n > 0 else None
        floor = (OOS_LIFT_WIN_SE_MULT * se_win) if se_win is not None else 0.0
        if lift_win <= floor:
            reasons.append(f"oos_lift_win={lift_win:+.1f}pp<={floor:.1f}pp(1SE,n={int(n or 0)})")
        if lift_ret <= 0:
            reasons.append(f"oos_lift_ret={lift_ret:+.2f}pp<=0")
        return reasons

    # 기준선을 못 봤다 — 옛 절대 기준으로 떨어진다.
    if win is not None and win < WEAK_OOS_MIN_WIN_RATE_PCT:
        reasons.append(f"oos_win={win:.1f}%<{WEAK_OOS_MIN_WIN_RATE_PCT:.1f}%")
    if avg is not None and avg < WEAK_OOS_MIN_AVG_RETURN_PCT:
        reasons.append(f"oos_avg={avg:.2f}%<{WEAK_OOS_MIN_AVG_RETURN_PCT:.1f}%")
    return reasons


def phase25_bundle_metadata(
    *,
    raw_auc: Any,
    cv_median_auc: Any = None,
    oos_auc: Any,
    oos_n: Any,
    oos_win_rate_pct: Any,
    oos_avg_return_pct: Any,
) -> dict:
    """번들이 실어야 할 판정 필드를 만든다 — **생산자와 소비자가 같은 이름을 쓰게 하는 지점**.

    2026-09-03 이전에는 `evaluate_kr_*_models.py` 가 같은 수치를 `benchmark_win_rate` 등
    **다른 이름**으로 저장했고, 이 모듈은 `oos_win_rate_pct` 를 찾다가 못 찾고 `None` 을 봤다.
    값이 없어서가 아니라 **어휘가 달라서** 게이트가 꺼져 있었다
    (stream_exclusion.py 의 F1 「두 소비자가 서로 다른 어휘」와 같은 실패 계열이다).
    """
    return {
        "raw_auc": _float_or_none(raw_auc),
        "cv_median_auc": _float_or_none(cv_median_auc),
        "signal_direction": phase25_signal_direction(raw_auc, cv_median_auc),
        "oos_auc": _float_or_none(oos_auc),
        "oos_n": None if _float_or_none(oos_n) is None else int(_float_or_none(oos_n)),
        "oos_win_rate_pct": _float_or_none(oos_win_rate_pct),
        "oos_avg_return_pct": _float_or_none(oos_avg_return_pct),
    }


def _float_or_none(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
    except Exception:
        pass
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out
