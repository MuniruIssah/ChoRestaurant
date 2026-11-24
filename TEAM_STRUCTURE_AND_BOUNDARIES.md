# Cho Restaurant — Master Project Structure & Developer Boundaries Guide

> **IMPORTANT RULE FOR ALL 5 DEVELOPERS:**  
> The folder structure, Django app names, settings split, custom `User` model, and core utilities have already been initialized by **Developer 1**.  
> **Do NOT rename, move, or delete existing folders or apps.** Every developer must work strictly inside their assigned directories and branch (`feature/dev2-...`, `feature/dev3-...`, `feature/dev4-...`, `feature/dev5-...`).

---

## 1. Complete Repository Tree & Ownership Map

Legend:
- `[LOCKED - DEV 1]` = Completed by Developer 1. **Do NOT modify without a coordinated PR reviewed by Developer 1.**
- `[SHARED - ADD ONLY]` = Only add your app's `path(...)` include when mounting your URLs.
- `[DEV 2]`, `[DEV 3]`, `[DEV 4]`, `[DEV 5]` = Owned by that developer. Create and update your files inside these folders.

```text
ChoRestaurant/
├── manage.py                         [LOCKED - DEV 1]
├── start.bat                         [LOCKED - DEV 1] (Local launcher & data seeder)
├── requirements.txt                  [LOCKED - DEV 1] (Coordinate new packages via PR)
├── pyproject.toml                    [LOCKED - DEV 1]
├── .env.example                      [LOCKED - DEV 1]
├── .gitignore                        [LOCKED - DEV 1]
├── README.md                         [LOCKED - DEV 1]
│
├── config/
│   ├── __init__.py                   [LOCKED - DEV 1] (Loads Celery app)
│   ├── celery.py                     [LOCKED - DEV 1] (Autodiscovers tasks.py in all apps)
│   ├── wsgi.py                       [LOCKED - DEV 1]
│   ├── asgi.py                       [DEV 4 UPDATES]  (Dev 4 adds websocket_urlpatterns here)
│   ├── urls.py                       [SHARED - ADD ONLY] (Each dev mounts their app's urls/api_urls)
│   └── settings/
│       ├── __init__.py               [LOCKED - DEV 1]
│       ├── base.py                   [LOCKED - DEV 1] (All 10 apps already in INSTALLED_APPS!)
│       ├── dev.py                    [LOCKED - DEV 1]
│       └── prod.py                   [LOCKED - DEV 1]
│
├── apps/
│   ├── core/                         [LOCKED - DEV 1] (Base models, RBAC permissions, MapsFacade, utils)
│   │   ├── models.py                 (TimeStampedModel, SoftDeleteModel, RestaurantSettings)
│   │   ├── permissions.py            (Role mixins, @role_required decorators, DRF permissions)
│   │   ├── maps.py                   (MapsFacade: Haversine distance, radius check, ETA)
│   │   ├── utils.py                  (quantize_money, format_currency, generate_unique_reference)
│   │   ├── context_processors.py     (Global template variables: CURRENCY_SYMBOL, roles, etc.)
│   │   └── views.py                  (Foundation portal & /api/health/)
│   │
│   ├── accounts/                     [LOCKED - DEV 1] (Custom User, Profiles, Addresses, Riders)
│   │   ├── models.py                 (User, CustomerProfile, Address, RiderProfile)
│   │   ├── services.py               (register_user, authenticate_user, get_available_riders, etc.)
│   │   ├── serializers.py            (UserSerializer, AddressSerializer, RiderProfileSerializer)
│   │   ├── forms.py                  (Registration, Login, Profile, Address, Rider forms)
│   │   ├── views.py & urls.py        (/accounts/... web endpoints)
│   │   └── api_views.py & api_urls.py (/api/accounts/... REST endpoints)
│   │
│   ├── menu/                         [LOCKED - DEV 1] (Food Categories & Food Items)
│   │   ├── models.py                 (Category, FoodItem)
│   │   ├── services.py               (get_active_categories, get_customer_menu_items, toggle_food_availability)
│   │   ├── serializers.py            (CategorySerializer, FoodItemSerializer)
│   │   ├── forms.py                  (CategoryForm, FoodItemForm)
│   │   ├── views.py & urls.py        (/menu/... web endpoints)
│   │   └── api_views.py & api_urls.py (/api/menu/... REST endpoints)
│   │
│   ├── orders/                       [DEV 3 OWNS] (Currently has __init__.py & apps.py stub)
│   ├── payments/                     [DEV 3 OWNS] (Currently has __init__.py & apps.py stub)
│   ├── delivery/                     [DEV 4 OWNS] (Currently has __init__.py & apps.py stub)
│   ├── notifications/                [DEV 4 OWNS] (Currently has __init__.py & apps.py stub)
│   ├── promotions/                   [DEV 5 OWNS] (Currently has __init__.py & apps.py stub)
│   ├── reviews/                      [DEV 5 OWNS] (Currently has __init__.py & apps.py stub)
│   └── dashboard/                    [DEV 5 OWNS] (Currently has __init__.py & apps.py stub)
│
├── templates/
│   ├── base.html                     [DEV 2 & DEV 5 COORDINATE] (Shared layout)
│   ├── customer/                     [DEV 2 OWNS] (Customer website HTML templates)
│   ├── rider/                        [DEV 4 OWNS] (Rider dashboard & live GPS page templates)
│   ├── staff/                        [DEV 5 OWNS] (Restaurant staff order prep templates)
│   └── admin/                        [DEV 5 OWNS] (Custom management dashboard templates)
│
├── static/
│   ├── css/
│   │   ├── customer/                 [DEV 2 OWNS]
│   │   ├── admin/                    [DEV 5 OWNS]
│   │   └── shared/                   [TEAM SHARED]
│   ├── js/
│   │   ├── customer/                 [DEV 2 OWNS]
│   │   ├── admin/                    [DEV 5 OWNS]
│   │   └── shared/                   [TEAM SHARED]
│   └── img/                          [DEV 2 OWNS]
│
├── tests/                            [DEV 5 COORDINATES] (Cross-app end-to-end integration tests)
└── docs/                             [REFERENCE DOCS]
    ├── ARCHITECTURE.md
    ├── PRD.md
    ├── schema.sql
    ├── API_DOCUMENTATION.md
    ├── GIT_WORKFLOW.md
    └── DEVELOPER_GUIDE.md
```

---

## 2. Detailed Instructions Per Developer (What to Create, Update, and NOT Touch)

---

### 👨‍💻 DEVELOPER 2 — Customer Website, Menu UI & Shopping Experience
**Branch:** `feature/dev2-customer-website`  
**Assigned Folders:** `templates/customer/`, `static/css/customer/`, `static/js/customer/`, `static/img/`

#### ✅ What Developer 2 SHOULD Create:
1. **Templates automatically wired to Developer 1's existing views** (create these exact file paths and Developer 1's views at `/`, `/accounts/...`, and `/menu/...` will render them automatically without changing a single line of Python!):
   - `templates/base.html` — Shared header, navigation, footer, notification badge.
   - `templates/customer/home.html` — Restaurant homepage (receives `categories`, `featured_offers`, `restaurant_settings`).
   - `templates/customer/login.html` — Login form (receives `form` with `identifier` and `password`).
   - `templates/customer/register.html` — Registration form (receives `form`).
   - `templates/customer/profile.html` — Customer profile & notification preferences (receives `user_form`, `pref_form`, `addresses`).
   - `templates/customer/addresses.html` — Saved delivery addresses list & add form (receives `form`, `addresses`).
   - `templates/customer/address_edit.html` — Edit delivery address page (receives `form`, `address`).
   - `templates/customer/menu_list.html` — Food catalog with category & search filters (receives `categories`, `food_items`, `featured_offers`, `selected_category`, `search_query`).
   - `templates/customer/category_detail.html` — Single category page (receives `category`, `food_items`).
   - `templates/customer/food_detail.html` — Single food item detail page (receives `food_item`).
2. **Templates for Cart, Checkout & Order Tracking (integrated with Developer 3 & Developer 4 APIs):**
   - `templates/customer/cart.html`
   - `templates/customer/checkout.html`
   - `templates/customer/order_confirmation.html`
   - `templates/customer/order_history.html`
   - `templates/customer/order_tracking.html` (includes Leaflet map for live rider tracking)
3. **Frontend Assets:**
   - `static/css/customer/main.css`
   - `static/js/customer/cart.js`, `checkout.js`, `tracking.js`

#### ❌ What Developer 2 MUST NOT Do:
- **Do NOT** create new Django apps or database models.
- **Do NOT** modify `apps/accounts/`, `apps/menu/`, or `apps/core/`.
- **Do NOT** hardcode currency symbols (`₦` or `$`); always use `{{ CURRENCY_SYMBOL }}` (which outputs `GH₵`) or `{{ food_item.formatted_price }}`.

---

### 👨‍💻 DEVELOPER 3 — Orders, Cart, Checkout, Delivery Fees & Paystack Payments
**Branch:** `feature/dev3-orders-payments`  
**Assigned Folders:** `apps/orders/`, `apps/payments/`

#### ✅ What Developer 3 SHOULD Create:
1. **Inside `apps/orders/`:**
   - `models.py` — Implement `Cart` (`orders_cart`), `CartItem` (`orders_cartitem`), `Order` (`orders_order`), `OrderItem` (`orders_orderitem`), and `OrderStatusHistory` (`orders_orderstatushistory`) matching `docs/schema.sql`.
     - **Note on `Order.promo_code`:** If `apps.promotions` hasn't created `PromoCode` yet, either coordinate with Developer 5 or make `promo_code` a nullable FK once `promotions.PromoCode` exists.
   - `services.py` — Cart calculations, server-side delivery fee calculation (`FLAT` vs `DISTANCE`), unique order reference generation, order status transition validation, immutable `OrderStatusHistory` recording, and cancellation rules (PRD §4.11 & §4.12).
   - `serializers.py`, `views.py`, `api_views.py`, `urls.py`, `api_urls.py`, `admin.py`, `tests.py`.
   - `tasks.py` — Celery task to auto-cancel unpaid `CARD` orders after 15 minutes (PRD §4.13).
2. **Inside `apps/payments/`:**
   - `models.py` — Implement `Payment` (`payments_payment`) with default `currency = "GHS"`.
   - `services.py` — Paystack `/transaction/initialize`, server-side `/transaction/verify/<ref>`, HMAC SHA-512 webhook signature check (`x-paystack-signature`), idempotent webhook processing, cash-on-delivery flow, and refund handling.
   - `serializers.py`, `views.py`, `api_views.py`, `urls.py`, `api_urls.py`, `admin.py`, `tests.py`.

#### 🔄 What Developer 3 SHOULD Import From Developer 1 (Do Not Recreate!):
```python
from django.conf import settings  # settings.AUTH_USER_MODEL for customer/user FKs
from apps.accounts.models import Address, User
from apps.menu.models import FoodItem
from apps.core.models import RestaurantSettings, TimeStampedModel
from apps.core.maps import MapsFacade  # MapsFacade.evaluate_destination(lat, lng)
from apps.core.utils import generate_unique_reference, quantize_money, format_currency
from apps.core.permissions import IsCustomer, IsStaffOrAdmin, IsOwnerOrAdmin
```

#### 🔧 What Developer 3 May Update:
- `config/urls.py`: Add **only** your URL includes:
  ```python
  path("orders/", include("apps.orders.urls", namespace="orders")),
  path("api/orders/", include("apps.orders.api_urls", namespace="orders-api")),
  path("payments/", include("apps.payments.urls", namespace="payments")),
  path("api/payments/", include("apps.payments.api_urls", namespace="payments-api")),
  ```

#### ❌ What Developer 3 MUST NOT Do:
- **Do NOT** edit `apps/accounts/models.py` or `apps/menu/models.py`.
- **Do NOT** use `FloatField` for money (always use `DecimalField(max_digits=12, decimal_places=2)` and `quantize_money()`).
- **Do NOT** create a duplicate settings model for delivery fees—use `RestaurantSettings.get_solo()` from `apps.core.models`.

---

### 👨‍💻 DEVELOPER 4 — Delivery Dispatch, Live GPS Tracking, WebSockets & Notifications
**Branch:** `feature/dev4-delivery-tracking`  
**Assigned Folders:** `apps/delivery/`, `apps/notifications/`, `templates/rider/`, `config/asgi.py`

#### ✅ What Developer 4 SHOULD Create:
1. **Inside `apps/delivery/`:**
   - `models.py` — Implement `Delivery` (`delivery_delivery`) and `RiderLocation` (`delivery_riderlocation`) matching `docs/schema.sql`.
     - **CRITICAL:** `Delivery.rider` and `RiderLocation.rider` must reference `apps.accounts.models.RiderProfile` (`on_delete=models.SET_NULL` / `CASCADE`). **Do NOT create a second `RiderProfile` model!**
   - `services.py` — Rider assignment, delivery status transitions (`ASSIGNED`, `IN_TRANSIT`, `DELIVERED`, `FAILED`, `CANCELLED`), GPS ping ingestion (checking `rider_profile.location_consent` and active `OUT_FOR_DELIVERY` status), ETA updates, and location pruning on delivery completion.
   - `consumers.py` & `routing.py` — `OrderConsumer` (`ws/orders/<reference>/`) and `DeliveryConsumer` (`ws/delivery/<id>/`) using Django Channels.
   - `tasks.py` — Celery tasks `recompute_eta` and `prune_rider_locations`.
   - `serializers.py`, `views.py`, `api_views.py`, `urls.py`, `api_urls.py`, `admin.py`, `tests.py`.
2. **Inside `apps/notifications/`:**
   - `models.py` — Implement `Notification` (`notifications_notification`) matching `docs/schema.sql`.
   - `tasks.py` — Celery `@shared_task` `send_order_notification` with exponential backoff retries, respecting `user.customer_profile.notify_in_app`, `notify_email`, and `notify_sms`.
   - `services.py`, `serializers.py`, `api_views.py`, `api_urls.py`, `admin.py`, `tests.py`.
3. **Inside `templates/rider/`:**
   - `templates/rider/dashboard.html` — Rider's assigned deliveries, status update buttons, and GPS sharing toggle.

#### 🔄 What Developer 4 SHOULD Import From Developer 1:
```python
from apps.accounts.models import RiderProfile, User
from apps.accounts.services import get_available_riders, update_rider_gps
from apps.core.maps import MapsFacade
from apps.core.permissions import IsRider, IsStaffOrAdmin, RiderRequiredMixin
```

#### 🔧 What Developer 4 May Update:
- `config/asgi.py`: Import your `websocket_urlpatterns` from `apps.delivery.routing` into `ProtocolTypeRouter`.
- `config/urls.py`: Add **only** your URL includes for `apps.delivery` and `apps.notifications`.

#### ❌ What Developer 4 MUST NOT Do:
- **Do NOT** create a duplicate `RiderProfile` model inside `apps/delivery/models.py`—use `apps.accounts.models.RiderProfile`.
- **Do NOT** accept rider GPS pings unless `rider_profile.location_consent == True`.

---

### 👨‍💻 DEVELOPER 5 — Admin/Staff Dashboards, Promotions, Reviews, Reports & QA
**Branch:** `feature/dev5-admin-reviews`  
**Assigned Folders:** `apps/promotions/`, `apps/reviews/`, `apps/dashboard/`, `templates/admin/`, `templates/staff/`, `static/css/admin/`, `static/js/admin/`, `tests/`

#### ✅ What Developer 5 SHOULD Create:
1. **Inside `apps/promotions/`:**
   - `models.py` — Implement `Campaign` (`promotions_campaign`, with M2M `items` to `menu.FoodItem`) and `PromoCode` (`promotions_promocode`) matching `docs/schema.sql`.
   - `tasks.py` — Celery task `deactivate_expired_promotions`.
   - `services.py`, `serializers.py`, `views.py`, `api_views.py`, `urls.py`, `api_urls.py`, `admin.py`, `tests.py`.
2. **Inside `apps/reviews/`:**
   - `models.py` — Implement `Review` (`reviews_review`) with 5-point `ReviewRating` choices (`VERY_BAD`, `BAD`, `OKAY`, `GOOD`, `EXCELLENT`) for `overall_rating`, `food_rating`, `service_rating`, `comment`, and `is_visible`.
   - `services.py` — Enforce PRD §4.10 rules: only the customer who placed a `DELIVERED` order can review it, 1 review per order, editable within 7 days, soft-hide moderation (`is_visible=False`, never hard delete).
   - `serializers.py`, `views.py`, `api_views.py`, `urls.py`, `api_urls.py`, `admin.py`, `tests.py`.
3. **Inside `apps/dashboard/`:**
   - `views.py`, `api_views.py`, `services.py`, `urls.py`, `api_urls.py`, `tasks.py` (`generate_report_export`).
   - Admin & Staff dashboards for managing orders, menus, riders, delivery-fee settings (reading/updating `RestaurantSettings.get_solo()`), revenue reports, popular food items, and review analytics.
4. **Inside `templates/staff/`, `templates/admin/`, and `tests/`:**
   - Staff preparation dashboard & Admin reporting templates.
   - End-to-end integration tests in `tests/`.

#### 🔄 What Developer 5 SHOULD Import From Developer 1:
```python
from apps.core.models import RestaurantSettings, TimeStampedModel
from apps.core.permissions import (
    AdminRequiredMixin,
    StaffOrAdminRequiredMixin,
    IsAdminRole,
    IsStaffOrAdmin,
    admin_required,
    staff_or_admin_required,
)
from apps.accounts.models import User, RiderProfile
from apps.menu.models import Category, FoodItem
```

#### ❌ What Developer 5 MUST NOT Do:
- **Do NOT** duplicate order, payment, or menu business logic inside `apps/dashboard/`—call the services in `apps.menu.services`, `apps.accounts.services`, `apps.orders.services`, and `apps.delivery.services`.
- **Do NOT** create a new delivery-fee configuration table—edit `RestaurantSettings.get_solo()` from `apps.core.models`.

---

## 3. Quick Summary Table: Who Touches What?

| Path | Dev 1 | Dev 2 | Dev 3 | Dev 4 | Dev 5 |
|---|:---:|:---:|:---:|:---:|:---:|
| `config/settings/*`, `manage.py`, `apps/core/*` | **OWNER** | Read Only | Read Only | Read Only | Read Only |
| `apps/accounts/*`, `apps/menu/*` | **OWNER** | Calls Views/APIs | Imports Models | Imports `RiderProfile` | Imports Models/Services |
| `config/urls.py` | **OWNER** | — | Add `orders`/`payments` URLs | Add `delivery`/`notifications` URLs | Add `promotions`/`reviews`/`dashboard` URLs |
| `config/asgi.py` | Baseline | — | — | **OWNER** (WebSocket routing) | — |
| `templates/customer/*`, `static/*/customer/*` | — | **OWNER** | — | — | — |
| `apps/orders/*`, `apps/payments/*` | Stubbed | Calls APIs | **OWNER** | Triggers Events | Reads for Reports |
| `apps/delivery/*`, `apps/notifications/*`, `templates/rider/*` | Stubbed | Connects WS | Publishes Events | **OWNER** | Reads for Reports |
| `apps/promotions/*`, `apps/reviews/*`, `apps/dashboard/*` | Stubbed | Displays Promos/Reviews | Validates `PromoCode` | Sends Promo/Review Alerts | **OWNER** |
| `templates/staff/*`, `templates/admin/*`, `tests/*` | Stubbed | — | — | — | **OWNER** |
