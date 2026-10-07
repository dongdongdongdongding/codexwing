import math
import sys
import types

import pandas as pd
import pytest

from modules.investor_flow_units import canonical_flow_unit, net_amount_to_turnover
from modules.kis_openapi import parse_investor_flow_snapshot
from modules.kis_operational_adapter import normalize_kis_flow_for_whale_contract
from modules.kis_model_features import flatten_kis_model_features
from modules.scanner_services import _flow_persistence_fields
from modules.top_deep_report import _flow_snapshot_from_kis_sidecar
from multi_agent.tools.backfill_kis_ticker_period_sidecar_features import build_flow_lookup


@pytest.mark.parametrize("source,unit,expected", [
    ("kis_openapi", "KRW", "KRW_million"),
    ("kis_openapi_period_cache", "KRW", "KRW_million"),
    ("kis_openapi_sidecar:kis_openapi", "KRW", "KRW_million"),
    ("pykrx_value", "KRW", "KRW"),
    (None, "KRW", "KRW"),
    ("kis_openapi", "shares", "shares"),
    ("kis_openapi", None, None),
])
def test_units_depend_on_identified_provider(source, unit, expected):
    assert canonical_flow_unit({"flow_source": source, "flow_unit": unit}) == expected


def test_dimensionless_ratio_converts_only_net_amount_and_preserves_nulls():
    net = pd.Series([-100, 50, float("nan")], index=[4, 7, 9])
    turnover = pd.Series([1e9, 1e9, 1e9], index=net.index)
    result = net_amount_to_turnover(net, turnover)
    assert result.index.equals(net.index)
    assert result.loc[4] == pytest.approx(-0.1)
    assert result.loc[7] == pytest.approx(0.05)
    assert math.isnan(result.loc[9])
    assert net_amount_to_turnover(0, 0) == 0


def test_live_and_historical_parsers_keep_numbers_and_agree_on_units():
    row = {"stck_bsop_date": "20261006", "frgn_ntby_qty": "-2064174", "orgn_ntby_qty": "-193422",
           "prsn_ntby_qty": "1273618", "frgn_ntby_tr_pbmn": "-564926", "orgn_ntby_tr_pbmn": "-52186",
           "prsn_ntby_tr_pbmn": "344993"}
    payload = {"rt_cd": "0", "output2": [row]}
    parsed = parse_investor_flow_snapshot("005930", payload)
    live = normalize_kis_flow_for_whale_contract(parsed)
    historical = build_flow_lookup({"chunks": [{"source_status": "ok", "payload": payload}]})
    value = next(iter(historical.values()))
    assert parsed["foreigner_1d"] == live["foreigner_1d"] == value["kis_foreigner_1d"] == -564926
    assert parsed["foreigner_1d_qty"] == -2064174
    assert parsed["flow_unit"] == live["flow_unit"] == value["flow_unit"] == "KRW_million"


def test_cached_legacy_kis_units_correct_on_consumer_paths_without_rescaling():
    old = {"valid": True, "source_status": "ok", "flow_source": "kis_openapi", "flow_unit": "KRW",
           "whale_score": 12, "foreigner_1d": -123, "institution_1d": 40, "retail_1d": 83}
    persisted = _flow_persistence_fields(old)
    displayed = _flow_snapshot_from_kis_sidecar({"flow_contract": old})
    flattened = flatten_kis_model_features({"kis_operational_prefilter": {"flow": old}})
    assert persisted["flow_unit"] == displayed["flow_unit"] == "KRW_million"
    assert persisted["foreigner_1d"] == displayed["foreigner_1d"] == -123
    assert flattened["kis_prefilter_flow_unit"] == "KRW_million"
    assert flattened["kis_prefilter_flow_foreigner_1d"] == -123
    assert old["flow_unit"] == "KRW"  # historical source object remains immutable


def flow_frame():
    return pd.DataFrame({"code": ["005930"] * 30, "date": pd.date_range("2026-08-01", periods=30),
                         "frgn_ntby": [10] * 30, "orgn_ntby": [-5] * 30,
                         "frgn_val": [100] * 30, "orgn_val": [-50] * 30, "acml_val": [1e9] * 30})


def test_research_features_have_dimensionless_scale_and_causal_shift(monkeypatch):
    from research.harness_2026_07 import flow_increment_research as research
    monkeypatch.setattr(research.pd, "read_parquet", lambda *a, **kw: flow_frame())
    same_day = research.build_flow_features(0)
    prior_day = research.build_flow_features(1)
    for feature in ("fr1", "fr5", "fr20"):
        assert same_day[feature].iloc[-1] == pytest.approx(0.1)
    assert same_day.or1.iloc[-1] == pytest.approx(-0.05)
    pd.testing.assert_series_equal(prior_day.fr1.iloc[1:].reset_index(drop=True),
                                  same_day.fr1.iloc[:-1].reset_index(drop=True))


def test_pead_panel_uses_correct_flow_fraction(monkeypatch, tmp_path):
    from multi_agent.tools import report_kospi_normal_pead_shadow as shadow
    dates = flow_frame().date
    prices = pd.DataFrame({"code": ["005930"] * len(dates), "date": dates, "close": 100., "liq": 2e10,
                           "market": "KOSPI", "idx_mom20": 0., "ft_5_5": 0.})
    ann = pd.DataFrame({"code": ["005930"], "ann": [dates.iloc[0]], "period": ["202606"], "rpt": ["test"]})

    def read(path, **kwargs):
        name = str(path).split("/")[-1]
        return {"px_long.parquet": prices, "flow.parquet": flow_frame(),
                "shares.parquet": pd.DataFrame({"code": ["005930"], "shares": [1000000]}),
                "dart_ann.parquet": ann}[name].copy()

    monkeypatch.setattr(shadow, "CACHE", tmp_path)
    (tmp_path / "dart_ann.parquet").touch()
    monkeypatch.setattr(shadow.pd, "read_parquet", read)
    monkeypatch.setattr(shadow, "_liquid_kospi_universe", lambda *a: ["005930"])
    monkeypatch.setattr(shadow, "_extend_price", lambda px, codes: px)
    monkeypatch.setattr(shadow, "_extend_flow", lambda flow, codes: flow)
    monkeypatch.setattr(shadow, "_refresh_dart", lambda codes, da: da)
    monkeypatch.setitem(sys.modules, "FinanceDataReader", types.SimpleNamespace(
        DataReader=lambda *a: pd.DataFrame({"Close": 100.}, index=dates)))
    panel = shadow.build_panel(1)
    assert panel.frgn_int.iloc[-1] == pytest.approx(0.1)
