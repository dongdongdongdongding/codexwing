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
            "--max-tail-prob-thresholds",
            "none",
            "0.25",
            "--final-topn",
            "1",
            "3",
            "--min-eval-n",
            "15",
            "--min-eval-active-days",
            "10",
        ]
    )

    assert args.rank_metric == "hit5_dd10_5d_pct"
    assert args.max_tail_prob_thresholds == [None, 0.25]
    assert args.final_topn == [1, 3]
    assert args.min_eval_n == 15
    assert args.min_eval_active_days == 10
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


def test_three_stage_research_configs_include_tail_gate_dimension() -> None:
    configs = tool._configs(["prefilter"], [10], [1, 2], ["ev"], [None, 0.25])

    assert [(config.final_topn, config.max_tail_prob) for config in configs] == [
        (1, None),
        (1, 0.25),
        (2, None),
        (2, 0.25),
    ]
    assert configs[0].key() == "prefilter|pool10|final1|ev|tail_none"
    assert configs[1].key() == "prefilter|pool10|final1|ev|tail0p25"
    assert configs[2].key() == "prefilter|pool10|final2|ev|tail_none"
