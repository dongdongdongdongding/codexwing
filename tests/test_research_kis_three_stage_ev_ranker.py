from pathlib import Path

from multi_agent.tools import research_kis_three_stage_ev_ranker as tool


def test_three_stage_research_accepts_market_input_path_overrides() -> None:
    args = tool.parse_args(
        [
            "--markets",
            "KOSPI",
            "KOSDAQ",
            "--input-path",
            "KOSPI=runtime_state/tmp/kospi.pkl",
            "--input-path",
            "kosdaq=runtime_state/tmp/kosdaq.pkl",
            "--rank-metric",
            "hit5_dd10_5d_pct",
        ]
    )

    assert args.rank_metric == "hit5_dd10_5d_pct"
    assert args.input_paths == {
        "KOSPI": "runtime_state/tmp/kospi.pkl",
        "KOSDAQ": "runtime_state/tmp/kosdaq.pkl",
    }
    assert tool._market_cache_path("KOSPI", args.start, args.end, args.input_paths["KOSPI"]) == Path(
        "runtime_state/tmp/kospi.pkl"
    )


def test_three_stage_research_default_market_cache_path_is_stable() -> None:
    path = tool._market_cache_path("KOSPI", "2026-01-01", "2026-06-10")

    assert path.name == "kis_historical_universe_prepared_kospi_20260101_20260610.pkl"
