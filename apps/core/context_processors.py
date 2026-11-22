"""
Template context processors exposing shared restaurant metadata, localization defaults
(Ghana & GHS), and role flags to all templates.
"""
from django.conf import settings


def restaurant_context(request) -> dict:
    user = getattr(request, "user", None)
    is_auth = bool(user and getattr(user, "is_authenticated", False))
    user_role = getattr(user, "role", None) if is_auth else None

    return {
        "RESTAURANT_NAME": getattr(settings, "RESTAURANT_NAME", "Cho Restaurant"),
        "DEFAULT_COUNTRY": getattr(settings, "DEFAULT_COUNTRY", "Ghana"),
        "DEFAULT_CURRENCY": getattr(settings, "DEFAULT_CURRENCY", "GHS"),
        "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "GH₵"),
        "CURRENT_USER_ROLE": user_role,
        "IS_CUSTOMER": is_auth and user_role == "CUSTOMER",
        "IS_STAFF_ROLE": is_auth and user_role in ("STAFF", "ADMIN"),
        "IS_RIDER": is_auth and user_role == "RIDER",
        "IS_ADMIN_ROLE": is_auth and (user_role == "ADMIN" or getattr(user, "is_superuser", False)),
    }
