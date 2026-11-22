"""
Web views for Menu browsing and Staff/Admin quick availability toggling.
Renders Developer 2's templates when present, returns JSON when Accept: application/json
is requested, and renders a built-in HTML catalog page in the browser otherwise.
Owned by Developer 1.
"""
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.utils.html import escape
from django.views.decorators.http import require_GET, require_POST

from apps.core.permissions import staff_or_admin_required

from .models import Category, FoodItem
from .serializers import CategoryDetailSerializer, CategorySerializer, FoodItemSerializer
from .services import (
    get_active_categories,
    get_customer_menu_items,
    get_featured_offers,
    toggle_food_availability,
)


def _render_or_fallback(
    request: HttpRequest,
    template_names: list[str],
    context: dict,
    json_payload: dict,
    html_fallback: str,
    status: int = 200,
) -> HttpResponse:
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse(json_payload, status=status)
    try:
        template = select_template(template_names)
        return HttpResponse(template.render(context, request), status=status)
    except TemplateDoesNotExist:
        return HttpResponse(html_fallback, status=status)


@require_GET
def menu_list_view(request: HttpRequest) -> HttpResponse:
    category_slug = request.GET.get("category")
    search_query = request.GET.get("q") or request.GET.get("search")
    featured_only = request.GET.get("featured", "").lower() in ("1", "true", "yes")

    categories = get_active_categories()
    items = get_customer_menu_items(
        category=category_slug,
        featured_only=featured_only,
        search_query=search_query,
    )
    featured_offers = get_featured_offers()

    rows = "".join(
        f"<li><strong>{escape(i.name)}</strong> ({escape(i.category.name)}) — "
        f"<span style='color:#f59e0b;font-weight:700;'>{escape(i.formatted_price)}</span> "
        f"· <a href='/menu/items/{escape(i.slug)}/' style='color:#38bdf8;'>Details</a></li>"
        for i in items
    )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Menu Catalog — Cho Restaurant</title></head>
<body style="font-family:system-ui,sans-serif;background:#0f172a;color:#f8fafc;padding:2rem;">
    <div style="max-width:800px;margin:0 auto;background:#1e293b;padding:1.75rem;border-radius:0.75rem;border:1px solid #334155;">
        <p><a href="/" style="color:#38bdf8;text-decoration:none;">← Back to Foundation Portal</a></p>
        <h2 style="color:#f59e0b;margin-top:0;">Cho Restaurant Menu ({items.count()} Available Items)</h2>
        <ul style="line-height:2;">{rows or "<li>No items match your filter.</li>"}</ul>
    </div>
</body></html>"""

    return _render_or_fallback(
        request,
        ["customer/menu_list.html", "customer/menu.html", "menu/menu_list.html"],
        {
            "categories": categories,
            "food_items": items,
            "featured_offers": featured_offers,
            "selected_category": category_slug,
            "search_query": search_query or "",
        },
        {
            "categories": CategorySerializer(categories, many=True, context={"request": request}).data,
            "food_items": FoodItemSerializer(items, many=True, context={"request": request}).data,
            "featured_offers": FoodItemSerializer(
                featured_offers, many=True, context={"request": request}
            ).data,
        },
        html,
    )


@require_GET
def category_detail_view(request: HttpRequest, slug: str) -> HttpResponse:
    category = get_object_or_404(Category.objects.active(), slug=slug)
    items = get_customer_menu_items(category=category.slug)
    rows = "".join(
        f"<li><strong>{escape(i.name)}</strong> — {escape(i.formatted_price)}</li>" for i in items
    )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{escape(category.name)} — Cho Restaurant</title></head>
<body style="font-family:system-ui,sans-serif;background:#0f172a;color:#f8fafc;padding:2rem;">
    <div style="max-width:700px;margin:0 auto;background:#1e293b;padding:1.75rem;border-radius:0.75rem;">
        <p><a href="/menu/" style="color:#38bdf8;">← All Menu Items</a></p>
        <h2 style="color:#f59e0b;">{escape(category.name)}</h2>
        <p>{escape(category.description or "")}</p>
        <ul>{rows}</ul>
    </div>
</body></html>"""
    return _render_or_fallback(
        request,
        ["customer/category_detail.html", "menu/category_detail.html"],
        {"category": category, "food_items": items},
        CategoryDetailSerializer(category, context={"request": request}).data,
        html,
    )


@require_GET
def food_item_detail_view(request: HttpRequest, slug: str) -> HttpResponse:
    item = get_object_or_404(FoodItem.objects.select_related("category").available(), slug=slug)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{escape(item.name)} — Cho Restaurant</title></head>
<body style="font-family:system-ui,sans-serif;background:#0f172a;color:#f8fafc;padding:2rem;">
    <div style="max-width:700px;margin:0 auto;background:#1e293b;padding:1.75rem;border-radius:0.75rem;">
        <p><a href="/menu/" style="color:#38bdf8;">← Back to Menu</a></p>
        <h2 style="color:#f59e0b;">{escape(item.name)}</h2>
        <p><strong>Category:</strong> {escape(item.category.name)}</p>
        <p><strong>Price:</strong> {escape(item.formatted_price)}</p>
        <p><strong>Prep Time:</strong> {item.prep_time_minutes} minutes</p>
        <p>{escape(item.description or "")}</p>
    </div>
</body></html>"""
    return _render_or_fallback(
        request,
        ["customer/food_detail.html", "menu/food_detail.html"],
        {"food_item": item},
        FoodItemSerializer(item, context={"request": request}).data,
        html,
    )


@staff_or_admin_required
@require_POST
def staff_toggle_availability_view(request: HttpRequest, slug: str) -> HttpResponse:
    food_item = get_object_or_404(FoodItem, slug=slug)
    food_item = toggle_food_availability(request.user, food_item)
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse(
            {
                "slug": food_item.slug,
                "is_available": food_item.is_available,
            }
        )
    next_url = request.POST.get("next") or "menu:menu-list"
    return redirect(next_url)
