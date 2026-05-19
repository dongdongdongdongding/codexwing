import json

from multi_agent.tools.report_structural_exclusion_risk import _load_rows, render_markdown
from modules.structural_exclusion_risk import summarize_structural_exclusion_risks


def test_structural_exclusion_report_loads_top_deep_rows(tmp_path):
    report_dir = tmp_path / "top_deep"
    report_dir.mkdir()
    (report_dir / "RUN-1.json").write_text(
        json.dumps(
            [
                {"structural_exclusion_risk": {"risk_level": "exclude", "reason_codes": ["RIGHTS_OFFERING"]}},
                {"structural_exclusion_risk": {"risk_level": "low", "reason_codes": []}},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rows = _load_rows(report_dir, limit_runs=10)
    report = summarize_structural_exclusion_risks(rows)
    markdown = render_markdown(report)

    assert report["rows"] == 2
    assert report["level_counts"]["exclude"] == 1
    assert report["reason_counts"]["RIGHTS_OFFERING"] == 1
    assert "Structural Exclusion Risk Report" in markdown
