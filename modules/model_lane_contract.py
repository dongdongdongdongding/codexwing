"""Carry a pick's issuance contract through persistence and every consumer."""
from __future__ import annotations

import math
from datetime import datetime


def pick_signal_date(interpretation, run_id, generated_at):
    if interpretation.get("signal_date"):
        return str(interpretation["signal_date"])[:10]
    # Legacy producers stamped UTC upload time instead of signal time. Their
    # deterministic run IDs already carry the actual signal session.
    suffix = str(run_id or "").rsplit("-", 1)[-1]
    if str(run_id).startswith(("SWING-CAND-", "KQ-ITD-3D-T5-")):
        try:
            return datetime.strptime(suffix, "%Y%m%d").date().isoformat()
        except ValueError:
            pass
    return str(generated_at or "")[:10]


def model_lane_contract(pick, bucket):
    horizon = int(pick.get("contract_h") or pick.get("hold_days") or (3 if bucket == "kospi_intraday" else 5))
    tp = float(pick.get("contract_tp") or 0.05)
    if horizon <= 0 or not math.isfinite(tp) or tp <= 0:
        raise ValueError("invalid pick contract")
    signal_date = str(pick.get("date") or pick.get("score_date") or "")[:10] or None
    if bucket == "swing_candidate":
        note = f"익일 시가 진입 · +{tp * 100:g}% 터치 익절, 미터치 시 {horizon}거래일 종가 청산"
        label = f"모델 점수 (학습 {pick.get('model_label') or 't5_5'}; 미캘리브레이션)"
    else:
        note = pick.get("hold_note") or f"{horizon}거래일 종가 보유 · 분산(타이트 손절 X)"
        label = pick.get("model_prob_label") or f"{horizon}일내 +{tp * 100:g}% 터치 모델 점수"
    return {"contract_h": horizon, "contract_tp": tp, "hold_days": horizon,
            "target_tp_pct": tp * 100, "hold_note": note,
            "model_prob_label": label, "signal_date": signal_date}
