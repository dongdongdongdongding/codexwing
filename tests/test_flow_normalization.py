import copy
import json

import pandas as pd
import pytest

from multi_agent.tools import normalize_flow_cache as norm
from multi_agent.tools.update_flow_cache import FIELDS, sha, write_json


def row():
    return {"stck_bsop_date": "20261006", "frgn_ntby_qty": "-3", "orgn_ntby_qty": "1",
            "prsn_ntby_qty": "2", "etc_ntby_qty": "0", "frgn_ntby_tr_pbmn": "-30",
            "orgn_ntby_tr_pbmn": "10", "acml_tr_pbmn": "1000", "acml_vol": "100",
            "stck_clpr": "10", "frgn_shnu_vol": "2", "frgn_seln_vol": "5",
            "orgn_shnu_vol": "3", "orgn_seln_vol": "2", "prsn_shnu_vol": "4", "prsn_seln_vol": "2",
            "etc_shnu_vol": "91", "etc_seln_vol": "91"}


def fixture(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    audit = tmp_path / "audit"
    audit.mkdir()
    old = pd.DataFrame([
        {"code": "005930", "date": pd.Timestamp("2026-10-06"), **{f: 999 for f in FIELDS}},
        {"code": "000660", "date": pd.Timestamp("2026-10-02"), **{f: -50 if f != "acml_val" else 50 for f in FIELDS}}])
    old.to_parquet(tmp_path / "flow.parquet", index=False)
    write_json(source / "005930.json", {"rt_cd": "0", "output2": [row()]})
    receipt = tmp_path / "source_receipt.json"
    write_json(receipt, {"cache_after_sha256": sha(tmp_path / "flow.parquet"), "audit_dir": str(source),
                        "excluded_on_or_after": "2026-10-07", "symbols": [{"code": "005930",
                        "capture_sha256": sha(source / "005930.json"), "request_trade_date": "20261006"}]})
    norm.initialize(receipt, audit)
    manifest = {}
    for endpoint in ("repeat", "current", "price"):
        name = "005930_" + endpoint + ".json"
        write_json(audit / name, {"rt_cd": "0", "output" if endpoint == "current" else "output2": [row()]})
        manifest[name] = {"sha256": sha(audit / name)}
    write_json(audit / "captures.json", manifest)
    return old, receipt, audit


def test_exact_cross_endpoint_normalization_and_untouched_rows(tmp_path, monkeypatch):
    old, receipt, audit = fixture(tmp_path)
    loaded, plan = norm.build_plan(receipt, audit, tmp_path)
    assert plan["verified_conflict_rows"] == 1 and not plan["deferred"]
    result = norm.apply_plan(loaded, plan, tmp_path, audit)
    assert result["state"] == "committed" and result["changed_rows"] == 1
    new = pd.read_parquet(tmp_path / "flow.parquet")
    pd.testing.assert_frame_equal(old.iloc[1:], new.iloc[1:], check_exact=True)
    pd.testing.assert_frame_equal(old[["code", "date"]], new[["code", "date"]])
    assert new.iloc[0].frgn_ntby == -3 and new.iloc[0].acml_val == 1000
    assert sha(audit / "flow.before.parquet") == plan["cache_before_sha256"]
    monkeypatch.setattr(norm, "legacy_writers", lambda: [])
    monkeypatch.setattr("sys.argv", ["normalize", "--apply", "--source-receipt", str(receipt),
                                    "--audit", str(audit), "--cache", str(tmp_path)])
    assert norm.main() == 0
    assert sha(tmp_path / "flow.parquet") == result["after_sha256"]


@pytest.mark.parametrize("which,field,value,reason", [
    ("repeat", "frgn_ntby_qty", "-4", "repeat_flow_changed"),
    ("current", "orgn_ntby_qty", "2", "current_flow_disagrees"),
    ("price", "acml_tr_pbmn", "1001", "price_control_disagrees"),
    ("price", "acml_vol", "101", "price_control_disagrees"),
    ("price", "stck_clpr", "11", "price_control_disagrees"),
    ("current", "stck_bsop_date", "20261002", "date_mismatch"),
])
def test_any_disagreement_rejects_row(which, field, value, reason):
    controls = {e: copy.deepcopy(row()) for e in ("repeat", "current", "price")}
    controls[which][field] = value
    with pytest.raises(ValueError, match=reason):
        norm.verify_row(row(), *(controls[e] for e in ("repeat", "current", "price")))


def test_missing_control_never_invents_values():
    with pytest.raises(ValueError, match="control_date_missing"):
        norm.verify_row(row(), row(), None, row())


@pytest.mark.parametrize("field,value,reason", [("etc_ntby_qty", "5", "net_quantity_not_balanced"),
    ("frgn_shnu_vol", "100", "buy_sell_quantity_disagrees")])
def test_internal_accounting_identity_required(field, value, reason):
    r = row()
    r[field] = value
    with pytest.raises(ValueError, match=reason):
        norm.verify_row(r, r, r, r)


@pytest.mark.parametrize("value", [None, True, "", "1.0", "NaN", "1,2", str(2**65)])
def test_strict_numbers(value):
    with pytest.raises(ValueError):
        norm.number(value)


def test_control_tamper_blocks_all_replacement(tmp_path):
    old, receipt, audit = fixture(tmp_path)
    before = sha(tmp_path / "flow.parquet")
    write_json(audit / "005930_price.json", {"rt_cd": "0", "output2": []})
    with pytest.raises(ValueError, match="control_capture_changed"):
        norm.build_plan(receipt, audit, tmp_path)
    assert sha(tmp_path / "flow.parquet") == before


def test_missing_control_defers_without_dropping_rows(tmp_path):
    old, receipt, audit = fixture(tmp_path)
    manifest = json.loads((audit / "captures.json").read_text())
    del manifest["005930_current.json"]
    write_json(audit / "captures.json", manifest)
    _, plan = norm.build_plan(receipt, audit, tmp_path)
    assert not plan["replacements"] and len(plan["deferred"]) == 1
    pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / "flow.parquet"), old)


def test_concurrent_change_refuses_apply(tmp_path):
    old, receipt, audit = fixture(tmp_path)
    loaded, plan = norm.build_plan(receipt, audit, tmp_path)
    (tmp_path / "flow.parquet").write_bytes(b"new writer")
    with pytest.raises(ValueError, match="cache_changed_before_apply"):
        norm.apply_plan(loaded, plan, tmp_path, audit)
    assert (tmp_path / "flow.parquet").read_bytes() == b"new writer"


def test_bad_backup_refuses_overwrite(tmp_path):
    old, receipt, audit = fixture(tmp_path)
    loaded, plan = norm.build_plan(receipt, audit, tmp_path)
    before = sha(tmp_path / "flow.parquet")
    (audit / "flow.before.parquet").write_bytes(b"wrong backup")
    with pytest.raises(ValueError, match="backup_mismatch"):
        norm.apply_plan(loaded, plan, tmp_path, audit)
    assert sha(tmp_path / "flow.parquet") == before


def test_crash_after_rename_is_recognized_without_second_write(tmp_path, monkeypatch):
    old, receipt, audit = fixture(tmp_path)
    loaded, plan = norm.build_plan(receipt, audit, tmp_path)
    original = norm.write_json

    def crash(path, data):
        if path.name == "apply_receipt.json" and data["state"] == "committed":
            raise OSError("interrupted after atomic rename")
        original(path, data)

    monkeypatch.setattr(norm, "write_json", crash)
    with pytest.raises(OSError):
        norm.apply_plan(loaded, plan, tmp_path, audit)
    monkeypatch.setattr(norm, "legacy_writers", lambda: [])
    monkeypatch.setattr("sys.argv", ["normalize", "--apply", "--source-receipt", str(receipt),
                                    "--audit", str(audit), "--cache", str(tmp_path)])
    assert norm.main() == 0
    assert pd.read_parquet(tmp_path / "flow.parquet").iloc[0].frgn_ntby == -3


def test_duplicate_dates_and_failed_envelopes_rejected():
    with pytest.raises(ValueError, match="duplicate_date"):
        norm.keyed({"rt_cd": "0", "output2": [row(), row()]}, "output2")
    with pytest.raises(ValueError, match="provider_failure"):
        norm.keyed({"rt_cd": "1", "output2": []}, "output2")


def test_explicit_adjusted_auxiliary_basis_preserves_all_net_flow_values():
    raw = row()
    raw.update(etc_shnu_vol="41", etc_seln_vol="41")
    price = dict(raw, acml_vol="50", stck_clpr="20")
    values, basis = norm.verify_row(raw, raw, raw, price, raw)
    assert values == {f: int(raw[s]) for f, s in FIELDS.items()}
    assert basis == "adjusted_J_auxiliary_price_volume_only"


@pytest.mark.parametrize("field,value", [("acml_vol", "101"), ("stck_clpr", "11"), ("acml_tr_pbmn", "1001")])
def test_adjusted_auxiliary_control_still_requires_exact_match(field, value):
    raw = row()
    price = dict(raw, acml_vol="50", stck_clpr="20")
    adjusted = dict(raw)
    adjusted[field] = value
    with pytest.raises(ValueError, match="adjusted_price_control_disagrees"):
        norm.verify_row(raw, raw, raw, price, adjusted)


def test_adjusted_control_cannot_override_cash_turnover_mismatch():
    raw = row()
    with pytest.raises(ValueError, match="price_control_disagrees_acml_tr_pbmn"):
        norm.verify_row(raw, raw, raw, dict(raw, acml_tr_pbmn="999"), raw)


def test_nominal_investor_total_must_equal_unadjusted_traded_volume():
    raw = dict(row(), etc_shnu_vol="90", etc_seln_vol="90")
    with pytest.raises(ValueError, match="investor_total_not_nominal_traded_volume"):
        norm.verify_row(raw, raw, raw, raw)
