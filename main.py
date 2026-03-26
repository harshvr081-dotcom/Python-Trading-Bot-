#!/usr/bin/env python3
"""
Trading Bot CLI — Binance Futures Testnet (USDT-M)

Usage examples
--------------
# Place a MARKET BUY for 0.01 BTC
python main.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Place a LIMIT SELL for 0.01 BTC at $90,000
python main.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 90000

# Use environment variables for credentials (recommended)
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
python main.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Or pass credentials directly (less secure)
python main.py --api-key KEY --api-secret SECRET --symbol BTCUSDT ...
"""

import argparse
import logging
import os
import sys

from binance_client import BinanceAPIError, BinanceFuturesClient
from log_config import setup_logging
from validator import ValidationError, validate_order_params

logger = logging.getLogger("trading_bot.cli")


# ---------------------------------------------------------------------------
# Output / formatting helpers
# ---------------------------------------------------------------------------

def _hr(char: str = "─", width: int = 60) -> str:
    return char * width


def print_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
) -> None:
    print()
    print(_hr())
    print("  ORDER REQUEST SUMMARY")
    print(_hr())
    print(f"  Symbol    : {symbol.upper()}")
    print(f"  Side      : {side.upper()}")
    print(f"  Type      : {order_type.upper()}")
    print(f"  Quantity  : {quantity}")
    if price is not None:
        print(f"  Price     : {price}")
    print(_hr())
    print()


def print_order_response(response: dict) -> None:
    print(_hr())
    print("  ORDER RESPONSE")
    print(_hr())
    print(f"  Order ID      : {response.get('orderId', 'N/A')}")
    print(f"  Client Order  : {response.get('clientOrderId', 'N/A')}")
    print(f"  Symbol        : {response.get('symbol', 'N/A')}")
    print(f"  Side          : {response.get('side', 'N/A')}")
    print(f"  Type          : {response.get('type', 'N/A')}")
    print(f"  Status        : {response.get('status', 'N/A')}")
    print(f"  Orig Qty      : {response.get('origQty', 'N/A')}")
    print(f"  Executed Qty  : {response.get('executedQty', 'N/A')}")

    avg_price = response.get("avgPrice") or response.get("price", "N/A")
    print(f"  Avg Price     : {avg_price}")

    if "updateTime" in response:
        import datetime
        ts = datetime.datetime.utcfromtimestamp(response["updateTime"] / 1000)
        print(f"  Update Time   : {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    print(_hr())
    print()


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place orders on Binance Futures Testnet (USDT-M)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Credentials — prefer env vars, allow CLI override
    creds = parser.add_argument_group("API Credentials")
    creds.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY", ""),
        help="Binance API key (or set BINANCE_API_KEY env var)",
    )
    creds.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET", ""),
        help="Binance API secret (or set BINANCE_API_SECRET env var)",
    )

    # Order parameters
    order = parser.add_argument_group("Order Parameters")
    order.add_argument(
        "--symbol", required=True,
        help="Trading pair symbol, e.g. BTCUSDT",
    )
    order.add_argument(
        "--side", required=True, choices=["BUY", "SELL"],
        type=str.upper,
        help="Order side: BUY or SELL",
    )
    order.add_argument(
        "--type", dest="order_type", required=True,
        choices=["MARKET", "LIMIT"], type=str.upper,
        help="Order type: MARKET or LIMIT",
    )
    order.add_argument(
        "--quantity", required=True, type=float,
        help="Order quantity (e.g. 0.01 for 0.01 BTC)",
    )
    order.add_argument(
        "--price", type=float, default=None,
        help="Limit price (required for LIMIT orders)",
    )
    order.add_argument(
        "--tif", dest="time_in_force", default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time-in-force for LIMIT orders (default: GTC)",
    )

    # Misc
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable DEBUG-level console output",
    )

    return parser


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(level=logging.DEBUG if args.verbose else logging.WARNING)

    logger.info(
        "Bot started: symbol=%s side=%s type=%s qty=%s price=%s",
        args.symbol, args.side, args.order_type, args.quantity, args.price,
    )

    # --- Credential check ---------------------------------------------------
    if not args.api_key or not args.api_secret:
        print(
            "ERROR: API credentials are required.\n"
            "  Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables,\n"
            "  or pass --api-key / --api-secret on the command line.",
            file=sys.stderr,
        )
        return 1

    # --- Input validation ---------------------------------------------------
    try:
        validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )
    except ValidationError as exc:
        print(f"VALIDATION ERROR: {exc}", file=sys.stderr)
        logger.error("Validation failed: %s", exc)
        return 2

    # --- Print request summary ----------------------------------------------
    print_order_summary(
        symbol=args.symbol,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
    )

    # --- Place order --------------------------------------------------------
    client = BinanceFuturesClient(api_key=args.api_key, api_secret=args.api_secret)

    try:
        response = client.place_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as exc:
        print(f"VALIDATION ERROR: {exc}", file=sys.stderr)
        logger.error("Validation error: %s", exc)
        return 2
    except BinanceAPIError as exc:
        print(f"API ERROR [{exc.code}]: {exc.message}", file=sys.stderr)
        logger.error("API error: %s", exc)
        return 3
    except ConnectionError as exc:
        print(f"NETWORK ERROR: {exc}", file=sys.stderr)
        logger.error("Network error: %s", exc)
        return 4
    except TimeoutError as exc:
        print(f"TIMEOUT: {exc}", file=sys.stderr)
        logger.error("Timeout: %s", exc)
        return 4
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        logger.exception("Unexpected error")
        return 5

    # --- Print response & success message -----------------------------------
    print_order_response(response)

    status = response.get("status", "UNKNOWN")
    order_id = response.get("orderId", "N/A")

    if status in ("FILLED", "NEW", "PARTIALLY_FILLED"):
        print(f"✅  Order placed successfully!  (orderId={order_id}, status={status})")
        logger.info("Order placed successfully: orderId=%s status=%s", order_id, status)
    else:
        print(f"⚠️  Order submitted but status is '{status}'. Check your dashboard.")
        logger.warning("Unexpected order status '%s' for orderId=%s", status, order_id)

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
