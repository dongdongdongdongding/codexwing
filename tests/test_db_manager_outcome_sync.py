from modules.db_manager import DBManager


def test_choose_feature_rich_peer_prefers_scanner_full_over_stub():
    db = DBManager.__new__(DBManager)
    rows = [
        {
            "id": "stub",
            "feature_origin": "outcome_sync_partial",
            "alpha_score": None,
            "created_at": "2026-05-10T09:00:00",
        },
        {
            "id": "scanner",
            "feature_origin": "scanner_full",
            "alpha_score": 82,
            "created_at": "2026-05-10T08:59:00",
        },
    ]

    assert db._choose_feature_rich_peer(rows)["id"] == "scanner"


def test_merge_non_empty_payload_preserves_existing_features():
    db = DBManager.__new__(DBManager)
    merged = db._merge_non_empty_payload(
        {
            "alpha_score": 82,
            "feature_origin": "scanner_full",
            "return_5d_pct": None,
            "decision": "PRIORITY_WATCHLIST",
        },
        {
            "alpha_score": None,
            "feature_origin": "outcome_sync_partial",
            "return_5d_pct": 6.2,
            "decision": "",
            "outcome_status": "RESOLVED",
        },
    )

    assert merged["alpha_score"] == 82
    assert merged["feature_origin"] == "scanner_full"
    assert merged["return_5d_pct"] == 6.2
    assert merged["decision"] == "PRIORITY_WATCHLIST"
    assert merged["outcome_status"] == "RESOLVED"


def test_authoritative_row_prefers_planner_telemetry_over_newer_raw_row():
    db = DBManager.__new__(DBManager)
    rows = [
        {
            "id": "raw",
            "feature_origin": "scanner_full",
            "alpha_score": 89,
            "created_at": "2026-05-11T14:50:37+00:00",
            "recommended_at": None,
            "priority_rank": None,
            "decision_bucket": None,
            "relative_rank_model": None,
        },
        {
            "id": "planner",
            "feature_origin": "scanner_full",
            "alpha_score": 89,
            "created_at": "2026-05-11T05:50:42+00:00",
            "recommended_at": "2026-05-11T05:50:42+00:00",
            "priority_rank": 1,
            "decision_bucket": "picked",
            "relative_rank_model": "kosdaq_floor_upside_relative_v3",
        },
    ]

    assert db._choose_authoritative_scan_row(rows)["id"] == "planner"


def test_merge_non_empty_payload_preserves_existing_rank_when_raw_has_none():
    db = DBManager.__new__(DBManager)
    merged = db._merge_non_empty_payload(
        {
            "id": "planner",
            "relative_rank_model": "kosdaq_floor_upside_relative_v3",
            "relative_rank_score": 54.7,
            "priority_rank": 1,
            "decision_bucket": "picked",
            "alpha_score": 69,
        },
        {
            "relative_rank_model": None,
            "relative_rank_score": None,
            "priority_rank": None,
            "decision_bucket": None,
            "alpha_score": 70,
            "volume_ratio": 2.1,
        },
    )

    assert merged["relative_rank_model"] == "kosdaq_floor_upside_relative_v3"
    assert merged["relative_rank_score"] == 54.7
    assert merged["priority_rank"] == 1
    assert merged["decision_bucket"] == "picked"
    assert merged["alpha_score"] == 70
    assert merged["volume_ratio"] == 2.1


def test_merge_non_empty_payload_clears_rank_zero_to_none_for_ignored():
    db = DBManager.__new__(DBManager)
    merged = db._merge_non_empty_payload(
        {
            "priority_rank": 0,
            "decision_bucket": "ignored",
        },
        {
            "priority_rank": None,
            "decision_bucket": "ignored",
        },
    )

    assert merged["priority_rank"] is None
