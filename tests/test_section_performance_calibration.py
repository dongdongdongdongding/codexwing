from pathlib import Path

from modules.realized_expectancy_admission import SectionCalibration, calibration_for
from modules.section_performance_calibration import build_section_performance_calibration, write_section_performance_calibration


def test_build_section_performance_calibration_groups_market_section_metrics(tmp_path):
    report = build_section_performance_calibration(
        [
            {"ticker": "A.KS", "market": "KOSPI", "section": "Top5", "return_3d_pct": 2, "return_5d_pct": 5, "stop_before_target_5d": False},
            {"ticker": "B.KS", "market": "KOSPI", "section": "Top5", "return_3d_pct": -1, "return_5d_pct": -3, "stop_before_target_5d": True},
            {"ticker": "C.KQ", "market": "KOSDAQ", "section": "Exception Leader", "return_3d_pct": 4, "return_5d_pct": 8, "stop_before_target_5d": False},
        ],
        recent_n=2,
    )

    top = next(entry for entry in report["entries"] if entry["market"] == "KOSPI" and entry["section"] == "Top5")

    assert top["sample_n"] == 2
    assert top["return_3d"]["win_pct"] == 50.0
    assert top["return_5d"]["avg_pct"] == 1.0
    assert top["return_5d"]["avg_loss_pct"] == -3.0
    assert top["stop_first_5d_pct"] == 50.0
    assert top["confidence"] == "small_sample"


def test_calibration_for_uses_explicit_table_over_artifact_fallback():
    custom = {
        ("KOSPI", "Top5"): SectionCalibration(
            "KOSPI",
            "Top5",
            "test",
            99,
            90,
            91,
            1,
            2,
            -0.5,
            -0.8,
            -1,
            -2,
            3,
            4,
            5,
        )
    }

    calibration = calibration_for("KOSPI", "Top5", custom)

    assert calibration is not None
    assert calibration.source == "test"
    assert calibration.section_win_5d_pct == 91


def test_write_section_performance_calibration_creates_artifact(tmp_path):
    path = tmp_path / "calibration.json"
    report = build_section_performance_calibration([{"ticker": "A.KS", "section": "Top5", "return_5d_pct": 5}])

    written = write_section_performance_calibration(report, path)

    assert written == path
    assert path.exists()
