from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List


FULL_KR_SCAN_MAX = 2000


WEB_EQUIVALENT_RESULT_FIELDS: Dict[str, List[str]] = {
    "scan_card": [
        "rank",
        "ticker",
        "stock_name",
        "decision",
        "accuracy",
        "day_change_pct",
        "loss_risk_score",
        "risk_flags",
        "final_action",
        "entry_condition_text",
        "stop_condition_text",
        "entry_policy",
        "target_tp_pct",
        "stop_sl_pct",
        "hold_days",
    ],
    "top_deep": [
        "buy_score",
        "quality.grade",
        "quality.score",
        "upside.grade",
        "upside.score",
        "timing.grade",
        "timing.score",
        "chase_risk_level",
        "final_buy_judgment.action",
        "final_buy_judgment.summary",
        "chase_filters",
        "price.current_price",
        "price.return_5d_pct",
        "price.return_20d_pct",
        "price.return_60d_pct",
        "price.pct_from_52w_high",
        "news.headlines",
    ],
    "archive": [
        "run_id",
        "market",
        "scan_mode",
        "recommended_at",
        "priority_rank",
        "decision_bucket",
        "realized_return_pct",
        "outcome_label",
        "source_ref",
    ],
}


@dataclass(frozen=True)
class DiscordCommandSpec:
    name: str
    description: str
    kind: str
    market: str = ""
    max_scan: int | None = None
    fixed_options: Dict[str, str | int] = field(default_factory=dict)
    response_style: str = "embed"
    web_equivalent_sections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


COMMAND_SPECS: Dict[str, DiscordCommandSpec] = {
    "kospi_scan": DiscordCommandSpec(
        name="kospi_scan",
        description="KOSPI 전체 스윙 스캔을 실행합니다. max_scan은 2000으로 고정됩니다.",
        kind="scan",
        market="KOSPI",
        max_scan=FULL_KR_SCAN_MAX,
        fixed_options={"scan_mode": "SWING", "profile": "prod"},
        response_style="deferred_embed_with_detail_buttons",
        web_equivalent_sections=["scan_card", "top_deep", "archive"],
    ),
    "kosdaq_scan": DiscordCommandSpec(
        name="kosdaq_scan",
        description="KOSDAQ 전체 스윙 스캔을 실행합니다. max_scan은 2000으로 고정됩니다.",
        kind="scan",
        market="KOSDAQ",
        max_scan=FULL_KR_SCAN_MAX,
        fixed_options={"scan_mode": "SWING", "profile": "prod"},
        response_style="deferred_embed_with_detail_buttons",
        web_equivalent_sections=["scan_card", "top_deep", "archive"],
    ),
    "macro_refresh": DiscordCommandSpec(
        name="macro_refresh",
        description="매크로/마켓 게이트 컨텍스트를 새로고침하고 요약을 표시합니다.",
        kind="macro_refresh",
        response_style="embed",
        web_equivalent_sections=["scan_card"],
    ),
    "top_deep": DiscordCommandSpec(
        name="top_deep",
        description="최근 자동 정밀분석 이력과 종목별 상세 매수 판단을 조회합니다.",
        kind="top_deep_lookup",
        response_style="embed_with_select_menu",
        web_equivalent_sections=["top_deep"],
    ),
    "archive": DiscordCommandSpec(
        name="archive",
        description="최근 스캔 아카이브와 realized outcome 상태를 조회합니다.",
        kind="archive_lookup",
        response_style="embed_with_csv_or_link",
        web_equivalent_sections=["archive", "scan_card"],
    ),
    "status": DiscordCommandSpec(
        name="status",
        description="Discord 연동 설정, 최근 Run, 서버 상태를 확인합니다.",
        kind="status",
        response_style="embed",
        web_equivalent_sections=[],
    ),
}


def command_contract() -> Dict[str, object]:
    return {
        "full_kr_scan_max": FULL_KR_SCAN_MAX,
        "commands": {name: spec.to_dict() for name, spec in COMMAND_SPECS.items()},
        "web_equivalent_result_fields": WEB_EQUIVALENT_RESULT_FIELDS,
    }


__all__ = [
    "COMMAND_SPECS",
    "DiscordCommandSpec",
    "FULL_KR_SCAN_MAX",
    "WEB_EQUIVALENT_RESULT_FIELDS",
    "command_contract",
]
