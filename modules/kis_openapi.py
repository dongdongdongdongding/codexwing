from __future__ import annotations

import json
import hashlib
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional


KIS_REAL_REST_DOMAIN = "https://openapi.koreainvestment.com:9443"
KIS_PAPER_REST_DOMAIN = "https://openapivts.koreainvestment.com:29443"
KIS_REAL_WS_DOMAIN = "ws://ops.koreainvestment.com:21000"
KIS_PAPER_WS_DOMAIN = "ws://ops.koreainvestment.com:31000"


Transport = Callable[[str, str, Dict[str, str], Optional[bytes], float], Dict[str, Any]]


class KISOpenAPIError(RuntimeError):
    """Raised for KIS adapter configuration, transport, or API response errors."""


@dataclass(frozen=True)
class KISEndpoint:
    key: str
    label: str
    method: str
    path: str
    real_tr_id: str
    paper_tr_id: str
    paper_supported: bool = True
    websocket: bool = False

    def tr_id_for_mode(self, mode: str) -> str:
        if str(mode or "").lower() == "paper" and self.paper_supported and self.paper_tr_id:
            return self.paper_tr_id
        return self.real_tr_id


KIS_ENDPOINTS: Dict[str, KISEndpoint] = {
    "token": KISEndpoint("token", "OAuth access token", "POST", "/oauth2/tokenP", "", ""),
    "approval_key": KISEndpoint("approval_key", "Websocket approval key", "POST", "/oauth2/Approval", "", ""),
    "quote": KISEndpoint(
        "quote",
        "Domestic stock quote",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-price",
        "FHKST01010100",
        "FHKST01010100",
    ),
    "daily_bars": KISEndpoint(
        "daily_bars",
        "Domestic daily/weekly/monthly/yearly bars",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        "FHKST03010100",
        "FHKST03010100",
    ),
    "today_minute_bars": KISEndpoint(
        "today_minute_bars",
        "Domestic same-day minute bars",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
        "FHKST03010200",
        "FHKST03010200",
    ),
    "daily_minute_bars": KISEndpoint(
        "daily_minute_bars",
        "Domestic historical daily minute bars",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice",
        "FHKST03010230",
        "",
        paper_supported=False,
    ),
    "asking_price": KISEndpoint(
        "asking_price",
        "Domestic asking price and expected match",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
        "FHKST01010200",
        "FHKST01010200",
    ),
    "conclusion": KISEndpoint(
        "conclusion",
        "Domestic conclusion tape",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-ccnl",
        "FHKST01010300",
        "FHKST01010300",
    ),
    "stock_investor_current": KISEndpoint(
        "stock_investor_current",
        "Domestic current investor by stock",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-investor",
        "FHKST01010900",
        "FHKST01010900",
    ),
    "stock_investor_daily": KISEndpoint(
        "stock_investor_daily",
        "Domestic daily investor by stock",
        "GET",
        "/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily",
        "FHPTJ04160001",
        "",
        paper_supported=False,
    ),
    "daily_credit_balance": KISEndpoint(
        "daily_credit_balance",
        "Domestic daily credit balance trend by stock",
        "GET",
        "/uapi/domestic-stock/v1/quotations/daily-credit-balance",
        "FHPST04760000",
        "",
        paper_supported=False,
    ),
    "investor_trend_estimate": KISEndpoint(
        "investor_trend_estimate",
        "Domestic foreigner/institution estimate",
        "GET",
        "/uapi/domestic-stock/v1/quotations/investor-trend-estimate",
        "HHPTJ04160200",
        "",
        paper_supported=False,
    ),
    "foreign_institution_total": KISEndpoint(
        "foreign_institution_total",
        "Domestic foreign/institution aggregate ranking",
        "GET",
        "/uapi/domestic-stock/v1/quotations/foreign-institution-total",
        "FHPTJ04400000",
        "",
        paper_supported=False,
    ),
    "volume_rank": KISEndpoint(
        "volume_rank",
        "Domestic volume ranking",
        "GET",
        "/uapi/domestic-stock/v1/quotations/volume-rank",
        "FHPST01710000",
        "",
        paper_supported=False,
    ),
    "fluctuation_rank": KISEndpoint(
        "fluctuation_rank",
        "Domestic fluctuation ranking",
        "GET",
        "/uapi/domestic-stock/v1/ranking/fluctuation",
        "FHPST01700000",
        "",
        paper_supported=False,
    ),
    "volume_power_rank": KISEndpoint(
        "volume_power_rank",
        "Domestic execution strength ranking",
        "GET",
        "/uapi/domestic-stock/v1/ranking/volume-power",
        "FHPST01680000",
        "",
        paper_supported=False,
    ),
    "expected_updown_rank": KISEndpoint(
        "expected_updown_rank",
        "Domestic expected match up/down ranking",
        "GET",
        "/uapi/domestic-stock/v1/ranking/exp-trans-updown",
        "FHPST01820000",
        "",
        paper_supported=False,
    ),
    "upper_lower_capture": KISEndpoint(
        "upper_lower_capture",
        "Domestic upper/lower limit capture",
        "GET",
        "/uapi/domestic-stock/v1/quotations/capture-uplowprice",
        "FHKST130000C0",
        "",
        paper_supported=False,
    ),
    "industry_price": KISEndpoint(
        "industry_price",
        "Domestic industry index current price",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-index-price",
        "FHPUP02100000",
        "",
        paper_supported=False,
    ),
    "industry_daily_bars": KISEndpoint(
        "industry_daily_bars",
        "Domestic industry daily bars",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice",
        "FHKUP03500100",
        "FHKUP03500100",
    ),
    "market_investor_time": KISEndpoint(
        "market_investor_time",
        "Domestic investor by market time series",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market",
        "FHPTJ04030000",
        "",
        paper_supported=False,
    ),
    "vi_status": KISEndpoint(
        "vi_status",
        "Domestic VI status",
        "GET",
        "/uapi/domestic-stock/v1/quotations/inquire-vi-status",
        "FHPST01390000",
        "",
        paper_supported=False,
    ),
    "news_title": KISEndpoint(
        "news_title",
        "Domestic market/news disclosure title",
        "GET",
        "/uapi/domestic-stock/v1/quotations/news-title",
        "FHKST01011800",
        "",
        paper_supported=False,
    ),
    "stock_info": KISEndpoint(
        "stock_info",
        "Domestic stock information",
        "GET",
        "/uapi/domestic-stock/v1/quotations/search-stock-info",
        "CTPF1002R",
        "",
        paper_supported=False,
    ),
    "financial_ratio": KISEndpoint(
        "financial_ratio",
        "Domestic financial ratios",
        "GET",
        "/uapi/domestic-stock/v1/finance/financial-ratio",
        "FHKST66430300",
        "",
        paper_supported=False,
    ),
    "estimate_perform": KISEndpoint(
        "estimate_perform",
        "Domestic estimated performance",
        "GET",
        "/uapi/domestic-stock/v1/quotations/estimate-perform",
        "HHKST668300C0",
        "",
        paper_supported=False,
    ),
    "balance": KISEndpoint(
        "balance",
        "Domestic balance inquiry",
        "GET",
        "/uapi/domestic-stock/v1/trading/inquire-balance",
        "TTTC8434R",
        "VTTC8434R",
    ),
    "buyable_cash": KISEndpoint(
        "buyable_cash",
        "Domestic buyable cash inquiry",
        "GET",
        "/uapi/domestic-stock/v1/trading/inquire-psbl-order",
        "TTTC8908R",
        "VTTC8908R",
    ),
    "sellable_quantity": KISEndpoint(
        "sellable_quantity",
        "Domestic sellable quantity inquiry",
        "GET",
        "/uapi/domestic-stock/v1/trading/inquire-psbl-sell",
        "TTTC8408R",
        "",
        paper_supported=False,
    ),
    "daily_fills": KISEndpoint(
        "daily_fills",
        "Domestic daily order/fill inquiry",
        "GET",
        "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
        "TTTC0081R",
        "VTTC0081R",
    ),
}


@dataclass
class KISConfig:
    app_key: str
    app_secret: str
    account_no: str = ""
    account_product_code: str = ""
    cust_type: str = "P"
    mode: str = "paper"
    real_domain: str = KIS_REAL_REST_DOMAIN
    paper_domain: str = KIS_PAPER_REST_DOMAIN
    real_ws_domain: str = KIS_REAL_WS_DOMAIN
    paper_ws_domain: str = KIS_PAPER_WS_DOMAIN
    live_network_allowed: bool = False

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "KISConfig":
        source = env if env is not None else os.environ
        return cls(
            app_key=str(source.get("KIS_APP_KEY") or "").strip(),
            app_secret=str(source.get("KIS_APP_SECRET") or "").strip(),
            account_no=str(source.get("KIS_ACCOUNT_NO") or "").strip(),
            account_product_code=str(source.get("KIS_ACCOUNT_PRODUCT_CODE") or "").strip(),
            cust_type=str(source.get("KIS_CUST_TYPE") or "P").strip() or "P",
            mode=str(source.get("KIS_MODE") or "paper").strip().lower() or "paper",
            live_network_allowed=str(source.get("KIS_ENABLE_LIVE_CALLS") or "").strip().lower()
            in {"1", "true", "yes", "y"},
        )

    @property
    def rest_domain(self) -> str:
        return self.real_domain if self.mode == "real" else self.paper_domain

    @property
    def ws_domain(self) -> str:
        return self.real_ws_domain if self.mode == "real" else self.paper_ws_domain

    @property
    def credentials_present(self) -> bool:
        return bool(self.app_key and self.app_secret)

    @property
    def account_present(self) -> bool:
        return bool(self.account_no and self.account_product_code)


@dataclass
class KISTokenState:
    access_token: str = ""
    token_type: str = "Bearer"
    expires_at_epoch: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)

    def valid(self, min_ttl_seconds: int = 300) -> bool:
        return bool(self.access_token) and (self.expires_at_epoch - time.time()) > float(min_ttl_seconds)


_TOKEN_CACHE_LOCK = threading.Lock()
_TOKEN_CACHE: Dict[tuple, KISTokenState] = {}
_LIVE_REQUEST_RATE_LOCK = threading.Lock()
_LIVE_REQUEST_LAST_AT = 0.0


def _token_file_cache_path() -> str:
    raw = str(os.getenv("KIS_TOKEN_CACHE_PATH") or "runtime_state/local_short_term/kis_token_cache.json").strip()
    return raw if os.path.isabs(raw) else os.path.abspath(raw)


def _token_file_cache_enabled() -> bool:
    raw = str(os.getenv("KIS_DISABLE_TOKEN_FILE_CACHE") or "").strip().lower()
    return raw not in {"1", "true", "yes", "on", "y"}


def _token_file_cache_key(cache_key: tuple) -> str:
    encoded = json.dumps([str(item) for item in cache_key], ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_token_file_cache(cache_key: tuple) -> Optional[KISTokenState]:
    if not _token_file_cache_enabled():
        return None
    path = _token_file_cache_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    item = payload.get(_token_file_cache_key(cache_key))
    if not isinstance(item, dict):
        return None
    state = KISTokenState(
        access_token=str(item.get("access_token") or "").strip(),
        token_type=str(item.get("token_type") or "Bearer"),
        expires_at_epoch=float(item.get("expires_at_epoch") or 0.0),
        raw={"cache_source": "file"},
    )
    return state if state.valid() else None


def _save_token_file_cache(cache_key: tuple, state: KISTokenState) -> None:
    if not _token_file_cache_enabled() or not state.valid(min_ttl_seconds=60):
        return
    path = _token_file_cache_path()
    payload: Dict[str, Any] = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            payload = loaded
    except Exception:
        payload = {}
    payload[_token_file_cache_key(cache_key)] = {
        "access_token": state.access_token,
        "token_type": state.token_type or "Bearer",
        "expires_at_epoch": float(state.expires_at_epoch or 0.0),
        "updated_at_epoch": time.time(),
    }
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp_path = f"{path}.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
    try:
        os.chmod(tmp_path, 0o600)
    except Exception:
        pass
    os.replace(tmp_path, path)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def _live_request_throttle() -> None:
    spacing_sec = max(0.0, _env_float("KIS_LIVE_CALL_SLEEP_SEC", 0.12))
    if spacing_sec <= 0:
        return
    global _LIVE_REQUEST_LAST_AT
    with _LIVE_REQUEST_RATE_LOCK:
        elapsed = time.monotonic() - _LIVE_REQUEST_LAST_AT
        if elapsed < spacing_sec:
            time.sleep(spacing_sec - elapsed)
        _LIVE_REQUEST_LAST_AT = time.monotonic()


def _retryable_kis_text(text: str) -> bool:
    return any(token in str(text or "") for token in ("EGW00201", "초당 거래건수", "rate limit", "too many requests"))


def _retryable_kis_payload(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping):
        return False
    return _retryable_kis_text(
        " ".join(
            str(payload.get(key) or "")
            for key in ("msg_cd", "msg1", "error_code", "error_description", "msg")
        )
    )


def normalize_kr_stock_code(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if raw.endswith(".KS") or raw.endswith(".KQ"):
        raw = raw[:-3]
    if raw.startswith("A") and len(raw) == 7 and raw[1:].isdigit():
        raw = raw[1:]
    return raw.zfill(6) if raw.isdigit() and len(raw) <= 6 else raw


def market_input_code(market: str) -> str:
    key = str(market or "").strip().upper()
    if key in {"KOSPI", "KS", "0001"}:
        return "0001"
    if key in {"KOSDAQ", "KQ", "1001"}:
        return "1001"
    if key in {"KOSPI200", "KS200", "2001"}:
        return "2001"
    return "0000"


def vi_market_code(market: str) -> str:
    key = str(market or "").strip().upper()
    if key in {"KOSPI", "KS", "0001"}:
        return "K"
    if key in {"KOSDAQ", "KQ", "1001"}:
        return "Q"
    return "0"


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        text = str(value).strip().replace(",", "")
        if text == "":
            return None
        return float(text)
    except Exception:
        return None


def _to_int(value: Any) -> Optional[int]:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)


def _compact_dict(data: Mapping[str, Any]) -> Dict[str, Any]:
    return {str(k): v for k, v in data.items() if v is not None}


def _output_list(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    for key in ("output2", "output", "Output", "output1"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _output_dict(payload: Mapping[str, Any]) -> Dict[str, Any]:
    for key in ("output", "output1", "Output"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


class KISOpenAPIClient:
    """Small, mockable KIS OpenAPI client.

    Network calls are disabled unless a transport is injected or
    ``KIS_ENABLE_LIVE_CALLS=1`` is set on the config. This keeps the adapter
    safe to import in production before the scanner is explicitly promoted.
    """

    def __init__(
        self,
        config: Optional[KISConfig] = None,
        *,
        transport: Optional[Transport] = None,
        timeout: float = 8.0,
    ) -> None:
        self.config = config or KISConfig.from_env()
        self.transport = transport
        self.timeout = float(timeout)
        self._token_state = KISTokenState()

    def _token_cache_key(self) -> tuple:
        return (
            self.config.mode,
            self.config.rest_domain,
            self.config.app_key,
            self.config.cust_type,
        )

    def endpoint_contract(self) -> Dict[str, Any]:
        return {
            key: {
                "label": endpoint.label,
                "method": endpoint.method,
                "path": endpoint.path,
                "real_tr_id": endpoint.real_tr_id,
                "paper_tr_id": endpoint.paper_tr_id,
                "paper_supported": endpoint.paper_supported,
                "websocket": endpoint.websocket,
            }
            for key, endpoint in KIS_ENDPOINTS.items()
        }

    def _url(self, path: str) -> str:
        return self.config.rest_domain.rstrip("/") + "/" + str(path or "").lstrip("/")

    def _raw_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[bytes],
    ) -> Dict[str, Any]:
        if self.transport is not None:
            return self.transport(method, url, headers, body, self.timeout)
        if not self.config.live_network_allowed:
            raise KISOpenAPIError(
                "Live KIS network calls are disabled. Set KIS_ENABLE_LIVE_CALLS=1 "
                "or inject a test transport."
            )
        _live_request_throttle()
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise KISOpenAPIError(f"KIS HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise KISOpenAPIError(f"KIS network error: {exc}") from exc
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise KISOpenAPIError("KIS returned non-JSON response") from exc
        if not isinstance(parsed, dict):
            raise KISOpenAPIError("KIS returned non-object JSON response")
        return parsed

    def _request_json(
        self,
        endpoint_key: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        tr_id: Optional[str] = None,
        authorize: bool = True,
    ) -> Dict[str, Any]:
        endpoint = KIS_ENDPOINTS[endpoint_key]
        method = endpoint.method.upper()
        url = self._url(endpoint.path)
        if params:
            query = urllib.parse.urlencode(_compact_dict(params))
            url = f"{url}?{query}"
        body = None
        headers: Dict[str, str] = {"content-type": "application/json; charset=utf-8"}
        if json_body is not None:
            body = json.dumps(_compact_dict(json_body), ensure_ascii=False).encode("utf-8")

        if endpoint_key not in {"token", "approval_key"}:
            headers["appkey"] = self.config.app_key
            headers["appsecret"] = self.config.app_secret
            headers["custtype"] = self.config.cust_type or "P"
            if tr_id or endpoint.real_tr_id:
                headers["tr_id"] = tr_id or endpoint.tr_id_for_mode(self.config.mode)
            if authorize:
                token = self.get_access_token()
                headers["authorization"] = f"{self._token_state.token_type or 'Bearer'} {token}"

        retry_count = max(0, int(_env_float("KIS_LIVE_RETRY_COUNT", 3)))
        retry_sleep_sec = max(0.0, _env_float("KIS_LIVE_RETRY_SLEEP_SEC", 0.8))
        payload: Dict[str, Any] = {}
        last_exc: Optional[Exception] = None
        for attempt in range(retry_count + 1):
            try:
                payload = self._raw_request(method, url, headers, body)
                if (
                    endpoint_key not in {"token", "approval_key"}
                    and _retryable_kis_payload(payload)
                    and attempt < retry_count
                ):
                    time.sleep(retry_sleep_sec * float(attempt + 1))
                    continue
                break
            except KISOpenAPIError as exc:
                last_exc = exc
                if endpoint_key in {"token", "approval_key"} or attempt >= retry_count or not _retryable_kis_text(str(exc)):
                    raise
                time.sleep(retry_sleep_sec * float(attempt + 1))
        if not payload and last_exc is not None:
            raise last_exc
        if endpoint_key not in {"token", "approval_key"}:
            rt_cd = payload.get("rt_cd")
            if rt_cd not in (None, "", "0"):
                raise KISOpenAPIError(f"KIS API error {payload.get('msg_cd')}: {payload.get('msg1')}")
        return payload

    def get_access_token(self, *, force: bool = False) -> str:
        if not force and self._token_state.valid():
            return self._token_state.access_token
        use_shared_cache = self.transport is None
        cache_key = self._token_cache_key()
        if use_shared_cache and not force:
            with _TOKEN_CACHE_LOCK:
                cached = _TOKEN_CACHE.get(cache_key)
                if cached and cached.valid():
                    self._token_state = cached
                    return cached.access_token
                file_cached = _load_token_file_cache(cache_key)
                if file_cached and file_cached.valid():
                    self._token_state = file_cached
                    _TOKEN_CACHE[cache_key] = file_cached
                    return file_cached.access_token
        if not self.config.credentials_present:
            raise KISOpenAPIError("Missing KIS_APP_KEY or KIS_APP_SECRET")
        if use_shared_cache:
            with _TOKEN_CACHE_LOCK:
                if not force:
                    cached = _TOKEN_CACHE.get(cache_key)
                    if cached and cached.valid():
                        self._token_state = cached
                        return cached.access_token
                    file_cached = _load_token_file_cache(cache_key)
                    if file_cached and file_cached.valid():
                        self._token_state = file_cached
                        _TOKEN_CACHE[cache_key] = file_cached
                        return file_cached.access_token
                payload = self._request_json(
                    "token",
                    json_body={
                        "grant_type": "client_credentials",
                        "appkey": self.config.app_key,
                        "appsecret": self.config.app_secret,
                    },
                    authorize=False,
                )
        else:
            payload = self._request_json(
                "token",
                json_body={
                    "grant_type": "client_credentials",
                    "appkey": self.config.app_key,
                    "appsecret": self.config.app_secret,
                },
                authorize=False,
            )
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise KISOpenAPIError("KIS token response missing access_token")
        expires_in = _to_float(payload.get("expires_in")) or 86400.0
        self._token_state = KISTokenState(
            access_token=token,
            token_type=str(payload.get("token_type") or "Bearer"),
            expires_at_epoch=time.time() + max(60.0, expires_in - 300.0),
            raw=dict(payload),
        )
        if use_shared_cache:
            with _TOKEN_CACHE_LOCK:
                _TOKEN_CACHE[cache_key] = self._token_state
                _save_token_file_cache(cache_key, self._token_state)
        return token

    def get_approval_key(self) -> str:
        if not self.config.credentials_present:
            raise KISOpenAPIError("Missing KIS_APP_KEY or KIS_APP_SECRET")
        payload = self._request_json(
            "approval_key",
            json_body={
                "grant_type": "client_credentials",
                "appkey": self.config.app_key,
                "secretkey": self.config.app_secret,
            },
            authorize=False,
        )
        approval_key = str(payload.get("approval_key") or "").strip()
        if not approval_key:
            raise KISOpenAPIError("KIS approval response missing approval_key")
        return approval_key

    def quote(self, symbol: str, *, market_div: str = "UN") -> Dict[str, Any]:
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "quote",
            params={"FID_COND_MRKT_DIV_CODE": market_div, "FID_INPUT_ISCD": code},
        )

    def quote_snapshot(self, symbol: str, *, market_div: str = "UN") -> Dict[str, Any]:
        payload = self.quote(symbol, market_div=market_div)
        return parse_quote_snapshot(symbol, payload)

    def daily_bars(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        period: str = "D",
        adjusted: bool = True,
        market_div: str = "J",
    ) -> Dict[str, Any]:
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "daily_bars",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": start_date,
                "FID_INPUT_DATE_2": end_date,
                "FID_PERIOD_DIV_CODE": period,
                "FID_ORG_ADJ_PRC": "0" if adjusted else "1",
            },
        )

    def today_minute_bars(
        self,
        symbol: str,
        *,
        input_hour: str = "153000",
        include_past: bool = True,
        market_div: str = "J",
    ) -> Dict[str, Any]:
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "today_minute_bars",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": code,
                "FID_INPUT_HOUR_1": input_hour,
                "FID_PW_DATA_INCU_YN": "Y" if include_past else "N",
                "FID_ETC_CLS_CODE": "",
            },
        )

    def daily_minute_bars(
        self,
        symbol: str,
        *,
        trade_date: str,
        input_hour: str = "153000",
        include_past: bool = True,
        market_div: str = "J",
    ) -> Dict[str, Any]:
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "daily_minute_bars",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": code,
                "FID_INPUT_HOUR_1": input_hour,
                "FID_INPUT_DATE_1": trade_date,
                "FID_PW_DATA_INCU_YN": "Y" if include_past else "N",
                "FID_FAKE_TICK_INCU_YN": "",
            },
        )

    def investor_trading_daily(
        self,
        symbol: str,
        *,
        trade_date: str,
        market_div: str = "J",
    ) -> Dict[str, Any]:
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "stock_investor_daily",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": trade_date,
                "FID_ORG_ADJ_PRC": "",
                "FID_ETC_CLS_CODE": "1",
            },
        )

    def investor_trading_current(self, symbol: str, *, market_div: str = "J") -> Dict[str, Any]:
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "stock_investor_current",
            params={"FID_COND_MRKT_DIV_CODE": market_div, "FID_INPUT_ISCD": code},
        )

    def daily_credit_balance(self, symbol: str, *, trade_date: str, market_div: str = "J") -> Dict[str, Any]:
        """국내주식 신용잔고 일별추이 (FHPST04760000). ~30 rows per call ending at trade_date;
        walk trade_date backwards for history. Mechanical-flow research input (swing-main-5r7t)."""
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "daily_credit_balance",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_COND_SCR_DIV_CODE": "20476",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": trade_date,
            },
        )

    def investor_flow_snapshot(self, symbol: str, *, trade_date: str, market_div: str = "J") -> Dict[str, Any]:
        requested_trade_date = str(trade_date or "").strip()
        try:
            payload = self.investor_trading_daily(symbol, trade_date=requested_trade_date, market_div=market_div)
            snapshot = parse_investor_flow_snapshot(symbol, payload)
            snapshot["requested_trade_date"] = requested_trade_date
            snapshot["resolved_trade_date"] = snapshot.get("flow_asof")
            snapshot["flow_endpoint"] = "stock_investor_daily"
            snapshot["flow_date_fallback"] = False
            return snapshot
        except KISOpenAPIError as exc:
            if not any(token in str(exc) for token in ("OPSQ2001", "TIME LIMIT")):
                raise
            payload = self.investor_trading_current(symbol, market_div=market_div)
            snapshot = parse_investor_flow_snapshot(symbol, payload)
            snapshot["requested_trade_date"] = requested_trade_date
            snapshot["resolved_trade_date"] = snapshot.get("flow_asof")
            snapshot["flow_endpoint"] = "stock_investor_current"
            snapshot["flow_date_fallback"] = True
            warnings = list(snapshot.get("warnings") or [])
            warnings.append(f"stock_investor_daily_time_limited:{requested_trade_date}")
            snapshot["warnings"] = sorted(set(str(item) for item in warnings if item))
            return snapshot

    def investor_trend_estimate(self, symbol: str) -> Dict[str, Any]:
        return self._request_json(
            "investor_trend_estimate",
            params={"MKSC_SHRN_ISCD": normalize_kr_stock_code(symbol)},
        )

    def foreign_institution_total(
        self,
        *,
        market: str = "ALL",
        sort_by_amount: bool = True,
        net_sell: bool = False,
        investor_type: str = "all",
    ) -> Dict[str, Any]:
        investor_map = {"all": "0", "foreigner": "1", "institution": "2", "etc": "3"}
        return self._request_json(
            "foreign_institution_total",
            params={
                "FID_COND_MRKT_DIV_CODE": "V",
                "FID_COND_SCR_DIV_CODE": "16449",
                "FID_INPUT_ISCD": market_input_code(market),
                "FID_DIV_CLS_CODE": "1" if sort_by_amount else "0",
                "FID_RANK_SORT_CLS_CODE": "1" if net_sell else "0",
                "FID_ETC_CLS_CODE": investor_map.get(str(investor_type).lower(), "0"),
            },
        )

    def volume_rank(self, *, market: str = "ALL", rank_by: str = "trade_value") -> Dict[str, Any]:
        rank_map = {
            "avg_volume": "0",
            "volume_increase": "1",
            "avg_turnover": "2",
            "trade_value": "3",
            "avg_trade_value_turnover": "4",
        }
        market_key = str(market or "").strip().upper()
        target_cls_code = "0" if market_key in {"KOSDAQ", "KQ", "1001"} else "111111111"
        target_exclude_code = "0" if market_key in {"KOSDAQ", "KQ", "1001"} else "1111111111"
        return self._request_json(
            "volume_rank",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": market_input_code(market),
                "FID_DIV_CLS_CODE": "1",
                "FID_BLNG_CLS_CODE": rank_map.get(str(rank_by).lower(), "3"),
                "FID_TRGT_CLS_CODE": target_cls_code,
                "FID_TRGT_EXLS_CLS_CODE": target_exclude_code,
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
            },
        )

    def fluctuation_rank(self, *, market: str = "ALL", sort: str = "up") -> Dict[str, Any]:
        sort_map = {"up": "0", "down": "1", "open_up": "2", "open_down": "3", "volatility": "4"}
        return self._request_json(
            "fluctuation_rank",
            params={
                "fid_rsfl_rate2": "",
                "fid_cond_mrkt_div_code": "J",
                "fid_cond_scr_div_code": "20170",
                "fid_input_iscd": market_input_code(market),
                "fid_rank_sort_cls_code": sort_map.get(str(sort).lower(), "0"),
                "fid_input_cnt_1": "0",
                "fid_prc_cls_code": "1",
                "fid_input_price_1": "",
                "fid_input_price_2": "",
                "fid_vol_cnt": "",
                "fid_trgt_cls_code": "0",
                "fid_trgt_exls_cls_code": "0",
                "fid_div_cls_code": "0",
                "fid_rsfl_rate1": "",
            },
        )

    def volume_power_rank(self, *, market: str = "ALL") -> Dict[str, Any]:
        return self._request_json(
            "volume_power_rank",
            params={
                "fid_trgt_exls_cls_code": "0",
                "fid_cond_mrkt_div_code": "J",
                "fid_cond_scr_div_code": "20168",
                "fid_input_iscd": market_input_code(market),
                "fid_div_cls_code": "1",
                "fid_input_price_1": "",
                "fid_input_price_2": "",
                "fid_vol_cnt": "",
                "fid_trgt_cls_code": "0",
            },
        )

    def industry_price(self, *, index_code: str = "0001") -> Dict[str, Any]:
        return self._request_json(
            "industry_price",
            params={"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": index_code},
        )

    def industry_daily_bars(
        self,
        *,
        index_code: str = "0001",
        start_date: str,
        end_date: str,
        period: str = "D",
        market_div: str = "U",
    ) -> Dict[str, Any]:
        return self._request_json(
            "industry_daily_bars",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": index_code,
                "FID_INPUT_DATE_1": start_date,
                "FID_INPUT_DATE_2": end_date,
                "FID_PERIOD_DIV_CODE": period,
            },
        )

    def vi_status(self, *, market: str = "ALL", trade_date: str) -> Dict[str, Any]:
        return self._request_json(
            "vi_status",
            params={
                "FID_DIV_CLS_CODE": "0",
                "FID_COND_SCR_DIV_CODE": "20139",
                "FID_MRKT_CLS_CODE": vi_market_code(market),
                "FID_INPUT_ISCD": "",
                "FID_RANK_SORT_CLS_CODE": "0",
                "FID_INPUT_DATE_1": trade_date,
                "FID_TRGT_CLS_CODE": "",
                "FID_TRGT_EXLS_CLS_CODE": "",
            },
        )

    def news_titles(self, *, symbol: str = "", trade_date: str = "", hour: str = "") -> Dict[str, Any]:
        return self._request_json(
            "news_title",
            params={
                "FID_NEWS_OFER_ENTP_CODE": "",
                "FID_COND_MRKT_CLS_CODE": "",
                "FID_INPUT_ISCD": normalize_kr_stock_code(symbol) if symbol else "",
                "FID_TITL_CNTT": "",
                "FID_INPUT_DATE_1": trade_date,
                "FID_INPUT_HOUR_1": hour,
                "FID_RANK_SORT_CLS_CODE": "",
                "FID_INPUT_SRNO": "",
            },
        )

    def stock_info(self, symbol: str, *, product_type: str = "300") -> Dict[str, Any]:
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "stock_info",
            params={
                "PDNO": code,
                "PRDT_TYPE_CD": str(product_type or "300"),
            },
        )

    def financial_ratio(self, symbol: str, *, market_div: str = "J", div_cls_code: str = "0") -> Dict[str, Any]:
        code = normalize_kr_stock_code(symbol)
        return self._request_json(
            "financial_ratio",
            params={
                "FID_DIV_CLS_CODE": str(div_cls_code or "0"),
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": code,
            },
        )


def parse_quote_snapshot(symbol: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    output = _output_dict(payload)
    now_kst = datetime.now(timezone.utc).astimezone().isoformat()
    quote = {
        "ticker": normalize_kr_stock_code(symbol),
        "source": "kis_openapi",
        "source_status": "ok" if output else "empty_output",
        "snapshot_at": now_kst,
        "last_price": _to_float(output.get("stck_prpr")),
        "day_change": _to_float(output.get("prdy_vrss")),
        "day_change_sign": output.get("prdy_vrss_sign"),
        "day_change_pct": _to_float(output.get("prdy_ctrt")),
        "session_open": _to_float(output.get("stck_oprc")),
        "session_high": _to_float(output.get("stck_hgpr")),
        "session_low": _to_float(output.get("stck_lwpr")),
        "volume": _to_int(output.get("acml_vol")),
        "value_traded": _to_float(output.get("acml_tr_pbmn")),
        "prev_volume_ratio": _to_float(output.get("prdy_vrss_vol_rate")),
        "weighted_avg_price": _to_float(output.get("wghn_avrg_stck_prc")),
        "market_name": output.get("rprs_mrkt_kor_name"),
        "sector_name": output.get("bstp_kor_isnm"),
        "status_code": output.get("iscd_stat_cls_code"),
        "status_warning": map_kis_status_warning(output.get("iscd_stat_cls_code")),
        "foreigner_net_qty": _to_int(output.get("frgn_ntby_qty")),
        "program_net_qty": _to_int(output.get("pgtr_ntby_qty")),
        "market_cap": _to_float(output.get("hts_avls")),
        "per": _to_float(output.get("per")),
        "pbr": _to_float(output.get("pbr")),
        "eps": _to_float(output.get("eps")),
        "bps": _to_float(output.get("bps")),
        "high_250d": _to_float(output.get("d250_hgpr")),
        "low_250d": _to_float(output.get("d250_lwpr")),
        "high_250d_gap_pct": _to_float(output.get("d250_hgpr_vrss_prpr_rate")),
        "low_250d_gap_pct": _to_float(output.get("d250_lwpr_vrss_prpr_rate")),
        "raw_output": output,
    }
    quote["warnings"] = [quote["status_warning"]] if quote.get("status_warning") else []
    return quote


def map_kis_status_warning(status_code: Any) -> Optional[str]:
    mapping = {
        "51": "management_stock",
        "52": "investment_risk",
        "53": "investment_warning",
        "54": "investment_caution",
        "58": "trading_halt",
        "59": "short_term_overheated",
    }
    return mapping.get(str(status_code or "").strip())


def parse_investor_flow_snapshot(symbol: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    rows = _output_list(payload)
    if not rows:
        first = _output_dict(payload)
        rows = [first] if first else []

    def sum_field(candidates: Iterable[str], take: int) -> Optional[float]:
        total = 0.0
        found = False
        for row in rows[:take]:
            for key in candidates:
                value = _to_float(row.get(key))
                if value is not None:
                    total += value
                    found = True
                    break
        return total if found else None

    amount_keys = {
        "foreigner": ("frgn_ntby_tr_pbmn", "frgn_ntby_pbmn"),
        "institution": ("orgn_ntby_tr_pbmn",),
        "retail": ("prsn_ntby_tr_pbmn",),
    }
    qty_keys = {
        "foreigner": ("frgn_ntby_qty",),
        "institution": ("orgn_ntby_qty",),
        "retail": ("prsn_ntby_qty",),
    }
    latest = rows[0] if rows else {}
    use_amount = any(_to_float(latest.get(key)) is not None for keys in amount_keys.values() for key in keys)

    def base(side: str, days: int) -> Optional[float]:
        return sum_field(amount_keys[side] if use_amount else qty_keys[side], days)

    def qty(side: str, days: int) -> Optional[float]:
        return sum_field(qty_keys[side], days)

    def amount(side: str, days: int) -> Optional[float]:
        return sum_field(amount_keys[side], days)

    f1, i1, r1 = base("foreigner", 1), base("institution", 1), base("retail", 1)
    f3, i3, r3 = base("foreigner", 3), base("institution", 3), base("retail", 3)
    f10, i10, r10 = base("foreigner", 10), base("institution", 10), base("retail", 10)
    asof = latest.get("stck_bsop_date") or latest.get("bsop_date")
    return {
        "ticker": normalize_kr_stock_code(symbol),
        "source": "kis_openapi",
        "source_status": "ok" if rows else "empty_output",
        "flow_unit": "KRW" if use_amount else "shares",
        "flow_asof": asof,
        "foreigner_1d": f1,
        "institution_1d": i1,
        "retail_1d": r1,
        "foreigner_3d": f3,
        "institution_3d": i3,
        "retail_3d": r3,
        "foreigner_10d": f10,
        "institution_10d": i10,
        "retail_10d": r10,
        "whale_flow_1d": (f1 + i1) if f1 is not None and i1 is not None else None,
        "whale_flow_3d": (f3 + i3) if f3 is not None and i3 is not None else None,
        "whale_flow_10d": (f10 + i10) if f10 is not None and i10 is not None else None,
        "foreigner_1d_qty": qty("foreigner", 1),
        "institution_1d_qty": qty("institution", 1),
        "retail_1d_qty": qty("retail", 1),
        "foreigner_1d_amount": amount("foreigner", 1),
        "institution_1d_amount": amount("institution", 1),
        "retail_1d_amount": amount("retail", 1),
        "raw_rows": rows,
    }


def build_kis_adapter_health(
    env: Optional[Mapping[str, str]] = None,
    *,
    config: Optional[KISConfig] = None,
) -> Dict[str, Any]:
    config = config or KISConfig.from_env(env)
    missing_credentials = []
    if not config.app_key:
        missing_credentials.append("KIS_APP_KEY")
    if not config.app_secret:
        missing_credentials.append("KIS_APP_SECRET")
    missing_account = []
    if not config.account_no:
        missing_account.append("KIS_ACCOUNT_NO")
    if not config.account_product_code:
        missing_account.append("KIS_ACCOUNT_PRODUCT_CODE")
    return {
        "source": "kis_openapi",
        "mode": config.mode,
        "rest_domain": config.rest_domain,
        "ws_domain": config.ws_domain,
        "credentials_present": not missing_credentials,
        "account_present": not missing_account,
        "missing_credentials": missing_credentials,
        "missing_account": missing_account,
        "live_network_allowed": bool(config.live_network_allowed),
        "production_default_enabled": False,
        "scanner_default_wired": False,
        "endpoint_count": len(KIS_ENDPOINTS),
        "implemented_endpoint_keys": sorted(KIS_ENDPOINTS.keys()),
        "notes": [
            "Adapter is safe for test/dry-run use; scanner production path is not wired.",
            "Set KIS_ENABLE_LIVE_CALLS=1 and pass the smoke tool live flag for actual network checks.",
            "Order submission is intentionally excluded from this adapter phase.",
        ],
    }


__all__ = [
    "KISConfig",
    "KISEndpoint",
    "KIS_ENDPOINTS",
    "KISOpenAPIClient",
    "KISOpenAPIError",
    "build_kis_adapter_health",
    "market_input_code",
    "map_kis_status_warning",
    "normalize_kr_stock_code",
    "parse_investor_flow_snapshot",
    "parse_quote_snapshot",
    "vi_market_code",
]
