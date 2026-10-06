import json
import pandas as pd
import pytest
from modules.kr_contract_settlement import settle
from multi_agent.tools.settle_pending_kr_contracts import apply_verified, run


def prices(n=7):
    return pd.DataFrame({"code": "000001", "date": pd.bdate_range("2026-07-01", periods=n),
                         "adj_open": 100., "adj_high": 102., "adj_low": 98., "adj_close": 101., "volume": 1000.})


def test_suspended_entry_is_terminal_unfilled_not_zero_return():
    p = prices()
    p.loc[1, ["adj_open", "adj_high", "volume"]] = 0
    result = settle(p, p.date, p.date.iloc[0], 5)
    assert result["status"] == "unfilled_entry" and "policy_ret" not in result


def test_horizon_is_not_compressed_by_missing_session():
    p = prices()
    result = settle(p.drop(index=2), p.date, p.date.iloc[0], 5)
    assert result == {"status": "data_error", "reason": "missing_horizon_bar"}


def test_full_horizon_required_and_gap_touch_obeys_entry_contract():
    p = prices(5)
    p.loc[1, "adj_high"] = 108
    assert settle(p, p.date, p.date.iloc[0], 5)["status"] == "pending"
    p = prices()
    p.loc[2, ["adj_open", "adj_high"]] = 108
    result = settle(p, p.date, p.date.iloc[0], 5)
    assert result["touch"] == 1 and result["policy_ret"] == pytest.approx(8)


def test_halted_scheduled_exit_is_not_a_stale_close_fill():
    p = prices()
    p.loc[5, ["volume", "adj_open"]] = 0
    assert settle(p, p.date, p.date.iloc[0], 5) == {"status": "pending", "reason": "scheduled_exit_suspended"}


def test_repair_dry_run_then_backup_then_idempotence(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    p = prices()
    p.to_parquet(cache / "px_delisted.parquet")
    exp = tmp_path / "runtime_state/reports/experimental"
    exp.mkdir(parents=True)
    path = exp / "kr_swing_candidate_ledger.jsonl"
    rows = [{"date": "2026-07-01", "ticker": "000001.KS", "policy_ret": None},
            {"date": "2026-07-01", "ticker": "000001.KS", "policy_ret": 9.9}]
    before = ("\n".join(json.dumps(r) for r in rows)+"\n").encode()
    path.write_bytes(before)
    assert run(tmp_path, cache, "2026-07-15")["changed"] == 1
    assert path.read_bytes() == before
    assert run(tmp_path, cache, "2026-07-15", True)["changed"] == 1
    after = [json.loads(r) for r in path.read_text().splitlines()]
    assert after[1] == rows[1] and after[0]["policy_ret"] == 1.
    assert next((tmp_path / "runtime_state/audit/kr_settlement").glob("*.bak")).read_bytes() == before
    assert run(tmp_path, cache, "2026-07-15", True)["changed"] == 0


def test_concurrent_modification_is_never_overwritten(tmp_path):
    path = tmp_path / "ledger"
    path.write_bytes(b"concurrent")
    with pytest.raises(RuntimeError, match="concurrent"):
        apply_verified(path, b"old", [{"test": 1}], tmp_path / "audit")
    assert path.read_bytes() == b"concurrent"
