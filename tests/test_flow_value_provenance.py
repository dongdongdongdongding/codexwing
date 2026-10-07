from copy import deepcopy

import pytest

from modules.investor_flow_units import flow_metadata_for_values
from modules.scan_universe_admission import _extract_feature_columns
from multi_agent.tools.backfill_scan_universe_snapshots import _feature_quality_payload as snapshot_quality
from multi_agent.tools.backfill_scan_universe_returns import _feature_quality_payload as return_quality
from multi_agent.tools.backfill_scan_universe_returns import _compute_return_payload
from multi_agent.tools.train_scan_universe_admission_challenger import SELECT_COLUMNS


@pytest.mark.parametrize("source,unit,canonical", [
    ("naver", "shares", "shares"), ("pykrx_value", "KRW", "KRW"),
    ("kis_openapi", "KRW", "KRW_million"), ("kis_openapi", "shares", "shares"),
])
def test_owner_metadata_survives_extraction_and_both_backfills(source, unit, canonical):
    raw = {"ticker": "005930.KS", "foreigner_1d": 100, "institution_1d": -20,
           "flow_source": source, "flow_unit": unit, "flow_asof": "20261006",
           "flow_warnings": ["original_warning"]}
    before = deepcopy(raw)
    features = _extract_feature_columns(raw, market="KOSPI")
    features["base_trade_date"] = "2026-10-07"
    for metadata in [features, snapshot_quality(features), return_quality(features, overwrite=True)]:
        assert metadata["flow_source"] == source
        assert metadata["flow_unit"] == canonical
        assert metadata["flow_asof"] == "20261006"
        assert metadata["flow_warnings"] == ["original_warning"]
    assert features["foreigner_1d"] == 100 and features["whale_flow_1d"] == 80
    assert raw == before


def test_recover_archived_metadata_only_when_every_selected_value_matches():
    owner = {"foreigner_1d": 100, "institution_1d": -20, "flow_source": "naver",
             "flow_unit": "shares", "flow_asof": "2026.05.27"}
    row = {"foreigner_1d": 100, "institution_1d": -20, "flow_source": "scan_universe_snapshot",
           "flow_unit": "source_units", "feature_snapshot": owner}
    assert flow_metadata_for_values(row, row)["flow_source"] == "naver"
    row["institution_1d"] = 0
    result = flow_metadata_for_values(row, row)
    assert result["flow_unit"] == "source_units"
    assert result["flow_warnings"] == ["flow_value_provenance_unverified"]


def test_sidecar_does_not_assign_units_to_unrelated_base_values():
    row = {"foreigner_1d": 100, "base_trade_date": "2026-10-07",
           "feature_snapshot": {"kis_sidecar": {"flow": {"foreigner_1d": 100,
               "flow_source": "kis_openapi", "flow_unit": "KRW"}}}}
    result = flow_metadata_for_values(row, row)
    assert result["flow_unit"] == "source_units" and result["flow_asof"] is None
    repeated = flow_metadata_for_values({**row, **result}, row)
    assert repeated == result


def test_metadata_is_loaded_for_training_without_becoming_a_numeric_feature():
    assert all(k in SELECT_COLUMNS for k in ("flow_source", "flow_unit", "flow_asof"))


def test_label_backfill_keeps_investor_date_instead_of_signal_date():
    row = {"base_trade_date": "2026-10-07", "entry_reference_price": 1000,
           "foreigner_1d": 100, "flow_source": "naver", "flow_unit": "shares",
           "flow_asof": "2026.10.06"}
    bars = [{"date": "2026-10-07", "close": 1000, "high": 1010, "low": 990},
            {"date": "2026-10-08", "close": 1020, "high": 1030, "low": 1000}]
    payload = _compute_return_payload(row, bars, overwrite=True)
    assert payload["flow_asof"] == "2026.10.06"
    assert payload["return_1d_pct"] == 2.0
