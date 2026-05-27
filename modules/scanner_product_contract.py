from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


SCANNER_PRODUCT_CONTRACT_VERSION = "scanner_product_contract_v1"


@dataclass(frozen=True)
class CandidateSectionContract:
    label: str
    role: str
    production_rank_source: bool
    replaces_top5: bool
    operator_semantics: str


@dataclass(frozen=True)
class ActionLabelContract:
    label: str
    family: str
    operator_semantics: str


CANDIDATE_SECTION_CONTRACTS: Dict[str, CandidateSectionContract] = {
    "KOSPI Operating Challenger": CandidateSectionContract(
        label="KOSPI Operating Challenger",
        role="kospi_operating_challenger",
        production_rank_source=True,
        replaces_top5=True,
        operator_semantics="현재 검증 기준에서 기존 KOSPI Top5/Exception보다 우선 확인하는 운영 챌린저 섹션입니다. 원본 Top5는 아래에 남기지만, 실전 확인 순서는 이 섹션을 먼저 봅니다.",
    ),
    "KOSDAQ Operating Challenger": CandidateSectionContract(
        label="KOSDAQ Operating Challenger",
        role="kosdaq_operating_challenger",
        production_rank_source=True,
        replaces_top5=True,
        operator_semantics="현재 검증 기준에서 기존 KOSDAQ Top5/Exception보다 우선 확인하는 운영 챌린저 섹션입니다. 손실경로 리스크가 높으므로 경고와 손절 기준을 함께 확인합니다.",
    ),
    "Practical 80 Gate": CandidateSectionContract(
        label="Practical 80 Gate",
        role="validated_practical_priority",
        production_rank_source=True,
        replaces_top5=False,
        operator_semantics="Top5/Exception 후보 중 스캔 시점 피처만으로 Practical 80 Gate를 통과한 실전 우선 섹션입니다. Top5 원본 랭킹을 삭제하지 않고 최상단에 중복 없는 우선 후보로 분리합니다.",
    ),
    "Top5": CandidateSectionContract(
        label="Top5",
        role="production_priority",
        production_rank_source=True,
        replaces_top5=False,
        operator_semantics="운영 스캐너가 우선순위로 올린 주력 후보입니다. 매수 가능 여부는 액션/진입 조건으로 별도 판단합니다.",
    ),
    "Exception Leader": CandidateSectionContract(
        label="Exception Leader",
        role="momentum_exception_stream",
        production_rank_source=False,
        replaces_top5=False,
        operator_semantics="Top5 밖의 강한 모멘텀 예외 후보입니다. Top5 대체가 아니라 별도 관찰/정밀분석 대상입니다.",
    ),
    "Shadow": CandidateSectionContract(
        label="Shadow",
        role="validated_observer_group",
        production_rank_source=False,
        replaces_top5=False,
        operator_semantics="검증 중인 관찰 게이트의 묶음입니다. 운영 랭킹을 바꾸지 않고 성과를 따로 축적합니다.",
    ),
    "KOSDAQ Ordered Shadow": CandidateSectionContract(
        label="KOSDAQ Ordered Shadow",
        role="kosdaq_ordered_observer",
        production_rank_source=False,
        replaces_top5=False,
        operator_semantics="KOSDAQ ordered rebound 관찰 게이트입니다. 표시는 상단에 하되 운영 Top5 교체 후보가 아닙니다.",
    ),
    "KOSDAQ Low-loss Shadow": CandidateSectionContract(
        label="KOSDAQ Low-loss Shadow",
        role="kosdaq_low_loss_observer",
        production_rank_source=False,
        replaces_top5=False,
        operator_semantics="KOSDAQ 손실 꼬리 축소형 shadow 게이트입니다. 낮은 낙폭 특성 검증을 따로 축적합니다.",
    ),
    "KOSDAQ Theme Rank Shadow": CandidateSectionContract(
        label="KOSDAQ Theme Rank Shadow",
        role="kosdaq_theme_rank_observer",
        production_rank_source=False,
        replaces_top5=False,
        operator_semantics="KOSDAQ 동적 테마 랭크 1위권 ordered 관찰 게이트입니다. 운영 Top5를 대체하지 않고 성과를 따로 축적합니다.",
    ),
    "KOSPI Shadow": CandidateSectionContract(
        label="KOSPI Shadow",
        role="kospi_ordered_observer",
        production_rank_source=False,
        replaces_top5=False,
        operator_semantics="KOSPI ordered 관찰 게이트입니다. 운영 Top5와 분리된 실험/관찰 섹션입니다.",
    ),
    "별도 급등 레이더": CandidateSectionContract(
        label="별도 급등 레이더",
        role="next_day_surge_radar",
        production_rank_source=False,
        replaces_top5=False,
        operator_semantics="익일 급등 가능성만 별도 감시하는 shadow-only 레이더입니다. Top5/Exception을 대체하지 않습니다.",
    ),
}


ACTION_LABEL_CONTRACTS: Dict[str, ActionLabelContract] = {
    "즉시 매수 가능": ActionLabelContract(
        label="즉시 매수 가능",
        family="buyable",
        operator_semantics="품질, 상승 여력, 진입 타이밍, 손실 위험 조건이 동시에 통과한 경우의 deterministic label입니다.",
    ),
    "조건부 매수 가능": ActionLabelContract(
        label="조건부 매수 가능",
        family="buyable_with_plan",
        operator_semantics="스캐너 후보는 유효하나 표시된 Entry/TP/SL, 지지/재돌파, 수급 조건을 지켜야 하는 상태입니다.",
    ),
    "눌림 대기": ActionLabelContract(
        label="눌림 대기",
        family="wait",
        operator_semantics="종목 강도는 인정하지만 현재 가격 부담이 있어 지지 확인 이후만 검토합니다.",
    ),
    "돌파 확인": ActionLabelContract(
        label="돌파 확인",
        family="wait",
        operator_semantics="저항 돌파와 거래량 유지가 확인되기 전까지 진입 판단을 보류합니다.",
    ),
    "눌림/확인 대기": ActionLabelContract(
        label="눌림/확인 대기",
        family="wait",
        operator_semantics="UI 축약 라벨입니다. 눌림 지지 또는 재돌파 확인 전 추격을 금지한다는 뜻입니다.",
    ),
    "조건부 대기": ActionLabelContract(
        label="조건부 대기",
        family="wait",
        operator_semantics="가격, 거래량, 정책 조건 중 일부가 부족해 대기하지만 후보 자체는 계속 추적합니다.",
    ),
    "관망": ActionLabelContract(
        label="관망",
        family="observe",
        operator_semantics="방향 또는 기대 엣지가 불명확한 상태입니다. 후보를 숨기지 않고 이유와 함께 보류합니다.",
    ),
    "매수 금지": ActionLabelContract(
        label="매수 금지",
        family="blocked",
        operator_semantics="과열, 수급 이탈, 손실 위험, 특수 리스크 등 hard/soft block 조건이 확인된 상태입니다.",
    ),
    "스윙 제외": ActionLabelContract(
        label="스윙 제외",
        family="excluded",
        operator_semantics="유증, 관리/환기, 지속 적자, 감사 리스크, 임상 바이오 등 구조적으로 스윙 매매 부적합한 상태입니다.",
    ),
    "급등 분리 관찰": ActionLabelContract(
        label="급등 분리 관찰",
        family="exception_observe",
        operator_semantics="Exception Leader용 UI 라벨입니다. 소액/별도 운용과 엄격한 손절 기준을 전제로 관찰합니다.",
    ),
    "별도 급등 관찰": ActionLabelContract(
        label="별도 급등 관찰",
        family="radar_observe",
        operator_semantics="별도 급등 레이더용 라벨입니다. 검증 전 shadow-only 관찰이며 운영 매수 판단을 대체하지 않습니다.",
    ),
    "확인 필요": ActionLabelContract(
        label="확인 필요",
        family="unknown",
        operator_semantics="계약된 라벨로 충분히 분류되지 않은 경우입니다. trace와 데이터 품질을 먼저 확인해야 합니다.",
    ),
}


ACCURACY_SOURCE_CONTRACTS: Tuple[str, ...] = (
    "phase25_oos_win_rate_pct",
    "phase25_prob_clean",
    "ml_prob",
    "segment_accuracy",
    "realized_expectancy_admission",
    "section_performance_calibration",
    "post_scan_outcome_ledger",
)


REQUIRED_ENTRY_READINESS_FIELDS: Tuple[str, ...] = (
    "stock_quality_score",
    "stock_quality_grade",
    "upside_room_score",
    "upside_room_grade",
    "entry_timing_score",
    "entry_timing_grade",
    "chase_risk_level",
    "chase_risk_reasons",
    "exclusion_risk_level",
    "final_action",
    "action_reason_codes",
    "input_signals",
    "missing_fields",
    "warnings",
    "policy_version",
)


def scanner_product_contract() -> Dict[str, object]:
    return {
        "version": SCANNER_PRODUCT_CONTRACT_VERSION,
        "candidate_sections": {key: asdict(value) for key, value in CANDIDATE_SECTION_CONTRACTS.items()},
        "action_labels": {key: asdict(value) for key, value in ACTION_LABEL_CONTRACTS.items()},
        "accuracy_sources": list(ACCURACY_SOURCE_CONTRACTS),
        "required_entry_readiness_fields": list(REQUIRED_ENTRY_READINESS_FIELDS),
    }


__all__ = [
    "ACCURACY_SOURCE_CONTRACTS",
    "ACTION_LABEL_CONTRACTS",
    "CANDIDATE_SECTION_CONTRACTS",
    "REQUIRED_ENTRY_READINESS_FIELDS",
    "SCANNER_PRODUCT_CONTRACT_VERSION",
    "scanner_product_contract",
]
