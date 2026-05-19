from datetime import datetime, timedelta, timezone

from modules.candidate_data_quality import DATA_QUALITY_VERSION, build_candidate_data_quality


def test_candidate_data_quality_flags_missing_entry_and_current_price():
    quality = build_candidate_data_quality(
        {
            "ticker": "000660.KS",
            "price": {"volume_ratio_20d": 2.1},
            "flow": {"foreigner": 1000},
            "realized_expectancy_admission": {"policy_version": "v1"},
        }
    )

    assert quality["version"] == DATA_QUALITY_VERSION
    assert quality["display_warning_level"] == "critical"
    assert "entry_reference_price" in quality["missing_required_fields"]
    assert "current_price" in quality["missing_required_fields"]
    assert "missing:entry_reference_price" in quality["visible_warnings"]


def test_candidate_data_quality_flags_stale_flow():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    quality = build_candidate_data_quality(
        {
            "trade_plan": {"entry_reference_price": 100},
            "price": {"current_price": 101, "volume_ratio_20d": 1.4, "asof": now.isoformat()},
            "flow": {"foreigner": 1000, "asof": (now - timedelta(hours=30)).isoformat()},
            "realized_expectancy_admission": {"policy_version": "v1", "generated_at": now.isoformat()},
        },
        now=now,
    )

    assert quality["display_warning_level"] == "warning"
    assert quality["missing_required_fields"] == []
    assert quality["stale_fields"] == ["flow"]
    assert "stale:flow" in quality["visible_warnings"]


def test_candidate_data_quality_ok_when_required_fields_are_fresh():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    quality = build_candidate_data_quality(
        {
            "trade_plan": {"entry_reference_price": 100},
            "price": {"current_price": 101, "volume_ratio_20d": 1.4, "asof": now.isoformat()},
            "flow": {"foreigner": 1000, "asof": now.isoformat()},
            "realized_expectancy_admission": {"policy_version": "v1", "generated_at": now.isoformat()},
        },
        now=now,
    )

    assert quality["display_warning_level"] == "ok"
    assert quality["required_present_pct"] == 100.0
