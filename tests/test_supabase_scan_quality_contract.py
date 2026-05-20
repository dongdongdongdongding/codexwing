from multi_agent.tools.report_supabase_scan_quality import FEATURE_COVERAGE_COLUMNS, REQUIRED_SCAN_COLUMNS


def test_supabase_scan_quality_tracks_multi_window_kr_flow():
    required = set(REQUIRED_SCAN_COLUMNS)
    coverage = set(FEATURE_COVERAGE_COLUMNS)
    for column in (
        "foreign_flow",
        "institution_flow",
        "retail_flow",
        "foreigner_1d",
        "institution_1d",
        "retail_1d",
        "foreigner_3d",
        "institution_3d",
        "retail_3d",
        "foreigner_10d",
        "institution_10d",
        "retail_10d",
        "flow_asof",
    ):
        assert column in required
        assert column in coverage
