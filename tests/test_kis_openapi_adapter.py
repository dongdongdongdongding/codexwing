from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from modules.kis_openapi import (
    KISConfig,
    KISOpenAPIClient,
    KISOpenAPIError,
    build_kis_adapter_health,
    market_input_code,
    normalize_kr_stock_code,
    parse_investor_flow_snapshot,
    parse_quote_snapshot,
)
import modules.kis_openapi as kis_openapi_module


def _client_with_transport(responder):
    calls = []

    def transport(method, url, headers, body, timeout):
        parsed_body = json.loads(body.decode("utf-8")) if body else None
        call = {
            "method": method,
            "url": url,
            "headers": headers,
            "body": parsed_body,
            "timeout": timeout,
            "query": {k: v[0] for k, v in parse_qs(urlparse(url).query).items()},
            "path": urlparse(url).path,
        }
        calls.append(call)
        return responder(call)

    config = KISConfig(
        app_key="app-key",
        app_secret="app-secret",
        account_no="12345678",
        account_product_code="01",
        mode="paper",
    )
    return KISOpenAPIClient(config=config, transport=transport), calls


def test_kis_health_is_non_operational_by_default():
    health = build_kis_adapter_health({})
    assert health["production_default_enabled"] is False
    assert health["scanner_default_wired"] is False
    assert health["credentials_present"] is False
    assert "quote" in health["implemented_endpoint_keys"]
    assert "stock_investor_daily" in health["implemented_endpoint_keys"]


def test_kis_health_can_report_effective_run_config():
    config = KISConfig(app_key="k", app_secret="s", mode="real", live_network_allowed=True)

    health = build_kis_adapter_health(config=config)

    assert health["mode"] == "real"
    assert health["live_network_allowed"] is True
    assert health["credentials_present"] is True
    assert health["scanner_default_wired"] is False


def test_live_network_is_blocked_without_flag_or_transport():
    client = KISOpenAPIClient(config=KISConfig(app_key="k", app_secret="s"))
    with pytest.raises(KISOpenAPIError, match="Live KIS network calls are disabled"):
        client.get_access_token(force=True)


def test_live_clients_reuse_process_token_cache(monkeypatch):
    monkeypatch.setenv("KIS_DISABLE_TOKEN_FILE_CACHE", "1")
    kis_openapi_module._TOKEN_CACHE.clear()
    calls = []

    def fake_raw_request(self, method, url, headers, body):
        calls.append({"method": method, "url": url, "body": json.loads(body.decode("utf-8"))})
        return {"access_token": "shared-token", "token_type": "Bearer", "expires_in": 86400}

    monkeypatch.setattr(KISOpenAPIClient, "_raw_request", fake_raw_request)
    config = KISConfig(app_key="cache-key", app_secret="cache-secret", mode="real", live_network_allowed=True)

    assert KISOpenAPIClient(config=config).get_access_token() == "shared-token"
    assert KISOpenAPIClient(config=config).get_access_token() == "shared-token"
    assert len(calls) == 1


def test_live_clients_reuse_file_token_cache(monkeypatch, tmp_path):
    kis_openapi_module._TOKEN_CACHE.clear()
    monkeypatch.delenv("KIS_DISABLE_TOKEN_FILE_CACHE", raising=False)
    monkeypatch.setenv("KIS_TOKEN_CACHE_PATH", str(tmp_path / "kis_token_cache.json"))
    calls = []

    def fake_raw_request(self, method, url, headers, body):
        calls.append({"method": method, "url": url, "body": json.loads(body.decode("utf-8"))})
        return {"access_token": "file-token", "token_type": "Bearer", "expires_in": 86400}

    monkeypatch.setattr(KISOpenAPIClient, "_raw_request", fake_raw_request)
    config = KISConfig(app_key="file-cache-key", app_secret="cache-secret", mode="real", live_network_allowed=True)

    assert KISOpenAPIClient(config=config).get_access_token() == "file-token"
    assert len(calls) == 1

    kis_openapi_module._TOKEN_CACHE.clear()

    def fail_raw_request(self, method, url, headers, body):
        raise AssertionError("token endpoint should not be called when file cache is valid")

    monkeypatch.setattr(KISOpenAPIClient, "_raw_request", fail_raw_request)
    assert KISOpenAPIClient(config=config).get_access_token() == "file-token"
    assert len(calls) == 1


def test_normalize_kr_stock_code_and_market_input_code():
    assert normalize_kr_stock_code("005930.KS") == "005930"
    assert normalize_kr_stock_code("A091990") == "091990"
    assert normalize_kr_stock_code("1234") == "001234"
    assert market_input_code("KOSPI") == "0001"
    assert market_input_code("KOSDAQ") == "1001"
    assert market_input_code("ALL") == "0000"


def test_quote_request_and_snapshot_parser_preserve_current_price_and_status():
    def responder(call):
        if call["path"] == "/oauth2/tokenP":
            assert call["body"]["grant_type"] == "client_credentials"
            return {"access_token": "token-123", "token_type": "Bearer", "expires_in": 86400}
        assert call["path"] == "/uapi/domestic-stock/v1/quotations/inquire-price"
        assert call["headers"]["authorization"] == "Bearer token-123"
        assert call["headers"]["tr_id"] == "FHKST01010100"
        assert call["query"]["FID_COND_MRKT_DIV_CODE"] == "UN"
        assert call["query"]["FID_INPUT_ISCD"] == "005930"
        return {
            "rt_cd": "0",
            "output": {
                "stck_prpr": "81200",
                "prdy_vrss": "1200",
                "prdy_vrss_sign": "2",
                "prdy_ctrt": "1.50",
                "acml_vol": "1234567",
                "acml_tr_pbmn": "100000000000",
                "stck_oprc": "80000",
                "stck_hgpr": "82000",
                "stck_lwpr": "79000",
                "frgn_ntby_qty": "10000",
                "pgtr_ntby_qty": "-2000",
                "hts_avls": "480000000",
                "per": "12.3",
                "pbr": "1.4",
                "d250_hgpr": "90000",
                "d250_lwpr": "50000",
                "iscd_stat_cls_code": "55",
            },
        }

    client, calls = _client_with_transport(responder)
    snapshot = client.quote_snapshot("005930.KS")

    assert len(calls) == 2
    assert snapshot["ticker"] == "005930"
    assert snapshot["last_price"] == 81200
    assert snapshot["day_change_pct"] == 1.5
    assert snapshot["volume"] == 1234567
    assert snapshot["value_traded"] == 100000000000
    assert snapshot["foreigner_net_qty"] == 10000
    assert snapshot["program_net_qty"] == -2000
    assert snapshot["status_warning"] is None


def test_quote_parser_maps_risk_status_code():
    snapshot = parse_quote_snapshot("005930", {"output": {"iscd_stat_cls_code": "51"}})
    assert snapshot["status_warning"] == "management_stock"
    assert snapshot["warnings"] == ["management_stock"]


def test_daily_and_minute_bar_requests_use_documented_parameters():
    def responder(call):
        if call["path"] == "/oauth2/tokenP":
            return {"access_token": "token-123", "token_type": "Bearer", "expires_in": 86400}
        return {"rt_cd": "0", "output2": []}

    client, calls = _client_with_transport(responder)
    client.daily_bars("005930", start_date="20260501", end_date="20260604")
    client.industry_daily_bars(index_code="1001", start_date="20260501", end_date="20260604")
    client.today_minute_bars("005930", input_hour="093500")
    client.daily_minute_bars("005930", trade_date="20260604", input_hour="093500")

    daily_call = next(call for call in calls if call["path"].endswith("inquire-daily-itemchartprice"))
    index_daily_call = next(call for call in calls if call["path"].endswith("inquire-daily-indexchartprice"))
    today_minute_call = next(call for call in calls if call["path"].endswith("inquire-time-itemchartprice"))
    daily_minute_call = next(call for call in calls if call["path"].endswith("inquire-time-dailychartprice"))

    assert daily_call["query"]["FID_PERIOD_DIV_CODE"] == "D"
    assert daily_call["query"]["FID_ORG_ADJ_PRC"] == "0"
    assert index_daily_call["query"]["FID_COND_MRKT_DIV_CODE"] == "U"
    assert index_daily_call["query"]["FID_INPUT_ISCD"] == "1001"
    assert today_minute_call["query"]["FID_INPUT_HOUR_1"] == "093500"
    assert today_minute_call["query"]["FID_PW_DATA_INCU_YN"] == "Y"
    assert daily_minute_call["query"]["FID_INPUT_DATE_1"] == "20260604"
    assert daily_minute_call["headers"]["tr_id"] == "FHKST03010230"


def test_investor_flow_parser_prefers_amount_and_keeps_quantity_fields():
    payload = {
        "output2": [
            {
                "stck_bsop_date": "20260604",
                "frgn_ntby_qty": "100",
                "orgn_ntby_qty": "-20",
                "prsn_ntby_qty": "-80",
                "frgn_ntby_tr_pbmn": "1000000",
                "orgn_ntby_tr_pbmn": "-200000",
                "prsn_ntby_tr_pbmn": "-800000",
            },
            {
                "stck_bsop_date": "20260603",
                "frgn_ntby_qty": "-50",
                "orgn_ntby_qty": "30",
                "prsn_ntby_qty": "20",
                "frgn_ntby_tr_pbmn": "-500000",
                "orgn_ntby_tr_pbmn": "300000",
                "prsn_ntby_tr_pbmn": "200000",
            },
        ]
    }

    snapshot = parse_investor_flow_snapshot("005930.KS", payload)

    assert snapshot["flow_unit"] == "KRW"
    assert snapshot["flow_asof"] == "20260604"
    assert snapshot["foreigner_1d"] == 1000000
    assert snapshot["institution_1d"] == -200000
    assert snapshot["retail_1d"] == -800000
    assert snapshot["whale_flow_1d"] == 800000
    assert snapshot["foreigner_3d"] == 500000
    assert snapshot["institution_3d"] == 100000
    assert snapshot["foreigner_1d_qty"] == 100
    assert snapshot["institution_1d_qty"] == -20


def test_ranking_and_context_requests_are_available_without_scanner_wiring():
    def responder(call):
        if call["path"] == "/oauth2/tokenP":
            return {"access_token": "token-123", "token_type": "Bearer", "expires_in": 86400}
        return {"rt_cd": "0", "output": []}

    client, calls = _client_with_transport(responder)
    client.volume_rank(market="KOSDAQ", rank_by="trade_value")
    client.fluctuation_rank(market="KOSPI", sort="up")
    client.volume_power_rank(market="ALL")
    client.foreign_institution_total(market="KOSDAQ", investor_type="institution")
    client.industry_price(index_code="1001")
    client.vi_status(market="KOSDAQ", trade_date="20260604")
    client.news_titles(symbol="005930", trade_date="20260604")

    paths = [call["path"] for call in calls]
    assert "/uapi/domestic-stock/v1/quotations/volume-rank" in paths
    assert "/uapi/domestic-stock/v1/ranking/fluctuation" in paths
    assert "/uapi/domestic-stock/v1/ranking/volume-power" in paths
    assert "/uapi/domestic-stock/v1/quotations/foreign-institution-total" in paths
    assert "/uapi/domestic-stock/v1/quotations/inquire-index-price" in paths
    assert "/uapi/domestic-stock/v1/quotations/inquire-vi-status" in paths
    assert "/uapi/domestic-stock/v1/quotations/news-title" in paths

    foreign_total = next(call for call in calls if call["path"].endswith("foreign-institution-total"))
    assert foreign_total["query"]["FID_INPUT_ISCD"] == "1001"
    assert foreign_total["query"]["FID_ETC_CLS_CODE"] == "2"
