import json

from modules.db_manager import DBManager


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTableQuery:
    def __init__(self, rows):
        self.rows = list(rows)
        self.filters = []
        self.limit_n = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def neq(self, key, value):
        self.filters.append(("neq", key, value))
        return self

    def is_(self, key, value):
        self.filters.append(("is", key, value))
        return self

    def gte(self, key, value):
        self.filters.append(("gte", key, value))
        return self

    def lte(self, key, value):
        self.filters.append(("lte", key, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def execute(self):
        rows = self.rows
        for op, key, value in self.filters:
            if op == "eq":
                rows = [r for r in rows if r.get(key) == value]
            elif op == "neq":
                rows = [r for r in rows if r.get(key) != value]
            elif op == "is":
                rows = [r for r in rows if r.get(key) is None and value == "null"]
            elif op == "gte":
                rows = [r for r in rows if str(r.get(key) or "") >= value]
            elif op == "lte":
                rows = [r for r in rows if str(r.get(key) or "") <= value]
        if self.limit_n is not None:
            rows = rows[: self.limit_n]
        return _FakeResponse(rows)


class _FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "market_scan_results"
        return _FakeTableQuery(self.rows)


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


def test_merge_non_empty_payload_recomputes_stale_quality_metadata():
    db = DBManager.__new__(DBManager)
    merged = db._merge_non_empty_payload(
        {
            "alpha_score": 82,
            "tech_score": 74,
            "ml_prob": 0.71,
            "whale_score": 63,
            "trend": "UP",
            "volume_ratio": 2.4,
            "position": "BREAKOUT",
            "tier": "A",
            "decision_score": 7.2,
            "entry_reference_price": 51200.0,
            "feature_origin": "scanner_full",
            "feature_quality": "complete",
            "feature_missing_fields": [],
            "validation_excluded": False,
            "validation_excluded_reason": None,
        },
        {
            "feature_origin": "outcome_sync_partial",
            "return_5d_pct": 6.2,
            "feature_quality": "incomplete",
            "feature_completeness": 0.5,
            "feature_missing_fields": ["tech_score", "volume_ratio", "position", "tier"],
            "validation_excluded": True,
            "validation_excluded_reason": "FEATURE_MISSING:tech_score,volume_ratio,position,tier",
        },
    )

    assert merged["feature_origin"] == "scanner_full"
    assert merged["return_5d_pct"] == 6.2
    assert merged["feature_quality"] == "complete"
    assert merged["feature_completeness"] == 1.0
    assert merged["feature_missing_fields"] == []
    assert merged["validation_excluded"] is False
    assert merged["validation_excluded_reason"] is None


def test_incomplete_live_scan_result_is_quarantined_not_saved(tmp_path, monkeypatch):
    db = DBManager.__new__(DBManager)
    quarantine_path = tmp_path / "scan_feature_quarantine.jsonl"
    monkeypatch.setenv("AG_SCAN_FEATURE_QUARANTINE_PATH", str(quarantine_path))
    monkeypatch.setenv("AG_STRICT_SCAN_QUALITY_GATE", "1")
    data = {
        "ticker": "005930.KS",
        "name": "Samsung",
        "market": "KOSPI",
        "market_type": "KR",
        "scan_mode": "SWING",
        "alpha_score": 82,
        "ml_prob": 61.0,
        "decision": "PRIORITY_WATCHLIST",
        "decision_bucket": "watchlist",
        "run_id": "RUN-QUALITY-GATE",
    }
    quality = db._feature_quality_payload(data, origin="scanner_full")

    assert db._should_block_incomplete_scan_result(data, quality) is True
    row = db._write_scan_feature_quarantine(data, quality, "KOSPI", "2026-05-12T13:00:00+00:00")

    assert "tech_score" in row["feature_missing_fields"]
    assert "volume_ratio" in row["feature_missing_fields"]
    saved = json.loads(quarantine_path.read_text(encoding="utf-8").strip())
    assert saved["ticker"] == "005930.KS"
    assert saved["validation_excluded_reason"].startswith("FEATURE_MISSING:")


def test_quality_gate_allows_outcome_sync_partial_rows(monkeypatch):
    db = DBManager.__new__(DBManager)
    monkeypatch.setenv("AG_STRICT_SCAN_QUALITY_GATE", "1")
    data = {
        "ticker": "005930.KS",
        "feature_origin": "outcome_sync_partial",
        "return_5d_pct": 6.2,
    }
    quality = db._feature_quality_payload(data, origin="outcome_sync_partial")

    assert quality["validation_excluded"] is True
    assert db._should_block_incomplete_scan_result(data, quality) is False


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
            "relative_rank_model": "kosdaq_floor_win_relative_v5",
        },
    ]

    assert db._choose_authoritative_scan_row(rows)["id"] == "planner"


def test_merge_non_empty_payload_preserves_existing_rank_when_raw_has_none():
    db = DBManager.__new__(DBManager)
    merged = db._merge_non_empty_payload(
        {
            "id": "planner",
            "relative_rank_model": "kosdaq_floor_win_relative_v5",
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

    assert merged["relative_rank_model"] == "kosdaq_floor_win_relative_v5"
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


def test_merge_non_empty_payload_clears_rank_for_planner_hard_risk_observe():
    db = DBManager.__new__(DBManager)
    merged = db._merge_non_empty_payload(
        {
            "priority_rank": 18,
            "decision_bucket": "watchlist",
            "decision": "OBSERVE",
            "relative_rank_model": "kospi_floor_win_relative_v2",
        },
        {
            "priority_rank": None,
            "decision_bucket": "watchlist",
            "decision": "OBSERVE",
            "relative_rank_model": "kospi_floor_win_relative_v2",
            "loss_risk_score": 98.618,
        },
    )

    assert merged["priority_rank"] is None
    assert merged["decision_bucket"] == "watchlist"
    assert merged["relative_rank_model"] == "kospi_floor_win_relative_v2"


def test_merge_non_empty_payload_clears_stale_relative_rank_for_exception_leader():
    db = DBManager.__new__(DBManager)
    merged = db._merge_non_empty_payload(
        {
            "priority_rank": 2,
            "decision_bucket": "exception_leader",
            "decision": "EXCEPTION_LEADER",
            "relative_rank_model": "kosdaq_floor_upside_relative_v3",
            "relative_rank_score": 45.0,
            "relative_rank_pct": 0.2,
            "regime_adjusted_grade": "RELATIVE_WATCHLIST",
        },
        {
            "priority_rank": 2,
            "decision_bucket": "exception_leader",
            "decision": "EXCEPTION_LEADER",
            "relative_rank_model": None,
            "relative_rank_score": None,
            "relative_rank_pct": None,
            "regime_adjusted_grade": None,
        },
    )

    assert merged["priority_rank"] == 2
    assert merged["relative_rank_model"] is None
    assert merged["relative_rank_score"] is None
    assert merged["relative_rank_pct"] is None
    assert merged["regime_adjusted_grade"] is None


def test_find_scan_result_conflict_row_is_run_scoped_for_repeated_same_day_ticker():
    db = DBManager.__new__(DBManager)
    db.client = _FakeClient(
        [
            {
                "id": "old-run",
                "run_id": "RUN-OLD",
                "ticker": "005930.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "recommended_at": "2026-05-13T01:00:00+00:00",
                "created_at": "2026-05-13T01:00:00+00:00",
                "priority_rank": 1,
            },
            {
                "id": "same-run",
                "run_id": "RUN-NEW",
                "ticker": "005930.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "recommended_at": "2026-05-13T02:00:00+00:00",
                "created_at": "2026-05-13T02:00:00+00:00",
                "priority_rank": 2,
            },
        ]
    )

    conflict = db._find_scan_result_conflict_row(
        {
            "run_id": "RUN-NEW",
            "ticker": "005930.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "recommended_at": "2026-05-13T03:00:00+00:00",
        }
    )

    assert conflict["id"] == "same-run"


def test_find_scan_result_conflict_row_does_not_merge_different_run():
    db = DBManager.__new__(DBManager)
    db.client = _FakeClient(
        [
            {
                "id": "old-run",
                "run_id": "RUN-OLD",
                "ticker": "005930.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "recommended_at": "2026-05-13T01:00:00+00:00",
                "created_at": "2026-05-13T01:00:00+00:00",
                "priority_rank": 1,
            }
        ]
    )

    conflict = db._find_scan_result_conflict_row(
        {
            "run_id": "RUN-NEW",
            "ticker": "005930.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "recommended_at": "2026-05-13T03:00:00+00:00",
        }
    )

    assert conflict is None


def test_find_scan_result_conflict_row_keeps_legacy_null_run_guard():
    db = DBManager.__new__(DBManager)
    db.client = _FakeClient(
        [
            {
                "id": "legacy",
                "run_id": None,
                "ticker": "005930.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "recommended_at": "2026-05-13T01:00:00+00:00",
                "created_at": "2026-05-13T01:00:00+00:00",
                "priority_rank": None,
            },
            {
                "id": "old-run",
                "run_id": "RUN-OLD",
                "ticker": "005930.KS",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "recommended_at": "2026-05-13T01:00:00+00:00",
                "created_at": "2026-05-13T01:00:00+00:00",
                "priority_rank": 1,
            },
        ]
    )

    conflict = db._find_scan_result_conflict_row(
        {
            "ticker": "005930.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "recommended_at": "2026-05-13T03:00:00+00:00",
        }
    )

    assert conflict["id"] == "legacy"
