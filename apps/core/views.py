"""
Core health check, API discovery, and Developer 1 Foundation Portal views.
Owned by Developer 1.
"""
from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.urls import reverse
from django.utils.html import escape
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import Address, RiderProfile, User
from apps.core.models import RestaurantSettings
from apps.menu.models import Category, FoodItem


def foundation_home_view(request: HttpRequest) -> HttpResponse:
    """
    Root landing view (/).
    If Developer 2 has added `templates/customer/home.html` or `customer/index.html`,
    renders that template automatically. Otherwise renders Developer 1's interactive
    Foundation & Backend Verification Portal so Developer 1 can view and demonstrate
    authentication, roles, delivery addresses, and menu data in the browser.
    """
    categories = Category.objects.active().ordered().prefetch_related("food_items")
    featured_items = FoodItem.objects.select_related("category").featured()
    rest_settings = RestaurantSettings.get_solo()

    try:
        template = select_template(["customer/home.html", "customer/index.html"])
        return HttpResponse(
            template.render(
                {
                    "categories": categories,
                    "featured_offers": featured_items,
                    "restaurant_settings": rest_settings,
                },
                request,
            )
        )
    except TemplateDoesNotExist:
        pass

    user = request.user
    is_auth = user.is_authenticated
    user_Count = User.objects.count()
    cat_count = Category.objects.count()
    item_count = FoodItem.objects.count()
    addr_count = Address.objects.count()
    rider_count = RiderProfile.objects.count()

    if is_auth:
        user_badge = (
            f'<span class="badge badge-role">{escape(user.username)} ({escape(user.role)})</span> '
            f'<a href="{reverse("accounts:profile")}" class="btn btn-sm">My Profile</a> '
            f'<a href="{reverse("accounts:addresses")}" class="btn btn-sm">Addresses</a> '
            f'<a href="{reverse("accounts:logout")}" class="btn btn-sm btn-outline">Logout</a>'
        )
    else:
        user_badge = (
            f'<a href="{reverse("accounts:login")}" class="btn btn-sm">Login</a> '
            f'<a href="{reverse("accounts:register")}" class="btn btn-sm btn-outline">Register</a>'
        )

    cat_cards_html = []
    for cat in categories:
        items_html = []
        for item in cat.food_items.all():
            avail_badge = (
                '<span class="tag tag-green">Available</span>'
                if item.is_available
                else '<span class="tag tag-red">Sold Out</span>'
            )
            feat_badge = '<span class="tag tag-gold">Featured</span>' if item.is_featured else ""
            items_html.append(
                f"""
                <div class="food-row">
                    <div>
                        <strong>{escape(item.name)}</strong> {avail_badge} {feat_badge}
                        <div class="muted">{escape(item.description or "")} · Prep: {item.prep_time_minutes} mins</div>
                    </div>
                    <div class="price">{escape(item.formatted_price)}</div>
                </div>
                """
            )
        cat_cards_html.append(
            f"""
            <div class="card">
                <h3>{escape(cat.name)} <span class="muted">({cat.food_items.count()} items)</span></h3>
                <p class="muted">{escape(cat.description or "")}</p>
                <div class="food-list">{"".join(items_html) or '<p class="muted">No items yet.</p>'}</div>
            </div>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(rest_settings.restaurant_name)} — Developer 1 Foundation Portal</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #f59e0b;
            --green: #10b981;
            --red: #ef4444;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
        }}
        .navbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            flex-wrap: wrap;
            gap: 1rem;
        }}
        .brand {{
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--accent);
            text-decoration: none;
        }}
        .container {{
            max-width: 1150px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            padding: 1.25rem;
        }}
        .card h3 {{ margin-top: 0; margin-bottom: 0.5rem; }}
        .stat-num {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
        .muted {{ color: var(--muted); font-size: 0.9rem; }}
        .btn {{
            display: inline-block;
            background: var(--accent);
            color: #0f172a;
            font-weight: 600;
            padding: 0.5rem 0.9rem;
            border-radius: 0.5rem;
            text-decoration: none;
            font-size: 0.9rem;
        }}
        .btn-outline {{
            background: transparent;
            color: var(--text);
            border: 1px solid var(--border);
        }}
        .btn-sm {{ padding: 0.35rem 0.75rem; font-size: 0.85rem; }}
        .badge-role {{
            background: #3b82f6;
            color: white;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 0.5rem;
        }}
        .tag {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 0.35rem;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 0.35rem;
        }}
        .tag-green {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .tag-red {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}
        .tag-gold {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .food-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 0.75rem 0;
            border-top: 1px solid var(--border);
            gap: 1rem;
        }}
        .price {{ font-weight: 700; color: var(--accent); white-space: nowrap; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        th, td {{
            text-align: left;
            padding: 0.55rem 0.5rem;
            border-bottom: 1px solid var(--border);
        }}
        code {{
            background: #0f172a;
            padding: 0.15rem 0.4rem;
            border-radius: 0.3rem;
            color: #38bdf8;
        }}
        a.link {{ color: #38bdf8; text-decoration: none; }}
        a.link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <nav class="navbar">
        <div>
            <a href="/" class="brand">{escape(rest_settings.restaurant_name)}</a>
            <span class="muted" style="margin-left:0.75rem;">Developer 1 Foundation ({escape(rest_settings.operating_country)} · {escape(rest_settings.currency)})</span>
        </div>
        <div>
            {user_badge}
            <a href="/admin/" class="btn btn-sm btn-outline" style="margin-left:0.4rem;">Django Admin</a>
        </div>
    </nav>

    <div class="container">
        <div class="grid">
            <div class="card">
                <div class="muted">Users &amp; Roles (`accounts_user`)</div>
                <div class="stat-num">{user_Count}</div>
                <div class="muted">CUSTOMER · STAFF · RIDER · ADMIN</div>
            </div>
            <div class="card">
                <div class="muted">Menu Categories (`menu_category`)</div>
                <div class="stat-num">{cat_count}</div>
                <div class="muted">{item_count} Food Items (`menu_fooditem`)</div>
            </div>
            <div class="card">
                <div class="muted">Saved Addresses (`accounts_address`)</div>
                <div class="stat-num">{addr_count}</div>
                <div class="muted">Default Country: {escape(rest_settings.operating_country)}</div>
            </div>
            <div class="card">
                <div class="muted">Dispatch Riders (`accounts_riderprofile`)</div>
                <div class="stat-num">{rider_count}</div>
                <div class="muted">Delivery Mode: {escape(rest_settings.delivery_fee_mode)}</div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <h3>Developer 1 Quick Links &amp; Views</h3>
                <table>
                    <tr><td><a class="link" href="/accounts/login/">/accounts/login/</a></td><td>Login (Username or Email)</td></tr>
                    <tr><td><a class="link" href="/accounts/register/">/accounts/register/</a></td><td>Customer Registration</td></tr>
                    <tr><td><a class="link" href="/accounts/profile/">/accounts/profile/</a></td><td>Customer Profile &amp; Notification Prefs</td></tr>
                    <tr><td><a class="link" href="/accounts/addresses/">/accounts/addresses/</a></td><td>Saved Delivery Addresses (Ghana/GPS)</td></tr>
                    <tr><td><a class="link" href="/menu/">/menu/</a></td><td>Food Catalog &amp; Availability</td></tr>
                    <tr><td><a class="link" href="/admin/">/admin/</a></td><td>Django Admin (Menu, Users, Settings)</td></tr>
                </table>
            </div>
            <div class="card">
                <h3>REST API Contracts &amp; Demo Credentials</h3>
                <table>
                    <tr><td><a class="link" href="/api/">/api/</a> · <a class="link" href="/api/health/">/api/health/</a></td><td>API Discovery &amp; Health Check</td></tr>
                    <tr><td><a class="link" href="/api/menu/categories/">/api/menu/categories/</a></td><td>Categories REST Endpoint</td></tr>
                    <tr><td><a class="link" href="/api/menu/items/">/api/menu/items/</a></td><td>Food Items REST Endpoint</td></tr>
                    <tr><td><a class="link" href="/api/menu/featured/">/api/menu/featured/</a></td><td>Featured Daily Offers</td></tr>
                </table>
                <p class="muted" style="margin-top:0.85rem; margin-bottom:0.25rem;"><strong>Seeded Demo Accounts:</strong></p>
                <div class="muted">
                    <code>admin_cho</code> / <code>AdminPass123!</code> (ADMIN)<br>
                    <code>staff_ama</code> / <code>StaffPass123!</code> (STAFF)<br>
                    <code>rider_kofi</code> / <code>RiderPass123!</code> (RIDER)<br>
                    <code>customer_akua</code> / <code>CustomerPass123!</code> (CUSTOMER)
                </div>
            </div>
        </div>

        <h2>Live Menu Data (`apps.menu`)</h2>
        <div class="grid-2">
            {"".join(cat_cards_html)}
        </div>
    </div>
</body>
</html>"""
    return HttpResponse(html)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check_view(request):
    """
    Health check endpoint verifying database connectivity, Redis reachability,
    media storage backend (Cloudinary vs local), and localization settings.
    """
    db_ok = False
    db_engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            db_ok = True
    except Exception:
        db_ok = False

    redis_url = getattr(settings, "REDIS_URL", "")
    redis_ok = False
    if redis_url:
        try:
            import redis as redis_client

            client = redis_client.from_url(
                redis_url,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
            )
            redis_ok = bool(client.ping())
        except Exception:
            redis_ok = False

    storage_backend = (
        getattr(settings, "STORAGES", {}).get("default", {}).get("BACKEND", "")
    )
    cloudinary_configured = bool(getattr(settings, "CLOUDINARY_URL", ""))

    return Response(
        {
            "status": "ok" if db_ok else "degraded",
            "restaurant": settings.RESTAURANT_NAME,
            "country": settings.DEFAULT_COUNTRY,
            "currency": settings.DEFAULT_CURRENCY,
            "currency_symbol": settings.CURRENCY_SYMBOL,
            "database_connected": db_ok,
            "database_engine": db_engine,
            "redis_configured": bool(redis_url),
            "redis_connected": redis_ok,
            "cloudinary_configured": cloudinary_configured,
            "media_storage_backend": storage_backend,
        },
        status=200 if db_ok else 503,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root_view(request):
    """Root API index exposing Developer 1's foundation endpoints."""
    return Response(
        {
            "project": "Restaurant Ordering & Delivery Management System",
            "country": settings.DEFAULT_COUNTRY,
            "currency": settings.DEFAULT_CURRENCY,
            "endpoints": {
                "health": request.build_absolute_uri(reverse("health-check")),
                "auth_register": request.build_absolute_uri(reverse("accounts-api:register")),
                "auth_login": request.build_absolute_uri(reverse("accounts-api:login")),
                "auth_logout": request.build_absolute_uri(reverse("accounts-api:logout")),
                "profile": request.build_absolute_uri(reverse("accounts-api:profile")),
                "addresses": request.build_absolute_uri(reverse("accounts-api:address-list")),
                "rider_profile": request.build_absolute_uri(reverse("accounts-api:rider-profile")),
                "riders": request.build_absolute_uri(reverse("accounts-api:rider-list")),
                "menu_categories": request.build_absolute_uri(reverse("menu-api:category-list")),
                "menu_items": request.build_absolute_uri(reverse("menu-api:fooditem-list")),
                "menu_featured": request.build_absolute_uri(reverse("menu-api:featured-items")),
            },
        }
    )
