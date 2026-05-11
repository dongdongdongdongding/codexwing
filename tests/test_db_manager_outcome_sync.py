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
