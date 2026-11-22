"""
Menu domain services for querying and administering categories and food items.
Consumed by Developer 2 (Customer catalog), Developer 3 (Order item price snapshots),
and Developer 5 (Admin menu management).
Owned by Developer 1.
"""
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.core.permissions import ROLE_ADMIN, ROLE_STAFF, user_has_role

from .models import Category, FoodItem


def get_active_categories():
    """Return active categories ordered by sort_order and name."""
    return Category.objects.active().ordered()


def get_customer_menu_items(
    *,
    category: str | int | None = None,
    featured_only: bool = False,
    search_query: str | None = None,
):
    """
    Return orderable food items for the customer menu interface, with optional filters.
    """
    qs = FoodItem.objects.select_related("category").available()
    if category:
        qs = qs.by_category(category)
    if featured_only:
        qs = qs.filter(is_featured=True)
    if search_query:
        qs = qs.search(search_query)
    return qs


def get_featured_offers():
    """Return active featured food items (special meals & daily offers)."""
    return FoodItem.objects.select_related("category").featured()


@transaction.atomic
def toggle_food_availability(actor, food_item: FoodItem, is_available: bool | None = None) -> FoodItem:
    """
    Allow STAFF or ADMIN to toggle or explicitly set a food item's availability (PRD §3 & §4.2).
    """
    if not user_has_role(actor, ROLE_STAFF, ROLE_ADMIN):
        raise PermissionDenied("Only restaurant staff or administrators can update food availability.")

    food_item.is_available = (not food_item.is_available) if is_available is None else bool(is_available)
    food_item.save(update_fields=["is_available", "updated_at"])
    return food_item


@transaction.atomic
def update_food_price(actor, food_item: FoodItem, new_price: Decimal | str | float) -> FoodItem:
    """
    Allow ADMIN (or STAFF) to update a food item's price.
    Note: Existing orders retain their snapshotted unit_price in orders_orderitem.
    """
    if not user_has_role(actor, ROLE_STAFF, ROLE_ADMIN):
        raise PermissionDenied("Only restaurant staff or administrators can update food prices.")

    food_item.price = Decimal(str(new_price))
    food_item.full_clean()
    food_item.save(update_fields=["price", "updated_at"])
    return food_item
