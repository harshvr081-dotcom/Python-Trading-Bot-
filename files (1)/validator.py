"""
Input validation for trading orders.
Validates user-supplied CLI arguments before they reach the API layer.
"""

import logging

logger = logging.getLogger("trading_bot.validator")

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


class ValidationError(ValueError):
    """Raised when user-supplied trading parameters fail validation."""


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
) -> None:
    """
    Validate order parameters and raise ValidationError with a clear message
    on the first problem found.
    """
    if not symbol or not symbol.isalpha():
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Must be alphabetic (e.g. BTCUSDT)."
        )

    if side.upper() not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )

    if order_type.upper() not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )

    if quantity <= 0:
        raise ValidationError(
            f"Quantity must be a positive number, got {quantity}."
        )

    if order_type.upper() == "LIMIT":
        if price is None:
            raise ValidationError("--price is required for LIMIT orders.")
        if price <= 0:
            raise ValidationError(
                f"Price must be a positive number, got {price}."
            )

    if order_type.upper() == "MARKET" and price is not None:
        logger.warning(
            "Price %.4f supplied for a MARKET order — it will be ignored.", price
        )

    logger.debug(
        "Validation passed: symbol=%s side=%s type=%s qty=%s price=%s",
        symbol, side, order_type, quantity, price,
    )
