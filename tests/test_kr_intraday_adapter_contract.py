from modules.kr_intraday_adapter_contract import (
    KIS_REQUIRED_ENV_VARS,
    adapter_decision_contract,
    build_kr_intraday_adapter_health,
    storage_budget_policy,
)


def test_adapter_decision_contract_prefers_kis_without_production_promotion():
    contract = adapter_decision_contract()
    assert contract["version"] == "kr_intraday_adapter_contract_v1"
    assert contract["recommended_primary"] == "kis_openapi"
    assert contract["promotion_gate"]["production_dependency_allowed"] is False
    assert contract["source_profiles"]["kis_openapi"]["minute_bar_capable"] is True
    assert contract["source_profiles"]["kis_openapi"]["investor_flow_capable"] is True
    assert contract["source_profiles"]["yfinance"]["investor_flow_capable"] is False


def test_storage_budget_is_candidate_persisted_and_universe_cache_only():
    budget = storage_budget_policy(universe_count=2000, candidate_count=50, snapshots_per_day=4, retention_days=20)
    assert budget["raw_tick_storage"] == "forbidden"
    assert budget["full_universe_intraday_retention"] == "cache_only"
    assert budget["candidate_rows_per_day"] == 200
    assert budget["full_universe_rows_per_day_if_cached"] == 8000
    assert "vwap" in budget["persisted_fields"]
    assert "theme_breadth_pct" in budget["persisted_fields"]


def test_adapter_health_is_non_network_and_reports_missing_kis_env():
    env = {key: "" for key in KIS_REQUIRED_ENV_VARS}
    health = build_kr_intraday_adapter_health(env)
    assert health["dry_run"] is True
    assert health["network_called"] is False
    assert health["kis"]["credentials_present"] is False
    assert set(health["kis"]["missing_env_vars"]) == set(KIS_REQUIRED_ENV_VARS)
