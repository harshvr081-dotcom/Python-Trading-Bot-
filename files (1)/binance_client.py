"""
Binance Futures Testnet - API Client Layer
Handles all HTTP communication, signing, and error handling.
"""

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response or an error payload."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceFuturesClient:
    """
    Low-level REST client for Binance USDT-M Futures Testnet.

    Responsibilities:
      - Build and sign requests (HMAC-SHA256)
      - Send HTTP requests with retries
      - Parse and raise structured API errors
      - Log every request and response
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict) -> str:
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _request(
        self, method: str, path: str, signed: bool = False, **kwargs
    ) -> Any:
        url = BASE_URL + path
        params = kwargs.pop("params", {}) or {}

        if signed:
            params["timestamp"] = self._timestamp()
            params["signature"] = self._sign(params)

        logger.debug("→ %s %s  params=%s", method.upper(), url, params)

        try:
            response = self.session.request(
                method,
                url,
                params=params if method.upper() == "GET" else None,
                data=params if method.upper() == "POST" else None,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network failure: %s", exc)
            raise ConnectionError(f"Could not reach Binance Testnet: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise TimeoutError("Request to Binance Testnet timed out.") from exc

        logger.debug(
            "← %s %s  body=%s", response.status_code, url, response.text[:500]
        )

        try:
            payload = response.json()
        except ValueError:
            response.raise_for_status()
            return {}

        if isinstance(payload, dict) and "code" in payload and payload["code"] != 200:
            raise BinanceAPIError(payload["code"], payload.get("msg", "Unknown error"))

        if not response.ok:
            raise BinanceAPIError(response.status_code, response.text)

        return payload

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_exchange_info(self) -> dict:
        """Fetch exchange metadata (symbol rules, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_symbol_info(self, symbol: str) -> dict | None:
        """Return the exchange-info entry for a single symbol, or None."""
        info = self.get_exchange_info()
        for s in info.get("symbols", []):
            if s["symbol"] == symbol.upper():
                return s
        return None

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Place a MARKET or LIMIT order on USDT-M Futures.

        Args:
            symbol:        Trading pair, e.g. "BTCUSDT"
            side:          "BUY" or "SELL"
            order_type:    "MARKET" or "LIMIT"
            quantity:      Contract quantity
            price:         Required for LIMIT orders
            time_in_force: "GTC" / "IOC" / "FOK" (LIMIT only)

        Returns:
            Raw order response dict from Binance.
        """
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
        }

        if order_type.upper() == "LIMIT":
            if price is None:
                raise ValueError("Price is required for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = time_in_force

        logger.info("Placing order: %s", params)
        return self._request("POST", "/fapi/v1/order", signed=True, params=params)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Query an existing order by ID."""
        params = {"symbol": symbol.upper(), "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", signed=True, params=params)

    def get_account(self) -> dict:
        """Fetch account information (balances, positions)."""
        return self._request("GET", "/fapi/v2/account", signed=True)
