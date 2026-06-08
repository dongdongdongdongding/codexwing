import json

from modules.model_governance import (
    ACTIVE_KR_POLICY_VERSION,
    ROLLBACK_ENV_FLAG,
    PolicyMetricSet,
    PolicyReleaseSpec,
    ReleaseGateThresholds,
    active_policy_metadata,
    build_policy_release_report_from_payload,
    evaluate_policy_release_gate,
    write_policy_release_report,
)


def _metric(market, win=70.0, avg=2.0, worst=-4.0, stop=25.0, capture=40.0):
    return PolicyMetricSet(
        market=market,
        section="Top5",
        horizon="3d",
        samples=80,
        active_days=12,
        win_rate_pct=win,
        avg_return_pct=avg,
        worst_loss_pct=worst,
        stop_first_rate_pct=stop,
        capture_rate_pct=capture,
    )


def test_release_gate_passes_only_when_challenger_beats_both_markets():
    spec = PolicyReleaseSpec(
        champion_policy_version="champion_v1",
        challenger_policy_version="challenger_v2",
        promotion_reason="oos uplift",
    )
    report = evaluate_policy_release_gate(
        spec=spec,
        champion_metrics=[_metric("KOSPI"), _metric("KOSDAQ")],
        challenger_metrics=[
            _metric("KOSPI", win=72.0, avg=2.4, worst=-3.5, stop=20.0, capture=45.0),
            _metric("KOSDAQ", win=73.0, avg=2.5, worst=-3.0, stop=19.0, capture=46.0),
        ],
        thresholds=ReleaseGateThresholds(min_samples=30, min_active_days=5),
    )

    assert report["release_ready"] is True
    assert report["promotion_status"] == "promote_allowed"
    assert report["rollback"]["enabled"] is False


def test_release_gate_fails_when_one_market_or_risk_metric_regresses():
    spec = PolicyReleaseSpec(champion_policy_version="champion_v1", challenger_policy_version="challenger_v2")
    report = evaluate_policy_release_gate(
        spec=spec,
        champion_metrics=[_metric("KOSPI"), _metric("KOSDAQ")],
        challenger_metrics=[
            _metric("KOSPI", win=72.0, avg=2.4, worst=-3.5, stop=20.0, capture=45.0),
            _metric("KOSDAQ", win=69.0, avg=1.5, worst=-7.0, stop=30.0, capture=35.0),
        ],
        thresholds=ReleaseGateThresholds(min_samples=30, min_active_days=5),
    )

    failed_codes = {row["code"] for row in report["all_checks"] if not row["passed"]}
    assert report["release_ready"] is False
    assert "WIN_RATE_NOT_WORSE" in failed_codes
    assert "WORST_LOSS_NOT_WORSE" in failed_codes
    assert report["rollback"]["enabled"] is True


def test_release_gate_fails_when_net_return_after_cost_is_too_low():
    spec = PolicyReleaseSpec(champion_policy_version="champion_v1", challenger_policy_version="challenger_v2")
    report = evaluate_policy_release_gate(
        spec=spec,
        champion_metrics=[_metric("KOSPI", avg=0.10), _metric("KOSDAQ", avg=0.10)],
        challenger_metrics=[
            _metric("KOSPI", win=72.0, avg=0.40, worst=-3.5, stop=20.0, capture=45.0),
            _metric("KOSDAQ", win=72.0, avg=0.40, worst=-3.5, stop=20.0, capture=45.0),
        ],
        thresholds=ReleaseGateThresholds(min_samples=30, min_active_days=5, min_net_avg_return_pct=0.25),
    )

    failed_codes = {row["code"] for row in report["all_checks"] if not row["passed"]}
    assert report["release_ready"] is False
    assert "NET_AVG_RETURN_AFTER_COST_POSITIVE" in failed_codes
    assert report["cost_model"]["version"] == "kr_tradable_pnl_cost_v1"


def test_active_policy_metadata_supports_env_rollback(monkeypatch):
    monkeypatch.delenv(ROLLBACK_ENV_FLAG, raising=False)
    active = active_policy_metadata(market="kospi", scan_mode="swing")
    assert active["active_policy_version"] == ACTIVE_KR_POLICY_VERSION
    assert active["rollback_active"] is False

    monkeypatch.setenv(ROLLBACK_ENV_FLAG, "1")
    rollback = active_policy_metadata(market="kospi", scan_mode="swing")
    assert rollback["active_policy_version"] == rollback["rollback_policy_version"]
    assert rollback["rollback_active"] is True


def test_release_report_payload_writer(tmp_path):
    payload = {
        "spec": {
            "champion_policy_version": "champion_v1",
            "challenger_policy_version": "challenger_v2",
            "promotion_reason": "fixture",
        },
        "thresholds": {"min_samples": 10, "min_active_days": 2},
        "champion_metrics": [_metric("KOSPI").__dict__, _metric("KOSDAQ").__dict__],
        "challenger_metrics": [
            _metric("KOSPI", win=72.0, avg=2.5, worst=-3.0, stop=20.0, capture=45.0).__dict__,
            _metric("KOSDAQ", win=72.0, avg=2.5, worst=-3.0, stop=20.0, capture=45.0).__dict__,
        ],
    }

    report = build_policy_release_report_from_payload(json.loads(json.dumps(payload)))
    paths = write_policy_release_report(report, tmp_path)

    assert report["release_ready"] is True
    assert (tmp_path / "kr_model_release_gate.json").exists()
    assert "release_ready: **PASS**" in (tmp_path / "kr_model_release_gate.md").read_text(encoding="utf-8")
    assert paths["json_path"].endswith("kr_model_release_gate.json")
