from __future__ import annotations

from typing import Dict


METRIC_LABELS: Dict[str, str] = {
    "buy_score": "스캐너 점수",
    "cohort_win_5d": "모델 검증 5D승률",
    "day_change": "당일 등락률",
    "loss_risk_score": "손실위험 점수",
    "news_sentiment": "뉴스 감성",
    "expected_net_return_3d": "예상 순수익 3D",
    "candidate_pass_prob_5d": "후보 통과확률",
    "validation_avg_return_5d": "검증 평균 5D수익",
    "validation_worst_return_5d": "검증 최저 5D수익",
    "model_rank": "모델 순위",
    "candidate_model_score_5d": "후보 모델점수",
    "stop_first_risk_5d": "Stop-first 5D",
    "raw_score": "원본 스캔점수",
    "relative_rank": "플래너 상대순위",
    "expected_edge": "기대엣지",
}


METRIC_HELP: Dict[str, str] = {
    "buy_score": (
        "스캐너/플래너가 후보를 정렬할 때 쓰는 내부 점수입니다. "
        "Admission 모델 확률이나 실제 수익률 보장은 아닙니다."
    ),
    "cohort_win_5d": (
        "후보 개별 확률이 아니라 현재 시장의 Admission 모델 선택규칙을 과거 실전 데이터에 적용했을 때의 "
        "5거래일 승률입니다. 같은 시장/같은 모델이면 여러 종목에 같은 값이 표시될 수 있습니다."
    ),
    "day_change": "스캔 기준 시점의 당일 가격 등락률입니다. 이미 급등한 후보인지 확인하는 용도입니다.",
    "loss_risk_score": (
        "가격 과열, 손실 경로, stop-first 비율 등 하락 리스크를 점수화한 값입니다. "
        "높을수록 진입 전 확인이 더 필요합니다."
    ),
    "news_sentiment": "뉴스/텍스트 기반 분위기 점수입니다. 없거나 낮은 경우 가격·수급 지표를 더 우선합니다.",
    "expected_net_return_3d": "거래 비용 모델을 반영한 3거래일 예상 순수익입니다. 음수면 단기 기대값이 약하다는 뜻입니다.",
    "candidate_pass_prob_5d": (
        "현재 후보의 피처를 Admission 모델에 넣어 계산한 후보별 확률입니다. "
        "운영 기준을 넘으면 Admission 통과, 못 넘으면 Near Miss로 표시됩니다."
    ),
    "validation_avg_return_5d": (
        "후보별 예상 수익이 아니라 현재 Admission 모델 선택규칙의 과거 검증 표본에서 나온 평균 5거래일 수익률입니다."
    ),
    "validation_worst_return_5d": (
        "후보별 손절 예상치가 아니라 현재 Admission 모델 선택규칙의 과거 검증 표본에서 가장 나빴던 5거래일 수익률입니다."
    ),
    "model_rank": "이번 스캔 후보를 Admission 모델 확률순으로 정렬한 순위입니다.",
    "candidate_model_score_5d": (
        "현재 Admission 경로에서는 후보 통과확률과 같은 값입니다. 과거 보고서 호환을 위해 별도 점수 필드로도 저장합니다."
    ),
    "stop_first_risk_5d": (
        "검증 표본에서 목표 수익보다 손절 조건이 먼저 발생한 비율입니다. 낮을수록 경로 품질이 좋습니다."
    ),
    "raw_score": "원래 스캐너가 산출한 강도 점수입니다. 좋은 종목 여부에 가깝고 진입 가능성 자체는 별도 판단합니다.",
    "relative_rank": (
        "플래너가 같은 스캔 후보 안에서 상대적으로 얼마나 우선순위를 줬는지 나타내는 점수입니다. "
        "Admission 모델 확률과는 다른 값입니다."
    ),
    "expected_edge": "예상 수익과 손실위험을 함께 본 단기 엣지 점수입니다. 음수면 즉시 진입 논리가 약합니다.",
}


def metric_label(key: str) -> str:
    return METRIC_LABELS.get(str(key), str(key))


def metric_help(key: str) -> str:
    return METRIC_HELP.get(str(key), "")


__all__ = ["METRIC_HELP", "METRIC_LABELS", "metric_help", "metric_label"]
