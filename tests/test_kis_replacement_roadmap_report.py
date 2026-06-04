from __future__ import annotations

import json

from multi_agent.tools.report_kis_replacement_roadmap import build_report, render_markdown


def test_replacement_roadmap_report_uses_prior_readiness_and_contract(tmp_path):
    (tmp_path / "kis_operational_readiness.json").write_text(
        json.dumps(
            {
                "summary": {
                    "operational_replacement_verdict": "prior verdict",
                },
                "quote_coverage": {
                    "total_effective_quote_success_rate_pct": 100.0,
                },
                "endpoint_rollup": {
                    "ok_count": 17,
                    "failed_count": 2,
                },
            }
        ),
        encoding="utf-8",
    )

    report = build_report(tmp_path)

    assert report["summary"]["prior_readiness_verdict"] == "prior verdict"
    assert report["summary"]["endpoint_ok_count"] == 17
    assert report["implemented_now"]["production_default_changed"] is False
    assert report["replacement_gates"][0]["current_status"] == "implemented_and_unit_tested"
    assert report["roadmap"]["phases"][0]["name"] == "contract_adapter"


def test_replacement_roadmap_markdown_contains_gate_table(tmp_path):
    report = build_report(tmp_path)
    markdown = render_markdown(report)

    assert "# KIS Replacement Roadmap" in markdown
    assert "100 Percent Replacement Gates" in markdown
    assert "source_contract" in markdown
