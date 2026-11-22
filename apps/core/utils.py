"""
Shared utility functions for reference generation, money rounding, Haversine distance,
and standardized JSON responses.
Owned by Developer 1.
"""
import math
import secrets
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

MONEY_QUANTIZE = Decimal("0.01")


def quantize_money(value: Decimal | int | float | str) -> Decimal:
    """
    Convert a monetary amount to a 2-decimal-place Decimal using ROUND_HALF_UP.
    Matches schema.sql rule: money = NUMERIC(12,2); never float.
    """
    return Decimal(str(value)).quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)


def format_currency(
    amount: Decimal | int | float | str,
    currency_symbol: str | None = None,
) -> str:
    """Format a monetary amount with the configured currency symbol (default GH₵)."""
    symbol = currency_symbol or getattr(settings, "CURRENCY_SYMBOL", "GH₵")
    quantized = quantize_money(amount)
    return f"{symbol}{quantized:,.2f}"


def generate_unique_reference(prefix: str = "ORD") -> str:
    """
    Generate a unique reference string fitting VARCHAR(24) in schema.sql.
    Example: ORD-20261122-8F3A2C (19 chars).
    """
    clean_prefix = (prefix or "REF").upper()[:4]
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"{clean_prefix}-{date_part}-{random_part}"


def haversine_distance_km(
    lat1: Decimal | float,
    lng1: Decimal | float,
    lat2: Decimal | float,
    lng2: Decimal | float,
) -> Decimal:
    """
    Compute the great-circle distance in kilometers between two GPS points
    using the Haversine formula (Architecture §4.5).
    Returns a Decimal rounded to 2 decimal places.
    """
    r_earth_km = 6371.0088

    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lng2) - float(lng1))

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = r_earth_km * c
    return Decimal(str(distance)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def api_response(
    data=None,
    message: str = "",
    status_code: int = 200,
    errors=None,
) -> JsonResponse:
    """Standardized JSON response helper for non-DRF views and shared API contracts."""
    payload = {
        "success": 200 <= status_code < 300,
        "message": message,
        "data": data,
    }
    if errors is not None:
        payload["errors"] = errors
    return JsonResponse(payload, status=status_code)
