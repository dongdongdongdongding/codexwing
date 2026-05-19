from pathlib import Path

from modules.discord_integration.commands import command_contract
from modules.next_day_explosive_radar import build_next_day_radar_records
from modules.scanner_product_contract import (
    ACTION_LABEL_CONTRACTS,
    CANDIDATE_SECTION_CONTRACTS,
    REQUIRED_ENTRY_READINESS_FIELDS,
    SCANNER_PRODUCT_CONTRACT_VERSION,
)
from modules.ui_helpers import build_action_display, build_kr_shadow_gate_records


DOC_PATH = Path("docs/operations/SCANNER_PRODUCT_CONTRACT.md")


def test_document_mentions_all_contract_sections_and_actions():
    text = DOC_PATH.read_text(encoding="utf-8")
    assert SCANNER_PRODUCT_CONTRACT_VERSION in command_contract()["scanner_product_contract"]["version"]

    for label in CANDIDATE_SECTION_CONTRACTS:
        assert label in text
    for label in ACTION_LABEL_CONTRACTS:
        assert label in text
    for field in REQUIRED_ENTRY_READINESS_FIELDS:
        assert field in text


def test_discord_command_contract_exports_product_contract():
    contract = command_contract()["scanner_product_contract"]
    assert contract["version"] == SCANNER_PRODUCT_CONTRACT_VERSION
    assert "Top5" in contract["candidate_sections"]
    assert "Exception Leader" in contract["candidate_sections"]
    assert "조건부 매수 가능" in contract["action_labels"]
    assert "post_scan_outcome_ledger" in contract["accuracy_sources"]


def test_ui_action_display_labels_are_documented():
    rows = [
        {"decision": "PRIORITY_WATCHLIST"},
        {"decision": "WATCHLIST"},
        {"decision": "OBSERVE"},
        {"decision": "NO_BUY"},
        {"decision": "EXCEPTION_LEADER"},
        {"decision": "UNKNOWN"},
        {"decision": "BUY", "day_change_pct": 9.1},
    ]

    for row in rows:
        label = build_action_display(row)["label"]
        assert label in ACTION_LABEL_CONTRACTS


def test_shadow_and_radar_sections_are_documented():
    shadow_records = build_kr_shadow_gate_records(
        [
            {
                "ticker": "000001.KQ",
                "market": "KOSDAQ",
                "volume_ratio": 1.0,
                "trend": "DOWN",
                "selection_lane": "1d",
            },
            {
                "ticker": "000002.KQ",
                "market": "KOSDAQ",
                "tech_score": 70,
                "theme_day_avg_decision_score": 60,
                "theme_day_candidate_count": 8,
                "trend": "UP",
            },
            {
                "ticker": "000003.KS",
                "market": "KOSPI",
                "prob_clean": 40,
                "alpha_score": 70,
                "theme_day_avg_alpha": 75,
                "theme_role": "CORE_TREND",
            },
        ],
        limit=5,
    )
    emitted_sections = {row["_analysis_section"] for row in shadow_records["combined"]}
    assert emitted_sections <= set(CANDIDATE_SECTION_CONTRACTS)

    radar_records = build_next_day_radar_records(
        [
            {
                "ticker": "000004.KQ",
                "market": "KOSDAQ",
                "alpha_score": 95,
                "volume_ratio": 3.0,
                "day_change_pct": 2.0,
                "phase25_prob_clean": 70,
                "technical_score": 85,
                "risk_score": 10,
            }
        ],
        limit=1,
    )
    assert radar_records[0]["_analysis_section"] in CANDIDATE_SECTION_CONTRACTS
    assert radar_records[0]["final_action"] in ACTION_LABEL_CONTRACTS
